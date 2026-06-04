import math
import random
import pygame
from src.settings import (
    TILE_SIZE,
    FIREBALL_MANA_COST, FIREBALL_SPEED, FIREBALL_MAX_RANGE, FIREBALL_RADIUS, STATUS_BURN,
    ICE_NOVA_MANA_COST, ICE_NOVA_DAMAGE, ICE_NOVA_RADIUS,
    ICE_NOVA_SLOW_DUR, ICE_NOVA_COOLDOWN, STATUS_FREEZE,
    CHAIN_LIGHTNING_MANA_COST, CHAIN_LIGHTNING_DAMAGE, CHAIN_LIGHTNING_JUMPS,
    CHAIN_LIGHTNING_RANGE, CHAIN_LIGHTNING_COOLDOWN,
    BLINK_MANA_COST, BLINK_COOLDOWN,
    BATTLE_CRY_MANA_COST, BATTLE_CRY_DURATION,
)


class SpellLayer:
    """All player spells: fireball, ice nova, chain lightning, blink, battle cry."""

    def _spell_mana_mult(self) -> float:
        """Mana cost multiplier from perks and skills (< 1.0 = cheaper)."""
        m = 1.0
        if self.player.has_perk("spell_surge"):    m *= 0.80
        if self.player.has_perk("arcane_reserve"): m *= 0.90
        if self.player.skill_tree.has_arcane_ascension() and \
                self.player.mana >= self.player.max_mana_total:
            m *= 0.50
        return m

    def _spell_dmg_mult(self) -> float:
        """Damage multiplier from perks and skills."""
        m = 1.0
        if self.player.has_perk("arcane_mastery"):   m *= 1.30
        if self.player.has_perk("arcane_overflow") and \
                self.player.mana >= self.player.max_mana_total:
            m *= 1.50
        # Skill: Elemental Fury
        ef = self.player.skill_tree.elemental_fury_mult()
        if ef > 0:
            m *= (1.0 + ef)
        # Skill: Arcane Ascension capstone — at full mana, extra 50%
        if self.player.skill_tree.has_arcane_ascension() and \
                self.player.mana >= self.player.max_mana_total:
            m *= 1.50
        return m

    def _maybe_arcane_surge(self, ex: float, ey: float):
        """Secondary echo explosion for the Arcane Surge skill."""
        import random as _rnd
        chance = self.player.skill_tree.arcane_surge_chance()
        if chance > 0 and _rnd.random() < chance:
            for enemy in self.enemies:
                if enemy.alive and math.hypot(enemy.x - ex, enemy.y - ey) < 64:
                    enemy.take_damage(int(12 * self._spell_dmg_mult()))
                    if not enemy.alive:
                        self._on_enemy_killed(enemy)

    def _cast_fireball(self):
        discount = self.player.skill_tree.fireball_mana_discount()
        cost     = max(5, int((FIREBALL_MANA_COST - discount) * self._spell_mana_mult()))
        if self.player.mana < cost:
            return
        self.player.mana -= cost

        # Target nearest living enemy; fall back to mouse cursor when none present
        nearest = min(
            (e for e in self.enemies if e.alive),
            key=lambda e: math.hypot(e.x - self.player.x, e.y - self.player.y),
            default=None,
        )
        if nearest:
            dx, dy = nearest.x - self.player.x, nearest.y - self.player.y
        else:
            mx, my = pygame.mouse.get_pos()
            wx, wy = mx + self.camera.x, my + self.camera.y
            dx, dy = wx - self.player.x, wy - self.player.y
        dist = math.hypot(dx, dy)
        if dist < 1.0:
            dx, dy, dist = math.cos(self.player.attack_angle), math.sin(self.player.attack_angle), 1.0
        nx, ny = dx / dist, dy / dist

        self.projectiles.append({
            'x': self.player.x, 'y': self.player.y,
            'vx': nx * FIREBALL_SPEED, 'vy': ny * FIREBALL_SPEED,
            'traveled': 0.0, 'alive': True,
            'exploding': False, 'exp_timer': 0.0,
            'type': 'fireball',
        })

    def _cast_ice_nova(self):
        if not self.player.skill_tree.has_ice_nova():
            return
        ice_cost = max(5, int(ICE_NOVA_MANA_COST * self._spell_mana_mult()))
        if self.player.mana < ice_cost or self._ice_nova_cd > 0:
            return
        self.player.mana -= ice_cost
        self._ice_nova_cd = ICE_NOVA_COOLDOWN

        px, py = self.player.x, self.player.y
        # AoE around player
        for enemy in self.enemies:
            if not enemy.alive:
                continue
            d = math.hypot(enemy.x - px, enemy.y - py)
            if d < ICE_NOVA_RADIUS:
                raw = int((ICE_NOVA_DAMAGE + random.randint(-3, 5)) * self._spell_dmg_mult())
                dmg = enemy.take_damage(raw)
                enemy.apply_status(STATUS_FREEZE, ICE_NOVA_SLOW_DUR)
                self._dmg_nums.append({
                    'x': enemy.x, 'y': enemy.y - 22,
                    'vx': random.uniform(-8, 8),
                    'text': str(dmg),
                    'timer': 0.9, 'max_timer': 0.9,
                    'color': (120, 210, 255), 'big': False,
                })
                if not enemy.alive:
                    self._on_enemy_killed(enemy)

        # Skill: Arcane Surge — chance to trigger echo at player position
        self._maybe_arcane_surge(px, py)

        # Ice burst visual — add as a projectile-style entry
        self.projectiles.append({
            'type': 'ice_nova', 'x': px, 'y': py,
            'alive': True, 'exploding': True, 'exp_timer': 0.45,
        })
        self._spawn_ice_particles(px, py)

    def _cast_chain_lightning(self):
        if not self.player.skill_tree.has_chain_lightning():
            return
        chain_cost = max(5, int(CHAIN_LIGHTNING_MANA_COST * self._spell_mana_mult()))
        if self.player.mana < chain_cost or self._chain_cd > 0:
            return
        self.player.mana -= chain_cost
        self._chain_cd = CHAIN_LIGHTNING_COOLDOWN

        alive = [e for e in self.enemies if e.alive]
        if not alive:
            return

        cur_x, cur_y = self.player.x, self.player.y
        dmg_base = float(CHAIN_LIGHTNING_DAMAGE) * self._spell_dmg_mult()
        hit_set      = set()
        self._lightning_arcs.clear()

        for _ in range(CHAIN_LIGHTNING_JUMPS):
            candidates = sorted(
                [e for e in alive if id(e) not in hit_set],
                key=lambda e: math.hypot(e.x - cur_x, e.y - cur_y))
            if not candidates:
                break
            target = candidates[0]
            if math.hypot(target.x - cur_x, target.y - cur_y) > CHAIN_LIGHTNING_RANGE:
                break
            hit_set.add(id(target))
            raw = int(dmg_base) + random.randint(-4, 4)
            dmg = target.take_damage(raw)
            self._lightning_arcs.append({
                'x1': cur_x, 'y1': cur_y, 'x2': target.x, 'y2': target.y,
                'timer': 0.25,
            })
            self._dmg_nums.append({
                'x': target.x, 'y': target.y - 22,
                'vx': random.uniform(-10, 10),
                'text': str(dmg),
                'timer': 0.9, 'max_timer': 0.9,
                'color': (180, 220, 255), 'big': False,
            })
            if not target.alive:
                self._on_enemy_killed(target)
            cur_x, cur_y = target.x, target.y
            dmg_base    *= 0.70   # 30% reduction per jump

    def _cast_blink(self):
        if not self.player.skill_tree.has_blink():
            return
        discount = self.player.skill_tree.blink_mana_discount()
        cost     = max(5, BLINK_MANA_COST - discount)
        if self.player.mana < cost or self._blink_cd > 0:
            return
        self.player.mana -= cost
        self._blink_cd = BLINK_COOLDOWN

        mx, my = pygame.mouse.get_pos()
        wtx    = int((mx + self.camera.x) / TILE_SIZE)
        wty    = int((my + self.camera.y) / TILE_SIZE)

        # Find nearest walkable tile to the click
        landed = False
        for radius in range(6):
            for dx in range(-radius, radius + 1):
                for dy in range(-radius, radius + 1):
                    if abs(dx) != radius and abs(dy) != radius:
                        continue
                    tx, ty = wtx + dx, wty + dy
                    if self.dungeon.is_walkable(tx, ty):
                        ox = self.player.x; oy = self.player.y
                        self.player.x = float(tx * TILE_SIZE + TILE_SIZE // 2)
                        self.player.y = float(ty * TILE_SIZE + TILE_SIZE // 2)
                        self.player._sync_rect()
                        self._spawn_blink_particles(ox, oy)
                        self._spawn_blink_particles(self.player.x, self.player.y)
                        landed = True
                        break
                if landed:
                    break
            if landed:
                break

    def _cast_battle_cry(self):
        if not self.player.skill_tree.level("battle_cry") > 0:
            return
        if self.player.mana < BATTLE_CRY_MANA_COST:
            return
        self.player.mana -= BATTLE_CRY_MANA_COST
        self._battle_cry_timer = BATTLE_CRY_DURATION
        # Visual — golden ring burst
        for _ in range(20):
            angle = random.uniform(0, math.pi * 2)
            spd   = random.uniform(60, 150)
            life  = random.uniform(0.3, 0.7)
            self._particles.append({
                'x': self.player.x, 'y': self.player.y,
                'vx': math.cos(angle) * spd, 'vy': math.sin(angle) * spd,
                'life': life, 'max_life': life,
                'color': (252, 200, 20), 'sz': random.randint(2, 5),
            })
