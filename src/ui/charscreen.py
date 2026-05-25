"""
D2-style Character Screen  (C key).

Shows STR / DEX / VIT / ENE with stat point allocation (+) buttons,
current XP bar, and a derived-stats summary panel.
"""
from __future__ import annotations

import pygame
from src.settings import (SCREEN_WIDTH, SCREEN_HEIGHT, HUD_HEIGHT, MAX_PLAYER_LEVEL,
                           WHITE, YELLOW, GRAY, LIGHT_GRAY)
from src.locale import t

# ── Geometry ──────────────────────────────────────────────────────────────────
_PW = 520
_PH = 490

# ── Palette ───────────────────────────────────────────────────────────────────
_BG     = (8,   4,  12)
_PANEL  = (16,  8,  28)
_HEADER = (24,  12, 44)
_BORDER = (68, 100, 176)   # dungeon-stone blue (feels like a screen from the same world)
_GOLD_C = (252, 188,   0)
_STAT_C = (140, 180, 252)  # label colour for stat names
_ROW_N  = (20,  10,  36)
_ROW_H  = (36,  18,  60)
_BTN_BG = (52,  28,  92)   # + button inactive
_BTN_AV = (0,  120,   0)   # + button when points available
_BTN_HV = (0,  180,   0)   # + button hovered
_XP_BG  = (20,  12,  36)
_XP_FG  = (60, 180,  60)

# ── Stat definitions (key, display name, description) ─────────────────────────
_STATS = [
    ("str", "Strength",  "STR",
     "Each point: +2 Attack"),
    ("dex", "Dexterity", "DEX",
     "Each point: +1 Defense  +0.5% Crit"),
    ("vit", "Vitality",  "VIT",
     "Each point: +10 Max Life"),
    ("ene", "Energy",    "ENE",
     "Each point: +5 Max Mana"),
]


