import math
import random
import pygame
from src.settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, HUD_HEIGHT, TILE_SIZE, YELLOW, WHITE,
    FIREBALL_SPEED, FIREBALL_MAX_RANGE, FIREBALL_RADIUS, FIREBALL_DAMAGE, STATUS_BURN,
    ARROW_SPEED, ARROW_MAX_RANGE, ICE_NOVA_RADIUS,
)


class ProjectileLayer:
    """Projectile update, explosion, and rendering (fireball, arrow, ice nova, lightning)."""

    def _update_projectiles(self, dt: float):
        keep = []
        for fb in self.projectiles:
            if fb.get('type') == 'arrow':
                fb['x'] += fb['vx'] * dt
                fb['y'] += fb['vy'] * dt
                fb['traveled'] += ARROW_SPEED * dt
                atx = int(fb['x'] // TILE_SIZE)
                aty = int(fb['y'] // TILE_SIZE)
                if (not self.dungeon.is_walkable(atx, aty)
                        or fb['traveled'] >= ARROW_MAX_RANGE):
                    fb['alive'] = False
                    keep.append(fb)
                    continue
                hit = False
                for enemy in self.enemies:
                    if not enemy.alive:
                        continue
                    if math.hypot(enemy.x - fb['x'], enemy.y - fb['y']) < enemy.size // 2 + 6:
                        raw = fb['damage'] + random.randint(-3, 5)
                        is_crit = random.uniform(0, 100) < self.player.crit_chance
                        if is_crit:
                            raw = int(raw * 2)
                        dmg = enemy.take_damage(raw)
                        if self.player.life_steal > 0:
                            self.player.heal(max(1, int(dmg * self.player.life_steal / 100)))
                        ed = math.hypot(enemy.x - fb['x'], enemy.y - fb['y'])
                        if ed > 0:
                            enemy.apply_knockback(
                                (enemy.x - fb['x']) / ed,
                                (enemy.y - fb['y']) / ed,
                                250.0)
                        self._dmg_nums.append({
                            'x': enemy.x, 'y': enemy.y - 22,
                            'vx': random.uniform(-12, 12),
                            'text': str(dmg),
                            'timer': 1.1, 'max_timer': 1.1,
                            'color': YELLOW if is_crit else WHITE, 'big': is_crit,
                        })
                        fb['alive'] = False
                        if not enemy.alive:
                            self._on_enemy_killed(enemy)
                        hit = True
                        break
                keep.append(fb)
                continue

            if fb.get('type') in ('ice_nova',):
                fb['exp_timer'] -= dt
                if fb['exp_timer'] <= 0:
                    fb['alive'] = False
                else:
                    keep.append(fb)
                continue

            if fb.get('exploding'):
                fb['exp_timer'] -= dt
                if fb['exp_timer'] <= 0:
                    fb['alive'] = False
                else:
                    keep.append(fb)
                continue

            step = FIREBALL_SPEED * dt
            fb['x'] += fb['vx'] * dt
            fb['y'] += fb['vy'] * dt
            fb['traveled'] += step

            tx = int(fb['x'] // TILE_SIZE)
            ty = int(fb['y'] // TILE_SIZE)
            if not self.dungeon.is_walkable(tx, ty) or fb['traveled'] >= FIREBALL_MAX_RANGE:
                fb['exploding'] = True
                fb['exp_timer'] = 0.30
                self._fireball_explode(fb)
                keep.append(fb)
                continue

            hit_any = False
            for enemy in self.enemies:
                if not enemy.alive:
                    continue
                if math.hypot(enemy.x - fb['x'], enemy.y - fb['y']) < enemy.size // 2 + 8:
                    self._fireball_explode(fb)
                    fb['exploding'] = True
                    fb['exp_timer'] = 0.30
                    hit_any = True
                    break
            if hit_any:
                keep.append(fb)
                continue
            keep.append(fb)
        self.projectiles = [f for f in keep if f['alive']]

    def _fireball_explode(self, fb: dict):
        ex, ey = fb['x'], fb['y']
        dmg_mult = self.player.skill_tree.fireball_damage_mult()
        for _ in range(22):
            angle = random.uniform(0, math.pi * 2)
            spd   = random.uniform(80, 260)
            life  = random.uniform(0.25, 0.65)
            col   = random.choice([(252, 120, 20), (252, 60, 0), (252, 200, 60)])
            self._particles.append({
                'x': ex, 'y': ey,
                'vx': math.cos(angle) * spd, 'vy': math.sin(angle) * spd - 40,
                'life': life, 'max_life': life,
                'color': col, 'sz': random.randint(3, 7),
            })
        self._hitstop_t = max(self._hitstop_t, 0.05)
        for enemy in self.enemies:
            if not enemy.alive:
                continue
            if math.hypot(enemy.x - ex, enemy.y - ey) > FIREBALL_RADIUS:
                continue
            raw = int((FIREBALL_DAMAGE + random.randint(-4, 8)) * dmg_mult)
            dmg = enemy.take_damage(raw)
            enemy.apply_status(STATUS_BURN, 3.0, 5.0)
            self._dmg_nums.append({
                'x': enemy.x, 'y': enemy.y - 22,
                'vx': random.uniform(-8, 8),
                'text': str(dmg),
                'timer': 0.95, 'max_timer': 0.95,
                'color': (252, 130, 20), 'big': False,
            })
            if not enemy.alive:
                self._on_enemy_killed(enemy)

    def _draw_projectiles(self):
        play_h = SCREEN_HEIGHT - HUD_HEIGHT
        for fb in self.projectiles:
            sx = int(fb['x'] - self.camera.x)
            sy = int(fb['y'] - self.camera.y)
            if not (-60 < sx < SCREEN_WIDTH+60 and -60 < sy < play_h+60):
                continue
            ftype = fb.get('type', 'fireball')

            if ftype == 'arrow':
                if not fb.get('alive', True):
                    continue
                ang = fb.get('angle', 0.0)
                cos_a, sin_a = math.cos(ang), math.sin(ang)
                tip_x = int(sx + cos_a * 5)
                tip_y = int(sy + sin_a * 5)
                tail_x = int(sx - cos_a * 13)
                tail_y = int(sy - sin_a * 13)
                # Shadow
                pygame.draw.line(self.screen, (0, 0, 0),
                                 (tail_x + 1, tail_y + 1), (tip_x + 1, tip_y + 1), 3)
                # Shaft
                pygame.draw.line(self.screen, (140, 90, 30),
                                 (tail_x, tail_y), (tip_x, tip_y), 2)
                # Tip
                pygame.draw.circle(self.screen, (200, 190, 160), (tip_x, tip_y), 3)
                # Fletching
                fa1 = ang + 2.5
                fa2 = ang - 2.5
                fl  = 7
                pygame.draw.line(self.screen, (160, 50, 50),
                                 (tail_x, tail_y),
                                 (int(tail_x + math.cos(fa1) * fl),
                                  int(tail_y + math.sin(fa1) * fl)), 2)
                pygame.draw.line(self.screen, (160, 50, 50),
                                 (tail_x, tail_y),
                                 (int(tail_x + math.cos(fa2) * fl),
                                  int(tail_y + math.sin(fa2) * fl)), 2)
                continue

            if ftype == 'ice_nova':
                t = 1.0 - fb['exp_timer'] / 0.45
                r = int(ICE_NOVA_RADIUS * t)
                a = int(200 * (1.0 - t))
                if r > 0:
                    gs = pygame.Surface((r*2+4, r*2+4), pygame.SRCALPHA)
                    pygame.draw.circle(gs, (120,200,255,a), (r+2,r+2), r, 3)
                    pygame.draw.circle(gs, (200,240,255,min(255,a+60)), (r+2,r+2), max(1,r//4))
                    self.screen.blit(gs, (sx-r-2, sy-r-2))
                continue

            if fb.get('exploding'):
                t = 1.0 - fb['exp_timer'] / 0.30
                r = int(FIREBALL_RADIUS * t * 0.9)
                a = int(220 * (1.0-t))
                if r > 0:
                    gs = pygame.Surface((r*2+4, r*2+4), pygame.SRCALPHA)
                    pygame.draw.circle(gs, (252,150,20,a), (r+2,r+2), r)
                    pygame.draw.circle(gs, (252,240,60,min(255,a+80)), (r+2,r+2), max(1,r//3))
                    self.screen.blit(gs, (sx-r-2, sy-r-2))
            else:
                pygame.draw.circle(self.screen, (252,60,0), (sx,sy), 7)
                pygame.draw.circle(self.screen, (252,220,60), (sx,sy), 4)
                gs = pygame.Surface((28,28), pygame.SRCALPHA)
                pygame.draw.circle(gs, (252,120,20,90), (14,14), 14)
                self.screen.blit(gs, (sx-14,sy-14))

    def _draw_lightning_arcs(self):
        """Draw chain-lightning arcs with a jagged line."""
        play_h = SCREEN_HEIGHT - HUD_HEIGHT
        for arc in self._lightning_arcs:
            fade = arc['timer'] / 0.25
            a    = int(220 * fade)
            x1 = int(arc['x1'] - self.camera.x)
            y1 = int(arc['y1'] - self.camera.y)
            x2 = int(arc['x2'] - self.camera.x)
            y2 = int(arc['y2'] - self.camera.y)
            if not any(-60 < v < SCREEN_WIDTH+60 for v in (x1, x2)):
                continue
            # Jagged lightning: split line into segments with random offsets
            segs = 8
            pts  = [(x1, y1)]
            for i in range(1, segs):
                t  = i / segs
                mx = int(x1 + (x2-x1)*t)
                my = int(y1 + (y2-y1)*t)
                jitter = int(12 * fade)
                pts.append((mx + random.randint(-jitter, jitter),
                             my + random.randint(-jitter, jitter)))
            pts.append((x2, y2))
            col = (min(255, 180+int(75*fade)), min(255, 220+int(35*fade)), 255)
            for i in range(len(pts)-1):
                pygame.draw.line(self.screen, (0,0,0), pts[i], pts[i+1], 3)
                pygame.draw.line(self.screen, col,     pts[i], pts[i+1], 1)
