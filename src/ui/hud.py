import math
import pygame
from src.settings import (SCREEN_WIDTH, SCREEN_HEIGHT, HUD_HEIGHT,
                           MAX_DUNGEON_LEVELS, FIREBALL_MANA_COST,
                           BLACK, WHITE, YELLOW, GRAY, LIGHT_GRAY,
                           RED, DARK_RED, BLUE, DARK_BLUE, GREEN)

# ── HUD colours ──────────────────────────────────────────────────────────────
_BG          = (0,   0,   0)
_BORDER      = (68, 100, 176)      # same blue as dungeon stone
_HEART_FULL  = (204,   0,   0)
_HEART_HI    = (252,  80,  80)     # lighter centre
_HEART_HALF  = (140,   0,   0)
_HEART_HALF_HI = (180, 60,  60)
_HEART_EMPTY = ( 52,   0,   0)     # almost-black red outline
_MAGIC_FILL  = (0,  168,   0)      # magic bar fill
_MAGIC_BG    = (0,   40,   0)
_RUPEE       = (0,  168,   0)      # coin icon
_RUPEE_HI    = (0,  252,   0)
_TEXT_BRIGHT = (252, 252, 252)
_TEXT_DIM    = (108, 108, 108)
_ATK_READY   = (0,  220,   0)
_ATK_WAIT    = (220, 92,   16)
_LVUP_COL    = (252, 188,   0)     # level-up flash


# ── Heart drawing ─────────────────────────────────────────────────────────────

def _draw_heart(surface: pygame.Surface, x: int, y: int,
                state: str):   # 'full' | 'half' | 'empty'
    """Draw a 12×10 pixel-art heart at pixel position (x, y)."""
    if state == 'full':
        c1, c2 = _HEART_FULL,  _HEART_HI
    elif state == 'half':
        c1, c2 = _HEART_HALF,  _HEART_HALF_HI
    else:
        c1, c2 = _HEART_EMPTY, _HEART_EMPTY

    # Two lobes + a downward pointing wedge
    pygame.draw.circle(surface, c1, (x + 3,  y + 3), 3)
    pygame.draw.circle(surface, c1, (x + 9,  y + 3), 3)
    pts = [(x,      y + 4), (x + 12, y + 4), (x + 6,  y + 11)]
    pygame.draw.polygon(surface, c1, pts)

    # Inner highlight (skipped for empty hearts)
    if state != 'empty':
        pygame.draw.circle(surface, c2, (x + 3,  y + 3), 2)
        pygame.draw.circle(surface, c2, (x + 9,  y + 3), 2)
        pygame.draw.polygon(surface, c2,
                            [(x + 1, y + 5), (x + 11, y + 5), (x + 6, y + 10)])


def _draw_rupee(surface: pygame.Surface, x: int, y: int):
    """Draw a diamond-shaped coin at (x, y). 8×12 px."""
    pts = [(x + 4, y),       (x + 8, y + 5),
           (x + 4, y + 12),  (x,     y + 5)]
    pygame.draw.polygon(surface, _RUPEE,    pts)
    pygame.draw.polygon(surface, _RUPEE_HI, pts, 1)
    # Highlight pip
    surface.set_at((x + 3, y + 4), _RUPEE_HI)
    surface.set_at((x + 4, y + 3), _RUPEE_HI)


