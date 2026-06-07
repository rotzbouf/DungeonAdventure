# Dungeon Adventure

A procedurally generated dungeon crawler built with Python and Pygame.
Fight through an endless dungeon of escalating danger — collect loot, enchant your gear,
craft materials, master a deep skill tree, and see how far you can descend.
Play solo or with up to four friends on a dedicated server.

**Current version: 0.4.1**

---

## Features at a glance

| | |
|---|---|
| Multiple heroes | Create and manage several heroes, each with a separate save |
| Endless dungeon | No floor cap — enemies and loot scale continuously |
| Power-gated bosses | Six named bosses appear based on your Combat Rating, not a fixed floor |
| Three character classes | Warrior, Mage, Rogue — distinct starting stats and playstyles |
| D2-style loot | Normal / Magic / Rare / Unique with 60+ affixes and 55 named uniques |
| Enchantment system | 25 enchantments, 10 cross-item synergy bonuses |
| Item crafting | Workshop NPC — combine materials or disassemble gear |
| Milestone perks | Pick one of three perks every 5 levels (20 perks across 4 tiers) |
| Skill tree | 24 skills across 3 branches and 4 tiers — one point per level |
| Player homestead | House in town with persistent stash chest |
| Dedicated multiplayer | Authoritative server, up to 4 players, all spells and floor transitions |
| Medieval visuals | Pre-baked dungeon surface, ambient occlusion, multi-source torch lighting |
| EN / DE localisation | Full German translation |

---

## Heroes & Character Creation

From the main menu choose **NEW HERO** to create a fresh character or **LOAD HERO** to
pick from your existing roster.

### Character creation

- **Name** your hero (up to 20 characters)
- **Choose a class** — each has a fixed starting stat spread:

| Class | STR | DEX | VIT | ENE | Playstyle |
|-------|-----|-----|-----|-----|-----------|
| Warrior | 14 | 4 | 12 | 2 | Tanky melee — high damage and survivability |
| Mage | 3 | 4 | 8 | 17 | Arcane caster — spell-dependent, fragile |
| Rogue | 7 | 15 | 7 | 3 | Critical striker — fast, evasive, burst damage |

- **Select gender** and **appearance** (DCSS-sourced portrait sprites)

### Multi-hero saves

Each hero has an independent save file in `~/.dungeonadventure/saves/`.
The hero select screen shows level, current floor, class, and portrait for each hero.
Individual heroes can be deleted from the selection screen.
Existing single-save files are migrated automatically on first launch.

---

## Endless Dungeon

The dungeon has no floor cap. Enemies scale with depth using an accelerating
formula; loot quality and affix values grow past floor 5. Five tile themes
cycle every five floors: **Dungeon → Crypt → Forge → Inferno → Abyss**.

### Power-gated bosses

Each of the six bosses has a **Combat Rating (CR) window**. When your CR falls
inside that window there is a random per-floor chance of a spawn. Your CR is:

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

- CR above a boss's maximum → window closes; that boss is permanently skipped
- After 9 floors past a boss's minimum without a spawn the game **force-spawns** it
- Defeating all six resets the cycle on deeper floors
- Bosses drop a guaranteed **Unique**, two **Rares**, and a gold scatter

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

A cozy cottage on the right side of town. Press **F** near the front door to open it.

- **Stash chest** — up to 80 items stored permanently across sessions
- **Save Game** button — manual checkpoint at any time

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
activates automatically. Ten combinations:

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

- **Levels 1 – 40** — XP from kills and quests; XP curve: `120 × level^1.45`
- **4 stat points per level** — allocate via `C` (160 total at cap)
- **Perk pick every 5 levels** — choose one of three offered perks (20 perks, 4 tiers)

| Stat | Effect per point above base |
|------|----------------------------|
| STR | +1 Attack |
| DEX | +0.5 Defense, +0.35 % Crit |
| VIT | +8 Max HP |
| ENE | +4 Max Mana |

### Skill Tree — 3 branches, 8 skills each, 4 tiers

| Branch | Tier 1 | Tier 2 | Tier 3 | Tier 4 |
|--------|--------|--------|--------|--------|
| **Combat** | Power Strike · Toughness | Battle Cry · Iron Fist | Whirlwind · War Shout | Shield Mastery · Colossus |
| **Magic** | Arcane Mind · Fireball Mastery | Ice Nova · Mana Shield | Chain Lightning · Arcane Surge | Elemental Fury · Arcane Ascension |
| **Rogue** | Critical Mastery · Evasion | Poison Blade · Shadow Step | Knife Fan · Assassination | Shadow Arts · Death Mark |

One skill point is awarded per level. Higher tiers require a prerequisite from the tier below.

---

## Combat

### Melee & Ranged

