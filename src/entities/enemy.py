import math
import random
import pygame
from src.entities.entity import Entity
from src.settings import (TILE_SIZE, ENEMY_SIZE, SCREEN_WIDTH, SCREEN_HEIGHT,
                           HUD_HEIGHT, RED, DARK_RED, YELLOW, WHITE, ORANGE,
                           STATUS_POISON, STATUS_SLOW)


class Enemy(Entity):
    NAME        = "Enemy"
    COLOR       = RED
    MAX_HP      = 30
    ATTACK      = 8
    DEFENSE     = 0
    SPEED       = 70.0
    DETECT      = 200.0
    ATK_RANGE   = 28.0
    ATK_CD      = 1.2
    XP_REWARD   = 20
    LOOT_CHANCE = 0.5
    # Subclasses override to apply a status on melee hit
    ON_HIT_STATUS: str | None = None
    ON_HIT_DURATION: float    = 0.0
    ON_HIT_MAG: float         = 0.0

    def __init__(self, x: float, y: float):
        super().__init__(x, y, ENEMY_SIZE, self.COLOR)
        self.max_hp      = self.MAX_HP
        self.hp          = float(self.MAX_HP)
        self.alive       = True
        # Instance copies of class stats so scale_to_level / make_elite can mutate
        self.attack      = int(self.ATTACK)
        self.defense     = int(self.DEFENSE)
        self.speed       = float(self.SPEED)
        self.detect      = float(self.DETECT)
        self.atk_range   = float(self.ATK_RANGE)
        self.atk_cd      = float(self.ATK_CD)
        self._atk_timer  = random.uniform(0, self.atk_cd)
        self._hurt_timer = 0.0
        self._state      = "idle"
        self._idle_timer = random.uniform(0, 2.5)
        self._idle_vx    = random.uniform(-1, 1)
        self._idle_vy    = random.uniform(-1, 1)

        # Elite variant
        self.is_elite         = False
        self._elite_aura_t    = 0.0   # for pulsing aura animation

    def make_elite(self):
        """Boost this enemy into an elite variant."""
        self.is_elite  = True
        self.max_hp    = int(self.max_hp * 1.6)
        self.hp        = float(self.max_hp)
        self.attack    = int(self.attack  * 1.5)
        self.size     += 4
        self.rect      = pygame.Rect(0, 0, self.size, self.size)
        self._sync_rect()

    def take_damage(self, amount: int) -> int:
        actual = max(1, amount - self.defense)
        self.hp -= actual
        self._hurt_timer = 0.18
        if self.hp <= 0:
            self.alive = False
        return actual

    def scale_to_level(self, level: int):
        """Boost stats proportionally for higher dungeon floors."""
        if level > 1:
            f = 1.0 + (level - 1) * 0.18
            self.max_hp  = max(1, int(self.MAX_HP  * f))
            self.hp      = float(self.max_hp)
            self.attack  = int(self.ATTACK  * f)
            self.speed   = self.SPEED * (1.0 + (level - 1) * 0.04)

    def update(self, dt: float, player, dungeon):
        self._atk_timer  = max(0.0, self._atk_timer  - dt)
        self._hurt_timer = max(0.0, self._hurt_timer - dt)
        self._elite_aura_t += dt

        # ── Status effect DoT (burn from player fireball, etc.) ──────────────
        dot_dmg = self.tick_statuses(dt)
        if dot_dmg > 0:
            self.hp -= dot_dmg
            self._hurt_timer = 0.12
            if self.hp <= 0:
                self.alive = False

        if not self.alive:
            return

        # ── Knockback physics ────────────────────────────────────────────────
        if self.kbx or self.kby:
            self._move(self.kbx * dt, self.kby * dt, dungeon)
            friction = max(0.0, 1.0 - 11.0 * dt)
            self.kbx *= friction
            self.kby *= friction
            if abs(self.kbx) < 2.0:
                self.kbx = 0.0
            if abs(self.kby) < 2.0:
                self.kby = 0.0

        dist = math.hypot(player.x - self.x, player.y - self.y)

        if dist < self.detect:
            self._state = "chase"
        elif self._state == "chase" and dist > self.detect * 1.3:
            self._state = "idle"

        # Slowed enemies move at 60% speed
        spd_mult = 0.60 if self.has_status('slow') else 1.0

        if self._state == "chase":
            if dist > self.atk_range + 2:
                nx = (player.x - self.x) / dist
                ny = (player.y - self.y) / dist
                self._move(nx * self.speed * spd_mult * dt,
                           ny * self.speed * spd_mult * dt, dungeon)
            elif self._atk_timer <= 0:
                self._atk_timer = self.atk_cd
                if dist > 0:
                    player.apply_knockback(
                        (player.x - self.x) / dist,
                        (player.y - self.y) / dist,
                        180.0,
                    )
                player.take_damage(self.attack)

                # Apply on-hit status to player
                hit_status = STATUS_POISON if self.is_elite else self.ON_HIT_STATUS
                if hit_status:
                    dur = 4.0 if self.is_elite else self.ON_HIT_DURATION
                    mag = 4.0 if self.is_elite else self.ON_HIT_MAG
                    player.apply_status(hit_status, dur, mag)

                # Thorns — player's gear reflects flat damage back
                thorns = getattr(player, 'thorns_damage', 0)
                if thorns > 0:
                    self.take_damage(int(thorns))
        else:
            self._idle_timer -= dt
            if self._idle_timer <= 0:
                self._idle_timer = random.uniform(1.0, 3.0)
                angle = random.uniform(0, math.pi * 2)
                self._idle_vx = math.cos(angle)
                self._idle_vy = math.sin(angle)
            self._move(self._idle_vx * self.speed * spd_mult * 0.25 * dt,
                       self._idle_vy * self.speed * spd_mult * 0.25 * dt, dungeon)

    def _move(self, dx: float, dy: float, dungeon):
        half = self.size // 2
        mg   = 2
        new_x = self.x + dx
        test  = pygame.Rect(new_x - half + mg, self.y - half + mg,
                            self.size - mg * 2, self.size - mg * 2)
        if self._corners_ok(test, dungeon):
            self.x = new_x
        new_y = self.y + dy
        test  = pygame.Rect(self.x - half + mg, new_y - half + mg,
                            self.size - mg * 2, self.size - mg * 2)
        if self._corners_ok(test, dungeon):
            self.y = new_y
        self._sync_rect()

    def _corners_ok(self, rect: pygame.Rect, dungeon) -> bool:
        for cx, cy in [(rect.left, rect.top), (rect.right, rect.top),
                       (rect.left, rect.bottom), (rect.right, rect.bottom)]:
            if not dungeon.is_walkable(int(cx // TILE_SIZE), int(cy // TILE_SIZE)):
                return False
        return True

    # ─── Shared helpers ──────────────────────────────────────────────────────────

    def _is_on_screen(self, dr: pygame.Rect) -> bool:
        play_h = SCREEN_HEIGHT - HUD_HEIGHT
        return (-30 < dr.x < SCREEN_WIDTH + 30 and
                -30 < dr.y < play_h + 30)

    def _draw_hp_bar(self, surface: pygame.Surface, dr: pygame.Rect):
        bar_w = self.size + 8
        bar_x = dr.centerx - bar_w // 2
        bar_y = dr.top - 10
        pygame.draw.rect(surface, (50, 10, 10), (bar_x, bar_y, bar_w, 5))
        fill = int(bar_w * max(0, self.hp) / self.max_hp)
        if fill > 0:
            col = (220, 160, 0) if self.is_elite else RED
            pygame.draw.rect(surface, col, (bar_x, bar_y, fill, 5))
        pygame.draw.rect(surface, (80, 20, 20), (bar_x, bar_y, bar_w, 5), 1)

    def _draw_shadow(self, surface: pygame.Surface, dr: pygame.Rect):
        sh = pygame.Surface((self.size + 6, 5), pygame.SRCALPHA)
        sh.fill((0, 0, 0, 50))
        surface.blit(sh, (dr.left - 3, dr.bottom - 1))

    def _hurt_color(self, base: tuple) -> tuple:
        tint = self.status_tint()
        if self._hurt_timer > 0:
            return (min(255, base[0] + 80), max(0, base[1] - 40), max(0, base[2] - 40))
        if tint:
            # Blend base with status tint
            return (
                min(255, (base[0] + tint[0]) // 2),
                min(255, (base[1] + tint[1]) // 2),
                min(255, (base[2] + tint[2]) // 2),
            )
        return base

    def _draw_elite_aura(self, surface: pygame.Surface, dr: pygame.Rect):
        """Pulsing gold/purple ring around elite enemies."""
        pulse = 0.65 + 0.35 * math.sin(self._elite_aura_t * 4.0)
        r     = self.size // 2 + 5
        cx, cy = dr.centerx, dr.centery
        # Outer gold ring
        a = int(180 * pulse)
        aura_surf = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
        pygame.draw.circle(aura_surf, (220, 175, 0, a),
                           (r + 2, r + 2), r + 2, 3)
        pygame.draw.circle(aura_surf, (148, 0, 216, int(a * 0.6)),
                           (r + 2, r + 2), r - 1, 2)
        surface.blit(aura_surf, (cx - r - 2, cy - r - 2))

        # "ELITE" label above HP bar
        if not hasattr(self, '_elite_font'):
            self._elite_font = pygame.font.SysFont("monospace", 10, bold=True)
        lbl = self._elite_font.render("★ ELITE", True, (220, 175, 0))
        surface.blit(lbl, (dr.centerx - lbl.get_width() // 2, dr.top - 22))

    def draw(self, surface: pygame.Surface, camera):
        """Fallback — subclasses override this."""
        dr = camera.apply(self.rect)
        if not self._is_on_screen(dr):
            return
        if self.is_elite:
            self._draw_elite_aura(surface, dr)
        self._draw_shadow(surface, dr)
        self._draw_hp_bar(surface, dr)
        cx, cy = dr.centerx, dr.centery
        col = self._hurt_color(self.COLOR)
        pygame.draw.rect(surface, (0, 0, 0), dr.inflate(2, 2))
        pygame.draw.rect(surface, col, dr)
        pygame.draw.circle(surface, YELLOW, (cx - 3, cy - 2), 2)
        pygame.draw.circle(surface, YELLOW, (cx + 3, cy - 2), 2)


# ─── Goblin / Octorok-style ── fast, squat, red eyes ─────────────────────────

class Goblin(Enemy):
    NAME        = "Goblin";  COLOR = (220,  92,  16)
    MAX_HP      = 25;        ATTACK = 7;    DEFENSE = 0
    SPEED       = 115.0;     DETECT = 220.0; ATK_RANGE = 26.0; ATK_CD = 0.9
    XP_REWARD   = 15;        LOOT_CHANCE = 0.35

    def draw(self, surface: pygame.Surface, camera):
        dr = camera.apply(self.rect)
        if not self._is_on_screen(dr):
            return
        if self.is_elite:
            self._draw_elite_aura(surface, dr)
        self._draw_shadow(surface, dr)
        self._draw_hp_bar(surface, dr)
        cx, cy = dr.centerx, dr.centery
        _BLK  = (0,    0,    0)
        _BODY = self._hurt_color((220,  92,  16))
        _DARK = (140,  48,   0)
        _EYE  = (204,   0,   0)   # red eyes

        pygame.draw.rect(surface, _BLK,  dr.inflate(2, 2))
        pygame.draw.rect(surface, _DARK, dr)
        inner = dr.inflate(-4, -4)
        pygame.draw.rect(surface, _BODY, inner)
        pygame.draw.polygon(surface, _BODY,
                            [(cx - 4, dr.top + 2), (cx - 9, dr.top - 7), (cx - 1, dr.top)])
        pygame.draw.polygon(surface, _BODY,
                            [(cx + 4, dr.top + 2), (cx + 9, dr.top - 7), (cx + 1, dr.top)])
        pygame.draw.rect(surface, _DARK, (cx - 3, cy + 1, 6, 4))
        pygame.draw.rect(surface, _EYE,  (cx - 6, cy - 3, 4, 4))
        pygame.draw.rect(surface, _EYE,  (cx + 2,  cy - 3, 4, 4))
        pygame.draw.rect(surface, _BLK,  (cx - 5, cy - 2, 2, 2))
        pygame.draw.rect(surface, _BLK,  (cx + 3,  cy - 2, 2, 2))


# ─── Skeleton / Stalfos-style ── bone white, hollow eye sockets, SLOWS on hit ─

class Skeleton(Enemy):
    NAME        = "Skeleton"; COLOR = (204, 196, 176)   # bone white
    MAX_HP      = 38;         ATTACK = 11;   DEFENSE = 2
    SPEED       = 75.0;       DETECT = 250.0; ATK_RANGE = 28.0; ATK_CD = 1.1
    XP_REWARD   = 28;         LOOT_CHANCE = 0.45
    ON_HIT_STATUS   = STATUS_SLOW
    ON_HIT_DURATION = 2.5
    ON_HIT_MAG      = 0.0   # no DoT; slow is handled by has_status check

    def draw(self, surface: pygame.Surface, camera):
        dr = camera.apply(self.rect)
        if not self._is_on_screen(dr):
            return
        if self.is_elite:
            self._draw_elite_aura(surface, dr)
        self._draw_shadow(surface, dr)
        self._draw_hp_bar(surface, dr)
        cx, cy = dr.centerx, dr.centery
        _BLK   = (0,   0,  0)
        _BONE  = self._hurt_color((204, 196, 176))
        _SHADE = (108,  100, 84)

        body = pygame.Rect(cx - 5, cy - 4, 10, dr.height - 5)
        pygame.draw.rect(surface, _BLK,   body.inflate(2, 2))
        pygame.draw.rect(surface, _SHADE, body)
        pygame.draw.rect(surface, _BONE,  body.inflate(-2, 0))
        for i in range(2):
            ry = body.top + 3 + i * 5
            pygame.draw.line(surface, _SHADE, (body.left + 1, ry), (body.right - 2, ry))
        skull_y = dr.top + 6
        pygame.draw.rect(surface, _BLK,   (cx - 7, skull_y - 6, 14, 12))
        pygame.draw.rect(surface, _SHADE, (cx - 6, skull_y - 5, 12, 10))
        pygame.draw.rect(surface, _BONE,  (cx - 5, skull_y - 4, 10,  8))
        pygame.draw.rect(surface, _BLK,   (cx - 6, skull_y - 3,  4,  4))
        pygame.draw.rect(surface, _BLK,   (cx + 2,  skull_y - 3,  4,  4))
        pygame.draw.line(surface, _SHADE, (cx - 4, skull_y + 4), (cx + 4, skull_y + 4))


# ─── Orc / Darknut-style ── armoured knight, blue plate mail ─────────────────

class Orc(Enemy):
    NAME        = "Orc";  COLOR = (0,  52, 216)   # blue armour
    MAX_HP      = 70;     ATTACK = 20;   DEFENSE = 4
    SPEED       = 60.0;   DETECT = 180.0; ATK_RANGE = 32.0; ATK_CD = 1.5
    XP_REWARD   = 50;     LOOT_CHANCE = 0.62

    def __init__(self, x, y):
        super().__init__(x, y)
        self.size = ENEMY_SIZE + 6   # bigger
        self.rect = pygame.Rect(0, 0, self.size, self.size)
        self._sync_rect()

    def draw(self, surface: pygame.Surface, camera):
        dr = camera.apply(self.rect)
        if not self._is_on_screen(dr):
            return
        if self.is_elite:
            self._draw_elite_aura(surface, dr)
        self._draw_shadow(surface, dr)
        self._draw_hp_bar(surface, dr)
        cx, cy = dr.centerx, dr.centery
        _BLK   = (0,    0,   0)
        _ARMOR = self._hurt_color((0,  52, 216))
        _HI    = (80,  140, 252)
        _SH    = (0,   24,  140)

        pygame.draw.rect(surface, _BLK,   dr.inflate(2, 2))
        pygame.draw.rect(surface, _SH,    dr)
        pygame.draw.rect(surface, _ARMOR, dr.inflate(-4, -4))
        for sx in (dr.left - 2, dr.right - 4):
            pygame.draw.rect(surface, _ARMOR, (sx, dr.top + 2, 6, 6))
            pygame.draw.rect(surface, _HI,   (sx, dr.top + 2, 6, 2))
        pygame.draw.rect(surface, _SH,   (cx - 7, cy - 5, 14, 5))
        pygame.draw.rect(surface, (204, 0, 0), (cx - 5, cy - 4, 4, 3))
        pygame.draw.rect(surface, (204, 0, 0), (cx + 1,  cy - 4, 4, 3))
        pygame.draw.line(surface, _HI, (cx, cy + 1), (cx, cy + 7), 2)
        pygame.draw.line(surface, _HI, (cx - 3, cy + 4), (cx + 3, cy + 4), 2)


# ─── Demon / Wizzrobe-style ── hooded sorcerer, glowing eyes ─────────────────

class Demon(Enemy):
    NAME        = "Demon"; COLOR = (148,  0, 216)   # purple
    MAX_HP      = 130;     ATTACK = 27;   DEFENSE = 6
    SPEED       = 92.0;    DETECT = 300.0; ATK_RANGE = 35.0; ATK_CD = 0.95
    XP_REWARD   = 110;     LOOT_CHANCE = 0.9

    def draw(self, surface: pygame.Surface, camera):
        dr = camera.apply(self.rect)
        if not self._is_on_screen(dr):
            return
        if self.is_elite:
            self._draw_elite_aura(surface, dr)
        self._draw_shadow(surface, dr)
        self._draw_hp_bar(surface, dr)
        cx, cy = dr.centerx, dr.centery
        _BLK   = (0,    0,    0)
        _ROBE  = self._hurt_color((148,  0, 216))
        _DARK  = (64,   0,  120)
        _GLOW  = (252, 188,   0)

        robe_pts = [
            (dr.left - 2, dr.bottom + 1),
            (dr.right + 2, dr.bottom + 1),
            (dr.right,     cy),
            (cx + 5,       dr.top + 3),
            (cx,           dr.top - 2),
            (cx - 5,       dr.top + 3),
            (dr.left,      cy),
        ]
        pygame.draw.polygon(surface, _BLK,  robe_pts)
        inner = [
            (dr.left,      dr.bottom),
            (dr.right,     dr.bottom),
            (dr.right - 2, cy),
            (cx + 4,       dr.top + 4),
            (cx,           dr.top),
            (cx - 4,       dr.top + 4),
            (dr.left + 2,  cy),
        ]
        pygame.draw.polygon(surface, _DARK,  inner)
        pygame.draw.line(surface, _ROBE,
                         (dr.left,     cy),
                         (dr.left + 2, dr.bottom), 2)
        pygame.draw.line(surface, _ROBE,
                         (dr.left + 2, cy),
                         (cx - 4,      dr.top + 4), 2)
        pygame.draw.rect(surface, _GLOW, (cx - 5, cy - 3, 4, 3))
        pygame.draw.rect(surface, _GLOW, (cx + 1,  cy - 3, 4, 3))
        surface.set_at((cx - 3, cy - 2), (252, 252, 252))
        surface.set_at((cx + 3,  cy - 2), (252, 252, 252))
        pygame.draw.line(surface, _ROBE, (cx - 3, cy + 2), (cx + 3, cy + 8), 1)
        pygame.draw.line(surface, _ROBE, (cx + 3, cy + 2), (cx - 3, cy + 8), 1)
        pygame.draw.line(surface, _ROBE, (cx - 4, cy + 5), (cx + 4, cy + 5), 1)


# ─── Registry ─────────────────────────────────────────────────────────────────

_BY_LEVEL: dict[int, list] = {
    1: [Goblin],
    2: [Goblin, Skeleton],
    3: [Goblin, Skeleton, Orc],
    4: [Skeleton, Orc, Demon],
    5: [Orc, Demon],
}


def get_enemy_types(level: int) -> list:
    return _BY_LEVEL.get(level, [Goblin, Skeleton, Orc])
