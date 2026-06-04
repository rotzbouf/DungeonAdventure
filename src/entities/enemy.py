import math
import random
import pygame
from src.entities.entity import Entity
from src.settings import (TILE_SIZE, ENEMY_SIZE, SCREEN_WIDTH, SCREEN_HEIGHT,
                           HUD_HEIGHT, RED, YELLOW,
                           STATUS_POISON, STATUS_SLOW)


class Enemy(Entity):
    COLOR       = RED
    MAX_HP      = 30
    ATTACK      = 8
    DEFENSE     = 0
    SPEED       = 50.0
    DETECT      = 200.0
    ATK_RANGE   = 35.0
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
        """Boost stats proportionally for dungeon depth (endless scaling)."""
        if level > 1:
            n = level - 1
            f = 1.0 + 0.12 * n + 0.001 * n * n   # accelerating curve
            self.max_hp = max(1, int(self.MAX_HP * f))
            self.hp     = float(self.max_hp)
            self.attack = int(self.ATTACK * f)
            # Cap at 2.0× so speed never vastly outpaces the player
            self.speed  = self.SPEED * min(2.0, 1.0 + n * 0.018)

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
                        225.0,
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
            self._elite_font = pygame.font.SysFont("monospace", 28, bold=True)
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

    def _try_sprite_asset(self, surface: pygame.Surface,
                          camera, kind: str) -> bool:
        """Try PNG asset first. Returns True if drawn (caller should return)."""
        try:
            from src.assets import assets
            dr  = camera.apply(self.rect)
            if not self._is_on_screen(dr):
                return True
            spr = assets.enemy(kind, size=(self.size + 4, self.size + 4))
            if spr is None:
                return False
            if getattr(self, 'is_elite', False):
                self._draw_elite_aura(surface, dr)
            if getattr(self, 'is_boss', False):
                self._draw_boss_aura(surface, dr)
            self._draw_shadow(surface, dr)
            self._draw_hp_bar(surface, dr)
            tint = self.status_tint()
            if tint or self._hurt_timer > 0:
                tinted = spr.copy()
                tc = tint if tint else (255, 80, 80)
                tinted.fill((*tc, 90), special_flags=pygame.BLEND_RGBA_ADD)
                spr = tinted
            surface.blit(spr, spr.get_rect(center=(dr.centerx, dr.centery)))
            return True
        except Exception:
            return False


# ─── Goblin / Octorok-style ── fast, squat, red eyes ─────────────────────────

