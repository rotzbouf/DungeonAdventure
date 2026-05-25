"""
Town — the player's central hub between dungeon runs.

A single fixed-layout screen (no scrolling).  Four specialist merchants
occupy the four corners; a dungeon-entrance archway sits at the top-centre.
Entering town fully restores the player's HP and mana.
"""
from __future__ import annotations

import math
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

# (display_title, specialty_key, px, py)
MERCHANT_SPECS: list[tuple[str, str, int, int]] = [
    ("Blacksmith",  "weapons",  200,  200),
    ("Armourer",    "armor",   1080,  200),
    ("Jeweler",     "jewelry",  200,  470),
    ("Alchemist",   "potions", 1080,  470),
]

TOWN_INTERACT_R = TILE_SIZE * 3.0   # bigger interact radius than dungeon


# ── Stall colour palette per specialty ────────────────────────────────────────

_STALL: dict[str, dict] = {
    "weapons":  {"bg": (72,  24,  8),  "hi": (180,  70, 20), "awning": (160, 50, 10)},
    "armor":    {"bg": (16,  36, 68),  "hi": ( 80, 130, 210), "awning": (30, 70, 130)},
    "jewelry":  {"bg": (12,  64, 64),  "hi": ( 40, 200, 200), "awning": (20, 130, 130)},
    "potions":  {"bg": (20,  56, 20),  "hi": ( 60, 200,  60), "awning": (30, 120, 30)},
}


# ── TownBounds — constrains player movement to the playable area ───────────────

class TownBounds:
    """
    Drop-in substitute for Dungeon when updating the player in town.
    Reports non-walkable for the two-tile border strip so the player
    cannot walk into the walls.
    """
    _MARGIN = 2   # tiles from each edge that are off-limits

    def is_walkable(self, tx: int, ty: int) -> bool:
        max_x = TOWN_W  // TILE_SIZE - 1
        max_y = TOWN_H  // TILE_SIZE - 1
        m = self._MARGIN
        return m <= tx <= max_x - m and m <= ty <= max_y - m


