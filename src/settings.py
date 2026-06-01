TITLE = "Dungeon Adventure"
SCREEN_WIDTH  = 1920
SCREEN_HEIGHT = 1080
TILE_SIZE     = 40
FPS           = 60

STATE_MENU      = "menu"
STATE_PLAYING   = "playing"
STATE_GAME_OVER = "game_over"
STATE_TOWN      = "town"
# STATE_WIN removed — replaced by the NG+ system (floor 5 descent loops back to floor 1)
# STATE_SHOP removed — shop is an overlay flag (Game.shop_open), not a game state

# ── Colour palette ────────────────────────────────────────────────────────────
WHITE      = (252, 252, 252)
RED        = (204,  0,   0)
GREEN      = (0,  168,   0)
YELLOW     = (252, 188,   0)
GRAY       = (108, 108, 108)
LIGHT_GRAY = (188, 188, 188)
GOLD_COLOR = (252, 188,   0)

VOID_COLOR      = (0,   0,   0)    # pure black — used by tile.py for void tiles

# Player
PLAYER_COLOR           = (110, 160, 255)
PLAYER_SPEED           = 225
PLAYER_SIZE            = 28
PLAYER_MAX_HP          = 100
PLAYER_MAX_MANA        = 50
PLAYER_BASE_ATTACK     = 10
PLAYER_BASE_DEFENSE    = 2
PLAYER_ATTACK_RANGE    = 72
PLAYER_ATTACK_COOLDOWN = 0.45

XP_BASE = 80
MAX_PLAYER_LEVEL = 20

# D2-style core stats (starting floor values — investment above floor gives bonuses)
BASE_STR = 10     # each point above floor: +2 attack
BASE_DEX = 5      # each point above floor: +1 defense, +0.5% crit
BASE_VIT = 10     # each point above floor: +10 max HP
BASE_ENE = 5      # each point above floor: +5 max mana
STAT_POINTS_PER_LEVEL = 5

# Enemies
ENEMY_SIZE = 25

# Items
ITEM_SIZE = 22

# Dungeon
DUNGEON_WIDTH      = 100
DUNGEON_HEIGHT     = 72
MIN_ROOM_SIZE      = 8
MAX_ROOM_SIZE      = 18
MAX_ROOMS          = 22

# UI
HUD_HEIGHT = 110

# Status effects
STATUS_POISON = "poison"   # green DoT — applied by elite enemies
STATUS_SLOW   = "slow"     # speed −40% — applied by Skeletons
STATUS_BURN   = "burn"     # orange DoT — applied by player fireball
STATUS_FREEZE = "freeze"   # ice-blue slow — applied by Ice Nova

# Fireball spell (Z)
FIREBALL_MANA_COST = 25
FIREBALL_SPEED     = 525.0
FIREBALL_MAX_RANGE = 650.0
FIREBALL_DAMAGE    = 35
FIREBALL_RADIUS    = 70.0

# Ice Nova spell (X) — AoE slow burst around player
ICE_NOVA_MANA_COST = 20
ICE_NOVA_DAMAGE    = 22
ICE_NOVA_RADIUS    = 112.0
ICE_NOVA_SLOW_DUR  = 3.0
ICE_NOVA_COOLDOWN  = 1.2

# Chain Lightning spell (R) — jumps between up to 4 enemies
CHAIN_LIGHTNING_RANGE     = 400.0
CHAIN_LIGHTNING_MANA_COST = 35
CHAIN_LIGHTNING_DAMAGE    = 30
CHAIN_LIGHTNING_JUMPS     = 4
CHAIN_LIGHTNING_COOLDOWN  = 1.6

# Blink spell (V) — teleport to mouse cursor
BLINK_MANA_COST  = 15
BLINK_COOLDOWN   = 2.0

# Battle Cry active skill (B) — temporary melee damage boost
BATTLE_CRY_MANA_COST = 20
BATTLE_CRY_DURATION  = 5.0

# Whirlwind active skill (SHIFT+SPC) — 360° melee
WHIRLWIND_MANA_COST = 25

# Boss floor interval (every N floors a boss spawns)
BOSS_FLOOR_INTERVAL = 20

# Arrow projectile constants
ARROW_SPEED     = 875.0
ARROW_MAX_RANGE = 625.0
ARROW_BASE_DMG  = 18
