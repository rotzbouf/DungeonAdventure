"""
Save / load system — checkpoint save (roguelike style).

Legacy path: ~/.dungeonadventure/save.json  (migrated on first launch)
Per-hero path: ~/.dungeonadventure/saves/{hero_id}.json
"""
from __future__ import annotations

import json
import pathlib
import time

_BASE_DIR  = pathlib.Path("~/.dungeonadventure").expanduser()
SAVE_PATH  = _BASE_DIR / "save.json"          # legacy single-save
SAVES_DIR  = _BASE_DIR / "saves"              # multi-hero directory


# ── Item serialisation ────────────────────────────────────────────────────────

def item_to_dict(item) -> dict | None:
    if item is None:
        return None
    from src.items.item import HealthPotion, EquipItem
    if isinstance(item, HealthPotion):
        return {"type": "potion", "heal": item.heal_amount}
    if isinstance(item, EquipItem):
        return {
            "type":          "equip",
            "base_name":     item.base_name,
            "quality":       item.quality,
            "unique_name":   item.unique_name,
            "flavor":        item.flavor,
            "rare_name":     item.rare_name,
            "base_stat":     item.base_stat,
            "enchant_slots": item.enchant_slots,
            "enchantments":  list(item.enchantments),
            "mods": [
                {
                    "kind":      m.kind,
                    "value":     m.value,
                    "name":      getattr(m, "name", ""),
                    "is_prefix": getattr(m, "is_prefix", False),
                    "is_suffix": getattr(m, "is_suffix", False),
                }
                for m in item.mods
            ],
        }
    return None


def item_from_dict(data: dict | None):
    if not data:
        return None
    from src.items.item import HealthPotion, EquipItem, Modifier
    kind = data.get("type")
    if kind == "potion":
        return HealthPotion(0, 0, data["heal"])
    if kind == "equip":
        mods = []
        for md in data.get("mods", []):
            m = Modifier(md["kind"], md["value"])
            m.name       = md.get("name", "")         # type: ignore[attr-defined]
            m.is_prefix  = md.get("is_prefix", False)  # type: ignore[attr-defined]
            m.is_suffix  = md.get("is_suffix", False)  # type: ignore[attr-defined]
            mods.append(m)
        item = EquipItem(
            0, 0,
            base_name=data["base_name"],
            quality=data["quality"],
            mods=mods,
            unique_name=data.get("unique_name", ""),
            flavor=data.get("flavor", ""),
        )
        item.base_stat     = data.get("base_stat", item.base_stat)
        item.rare_name     = data.get("rare_name", "")
        item.enchant_slots = data.get("enchant_slots", 0)
        item.enchantments  = data.get("enchantments", [])
        return item
    return None


# ── Legacy compatibility ──────────────────────────────────────────────────────

def has_save() -> bool:
    """True if any save exists (hero or legacy)."""
    if SAVES_DIR.exists() and any(SAVES_DIR.glob("*.json")):
        return True
    return SAVE_PATH.exists()


def delete_save():
    SAVE_PATH.unlink(missing_ok=True)


def migrate_legacy_save():
    """Move ~/.dungeonadventure/save.json → saves/legacy.json (once)."""
    if not SAVE_PATH.exists():
        return
    legacy_path = SAVES_DIR / "legacy.json"
    if legacy_path.exists():
        return
    SAVES_DIR.mkdir(parents=True, exist_ok=True)
    data = json.loads(SAVE_PATH.read_text())
    data.setdefault("hero_id",    "legacy")
    data.setdefault("hero_name",  "Hero")
    data.setdefault("hero_class", "warrior")
    data.setdefault("gender",     "male")
    data.setdefault("last_played", time.time())
    legacy_path.write_text(json.dumps(data, indent=2))
    SAVE_PATH.unlink(missing_ok=True)


# ── Multi-hero API ────────────────────────────────────────────────────────────

def list_heroes() -> list[dict]:
    """Return hero summary dicts sorted newest-first.  Empty list if none."""
    if not SAVES_DIR.exists():
        return []
    heroes = []
    for p in SAVES_DIR.glob("*.json"):
        try:
            d = json.loads(p.read_text())
            heroes.append({
                "hero_id":    d.get("hero_id", p.stem),
                "hero_name":  d.get("hero_name", "Hero"),
                "hero_class": d.get("hero_class", "warrior"),
                "gender":     d.get("gender", "male"),
                "level":      d.get("level", 1),
                "dungeon_level": d.get("dungeon_level", 1),
                "last_played":   d.get("last_played", 0.0),
            })
        except Exception:
            pass
    heroes.sort(key=lambda h: h["last_played"], reverse=True)
    return heroes


def has_hero(hero_id: str) -> bool:
    return (SAVES_DIR / f"{hero_id}.json").exists()


