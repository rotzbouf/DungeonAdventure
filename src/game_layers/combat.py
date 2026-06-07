import math
import random
import pygame
from src.settings import (TILE_SIZE, ARROW_SPEED, YELLOW, WHITE, WHIRLWIND_MANA_COST)
from src.items.item import (GoldPile, random_item, random_equip,
                              QUALITY_RARE, QUALITY_UNIQUE, _ilvl_and_mult)
from src.entities.enemy import Skeleton, Orc, Demon
from src.locale import t, t_quest_name


def _nearest_enemy(player, enemies):
    """Return the closest alive enemy to *player*, or None."""
    alive = [e for e in enemies if e.alive]
    if not alive:
        return None
    return min(alive, key=lambda e: math.hypot(e.x - player.x, e.y - player.y))


class CombatLayer:
    """Melee, arrows, whirlwind, damage resolution, loot drops, kill handling."""

    def _player_attack(self):
        hit_list = self.player.try_attack(self.enemies)
        self._resolve_hits(hit_list)
        if hit_list:
            self._hitstop_t = max(self._hitstop_t, 0.07)

    def _fire_arrow(self):
        if self.player._attack_timer > 0:
            return
        self.player._attack_timer = self.player.effective_cooldown
        self.player._attack_anim  = 0.2

        target = _nearest_enemy(self.player, self.enemies)
        if target is not None:
            dx, dy = target.x - self.player.x, target.y - self.player.y
        else:
            dx, dy = math.cos(self.player.attack_angle), math.sin(self.player.attack_angle)
        dist = math.hypot(dx, dy) or 1.0
        nx, ny = dx / dist, dy / dist
        angle  = math.atan2(ny, nx)
        self.player.attack_angle = angle

        self.projectiles.append({
            'x': self.player.x, 'y': self.player.y,
            'vx': nx * ARROW_SPEED, 'vy': ny * ARROW_SPEED,
            'traveled': 0.0, 'alive': True,
            'type': 'arrow',
            'damage': self.player.bow_attack,
            'angle': angle,
        })

    def _cast_whirlwind(self):
        """360° melee burst — hits all enemies in attack range."""
        if self.player.mana < WHIRLWIND_MANA_COST:
            return
        hit_list = self.player.try_attack(self.enemies, whirlwind=True)
        if not hit_list:
            return
        self.player.mana -= WHIRLWIND_MANA_COST
        self._resolve_hits(hit_list)
        # Bigger flash for whirlwind
        self.player._attack_anim = 0.35
        self._hitstop_t = max(self._hitstop_t, 0.10)

    def _resolve_hits(self, hit_list: list, dmg_mult: float = 1.0):
        """Apply melee hits, crits, life steal, thorns, knock-back."""
        # Battle Cry bonus
        if self._battle_cry_timer > 0:
            dmg_mult *= 1.0 + self.player.skill_tree.battle_cry_bonus()

        for enemy in hit_list:
            raw = int((self.player.attack + random.randint(-2, 4)) * dmg_mult)
            # Perk: Execute — bonus damage to enemies below 25% HP
            if self.player.has_perk("execute") and enemy.hp < enemy.max_hp * 0.25:
                raw = int(raw * 1.60)
            is_crit = random.uniform(0, 100) < self.player.crit_chance
            if is_crit:
                # Perk: Precision — crits deal 3× (base is 2×)
                crit_mult = 3.0 if self.player.has_perk("precision") else 2.0
                raw = int(raw * crit_mult)
            dmg = enemy.take_damage(raw)

            self._dmg_nums.append({
                'x': enemy.x, 'y': enemy.y - 22,
                'vx': random.uniform(-12, 12),
                'text': str(dmg),
                'timer': 1.1, 'max_timer': 1.1,
                'color': YELLOW if is_crit else WHITE,
                'big': is_crit,
            })

            if dmg > 0 and self.player.life_steal > 0:
                self.player.heal(max(1, int(dmg * self.player.life_steal / 100)))

            # Assassination — extra crit damage multiplier
            if is_crit:
                ab = self.player.skill_tree.assassination_crit_bonus()
                if ab > 0:
                    bonus = int(dmg * ab)
                    enemy.take_damage(bonus)
                    dmg += bonus

            # Iron Fist — stun on melee hit
            stun_ch = self.player.skill_tree.iron_fist_stun_chance()
            if stun_ch > 0 and random.random() < stun_ch:
                enemy.apply_status('stun', 0.7)

            # Poison Blade
            pb = self.player.skill_tree.poison_blade_chance()
            if pb > 0 and random.random() < pb:
                enemy.apply_status('poison', 4.0, 3.0)

            dist = math.hypot(enemy.x - self.player.x, enemy.y - self.player.y)
            if dist > 0:
                enemy.apply_knockback(
                    (enemy.x - self.player.x) / dist,
                    (enemy.y - self.player.y) / dist, 362.0)

            if not enemy.alive:
                self._on_enemy_killed(enemy)

    def _on_enemy_killed(self, enemy):
        leveled = self.player.gain_xp(enemy.XP_REWARD)
        if leveled:
            self.hud.notify_level_up()
        self._spawn_death_particles(enemy)
        if getattr(enemy, 'is_boss', False):
            self._drop_boss_loot(enemy)
            self.player.defeated_bosses.add(type(enemy).__name__)
        else:
            self._drop_loot(enemy)
        # Perk: Bloodlust — restore HP on kill
        if self.player.has_perk("bloodlust"):
            self.player.heal(8)
        # Skill: Death Mark — killed enemy explodes, damaging nearby foes
        if self.player.skill_tree.has_death_mark():
            boom_dmg = int(enemy.MAX_HP * 0.20)
            if boom_dmg > 0:
                for other in self.enemies:
                    if other is not enemy and other.alive:
                        dist = math.hypot(other.x - enemy.x, other.y - enemy.y)
                        if dist < 80:
                            other.take_damage(boom_dmg)
                            if not other.alive:
                                self._on_enemy_killed(other)
        # Perk: Momentum — brief speed boost after kill
        if self.player.has_perk("momentum"):
            self.player.apply_status("haste", 3.0, 25.0)   # 3s, 25% speed bonus

        # Quest notifications
        done = self.quest_log.notify("kill", type(enemy).__name__)
        if getattr(enemy, 'is_elite', False):
            done += self.quest_log.notify("kill", "Elite")
        if getattr(enemy, 'quest_id', None):
            done += self.quest_log.notify("bounty", enemy.quest_id)
        self._apply_quest_rewards(done)

    def _scatter_pos(self, px: float, py: float, spread: float) -> tuple[float, float]:
        """
        Pick a random offset position within *spread* pixels of (px, py) that
        lands on a walkable tile, falling back to (px, py) itself — guaranteed
        walkable since the enemy died there — if the offset would drop the
        item inside a wall.
        """
        nx = px + random.uniform(-spread, spread)
        ny = py + random.uniform(-spread, spread)
        tx, ty = int(nx // TILE_SIZE), int(ny // TILE_SIZE)
        if self.dungeon.is_walkable(tx, ty):
            return nx, ny
        return px, py

    def _drop_boss_loot(self, enemy):
        from src.items.item import _ilvl_and_mult
        px, py = enemy.x, enemy.y
        lvl    = self.dungeon_level
        gf     = 1.0 + self.player.gold_find_bonus / 100
        ilvl, depth_mult = _ilvl_and_mult(lvl)

        # Guaranteed unique item
        loot = random_equip(0, 0, ilvl, quality=QUALITY_UNIQUE, depth_mult=depth_mult)
        loot._reposition(px, py)
        self.items.append(loot)
        # Two rare-quality bonus drops
        for _ in range(2):
            extra = random_equip(0, 0, ilvl, quality=QUALITY_RARE, depth_mult=depth_mult)
            extra._reposition(*self._scatter_pos(px, py, 24))
            self.items.append(extra)
        # Gold scatter
        for _ in range(3):
            gold = GoldPile(0, 0, int(random.randint(10, 25) * lvl * gf))
            gold._reposition(*self._scatter_pos(px, py, 28))
            self.items.append(gold)

        boss_name = getattr(enemy, 'BOSS_NAME', type(enemy).__name__)
        self.hud.notify_quest(t("game.boss_defeated", name=boss_name))
        self._shake_t   = max(self._shake_t,   0.9)
        self._shake_int = max(self._shake_int, 2.5)

    def _drop_loot(self, enemy):
        from src.entities.enemy import Skeleton, Orc, Demon
        px, py = enemy.x, enemy.y
        lvl    = self.dungeon_level
        q_bonus = (40 if isinstance(enemy, Demon) else
                   20 if isinstance(enemy, Orc)   else
                   10 if isinstance(enemy, Skeleton) else 0)
        if getattr(enemy, 'is_elite', False):
            q_bonus += 30
        if random.random() < enemy.LOOT_CHANCE:
            item = random_item(0, 0, lvl, quality_bonus=q_bonus, floor=lvl)
            item._reposition(*self._scatter_pos(px, py, 14))
            self.items.append(item)
        base_gold   = random.randint(1, 4) * lvl
        gf_mult     = 1.0 + self.player.gold_find_bonus / 100
        gold        = GoldPile(0, 0, int(base_gold * gf_mult))
        gold._reposition(*self._scatter_pos(px, py, 10))
        self.items.append(gold)
        if isinstance(enemy, Demon) and random.random() < 0.45:
            extra = random_item(0, 0, lvl, quality_bonus=60, floor=lvl)
            extra._reposition(*self._scatter_pos(px, py, 18))
            self.items.append(extra)