TOWN_BOUNDS = TownBounds()


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

    # ── Init ──────────────────────────────────────────────────────────────────

    def _ensure_fonts(self):
        if self._font is None:
            self._font    = pygame.font.SysFont("monospace", 17, bold=True)
            self._font_sm = pygame.font.SysFont("monospace", 13)

    def _build_bg(self) -> pygame.Surface:
        """Build the static background surface (cobblestone, walls, stalls)."""
        surf = pygame.Surface((TOWN_W, TOWN_H))

        # ── Cobblestone floor ─────────────────────────────────────────────────
        SW, SH = 46, 28   # stone block size
        for row in range(TOWN_H // SH + 2):
            off = (SW // 2) if row % 2 else 0
            for col in range(-1, TOWN_W // SW + 2):
                bx = col * SW + off
                by = row * SH
                if bx + SW < 0 or bx >= TOWN_W or by + SH < 0 or by >= TOWN_H:
                    continue
                v   = ((col * 3 + row * 7) % 10)
                col_ = (64 + v, 54 + v // 2, 42)
                r   = pygame.Rect(bx + 1, by + 1, SW - 2, SH - 2)
                pygame.draw.rect(surf, col_, r)
                pygame.draw.line(surf, (44, 38, 30), r.topleft, r.topright)
                pygame.draw.line(surf, (44, 38, 30), r.topleft, r.bottomleft)

        # ── Border walls ──────────────────────────────────────────────────────
        _WALL = (50, 46, 42)
        _W_HI = (88, 82, 76)
        B = 34   # border width in px
        for wr in [pygame.Rect(0, 0, TOWN_W, B),
                   pygame.Rect(0, TOWN_H - B, TOWN_W, B),
                   pygame.Rect(0, 0, B, TOWN_H),
                   pygame.Rect(TOWN_W - B, 0, B, TOWN_H)]:
            pygame.draw.rect(surf, _WALL, wr)
            pygame.draw.rect(surf, _W_HI, wr, 2)
        # inner lip
        pygame.draw.rect(surf, _W_HI,
                         (B, B, TOWN_W - B * 2, TOWN_H - B * 2), 1)

        # ── Corner lanterns ───────────────────────────────────────────────────
        for lx, ly in [(B + 20, B + 20), (TOWN_W - B - 20, B + 20),
                       (B + 20, TOWN_H - B - 20), (TOWN_W - B - 20, TOWN_H - B - 20)]:
            pygame.draw.line(surf, (90, 70, 40), (lx, ly - 12), (lx, ly - 26), 2)
            pygame.draw.rect(surf, (70, 52, 16), (lx - 5, ly - 12, 10, 12))
            pygame.draw.rect(surf, (200, 155, 30), (lx - 4, ly - 11, 8, 10))
            pygame.draw.circle(surf, (252, 215, 70), (lx, ly - 6), 3)

        # ── Central well ──────────────────────────────────────────────────────
        wcx, wcy = TOWN_W // 2, TOWN_H // 2
        pygame.draw.circle(surf, (36, 32, 28), (wcx, wcy), 28, 7)
        pygame.draw.circle(surf, (70, 62, 54), (wcx, wcy), 28, 2)
        # wooden frame
        for wx, wy in [(-10, -26), (10, -26)]:
            pygame.draw.line(surf, (100, 75, 40), (wcx + wx, wcy + wy),
                             (wcx + wx, wcy + wy - 18), 2)
        pygame.draw.line(surf, (80, 58, 28),
                         (wcx - 10, wcy - 44), (wcx + 10, wcy - 44), 2)
        # bucket
        pygame.draw.rect(surf, (60, 45, 20), (wcx - 4, wcy - 42, 8, 8))

        # ── Merchant stalls ───────────────────────────────────────────────────
        for title, specialty, px, py in MERCHANT_SPECS:
            pal = _STALL[specialty]
            sw, sh = 100, 100
            sr = pygame.Rect(px - sw // 2, py - sh // 2, sw, sh)

            # Back wall
            pygame.draw.rect(surf, pal["bg"], sr)
            pygame.draw.rect(surf, pal["hi"], sr, 2)

            # Counter (lower band)
            counter_r = pygame.Rect(sr.left - 6, sr.centery + 10, sr.width + 12, 24)
            pygame.draw.rect(surf, tuple(min(255, c + 18) for c in pal["bg"]), counter_r)
            pygame.draw.rect(surf, pal["hi"], counter_r, 1)

            # Awning strip above
            aw_r = pygame.Rect(sr.left - 10, sr.top - 10, sr.width + 20, 16)
            pygame.draw.rect(surf, pal["awning"], aw_r)
            # Striped detail on awning
            stripe_col = tuple(min(255, c + 30) for c in pal["awning"])
            for sx_ in range(aw_r.left + 6, aw_r.right, 14):
                pygame.draw.line(surf, stripe_col,
                                 (sx_, aw_r.top), (sx_ - 6, aw_r.bottom), 2)

        # ── Dungeon entrance archway (static part) ────────────────────────────
        ex, ey = DUNGEON_ENTRANCE_POS
        AW, AH = 68, 90   # arch width / height
        _STONE  = (44, 40, 52)
        _KEYSTO = (72, 66, 82)
        _ARCH_D = (18, 10, 32)

        # outer arch blocks
        arch_r = pygame.Rect(ex - AW // 2 - 10, ey - AH // 2 - 4, AW + 20, AH + 4)
        pygame.draw.rect(surf, _STONE, arch_r)
        pygame.draw.rect(surf, _KEYSTO, arch_r, 3)
        # inner void
        inner_r = pygame.Rect(ex - AW // 2, ey - AH // 2 + 8, AW, AH - 8)
        pygame.draw.rect(surf, _ARCH_D, inner_r)
        # arch curve (top)
        pygame.draw.ellipse(surf, _ARCH_D,
                            pygame.Rect(ex - AW // 2, ey - AH // 2 - 12, AW, AH // 2))
        pygame.draw.ellipse(surf, _STONE,
                            pygame.Rect(ex - AW // 2 - 6, ey - AH // 2 - 16, AW + 12, AH // 2 + 4), 5)
        # keystone block
        pygame.draw.rect(surf, _KEYSTO,
                         (ex - 7, ey - AH // 2 - 18, 14, 10))
        # "DUNGEON" sign above arch
        # (rendered dynamically in draw() so we can use a font)

        self._bg = surf
        return surf

    # ── Public draw ───────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface, time: float,
             near_entrance: bool):
        """Draw background + animated dungeon entrance portal."""
        self._ensure_fonts()
        if self._bg is None:
            self._build_bg()
        surface.blit(self._bg, (0, 0))

        # ── Animated portal glow inside the archway ───────────────────────────
        ex, ey = DUNGEON_ENTRANCE_POS
        pulse  = 0.65 + 0.35 * math.sin(time * 2.8)
        glow   = (60, 20, 110) if near_entrance else (30, 10, 60)
        for r in range(28, 6, -4):
            a  = int(55 * pulse * (r / 28))
            gs = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(gs, (*glow, a), (r, r), r)
            surface.blit(gs, (ex - r, ey + 10 - r))

        # ── Stall names (rendered each frame so fonts are ready) ──────────────
        for title, specialty, px, py in MERCHANT_SPECS:
            pal = _STALL[specialty]
            display_name = t(f"merchant.{title.lower()}")
            name_s = self._font.render(display_name, True, pal["hi"])
            surface.blit(name_s, name_s.get_rect(centerx=px, centery=py - 60))

        # ── Dungeon entrance sign ─────────────────────────────────────────────
        lbl_col = (180, 140, 255) if near_entrance else (120, 90, 180)
        lbl = self._font.render(t("town.dungeon_sign"), True, lbl_col)
        surface.blit(lbl, lbl.get_rect(centerx=ex, centery=ey - 62))

        if near_entrance:
            hint = self._font_sm.render(t("town.enter_dungeon"), True, (200, 170, 255))
            surface.blit(hint, hint.get_rect(centerx=ex, centery=ey + 38))

    def draw_return_notice(self, surface: pygame.Surface, msg: str):
        """Short-lived 'Rested' banner after returning from the dungeon."""
        self._ensure_fonts()
        cx = TOWN_W // 2
        s = self._font.render(msg, True, (120, 240, 120))
        bg = pygame.Surface((s.get_width() + 24, s.get_height() + 10), pygame.SRCALPHA)
        bg.fill((0, 40, 0, 200))
        surface.blit(bg, bg.get_rect(center=(cx, TOWN_H // 2 - 80)))
        surface.blit(s, s.get_rect(center=(cx, TOWN_H // 2 - 80)))