def delete_hero(hero_id: str):
    (SAVES_DIR / f"{hero_id}.json").unlink(missing_ok=True)


def load_hero(hero_id: str) -> dict | None:
    p = SAVES_DIR / f"{hero_id}.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


# ── Save / restore ────────────────────────────────────────────────────────────

def save_game(player, dungeon_level: int, ng_plus: int = 0,
              quest_log=None, skill_tree=None):
    """Persist the current game state to disk."""
    hero_id = getattr(player, "hero_id", "")
    data = {
        "version":       3,
        "dungeon_level": dungeon_level,
        "ng_plus":       ng_plus,
        # ── Hero identity ──
        "hero_id":    hero_id,
        "hero_name":  getattr(player, "name",       "Hero"),
        "hero_class": getattr(player, "hero_class", "warrior"),
        "gender":     getattr(player, "gender",     "male"),
        "last_played": time.time(),
        # ── Player core ──
        "level":         player.level,
        "xp":            player.xp,
        "xp_to_next":    player.xp_to_next,
        "hp":            player.hp,
        "max_hp":        player.max_hp,
        "mana":          player.mana,
        "max_mana":      player.max_mana,
        "gold":          player.gold,
        "materials":       dict(getattr(player, "materials", {})),
        "defeated_bosses": list(getattr(player, "defeated_bosses", set())),
        "perks":           list(getattr(player, "perks", [])),
        # ── D2 stats ──
        "str_pts":       player.str_pts,
        "dex_pts":       player.dex_pts,
        "vit_pts":       player.vit_pts,
        "ene_pts":       player.ene_pts,
        "stat_points":   player.stat_points,
        # ── Inventory ──
        "potions":  [{"heal": p.heal_amount} for p in player.potions],
        "backpack":  [d for d in (item_to_dict(i) for i in player.backpack) if d],
        "stash":     [d for d in (item_to_dict(i) for i in getattr(player, "stash", [])) if d],
        "equipment": {
            slot: item_to_dict(it)
            for slot, it in player.equipment.items()
        },
        # ── Skills / Quests ──
        "skills":  skill_tree.to_dict() if skill_tree else {},
        "quests":  quest_log.to_dict() if quest_log else {},
    }
    if hero_id:
        SAVES_DIR.mkdir(parents=True, exist_ok=True)
        (SAVES_DIR / f"{hero_id}.json").write_text(json.dumps(data, indent=2))
    else:
        # Fallback: legacy path (should not happen for new heroes)
        SAVE_PATH.parent.mkdir(parents=True, exist_ok=True)
        SAVE_PATH.write_text(json.dumps(data, indent=2))


def load_game() -> dict | None:
    """Load the most-recently-played hero, or the legacy save."""
    heroes = list_heroes()
    if heroes:
        return load_hero(heroes[0]["hero_id"])
    if not SAVE_PATH.exists():
        return None
    try:
        return json.loads(SAVE_PATH.read_text())
    except Exception:
        return None


def restore_player(player, data: dict):
    """Overwrite player fields from a saved-data dict."""
    from src.items.item import HealthPotion
    player.level       = data["level"]
    player.xp          = data["xp"]
    player.xp_to_next  = data["xp_to_next"]
    player.max_hp      = data.get("max_hp",   player.max_hp)
    player.max_mana    = data.get("max_mana", player.max_mana)
    player.hp          = min(data["hp"],  float(player.max_hp))
    player.mana        = min(data["mana"], float(player.max_mana))
    player.gold        = data["gold"]
    player.materials       = dict(data.get("materials", {}))
    player.defeated_bosses = set(data.get("defeated_bosses", []))
    player.perks           = list(data.get("perks", []))
    player.str_pts     = data["str_pts"]
    player.dex_pts     = data["dex_pts"]
    player.vit_pts     = data["vit_pts"]
    player.ene_pts     = data["ene_pts"]
    player.stat_points = data["stat_points"]

    player.name       = data.get("hero_name",  getattr(player, "name",       "Hero"))
    player.hero_class = data.get("hero_class",  getattr(player, "hero_class", "warrior"))
    player.gender     = data.get("gender",      getattr(player, "gender",     "male"))
    player.hero_id    = data.get("hero_id",     getattr(player, "hero_id",    ""))

    player.potions = [HealthPotion(0, 0, pd["heal"])
                      for pd in data.get("potions", [])]

    player.backpack = [it for it in
                       (item_from_dict(d) for d in data.get("backpack", []))
                       if it is not None]
    player.stash    = [it for it in
                       (item_from_dict(d) for d in data.get("stash", []))
                       if it is not None]

    for slot, idata in data.get("equipment", {}).items():
        if slot in player.equipment:
            player.equipment[slot] = item_from_dict(idata)