class HUD:
    def __init__(self):
        self._font_lg = pygame.font.SysFont("monospace", 20, bold=True)
        self._font_md = pygame.font.SysFont("monospace", 14, bold=True)
        self._font_sm = pygame.font.SysFont("monospace", 12)
        self._lvup_timer  = 0.0
        self._shop_timer  = 0.0   # "near merchant" hint pulse

    def notify_level_up(self):
        self._lvup_timer = 2.8

    def update(self, dt: float):
        self._lvup_timer = max(0.0, self._lvup_timer - dt)
        self._shop_timer = max(0.0, self._shop_timer - dt)

    def draw(self, surface: pygame.Surface, player, dungeon_level: int):
        hud_y = SCREEN_HEIGHT - HUD_HEIGHT

        # ── Background & top border ──────────────────────────────────────────
        pygame.draw.rect(surface, _BG, (0, hud_y, SCREEN_WIDTH, HUD_HEIGHT))
        pygame.draw.line(surface, _BORDER, (0, hud_y), (SCREEN_WIDTH, hud_y), 2)

        pad  = 12
        cy   = hud_y + HUD_HEIGHT // 2   # vertical centre of HUD

        # ── HEARTS (left column) ─────────────────────────────────────────────
        hp_per_heart   = 10
        total_hearts   = max(10, math.ceil(player.max_hp_total / hp_per_heart))
        filled_hearts  = int(player.hp // hp_per_heart)
        has_half       = int(player.hp) % hp_per_heart >= 5
        hearts_per_row = 10
        heart_w, heart_h = 14, 12   # spacing between hearts

        for i in range(total_hearts):
            row = i // hearts_per_row
            col = i  % hearts_per_row
            hx  = pad + col * heart_w
            hy  = hud_y + 6 + row * (heart_h + 2)
            if i < filled_hearts:
                state = 'full'
            elif i == filled_hearts and has_half:
                state = 'half'
            else:
                state = 'empty'
            _draw_heart(surface, hx, hy, state)

        # ── MAGIC BAR (below hearts if only 1 heart row, else inline) ────────
        bar_x  = pad
        bar_y  = hud_y + 6 + ((total_hearts - 1) // hearts_per_row + 1) * (heart_h + 2)
        bar_w  = hearts_per_row * heart_w
        bar_h  = 6
        if bar_y + bar_h < SCREEN_HEIGHT - 4:
            label = self._font_sm.render("MP", True, _TEXT_DIM)
            surface.blit(label, (bar_x, bar_y - 1))
            bx = bar_x + 18
            pygame.draw.rect(surface, _MAGIC_BG, (bx, bar_y, bar_w - 18, bar_h))
            fill_w = int((bar_w - 18) * max(0, player.mana) / player.max_mana_total) if player.max_mana_total else 0
            if fill_w > 0:
                pygame.draw.rect(surface, _MAGIC_FILL, (bx, bar_y, fill_w, bar_h))
            pygame.draw.rect(surface, _BORDER, (bx, bar_y, bar_w - 18, bar_h), 1)

        # ── STATS (centre column) ─────────────────────────────────────────────
        sx = SCREEN_WIDTH // 2 - 160

        # Level
        lv_txt = self._font_lg.render(f"LV {player.level}", True, YELLOW)
        surface.blit(lv_txt, (sx, hud_y + 5))

        # ATK / DEF
        atk_col = _ATK_READY if player.attack_ready >= 1.0 else _ATK_WAIT
        atk_txt = self._font_md.render(f"ATK {player.attack}", True, atk_col)
        def_txt = self._font_md.render(f"DEF {player.defense}", True, LIGHT_GRAY)
        surface.blit(atk_txt, (sx, hud_y + 28))
        surface.blit(def_txt, (sx + 80, hud_y + 28))

        # Potions
        pot_col = (252, 80, 80) if player.potions else _TEXT_DIM
        pot_txt = self._font_md.render(f"POT {len(player.potions)}", True, pot_col)
        surface.blit(pot_txt, (sx, hud_y + 46))

        # ── RUPEE + GOLD (right of centre) ────────────────────────────────────
        rx = sx + 200
        _draw_rupee(surface, rx, hud_y + 8)
        gold_txt = self._font_md.render(f" x {player.gold}", True, _TEXT_BRIGHT)
        surface.blit(gold_txt, (rx + 10, hud_y + 10))

        # ── FLOOR INDICATOR (right column) ────────────────────────────────────
        fx = SCREEN_WIDTH - 190
        fl_txt = self._font_lg.render(
            f"B{dungeon_level}/{MAX_DUNGEON_LEVELS}", True, LIGHT_GRAY)
        surface.blit(fl_txt, (fx, hud_y + 5))

        # ATK cooldown bar (thin, below floor)
        rdy   = player.attack_ready
        cd_w  = 150
        pygame.draw.rect(surface, (32, 32, 32), (fx, hud_y + 30, cd_w, 7))
        fill  = int(cd_w * rdy)
        if fill > 0:
            col = _ATK_READY if rdy >= 1.0 else _ATK_WAIT
            pygame.draw.rect(surface, col, (fx, hud_y + 30, fill, 7))
        pygame.draw.rect(surface, _BORDER, (fx, hud_y + 30, cd_w, 7), 1)
        lbl = "READY" if rdy >= 1.0 else "ATK"
        cd_lbl = self._font_sm.render(lbl, True, _TEXT_DIM)
        surface.blit(cd_lbl, (fx + cd_w + 4, hud_y + 29))

        # Controls hint — colour Z key by mana availability
        can_fire    = player.mana >= FIREBALL_MANA_COST
        z_col       = (80, 200, 80) if can_fire else (180, 50, 50)
        prefix      = self._font_sm.render("WASD Move  Spc Atk  ", True, _TEXT_DIM)
        z_lbl       = self._font_sm.render("Z", True, z_col)
        suffix      = self._font_sm.render(
            " Fireball  E Stairs  Q Pot  I Inv", True, _TEXT_DIM)
        hx0 = fx - 60
        hy0 = hud_y + 46
        surface.blit(prefix, (hx0, hy0))
        surface.blit(z_lbl,  (hx0 + prefix.get_width(), hy0))
        surface.blit(suffix, (hx0 + prefix.get_width() + z_lbl.get_width(), hy0))

        # ── Status effect icons with remaining time ───────────────────────────
        _STATUS_DEFS = [
            ('poison', (30, 200, 30),  "PSN"),
            ('burn',   (252, 120, 20), "BRN"),
            ('slow',   (60, 120, 220), "SLW"),
        ]
        icon_x = sx + 148
        for sname, scol, slabel in _STATUS_DEFS:
            if player.has_status(sname):
                s_data = player._status[sname]
                t_left = s_data['timer']
                stxt   = self._font_sm.render(
                    f"[{slabel} {t_left:.1f}s]", True, scol)
                # Subtle background pill
                bg_s = pygame.Surface((stxt.get_width() + 6, stxt.get_height() + 2),
                                      pygame.SRCALPHA)
                bg_s.fill((*scol, 30))
                surface.blit(bg_s, (icon_x - 3, hud_y + 45))
                surface.blit(stxt, (icon_x, hud_y + 46))
                icon_x += stxt.get_width() + 8

        # ── LEVEL-UP FLASH ────────────────────────────────────────────────────
        if self._lvup_timer > 0:
            alpha  = min(255, int(self._lvup_timer * 130))
            msg    = self._font_lg.render(
                f"LEVEL UP!  NOW LEVEL {player.level}", True, _LVUP_COL)
            msg.set_alpha(alpha)
            surface.blit(msg, msg.get_rect(
                center=(SCREEN_WIDTH // 2,
                        (SCREEN_HEIGHT - HUD_HEIGHT) // 2 - 60)))

        # ── STAT POINTS AVAILABLE indicator ───────────────────────────────────
        if player.stat_points > 0:
            blink = int(pygame.time.get_ticks() / 500) % 2 == 0
            if blink:
                pts_col = (80, 255, 120)
                sp_msg  = self._font_md.render(
                    f"★ {player.stat_points} STAT POINT{'S' if player.stat_points != 1 else ''}  [C]",
                    True, pts_col)
                surface.blit(sp_msg, sp_msg.get_rect(
                    center=(SCREEN_WIDTH // 2,
                            (SCREEN_HEIGHT - HUD_HEIGHT) // 2 - 38)))
