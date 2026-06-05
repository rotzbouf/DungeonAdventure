"""
D2-style Character Screen  (C key).

Shows STR / DEX / VIT / ENE with stat point allocation (+) buttons,
current XP bar, and a derived-stats summary panel.
"""
from __future__ import annotations

import math
import pygame
from src.settings import (SCREEN_WIDTH, SCREEN_HEIGHT, HUD_HEIGHT, MAX_PLAYER_LEVEL,
                           WHITE, YELLOW, GRAY, LIGHT_GRAY)
from src.locale import t

# ── Geometry ──────────────────────────────────────────────────────────────────
_PW = 960
_PH = 780

# ── Palette ───────────────────────────────────────────────────────────────────
_PANEL  = (13,   6,  22)
_HEADER = (20,   9,  38)
_BORDER = (68, 100, 176)
_GOLD_C = (252, 188,   0)
_ROW_N  = (20,  10,  36)
_BTN_BG = (52,  28,  92)
_BTN_AV = (10, 130,  10)
_BTN_HV = (20, 200,  20)
_XP_BG  = (18,  10,  30)
_XP_FG  = (50, 170,  50)

# ── Per-stat color themes (normal, dim) ───────────────────────────────────────
_STAT_COLORS = {
    "str": ((220,  80,  40), ( 70,  20,  10)),
    "dex": (( 60, 210, 100), ( 16,  66,  28)),
    "vit": (( 70, 150, 230), ( 18,  44,  74)),
    "ene": ((190, 110, 250), ( 58,  28,  82)),
}

# ── Stat definitions ──────────────────────────────────────────────────────────
_STATS = [
    ("str", "Strength",  "STR", "Each point: +2 Attack"),
    ("dex", "Dexterity", "DEX", "Each point: +1 Defense  +0.5% Crit"),
    ("vit", "Vitality",  "VIT", "Each point: +10 Max Life"),
    ("ene", "Energy",    "ENE", "Each point: +5 Max Mana"),
]

_PIP_TOTAL = 20   # dots shown in the visual pip bar
_PIP_SIZE  = 10
_PIP_GAP   = 4
_ROW_H     = 106
_ROW_GAP   = 7


