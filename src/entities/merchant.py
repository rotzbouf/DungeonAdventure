"""
Merchant NPC — stationary shopkeeper placed in dungeon rooms.

Pressing F when nearby opens the shop screen.
"""
from __future__ import annotations

import math
import random
import pygame
from src.settings import TILE_SIZE, SCREEN_WIDTH, SCREEN_HEIGHT, HUD_HEIGHT
from src.items.item import (EquipItem, HealthPotion, random_equip,
                             QUALITY_NORMAL, QUALITY_MAGIC, QUALITY_RARE, QUALITY_UNIQUE)

# How close the player must be to interact (pixels)
INTERACT_RADIUS = TILE_SIZE * 2.5


# ── Pricing ───────────────────────────────────────────────────────────────────

def item_buy_price(item) -> int:
    """Gold cost to buy an item from the merchant."""
    if isinstance(item, HealthPotion):
        return 60
    if isinstance(item, EquipItem):
        base = max(20, item.base_stat * 8 + 25)
        mult = {
            QUALITY_NORMAL: 1,
            QUALITY_MAGIC:  4,
            QUALITY_RARE:   12,
            QUALITY_UNIQUE: 35,
        }
        return int(base * mult.get(item.quality, 1))
    return 10


def item_sell_price(item) -> int:
    """Gold earned when the player sells an item."""
    return max(5, item_buy_price(item) // 3)


# ── Merchant entity ───────────────────────────────────────────────────────────

class Merchant:
    """Stationary NPC shopkeeper. Not an Entity subclass — no physics needed."""

    def __init__(self, px: float, py: float, dungeon_level: int):
        self.x, self.y = px, py
        self.size      = 28
        self.rect      = pygame.Rect(0, 0, self.size, self.size)
        self.rect.center = (int(px), int(py))
        self._bob      = random.uniform(0, math.pi * 2)
        self.stock: list = self._generate_stock(dungeon_level)

    # ── Stock generation ──────────────────────────────────────────────────────

    def _generate_stock(self, level: int) -> list:
        """Generate 3 potions + 5 equipment pieces scaled to the dungeon level."""
        items: list = []
        tier = min(5, max(1, level))

        # Three health potions always available
        for _ in range(3):
            p = HealthPotion(0, 0)
            p._reposition(self.x, self.y)
            items.append(p)

        # Equipment — quality skews toward level
        if level <= 1:
            qualities = [QUALITY_NORMAL, QUALITY_NORMAL, QUALITY_MAGIC,
                         QUALITY_MAGIC,  QUALITY_MAGIC]
        elif level <= 2:
            qualities = [QUALITY_NORMAL, QUALITY_MAGIC,  QUALITY_MAGIC,
                         QUALITY_MAGIC,  QUALITY_RARE]
        elif level <= 3:
            qualities = [QUALITY_MAGIC,  QUALITY_MAGIC,  QUALITY_RARE,
                         QUALITY_RARE,   QUALITY_RARE]
        else:
            qualities = [QUALITY_MAGIC,  QUALITY_RARE,   QUALITY_RARE,
                         QUALITY_RARE,   QUALITY_UNIQUE]

        for q in qualities:
            it = random_equip(0, 0, ilvl=tier, quality=q, slot=None)
            if it:
                it._reposition(self.x, self.y)
                items.append(it)
        return items

    # ── Update ────────────────────────────────────────────────────────────────

    def update(self, dt: float):
        self._bob += dt * 1.6

    def near_player(self, player) -> bool:
        return math.hypot(player.x - self.x, player.y - self.y) < INTERACT_RADIUS

    # ── Draw ──────────────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface, camera):
        play_h = SCREEN_HEIGHT - HUD_HEIGHT
        sx = int(self.x - camera.x)
        sy = int(self.y - camera.y)
        if not (-40 < sx < SCREEN_WIDTH + 40 and -40 < sy < play_h + 40):
            return

        bob = int(math.sin(self._bob) * 2)
        cx, cy = sx, sy + bob

        _BLK    = (0,   0,   0)
        _ROBE   = (88,  40, 128)   # purple robe
        _ROBE_D = (52,  20,  80)
        _ROBE_H = (140, 80, 192)   # robe highlight
        _SKIN   = (252, 188, 100)
        _GOLD   = (252, 188,   0)
        _HOOD   = (56,  16,  96)
        _GEM    = (148,  0, 216)   # purple
        _GEM_H  = (200, 100, 255)

        h = self.size

        # ── Robe (trapezoidal body) ──────────────────────────────────────────
        robe_pts = [
            (cx - 11, cy + h // 2),
            (cx + 11, cy + h // 2),
            (cx + 7,  cy - 6),
            (cx - 7,  cy - 6),
        ]
        pygame.draw.polygon(surface, _BLK,    [(x - 1, y + 1) for x, y in robe_pts])
        pygame.draw.polygon(surface, _ROBE,   robe_pts)
        # Shadow on left half of robe
        pygame.draw.polygon(surface, _ROBE_D,
                            [(cx - 11, cy + h // 2), (cx, cy + h // 2),
                             (cx, cy - 6), (cx - 7, cy - 6)])
        # Highlight on right shoulder
        pygame.draw.line(surface, _ROBE_H, (cx + 7, cy - 6), (cx + 11, cy + h // 2), 1)

        # ── Hood ──────────────────────────────────────────────────────────────
        pygame.draw.circle(surface, _BLK,  (cx, cy - 10), 11)
        pygame.draw.circle(surface, _HOOD, (cx, cy - 10), 10)

        # ── Face ──────────────────────────────────────────────────────────────
        pygame.draw.circle(surface, _SKIN, (cx, cy - 10), 7)
        # Eyes
        surface.set_at((cx - 2, cy - 11), _BLK)
        surface.set_at((cx + 2, cy - 11), _BLK)
        # Mouth (tiny smile)
        pygame.draw.line(surface, _BLK, (cx - 2, cy - 8), (cx + 2, cy - 8), 1)

        # ── Staff (right side, extends above head) ────────────────────────────
        staff_x = cx + 12
        staff_top = cy - h // 2 - 8
        pygame.draw.line(surface, _BLK,  (staff_x, cy + h // 2), (staff_x, staff_top), 3)
        pygame.draw.line(surface, _GOLD, (staff_x, cy + h // 2), (staff_x, staff_top), 2)
        # Gem at top
        pygame.draw.circle(surface, _BLK, (staff_x, staff_top), 5)
        pygame.draw.circle(surface, _GEM, (staff_x, staff_top), 4)
        pygame.draw.circle(surface, _GEM_H, (staff_x, staff_top), 2)
        pygame.draw.circle(surface, (255, 255, 255), (staff_x - 1, staff_top - 1), 1)

        # ── Ambient glow ring (pulsing purple) ────────────────────────────────
        pulse = 0.55 + 0.45 * abs(math.sin(self._bob * 0.9))
        gr    = 22
        gs    = pygame.Surface((gr * 2, gr * 2), pygame.SRCALPHA)
        pygame.draw.circle(gs, (148, 0, 216, int(35 * pulse)), (gr, gr), gr)
        surface.blit(gs, (cx - gr, cy - gr))
