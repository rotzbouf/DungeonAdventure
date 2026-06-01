# Dungeon Adventure

A procedurally generated dungeon crawler built with Python and pygame.
Fight through an endless dungeon of escalating danger — collect loot, enchant your gear,
master a deep skill tree, and see how far you can descend.

---

## Features

### Endless Dungeon

The dungeon has no floor cap. Enemies scale with depth using an accelerating formula,
loot quality and affix values grow past floor 5, and a named boss spawns every 20 floors.
The further you go, the harder it gets — and the better the rewards.

### Floor Bosses

Every 20th floor spawns a unique named boss in the deepest room. Six bosses rotate in sequence:

| Boss | HP | Notes |
|------|----|-------|
| **Lich** | 450 | Fast spellcaster |
| **Demon Lord** | 650 | High attack, charge |
| **Stone Golem** | 950 | Enormous defence |
| **Vampire Lord** | 900 | Life-steal on hit |
| **Elder Dragon** | 1400 | Massive, hard-hitting |
| **Iron Colossus** | 1800 | Highest defence in the game |

Killing a boss drops a guaranteed Unique item, two Rare items, and a pile of gold.

### Town Hub

Every run starts and ends in a cobblestone town square with five permanent specialist
merchants, a central well, and a dungeon-entrance archway at the top.

- Entering town **fully restores HP and mana**
- Press **T** anywhere in the dungeon to save and return to town
- Press **E** near the archway to enter (or re-enter) the dungeon
- Merchant stock **refreshes each visit** and scales with your level

| Merchant | Sells |
|----------|-------|
| **Blacksmith** | Weapons (melee and bows) |
| **Armourer** | Shield, helm, chest, gloves, boots, belt |
| **Jeweler** | Rings and amulets |
| **Alchemist** | Potions + mixed gear |
| **Enchanter** | Apply enchantments to items with open slots |

### Dungeon & World

- BSP-based procedural generation — no two floors are the same
- Five tile themes cycling every 5 floors: **Dungeon → Crypt → Forge → Inferno → Abyss**
- Spike traps on corridor tiles, treasure chests in rooms
- Minimap with colour-coded dots for player, enemies, merchants, chests, and stairs
- Torch-lit fog of war with animated warm vignette

### Travelling Merchants (dungeon)

Rare lucky find — ~10–16% chance per floor, at most one.
When found, they carry **only Rare and Unique items** at **2.5× price**.

### Enemies

| Enemy | Notes |
|-------|-------|
| Goblin | Fast, weak — floor 1+ |
| Skeleton | Slows on hit — floor 2+ |
| Orc | Armoured tank — floor 3+ |
| Demon | High speed + damage — floor 4+ |
| **Elite** | Any enemy can be elite: bigger, gold aura, better loot, applies Poison |

---

## Loot System

Four quality tiers with colour-coded names and ground glow:

| Quality | Colour | Notes |
|---------|--------|-------|
| Normal | Grey | Base stats only |
| Magic | Blue | 1–2 random affixes |
| Rare | Yellow | 3–5 random affixes, randomised name |
| Unique | Gold | Fixed affixes, flavour text, unique name |

Ten equipment slots: weapon, shield, helm, chest, gloves, boots, belt, two rings, amulet.

Modifier types: ATK, ATK%, DEF, Max HP, Max Mana, Crit, Life Steal, Thorns, Speed, Gold Find, HP Regen, Attack Speed.

**Depth scaling** — from floor 6 onward, affix rolls scale upward (up to ×2.0 at floor 30+),
and the quality table extends to item level 10 giving much higher Rare and Unique drop rates.

---

## Enchantment System

Items occasionally drop with **enchantment slots** (very rare — most items have none).
Visit the **Enchanter** in town to fill them.

### Slot chances by quality

| Quality | 0 slots | 1 slot | 2 slots | 3 slots |
|---------|---------|--------|---------|---------|
| Normal | 98% | 2% | — | — |
| Magic | 92% | 7% | 1% | — |
| Rare | 82% | 14% | 3% | 1% |
| Unique | — | 40% | 45% | 15% |

### Enchantments (25 total, 5 rarity tiers)

| Rarity | Examples |
|--------|---------|
| Common | Bloodrage, Rending, Bulwark, Vitality, Swiftness |
| Uncommon | Shatter, Frenzy, Mending, Retribution, Gilded |
| Rare | Arcane Surge, Overcharge, Venomous, Lucky, Fleetfoot |
| Very Rare | Ancient Power, Ancient Might, Ethereal |
| Legendary | Cursed, Demonic, Worldbreaker |

### Synergies

When two equipped items share enchantment tag pairs, a **synergy bonus** activates automatically
across your entire stat sheet — no action required. Ten synergy combinations:

| Synergy | Tags | Bonus |
|---------|------|-------|
| Blood Frenzy | assault + blood | +15% dmg, +3% life steal |
| Iron Fortress | ward + iron | +15 def, +15 thorns |
| Undying | ward + life | +40 HP, +1.5 regen/s |
| Killing Blow | assault + precise | +8% crit, +10% dmg |
| Phantom | shadow + speed | +10% speed, +10% atk spd |
| Abyssal | ancient + cursed | +40 atk, +25% dmg, −30 HP |
| Spellblade | arcane + power | +20 atk, +15 mana |
| Treasure Hunter | fortune + gold | +30% gold find, +5% crit |
| Berserker | assault + speed | +12% atk spd, +12% dmg |
| Predator | shadow + blood | +5% life steal, +18 atk |

---

## Player Progression

- **Levels 1–20** — XP from kills and quests
- **5 stat points per level** — allocate via the character screen (`C`)

| Stat | Effect per point above floor |
|------|------------------------------|
| STR | +2 Attack |
| DEX | +1 Defense, +0.5% Crit |
| VIT | +10 Max HP |
| ENE | +5 Max Mana |

### Skill Tree — 3 branches, 12 skills, 1 point per level

| Branch | Skills |
|--------|--------|
| Combat | Power Strike · Toughness · Battle Cry · Whirlwind |
| Magic | Fireball Mastery · Arcane Mind · Ice Nova · Chain Lightning |
| Rogue | Critical Mastery · Evasion · Poison Blade · Shadow Step |

---

## Combat

### Melee & Ranged

- **Space** — melee attack (default), or **fire arrow** when a bow is equipped
- Equipping a bow (Short Bow / Long Bow / Hunter's Bow / War Bow / Crossbow) replaces
  your melee attack; DEX boosts arrow damage via the `bow_attack` stat
- Arrows travel in a straight line toward the cursor and pierce based on range

### Spells & Actives

| Key | Skill | Description |
|-----|-------|-------------|
| `Z` | Fireball | AoE explosion at cursor; always available |
| `X` | Ice Nova | Burst around player, slows all nearby enemies |
| `R` | Chain Lightning | Jumps between up to 4 enemies, −30% per jump |
| `V` | Blink | Teleport to cursor position |
| `B` | Battle Cry | +25–55% melee damage for 5 s |
| `Shift+Space` | Whirlwind | 360° melee sweep (requires Whirlwind skill) |

### Status Effects

Poison · Burn · Slow · Freeze

---

## Quest System

Each floor offers a guaranteed **descent quest** plus two random quests (kill enemies / collect gold).
Completing quests rewards XP and gold. Progress carries across descents.

---

## Controls

### Town

| Key | Action |
|-----|--------|
| `WASD` | Move |
| `E` | Enter dungeon (near the archway) |
| `F` | Open shop / Enchantment Forge (near a merchant) |
| `I` / `Tab` | Inventory |
| `C` | Character screen |
| `K` | Skill tree |
| `ESC` | Main menu |

### Dungeon

| Key | Action |
|-----|--------|
| `WASD` | Move |
| `Space` | Melee attack / Fire arrow (if bow equipped) |
| `Z` | Fireball |
| `X` | Ice Nova |
| `R` | Chain Lightning |
| `V` | Blink |
| `B` | Battle Cry |
| `Shift+Space` | Whirlwind |
| `Q` | Use health potion |
| `E` | Descend stairs |
| `T` | Return to town (saves) |
| `F` | Open travelling merchant |
| `I` / `Tab` | Inventory |
| `C` | Character screen |
| `K` | Skill tree |
| `J` | Quest log |
| `ESC` | Main menu |

---

## Saves

Progress is auto-saved on stair descent and when returning to town.
The save is **deleted on death** — permadeath.

---

## Requirements

- Python 3.10+
- pygame 2.0+

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

---

## Project Structure

```
main.py                    Entry point
build.py                   PyInstaller packaging script
requirements.txt
src/
  game.py                  Orchestrator: __init__, run, events, update, draw
  settings.py              All tunable constants
  save.py                  Checkpoint save / load (permadeath)
  quests.py                Quest definitions and tracking
  skills.py                Skill tree definitions and SkillTree class
  locale.py                EN/DE localisation
  game_layers/             Game logic split into focused mixin layers
    session.py             Level loading, save/load, descend, quest rewards
    town.py                Town enter/exit, shop routing, town draw
    combat.py              Melee, arrows, whirlwind, hit resolution, loot
    spells.py              Fireball, ice nova, chain lightning, blink, battle cry
    projectiles.py         Projectile update and rendering
    particles.py           Particle spawn, update, rendering
    traps.py               Spike trap logic and rendering
    renderer.py            World render, fog, boss bar, menus, item labels
  entities/
    entity.py              Base entity (knockback, status effects)
    player.py              Player stats, equipment, combat, synergy bonuses
    enemy.py               Enemy AI, four types, elite system, six boss classes
    merchant.py            Dungeon Merchant + TownMerchant (five specialists)
  items/
    item.py                Loot system (EquipItem, HealthPotion, GoldPile, TreasureChest)
    enchant.py             Enchantment registry, synergy table, slot rolling
  world/
    dungeon.py             BSP dungeon generator
    tile.py                Procedural tile renderer with five themes
    town.py                Town layout, TownBounds, TownRenderer
  ui/
    hud.py                 HUD (gradient HP/MP/XP bars, spells, status)
    inventory.py           Inventory and equipment screen
    shop.py                Shop overlay
    enchant_screen.py      Enchantment Forge overlay
    charscreen.py          Character / stat allocation screen
    skillscreen.py         Skill tree screen
    questlog.py            Quest log overlay
    minimap.py             Minimap renderer
  utils/
    camera.py              Smooth-follow camera
tests/                     pytest suite (166 tests)
```

---

## License

MIT
