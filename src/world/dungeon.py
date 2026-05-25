import random
import pygame
from src.world.tile import (TILE_VOID, TILE_FLOOR, TILE_WALL, TILE_STAIRS_DOWN,
                             WALKABLE, get_tile_surface)
from src.settings import (TILE_SIZE, SCREEN_WIDTH, SCREEN_HEIGHT, HUD_HEIGHT,
                           DUNGEON_WIDTH, DUNGEON_HEIGHT, MIN_ROOM_SIZE,
                           MAX_ROOM_SIZE, MAX_ROOMS)


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
        self.rng = random.Random(seed)
        self.width  = DUNGEON_WIDTH
        self.height = DUNGEON_HEIGHT
        self.grid: list[list[int]] = [
            [TILE_VOID] * self.width for _ in range(self.height)
        ]
        self.rooms: list[Room] = []
        self.player_start = (0, 0)   # pixel coords
        self.stairs_pos   = (0, 0)   # pixel coords
        self.enemy_spawns:    list[tuple[int, int]] = []  # tile coords
        self.item_spawns:     list[tuple[int, int]] = []  # tile coords
        self.merchant_spawns: list[tuple[int, int]] = []  # tile coords (room centres)
        self.trap_positions:  list[tuple[int, int]] = []  # tile coords of spike traps
        self.chest_positions: list[tuple[int, int]] = []  # tile coords of treasure chests
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
        self._place_pillars()

        cx, cy = rooms[0].center
        self.player_start = (cx * TILE_SIZE + TILE_SIZE // 2,
                             cy * TILE_SIZE + TILE_SIZE // 2)

        lx, ly = rooms[-1].center
        self.grid[ly][lx] = TILE_STAIRS_DOWN
        self.stairs_pos = (lx * TILE_SIZE + TILE_SIZE // 2,
                           ly * TILE_SIZE + TILE_SIZE // 2)

        self._place_spawns()

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
            positions = room.inner_positions()
            self.rng.shuffle(positions)
            for pos in positions[:enemies_per_room]:
                self.enemy_spawns.append(pos)
        for room in self.rooms[1:]:
            if self.rng.random() < 0.65:
                self.item_spawns.append(room.random_inner(self.rng))

        # Merchants — rare find; ~28 % on floor 1, scaling to ~60 % on floor 5.
        # Player should feel lucky to stumble upon one, not annoyed by them everywhere.
        eligible = self.rooms[2:-1]
        if eligible:
            spawn_chance = 0.20 + self.level * 0.08   # 0.28 → 0.60
            if self.rng.random() < spawn_chance:
                self.rng.shuffle(eligible)
                # Almost always just one; deep floors very occasionally spawn two
                n_merchants = 1
                if self.level >= 4 and len(eligible) >= 4 and self.rng.random() < 0.25:
                    n_merchants = 2
                for room in eligible[:n_merchants]:
                    cx, cy = room.center
                    self.merchant_spawns.append((cx, cy))

        # Spike traps — scatter in floor tiles that are in corridors (not in rooms)
        room_cells: set[tuple[int, int]] = set()
        for room in self.rooms:
            for pos in room.inner_positions():
                room_cells.add(pos)

        corridor_floor: list[tuple[int, int]] = []
        for ty in range(1, self.height - 1):
            for tx in range(1, self.width - 1):
                if self.grid[ty][tx] == TILE_FLOOR and (tx, ty) not in room_cells:
                    corridor_floor.append((tx, ty))

        self.rng.shuffle(corridor_floor)
        n_traps = min(len(corridor_floor), 4 + self.level * 2)
        self.trap_positions = corridor_floor[:n_traps]

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

    # ─── Rendering ───────────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface, camera):
        cx = int(camera.x // TILE_SIZE)
        cy = int(camera.y // TILE_SIZE)
        cols = SCREEN_WIDTH  // TILE_SIZE + 2
        rows = (SCREEN_HEIGHT - HUD_HEIGHT) // TILE_SIZE + 2

        for ty in range(max(0, cy - 1), min(self.height, cy + rows + 1)):
            for tx in range(max(0, cx - 1), min(self.width, cx + cols + 1)):
                tile_type = self.grid[ty][tx]
                surf = get_tile_surface(tile_type, tx, ty)
                surface.blit(surf, (tx * TILE_SIZE - int(camera.x),
                                    ty * TILE_SIZE - int(camera.y)))
