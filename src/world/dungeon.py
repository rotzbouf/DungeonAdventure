import math
import random
import pygame
from src.world.tile import (TILE_VOID, TILE_FLOOR, TILE_WALL, TILE_STAIRS_DOWN,
                             WALKABLE, get_tile_surface)
from src.settings import (TILE_SIZE, SCREEN_WIDTH, SCREEN_HEIGHT, HUD_HEIGHT,
                           DUNGEON_WIDTH, DUNGEON_HEIGHT, MIN_ROOM_SIZE,
                           MAX_ROOM_SIZE, MAX_ROOMS)

# ── Ambient-occlusion strips (built lazily once pygame is ready) ──────────────
_AO_STRIPS: dict | None = None

def _ensure_ao_strips() -> dict:
    global _AO_STRIPS
    if _AO_STRIPS is not None:
        return _AO_STRIPS
    depth = 7
    result = {}
    dirs = {
        'N': lambda i: ((0, i),              (TILE_SIZE - 1, i)),
        'S': lambda i: ((0, TILE_SIZE-1-i),  (TILE_SIZE - 1, TILE_SIZE-1-i)),
        'W': lambda i: ((i, 0),              (i, TILE_SIZE - 1)),
        'E': lambda i: ((TILE_SIZE-1-i, 0),  (TILE_SIZE-1-i, TILE_SIZE - 1)),
    }
    for name, pts_fn in dirs.items():
        s = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
        for i in range(depth):
            a = int(105 * (1.0 - i / depth) ** 1.8)
            p1, p2 = pts_fn(i)
            pygame.draw.line(s, (0, 0, 0, a), p1, p2)
        result[name] = s
    _AO_STRIPS = result
    return result


# ── Prop drawing helpers (drawn into the baked surface) ───────────────────────

_WD_D = (46, 30, 12);  _WD_M = (72, 50, 20);  _WD_L = (106, 76, 34)
_IR_D = (28, 28, 30);  _IR_M = (52, 52, 56);  _IR_L = (82, 82, 88)
_ST_D = (52, 46, 38);  _ST_M = (76, 68, 58)
_BONE = (178, 168, 148);  _BONE_SH = (110, 104, 90)


def _draw_sconce(surf: pygame.Surface, sx: int, sy: int):
    """Iron wall-sconce bracket with torch body at (sx, sy)."""
    # Horizontal arm
    pygame.draw.rect(surf, _IR_D, (sx - 7, sy - 2, 14, 4))
    pygame.draw.rect(surf, _IR_M, (sx - 6, sy - 1, 12, 2))
    pygame.draw.line(surf, _IR_L, (sx - 6, sy - 1), (sx + 5, sy - 1))
    # Wall anchor plate
    pygame.draw.rect(surf, _IR_D, (sx - 9, sy - 5, 5, 9))
    pygame.draw.rect(surf, _IR_M, (sx - 8, sy - 4, 3, 7))
    # Torch body
    pygame.draw.rect(surf, _WD_D, (sx - 2, sy - 9, 5, 10))
    pygame.draw.rect(surf, _WD_M, (sx - 1, sy - 8, 3,  8))
    pygame.draw.line(surf, _WD_L, (sx,     sy - 8), (sx, sy + 1))


def _draw_rubble(surf: pygame.Surface, px: int, py: int, rng: random.Random):
    """3-5 dark stone chips near a wall edge."""
    cx = px + rng.randint(6, TILE_SIZE - 8)
    cy = py + rng.randint(6, TILE_SIZE - 8)
    for _ in range(rng.randint(3, 5)):
        rx = cx + rng.randint(-7, 7)
        ry = cy + rng.randint(-4, 4)
        rw = rng.randint(3, 9);  rh = rng.randint(2, 5)
        v  = rng.randint(-14, 5)
        col = (max(0, _ST_D[0]+v), max(0, _ST_D[1]+v), max(0, _ST_D[2]+v))
        pygame.draw.ellipse(surf, col, (rx - rw//2, ry - rh//2, rw, rh))


def _draw_bones(surf: pygame.Surface, px: int, py: int, rng: random.Random):
    """Scattered bone fragments."""
    cx = px + rng.randint(8, TILE_SIZE - 8)
    cy = py + rng.randint(8, TILE_SIZE - 8)
    for _ in range(rng.randint(2, 3)):
        ang = rng.uniform(0, math.pi)
        L   = rng.randint(5, 10)
        x1  = int(cx + math.cos(ang) * L);  y1 = int(cy + math.sin(ang) * L)
        x2  = int(cx - math.cos(ang) * L);  y2 = int(cy - math.sin(ang) * L)
        pygame.draw.line(surf, _BONE_SH, (x1+1, y1+1), (x2+1, y2+1), 2)
        pygame.draw.line(surf, _BONE,    (x1,   y1),   (x2,   y2),   2)
        pygame.draw.circle(surf, _BONE, (x1, y1), 2)
        pygame.draw.circle(surf, _BONE, (x2, y2), 2)


def _draw_barrel_or_crate(surf: pygame.Surface, px: int, py: int,
                           rng: random.Random):
    """Small decorative barrel or crate."""
    cx = px + rng.randint(7, TILE_SIZE - 9)
    cy = py + rng.randint(7, TILE_SIZE - 9)
    sh = pygame.Surface((22, 5), pygame.SRCALPHA)
    sh.fill((0, 0, 0, 50))

    if rng.random() < 0.5:              # barrel
        bw, bh = 14, 18
        surf.blit(sh, (cx - bw//2 - 2, cy + bh//2 - 1))
        for i in range(bh):
            f  = abs(i - bh//2) / (bh//2)
            col = tuple(int(_WD_D[j] + (_WD_M[j]-_WD_D[j])*(1-f*0.5)) for j in range(3))
            pygame.draw.line(surf, col, (cx-bw//2, cy-bh//2+i), (cx+bw//2, cy-bh//2+i))
        pygame.draw.ellipse(surf, _WD_L, (cx-bw//2, cy-bh//2-3, bw, 7))
        pygame.draw.ellipse(surf, _WD_M, (cx-bw//2, cy-bh//2-2, bw, 5))
        for hy in [cy - bh//4, cy + bh//4]:
            pygame.draw.rect(surf, _IR_M, (cx-bw//2-1, hy-1, bw+2, 3))
        pygame.draw.rect(surf, _WD_D, (cx-bw//2, cy-bh//2, bw, bh), 1)
    else:                               # crate
        bw, bh = 16, 14
        surf.blit(sh, (cx - bw//2 - 2, cy + bh//2 - 1))
        for i in range(bh):
            f   = i / max(1, bh-1)
            col = tuple(int(_WD_L[j]+(_WD_D[j]-_WD_L[j])*f) for j in range(3))
            pygame.draw.line(surf, col, (cx-bw//2, cy-bh//2+i), (cx+bw//2-1, cy-bh//2+i))
        pygame.draw.line(surf, _WD_D, (cx-bw//2, cy-bh//2), (cx+bw//2, cy+bh//2), 1)
        pygame.draw.line(surf, _WD_D, (cx+bw//2, cy-bh//2), (cx-bw//2, cy+bh//2), 1)
        pygame.draw.line(surf, _WD_L, (cx-bw//2, cy-bh//2), (cx+bw//2, cy-bh//2))
        pygame.draw.rect(surf, _WD_D, (cx-bw//2, cy-bh//2, bw, bh), 1)


class Room:
    def __init__(self, x: int, y: int, w: int, h: int):
        self.x, self.y, self.w, self.h = x, y, w, h

    @property
    def center(self):
        return self.x + self.w // 2, self.y + self.h // 2

    def intersects(self, other: "Room", margin: int = 1) -> bool:
        return (self.x - margin < other.x + other.w and
                self.x + self.w + margin > other.x and
                self.y - margin < other.y + other.h and
                self.y + self.h + margin > other.y)

    def random_inner(self, rng: random.Random):
        return (rng.randint(self.x + 1, self.x + self.w - 2),
                rng.randint(self.y + 1, self.y + self.h - 2))

    def inner_positions(self):
        return [(rx, ry)
                for ry in range(self.y + 1, self.y + self.h - 1)
                for rx in range(self.x + 1, self.x + self.w - 1)]


class Dungeon:
    def __init__(self, level: int = 1, seed=None):
        self.level = level
        self.seed  = seed if seed is not None else random.randint(1, 2**30)
        self.rng   = random.Random(self.seed)
        self.width  = DUNGEON_WIDTH
        self.height = DUNGEON_HEIGHT
        self.grid: list[list[int]] = [
            [TILE_VOID] * self.width for _ in range(self.height)
        ]
        self.rooms:     list[Room] = []
        self.boss_room: Room | None = None  # pre-selected arena, set during generation
        self.player_start = (0, 0)   # pixel coords
        self.stairs_pos   = (0, 0)   # pixel coords
        self.enemy_spawns:    list[tuple[int, int]] = []  # tile coords
        self.item_spawns:     list[tuple[int, int]] = []  # tile coords
        self.merchant_spawns: list[tuple[int, int]] = []  # tile coords (room centres)
        self.chest_positions: list[tuple[int, int]] = []  # tile coords of treasure chests
        self.sconce_positions: list[tuple[int, int]] = []  # world px (sconce flame)
        self._baked: pygame.Surface | None = None           # pre-rendered level surface
        self._generate()

    # ─── Generation ──────────────────────────────────────────────────────────────

    def _generate(self):
        rooms: list[Room] = []
        attempts = 0
        while len(rooms) < MAX_ROOMS and attempts < MAX_ROOMS * 10:
            attempts += 1
            w = self.rng.randint(MIN_ROOM_SIZE, MAX_ROOM_SIZE)
            h = self.rng.randint(MIN_ROOM_SIZE, MAX_ROOM_SIZE)
            x = self.rng.randint(1, self.width  - w - 1)
            y = self.rng.randint(1, self.height - h - 1)
            r = Room(x, y, w, h)
            if not any(r.intersects(existing) for existing in rooms):
                rooms.append(r)

        self.rooms = rooms
        for room in rooms:
            self._carve_room(room)
        for i in range(1, len(rooms)):
            self._connect(rooms[i - 1], rooms[i])
        self._build_walls()
        self.boss_room = self._pick_boss_room()
        self._place_pillars()

        cx, cy = rooms[0].center
        self.player_start = (cx * TILE_SIZE + TILE_SIZE // 2,
                             cy * TILE_SIZE + TILE_SIZE // 2)

        lx, ly = rooms[-1].center
        self.grid[ly][lx] = TILE_STAIRS_DOWN
        self.stairs_pos = (lx * TILE_SIZE + TILE_SIZE // 2,
                           ly * TILE_SIZE + TILE_SIZE // 2)

        self._place_spawns()

    def _pick_boss_room(self) -> Room:
        """Return the best room for a boss arena: largest, not start, not staircase."""
        _BOSS_MIN = 11   # minimum tiles in each dimension for a comfortable arena
        candidates = self.rooms[1:-1]   # exclude player spawn and staircase room
        if not candidates:
            return self.rooms[-1]       # degenerate: only 1-2 rooms
        big  = [r for r in candidates if r.w >= _BOSS_MIN and r.h >= _BOSS_MIN]
        pool = big if big else candidates
        return max(pool, key=lambda r: r.w * r.h)

    def _carve_room(self, room: Room):
        for ry in range(room.y, room.y + room.h):
            for rx in range(room.x, room.x + room.w):
                self.grid[ry][rx] = TILE_FLOOR

    def _connect(self, a: Room, b: Room):
        ax, ay = a.center
        bx, by = b.center
        if self.rng.random() < 0.5:
            self._h_corridor(ax, bx, ay)
            self._v_corridor(ay, by, bx)
        else:
            self._v_corridor(ay, by, ax)
            self._h_corridor(ax, bx, by)

    def _h_corridor(self, x1: int, x2: int, y: int):
        for x in range(min(x1, x2), max(x1, x2) + 1):
            for dy in range(-1, 2):   # 3 tiles wide
                ny = y + dy
                if 0 <= ny < self.height and 0 <= x < self.width:
                    self.grid[ny][x] = TILE_FLOOR

    def _v_corridor(self, y1: int, y2: int, x: int):
        for y in range(min(y1, y2), max(y1, y2) + 1):
            for dx in range(-1, 2):   # 3 tiles wide
                nx = x + dx
                if 0 <= y < self.height and 0 <= nx < self.width:
                    self.grid[y][nx] = TILE_FLOOR

    def _build_walls(self):
        for y in range(self.height):
            for x in range(self.width):
                if self.grid[y][x] != TILE_VOID:
                    continue
                for dy in range(-1, 2):
                    for dx in range(-1, 2):
                        ny, nx = y + dy, x + dx
                        if (0 <= ny < self.height and 0 <= nx < self.width and
                                self.grid[ny][nx] == TILE_FLOOR):
                            self.grid[y][x] = TILE_WALL
                            break
                    else:
                        continue
                    break

    def _place_pillars(self):
        """Add stone pillar pairs inside large rooms for tactical cover."""
        for room in self.rooms[1:]:   # skip starting room
            if room is self.boss_room:  # keep the boss arena open
                continue
            if room.w < 9 or room.h < 9:
                continue
            cx, cy = room.center
            # Four symmetric pillar positions offset from the room centre
            offsets = [(-2, -2), (2, -2), (-2, 2), (2, 2)]
            for ox, oy in offsets:
                px, py = cx + ox, cy + oy
                # Keep pillars safely away from room border (2-tile margin)
                if (room.x + 2 <= px <= room.x + room.w - 3 and
                        room.y + 2 <= py <= room.y + room.h - 3):
                    self.grid[py][px] = TILE_WALL

    def _place_spawns(self):
        enemies_per_room = min(2 + self.level // 2, 4)
        for room in self.rooms[1:-1]:
            positions = [p for p in room.inner_positions()
                         if self.grid[p[1]][p[0]] == TILE_FLOOR]
            self.rng.shuffle(positions)
            for pos in positions[:enemies_per_room]:
                self.enemy_spawns.append(pos)
        for room in self.rooms[1:]:
            if self.rng.random() < 0.65:
                walkable = [p for p in room.inner_positions()
                            if self.grid[p[1]][p[0]] == TILE_FLOOR]
                if walkable:
                    self.item_spawns.append(self.rng.choice(walkable))

        # Travelling merchant — a very rare, lucky find in the dungeon.
        # Spawn chance: ~10-15 % flat.  Always one at most, always elite stock.
        eligible = self.rooms[2:-1]
        if eligible:
            spawn_chance = 0.08 + self.level * 0.015   # 0.095 → 0.155
            if self.rng.random() < spawn_chance:
                room = self.rng.choice(eligible)
                cx, cy = room.center
                self.merchant_spawns.append((cx, cy))

        # Treasure chest — one per floor in a random mid room (not merchant room)
        merchant_rooms = {self.merchant_spawns[i] for i in range(len(self.merchant_spawns))} if self.merchant_spawns else set()
        chest_eligible = [r for r in self.rooms[1:-1]
                          if r.center not in merchant_rooms and r.w >= 5 and r.h >= 5]
        if chest_eligible:
            chosen = self.rng.choice(chest_eligible)
            self.chest_positions.append(chosen.center)

    # ─── Queries ─────────────────────────────────────────────────────────────────

    def is_walkable(self, tx: int, ty: int) -> bool:
        if 0 <= tx < self.width and 0 <= ty < self.height:
            return self.grid[ty][tx] in WALKABLE
        return False

    def has_los(self, x1: float, y1: float,
                x2: float, y2: float) -> bool:
        """
        Return True if the straight line from pixel (x1,y1) to (x2,y2)
        passes through no wall or void tile.
        Uses a ray-march at half-tile resolution — cheap enough to call
        for every on-screen entity each frame.
        """
        dx = x2 - x1
        dy = y2 - y1
        dist = math.hypot(dx, dy)
        if dist < 1:
            return True
        # One sample per half-tile; cap to avoid per-frame spikes
        steps = min(48, max(3, int(dist / (TILE_SIZE * 0.5))))
        for i in range(1, steps):
            t   = i / steps
            tx_ = int((x1 + dx * t) / TILE_SIZE)
            ty_ = int((y1 + dy * t) / TILE_SIZE)
            if not (0 <= tx_ < self.width and 0 <= ty_ < self.height):
                return False   # out of dungeon bounds = blocked
            if self.grid[ty_][tx_] not in WALKABLE:
                return False   # wall or void blocks sight
        return True

    # ─── Rendering ───────────────────────────────────────────────────────────────

    def _bake(self):
        """Build the full pre-rendered dungeon surface with AO and props."""
        W = self.width  * TILE_SIZE
        H = self.height * TILE_SIZE
        surf = pygame.Surface((W, H))
        surf.fill((0, 0, 0))

        # 1. All tiles
        for ty in range(self.height):
            for tx in range(self.width):
                tt = self.grid[ty][tx]
                if tt != TILE_VOID:
                    surf.blit(get_tile_surface(tt, tx, ty),
                              (tx * TILE_SIZE, ty * TILE_SIZE))

        # 2. Ambient occlusion (floor tiles adjacent to walls get dark edge shadows)
        ao = _ensure_ao_strips()
        for ty in range(self.height):
            for tx in range(self.width):
                if self.grid[ty][tx] not in WALKABLE:
                    continue
                px_, py_ = tx * TILE_SIZE, ty * TILE_SIZE
                if ty > 0             and self.grid[ty-1][tx] == TILE_WALL: surf.blit(ao['N'], (px_, py_))
                if ty < self.height-1 and self.grid[ty+1][tx] == TILE_WALL: surf.blit(ao['S'], (px_, py_))
                if tx > 0             and self.grid[ty][tx-1] == TILE_WALL: surf.blit(ao['W'], (px_, py_))
                if tx < self.width-1  and self.grid[ty][tx+1] == TILE_WALL: surf.blit(ao['E'], (px_, py_))

        # 3. Wall sconces on south-facing walls (wall tile with walkable tile below)
        sc_rng = random.Random(self.seed + 1001)
        self.sconce_positions = []
        for ty in range(1, self.height - 1):
            for tx in range(self.width):
                if self.grid[ty][tx] != TILE_WALL:
                    continue
                if self.grid[ty + 1][tx] in WALKABLE and sc_rng.random() < 0.22:
                    sx = tx * TILE_SIZE + TILE_SIZE // 2
                    sy = ty * TILE_SIZE + TILE_SIZE - 6
                    _draw_sconce(surf, sx, sy)
                    self.sconce_positions.append((sx, sy - 5))  # flame pixel position

        # 4. Decorative props
        pr_rng = random.Random(self.seed + 2002)

        # Rubble on floor tiles next to walls
        for ty in range(1, self.height - 1):
            for tx in range(1, self.width - 1):
                if self.grid[ty][tx] not in WALKABLE:
                    continue
                near = any(self.grid[ty+dy][tx+dx] == TILE_WALL
                           for dx, dy in ((-1,0),(1,0),(0,-1),(0,1)))
                if near and pr_rng.random() < 0.065:
                    _draw_rubble(surf, tx*TILE_SIZE, ty*TILE_SIZE, pr_rng)

        # Bone clusters on room floor tiles
        room_cells = {pos for room in self.rooms for pos in room.inner_positions()}
        for tx, ty in room_cells:
            if self.grid[ty][tx] in WALKABLE and pr_rng.random() < 0.045:
                _draw_bones(surf, tx*TILE_SIZE, ty*TILE_SIZE, pr_rng)

        # Barrel / crate group in ~55 % of rooms (one corner each)
        for room in self.rooms[1:]:
            if pr_rng.random() > 0.55:
                continue
            corners = [(room.x+1, room.y+1), (room.x+room.w-2, room.y+1),
                       (room.x+1, room.y+room.h-2), (room.x+room.w-2, room.y+room.h-2)]
            cx_, cy_ = pr_rng.choice(corners)
            if (0 <= cy_ < self.height and 0 <= cx_ < self.width
                    and self.grid[cy_][cx_] in WALKABLE):
                _draw_barrel_or_crate(surf, cx_*TILE_SIZE, cy_*TILE_SIZE, pr_rng)

        self._baked = surf.convert()  # hardware-format conversion for fast blitting

    def draw(self, surface: pygame.Surface, camera):
        if self._baked is None:
            self._bake()
        cam_x = int(camera.x)
        cam_y = int(camera.y)
        sw, sh = surface.get_size()
        src = pygame.Rect(
            max(0, cam_x), max(0, cam_y),
            min(sw, self.width  * TILE_SIZE - max(0, cam_x)),
            min(sh, self.height * TILE_SIZE - max(0, cam_y)),
        )
        if src.width > 0 and src.height > 0:
            surface.blit(self._baked, (max(0, -cam_x), max(0, -cam_y)), src)