class Goblin(Enemy):
    ASSET_KEY = "goblin"
    COLOR = (220,  92,  16)
    MAX_HP      = 25;        ATTACK = 7;    DEFENSE = 0
    SPEED       = 104.0;     DETECT = 275.0; ATK_RANGE = 32.0; ATK_CD = 0.9
    XP_REWARD   = 15;        LOOT_CHANCE = 0.35

    def draw(self, surface: pygame.Surface, camera):
        dr = camera.apply(self.rect)
        if not self._is_on_screen(dr):
            return
        if self.is_elite:
            self._draw_elite_aura(surface, dr)
        self._draw_shadow(surface, dr)
        self._draw_hp_bar(surface, dr)
        if self._try_sprite_asset(surface, camera, self.ASSET_KEY): return
        cx, cy = dr.centerx, dr.centery
        _BLK  = (0,   0,   0)
        _BODY = self._hurt_color((220, 92, 16))
        _DARK = (120, 40,  0)
        _SKIN = (180, 100, 40)
        _EYE  = (220,  0,  0)
        _FANG = (240, 220, 180)

        # ── Hunched body ──────────────────────────────────────────────────────
        pygame.draw.rect(surface, _BLK,  dr.inflate(2, 2))
        pygame.draw.rect(surface, _DARK, dr)
        inner = dr.inflate(-4, -6)
        inner.move_ip(0, 3)   # shift body down — hunched posture
        pygame.draw.rect(surface, _BODY, inner)
        # Belly shading
        pygame.draw.rect(surface, _DARK, (inner.left, inner.centery, inner.w, inner.h//2))
        # Claw lines at lower body corners
        for sign in (1, -1):
            base_x = cx + sign * (dr.w//2 - 2)
            for i in range(3):
                pygame.draw.line(surface, _BLK,
                                 (base_x, dr.bottom - 4),
                                 (base_x + sign*(2+i), dr.bottom + 2 + i*2), 1)

        # ── Oversized pointed ears ────────────────────────────────────────────
        for sign in (1, -1):
            ear = [
                (cx + sign * 4, dr.top + 4),
                (cx + sign * 13, dr.top - 12),
                (cx + sign * 2,  dr.top),
            ]
            pygame.draw.polygon(surface, _BLK,  [(x+1,y+1) for x,y in ear])
            pygame.draw.polygon(surface, _BODY, ear)
            pygame.draw.polygon(surface, _DARK,
                                [(cx+sign*4,dr.top+4),(cx+sign*10,dr.top-8),(cx+sign*3,dr.top+1)])

        # ── Face ─────────────────────────────────────────────────────────────
        face_y = dr.top + 5
        pygame.draw.rect(surface, _BLK,  (cx - 6, face_y,     12, 10))
        pygame.draw.rect(surface, _SKIN, (cx - 5, face_y + 1, 10,  8))
        # Deep-set red eyes
        pygame.draw.rect(surface, _BLK, (cx - 5, face_y + 1, 4, 3))
        pygame.draw.rect(surface, _BLK, (cx + 1, face_y + 1, 4, 3))
        pygame.draw.rect(surface, _EYE, (cx - 4, face_y + 2, 2, 2))
        pygame.draw.rect(surface, _EYE, (cx + 2, face_y + 2, 2, 2))
        # Fangs
        for fxoff in (-3, 0, 3):
            pygame.draw.line(surface, _FANG,
                             (cx + fxoff, face_y + 8),
                             (cx + fxoff, face_y + 11), 1)

        # ── Crude bone club ───────────────────────────────────────────────────
        club_x0 = cx + dr.w//2
        club_y0 = cy + 2
        pygame.draw.line(surface, _BLK, (club_x0,   club_y0), (club_x0+8, club_y0-8), 4)
        pygame.draw.line(surface, (180,155,130), (club_x0, club_y0), (club_x0+8, club_y0-8), 2)
        pygame.draw.circle(surface, _BLK,       (club_x0+9, club_y0-9), 5)
        pygame.draw.circle(surface, (190,165,140),(club_x0+9, club_y0-9), 4)


# ─── Skeleton / Stalfos-style ── bone white, hollow eye sockets, SLOWS on hit ─

class Skeleton(Enemy):
    ASSET_KEY = "skeleton"
    COLOR = (204, 196, 176)   # bone white
    MAX_HP      = 38;         ATTACK = 11;   DEFENSE = 2
    SPEED       = 68.0;       DETECT = 312.0; ATK_RANGE = 35.0; ATK_CD = 1.1
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
        if self._try_sprite_asset(surface, camera, self.ASSET_KEY): return
        cx, cy = dr.centerx, dr.centery
        _BLK   = (0,   0,  0)
        _BONE  = self._hurt_color((204, 196, 176))
        _SHADE = (108,  100, 84)

        # ── Ribcage / torso ───────────────────────────────────────────────────
        body = pygame.Rect(cx - 5, cy - 2, 10, dr.height - 6)
        pygame.draw.rect(surface, _BLK,   body.inflate(2, 2))
        pygame.draw.rect(surface, _SHADE, body)
        pygame.draw.rect(surface, _BONE,  body.inflate(-2, 0))
        # Visible ribs — 3 pairs
        for i in range(3):
            ry = body.top + 3 + i * 5
            pygame.draw.line(surface, _SHADE, (body.left+1, ry), (body.right-2, ry))
            pygame.draw.line(surface, _BONE,  (body.left+1, ry-1), (body.right-2, ry-1), 1)

        # ── Arm bones ─────────────────────────────────────────────────────────
        for side in (1, -1):
            ax0 = cx + side * 5
            pygame.draw.line(surface, _SHADE, (ax0, body.top+2), (ax0+side*6, body.top+10), 2)
            pygame.draw.line(surface, _BONE,  (ax0-side, body.top+2), (ax0+side*5, body.top+10), 1)

        # ── Skull ─────────────────────────────────────────────────────────────
        skull_y = dr.top + 4
        # Cranium (slightly rounded via stacked rects)
        pygame.draw.rect(surface, _BLK,   (cx - 7, skull_y - 2, 14, 13))
        pygame.draw.rect(surface, _SHADE, (cx - 6, skull_y - 1, 12, 11))
        pygame.draw.rect(surface, _BONE,  (cx - 5, skull_y,     10,  9))
        pygame.draw.rect(surface, _BONE,  (cx - 4, skull_y - 1,  8,  2))  # skull dome
        # Eye sockets
        pygame.draw.rect(surface, _BLK,   (cx - 6, skull_y + 1, 4, 4))
        pygame.draw.rect(surface, _BLK,   (cx + 2, skull_y + 1, 4, 4))
        # Jaw
        pygame.draw.rect(surface, _SHADE, (cx - 4, skull_y + 8, 8, 3))
        for tx2 in (-3, -1, 1, 3):
            pygame.draw.line(surface, _BLK, (cx+tx2, skull_y+8), (cx+tx2, skull_y+11), 1)

        # ── Sword ─────────────────────────────────────────────────────────────
        sw_x0 = cx + dr.w//2 - 1
        sw_y0 = cy + 2
        pygame.draw.line(surface, _BLK,           (sw_x0, sw_y0), (sw_x0+9, sw_y0-12), 3)
        pygame.draw.line(surface, (200, 195, 180), (sw_x0, sw_y0), (sw_x0+9, sw_y0-12), 2)
        # Guard
        pygame.draw.line(surface, (130, 110, 60),
                         (sw_x0-3, sw_y0-3), (sw_x0+3, sw_y0+3), 2)


# ─── Orc / Darknut-style ── armoured knight, blue plate mail ─────────────────

class Orc(Enemy):
    ASSET_KEY = "orc"
    COLOR = (0,  52, 216)   # blue armour
    MAX_HP      = 70;     ATTACK = 20;   DEFENSE = 4
    SPEED       = 54.0;   DETECT = 225.0; ATK_RANGE = 40.0; ATK_CD = 1.5
    XP_REWARD   = 50;     LOOT_CHANCE = 0.62

    def __init__(self, x, y):
        super().__init__(x, y)
        self.size = ENEMY_SIZE + 10   # bigger than standard enemies
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
        if self._try_sprite_asset(surface, camera, self.ASSET_KEY): return
        _BLK   = (0,    0,   0)
        _ARMOR = self._hurt_color((0,  52, 216))
        _HI    = (80,  140, 252)
        _SH    = (0,   24,  140)

        # ── Cape behind body ──────────────────────────────────────────────────
        cape_col = (0, 20, 100)
        pygame.draw.polygon(surface, (0,0,0),
                            [(cx-1, dr.bottom+1), (cx+1, dr.bottom+1),
                             (cx+dr.w//2+4, dr.bottom+12), (cx-dr.w//2-4, dr.bottom+12)])
        pygame.draw.polygon(surface, cape_col,
                            [(cx-1, dr.bottom), (cx+1, dr.bottom),
                             (cx+dr.w//2+3, dr.bottom+11), (cx-dr.w//2-3, dr.bottom+11)])
        pygame.draw.line(surface, _HI,
                         (cx-1, dr.bottom), (cx-dr.w//2-3, dr.bottom+11), 1)

        # ── Armoured body ─────────────────────────────────────────────────────
        pygame.draw.rect(surface, _BLK,   dr.inflate(2, 2))
        pygame.draw.rect(surface, _SH,    dr)
        pygame.draw.rect(surface, _ARMOR, dr.inflate(-4, -4))
        # Chest plate highlight stripe
        pygame.draw.line(surface, _HI,
                         (dr.left+4, dr.top+4), (dr.left+4, dr.bottom-4), 1)
        # Tabard (vertical strip down the front)
        pygame.draw.rect(surface, (0, 30, 130), (cx-2, dr.top+6, 4, dr.h-10))

        # ── Pauldrons ─────────────────────────────────────────────────────────
        for sx_off in (dr.left - 5, dr.right + 1):
            pygame.draw.rect(surface, _BLK,   (sx_off - 1, dr.top + 2, 8, 10))
            pygame.draw.rect(surface, _ARMOR, (sx_off,     dr.top + 3, 7,  8))
            pygame.draw.rect(surface, _HI,    (sx_off,     dr.top + 3, 7,  2))
            # Pauldron spike
            pygame.draw.line(surface, _SH,
                             (sx_off+3, dr.top+3), (sx_off+3, dr.top-3), 2)

        # ── Helmet with nose guard ────────────────────────────────────────────
        hx, hy = cx, dr.top - 2
        pygame.draw.rect(surface, _BLK,  (hx-8, hy-6, 16, 12))
        pygame.draw.rect(surface, _SH,   (hx-7, hy-5, 14, 10))
        pygame.draw.rect(surface, _ARMOR,(hx-6, hy-4, 12,  8))
        pygame.draw.line(surface, _HI, (hx-6, hy-4), (hx+5, hy-4))   # brow ridge
        # Eye slits
        pygame.draw.rect(surface, _BLK, (hx-6, hy-1, 4, 2))
        pygame.draw.rect(surface, _BLK, (hx+2, hy-1, 4, 2))
        pygame.draw.rect(surface, (180, 0, 0), (hx-5, hy-1, 2, 1))
        pygame.draw.rect(surface, (180, 0, 0), (hx+3, hy-1, 2, 1))
        # Nose guard
        pygame.draw.rect(surface, _SH,  (hx-1, hy-1, 2, 5))
        pygame.draw.line(surface, _HI,  (hx-1, hy-1), (hx-1, hy+3))


# ─── Demon / Wizzrobe-style ── hooded sorcerer, glowing eyes ─────────────────

class Demon(Enemy):
    ASSET_KEY = "demon"
    COLOR = (148,  0, 216)   # purple
    MAX_HP      = 130;     ATTACK = 27;   DEFENSE = 6
    SPEED       = 82.0;   DETECT = 375.0; ATK_RANGE = 44.0; ATK_CD = 0.95
    XP_REWARD   = 110;     LOOT_CHANCE = 0.9

    def draw(self, surface: pygame.Surface, camera):
        dr = camera.apply(self.rect)
        if not self._is_on_screen(dr):
            return
        if self.is_elite:
            self._draw_elite_aura(surface, dr)
        self._draw_shadow(surface, dr)
        self._draw_hp_bar(surface, dr)
        if self._try_sprite_asset(surface, camera, self.ASSET_KEY): return
        cx, cy = dr.centerx, dr.centery
        _BLK   = (0,    0,    0)
        _ROBE  = self._hurt_color((148,  0, 216))
        _DARK  = (64,   0,  120)
        _GLOW  = (252, 188,   0)

        # ── Animated wavy hem ─────────────────────────────────────────────────
        t_anim = self._elite_aura_t
        n_hem  = 7
        hem_pts = []
        for j in range(n_hem):
            hx_ = dr.left - 2 + (dr.width + 4) * j // (n_hem - 1)
            hy_ = dr.bottom + 2 + int(math.sin(t_anim * 4.2 + j * 1.1) * 5)
            hem_pts.append((hx_, hy_))

        robe_pts = list(hem_pts) + [
            (dr.right,  cy),
            (cx + 5,    dr.top + 3),
            (cx,        dr.top - 2),
            (cx - 5,    dr.top + 3),
            (dr.left,   cy),
        ]
        pygame.draw.polygon(surface, _BLK,  [(x+1,y+1) for x,y in robe_pts])
        inner_pts = hem_pts[1:-1] + [
            (dr.right - 2, cy),
            (cx + 4,  dr.top + 4),
            (cx,      dr.top),
            (cx - 4,  dr.top + 4),
            (dr.left + 2, cy),
        ]
        pygame.draw.polygon(surface, _DARK, robe_pts)
        pygame.draw.polygon(surface, _ROBE, inner_pts)

        # Robe highlight folds
        pygame.draw.line(surface, _ROBE, (dr.left,    cy), (dr.left+2,  dr.bottom), 2)
        pygame.draw.line(surface, _ROBE, (dr.left+2,  cy), (cx-4,  dr.top+4), 2)
        pygame.draw.line(surface, tuple(min(255,c+30) for c in _ROBE),
                         (cx, dr.top+4), (cx, cy), 1)

        # ── Clawed hands at robe sides ────────────────────────────────────────
        for side, sign in (('left', -1), ('right', 1)):
            hand_x = dr.left - 3 if sign < 0 else dr.right + 3
            hand_y = cy + 4
            # Palm
            pygame.draw.ellipse(surface, _DARK, (hand_x - 3, hand_y - 3, 7, 6))
            # Claws
            for ci in range(3):
                cx2 = hand_x + sign * (ci * 2)
                pygame.draw.line(surface, _DARK,
                                 (cx2, hand_y - 3),
                                 (cx2 + sign * 3, hand_y - 8), 1)

        # ── Glowing eyes ─────────────────────────────────────────────────────
        eye_y = dr.top + dr.h // 3
        pygame.draw.rect(surface, _GLOW, (cx - 6, eye_y, 4, 3))
        pygame.draw.rect(surface, _GLOW, (cx + 2, eye_y, 4, 3))
        surface.set_at((cx - 4, eye_y + 1), (252, 252, 252))
        surface.set_at((cx + 4, eye_y + 1), (252, 252, 252))

        # ── Hood rim ──────────────────────────────────────────────────────────
        pygame.draw.arc(surface, _ROBE,
                        pygame.Rect(cx-8, dr.top-4, 16, 10), 0, math.pi, 2)


# ─── Boss enemies ─────────────────────────────────────────────────────────────

class BossEnemy(Enemy):
    """Base class for floor-boss enemies: large, has a charge attack."""
    is_boss        = True
    SIZE           = 80        # was 60
    LOOT_CHANCE    = 1.0
    CHARGE_INTERVAL = 6.0
    CHARGE_DURATION = 1.1

    def __init__(self, x: float, y: float):
        super().__init__(x, y)
        self.size = self.SIZE
        self.rect = pygame.Rect(0, 0, self.size, self.size)
        self._sync_rect()
        self._charge_cd    = random.uniform(3.0, self.CHARGE_INTERVAL)
        self._charging     = False
        self._charge_timer = 0.0

    def update(self, dt: float, player, dungeon):
        if self._charging:
            self._charge_timer -= dt
            if self._charge_timer <= 0:
                self._charging  = False
                self._charge_cd = self.CHARGE_INTERVAL + random.uniform(-1.0, 2.0)
        elif self._state == "chase":
            self._charge_cd -= dt
            if self._charge_cd <= 0:
                self._charging     = True
                self._charge_timer = self.CHARGE_DURATION

        saved_spd  = self.speed
        if self._charging:
            self.speed = saved_spd * 3.2
        super().update(dt, player, dungeon)
        self.speed = saved_spd

    def _draw_boss_aura(self, surface: pygame.Surface, dr: pygame.Rect):
        pulse = 0.55 + 0.45 * math.sin(self._elite_aura_t * 3.0)
        r     = self.size // 2 + 8
        cx, cy = dr.centerx, dr.centery
        a  = int(160 * pulse)
        s  = pygame.Surface((r * 2 + 8, r * 2 + 8), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.COLOR[:3], a), (r + 4, r + 4), r + 4, 5)
        pygame.draw.circle(s, (0, 0, 0, int(a * 0.4)), (r + 4, r + 4), r - 2, 2)
        surface.blit(s, (cx - r - 4, cy - r - 4))
        # Charge flash
        if self._charging:
            ca = int(200 * (self._charge_timer / self.CHARGE_DURATION))
            fs = pygame.Surface((self.size + 16, self.size + 16), pygame.SRCALPHA)
            pygame.draw.rect(fs, (252, 200, 60, ca), fs.get_rect(), border_radius=6)
            surface.blit(fs, (dr.left - 8, dr.top - 8))


class Lich(BossEnemy):
    """The Lich — undead sorcerer, slow but hits hard, floaty movement."""
    ASSET_KEY      = "lich"
    BOSS_NAME      = "The Lich"
    COLOR          = (80, 0, 140)
    MAX_HP         = 450;   ATTACK = 32;   DEFENSE = 6
    SPEED          = 65.0;  DETECT = 475.0; ATK_RANGE = 52.0; ATK_CD = 1.9
    XP_REWARD      = 650
    CHARGE_INTERVAL = 10.0; CHARGE_DURATION = 0.8

    def draw(self, surface: pygame.Surface, camera):
        dr = camera.apply(self.rect)
        if not self._is_on_screen(dr):
            return
        self._draw_boss_aura(surface, dr)
        self._draw_shadow(surface, dr)
        self._draw_hp_bar(surface, dr)
        if self._try_sprite_asset(surface, camera, self.ASSET_KEY): return
        cx, cy = dr.centerx, dr.centery

        _BLK  = (0, 0, 0)
        _ROBE = self._hurt_color((80, 0, 140))
        _DARK = (30, 0, 60)
        _BONE = (200, 190, 170)
        _GOLD = (220, 175, 0)
        _EYE  = (148, 0, 252)

        # Outer robe — large diamond silhouette
        robe_pts = [
            (cx,        dr.top - 4),
            (dr.right + 4, cy + 4),
            (cx,        dr.bottom + 2),
            (dr.left - 4,  cy + 4),
        ]
        pygame.draw.polygon(surface, _BLK,  [(x + 2, y + 2) for x, y in robe_pts])
        pygame.draw.polygon(surface, _DARK, robe_pts)
        inner = [(cx, dr.top + 2), (dr.right, cy + 4),
                 (cx, dr.bottom - 2), (dr.left, cy + 4)]
        pygame.draw.polygon(surface, _ROBE, inner)

        # Skull face (upper third)
        skull_y = dr.top + 4
        pygame.draw.rect(surface, _BLK,  (cx - 9, skull_y, 18, 16))
        pygame.draw.rect(surface, _BONE, (cx - 8, skull_y + 1, 16, 14))
        # Eye sockets
        pygame.draw.rect(surface, _BLK,  (cx - 7, skull_y + 3, 5, 5))
        pygame.draw.rect(surface, _BLK,  (cx + 2, skull_y + 3, 5, 5))
        pygame.draw.rect(surface, _EYE,  (cx - 6, skull_y + 4, 3, 3))
        pygame.draw.rect(surface, _EYE,  (cx + 3, skull_y + 4, 3, 3))
        # Teeth
        for tx_off in (-5, -2, 1, 4):
            pygame.draw.rect(surface, _BLK, (cx + tx_off, skull_y + 12, 2, 3))

        # Crown
        for ox in (-6, -2, 2, 6):
            pygame.draw.rect(surface, _GOLD, (cx + ox - 1, skull_y - 6, 3, 6))
        pygame.draw.rect(surface, _GOLD, (cx - 8, skull_y - 2, 16, 3))

        # Robe highlights
        pygame.draw.line(surface, _ROBE,
                         (cx, dr.top + 4), (cx, dr.bottom - 4), 1)


class DemonLord(BossEnemy):
    """The Demon Lord — charging brute with massive horns."""
    ASSET_KEY      = "demonlord"
    BOSS_NAME      = "Demon Lord"
    COLOR          = (160, 10, 20)
    MAX_HP         = 650;   ATTACK = 42;   DEFENSE = 8
    SPEED          = 85.0; DETECT = 400.0; ATK_RANGE = 55.0; ATK_CD = 1.1
    XP_REWARD      = 650
    CHARGE_INTERVAL = 5.0; CHARGE_DURATION = 1.3

    def draw(self, surface: pygame.Surface, camera):
        dr = camera.apply(self.rect)
        if not self._is_on_screen(dr):
            return
        self._draw_boss_aura(surface, dr)
        self._draw_shadow(surface, dr)
        self._draw_hp_bar(surface, dr)
        if self._try_sprite_asset(surface, camera, self.ASSET_KEY): return
        cx, cy = dr.centerx, dr.centery

        _BLK  = (0, 0, 0)
        _BODY = self._hurt_color((160, 10, 20))
        _DARK = (80, 0, 8)
        _HI   = (220, 60, 40)
        _HORN = (100, 40, 0)
        _EYE  = (252, 100, 0)

        # Body — wide hulking square
        pygame.draw.rect(surface, _BLK,  dr.inflate(4, 4))
        pygame.draw.rect(surface, _DARK, dr)
        pygame.draw.rect(surface, _BODY, dr.inflate(-6, -6))

        # Shoulder plates
        for sx_off, sign in ((-1, -1), (1, 1)):
            sh = pygame.Rect(dr.left + sx_off * 2 - 4, dr.top + 6, 10, 14)
            if sign < 0:
                sh.x = dr.left - 4
            else:
                sh.x = dr.right - 6
            pygame.draw.rect(surface, _BLK,  sh.inflate(2, 2))
            pygame.draw.rect(surface, _BODY, sh)
            pygame.draw.rect(surface, _HI,   (sh.x, sh.y, sh.w, 3))

        # Horns
        horn_pts_l = [(cx - 8, dr.top + 4), (cx - 16, dr.top - 14), (cx - 4, dr.top)]
        horn_pts_r = [(cx + 8, dr.top + 4), (cx + 16, dr.top - 14), (cx + 4, dr.top)]
        pygame.draw.polygon(surface, _BLK,  [(x+1, y+1) for x, y in horn_pts_l])
        pygame.draw.polygon(surface, _BLK,  [(x+1, y+1) for x, y in horn_pts_r])
        pygame.draw.polygon(surface, _HORN, horn_pts_l)
        pygame.draw.polygon(surface, _HORN, horn_pts_r)

        # Face / eyes
        pygame.draw.rect(surface, _BLK,  (cx - 8, cy - 8, 16, 12))
        pygame.draw.rect(surface, _DARK, (cx - 7, cy - 7, 14, 10))
        pygame.draw.rect(surface, _EYE,  (cx - 6, cy - 6, 5, 5))
        pygame.draw.rect(surface, _EYE,  (cx + 1, cy - 6, 5, 5))
        surface.set_at((cx - 4, cy - 4), (252, 230, 120))
        surface.set_at((cx + 3, cy - 4), (252, 230, 120))

        # Wing hints
        for side, sign in (('left', -1), ('right', 1)):
            wx_base = dr.left - 4 if sign < 0 else dr.right
            wpts = [
                (wx_base, cy),
                (wx_base + sign * 12, cy - 8),
                (wx_base + sign * 10, cy + 10),
            ]
            pygame.draw.polygon(surface, _DARK, wpts)


class StoneGolem(BossEnemy):
    """The Stone Golem — massive tank with crystal eyes."""
    ASSET_KEY      = "stonegolem"
    BOSS_NAME      = "Stone Golem"
    COLOR          = (100, 95, 88)
    MAX_HP         = 950;   ATTACK = 58;   DEFENSE = 20
    SPEED          = 42.0;  DETECT = 325.0; ATK_RANGE = 60.0; ATK_CD = 2.6
    XP_REWARD      = 650
    CHARGE_INTERVAL = 8.0; CHARGE_DURATION = 1.1

    def draw(self, surface: pygame.Surface, camera):
        dr = camera.apply(self.rect)
        if not self._is_on_screen(dr):
            return
        self._draw_boss_aura(surface, dr)
        self._draw_shadow(surface, dr)
        self._draw_hp_bar(surface, dr)
        if self._try_sprite_asset(surface, camera, self.ASSET_KEY): return
        cx, cy = dr.centerx, dr.centery

        _BLK   = (0, 0, 0)
        _STONE = self._hurt_color((100, 95, 88))
        _DARK  = (55, 50, 44)
        _HI    = (160, 155, 148)
        _MOSS  = (40, 90, 40)
        _CRYS  = (60, 180, 252)

        # Main body — solid block
        pygame.draw.rect(surface, _BLK,  dr.inflate(4, 4))
        pygame.draw.rect(surface, _DARK, dr)
        pygame.draw.rect(surface, _STONE, dr.inflate(-6, -6))

        # Stone texture — crack lines
        pygame.draw.line(surface, _DARK, (cx - 6, dr.top + 6), (cx + 2, cy), 2)
        pygame.draw.line(surface, _DARK, (cx + 4, cy + 2), (cx - 2, dr.bottom - 6), 2)
        pygame.draw.line(surface, _HI,   (cx - 5, dr.top + 7), (cx + 3, cy + 1), 1)

        # Mossy patches
        for mx_, my_ in [(cx - 10, cy + 6), (cx + 6, cy + 10), (cx - 4, dr.bottom - 8)]:
            pygame.draw.rect(surface, _MOSS, (mx_, my_, 5, 4))

        # Arm stumps
        for side_x in (dr.left - 6, dr.right + 2):
            pygame.draw.rect(surface, _BLK,  (side_x - 1, cy - 4, 8, 14))
            pygame.draw.rect(surface, _DARK, (side_x,     cy - 3, 7, 12))
            pygame.draw.rect(surface, _STONE,(side_x + 1, cy - 2, 5, 10))

        # Face — deep-set crystal eyes
        pygame.draw.rect(surface, _DARK, (cx - 10, cy - 12, 20, 10))
        pygame.draw.rect(surface, _BLK,  (cx - 8,  cy - 10,  6,  6))
        pygame.draw.rect(surface, _BLK,  (cx + 2,  cy - 10,  6,  6))
        pygame.draw.rect(surface, _CRYS, (cx - 7,  cy - 9,   4,  4))
        pygame.draw.rect(surface, _CRYS, (cx + 3,  cy - 9,   4,  4))
        surface.set_at((cx - 5, cy - 7), (200, 240, 252))
        surface.set_at((cx + 5, cy - 7), (200, 240, 252))

        # Highlight edge
        pygame.draw.rect(surface, _HI, dr.inflate(-6, -6), 1)


class VampireLord(BossEnemy):
    """The Vampire Lord — lightning-fast predator with life steal."""
    ASSET_KEY      = "vampirelord"
    BOSS_NAME      = "Vampire Lord"
    COLOR          = (100, 0, 60)
    MAX_HP         = 900;   ATTACK = 55;   DEFENSE = 12
    SPEED          = 100.0; DETECT = 430.0; ATK_RANGE = 48.0; ATK_CD = 0.85
    XP_REWARD      = 800
    CHARGE_INTERVAL = 4.0; CHARGE_DURATION = 0.9

    def update(self, dt: float, player, dungeon):
        super().update(dt, player, dungeon)
        # Life steal on successful hit — handled in Enemy.update via player.take_damage,
        # we approximate by healing 10% each frame we're in attack range post-hit
        if self._atk_timer > self.atk_cd - 0.15 and self.hp < self.max_hp:
            self.hp = min(self.max_hp, self.hp + 1.0 * dt * 20)

    def draw(self, surface: pygame.Surface, camera):
        dr = camera.apply(self.rect)
        if not self._is_on_screen(dr):
            return
        self._draw_boss_aura(surface, dr)
        self._draw_shadow(surface, dr)
        self._draw_hp_bar(surface, dr)
        if self._try_sprite_asset(surface, camera, self.ASSET_KEY): return
        cx, cy = dr.centerx, dr.centery

        _BLK  = (0, 0, 0)
        _CAPE = self._hurt_color((100, 0, 60))
        _DARK = (50, 0, 28)
        _PALE = (220, 200, 210)
        _RED  = (200, 0, 0)
        _GOLD = (180, 140, 0)

        # Cape — sweeping diamond
        cape_pts = [
            (cx,        dr.top),
            (dr.right + 8, cy - 4),
            (dr.right + 2, dr.bottom + 4),
            (cx,        dr.bottom - 6),
            (dr.left - 2,  dr.bottom + 4),
            (dr.left - 8,  cy - 4),
        ]
        pygame.draw.polygon(surface, _BLK,  [(x+2, y+2) for x, y in cape_pts])
        pygame.draw.polygon(surface, _DARK, cape_pts)
        inner_cape = [
            (cx, dr.top + 4), (dr.right + 4, cy),
            (dr.right - 2, dr.bottom), (cx, dr.bottom - 8),
            (dr.left + 2, dr.bottom), (dr.left - 4, cy),
        ]
        pygame.draw.polygon(surface, _CAPE, inner_cape)

        # Bat wings (above cape)
        for sign, wx_tip in ((-1, cx - 20), (1, cx + 20)):
            wy_tip = dr.top - 10
            wpts = [(cx + sign * 4, dr.top + 2),
                    (wx_tip,        wy_tip),
                    (cx + sign * 12, dr.top + 6),
                    (cx + sign * 10, dr.top + 14)]
            pygame.draw.polygon(surface, _BLK,  [(x+1, y+1) for x, y in wpts])
            pygame.draw.polygon(surface, _DARK, wpts)

        # Head (pale)
        head_y = dr.top + 2
        pygame.draw.rect(surface, _BLK,  (cx - 9, head_y, 18, 18))
        pygame.draw.rect(surface, _PALE, (cx - 8, head_y + 1, 16, 16))
        # Eyes — red slits
        pygame.draw.rect(surface, _RED,  (cx - 7, head_y + 5, 5, 3))
        pygame.draw.rect(surface, _RED,  (cx + 2, head_y + 5, 5, 3))
        # Fangs
        pygame.draw.rect(surface, _PALE, (cx - 3, head_y + 15, 2, 5))
        pygame.draw.rect(surface, _PALE, (cx + 1, head_y + 15, 2, 5))
        # Hair
        pygame.draw.rect(surface, _DARK, (cx - 8, head_y, 16, 5))
        for hx in range(cx - 7, cx + 8, 4):
            pygame.draw.rect(surface, _DARK, (hx, head_y - 3, 3, 4))
        # Gold collar
        pygame.draw.rect(surface, _GOLD, (cx - 6, head_y + 16, 12, 3))


class ElderDragon(BossEnemy):
    """The Elder Dragon — ancient wyrm, most dangerous beast in the deep."""
    ASSET_KEY      = "elderdragon"
    BOSS_NAME      = "Elder Dragon"
    COLOR          = (30, 100, 20)
    MAX_HP         = 1400;  ATTACK = 80;   DEFENSE = 22
    SPEED          = 64.0;  DETECT = 380.0; ATK_RANGE = 56.0; ATK_CD = 1.6
    XP_REWARD      = 1000
    CHARGE_INTERVAL = 5.5; CHARGE_DURATION = 1.4

    def draw(self, surface: pygame.Surface, camera):
        dr = camera.apply(self.rect)
        if not self._is_on_screen(dr):
            return
        self._draw_boss_aura(surface, dr)
        self._draw_shadow(surface, dr)
        self._draw_hp_bar(surface, dr)
        if self._try_sprite_asset(surface, camera, self.ASSET_KEY): return
        cx, cy = dr.centerx, dr.centery

        _BLK   = (0, 0, 0)
        _SCALE = self._hurt_color((30, 100, 20))
        _DARK  = (12, 50, 8)
        _BELLY = (180, 150, 60)
        _HORN  = (140, 110, 40)
        _EYE   = (252, 200, 0)
        _TOOTH = (240, 235, 210)

        # Body — bulky oval
        pygame.draw.ellipse(surface, _BLK,  dr.inflate(6, 4))
        pygame.draw.ellipse(surface, _DARK, dr.inflate(2, 0))
        pygame.draw.ellipse(surface, _SCALE, dr.inflate(-4, -4))

        # Scale texture — rows of chevrons
        for row in range(4):
            sy_ = dr.top + 6 + row * 12
            for col in range(3):
                sx_ = dr.left + 5 + col * 14
                pts = [(sx_, sy_ + 5), (sx_ + 5, sy_), (sx_ + 10, sy_ + 5)]
                pygame.draw.lines(surface, _DARK, False, pts, 1)

        # Belly — lighter underbelly strip
        belly_pts = [(cx - 10, cy - 2), (cx + 10, cy - 2),
                     (cx + 8,  cy + 14), (cx - 8,  cy + 14)]
        pygame.draw.polygon(surface, _BELLY, belly_pts)

        # Wings — spread behind body
        for side, tip_x in ((-1, dr.left - 18), (1, dr.right + 18)):
            wpts = [(cx + side * 8, cy - 4),
                    (tip_x,          dr.top - 8),
                    (tip_x + side * 4, cy + 4),
                    (cx + side * 10, cy + 8)]
            pygame.draw.polygon(surface, _BLK,  [(x+1, y+1) for x, y in wpts])
            pygame.draw.polygon(surface, _DARK, wpts)
            # Wing membrane lines
            for i in range(1, 4):
                wx1 = cx + side * 8
                wy1 = cy - 4
                wx2 = int(wx1 + (tip_x - wx1) * i / 4)
                wy2 = int(wy1 + (dr.top - 8 - wy1) * i / 4)
                pygame.draw.line(surface, _SCALE, (wx1, wy1), (wx2, wy2), 1)

        # Head — distinctive dragon snout
        head_r = pygame.Rect(cx - 14, dr.top - 2, 28, 22)
        pygame.draw.rect(surface, _BLK,  head_r.inflate(2, 2))
        pygame.draw.rect(surface, _DARK, head_r)
        pygame.draw.rect(surface, _SCALE, head_r.inflate(-4, -2))
        # Snout
        snout = pygame.Rect(cx - 10, dr.top + 10, 20, 10)
        pygame.draw.rect(surface, _DARK, snout)
        pygame.draw.rect(surface, _SCALE, snout.inflate(-2, -2))
        # Nostrils
        surface.set_at((cx - 5, dr.top + 16), _BLK)
        surface.set_at((cx + 5, dr.top + 16), _BLK)
        # Eyes
        pygame.draw.rect(surface, _BLK, (cx - 12, dr.top + 2, 6, 5))
        pygame.draw.rect(surface, _BLK, (cx + 6,  dr.top + 2, 6, 5))
        pygame.draw.rect(surface, _EYE, (cx - 11, dr.top + 3, 4, 3))
        pygame.draw.rect(surface, _EYE, (cx + 7,  dr.top + 3, 4, 3))
        surface.set_at((cx - 9, dr.top + 4), (252, 252, 200))
        surface.set_at((cx + 9, dr.top + 4), (252, 252, 200))
        # Horns
        for hx_off, hx_tip in ((-8, -14), (8, 14)):
            pygame.draw.line(surface, _HORN,
                             (cx + hx_off, dr.top - 2),
                             (cx + hx_tip, dr.top - 12), 3)
        # Teeth
        for tx_off in (-7, -3, 1, 5):
            pygame.draw.rect(surface, _TOOTH, (cx + tx_off, dr.top + 20, 3, 5))


class IronColossus(BossEnemy):
    """The Iron Colossus — mechanical titan forged in the deepest abyss."""
    ASSET_KEY      = "ironcolossus"
    BOSS_NAME      = "Iron Colossus"
    COLOR          = (80, 80, 90)
    MAX_HP         = 1800;  ATTACK = 95;   DEFENSE = 35
    SPEED          = 40.0;  DETECT = 300.0; ATK_RANGE = 60.0; ATK_CD = 2.8
    XP_REWARD      = 1200
    CHARGE_INTERVAL = 9.0; CHARGE_DURATION = 1.2

    def draw(self, surface: pygame.Surface, camera):
        dr = camera.apply(self.rect)
        if not self._is_on_screen(dr):
            return
        self._draw_boss_aura(surface, dr)
        self._draw_shadow(surface, dr)
        self._draw_hp_bar(surface, dr)
        if self._try_sprite_asset(surface, camera, self.ASSET_KEY): return
        cx, cy = dr.centerx, dr.centery

        _BLK   = (0, 0, 0)
        _STEEL = self._hurt_color((80, 80, 90))
        _DARK  = (36, 36, 44)
        _HI    = (160, 160, 175)
        _GOLD  = (180, 150, 20)
        _CORE  = (60, 200, 255)

        # Main body — heavy rectangular torso
        pygame.draw.rect(surface, _BLK,  dr.inflate(6, 6))
        pygame.draw.rect(surface, _DARK, dr)
        pygame.draw.rect(surface, _STEEL, dr.inflate(-6, -6))

        # Plate seams (horizontal lines)
        for iy in range(dr.top + 8, dr.bottom - 6, 10):
            pygame.draw.line(surface, _DARK, (dr.left + 2, iy), (dr.right - 2, iy), 2)
            pygame.draw.line(surface, _HI,   (dr.left + 2, iy + 1), (dr.right - 2, iy + 1), 1)

        # Rivets / bolt pattern
        for riy in (dr.top + 4, cy, dr.bottom - 6):
            for rix in (dr.left + 4, cx - 8, cx + 4, dr.right - 8):
                pygame.draw.circle(surface, _DARK, (rix, riy), 2)
                pygame.draw.circle(surface, _HI,   (rix, riy), 1)

        # Shoulder armour
        for side_x, side_dx in ((dr.left - 8, -6), (dr.right + 2, 4)):
            sh = pygame.Rect(side_x, dr.top + 4, 10, 18)
            pygame.draw.rect(surface, _BLK,  sh.inflate(2, 2))
            pygame.draw.rect(surface, _DARK, sh)
            pygame.draw.rect(surface, _STEEL, sh.inflate(-2, -2))
            pygame.draw.line(surface, _GOLD,
                             (sh.left + 1, sh.top + 1), (sh.right - 1, sh.top + 1))

        # Gold trim frame
        pygame.draw.rect(surface, _GOLD, dr.inflate(-2, -2), 2)

        # Steam vents (3 slots in lower body)
        for vx in (cx - 10, cx, cx + 10):
            pygame.draw.rect(surface, _DARK, (vx - 3, cy + 12, 6, 4))
            pygame.draw.rect(surface, _BLK,  (vx - 2, cy + 13, 4, 2))

        # Glowing eye slit visor
        pygame.draw.rect(surface, _BLK,  (cx - 14, cy - 16, 28, 7))
        pygame.draw.rect(surface, _CORE, (cx - 12, cy - 15, 24, 5))
        # Scanline effect
        pygame.draw.line(surface, _BLK,  (cx - 12, cy - 13), (cx + 12, cy - 13), 1)
        # Bright pupils
        surface.set_at((cx - 8, cy - 13), (200, 240, 255))
        surface.set_at((cx + 8, cy - 13), (200, 240, 255))

        # Central power core — glowing circle
        pulse = 0.6 + 0.4 * math.sin(self._elite_aura_t * 5.0)
        core_r = int(6 * pulse)
        core_s = pygame.Surface((core_r * 2 + 8, core_r * 2 + 8), pygame.SRCALPHA)
        pygame.draw.circle(core_s, (*_CORE, int(180 * pulse)),
                           (core_r + 4, core_r + 4), core_r + 3)
        pygame.draw.circle(core_s, (200, 240, 255, 220),
                           (core_r + 4, core_r + 4), core_r)
        surface.blit(core_s, (cx - core_r - 4, cy - core_r - 4))


# ─── Registry ─────────────────────────────────────────────────────────────────

_BOSS_ROTATION = [Lich, DemonLord, StoneGolem, VampireLord, ElderDragon, IronColossus]

_BY_LEVEL: dict[int, list] = {
    1:  [Goblin],
    2:  [Goblin, Skeleton],
    3:  [Goblin, Skeleton, Orc],
    4:  [Skeleton, Orc, Demon],
    5:  [Orc, Demon],
    10: [Skeleton, Orc, Demon],
    15: [Orc, Demon],
}


def get_enemy_types(level: int) -> list:
    if level <= 5:
        return _BY_LEVEL.get(level, [Goblin, Skeleton, Orc])
    if level <= 15:
        return [Skeleton, Orc, Demon]
    return [Orc, Demon]
