import pygame
from src.settings import SCREEN_WIDTH, TILE_SIZE
from src.world.tile  import TILE_VOID, TILE_WALL, TILE_STAIRS_DOWN

SCALE    = 2         # pixels per tile
_MM_BG   = (8,  6,  4)
_MM_FLOR = (80, 65, 50)
_MM_WALL = (35, 28, 22)
_MM_STRS = (200, 175, 60)   # gold — stairs
_MM_ENE  = (210, 55,  55)   # red — enemies
_MM_PLR  = (120, 180, 255)  # blue — player
_MM_CHST = (220, 175, 40)   # gold — treasure chest
_MM_MRCH = (180, 80,  220)  # purple — merchant
_MM_TRAP = (160, 35,  35)   # dark red — spike trap
_ELITE_E = (220, 175, 0)    # gold — elite enemy


def _dot2(surf: pygame.Surface, x: int, y: int, col: tuple):
    """Draw a 2×2 pixel dot (clipped)."""
    w, h = surf.get_size()
    for dx in range(2):
        for dy in range(2):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h:
                surf.set_at((nx, ny), col)


class Minimap:
    def __init__(self):
        self._base: pygame.Surface | None = None
        self._dw = 0
        self._dh = 0

    def build(self, dungeon):
        self._dw = dungeon.width  * SCALE
        self._dh = dungeon.height * SCALE
        self._base = pygame.Surface((self._dw, self._dh))
        self._base.fill(_MM_BG)
        for ty in range(dungeon.height):
            for tx in range(dungeon.width):
                t = dungeon.grid[ty][tx]
                if t == TILE_VOID:
                    continue
                elif t == TILE_WALL:
                    col = _MM_WALL
                elif t == TILE_STAIRS_DOWN:
                    col = _MM_STRS
                else:
                    col = _MM_FLOR
                _dot2(self._base, tx * SCALE, ty * SCALE, col)

    def draw(self, surface: pygame.Surface, player, enemies,
             stairs_pos, chests=None, merchants=None, trap_positions=None):
        if self._base is None:
            return

        mm_x = SCREEN_WIDTH - self._dw - 10
        mm_y = 10

        frame = self._base.copy()

        # ── Traps (dim red dots — subtle, hard to miss) ───────────────────────
        if trap_positions:
            for tx, ty in trap_positions:
                _dot2(frame, tx * SCALE, ty * SCALE, _MM_TRAP)

        # ── Merchants (purple dot) ────────────────────────────────────────────
        if merchants:
            for m in merchants:
                mx_ = int(m.x / TILE_SIZE) * SCALE
                my_ = int(m.y / TILE_SIZE) * SCALE
                _dot2(frame, mx_, my_, _MM_MRCH)
                # Extra pixel ring so they stand out
                for ox, oy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nx_, ny_ = mx_ + ox, my_ + oy
                    if 0 <= nx_ < self._dw and 0 <= ny_ < self._dh:
                        frame.set_at((nx_, ny_), _MM_MRCH)

        # ── Treasure chests (gold dot, slightly bigger) ───────────────────────
        if chests:
            for chest in chests:
                if chest.opened:
                    continue
                cx_ = int(chest.x / TILE_SIZE) * SCALE
                cy_ = int(chest.y / TILE_SIZE) * SCALE
                # 3×3 gold mark
                for ox in range(-1, 2):
                    for oy in range(-1, 2):
                        nx_, ny_ = cx_ + ox, cy_ + oy
                        if 0 <= nx_ < self._dw and 0 <= ny_ < self._dh:
                            frame.set_at((nx_, ny_), _MM_CHST)

        # ── Stairs dot ────────────────────────────────────────────────────────
        sx = int(stairs_pos[0] / TILE_SIZE) * SCALE
        sy = int(stairs_pos[1] / TILE_SIZE) * SCALE
        for ox in range(-1, 2):
            for oy in range(-1, 2):
                nx_, ny_ = sx + ox, sy + oy
                if 0 <= nx_ < self._dw and 0 <= ny_ < self._dh:
                    frame.set_at((nx_, ny_), _MM_STRS)

        # ── Enemy dots ────────────────────────────────────────────────────────
        for e in enemies:
            ex = int(e.x / TILE_SIZE) * SCALE
            ey = int(e.y / TILE_SIZE) * SCALE
            col = _ELITE_E if getattr(e, 'is_elite', False) else _MM_ENE
            _dot2(frame, ex, ey, col)

        # ── Player dot (larger, bright) ───────────────────────────────────────
        px = int(player.x / TILE_SIZE) * SCALE
        py = int(player.y / TILE_SIZE) * SCALE
        pygame.draw.rect(frame, _MM_PLR, (px - 1, py - 1, SCALE + 2, SCALE + 2))

        # ── Frame border ──────────────────────────────────────────────────────
        pygame.draw.rect(frame, (110, 88, 60), (0, 0, self._dw, self._dh), 1)

        # ── Layered backing ───────────────────────────────────────────────────
        pygame.draw.rect(surface, (2, 1, 0),
                         (mm_x - 6, mm_y - 6, self._dw + 12, self._dh + 12),
                         border_radius=2)
        pygame.draw.rect(surface, (28, 20, 12),
                         (mm_x - 4, mm_y - 4, self._dw + 8, self._dh + 8),
                         border_radius=2)
        pygame.draw.rect(surface, (75, 55, 34),
                         (mm_x - 3, mm_y - 3, self._dw + 6, self._dh + 6),
                         2, border_radius=2)
        surface.blit(frame, (mm_x, mm_y))
        # Inner bright edge
        pygame.draw.rect(surface, (95, 72, 44),
                         (mm_x, mm_y, self._dw, self._dh), 1)

        # ── Legend strip below minimap ────────────────────────────────────────
        if not hasattr(self, '_leg_font'):
            self._leg_font = pygame.font.SysFont("monospace", 9)
        leg_y  = mm_y + self._dh + 4
        leg_x  = mm_x
        legend = [("■ YOU",   _MM_PLR),  ("■ ENE",  _MM_ENE),
                  ("■ MRCH",  _MM_MRCH), ("■ CHST", _MM_CHST)]
        for lbl, col in legend:
            lt = self._leg_font.render(lbl, True, col)
            surface.blit(lt, (leg_x, leg_y))
            leg_x += lt.get_width() + 4
