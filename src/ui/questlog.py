"""Quest Journal UI — J key opens/closes."""
from __future__ import annotations

import pygame
from src.settings import SCREEN_WIDTH, SCREEN_HEIGHT, HUD_HEIGHT
from src.locale import t, t_quest_name, t_quest_desc

_BG_FILL    = (8,   6,  4, 218)
_BORDER     = (110, 88, 60)
_TITLE_COL  = (252, 188, 0)
_ACTIVE_COL = (220, 200, 160)
_DONE_COL   = (80,  160,  80)
_DIM_COL    = (100,  90,  70)
_BAR_BG     = (40,   35,  25)
_BAR_FILL   = (80,  160,  80)


class QuestLogScreen:
    def __init__(self):
        self._font_lg = pygame.font.SysFont("monospace", 20, bold=True)
        self._font_md = pygame.font.SysFont("monospace", 13, bold=True)
        self._font_sm = pygame.font.SysFont("monospace", 12)

    def draw(self, surface: pygame.Surface, quest_log):
        W = SCREEN_WIDTH
        H = SCREEN_HEIGHT - HUD_HEIGHT

        # Overlay
        bg = pygame.Surface((W, H), pygame.SRCALPHA)
        bg.fill(_BG_FILL)
        surface.blit(bg, (0, 0))

        # Panel geometry
        pw, ph = 580, H - 36
        px = (W - pw) // 2
        py = 18
        panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
        panel.fill((12, 9, 6, 242))
        surface.blit(panel, (px, py))
        pygame.draw.rect(surface, _BORDER, (px, py, pw, ph), 2)

        # Title bar
        title_s = self._font_lg.render(t("quest.title"), True, _TITLE_COL)
        surface.blit(title_s, (px + pw // 2 - title_s.get_width() // 2, py + 10))
        pygame.draw.line(surface, _BORDER, (px + 10, py + 38), (px + pw - 10, py + 38))

        y    = py + 52
        lh   = 18
        edge = px + pw - 10

        def line(text: str, color: tuple, indent: int = 0):
            nonlocal y
            if y > py + ph - 20:
                return
            s = self._font_sm.render(text, True, color)
            surface.blit(s, (px + 14 + indent, y))
            y += lh

        def section(title: str):
            nonlocal y
            line(title, _BORDER)
            y += 2

        # ── Active quests ─────────────────────────────────────────────────────
        section(t("quest.active"))
        if not quest_log.active:
            line(t("quest.no_active"), _DIM_COL, 8)
        else:
            for q in quest_log.active:
                line(f"▶ {t_quest_name(q.id)}", _ACTIVE_COL)
                line(t_quest_desc(q.id, q.required, q.target), _DIM_COL, 12)

                # Progress bar
                bar_x  = px + 26
                bar_w  = 130
                bar_h  = 7
                pct    = q.current / q.required if q.required else 1.0
                fill_w = int(bar_w * pct)
                pygame.draw.rect(surface, _BAR_BG,  (bar_x, y, bar_w, bar_h))
                if fill_w > 0:
                    pygame.draw.rect(surface, _BAR_FILL, (bar_x, y, fill_w, bar_h))
                pygame.draw.rect(surface, _BORDER,  (bar_x, y, bar_w, bar_h), 1)

                prog_s = self._font_sm.render(
                    f" {q.progress_text()}", True, _ACTIVE_COL)
                surface.blit(prog_s, (bar_x + bar_w + 4, y - 1))
                y += bar_h + 4

                rwd = t("quest.reward_xp", xp=q.reward_xp)
                if q.reward_gold:
                    rwd += t("quest.reward_gold", gold=q.reward_gold)
                line(rwd, (180, 155, 60), 12)
                y += 6

        # ── Divider ───────────────────────────────────────────────────────────
        y += 6
        if y < py + ph - 30:
            pygame.draw.line(surface, _BORDER, (px + 10, y), (edge, y))
            y += 10

        # ── Completed quests ──────────────────────────────────────────────────
        section(t("quest.completed", n=len(quest_log.completed)))
        for q in reversed(quest_log.completed[-10:]):
            line(f"✓  {t_quest_name(q.id)}", _DONE_COL)

        # Footer hint
        hint = self._font_sm.render(t("quest.hint"), True, _DIM_COL)
        surface.blit(hint, (px + pw // 2 - hint.get_width() // 2, py + ph - 18))
