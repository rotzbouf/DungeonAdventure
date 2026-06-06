"""
Perk pick screen — shown at every milestone level-up.

Three cards are displayed; the player must click one before the game
resumes.  ESC is intentionally disabled (force a choice).
"""
from __future__ import annotations

import math
import random

import pygame

from src.settings import SCREEN_WIDTH, SCREEN_HEIGHT, HUD_HEIGHT
from src.perks import Perk, CATEGORY_COLORS
from src.locale import t

# ── Layout ────────────────────────────────────────────────────────────────────
_CARD_W  = 290
_CARD_H  = 380
_CARD_GAP = 36
_CARDS_TOTAL_W = _CARD_W * 3 + _CARD_GAP * 2
_CARDS_X = (SCREEN_WIDTH - _CARDS_TOTAL_W) // 2
_CARDS_Y = (SCREEN_HEIGHT - HUD_HEIGHT) // 2 - _CARD_H // 2 - 30

# ── Palette ───────────────────────────────────────────────────────────────────
_BG_TINT  = (0, 0, 0, 210)
_CARD_BG  = (12,  8,  4)
_CARD_HOV = (22, 16, 10)
_DIM      = (100, 88, 68)
_WHITE    = (220, 220, 210)
_GOLD     = (220, 175,  0)


class PerkScreen:
    def __init__(self):
        self._fl   = pygame.font.SysFont("monospace", 28, bold=True)
        self._fm   = pygame.font.SysFont("monospace", 20, bold=True)
        self._fs   = pygame.font.SysFont("monospace", 16)
        self._fxs  = pygame.font.SysFont("monospace", 13)

        self._choices: list[Perk] = []
        self._level:   int        = 0
        self._hovered: int        = -1   # index 0-2
        self._time:    float      = 0.0
        self._chosen:  int        = -1   # set when player picks

    # ── Public API ────────────────────────────────────────────────────────────

    def open(self, choices: list[Perk], level: int):
        self._choices = choices[:3]
        self._level   = level
        self._hovered = -1
        self._chosen  = -1
        self._time    = 0.0

    @property
    def is_open(self) -> bool:
        return bool(self._choices) and self._chosen < 0

    def handle_event(self, event: pygame.event.Event) -> str | None:
        """
        Process an event.  Returns the chosen perk ID when a card is clicked,
        otherwise None.  ESC is intentionally ignored.
        """
        if event.type == pygame.MOUSEMOTION:
            self._hovered = self._card_index_at(*event.pos)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            idx = self._card_index_at(*event.pos)
            if 0 <= idx < len(self._choices):
                self._chosen = idx
                return self._choices[idx].id
        return None

    def update(self, dt: float):
        self._time += dt

    def draw(self, surface: pygame.Surface):
        # Full-screen dimmed overlay
        ov = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT - HUD_HEIGHT),
                             pygame.SRCALPHA)
        ov.fill(_BG_TINT)
        surface.blit(ov, (0, 0))

        # Title
        title_txt = t("perk.screen.title", n=self._level)
        pulse     = 0.85 + 0.15 * math.sin(self._time * 3.0)
        tcol      = tuple(int(c * pulse) for c in _GOLD)
        title_s   = self._fl.render(title_txt, True, tcol)
        sh_s      = self._fl.render(title_txt, True, (0, 0, 0))
        ty        = _CARDS_Y - 56
        surface.blit(sh_s,   sh_s.get_rect(  centerx=SCREEN_WIDTH // 2, centery=ty + 2))
        surface.blit(title_s, title_s.get_rect(centerx=SCREEN_WIDTH // 2, centery=ty))

        subtitle = self._fs.render(
            t("perk.screen.subtitle"),
            True, _DIM)
        surface.blit(subtitle, subtitle.get_rect(
            centerx=SCREEN_WIDTH // 2, centery=ty + 30))

        # Cards
        for i, perk in enumerate(self._choices):
            self._draw_card(surface, i, perk)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _card_rect(self, idx: int) -> pygame.Rect:
        x = _CARDS_X + idx * (_CARD_W + _CARD_GAP)
        return pygame.Rect(x, _CARDS_Y, _CARD_W, _CARD_H)

    def _card_index_at(self, mx: int, my: int) -> int:
        for i in range(len(self._choices)):
            if self._card_rect(i).collidepoint(mx, my):
                return i
        return -1

    def _draw_card(self, surface: pygame.Surface, idx: int, perk: Perk):
        r       = self._card_rect(idx)
        hov     = (idx == self._hovered)
        cat_col = CATEGORY_COLORS.get(perk.category, (140, 140, 140))

        # Hover lift effect
        if hov:
            r = r.move(0, -6)

        # Drop shadow
        sh = pygame.Surface((r.width + 10, r.height + 10), pygame.SRCALPHA)
        sh.fill((0, 0, 0, 100 if hov else 60))
        surface.blit(sh, (r.left - 5, r.top + (10 if hov else 6)))

        # Card background
        bg_col = _CARD_HOV if hov else _CARD_BG
        pygame.draw.rect(surface, bg_col, r, border_radius=8)

        # Coloured top bar (category colour)
        bar_r = pygame.Rect(r.left, r.top, r.width, 10)
        pygame.draw.rect(surface, cat_col, bar_r,
                         border_top_left_radius=8, border_top_right_radius=8)

        # Outer border — glows in category colour when hovered
        border_col = cat_col if hov else tuple(c // 3 for c in cat_col)
        border_w   = 3 if hov else 1
        pygame.draw.rect(surface, border_col, r, border_w, border_radius=8)

        pad = 16
        y   = r.top + 22

        # Category badge
        badge_txt = t(f"perk.cat.{perk.category}")
        badge_s   = self._fxs.render(badge_txt, True, cat_col)
        badge_bg  = pygame.Surface((badge_s.get_width() + 10,
                                     badge_s.get_height() + 4), pygame.SRCALPHA)
        badge_bg.fill((*cat_col, 40))
        surface.blit(badge_bg, (r.left + pad, y))
        surface.blit(badge_s,  (r.left + pad + 5, y + 2))
        y += badge_s.get_height() + 12

        # Perk name
        name_col  = cat_col if hov else _WHITE
        perk_name = t(f"perk.{perk.id}.name")
        name_s    = self._fm.render(perk_name, True, name_col)
        # Shadow
        sh_n = self._fm.render(perk_name, True, (0, 0, 0))
        surface.blit(sh_n, (r.left + pad + 1, y + 1))
        surface.blit(name_s, (r.left + pad, y))
        y += name_s.get_height() + 14

        # Divider
        pygame.draw.line(surface, tuple(c // 4 for c in cat_col),
                         (r.left + pad, y), (r.right - pad, y))
        y += 10

        # Description (word-wrapped)
        for line in _wrap(t(f"perk.{perk.id}.desc"), r.width - pad * 2, self._fs):
            ls = self._fs.render(line, True, _WHITE if hov else _DIM)
            surface.blit(ls, (r.left + pad, y))
            y += ls.get_height() + 3

        # Tier indicator (bottom-right)
        tier_txt = t("perk.screen.tier", n=perk.tier)
        tier_s   = self._fxs.render(tier_txt, True, tuple(c // 2 for c in cat_col))
        surface.blit(tier_s, (r.right - tier_s.get_width() - pad,
                               r.bottom - tier_s.get_height() - 8))

        # "CLICK" hint at bottom centre when hovered
        if hov:
            hint_s = self._fxs.render(t("perk.screen.click"), True, cat_col)
            hint_p = hint_s.get_rect(centerx=r.centerx,
                                      centery=r.bottom - 18)
            surface.blit(hint_s, hint_p)


def _wrap(text: str, max_w: int, font) -> list[str]:
    """Word-wrap *text* to fit within *max_w* pixels."""
    words = text.split()
    lines: list[str] = []
    cur   = ""
    for w in words:
        test = (cur + " " + w).strip()
        if font.size(test)[0] <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines
