# Dungeon Adventure

A procedurally generated dungeon crawler built with Python and Pygame.
Fight through an endless dungeon of escalating danger — collect loot, enchant your gear,
craft materials, master a deep skill tree, and see how far you can descend.
Play solo or with up to four friends on a dedicated server.

---

## Features at a glance

| | |
|---|---|
| Endless dungeon | No floor cap — enemies and loot scale continuously |
| Power-gated bosses | Six named bosses appear based on your Combat Rating, not a fixed floor |
| D2-style loot | Normal / Magic / Rare / Unique with 60+ affixes and 25 named uniques |
| Enchantment system | 25 enchantments, 10 cross-item synergy bonuses |
| Item crafting | Workshop NPC — combine materials or disassemble gear |
| Player homestead | House in town with persistent stash chest and manual save/load |
| Dedicated multiplayer | Authoritative server, up to 4 players, all spells and floor transitions |
| Medieval visuals | Pre-baked dungeon surface, ambient occlusion, multi-source torch lighting |
| Pillow-generated assets | PNG sprite sheets for player, enemies, and town facades (beta branch) |

---

## Endless Dungeon

The dungeon has no floor cap.  Enemies scale with depth using an accelerating
formula; loot quality and affix values grow past floor 5.  Five tile themes
cycle every five floors: **Dungeon → Crypt → Forge → Inferno → Abyss**.

### Power-gated bosses

Bosses no longer spawn on a fixed interval.  Each of the six bosses has a
**Combat Rating (CR) window**.  When your CR falls inside that window there is a
random per-floor chance of a spawn.  Your CR is:

```
CR = level × 12  +  floor × 3  +  gear_score
gear_score: Normal 0 / Magic 3 / Rare 8 / Unique 20 per equipped slot
```

| Boss | CR window | Min floor | Spawn chance |
|------|-----------|-----------|-------------|
| **Lich** | 45 – 140 | 3 | 30 %/floor |
| **Demon Lord** | 90 – 220 | 6 | 28 % |
| **Stone Golem** | 155 – 310 | 9 | 25 % |
| **Vampire Lord** | 230 – 400 | 13 | 22 % |
| **Elder Dragon** | 320 – 530 | 18 | 20 % |
| **Iron Colossus** | 440 + | 24 | 18 % |

- CR above a boss's maximum → window closes; that boss is **permanently skipped**
  for players who outlevel it (incentivises playing in-range)
- After 9 floors past the boss's minimum without a spawn the game **force-spawns**
  it regardless of luck (prevents infinite avoidance)
- Defeated bosses are tracked; once all six are killed the cycle resets on deeper
  floors (bosses scale via `scale_to_level`)
- Killing a boss drops a guaranteed **Unique** item, two **Rare** items, and a gold
  pile

---

## Town Hub

A hand-drawn medieval town with six permanent merchants, a stone fountain,
corner towers, and a portcullis gate leading to the dungeon.

| NPC | Specialty |
|-----|-----------|
| **Blacksmith** | Weapons (melee and bows) |
| **Armourer** | Armour slots |
| **Jeweler** | Rings and amulets |
| **Alchemist** | Potions and mixed gear |
| **Enchanter** | Apply enchantments to items with open slots |
| **Craftsman** | Craft items from materials / disassemble gear |

Press **F** near any NPC to open their screen.

### Your Homestead

A cozy cottage on the right side of town.  Press **F** near the front door to open it.

- **Stash chest** — up to 80 items stored permanently across saves
- **Save Game** button — manual checkpoint at any time
- **Load Game** button — reload the last checkpoint

---

## Crafting & Disassembly

Visit the **Craftsman** (Workshop) to:

- **Craft** potions, Magic/Rare/Unique gear, or use special recipes:
  - *Reforge* — reroll all affixes on a Rare or Unique item
  - *Add Slot* — add an enchantment slot to any item
- **Disassemble** backpack items into five material types:
  `Scrap Metal · Mana Shard · Ether Dust · Rune Fragment · Void Crystal`

Material yields scale with item quality and enchantment slots.

---

## Enchantment System

Items occasionally drop with **enchantment slots** (very rare — most have none).
Visit the **Enchanter** to fill them with one of 25 enchantments.