class CharScreen:
    def __init__(self):
        self._fonts_init  = False
        self._notify_msg  = ""
        self._notify_t    = 0.0
        self._btn_rects: dict[str, pygame.Rect] = {}
        self._time        = 0.0

    # ── Init ──────────────────────────────────────────────────────────────────

    def _init_fonts(self):
        if self._fonts_init:
            return
        self._f_title = pygame.font.SysFont("monospace", 34, bold=True)
        self._f_lv    = pygame.font.SysFont("monospace", 22, bold=True)
        self._f_badge = pygame.font.SysFont("monospace", 20, bold=True)
        self._f_name  = pygame.font.SysFont("monospace", 26, bold=True)
        self._f_desc  = pygame.font.SysFont("monospace", 17)
        self._f_val   = pygame.font.SysFont("monospace", 46, bold=True)
        self._f_plus  = pygame.font.SysFont("monospace", 34, bold=True)
        self._f_pts   = pygame.font.SysFont("monospace", 24, bold=True)
        self._f_sm    = pygame.font.SysFont("monospace", 18)
        self._f_xs    = pygame.font.SysFont("monospace", 15)
        self._fonts_init = True

    def notify(self, msg: str, duration: float = 1.8):
        self._notify_msg = msg
        self._notify_t   = duration

    def update(self, dt: float):
        self._notify_t = max(0.0, self._notify_t - dt)
        self._time    += dt

    # ── Geometry ──────────────────────────────────────────────────────────────

    def _panel(self) -> pygame.Rect:
        x = (SCREEN_WIDTH  - _PW) // 2
        y = (SCREEN_HEIGHT - HUD_HEIGHT - _PH) // 2
        return pygame.Rect(x, y, _PW, _PH)

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _draw_pip_bar(surface, val, col, dim, x, y, max_w):
        """Filled / empty dot bar visualising stat investment."""
        filled = min(val, _PIP_TOTAL)
        step   = _PIP_SIZE + _PIP_GAP
        total_w = _PIP_TOTAL * step - _PIP_GAP
        # shrink if not enough room
        if max_w < total_w:
            step = max(7, max_w // _PIP_TOTAL)
        for i in range(_PIP_TOTAL):
            c = col if i < filled else dim
            pygame.draw.rect(surface, c,
                             (x + i * step, y, _PIP_SIZE, _PIP_SIZE),
                             border_radius=2)
        if val > _PIP_TOTAL:
            ovf = pygame.font.SysFont("monospace", 13).render(
                f"+{val - _PIP_TOTAL}", True, col)
            surface.blit(ovf, (x + _PIP_TOTAL * step + 4, y - 1))

    def _draw_stat_row(self, surface, player, key, row_r, mx, my, has_pts):
        col, dim = _STAT_COLORS[key]
        val = getattr(player, f"{key}_pts")

        # Row background + left accent strip
        pygame.draw.rect(surface, _ROW_N, row_r)
        pygame.draw.rect(surface, (50, 30, 80), row_r, 1)
        pygame.draw.rect(surface, col,
                         pygame.Rect(row_r.x, row_r.y, 6, row_r.h))

        # Badge circle
        bx, by = row_r.x + 50, row_r.centery
        pygame.draw.circle(surface, dim, (bx, by), 30)
        pygame.draw.circle(surface, col, (bx, by), 30, 2)
        ab = self._f_badge.render(t(f"stat.{key}.short"), True, col)
        surface.blit(ab, ab.get_rect(center=(bx, by)))

        # Stat name + description
        nx = row_r.x + 94
        name_s = self._f_name.render(t(f"stat.{key}.long"), True, WHITE)
        surface.blit(name_s, (nx, row_r.y + 10))
        desc_s = self._f_desc.render(t(f"stat.{key}.desc"), True,
                                     (160, 155, 175))
        surface.blit(desc_s, (nx, row_r.y + 44))

        # Pip bar
        pip_x = nx
        pip_y = row_r.y + 72
        pip_max_w = row_r.w - 94 - 260
        self._draw_pip_bar(surface, val, col, dim, pip_x, pip_y, pip_max_w)

        # Vertical divider before value/button zone
        div_x = row_r.right - 210
        pygame.draw.line(surface, (50, 35, 80),
                         (div_x, row_r.y + 8),
                         (div_x, row_r.bottom - 8), 1)

        # Value (large, right-aligned inside value zone)
        val_s = self._f_val.render(str(val), True, _GOLD_C)
        val_x = row_r.right - 130 - val_s.get_width()
        val_y = row_r.centery - val_s.get_height() // 2
        surface.blit(val_s, (val_x, val_y))

        # + button
        btn = pygame.Rect(row_r.right - 58, row_r.centery - 24, 46, 46)
        hov = btn.collidepoint(mx, my) and has_pts
        if has_pts:
            btn_col = _BTN_HV if hov else _BTN_AV
            # Outer glow ring
            pygame.draw.rect(surface, col,
                             btn.inflate(8, 8), 2, border_radius=10)
        else:
            btn_col = _BTN_BG
        pygame.draw.rect(surface, btn_col, btn, border_radius=8)
        pygame.draw.rect(surface,
                         col if has_pts else (60, 60, 60),
                         btn, 2, border_radius=8)
        plus_s = self._f_plus.render("+", True,
                                      WHITE if has_pts else (80, 80, 80))
        surface.blit(plus_s, plus_s.get_rect(center=btn.center))
        return btn

    # ── Draw ──────────────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface, player):
        self._init_fonts()
        panel  = self._panel()
        mx, my = pygame.mouse.get_pos()

        # Dimmed overlay
        ov = pygame.Surface(
            (SCREEN_WIDTH, SCREEN_HEIGHT - HUD_HEIGHT), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 172))
        surface.blit(ov, (0, 0))

        # Panel outer glow + fill
        pygame.draw.rect(surface, (38, 56, 110), panel.inflate(4, 4),
                         border_radius=4)
        pygame.draw.rect(surface, _PANEL, panel)
        pygame.draw.rect(surface, _BORDER, panel, 2)

        # ── Header ────────────────────────────────────────────────────────────
        hdr_r = pygame.Rect(panel.x, panel.y, panel.w, 68)
        pygame.draw.rect(surface, _HEADER, hdr_r)
        pygame.draw.line(surface, _BORDER,
                         (panel.x, panel.y + 68),
                         (panel.right, panel.y + 68), 1)

        title = self._f_title.render(t("char.title"), True, _GOLD_C)
        surface.blit(title, title.get_rect(
            centerx=panel.centerx, centery=panel.y + 22))

        if player.level >= MAX_PLAYER_LEVEL:
            lv_str = t("char.max", n=player.level)
        else:
            lv_str = t("char.hero", n=player.level)
        lv_s = self._f_lv.render(lv_str, True, LIGHT_GRAY)
        surface.blit(lv_s, lv_s.get_rect(
            centerx=panel.centerx, centery=panel.y + 52))

        y = panel.y + 74

        # ── XP bar ────────────────────────────────────────────────────────────
        xp_r = pygame.Rect(panel.x + 16, y, panel.w - 32, 24)
        pygame.draw.rect(surface, _XP_BG, xp_r, border_radius=5)
        if player.xp_to_next > 0:
            fill = int(xp_r.w * min(1.0, player.xp / player.xp_to_next))
            if fill > 0:
                pygame.draw.rect(surface, _XP_FG,
                                 pygame.Rect(xp_r.x, xp_r.y, fill, xp_r.h),
                                 border_radius=5)
                # Highlight top edge
                pygame.draw.rect(surface, (110, 240, 110),
                                 pygame.Rect(xp_r.x + 2, xp_r.y + 2,
                                             fill - 4, 4),
                                 border_radius=3)
        pygame.draw.rect(surface, _BORDER, xp_r, 1, border_radius=5)
        xp_label = (t("char.xp", cur=player.xp, nxt=player.xp_to_next)
                    if player.level < MAX_PLAYER_LEVEL
                    else t("char.xp_max"))
        xp_s = self._f_xs.render(xp_label, True, (200, 240, 200))
        surface.blit(xp_s, xp_s.get_rect(
            centerx=xp_r.centerx, centery=xp_r.centery))
        y += 32

        # ── Unspent stat points banner ─────────────────────────────────────────
        BANNER_H = 42
        if player.stat_points > 0:
            pulse = 0.5 + 0.5 * math.sin(self._time * 3.5)
            pts_col = (
                int(80 + 172 * pulse),
                int(205 + 50 * pulse),
                int(80 + 40 * pulse),
            )
            pts_txt = self._f_pts.render(
                t("char.stat_pts", n=player.stat_points), True, pts_col)
            bg_r = pts_txt.get_rect(
                centerx=panel.centerx, centery=y + BANNER_H // 2)
            pygame.draw.rect(surface, (0, 48, 0), bg_r.inflate(24, 12),
                             border_radius=7)
            pygame.draw.rect(surface, (0, int(80 + 40 * pulse), 0),
                             bg_r.inflate(24, 12), 1, border_radius=7)
            surface.blit(pts_txt, bg_r)
        y += BANNER_H

        # ── Core stats block ──────────────────────────────────────────────────
        self._btn_rects.clear()
        has_pts = player.stat_points > 0
        for key, *_ in _STATS:
            row_r = pygame.Rect(panel.x + 12, y, panel.w - 24, _ROW_H)
            btn = self._draw_stat_row(surface, player, key,
                                      row_r, mx, my, has_pts)
            self._btn_rects[key] = btn
            y += _ROW_H + _ROW_GAP

        # ── Separator ─────────────────────────────────────────────────────────
        y += 4
        pygame.draw.line(surface, _BORDER,
                         (panel.x + 16, y), (panel.right - 16, y), 1)
        y += 12

        # ── Derived stats (two columns) ────────────────────────────────────────
        derived = [
            (t("derived.attack"),    str(player.attack)),
            (t("derived.defense"),   str(player.defense)),
            (t("derived.max_life"),  str(player.max_hp_total)),
            (t("derived.max_mana"),  str(player.max_mana_total)),
            (t("derived.crit"),      f"{player.crit_chance:.1f}%"),
            (t("derived.lifesteal"), f"{player.life_steal:.0f}%"),
            (t("derived.move_spd"),  f"{int(player.move_speed)}"),
            (t("derived.gold_find"), f"+{player.gold_find_bonus:.0f}%"),
        ]
        col_w = (_PW - 32) // 2
        for i, (label, val) in enumerate(derived):
            col   = i % 2
            row   = i // 2
            dx    = panel.x + 16 + col * col_w
            dy    = y + row * 22
            if dy + 18 > panel.bottom - 30:
                break
            l_s = self._f_sm.render(f"{label}:", True, LIGHT_GRAY)
            v_s = self._f_sm.render(val,          True, _GOLD_C)
            surface.blit(l_s, (dx, dy))
            surface.blit(v_s, (dx + col_w - v_s.get_width() - 8, dy))

        # ── Notification ──────────────────────────────────────────────────────
        if self._notify_t > 0:
            alpha = min(255, int(self._notify_t * 160))
            msg_s = self._f_pts.render(self._notify_msg, True, YELLOW)
            msg_s.set_alpha(alpha)
            surface.blit(msg_s, msg_s.get_rect(
                centerx=panel.centerx, y=panel.bottom - 30))

        # ── Hint footer ───────────────────────────────────────────────────────
        hint = self._f_xs.render(t("char.hint"), True, GRAY)
        surface.blit(hint, hint.get_rect(
            centerx=panel.centerx, y=panel.bottom - 14))

    # ── Click ─────────────────────────────────────────────────────────────────

    def handle_click(self, mx: int, my: int, player) -> bool:
        for key, btn in self._btn_rects.items():
            if btn.collidepoint(mx, my):
                if player.spend_stat(key):
                    self.notify(f"{t(f'stat.{key}.long')} → "
                                f"{getattr(player, key + '_pts')}")
                else:
                    self.notify(t("char.no_pts"))
                return True
        return False
