"""
Merchant NPCs.

Two flavours
------------
Merchant     — dungeon merchant; very rare, sells only Rare/Unique items at
               premium prices (2.5×).  Created with `elite=True` by the dungeon
               loader.

TownMerchant — permanent town shopkeeper; one per speciality (weapons, armor,
               jewellery, potions).  Normal prices.  Stock refreshes each time
               the player enters town.
"""
from __future__ import annotations

import math
import random
import pygame
from src.settings import TILE_SIZE, SCREEN_WIDTH, SCREEN_HEIGHT, HUD_HEIGHT
from src.items.item import (EquipItem, HealthPotion, random_equip,
                             QUALITY_MAGIC, QUALITY_RARE, QUALITY_UNIQUE,
                             SLOT_WEAPON, SLOT_SHIELD, SLOT_HELM, SLOT_CHEST,
                             SLOT_GLOVES, SLOT_BOOTS, SLOT_BELT,
                             SLOT_RING, SLOT_AMULET)

# How close the player must be to open the dungeon shop
INTERACT_RADIUS  = TILE_SIZE * 2.5
# How close the player must be to open a town shop
TOWN_INTERACT_R  = TILE_SIZE * 3.0


# ── Pricing ───────────────────────────────────────────────────────────────────

def item_buy_price(item) -> int:
    """Base gold cost (before any merchant multiplier)."""
    if isinstance(item, HealthPotion):
        return 60
    if isinstance(item, EquipItem):
        base = max(20, item.base_stat * 8 + 25)
        mult = {
            QUALITY_MAGIC:  4,
            QUALITY_RARE:   12,
            QUALITY_UNIQUE: 35,
        }
        return int(base * mult.get(item.quality, 1))
    return 10