class CharScreen:
    def __init__(self):
        self._fonts_init = False
        self._notify_msg = ""
        self._notify_t   = 0.0
        self._btn_rects: dict[str, pygame.Rect] = {}

    # ── Init ──────────────────────────────────────────────────────────────────

    def _init_fonts(self):
        if self._fonts_init:
            return
        self._font_xl = pygame.font.SysFont("monospace", 22, bold=True)
        self._font_lg = pygame.font.SysFont("monospace", 18, bold=True)
        self._font_md = pygame.font.SysFont("monospace", 14, bold=True)
        self._font_sm = pygame.font.SysFont("monospace", 13)
        self._fonts_init = True

    def notify(self, msg: str, duration: float = 1.8):
        self._notify_msg = msg
        self._notify_t   = duration

    def update(self, dt: float):
        self._notify_t = max(0.0, self._notify_t - dt)

    # ── Geometry ──────────────────────────────────────────────────────────────

    def _panel(self) -> pygame.Rect:
        x = (SCREEN_WIDTH  - _PW) // 2
        y = (SCREEN_HEIGHT - HUD_HEIGHT - _PH) // 2
        return pygame.Rect(x, y, _PW, _PH)

    # ── Draw ──────────────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface, player):
        self._init_fonts()
        panel  = self._panel()
        mx, my = pygame.mouse.get_pos()

        # ── Overlay ───────────────────────────────────────────────────────────
        overlay = pygame.Surface(
            (SCREEN_WIDTH, SCREEN_HEIGHT - HUD_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 155))
        surface.blit(overlay, (0, 0))

        # ── Panel ─────────────────────────────────────────────────────────────
        pygame.draw.rect(surface, _PANEL, panel)
        pygame.draw.rect(surface, _BORDER, panel, 2)

        # ── Header ────────────────────────────────────────────────────────────
        hdr_r = pygame.Rect(panel.x, panel.y, panel.w, 50)
        pygame.draw.rect(surface, _HEADER, hdr_r)
        pygame.draw.line(surface, _BORDER,
                         (panel.x, panel.y + 50),
                         (panel.right, panel.y + 50), 1)

        title = self._font_xl.render(t("char.title"), True, _GOLD_C)
        surface.blit(title, title.get_rect(
            centerx=panel.centerx, centery=panel.y + 16))

        if player.level >= MAX_PLAYER_LEVEL:
            lv_str = t("char.max", n=player.level)
        else:
            lv_str = t("char.hero", n=player.level)
        lv_s = self._font_md.render(lv_str, True, LIGHT_GRAY)
        surface.blit(lv_s, lv_s.get_rect(
            centerx=panel.centerx, centery=panel.y + 38))

        y = panel.y + 58

        # ── XP bar ────────────────────────────────────────────────────────────
        xp_r = pygame.Rect(panel.x + 10, y, panel.w - 20, 14)
        pygame.draw.rect(surface, _XP_BG, xp_r)
        if player.xp_to_next > 0:
            fill = int(xp_r.w * min(1.0, player.xp / player.xp_to_next))
            if fill > 0:
                pygame.draw.rect(surface, _XP_FG,
                                 (xp_r.x, xp_r.y, fill, xp_r.h))
        pygame.draw.rect(surface, _BORDER, xp_r, 1)
        xp_label = (t("char.xp", cur=player.xp, nxt=player.xp_to_next)
                    if player.level < MAX_PLAYER_LEVEL
                    else t("char.xp_max"))
        xp_s = self._font_sm.render(xp_label, True, LIGHT_GRAY)
        surface.blit(xp_s, xp_s.get_rect(centerx=xp_r.centerx,
                                           centery=xp_r.centery))
        y += 20

        # ── Unspent stat points banner ─────────────────────────────────────────
        if player.stat_points > 0:
            blink = int(pygame.time.get_ticks() / 400) % 2 == 0
            pts_col = (80, 255, 120) if blink else _GOLD_C
            pts_txt = self._font_lg.render(
                t("char.stat_pts", n=player.stat_points),
                True, pts_col)
            bg_r = pts_txt.get_rect(centerx=panel.centerx, centery=y + 12)
            pygame.draw.rect(surface, (0, 40, 0), bg_r.inflate(8, 4))
            surface.blit(pts_txt, bg_r)
        y += 30

        # ── Core stats block ──────────────────────────────────────────────────
        self._btn_rects.clear()
        ROW_H = 56
        for key, _long_en, _short_en, _desc_en in _STATS:
            long_name  = t(f"stat.{key}.long")
            short_name = t(f"stat.{key}.short")
            desc       = t(f"stat.{key}.desc")
            val = getattr(player, f"{key}_pts")
            row_r = pygame.Rect(panel.x + 8, y, panel.w - 16, ROW_H - 4)
            pygame.draw.rect(surface, _ROW_N, row_r)
            pygame.draw.rect(surface, (60, 40, 90), row_r, 1)

            # Short name badge
            badge = self._font_lg.render(short_name, True, _STAT_C)
            surface.blit(badge, (row_r.x + 8, row_r.y + 6))

            # Full name
            full = self._font_md.render(long_name, True, WHITE)
            surface.blit(full, (row_r.x + 55, row_r.y + 6))

            # Value (large)
            val_s = self._font_xl.render(str(val), True, _GOLD_C)
            surface.blit(val_s, (row_r.x + 55, row_r.y + 26))

            # Description
            desc_s = self._font_sm.render(desc, True, GRAY)
            surface.blit(desc_s, (row_r.x + 140, row_r.y + 30))

            # + button
            btn = pygame.Rect(row_r.right - 38, row_r.y + (ROW_H - 32) // 2,
                              30, 30)
            has_pts = player.stat_points > 0
            hov     = btn.collidepoint(mx, my) and has_pts
            btn_col = _BTN_HV if hov else (_BTN_AV if has_pts else _BTN_BG)
            pygame.draw.rect(surface, btn_col, btn, border_radius=5)
            pygame.draw.rect(surface, _BORDER, btn, 1, border_radius=5)
            plus_s = self._font_xl.render("+", True,
                                           WHITE if has_pts else (80, 80, 80))
            surface.blit(plus_s, plus_s.get_rect(center=btn.center))
            self._btn_rects[key] = btn

            y += ROW_H

        # ── Separator ─────────────────────────────────────────────────────────
        y += 4
        pygame.draw.line(surface, _BORDER,
                         (panel.x + 10, y), (panel.right - 10, y), 1)
        y += 8

        # ── Derived stats (two columns) ────────────────────────────────────────
        derived = [
            (t("derived.attack"),   str(player.attack)),
            (t("derived.defense"),  str(player.defense)),
            (t("derived.max_life"), str(player.max_hp_total)),
            (t("derived.max_mana"), str(player.max_mana_total)),
            (t("derived.crit"),     f"{player.crit_chance:.1f}%"),
            (t("derived.lifesteal"),f"{player.life_steal:.0f}%"),
            (t("derived.move_spd"), f"{int(player.move_speed)}"),
            (t("derived.gold_find"),f"+{player.gold_find_bonus:.0f}%"),
        ]
        col_w = (_PW - 20) // 2
        for i, (label, val) in enumerate(derived):
            col = i % 2
            row = i // 2
            dx  = panel.x + 10 + col * col_w
            dy  = y + row * 20
            if dy + 16 > panel.bottom - 26:
                break
            l_s = self._font_sm.render(f"{label}:", True, LIGHT_GRAY)
            v_s = self._font_sm.render(val, True, _GOLD_C)
            surface.blit(l_s, (dx, dy))
            surface.blit(v_s, (dx + col_w - v_s.get_width() - 10, dy))

        # ── Notification ──────────────────────────────────────────────────────
        if self._notify_t > 0:
            alpha = min(255, int(self._notify_t * 160))
            msg_s = self._font_md.render(self._notify_msg, True, YELLOW)
            msg_s.set_alpha(alpha)
            surface.blit(msg_s, msg_s.get_rect(
                centerx=panel.centerx, y=panel.bottom - 26))

        # ── Hint footer ───────────────────────────────────────────────────────
        hint = self._font_sm.render(t("char.hint"), True, GRAY)
        surface.blit(hint, hint.get_rect(
            centerx=panel.centerx, y=panel.bottom - 13))

    # ── Click ─────────────────────────────────────────────────────────────────

    def handle_click(self, mx: int, my: int, player) -> bool:
        for key, btn in self._btn_rects.items():
            if btn.collidepoint(mx, my):
                if player.spend_stat(key):
                    long_name_l = t(f"stat.{key}.long")
                    self.notify(f"{long_name_l} → {getattr(player, key + '_pts')}")
                else:
                    self.notify(t("char.no_pts"))
                return True
        return False