- **Space** — melee attack, or **fire arrow** when a bow is equipped
- Equipping a bow replaces melee; DEX boosts arrow damage
- Arrows travel toward the cursor; AoE spells auto-target or centre on player
- **Elite enemies** — marked with ★ ELITE; stronger stats and better loot

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
python server.py                        # localhost:5555, floor 1
python server.py --host 0.0.0.0 --port 5555
python server.py --floor 3 --seed 42
python server.py --max-players 4
```

Runs without a display on any Linux server. Use `screen` / `tmux` / systemd.

### Connect as a client

```bash
python main.py --connect localhost:5555 --name Hero
python main.py --connect 192.168.1.10:5555 --name Wizard
```

Your local save file is sent to the server so your real character —
including equipment and stat bonuses — is used in multiplayer.

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

- Entire dungeon pre-baked to a single surface at floor load for fast per-frame blitting
- **Ambient occlusion** — floor tiles adjacent to walls receive gradient shadow strips
- **Wall sconces** — animated torch flames on ~22 % of south-facing walls
- **Decorative props** — DCSS-sourced statues, rubble, barrels, columns scattered per seed

### Lighting

Three light-source types accumulate in the fog layer:

- **Player torch** — large warm amber glow, flickering
- **Sconce lights** — smaller radius, each with a unique flicker phase
- **Stairs portal** — cool golden pulse

Per-floor ambient darkness is tinted by theme (blue in dungeon, red in forge, teal in abyss).

### Sprites

Run the asset generator once to enable PNG sprites (beta branch):

```bash
pip install Pillow
python tools/generate_assets.py
```

Assets generated:
- `assets/tiles/` — floor and wall textures for all five themes
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
| `J` | Quest log |
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
| `T` | Return to town (auto-saves) |
| `F` | Open travelling merchant |
| `I` / `Tab` | Inventory |
| `C` | Character screen |
| `K` | Skill tree |
| `J` | Quest log |
| `ESC` | Main menu |

Keys are fully rebindable in **Settings**.

---

## Saves

Progress auto-saves on stair descent and when returning to town.
Each hero's save is stored in `~/.dungeonadventure/saves/{hero_id}.json` and
**deleted on death** — permadeath per hero.
Manual saves are available any time from the **Homestead** in town.

---

## Requirements

- Python 3.10+
- pygame ≥ 2.6.1
- Pillow ≥ 12.0.0 *(only required to regenerate assets)*

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
  Dungeon Crawl Stone Soup Full/   DCSS sprite bundle (portraits, decorations)
src/
  game.py                  Orchestrator: init, run, events, update, draw
  settings.py              All tunable constants
  save.py                  Per-hero checkpoint save / load (permadeath)
  hero_classes.py          Class definitions (Warrior / Mage / Rogue)
  boss_pool.py             Power-gated boss schedule, CR formula, pick_boss()
  quests.py                Quest definitions and tracking
  skills.py                Skill tree definitions (24 skills, 3 branches, 4 tiers)
  locale.py                EN / DE localisation
  assets.py                PNG asset loader with procedural fallback
  game_layers/
    session.py             Level loading, hero create/load, descend, quest rewards
    town.py                Town enter/exit, NPC routing
    combat.py              Melee, arrows, whirlwind, hit resolution, loot
    spells.py              All six spells
    projectiles.py         Projectile update and rendering
    particles.py           Particle system
    renderer.py            World render, multi-source fog, boss bar, menus
  entities/
    player.py              Stats, equipment, skill bonuses, directional sprite
    enemy.py               AI, enemy types, elite system, six boss classes
    merchant.py            Dungeon Merchant + TownMerchant (six specialists)
    wanderer.py            Quest-giver NPC system
  items/
    item.py                Loot system (EquipItem, HealthPotion, GoldPile …)
    enchant.py             Enchantment registry, synergy table, slot rolling
    materials.py           Material types, recipes, execute_recipe(), disassemble()
  world/
    dungeon.py             BSP generator, pre-baked surface, AO, props, sconces
    tile.py                Procedural + PNG tile renderer, five themes
    town.py                Town layout, buildings, fountain, TownRenderer
    decorations.py         DCSS decoration placement
  ui/
    hud.py                 HUD (HP/MP/XP bars, spells, notifications)
    hero_select.py         Hero selection screen
    char_create.py         Character creation screen
    inventory.py           Inventory and equipment screen
    shop.py                Shop overlay
    enchant_screen.py      Enchantment Forge overlay
    craft_screen.py        Workshop overlay (craft + disassemble tabs)
    house_screen.py        Homestead overlay (stash + save)
    charscreen.py          Character / stat allocation screen
    skillscreen.py         Skill tree screen
    perk_screen.py         Milestone perk selection screen
    questlog.py            Quest log overlay
    quest_giver_screen.py  NPC quest dialogue
    settings_screen.py     Settings overlay (keybinds, display, language, multiplayer)
    minimap.py             Minimap renderer
    pager.py               Shared prev/next page helper for scrollable screens
  network/
    protocol.py            Length-prefixed JSON framing
    server.py              Headless authoritative game server (asyncio)
    client.py              Thread-safe client + GhostEnemy/RemotePlayer proxies
  utils/
    camera.py              Smooth-follow camera
tests/                     pytest suite
```

---

## License

MIT
