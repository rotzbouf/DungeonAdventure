"""
Town — the player's central hub between dungeon runs.

A single fixed-layout screen (no scrolling).  Four specialist merchants
occupy the four corners; a dungeon-entrance archway sits at the top-centre.
Entering town fully restores the player's HP and mana.
"""
from __future__ import annotations

import math
import random
import pygame
from src.settings import SCREEN_WIDTH, SCREEN_HEIGHT, HUD_HEIGHT, TILE_SIZE
from src.locale import t

TOWN_W = SCREEN_WIDTH
TOWN_H = SCREEN_HEIGHT - HUD_HEIGHT

# ── Key positions (pixel coords) ──────────────────────────────────────────────

PLAYER_SPAWN = (TOWN_W // 2, TOWN_H // 2 + 55)

# Top-centre archway leading to the dungeon
DUNGEON_ENTRANCE_POS = (TOWN_W // 2, 82)
DUNGEON_INTERACT_R   = TILE_SIZE * 2.8   # px, enter-dungeon prompt radius

# Player-owned house — right-side mid, symmetric with Craftsman
HOUSE_POS      = (TOWN_W * 3 // 4, TOWN_H // 2)
HOUSE_INTERACT_R = TILE_SIZE * 2.8

# (display_title, specialty_key, px, py)
MERCHANT_SPECS: list[tuple[str, str, int, int]] = [
    ("Blacksmith",  "weapons",  TOWN_W * 5 // 32,  TOWN_H * 5 // 16),
    ("Armourer",    "armor",    TOWN_W * 27 // 32, TOWN_H * 5 // 16),
    ("Jeweler",     "jewelry",  TOWN_W * 5 // 32,  TOWN_H * 47 // 64),
    ("Alchemist",   "potions",  TOWN_W * 27 // 32, TOWN_H * 47 // 64),
    ("Enchanter",   "enchant",  TOWN_W // 2,        TOWN_H * 5 // 6),
    ("Craftsman",   "craft",    TOWN_W // 4,        TOWN_H // 2),
]

TOWN_INTERACT_R = TILE_SIZE * 3.0   # bigger interact radius than dungeon


# ── Stall colour palette per specialty ────────────────────────────────────────

_STALL: dict[str, dict] = {
    "weapons":  {"bg": (72,  24,  8),  "hi": (180,  70, 20), "awning": (160, 50, 10)},
    "armor":    {"bg": (16,  36, 68),  "hi": ( 80, 130, 210), "awning": (30, 70, 130)},
    "jewelry":  {"bg": (12,  64, 64),  "hi": ( 40, 200, 200), "awning": (20, 130, 130)},
    "potions":  {"bg": (20,  56, 20),  "hi": ( 60, 200,  60), "awning": (30, 120, 30)},
    "enchant":  {"bg": (36,   8, 72),  "hi": (160,  80, 255), "awning": (80, 20, 150)},
    "craft":    {"bg": (48,  28,   8), "hi": (200, 130,  40), "awning": (140, 80, 20)},
}


# ── TownBounds — constrains player movement to the playable area ───────────────

class TownBounds:
    """
    Drop-in substitute for Dungeon when updating the player in town.
    Reports non-walkable for the two-tile border strip so the player
    cannot walk into the walls.
    """
    _MARGIN = 1   # tiles from each edge that are off-limits

    def is_walkable(self, tx: int, ty: int) -> bool:
        max_x = TOWN_W  // TILE_SIZE - 1
        max_y = TOWN_H  // TILE_SIZE - 1
        m = self._MARGIN
        return m <= tx <= max_x - m and m <= ty <= max_y - m


TOWN_BOUNDS = TownBounds()


# ── Colour palette ─────────────────────────────────────────────────────────────

# Stone
_ST_DARK  = (52, 46, 38)
_ST_MID   = (76, 68, 58)
_ST_LGT   = (104, 94, 82)
_ST_HI    = (136, 124, 108)
_MORTAR   = (32, 28, 22)
# Ground/earth
_GR_DARK  = (32, 24, 16)
_GR_MID   = (46, 36, 24)
_GR_LGT   = (62, 50, 36)
# Path (lighter stone slabs)
_PA_DARK  = (68, 60, 50)
_PA_MID   = (88, 80, 68)
_PA_LGT   = (112, 102, 88)
_PA_MORT  = (48, 42, 34)
# Wood/timber
_WD_DARK  = (46, 30, 12)
_WD_MID   = (72, 50, 20)
_WD_LGT   = (106, 76, 34)
# Plaster (between timbers)
_PL_BASE  = (168, 152, 120)
_PL_SHD   = (140, 126, 98)
# Roof tiles
_RF_DARK  = (64, 32, 16)
_RF_MID   = (92, 48, 22)
_RF_LGT   = (120, 64, 30)
# Foliage
_LF_DARK  = (24, 48, 12)
_LF_MID   = (36, 68, 18)
_LF_LGT   = (52, 90, 26)
# Water
_WA_DARK  = (12, 24, 48)
_WA_MID   = (16, 36, 68)
# Iron/metal
_IR_DARK  = (28, 28, 30)
_IR_MID   = (52, 52, 56)
_IR_LGT   = (82, 82, 88)


# ── Drawing helpers ────────────────────────────────────────────────────────────

def _grad_rect(surf, r, top_col, bot_col):
    """Fill a rect with a vertical linear gradient."""
    for i in range(r.height):
        t_ = i / max(1, r.height - 1)
        c = tuple(int(a + (b - a) * t_) for a, b in zip(top_col, bot_col))
        pygame.draw.line(surf, c, (r.left, r.top + i), (r.right, r.top + i))


def _blit_shadowed(surf, text_surf, pos, shadow_off=(2, 2)):
    """Blit a text surface with a darkened drop shadow."""
    sh = text_surf.copy()
    sh.fill((0, 0, 0, 160), special_flags=pygame.BLEND_RGBA_MULT)
    surf.blit(sh, (pos[0] + shadow_off[0], pos[1] + shadow_off[1]))
    surf.blit(text_surf, pos)


def _draw_stone_blocks(surf, rect, block_w, block_h, seed=0):
    """Tile a rect with offset stone blocks in multiple shades."""
    rng = random.Random(seed)
    shades = [_ST_DARK, _ST_MID, _ST_LGT, _ST_HI]
    for row in range(rect.top, rect.bottom, block_h):
        offset = (block_w // 2) if ((row - rect.top) // block_h) % 2 == 0 else 0
        for col in range(rect.left - block_w, rect.right + block_w, block_w):
            bx = col + offset
            x1 = max(rect.left, bx + 1)
            x2 = min(rect.right, bx + block_w - 1)
            y1 = max(rect.top, row + 1)
            y2 = min(rect.bottom, row + block_h - 1)
            if x2 <= x1 or y2 <= y1:
                continue
            shade = shades[rng.randint(0, 3)]
            pygame.draw.rect(surf, shade, (x1, y1, x2 - x1, y2 - y1))
            pygame.draw.line(surf, _ST_HI, (x1, y1), (x2 - 1, y1))
            pygame.draw.line(surf, _ST_HI, (x1, y1), (x1, y2 - 1))
            pygame.draw.line(surf, _MORTAR, (x1, y2 - 1), (x2 - 1, y2 - 1))
            pygame.draw.line(surf, _MORTAR, (x2 - 1, y1), (x2 - 1, y2 - 1))


def _draw_building(surf, px, py, pal, seed=0):
    """Draw a full merchant building facade centered at (px, py)."""
    BW, BH = 200, 140   # building width, height
    bx = px - BW // 2
    by = py - BH // 2 - 20   # shifted up so merchant stands in front

    # ── Drop shadow ──────────────────────────────────────────────────────────
    sh_surf = pygame.Surface((BW + 12, BH + 16), pygame.SRCALPHA)
    sh_surf.fill((0, 0, 0, 80))
    surf.blit(sh_surf, (bx + 6, by + 6))

    # ── Stone base (lower 40px) ───────────────────────────────────────────────
    base_r = pygame.Rect(bx, by + BH - 40, BW, 40)
    _draw_stone_blocks(surf, base_r, 28, 14, seed=seed)
    pygame.draw.rect(surf, _MORTAR, base_r, 1)

    # ── Timber-frame plaster wall (upper portion) ─────────────────────────────
    wall_r = pygame.Rect(bx, by, BW, BH - 40)
    pygame.draw.rect(surf, _PL_BASE, wall_r)
    # plaster shading — subtle gradient
    _grad_rect(surf, wall_r, _PL_SHD, _PL_BASE)
    # vertical timber beams
    for beam_x in range(bx, bx + BW + 1, BW // 3):
        pygame.draw.rect(surf, _WD_DARK, (beam_x - 3, by, 6, BH - 40))
        pygame.draw.line(surf, _WD_MID, (beam_x - 2, by), (beam_x - 2, by + BH - 40))
    # horizontal timber beams
    for beam_y in [by, by + (BH - 40) // 2, by + BH - 40]:
        pygame.draw.rect(surf, _WD_DARK, (bx, beam_y - 3, BW, 6))
        pygame.draw.line(surf, _WD_MID, (bx, beam_y - 2), (bx + BW, beam_y - 2))
    # diagonal brace timbers (X pattern in each panel)
    panel_w = BW // 3
    for pi in range(3):
        px1 = bx + pi * panel_w
        py1 = by
        py2 = by + (BH - 40)
        pygame.draw.line(surf, _WD_DARK, (px1 + 4, py1 + 4), (px1 + panel_w - 4, py2 - 4), 2)
        pygame.draw.line(surf, _WD_DARK, (px1 + panel_w - 4, py1 + 4), (px1 + 4, py2 - 4), 2)

    # ── Pitched roof ─────────────────────────────────────────────────────────
    roof_pts = [
        (bx - 8,      by),
        (bx + BW + 8, by),
        (bx + BW + 14, by - 10),
        (bx + BW // 2, by - 48),
        (bx - 14,     by - 10),
    ]
    pygame.draw.polygon(surf, _RF_MID, roof_pts)
    pygame.draw.polygon(surf, _RF_DARK, roof_pts, 3)
    # roof ridge highlight
    pygame.draw.line(surf, _RF_LGT,
                     (bx - 14, by - 10), (bx + BW // 2, by - 48))
    pygame.draw.line(surf, _RF_LGT,
                     (bx + BW // 2, by - 48), (bx + BW + 14, by - 10))
    # roof tiles (horizontal lines)
    for ry in range(by - 8, by, 4):
        t_ = (by - ry) / 48.0
        tile_w = int((BW + 28) * (1.0 - t_ * 0.5))
        pygame.draw.line(surf, _RF_DARK,
                         (bx + BW // 2 - tile_w // 2, ry),
                         (bx + BW // 2 + tile_w // 2, ry))

    # ── Shop awning / counter ─────────────────────────────────────────────────
    aw_col  = pal["awning"]
    aw_hi   = pal["hi"]
    aw_r    = pygame.Rect(bx - 14, by + BH - 44, BW + 28, 18)
    pygame.draw.rect(surf, aw_col, aw_r)
    # awning stripes
    stripe_col = tuple(min(255, c + 30) for c in aw_col)
    for sx_ in range(aw_r.left + 6, aw_r.right, 16):
        pygame.draw.line(surf, stripe_col,
                         (sx_, aw_r.top), (sx_ - 8, aw_r.bottom), 2)
    pygame.draw.rect(surf, aw_hi, aw_r, 2)
    # awning scalloped bottom edge
    for sx_ in range(aw_r.left, aw_r.right - 10, 14):
        pygame.draw.arc(surf, aw_hi,
                        pygame.Rect(sx_, aw_r.bottom - 4, 14, 10),
                        0, math.pi, 2)

    # ── Hanging sign board ────────────────────────────────────────────────────
    post_x = bx + BW // 2
    post_y = by - 14
    pygame.draw.line(surf, _WD_DARK, (post_x, post_y), (post_x, post_y - 22), 3)
    sign_r = pygame.Rect(post_x - 36, post_y - 42, 72, 20)
    pygame.draw.rect(surf, _WD_MID, sign_r)
    pygame.draw.rect(surf, _WD_DARK, sign_r, 2)
    pygame.draw.line(surf, _WD_LGT, (sign_r.left, sign_r.top), (sign_r.right, sign_r.top))
    # thin rope lines from sign to beam
    pygame.draw.line(surf, _WD_DARK,
                     (sign_r.left + 6, sign_r.top), (post_x - 8, post_y - 22), 1)
    pygame.draw.line(surf, _WD_DARK,
                     (sign_r.right - 6, sign_r.top), (post_x + 8, post_y - 22), 1)

    # ── Outline ───────────────────────────────────────────────────────────────
    pygame.draw.rect(surf, _WD_DARK, (bx, by, BW, BH), 2)


def _draw_tree(surf, cx, cy, seed=0):
    """Draw a layered foliage tree with trunk and shadow."""
    rng = random.Random(seed)
    trunk_w = 14
    trunk_h = 38
    # shadow
    sh = pygame.Surface((60, 20), pygame.SRCALPHA)
    pygame.draw.ellipse(sh, (0, 0, 0, 60), (0, 0, 60, 20))
    surf.blit(sh, (cx - 30, cy + trunk_h // 2 - 6))
    # trunk
    _grad_rect(surf, pygame.Rect(cx - trunk_w // 2, cy - trunk_h // 2,
                                 trunk_w, trunk_h), _WD_DARK, _WD_MID)
    pygame.draw.line(surf, _WD_LGT,
                     (cx - trunk_w // 2 + 2, cy - trunk_h // 2),
                     (cx - trunk_w // 2 + 2, cy + trunk_h // 2))
    # foliage — 3 overlapping circles
    for r_, col, dy_ in [
        (36, _LF_DARK, 0),
        (30, _LF_MID,  -8 + rng.randint(-4, 4)),
        (22, _LF_LGT,  -18 + rng.randint(-4, 4)),
    ]:
        foliage_s = pygame.Surface((r_ * 2, r_ * 2), pygame.SRCALPHA)
        pygame.draw.circle(foliage_s, (*col, 230), (r_, r_), r_)
        # highlight
        pygame.draw.circle(foliage_s, (min(255, col[0]+12),
                                       min(255, col[1]+20),
                                       min(255, col[2]+8), 100),
                           (r_ - 4, r_ - 6), r_ // 3)
        surf.blit(foliage_s, (cx - r_, cy - trunk_h // 2 + dy_ - r_))


def _draw_barrel(surf, bx, by):
    """Draw a decorative barrel."""
    bw, bh = 22, 30
    _grad_rect(surf, pygame.Rect(bx, by, bw, bh), _WD_MID, _WD_DARK)
    # top ellipse (curved top)
    pygame.draw.ellipse(surf, _WD_LGT, (bx, by - 5, bw, 10))
    pygame.draw.ellipse(surf, _WD_MID, (bx, by - 4, bw, 8))
    # iron hoops
    for hy in [by + bh // 4, by + bh * 3 // 4]:
        pygame.draw.rect(surf, _IR_MID, (bx - 1, hy - 2, bw + 2, 4))
        pygame.draw.line(surf, _IR_LGT, (bx, hy - 2), (bx + bw, hy - 2))
    pygame.draw.rect(surf, _WD_DARK, (bx, by, bw, bh), 1)


def _draw_crate(surf, bx, by):
    """Draw a decorative wooden crate."""
    cw, ch = 28, 26
    _grad_rect(surf, pygame.Rect(bx, by, cw, ch), _WD_LGT, _WD_MID)
    # cross-hatch planks
    pygame.draw.line(surf, _WD_DARK, (bx, by), (bx + cw, by + ch), 1)
    pygame.draw.line(surf, _WD_DARK, (bx + cw, by), (bx, by + ch), 1)
    pygame.draw.rect(surf, _WD_DARK, (bx, by + ch // 2 - 1, cw, 2))
    pygame.draw.rect(surf, _WD_DARK, (bx + cw // 2 - 1, by, 2, ch))
    pygame.draw.rect(surf, _WD_DARK, (bx, by, cw, ch), 2)
    pygame.draw.line(surf, _WD_LGT, (bx + 1, by + 1), (bx + cw - 1, by + 1))


def _draw_fountain(surf, cx, cy):
    """Draw a multi-layered stone fountain with iron fence posts."""
    # outer stone ring — multiple passes for depth
    for rad, col, thick in [
        (56, _ST_DARK, 0),   # filled base disc
        (52, _ST_MID,  14),
        (52, _ST_LGT,  3),
        (52, _ST_HI,   1),
    ]:
        if thick == 0:
            pygame.draw.circle(surf, col, (cx, cy), rad)
        else:
            pygame.draw.circle(surf, col, (cx, cy), rad, thick)
    # inner stone rim
    pygame.draw.circle(surf, _ST_MID, (cx, cy), 38, 10)
    pygame.draw.circle(surf, _ST_HI,  (cx, cy), 38, 1)
    # water pool
    water_s = pygame.Surface((56, 56), pygame.SRCALPHA)
    pygame.draw.circle(water_s, (*_WA_MID, 220), (28, 28), 28)
    # ripple
    pygame.draw.circle(water_s, (*_WA_DARK, 140), (28, 28), 18, 2)
    pygame.draw.circle(water_s, (*_WA_DARK, 80),  (28, 28), 10, 1)
    surf.blit(water_s, (cx - 28, cy - 28))
    # central pillar
    pygame.draw.circle(surf, _ST_MID, (cx, cy), 8)
    pygame.draw.circle(surf, _ST_HI,  (cx, cy), 8, 1)
    # iron fence posts (8 posts at radius 68)
    for i in range(8):
        ang = i * math.pi * 2 / 8
        fx = int(cx + math.cos(ang) * 68)
        fy = int(cy + math.sin(ang) * 68)
        # post
        pygame.draw.rect(surf, _IR_DARK, (fx - 3, fy - 12, 6, 24))
        pygame.draw.rect(surf, _IR_MID,  (fx - 2, fy - 11, 4, 22))
        pygame.draw.line(surf, _IR_LGT,  (fx - 1, fy - 10), (fx - 1, fy + 10))
        # spear tip
        pts = [(fx, fy - 16), (fx - 3, fy - 12), (fx + 3, fy - 12)]
        pygame.draw.polygon(surf, _IR_MID, pts)
        pygame.draw.polygon(surf, _IR_LGT, pts, 1)
    # iron fence rails connecting posts
    for i in range(8):
        ang1 = i * math.pi * 2 / 8
        ang2 = (i + 1) * math.pi * 2 / 8
        x1 = int(cx + math.cos(ang1) * 68)
        y1 = int(cy + math.sin(ang1) * 68)
        x2 = int(cx + math.cos(ang2) * 68)
        y2 = int(cy + math.sin(ang2) * 68)
        pygame.draw.line(surf, _IR_MID, (x1, y1 - 6), (x2, y2 - 6), 2)
        pygame.draw.line(surf, _IR_MID, (x1, y1 + 4), (x2, y2 + 4), 1)


def _draw_dungeon_gate(surf, ex, ey):
    """Draw a tall stone gate with portcullis at the dungeon entrance."""
    col_w, col_h = 30, 108
    gate_w = 80   # inner opening width
    arch_h = 56   # height of pointed arch above opening

    # columns
    for cx_, cy_ in [(ex - gate_w // 2 - col_w, ey - col_h // 2),
                     (ex + gate_w // 2,          ey - col_h // 2)]:
        col_r = pygame.Rect(cx_, cy_, col_w, col_h)
        _draw_stone_blocks(surf, col_r, 16, 12, seed=hash((cx_, cy_)))
        pygame.draw.rect(surf, _MORTAR, col_r, 2)
        # column cap
        cap_r = pygame.Rect(cx_ - 4, cy_ - 8, col_w + 8, 10)
        pygame.draw.rect(surf, _ST_HI, cap_r)
        pygame.draw.rect(surf, _MORTAR, cap_r, 1)
        # torch bracket
        torch_x = cx_ + col_w // 2
        torch_y = cy_ + col_h // 3
        pygame.draw.rect(surf, _IR_DARK, (torch_x - 2, torch_y - 12, 4, 14))
        pygame.draw.rect(surf, _IR_MID,  (torch_x - 4, torch_y - 4, 8, 6))

    # pointed arch stone lintel
    arch_top_y = ey - col_h // 2 - arch_h
    arch_pts = [
        (ex - gate_w // 2 - col_w, ey - col_h // 2),
        (ex - gate_w // 2 - col_w, ey - col_h // 2 + 10),
        (ex - gate_w // 2,         ey - col_h // 2 + 10),
        (ex - gate_w // 2,         ey - col_h // 2 - 20),
        (ex,                        arch_top_y),
        (ex + gate_w // 2,         ey - col_h // 2 - 20),
        (ex + gate_w // 2,         ey - col_h // 2 + 10),
        (ex + gate_w // 2 + col_w, ey - col_h // 2 + 10),
        (ex + gate_w // 2 + col_w, ey - col_h // 2),
    ]
    pygame.draw.polygon(surf, _ST_MID, arch_pts)
    pygame.draw.polygon(surf, _ST_HI,  arch_pts, 2)
    # keystone
    ks_r = pygame.Rect(ex - 10, arch_top_y - 8, 20, 14)
    pygame.draw.rect(surf, _ST_HI, ks_r)
    pygame.draw.rect(surf, _MORTAR, ks_r, 1)

    # inner void (dark passage)
    void_r = pygame.Rect(ex - gate_w // 2, ey - col_h // 2,
                         gate_w, col_h // 2 + 20)
    pygame.draw.rect(surf, (14, 8, 24), void_r)
    # pointed arch void cutout
    void_arch_pts = [
        (ex - gate_w // 2, ey - col_h // 2),
        (ex - gate_w // 2, ey - col_h // 2 - 18),
        (ex,               ey - col_h // 2 - arch_h + 16),
        (ex + gate_w // 2, ey - col_h // 2 - 18),
        (ex + gate_w // 2, ey - col_h // 2),
    ]
    pygame.draw.polygon(surf, (14, 8, 24), void_arch_pts)

    # iron portcullis bars (vertical)
    bar_top    = ey - col_h // 2 - 14
    bar_bottom = ey - col_h // 2 + 18
    for bx_ in range(ex - gate_w // 2 + 6, ex + gate_w // 2 - 4, 12):
        pygame.draw.line(surf, _IR_DARK,  (bx_, bar_top), (bx_, bar_bottom), 3)
        pygame.draw.line(surf, _IR_MID,   (bx_, bar_top), (bx_, bar_bottom), 1)
        # pointed bar tips
        pts = [(bx_, bar_bottom + 6), (bx_ - 3, bar_bottom), (bx_ + 3, bar_bottom)]
        pygame.draw.polygon(surf, _IR_MID, pts)
    # horizontal bars
    for hy_ in [bar_top + 8, bar_top + (bar_bottom - bar_top) // 2]:
        pygame.draw.line(surf, _IR_DARK,
                         (ex - gate_w // 2 + 6, hy_),
                         (ex + gate_w // 2 - 6, hy_), 3)
        pygame.draw.line(surf, _IR_MID,
                         (ex - gate_w // 2 + 6, hy_),
                         (ex + gate_w // 2 - 6, hy_), 1)


def _draw_tower(surf, cx, cy, radius, n_sides=10):
    """Draw a stone tower centered at (cx,cy), clipped naturally at screen edges."""
    # Fill layers: dark → mid → light for a rounded 3D look
    for shrink, col in [(0, _ST_DARK), (5, _ST_MID), (12, _ST_LGT), (18, _ST_HI)]:
        r = radius - shrink
        pts = []
        for i in range(n_sides):
            ang = i * 2 * math.pi / n_sides - math.pi / n_sides
            pts.append((int(cx + math.cos(ang) * r), int(cy + math.sin(ang) * r)))
        if shrink < 18:
            pygame.draw.polygon(surf, col, pts)
        else:
            pygame.draw.polygon(surf, col, pts, 2)

    # Battlements around tower perimeter
    for i in range(n_sides * 2):
        ang = i * math.pi / n_sides
        if i % 2 == 0:
            inner_r = radius - 2
            outer_r = radius + 10
            ang_w   = math.pi / (n_sides * 1.8)
            pts = [
                (int(cx + math.cos(ang - ang_w) * inner_r),
                 int(cy + math.sin(ang - ang_w) * inner_r)),
                (int(cx + math.cos(ang + ang_w) * inner_r),
                 int(cy + math.sin(ang + ang_w) * inner_r)),
                (int(cx + math.cos(ang + ang_w) * outer_r),
                 int(cy + math.sin(ang + ang_w) * outer_r)),
                (int(cx + math.cos(ang - ang_w) * outer_r),
                 int(cy + math.sin(ang - ang_w) * outer_r)),
            ]
            pygame.draw.polygon(surf, _ST_MID, pts)
            pygame.draw.polygon(surf, _ST_HI,  pts, 1)

    # Stone texture ring
    pygame.draw.circle(surf, _MORTAR, (cx, cy), radius, 2)


def _draw_house(surf, px, py):
    """Draw the player's cozy timber-frame cottage — door, windows, chimney, fence."""
    BW, BH = 180, 128
    bx = px - BW // 2
    by = py - BH // 2 - 15   # shift up so player stands in front

    # ── Drop shadow ───────────────────────────────────────────────────────────
    sh = pygame.Surface((BW + 16, BH + 20), pygame.SRCALPHA)
    sh.fill((0, 0, 0, 90))
    surf.blit(sh, (bx + 7, by + 7))

    # ── Stone base (lower 32px) ───────────────────────────────────────────────
    base_r = pygame.Rect(bx, by + BH - 32, BW, 32)
    _draw_stone_blocks(surf, base_r, 24, 12, seed=9001)
    pygame.draw.rect(surf, _MORTAR, base_r, 1)

    # ── Warm plaster wall (upper portion) ─────────────────────────────────────
    _PL_WARM     = (172, 156, 124)
    _PL_WARM_SHD = (148, 132, 104)
    wall_r = pygame.Rect(bx, by, BW, BH - 32)
    pygame.draw.rect(surf, _PL_WARM, wall_r)
    _grad_rect(surf, wall_r, _PL_WARM_SHD, _PL_WARM)

    # Timber beams — thirds
    for beam_x in [bx, bx + BW // 3, bx + 2 * BW // 3, bx + BW]:
        pygame.draw.rect(surf, _WD_DARK, (beam_x - 3, by, 6, BH - 32))
        pygame.draw.line(surf, _WD_MID,
                         (beam_x - 2, by), (beam_x - 2, by + BH - 32))
    for beam_y in [by, by + (BH - 32) // 2, by + BH - 32]:
        pygame.draw.rect(surf, _WD_DARK, (bx, beam_y - 3, BW, 6))
        pygame.draw.line(surf, _WD_MID, (bx, beam_y - 2), (bx + BW, beam_y - 2))

    # ── Windows — left and right of door, upper half ─────────────────────────
    win_w = BW // 5
    win_h = (BH - 32) // 3
    win_y = by + 10
    for wx in [bx + 14, bx + BW - 14 - win_w]:
        # Warm interior glow
        glow_s = pygame.Surface((win_w, win_h), pygame.SRCALPHA)
        glow_s.fill((255, 200, 80, 130))
        surf.blit(glow_s, (wx, win_y))
        # Frame + cross panes
        pygame.draw.rect(surf, _WD_DARK, (wx, win_y, win_w, win_h), 3)
        pygame.draw.line(surf, _WD_DARK,
                         (wx + win_w // 2, win_y), (wx + win_w // 2, win_y + win_h), 2)
        pygame.draw.line(surf, _WD_DARK,
                         (wx, win_y + win_h // 2), (wx + win_w, win_y + win_h // 2), 2)

    # ── Front door (bottom-centre of plaster wall) ────────────────────────────
    door_w = 36
    door_h = 64
    door_x = px - door_w // 2
    door_y = by + (BH - 32) - door_h
    # Door body — warm wood gradient
    _grad_rect(surf, pygame.Rect(door_x, door_y, door_w, door_h),
               (60, 36, 12), (44, 26, 8))
    # Arched top
    pygame.draw.ellipse(surf, (52, 30, 10), (door_x, door_y - 8, door_w, 20))
    pygame.draw.ellipse(surf, _WD_DARK,    (door_x, door_y - 8, door_w, 20), 2)
    # Vertical centre divide
    pygame.draw.line(surf, _WD_DARK, (px, door_y), (px, door_y + door_h), 1)
    # Four recessed panels
    panel_w = door_w // 2 - 6
    for pdx in [door_x + 4, door_x + door_w // 2 + 2]:
        for pdy in [door_y + 4, door_y + 34]:
            pygame.draw.rect(surf, (48, 28, 8), (pdx, pdy, panel_w, 26))
    # Brass knob
    pygame.draw.circle(surf, (190, 150, 30),
                       (door_x + door_w - 6, door_y + door_h // 2), 3)
    # Iron hinges
    for hy_ in [door_y + 10, door_y + door_h - 14]:
        pygame.draw.rect(surf, _IR_MID, (door_x + 2, hy_ - 3, 8, 5))
    pygame.draw.rect(surf, _WD_DARK, (door_x, door_y, door_w, door_h), 2)

    # ── Door-side torch brackets ──────────────────────────────────────────────
    for tx_ in [door_x - 14, door_x + door_w + 8]:
        pygame.draw.rect(surf, _IR_DARK, (tx_ - 2, door_y - 14, 4, 14))
        pygame.draw.rect(surf, _IR_MID,  (tx_ - 4, door_y - 6, 8, 6))
        pygame.draw.rect(surf, _WD_DARK, (tx_ - 2, door_y - 4, 4, 8))

    # ── Chimney (drawn BEFORE roof so roof polygon overlaps its base) ─────────
    ch_w = 20
    ch_x = bx + int(BW * 0.70) - ch_w // 2
    ch_top = by - 58
    ch_h   = 50
    ch_r   = pygame.Rect(ch_x, ch_top, ch_w, ch_h)
    _draw_stone_blocks(surf, ch_r, 10, 8, seed=5678)
    pygame.draw.rect(surf, _MORTAR, ch_r, 1)

    # ── Pitched roof (covers lower chimney) ───────────────────────────────────
    roof_pts = [
        (bx - 10,      by),
        (bx + BW + 10, by),
        (bx + BW + 14, by - 8),
        (bx + BW // 2, by - 44),
        (bx - 14,      by - 8),
    ]
    pygame.draw.polygon(surf, _RF_MID, roof_pts)
    pygame.draw.polygon(surf, _RF_DARK, roof_pts, 3)
    pygame.draw.line(surf, _RF_LGT, (bx - 14,      by - 8), (bx + BW // 2, by - 44))
    pygame.draw.line(surf, _RF_LGT, (bx + BW // 2, by - 44), (bx + BW + 14, by - 8))
    for ry in range(by - 6, by, 4):
        t_ = (by - ry) / 44.0
        tile_w = int((BW + 28) * (1.0 - t_ * 0.5))
        pygame.draw.line(surf, _RF_DARK,
                         (bx + BW // 2 - tile_w // 2, ry),
                         (bx + BW // 2 + tile_w // 2, ry))

    # ── Chimney cap on top of roof ────────────────────────────────────────────
    pygame.draw.rect(surf, _ST_HI, (ch_x - 3, ch_top - 4, ch_w + 6, 6))

    # ── Hanging sign board ────────────────────────────────────────────────────
    post_x = px
    post_y = by - 14
    pygame.draw.line(surf, _WD_DARK, (post_x, post_y), (post_x, post_y - 22), 3)
    sign_r = pygame.Rect(post_x - 36, post_y - 42, 72, 20)
    pygame.draw.rect(surf, _WD_MID, sign_r)
    pygame.draw.rect(surf, _WD_DARK, sign_r, 2)
    pygame.draw.line(surf, _WD_LGT, (sign_r.left, sign_r.top), (sign_r.right, sign_r.top))
    pygame.draw.line(surf, _WD_DARK,
                     (sign_r.left + 6, sign_r.top), (post_x - 8, post_y - 22), 1)
    pygame.draw.line(surf, _WD_DARK,
                     (sign_r.right - 6, sign_r.top), (post_x + 8, post_y - 22), 1)

    # ── Picket fence ──────────────────────────────────────────────────────────
    fence_y = by + BH + 6
    for fx in range(bx - 14, bx + BW + 18, 18):
        # Pointed picket
        pts = [(fx + 1, fence_y - 5), (fx - 2, fence_y), (fx + 4, fence_y)]
        pygame.draw.polygon(surf, _WD_LGT, pts)
        pygame.draw.rect(surf, _WD_MID, (fx - 2, fence_y, 5, 18))
        pygame.draw.line(surf, _WD_LGT, (fx - 1, fence_y), (fx - 1, fence_y + 15))
    pygame.draw.line(surf, _WD_DARK,
                     (bx - 14, fence_y + 8), (bx + BW + 14, fence_y + 8), 2)
    pygame.draw.line(surf, _WD_DARK,
                     (bx - 14, fence_y + 15), (bx + BW + 14, fence_y + 15), 1)

    # ── Building outline ──────────────────────────────────────────────────────
    pygame.draw.rect(surf, _WD_DARK, (bx, by, BW, BH), 2)


def _draw_outer_walls(surf):
    """Draw irregular stone outer walls: thin bands with large corner towers
    and mid-wall towers that break up every straight run."""
    B  = 38   # wall band thickness (thinner → more interior visible)
    CR = 84   # corner tower radius  (centred at screen corners, curves inward)
    MR = 52   # mid-wall tower radius

    # ── 1. Wall bands (thin rectangular stone sections) ───────────────────────
    for wr in [
        pygame.Rect(0,           0,           TOWN_W, B),
        pygame.Rect(0,           TOWN_H - B,  TOWN_W, B),
        pygame.Rect(0,           B,           B,      TOWN_H - B * 2),
        pygame.Rect(TOWN_W - B,  B,           B,      TOWN_H - B * 2),
    ]:
        _draw_stone_blocks(surf, wr, 20, 13, seed=hash(str(wr)))
        pygame.draw.rect(surf, _MORTAR, wr, 1)

    # Thin inner-edge highlight so the wall reads as raised
    pygame.draw.rect(surf, _ST_HI,  (B, B, TOWN_W - B * 2, TOWN_H - B * 2), 2)
    pygame.draw.rect(surf, _ST_MID, (B + 3, B + 3, TOWN_W - B * 2 - 6, TOWN_H - B * 2 - 6), 1)

    # ── 2. Battlements along wall outer edges ─────────────────────────────────
    mw, mh, cw = 20, 16, 12
    step = mw + cw
    # Top / bottom
    for mx in range(CR // 2, TOWN_W - CR // 2 - mw, step):
        for my_, flip in [(0, False), (TOWN_H - mh, True)]:
            mr = pygame.Rect(mx, my_, mw, mh)
            pygame.draw.rect(surf, _ST_MID, mr)
            pygame.draw.rect(surf, _ST_HI,  mr, 1)
    # Left / right
    for my in range(CR // 2, TOWN_H - CR // 2 - mw, step):
        for mx_ in [(0, mh), (TOWN_W - mh, mh)]:
            mr = pygame.Rect(mx_[0], my, mx_[1], mw)
            pygame.draw.rect(surf, _ST_MID, mr)
            pygame.draw.rect(surf, _ST_HI,  mr, 1)

    # ── 3. Corner towers — centred at screen corners, protrude inward ─────────
    for cx, cy in [(0, 0), (TOWN_W, 0), (0, TOWN_H), (TOWN_W, TOWN_H)]:
        _draw_tower(surf, cx, cy, CR, n_sides=12)

    # ── 4. Mid-wall towers — break up the long straight runs ──────────────────
    # Top wall: two towers flanking the gate
    ex = DUNGEON_ENTRANCE_POS[0]
    mid_towers = [
        (ex - 280, 0), (ex + 280, 0),            # top wall flanking gate
        (TOWN_W // 4, TOWN_H), (3 * TOWN_W // 4, TOWN_H),  # bottom wall
        (0, TOWN_H // 3),  (0, 2 * TOWN_H // 3), # left wall
        (TOWN_W, TOWN_H // 3), (TOWN_W, 2 * TOWN_H // 3),  # right wall
    ]
    for cx, cy in mid_towers:
        _draw_tower(surf, cx, cy, MR, n_sides=10)

    # ── 5. Gate gap in top wall ────────────────────────────────────────────────
    ex, ey = DUNGEON_ENTRANCE_POS
    gap = 94
    pygame.draw.rect(surf, _GR_DARK, (ex - gap // 2, 0, gap, B + 2))


def _draw_ground(surf):
    """Draw earth base, gravel scatter, and paved paths."""
    rng = random.Random(42)

    # ── Dark earth base ───────────────────────────────────────────────────────
    surf.fill(_GR_DARK)

    # ── Soil texture — subtle variation patches ───────────────────────────────
    for _ in range(340):
        px = rng.randint(0, TOWN_W - 1)
        py = rng.randint(0, TOWN_H - 1)
        r_ = rng.randint(12, 40)
        shade = rng.choice([_GR_MID, _GR_LGT, _GR_DARK])
        alpha = rng.randint(40, 90)
        patch = pygame.Surface((r_ * 2, r_ * 2), pygame.SRCALPHA)
        pygame.draw.ellipse(patch, (*shade, alpha), (0, 0, r_ * 2, r_ * 2))
        surf.blit(patch, (px - r_, py - r_))

    # ── Pebble/gravel scatter ─────────────────────────────────────────────────
    for _ in range(1800):
        px = rng.randint(0, TOWN_W - 1)
        py = rng.randint(0, TOWN_H - 1)
        shade = rng.choice([_GR_MID, _GR_LGT, (55, 45, 32), (40, 32, 20)])
        r_ = rng.randint(1, 3)
        pygame.draw.circle(surf, shade, (px, py), r_)

    # ── Stone paving slabs — main cross paths ─────────────────────────────────
    PATH_W  = 110   # width of main paths
    # vertical path: from gate to fountain area
    vpath_x = TOWN_W // 2
    vpath_r = pygame.Rect(vpath_x - PATH_W // 2, 62, PATH_W, TOWN_H - 62)
    # horizontal path 1 (upper third)
    hpath1_y = TOWN_H // 3
    hpath1_r = pygame.Rect(62, hpath1_y - PATH_W // 2, TOWN_W - 124, PATH_W)
    # horizontal path 2 (lower two-thirds)
    hpath2_y = TOWN_H * 2 // 3
    hpath2_r = pygame.Rect(62, hpath2_y - PATH_W // 2, TOWN_W - 124, PATH_W)

    for path_r in [vpath_r, hpath1_r, hpath2_r]:
        # grout background
        pygame.draw.rect(surf, _PA_MORT, path_r)
        # paving slabs
        SLAB_W, SLAB_H = 52, 36
        for row in range(path_r.top - SLAB_H, path_r.bottom + SLAB_H, SLAB_H):
            off = (SLAB_W // 2) if ((row - path_r.top) // SLAB_H) % 2 == 0 else 0
            for col in range(path_r.left - SLAB_W, path_r.right + SLAB_W, SLAB_W):
                sx = col + off
                x1 = max(path_r.left, sx + 2)
                x2 = min(path_r.right, sx + SLAB_W - 2)
                y1 = max(path_r.top, row + 2)
                y2 = min(path_r.bottom, row + SLAB_H - 2)
                if x2 <= x1 + 2 or y2 <= y1 + 2:
                    continue
                v = ((sx // SLAB_W + row // SLAB_H) * 17) % 18
                shade = (
                    _PA_DARK[0] + v, _PA_DARK[1] + v // 2, _PA_DARK[2] + v // 3
                )
                pygame.draw.rect(surf, shade, (x1, y1, x2 - x1, y2 - y1))
                pygame.draw.line(surf, _PA_LGT, (x1, y1), (x2, y1))
                pygame.draw.line(surf, _PA_LGT, (x1, y1), (x1, y2))
                pygame.draw.line(surf, _PA_MORT, (x1, y2 - 1), (x2, y2 - 1))
                pygame.draw.line(surf, _PA_MORT, (x2 - 1, y1), (x2 - 1, y2))


# ── TownRenderer — draws the static and dynamic town scene ────────────────────

class TownRenderer:
    """
    Renders the town background (cached) plus animated elements
    (dungeon entrance glow, merchant interaction hints).
    """

    def __init__(self):
        self._bg:   pygame.Surface | None = None
        self._font: pygame.font.Font | None = None
        self._font_sm: pygame.font.Font | None = None
        # Torch positions for animation (filled by _build_bg)
        self._torch_positions: list[tuple[int, int]] = []
        # Random phases so torches flicker independently
        self._torch_phases: list[float] = []

    # ── Init ──────────────────────────────────────────────────────────────────

    def _ensure_fonts(self):
        if self._font is None:
            self._font    = pygame.font.SysFont("monospace", 17, bold=True)
            self._font_sm = pygame.font.SysFont("monospace", 13)

    def _build_bg(self) -> pygame.Surface:
        """Build the static background surface — rich medieval town."""
        surf = pygame.Surface((TOWN_W, TOWN_H))

        # ── 1. Ground (must be first — everything paints on top) ──────────────
        _draw_ground(surf)

        # ── 2. Outer walls (on top of ground) ────────────────────────────────
        _draw_outer_walls(surf)

        # ── 3. Central fountain ───────────────────────────────────────────────
        fcx, fcy = TOWN_W // 2, TOWN_H // 2
        _draw_fountain(surf, fcx, fcy)

        # ── 4. Corner trees ───────────────────────────────────────────────────
        B = 38
        tree_positions = [
            (B + 88,          B + 88),
            (TOWN_W - B - 88, B + 88),
            (B + 88,          TOWN_H - B - 88),
            (TOWN_W - B - 88, TOWN_H - B - 88),
            # extra trees flanking mid-wall towers on left/right
            (B + 60,          TOWN_H // 3 + 80),
            (TOWN_W - B - 60, TOWN_H // 3 + 80),
            (B + 60,          2 * TOWN_H // 3 - 80),
            (TOWN_W - B - 60, 2 * TOWN_H // 3 - 80),
        ]
        for i, (tx, ty) in enumerate(tree_positions):
            _draw_tree(surf, tx, ty, seed=i * 37)

        # ── 5. Merchant buildings ─────────────────────────────────────────────
        for title, specialty, px, py in MERCHANT_SPECS:
            pal = _STALL[specialty]
            _draw_building(surf, px, py, pal, seed=hash(title))

        # ── 5b. Player house ──────────────────────────────────────────────────
        _draw_house(surf, HOUSE_POS[0], HOUSE_POS[1])

        # ── 6. Barrels and crates near buildings ─────────────────────────────
        rng = random.Random(77)
        for title, specialty, px, py in MERCHANT_SPECS:
            # 2-3 props per building
            for i in range(rng.randint(2, 3)):
                ox = px + rng.randint(-120, 120)
                oy = py + rng.randint(50, 90)
                if rng.random() < 0.5:
                    _draw_barrel(surf, ox - 11, oy - 15)
                else:
                    _draw_crate(surf, ox - 14, oy - 13)

        # ── 7. Dungeon entrance gate ──────────────────────────────────────────
        ex, ey = DUNGEON_ENTRANCE_POS
        _draw_dungeon_gate(surf, ex, ey)

        # ── 8. Wall torch sconces (static bracket; flame drawn in draw()) ─────
        B = 38
        torch_rng = random.Random(31)
        wall_torches = []
        # top wall torches (skip gate area)
        ex_ = DUNGEON_ENTRANCE_POS[0]
        for wx in range(160, TOWN_W - 160, 200):
            if abs(wx - ex_) > 120:
                wall_torches.append((wx, B - 2))
        # left/right wall torches
        for wy in range(140, TOWN_H - 140, 200):
            wall_torches.append((B - 2,          wy))
            wall_torches.append((TOWN_W - B + 2, wy))
        # bottom wall torches
        for wx in range(160, TOWN_W - 160, 240):
            wall_torches.append((wx, TOWN_H - B + 2))

        for tx, ty in wall_torches:
            # iron bracket
            pygame.draw.rect(surf, _IR_DARK, (tx - 4, ty - 2, 8, 14))
            pygame.draw.rect(surf, _IR_MID,  (tx - 3, ty - 1, 6, 12))
            pygame.draw.line(surf, _IR_LGT,  (tx - 2, ty - 1), (tx - 2, ty + 10))
            # torch body
            pygame.draw.rect(surf, _WD_DARK, (tx - 2, ty + 2, 4, 8))
            pygame.draw.line(surf, _WD_LGT,  (tx - 1, ty + 2), (tx - 1, ty + 9))

        # Store torch positions + random phases for animation
        self._torch_positions = [(tx, ty - 4) for tx, ty in wall_torches]
        # Also add building torch positions (on column brackets)
        for title, specialty, px, py in MERCHANT_SPECS:
            BW = 200
            bx = px - BW // 2
            by = py - 140 // 2 - 20
            for side_x in [bx - 10, bx + BW + 10]:
                self._torch_positions.append((side_x, by + 20))
        # House door torches
        _h_bw, _h_bh = 180, 128
        _h_door_w = 36
        _h_bx = HOUSE_POS[0] - _h_bw // 2
        _h_by = HOUSE_POS[1] - _h_bh // 2 - 15
        _h_door_y = _h_by + (_h_bh - 32) - 64
        _h_door_x = HOUSE_POS[0] - _h_door_w // 2
        for _tx in [_h_door_x - 14, _h_door_x + _h_door_w + 8]:
            self._torch_positions.append((_tx, _h_door_y - 4))
        self._torch_phases = [
            torch_rng.uniform(0, math.pi * 2)
            for _ in self._torch_positions
        ]

        self._bg = surf
        return surf

    # ── Public draw ───────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface, time: float,
             near_entrance: bool, near_house: bool = False):
        """Draw background + animated dungeon entrance portal and torches."""
        self._ensure_fonts()
        if self._bg is None:
            self._build_bg()
        surface.blit(self._bg, (0, 0))

        # ── Animated torch flames ─────────────────────────────────────────────
        for (tx, ty), phase in zip(self._torch_positions, self._torch_phases):
            flicker = 0.65 + 0.35 * math.sin(time * 9.4 + phase)
            r_ = int(6 + 4 * flicker)
            # outer glow
            glow_s = pygame.Surface((r_ * 4, r_ * 4), pygame.SRCALPHA)
            pygame.draw.circle(glow_s, (255, 120, 20, int(40 * flicker)),
                               (r_ * 2, r_ * 2), r_ * 2)
            surface.blit(glow_s, (tx - r_ * 2, ty - r_ * 2))
            # inner flame
            flame_s = pygame.Surface((r_ * 2 + 4, r_ * 2 + 4), pygame.SRCALPHA)
            col_inner = (255, int(180 + 60 * flicker), 20, int(200 * flicker))
            col_tip   = (255, 220, 80, int(160 * flicker))
            pygame.draw.circle(flame_s, col_inner,
                               (r_ + 2, r_ + 2), r_)
            pygame.draw.circle(flame_s, col_tip,
                               (r_ + 2, r_ + 2), r_ // 2)
            surface.blit(flame_s, (tx - r_ - 2, ty - r_ - 2))

        # ── Animated portal glow inside the archway ───────────────────────────
        ex, ey = DUNGEON_ENTRANCE_POS
        pulse  = 0.65 + 0.35 * math.sin(time * 2.8)
        glow   = (80, 30, 140) if near_entrance else (40, 12, 80)
        for r in range(34, 6, -5):
            a  = int(70 * pulse * (r / 34))
            gs = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(gs, (*glow, a), (r, r), r)
            surface.blit(gs, (ex - r, ey + 12 - r))

        # ── House label and interaction hint ──────────────────────────────────
        hpx, hpy = HOUSE_POS
        _h_bh = 128
        _h_by = hpy - _h_bh // 2 - 15
        home_col = (220, 185, 80) if near_house else (160, 130, 55)
        home_lbl = self._font.render(t("town.your_home"), True, home_col)
        _blit_shadowed(surface, home_lbl,
                       home_lbl.get_rect(centerx=hpx, centery=_h_by - 70).topleft)
        if near_house:
            hint = self._font_sm.render(t("town.enter_house"), True, (240, 200, 120))
            _blit_shadowed(surface, hint,
                           hint.get_rect(centerx=hpx, centery=hpy + 80).topleft)

        # ── Stall names with drop shadows ─────────────────────────────────────
        for title, specialty, px, py in MERCHANT_SPECS:
            pal = _STALL[specialty]
            display_name = t(f"merchant.{title.lower()}")
            name_s = self._font.render(display_name, True, pal["hi"])
            nrect  = name_s.get_rect(centerx=px, centery=py - 120)
            _blit_shadowed(surface, name_s, nrect.topleft, shadow_off=(2, 2))

        # ── Dungeon entrance sign with shadow ─────────────────────────────────
        lbl_col = (200, 160, 255) if near_entrance else (140, 100, 200)
        lbl = self._font.render(t("town.dungeon_sign"), True, lbl_col)
        lrect = lbl.get_rect(centerx=ex, centery=ex - 962)  # ey - 66 equiv
        # recalculate properly
        lrect = lbl.get_rect(centerx=ex, centery=ey - 66)
        _blit_shadowed(surface, lbl, lrect.topleft, shadow_off=(2, 2))

        if near_entrance:
            hint = self._font_sm.render(t("town.enter_dungeon"), True, (220, 190, 255))
            hrect = hint.get_rect(centerx=ex, centery=ey + 46)
            _blit_shadowed(surface, hint, hrect.topleft)

    def draw_return_notice(self, surface: pygame.Surface, msg: str):
        """Short-lived 'Rested' banner after returning from the dungeon."""
        self._ensure_fonts()
        cx = TOWN_W // 2
        s = self._font.render(msg, True, (120, 240, 120))
        bg = pygame.Surface((s.get_width() + 24, s.get_height() + 10), pygame.SRCALPHA)
        bg.fill((0, 40, 0, 200))
        surface.blit(bg, bg.get_rect(center=(cx, TOWN_H // 2 - 80)))
        _blit_shadowed(surface, s, s.get_rect(center=(cx, TOWN_H // 2 - 80)).topleft)