### Slot chances by quality

| Quality | 0 slots | 1 slot | 2 slots | 3 slots |
|---------|---------|--------|---------|---------|
| Normal | 98 % | 2 % | — | — |
| Magic | 92 % | 7 % | 1 % | — |
| Rare | 82 % | 14 % | 3 % | 1 % |
| Unique | — | 40 % | 45 % | 15 % |

### Synergies

When two equipped items share certain enchantment tag pairs a **synergy bonus**
activates automatically.  Ten combinations:

| Synergy | Bonus |
|---------|-------|
| Blood Frenzy | +15 % dmg, +3 % life steal |
| Iron Fortress | +15 def, +15 thorns |
| Undying | +40 HP, +1.5 regen/s |
| Killing Blow | +8 % crit, +10 % dmg |
| Phantom | +10 % speed, +10 % atk spd |
| Abyssal | +40 atk, +25 % dmg, −30 HP |
| Spellblade | +20 atk, +15 mana |
| Treasure Hunter | +30 % gold find, +5 % crit |
| Berserker | +12 % atk spd, +12 % dmg |
| Predator | +5 % life steal, +18 atk |

---

## Player Progression

- **Levels 1 – 20** — XP from kills and quests
- **5 stat points per level** — allocate via `C`

| Stat | Effect per point |
|------|-----------------|
| STR | +2 Attack |
| DEX | +1 Defense, +0.5 % Crit |
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

- **Space** — melee attack, or **fire arrow** when a bow is equipped
- Equipping a bow replaces melee; DEX boosts arrow damage
- Arrows travel toward the cursor; AoE spells auto-target or centre on player

### Spells

| Key | Spell | Description |
|-----|-------|-------------|
| `Z` | Fireball | Auto-targets nearest enemy; AoE explosion with burn |
| `X` | Ice Nova | Burst around player — freezes all nearby enemies |
| `R` | Chain Lightning | Jumps between up to 4 enemies, −30 % per jump |
| `V` | Blink | Teleport toward cursor |
| `B` | Battle Cry | +25 – 55 % melee damage for 5 s |
| `Shift+Space` | Whirlwind | 360° sweep (requires skill) |

### Status effects

Poison · Burn · Slow · Freeze

---

## Multiplayer

### Dedicated server (headless)

```bash
python server.py                                  # localhost:5555, floor 1
python server.py --host 0.0.0.0 --port 5555
python server.py --floor 3 --seed 42
python server.py --max-players 4
```

Runs without a display on any Linux server.  Use `screen` / `tmux` / systemd.

### Connect as a client

```bash
python main.py --connect localhost:5555 --name Hero
python main.py --connect 192.168.1.10:5555 --name Wizard
```

Your local save file is sent to the server so your real character — including
equipment and stat bonuses — is used in multiplayer.

### What works in multiplayer

