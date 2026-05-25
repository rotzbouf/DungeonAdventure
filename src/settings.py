TITLE = "Dungeon Adventure"
SCREEN_WIDTH  = 1280
SCREEN_HEIGHT = 720
TILE_SIZE     = 32
FPS           = 60

STATE_MENU      = "menu"
STATE_PLAYING   = "playing"
STATE_GAME_OVER = "game_over"
# STATE_WIN removed — replaced by the NG+ system (floor 5 descent loops back to floor 1)
# STATE_SHOP removed — shop is an overlay flag (Game.shop_open), not a game state

# ── Colour palette ────────────────────────────────────────────────────────────
BLACK      = (0,   0,   0)
WHITE      = (252, 252, 252)
RED        = (204,  0,   0)
DARK_RED   = (120,  0,   0)
GREEN      = (0,  168,   0)
BLUE       = (0,   60, 216)
DARK_BLUE  = (0,   24, 140)
YELLOW     = (252, 188,   0)
ORANGE     = (220,  92,  16)
PURPLE     = (148,   0, 216)
DARK_GRAY  = (60,   60,  60)
GRAY       = (108, 108, 108)
LIGHT_GRAY = (188, 188, 188)
GOLD_COLOR = (252, 188,   0)

# Dungeon tile palette
FLOOR_COLOR     = (16,   8,   0)   # near-black warm dungeon floor
FLOOR_ALT_COLOR = (12,   6,   0)
WALL_COLOR      = (0,    8,  52)   # dark blue mortar
WALL_TOP_COLOR  = (112, 152, 220)  # stone block highlight
DOOR_COLOR      = (160, 100,  28)  # wood brown
STAIRS_COLOR    = (216, 188,  88)  # gold step highlight
VOID_COLOR      = (0,   0,   0)    # pure black

# Player
PLAYER_COLOR           = (110, 160, 255)
PLAYER_SPEED           = 180
PLAYER_SIZE            = 22
PLAYER_MAX_HP          = 100
PLAYER_MAX_MANA        = 50
PLAYER_BASE_ATTACK     = 10
PLAYER_BASE_DEFENSE    = 2
PLAYER_ATTACK_RANGE    = 58
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
ENEMY_SIZE = 20

# Items
ITEM_SIZE    = 18
POTION_COLOR = (200, 50,  50)
WEAPON_COLOR = (190, 190, 230)
ARMOR_COLOR  = (160, 135, 100)

# Dungeon
DUNGEON_WIDTH      = 80
DUNGEON_HEIGHT     = 60
MIN_ROOM_SIZE      = 6
MAX_ROOM_SIZE      = 14
MAX_ROOMS          = 18
MAX_DUNGEON_LEVELS = 5

# UI
HUD_HEIGHT = 80
BAR_WIDTH  = 200
BAR_HEIGHT = 18

# Status effects
STATUS_POISON = "poison"   # green DoT — applied by elite enemies
STATUS_SLOW   = "slow"     # speed −40% — applied by Skeletons
STATUS_BURN   = "burn"     # orange DoT — applied by player fireball
STATUS_FREEZE = "freeze"   # ice-blue slow — applied by Ice Nova

# Fireball spell (Z)
FIREBALL_MANA_COST = 25
FIREBALL_SPEED     = 420.0   # px/s
FIREBALL_MAX_RANGE = 520.0   # px before it fizzles
FIREBALL_DAMAGE    = 35
FIREBALL_RADIUS    = 56.0    # AOE explosion radius

# Ice Nova spell (X) — AoE slow burst around player
ICE_NOVA_MANA_COST = 20
ICE_NOVA_DAMAGE    = 22
ICE_NOVA_RADIUS    = 90.0
ICE_NOVA_SLOW_DUR  = 3.0
ICE_NOVA_COOLDOWN  = 1.2

# Chain Lightning spell (R) — jumps between up to 4 enemies
CHAIN_LIGHTNING_MANA_COST = 35
CHAIN_LIGHTNING_DAMAGE    = 30
CHAIN_LIGHTNING_JUMPS     = 4
CHAIN_LIGHTNING_RANGE     = 320.0   # max jump distance per arc
CHAIN_LIGHTNING_COOLDOWN  = 1.6

# Blink spell (V) — teleport to mouse cursor
BLINK_MANA_COST  = 15
BLINK_COOLDOWN   = 2.0

# Battle Cry active skill (B) — temporary melee damage boost
BATTLE_CRY_MANA_COST = 20
BATTLE_CRY_DURATION  = 5.0

# Whirlwind active skill (SHIFT+SPC) — 360° melee
WHIRLWIND_MANA_COST = 25

# Floors per New-Game-Plus cycle
FLOORS_PER_NG = 5
