"""
Crafting and disassembly material system.

Five material tiers extracted from disassembled gear:
  scrap_metal   – normal/magic weapons and armour
  mana_shard    – any jewellery (rings, amulets)
  ether_dust    – magic+ items (affix essence)
  rune_fragment – rare+ items
  void_crystal  – unique items
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from src.items.item import (
    EquipItem, HealthPotion, Modifier,
    QUALITY_NORMAL, QUALITY_MAGIC, QUALITY_RARE, QUALITY_UNIQUE,
    SLOT_WEAPON, SLOT_RING, SLOT_AMULET,
    random_equip, _pick_affixes, _ilvl_and_mult, _BASES,
)

if TYPE_CHECKING:
    pass


# ── Material definitions ───────────────────────────────────────────────────────

@dataclass
class Material:
    id:    str
    name:  str
    color: tuple
    desc:  str


MATERIALS: dict[str, Material] = {
    "scrap_metal":   Material("scrap_metal",   "Scrap Metal",   (140, 128, 112), "Salvaged from weapons and armour."),
    "mana_shard":    Material("mana_shard",    "Mana Shard",    ( 80, 160, 255), "Crystallised mana from jewellery."),
    "ether_dust":    Material("ether_dust",    "Ether Dust",    (180, 100, 255), "Affix essence from enchanted gear."),
    "rune_fragment": Material("rune_fragment", "Rune Fragment", (220, 175,   0), "Rare power from yellow-quality items."),
    "void_crystal":  Material("void_crystal",  "Void Crystal",  (255, 100,  30), "Essence of unique artefacts."),
}

_JEWEL_SLOTS = {SLOT_RING, SLOT_AMULET, "ring2"}
_ARMOUR_SLOTS = {"shield", "helm", "chest", "gloves", "boots", "belt"}

# ── Disassembly yield tables ───────────────────────────────────────────────────

def disassemble(item: EquipItem) -> dict[str, int]:
    """Return the material dict yielded by breaking down item."""
    q = item.quality
    slot = item.slot
    is_jewel  = slot in _JEWEL_SLOTS
    is_weapon = slot == SLOT_WEAPON

    if q == QUALITY_NORMAL:
        if is_jewel:
            return {"mana_shard": random.randint(2, 3)}
        return {"scrap_metal": random.randint(2, 4)}

    if q == QUALITY_MAGIC:
        if is_jewel:
            return {"mana_shard": random.randint(2, 3), "ether_dust": random.randint(1, 2)}
        return {"scrap_metal": random.randint(1, 2), "ether_dust": random.randint(2, 3)}

    if q == QUALITY_RARE:
        base = {"ether_dust": random.randint(3, 5), "rune_fragment": random.randint(2, 3)}
        if is_jewel:
            base["mana_shard"] = random.randint(1, 2)
        return base

    # QUALITY_UNIQUE
    return {"rune_fragment": random.randint(2, 4), "void_crystal": random.randint(1, 2)}


# ── Recipe definitions ─────────────────────────────────────────────────────────

@dataclass
class Recipe:
    id:          str
    name:        str
    cost:        dict[str, int]
    desc:        str
    result_type: str          # "potion" | "equip" | "reforge" | "add_slot"
    result_quality: int  = QUALITY_MAGIC
    result_slot:    str | None = None   # None = random; "jewel" = ring/amulet
    result_ilvl:    int  = 2
    # needs_target: True for reforge/add_slot (player must pick an item)
    needs_target: bool = False


_ARMOUR_SLOT_POOL = ["shield", "helm", "chest", "gloves", "boots", "belt"]

RECIPES: list[Recipe] = [
    # ── Consumables ───────────────────────────────────────────────────────────
    Recipe("health_potion", "Health Potion",
           cost={"scrap_metal": 5},
           desc="Brew a healing potion from salvaged metal scraps.",
           result_type="potion"),

    # ── Magic equipment ───────────────────────────────────────────────────────
    Recipe("magic_weapon", "Magic Weapon",
           cost={"scrap_metal": 6, "ether_dust": 3},
           desc="Forge a random Magic-quality weapon.",
           result_type="equip", result_quality=QUALITY_MAGIC,
           result_slot=SLOT_WEAPON, result_ilvl=2),

    Recipe("magic_armour", "Magic Armour",
           cost={"scrap_metal": 5, "ether_dust": 3},
           desc="Forge a random Magic-quality armour piece.",
           result_type="equip", result_quality=QUALITY_MAGIC,
           result_slot="armour", result_ilvl=2),

    Recipe("magic_jewel", "Magic Jewellery",
           cost={"mana_shard": 4, "ether_dust": 2},
           desc="Craft a random Magic-quality ring or amulet.",
           result_type="equip", result_quality=QUALITY_MAGIC,
           result_slot="jewel", result_ilvl=2),

    # ── Rare equipment ────────────────────────────────────────────────────────
    Recipe("rare_weapon", "Rare Weapon",
           cost={"ether_dust": 5, "rune_fragment": 3},
           desc="Forge a powerful Rare-quality weapon.",
           result_type="equip", result_quality=QUALITY_RARE,
           result_slot=SLOT_WEAPON, result_ilvl=4),

    Recipe("rare_armour", "Rare Armour",
           cost={"ether_dust": 4, "rune_fragment": 3},
           desc="Forge powerful Rare-quality armour.",
           result_type="equip", result_quality=QUALITY_RARE,
           result_slot="armour", result_ilvl=4),

    Recipe("rare_jewel", "Rare Jewellery",
           cost={"mana_shard": 4, "ether_dust": 3, "rune_fragment": 2},
           desc="Craft powerful Rare-quality jewellery.",
           result_type="equip", result_quality=QUALITY_RARE,
           result_slot="jewel", result_ilvl=4),

    # ── Unique ────────────────────────────────────────────────────────────────
    Recipe("unique_item", "Unique Artefact",
           cost={"rune_fragment": 5, "void_crystal": 2},
           desc="Channel void essence into a Unique artefact.",
           result_type="equip", result_quality=QUALITY_UNIQUE,
           result_slot=None, result_ilvl=5),

    # ── Item modification ─────────────────────────────────────────────────────
    Recipe("reforge", "Reforge Item",
           cost={"rune_fragment": 4},
           desc="Reroll all affixes on a Rare or Unique item. "
                "Select the target from your backpack.",
           result_type="reforge", needs_target=True),

    Recipe("add_slot", "Add Enchant Slot",
           cost={"rune_fragment": 3, "void_crystal": 2},
           desc="Add one enchantment slot to any item that has fewer than 3. "
                "Select the target from your backpack.",
           result_type="add_slot", needs_target=True),
]

RECIPE_BY_ID: dict[str, Recipe] = {r.id: r for r in RECIPES}


# ── Execution ─────────────────────────────────────────────────────────────────

def execute_recipe(recipe: Recipe, player,
                   target_item: EquipItem | None = None) -> str:
    """
    Apply recipe, deduct materials, return result description string.
    Raises ValueError if requirements not met.
    """
    mats = getattr(player, "materials", {})
    for mat, qty in recipe.cost.items():
        if mats.get(mat, 0) < qty:
            raise ValueError(f"Not enough {MATERIALS[mat].name}")

    if recipe.needs_target and target_item is None:
        raise ValueError("No target item selected")

    if recipe.result_type == "reforge":
        if target_item is None or target_item.quality not in (QUALITY_RARE, QUALITY_UNIQUE):
            raise ValueError("Target must be Rare or Unique")
        b_ilvl    = max(1, min(5, _BASES[target_item.base_name][3]))
        ilvl, dm  = _ilvl_and_mult(b_ilvl)
        new_mods  = _pick_affixes(target_item.quality, b_ilvl, dm)
        target_item.mods = new_mods
        _spend(player, recipe.cost)
        return f"Reforged {target_item.display_name}!"

    if recipe.result_type == "add_slot":
        if target_item is None:
            raise ValueError("No target item selected")
        if target_item.enchant_slots >= 3:
            raise ValueError("Item already has 3 slots")
        target_item.enchant_slots += 1
        _spend(player, recipe.cost)
        return f"Added slot to {target_item.display_name}!"

    if recipe.result_type == "potion":
        from src.items.item import HealthPotion as HP
        pot = HP(0, 0, random.randint(35, 55))
        player.add_item(pot)
        _spend(player, recipe.cost)
        return "Crafted a Health Potion!"

    # equip result
    slot = recipe.result_slot
    if slot == "jewel":
        slot = random.choice([SLOT_RING, SLOT_AMULET])
    elif slot == "armour":
        slot = random.choice(_ARMOUR_SLOT_POOL)

    ilvl, depth_mult = _ilvl_and_mult(recipe.result_ilvl)
    item = random_equip(0, 0, ilvl,
                        quality=recipe.result_quality,
                        slot=slot,
                        depth_mult=depth_mult)
    player.add_item(item)
    _spend(player, recipe.cost)
    return f"Crafted {item.display_name}!"


def _spend(player, cost: dict[str, int]):
    mats = getattr(player, "materials", {})
    for mat, qty in cost.items():
        mats[mat] = mats.get(mat, 0) - qty
    player.materials = mats
