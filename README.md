# Dungeon Adventure

A procedurally generated dungeon crawler built with Python and pygame.
Fight your way through five floors of increasingly dangerous enemies,
collect loot, level up your character, and descend into New Game Plus
for harder runs with new tile themes.

---

## Features

### Dungeon & World
- BSP-based procedural generation — no two floors are the same
- Five themed tile sets: **Dungeon** → **Crypt** → **Forge** → **Inferno** → **Abyss** (NG+)
- Spike traps on corridor tiles, treasure chests in rooms
- Minimap with colour-coded dots for player, enemies, merchants, chests and stairs

### Enemies
| Enemy | Notes |
|-------|-------|
| Goblin | Fast, weak — appears from floor 1 |
| Skeleton | Slows on hit — floor 2+ |
| Orc | Armoured tank — floor 3+ |
| Demon | High speed + damage — floor 4+ |
| **Elite** | Any enemy can spawn as an elite variant: bigger, pulsing gold aura, drops better loot, applies Poison on hit |

### Player Progression
- **Levels 1–20** with XP earned from kills and completed quests
- **D2-style core attributes** — spend 5 stat points per level:
  - STR → Attack · DEX → Defense + Crit · VIT → Max Life · ENE → Max Mana
- **Skill tree** — three branches, 12 skills, 1 skill point per level

| Branch | Skills |
|--------|--------|
| Combat | Power Strike · Toughness · Battle Cry · Whirlwind |
| Magic | Fireball Mastery · Arcane Mind · Ice Nova · Chain Lightning |
| Rogue | Critical Mastery · Evasion · Poison Blade · Shadow Step |

### Spells & Actives
| Key | Skill | Description |
|-----|-------|-------------|
| `Z` | Fireball | AoE explosion; unlocked from the start |
| `X` | Ice Nova | Burst around player, slows enemies (requires Ice Nova skill) |
| `R` | Chain Lightning | Jumps between up to 4 enemies (requires Chain Lightning skill) |
| `V` | Blink | Teleport to cursor (requires Shadow Step skill) |
| `B` | Battle Cry | +25–55% melee damage for 5 s (requires Battle Cry skill) |
| `Shift+Space` | Whirlwind | 360° melee sweep (requires Whirlwind skill) |

### Loot System
Four quality tiers with colour-coded names and ground glow:

| Quality | Colour | Notes |
|---------|--------|-------|
| Normal | Grey | Base stats only |
| Magic | Blue | 1–2 random affixes |
| Rare | Yellow | 3–5 random affixes, randomised name |
| Unique | Gold | Fixed affixes, flavour text, unique name |

Fourteen equipment slots (weapon, shield, helm, chest, gloves, boots, belt, two rings, amulet).
Modifier types include ATK, DEF, Max HP, Max Mana, Crit, Life Steal, Thorns, Speed, Gold Find, HP Regen, and Attack Speed.

### Other Systems
- **Merchants** — rare find (~28–60% chance per floor, scaling with depth); buy equipment and potions with `F`
- **Quest log** — 2–3 quests per floor (kill, collect gold, descend); rewards XP and gold
- **Status effects** — Poison (DoT), Burn (DoT), Slow (speed −40%), Freeze (speed −45%)
- **Checkpoint saves** — auto-saved on stair descent to `~/.dungeonadventure/save.json`, deleted on death; continue from the title screen
- **New Game Plus** — completing floor 5 loops back to floor 1 with scaled enemies and a new tile theme

---

## Controls

| Key / Input | Action |
|-------------|--------|
| `WASD` | Move |
| Left click | Melee attack |
| Right click | Fire fireball |
| `Z` | Fireball |
| `X` | Ice Nova |
| `R` | Chain Lightning |
| `V` | Blink (teleport to cursor) |
| `B` | Battle Cry |
| `Shift+Space` | Whirlwind |
| `Q` | Use health potion |
| `F` | Open / close shop (when near a merchant) |
| `I` / `Tab` | Inventory |
| `C` | Character / stat screen |
| `K` | Skill tree |
| `J` | Quest log |
| `M` | Toggle minimap |
| `ESC` | Close overlay / quit to menu |

---

## Requirements

- Python 3.10+
- pygame 2.0+

```
pip install pygame
```

Or install into a virtual environment:

```
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

---

## Running

```
python main.py
```

---

## Building a Portable Executable

Produces a single self-contained binary in `dist/`:

```
python build.py
```

Options:

```
python build.py --clean       # wipe previous build artefacts first
python build.py --clean-only  # just clean, don't build
```

Requires PyInstaller (installed automatically if missing).
The binary bundles the Python interpreter and all pygame SDL2 libraries — no external dependencies needed to run it.

---

## Project Structure

```
main.py                  Entry point
build.py                 PyInstaller packaging script
requirements.txt
src/
  game.py                Main game loop, event handling, spell logic
  settings.py            All tunable constants
  save.py                Save / load system
  quests.py              Quest definitions and tracking
  skills.py              Skill tree definitions and SkillTree class
  entities/
    entity.py            Base class (knockback, status effects)
    player.py            Player stats, inventory, combat
    enemy.py             Enemy AI, four enemy types + elite system
    merchant.py          Merchant entity and shop inventory
  items/
    item.py              Full loot system (EquipItem, HealthPotion, GoldPile, TreasureChest)
  world/
    dungeon.py           BSP dungeon generator
    tile.py              Procedural tile renderer with five themes
  ui/
    hud.py               In-game HUD (hearts, mana, spells, status)
    inventory.py         Inventory / equipment screen
    shop.py              Shop overlay
    charscreen.py        Character / stat allocation screen
    skillscreen.py       Skill tree screen
    questlog.py          Quest log overlay
    minimap.py           Minimap renderer
  utils/
    camera.py            Smooth-follow camera
tests/                   pytest test suite (166 tests)
```

---

## License

MIT