- All movement and melee / bow attacks
- All six spells (fireball, ice nova, chain lightning, blink, battle cry, whirlwind)
- Power-gated bosses (based on the strongest player's CR)
- Floor transitions — any player reaching the stairs moves everyone
- Town mode — press `T` to visit town while others stay in the dungeon
- Loot, gold, and chests are all server-authoritative

---

## Visual System

### Dungeon rendering

- Entire dungeon pre-baked to a single surface at floor load (~80 ms) for
  fast per-frame blitting
- **Ambient occlusion** — floor tiles adjacent to walls receive gradient shadow
  strips for convincing depth without shaders
- **Wall sconces** — ~22 % of south-facing walls get iron brackets and animated
  torch flames
- **Decorative props** — rubble piles, bone clusters, barrels/crates scattered
  deterministically per seed

### Lighting

Three light-source types accumulate in the fog layer:

- **Player torch** — large warm amber glow, flickering
- **Sconce lights** — smaller radius, each with a unique flicker phase
- **Stairs portal** — cool golden pulse

Per-floor ambient darkness is tinted by theme (blue in dungeon, red in forge, teal in abyss).

### Sprites (beta branch)

The `beta` branch includes Pillow-generated PNG assets that override the
procedural pygame drawing when present.  Run the generator once:

```bash
pip install Pillow
python tools/generate_assets.py
```

Assets generated:
- `assets/tiles/` — floor and wall textures for all five themes (noise-based)
- `assets/sprites/` — directional player knight + Goblin, Skeleton, Orc, Demon
- `assets/town/` — building facade textures per merchant specialty

The game falls back to procedural drawing automatically if assets are absent.

---

## Controls

### Town

| Key | Action |
|-----|--------|
| `WASD` | Move |
| `E` | Enter dungeon |
| `F` | Interact (shop, enchant, craft, homestead) |
| `I` / `Tab` | Inventory |
| `C` | Character screen |
| `K` | Skill tree |
| `ESC` | Main menu |

### Dungeon

| Key | Action |
|-----|--------|
| `WASD` | Move |
| `Space` | Attack / Fire arrow |
| `Shift+Space` | Whirlwind |
| `Z / X / R / V / B` | Spells |
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

Progress auto-saves on stair descent and when returning to town.
The save is **deleted on death** — permadeath.
Manual saves are available any time from the **Homestead** in town.

---

## Requirements

- Python 3.10+
- pygame ≥ 2.6.0
- Pillow ≥ 10.0.0 *(only required to regenerate assets)*

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

---

## Multiplayer quick-start

```bash
# Terminal 1 — server
pip install -r requirements.txt
python server.py --port 5555

# Terminal 2 — client
python main.py --connect localhost:5555 --name YourName
```

---

## Building a portable executable

```bash
python build.py           # produces dist/ binary
python build.py --clean   # wipe previous artefacts first
```

Requires PyInstaller (installed automatically if missing).

---

## Project structure

```
main.py                    Entry point (--connect HOST:PORT for multiplayer)
server.py                  Dedicated headless server
build.py                   PyInstaller packaging
requirements.txt
tools/
  generate_assets.py       Pillow asset generator (sprites, tiles, facades)
assets/
  sprites/                 Player + enemy PNG sprites
  tiles/                   Floor/wall textures per theme
  town/                    Building facade textures
src/
  game.py                  Orchestrator: init, run, events, update, draw
  settings.py              All tunable constants
  save.py                  Checkpoint save / load (permadeath)
  boss_pool.py             Power-gated boss schedule, CR formula, pick_boss()
  quests.py                Quest definitions and tracking
  skills.py                Skill tree definitions
  locale.py                EN / DE localisation
  assets.py                PNG asset loader with procedural fallback
  game_layers/
    session.py             Level loading, save/load, descend, quest rewards
    town.py                Town enter/exit, shop routing
    combat.py              Melee, arrows, whirlwind, hit resolution, loot
    spells.py              All six spells
    projectiles.py         Projectile update and rendering
    particles.py           Particle system
    traps.py               Spike traps
    renderer.py            World render, multi-source fog, boss bar, menus
  entities/
    player.py              Stats, equipment, skill bonuses, directional sprite
    enemy.py               AI, four enemy types, elite system, six boss classes
    merchant.py            Dungeon Merchant + TownMerchant (six specialists)
  items/
    item.py                Loot system (EquipItem, HealthPotion, GoldPile …)
    enchant.py             Enchantment registry, synergy table, slot rolling
    materials.py           Material types, recipes, execute_recipe(), disassemble()
  world/
    dungeon.py             BSP generator, pre-baked surface, AO, props, sconces
    tile.py                Procedural + PNG tile renderer, five themes
    town.py                Town layout, buildings, fountain, TownRenderer
  ui/
    hud.py                 HUD (HP/MP/XP bars, spells, notifications)
    inventory.py           Inventory and equipment screen
    shop.py                Shop overlay
    enchant_screen.py      Enchantment Forge overlay
    craft_screen.py        Workshop overlay (craft + disassemble tabs)
    house_screen.py        Homestead overlay (stash + save/load)
    charscreen.py          Character / stat allocation screen
    skillscreen.py         Skill tree screen
    questlog.py            Quest log overlay
    minimap.py             Minimap renderer
  network/
    protocol.py            Length-prefixed JSON framing
    server.py              Headless authoritative game server (asyncio)
    client.py              Thread-safe client + GhostEnemy/RemotePlayer proxies
  utils/
    camera.py              Smooth-follow camera
tests/                     pytest suite (178 tests)
```

---

## License

MIT