def item_sell_price(item) -> int:
    return max(5, item_buy_price(item) // 3)


# ── Dungeon Merchant ──────────────────────────────────────────────────────────

class Merchant:
    """
    Stationary dungeon shopkeeper.  Very rare find; always carries
    high-quality items at premium prices.
    """

    def __init__(self, px: float, py: float, dungeon_level: int,
                 elite: bool = True):
        self.x, self.y   = px, py
        self.size        = 28
        self.rect        = pygame.Rect(0, 0, self.size, self.size)
        self.rect.center = (int(px), int(py))
        self._bob        = random.uniform(0, math.pi * 2)
        self.elite       = elite
        self.price_mult  = 2.5 if elite else 1.0
        self.stock: list = self._generate_stock(dungeon_level)

    # ── Queries ───────────────────────────────────────────────────────────────

    def get_title(self) -> str:
        from src.locale import t
        return t("merchant.travelling") if self.elite else t("merchant.default")

    def price_of(self, item) -> int:
        """Price the player must pay to buy this item from this merchant."""
        return int(item_buy_price(item) * self.price_mult)

    def near_player(self, player) -> bool:
        return math.hypot(player.x - self.x, player.y - self.y) < INTERACT_RADIUS

    # ── Stock ─────────────────────────────────────────────────────────────────

    def _generate_stock(self, level: int) -> list:
        items: list = []
        tier = min(5, max(1, level))

        if self.elite:
            # Rare/Unique treasure trove — no potions, just premium gear
            for q in [QUALITY_RARE, QUALITY_RARE, QUALITY_RARE,
                      QUALITY_UNIQUE, QUALITY_UNIQUE]:
                it = random_equip(0, 0, ilvl=tier, quality=q, slot=None)
                if it:
                    it._reposition(self.x, self.y)
                    items.append(it)
        else:
            # Fallback normal stock (should rarely be used)
            for _ in range(3):
                p = HealthPotion(0, 0)
                p._reposition(self.x, self.y)
                items.append(p)
            for q in [QUALITY_MAGIC, QUALITY_MAGIC, QUALITY_RARE,
                      QUALITY_RARE, QUALITY_RARE]:
                it = random_equip(0, 0, ilvl=tier, quality=q, slot=None)
                if it:
                    it._reposition(self.x, self.y)
                    items.append(it)
        return items

    # ── Update ────────────────────────────────────────────────────────────────

    def update(self, dt: float):
        self._bob += dt * 1.6

    # ── Draw ──────────────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface, camera):
        play_h = SCREEN_HEIGHT - HUD_HEIGHT
        sx = int(self.x - camera.x)
        sy = int(self.y - camera.y)
        if not (-40 < sx < SCREEN_WIDTH + 40 and -40 < sy < play_h + 40):
            return
        self._draw_sprite(surface, sx, sy,
                          robe=(88, 40, 128), robe_d=(52, 20, 80), robe_h=(140, 80, 192),
                          gem=(148, 0, 216), gem_h=(200, 100, 255))

    def _draw_sprite(self, surface, cx, cy,
                     robe, robe_d, robe_h, gem, gem_h):
        bob = int(math.sin(self._bob) * 2)
        cy += bob

        _BLK  = (0,   0,   0)
        _SKIN = (252, 188, 100)
        _GOLD = (252, 188,   0)
        _HOOD = tuple(max(0, c - 36) for c in robe)

        h = self.size

        # Robe
        robe_pts = [(cx - 11, cy + h // 2), (cx + 11, cy + h // 2),
                    (cx +  7, cy - 6),       (cx -  7, cy - 6)]
        pygame.draw.polygon(surface, _BLK,   [(x-1, y+1) for x, y in robe_pts])
        pygame.draw.polygon(surface, robe,   robe_pts)
        pygame.draw.polygon(surface, robe_d,
                            [(cx-11, cy+h//2), (cx, cy+h//2), (cx, cy-6), (cx-7, cy-6)])
        pygame.draw.line(surface, robe_h, (cx+7, cy-6), (cx+11, cy+h//2), 1)

        # Hood
        pygame.draw.circle(surface, _BLK,  (cx, cy - 10), 11)
        pygame.draw.circle(surface, _HOOD, (cx, cy - 10), 10)

        # Face
        pygame.draw.circle(surface, _SKIN, (cx, cy - 10), 7)
        surface.set_at((cx - 2, cy - 11), _BLK)
        surface.set_at((cx + 2, cy - 11), _BLK)
        pygame.draw.line(surface, _BLK, (cx - 2, cy - 8), (cx + 2, cy - 8), 1)

        # Staff
        staff_x  = cx + 12
        staff_top = cy - h // 2 - 8
        pygame.draw.line(surface, _BLK,  (staff_x, cy + h // 2), (staff_x, staff_top), 3)
        pygame.draw.line(surface, _GOLD, (staff_x, cy + h // 2), (staff_x, staff_top), 2)
        pygame.draw.circle(surface, _BLK,  (staff_x, staff_top), 5)
        pygame.draw.circle(surface, gem,   (staff_x, staff_top), 4)
        pygame.draw.circle(surface, gem_h, (staff_x, staff_top), 2)
        pygame.draw.circle(surface, (255, 255, 255), (staff_x - 1, staff_top - 1), 1)

        # Glow ring
        pulse = 0.55 + 0.45 * abs(math.sin(self._bob * 0.9))
        gr    = 22
        gs    = pygame.Surface((gr * 2, gr * 2), pygame.SRCALPHA)
        pygame.draw.circle(gs, (*gem, int(35 * pulse)), (gr, gr), gr)
        surface.blit(gs, (cx - gr, cy - gr))


# ── Town Merchant ─────────────────────────────────────────────────────────────

# Slot groups per specialty
_SPECIALTY_SLOTS: dict[str, list[str] | None] = {
    "weapons": [SLOT_WEAPON],
    "armor":   [SLOT_SHIELD, SLOT_HELM, SLOT_CHEST,
                SLOT_GLOVES, SLOT_BOOTS, SLOT_BELT],
    "jewelry": [SLOT_RING, SLOT_AMULET],
    "potions": None,   # mixed — handled separately
    "enchant": None,   # no traditional stock — handled by EnchantScreen
    "craft":   None,   # no traditional stock — handled by CraftScreen
}

# Visual palette per specialty
_SPECIALTY_PALETTE: dict[str, dict] = {
    "weapons": {"robe": (180, 70, 20), "robe_d": (100, 32, 8),
                "robe_h": (240, 130, 60), "gem": (220, 80, 20), "gem_h": (255, 160, 80)},
    "armor":   {"robe": (50, 80, 140), "robe_d": (24, 44, 88),
                "robe_h": (100, 150, 220), "gem": (60, 160, 255), "gem_h": (140, 210, 255)},
    "jewelry": {"robe": (20, 140, 140), "robe_d": (8, 76, 76),
                "robe_h": (50, 220, 220), "gem": (0, 230, 230), "gem_h": (140, 255, 255)},
    "potions": {"robe": (40, 130, 50), "robe_d": (18, 72, 22),
                "robe_h": (80, 210, 90), "gem": (80, 240, 80), "gem_h": (180, 255, 180)},
    "enchant": {"robe": (80, 20, 140), "robe_d": (40, 8, 80),
                "robe_h": (160, 80, 255), "gem": (200, 100, 255), "gem_h": (230, 180, 255)},
    "craft":   {"robe": (100, 58, 16), "robe_d": (56, 30, 6),
                "robe_h": (200, 130, 50), "gem": (220, 150, 40), "gem_h": (255, 200, 100)},
}


class TownMerchant(Merchant):
    """
    Permanent town shopkeeper with a fixed specialty.
    Sells slot-appropriate gear at normal prices.
    Stock is regenerated each time the player visits town.
    """

    def __init__(self, px: float, py: float,
                 title: str, specialty: str, player_level: int = 1):
        # Bypass Merchant.__init__ so we can set everything ourselves
        self.x, self.y   = px, py
        self.size        = 32   # slightly larger than dungeon merchants
        self.rect        = pygame.Rect(0, 0, self.size, self.size)
        self.rect.center = (int(px), int(py))
        self._bob        = random.uniform(0, math.pi * 2)
        self.elite       = False
        self.price_mult  = 1.0

        self.title      = title
        self.specialty  = specialty
        self._palette   = _SPECIALTY_PALETTE[specialty]

        self.stock: list = self._build_specialty_stock(player_level)

    # ── Identity ──────────────────────────────────────────────────────────────

    def get_title(self) -> str:
        from src.locale import t
        key = f"merchant.{self.title.lower()}"
        txt = t(key)
        return txt.upper() if txt != key else self.title.upper()

    def price_of(self, item) -> int:
        return item_buy_price(item)

    def near_player(self, player) -> bool:
        return math.hypot(player.x - self.x, player.y - self.y) < TOWN_INTERACT_R

    # ── Stock ─────────────────────────────────────────────────────────────────

    def _build_specialty_stock(self, player_level: int) -> list:
        items: list = []
        tier  = max(1, min(10, player_level))

        # Quality distribution based on player level
        if player_level <= 3:
            equip_qualities = [QUALITY_MAGIC, QUALITY_MAGIC, QUALITY_MAGIC,
                               QUALITY_RARE,  QUALITY_RARE]
        elif player_level <= 8:
            equip_qualities = [QUALITY_MAGIC, QUALITY_RARE,  QUALITY_RARE,
                               QUALITY_RARE,  QUALITY_UNIQUE]
        else:
            equip_qualities = [QUALITY_RARE,  QUALITY_RARE,  QUALITY_UNIQUE,
                               QUALITY_UNIQUE, QUALITY_UNIQUE]

        slots = _SPECIALTY_SLOTS[self.specialty]

        if self.specialty in ("enchant", "craft"):
            return []   # handled by EnchantScreen / CraftScreen
        if self.specialty == "potions":
            # Alchemist: lots of potions + a few mixed-slot items
            for _ in range(5):
                p = HealthPotion(0, 0)
                p._reposition(self.x, self.y)
                items.append(p)
            for q in equip_qualities[:3]:
                it = random_equip(0, 0, ilvl=tier, quality=q, slot=None)
                if it:
                    it._reposition(self.x, self.y)
                    items.append(it)
        else:
            # 2 potions for all other specialists
            for _ in range(2):
                p = HealthPotion(0, 0)
                p._reposition(self.x, self.y)
                items.append(p)
            # 5 slot-appropriate equipment pieces
            for q in equip_qualities:
                slot = random.choice(slots)   # type: ignore[arg-type]
                it = random_equip(0, 0, ilvl=tier, quality=q, slot=slot)
                if it:
                    it._reposition(self.x, self.y)
                    items.append(it)
        return items

    def restock(self, player_level: int):
        """Regenerate stock — called each time the player enters town."""
        self.stock = self._build_specialty_stock(player_level)

    # ── Draw ──────────────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface, camera):
        """Draw the merchant; camera is a zero-offset Camera in town."""
        sx = int(self.x - camera.x)
        sy = int(self.y - camera.y)
        pal = self._palette
        self._draw_sprite(surface, sx, sy,
                          robe=pal["robe"], robe_d=pal["robe_d"],
                          robe_h=pal["robe_h"],
                          gem=pal["gem"], gem_h=pal["gem_h"])
