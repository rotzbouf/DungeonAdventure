import math
import random
import pygame
from src.settings import SCREEN_WIDTH, SCREEN_HEIGHT, HUD_HEIGHT
from src.entities.enemy import Skeleton, Orc, Demon


class ParticleLayer:
    """Particle spawn, update, and rendering."""

    def _spawn_death_particles(self, enemy):
        from src.entities.enemy import Skeleton, Orc, Demon
        if isinstance(enemy, Skeleton):
            palette = [(204,196,176),(160,150,130),(240,235,220),(80,72,60)]
            count, sz = 22, (2, 4); spd_r = (50,230); life_r = (0.4, 1.1)
        elif isinstance(enemy, Demon):
            palette = [(148,0,216),(100,0,180),(252,188,0),(220,60,255)]
            count, sz = 28, (3, 7); spd_r = (80,280); life_r = (0.3, 0.9)
        elif isinstance(enemy, Orc):
            palette = [(0,52,216),(0,80,255),(80,140,255),(180,0,0)]
            count, sz = 20, (3, 5); spd_r = (60,210); life_r = (0.35, 0.8)
        else:
            palette = [(220,92,16),(180,50,0),(252,140,40),(200,70,0)]
            count, sz = 18, (2, 5); spd_r = (60,200); life_r = (0.3, 0.75)
        if getattr(enemy, 'is_elite', False):
            palette = [(220,175,0),(252,220,60)] + palette
            count   = int(count * 1.5)
        for _ in range(count):
            angle = random.uniform(0, math.pi*2)
            spd   = random.uniform(*spd_r)
            life  = random.uniform(*life_r)
            self._particles.append({
                'x': enemy.x, 'y': enemy.y,
                'vx': math.cos(angle)*spd, 'vy': math.sin(angle)*spd,
                'life': life, 'max_life': life,
                'color': random.choice(palette), 'sz': random.randint(*sz),
            })

    def _spawn_pickup_sparkle(self, px: float, py: float):
        for _ in range(8):
            angle = random.uniform(0, math.pi * 2)
            spd   = random.uniform(30, 90)
            life  = random.uniform(0.2, 0.5)
            self._particles.append({
                'x': px, 'y': py,
                'vx': math.cos(angle)*spd, 'vy': math.sin(angle)*spd - 30,
                'life': life, 'max_life': life, 'color': (255, 215, 0),
                'sz': random.randint(1, 3),
            })

    def _spawn_ice_particles(self, px: float, py: float):
        for _ in range(28):
            angle = random.uniform(0, math.pi * 2)
            spd   = random.uniform(60, 200)
            life  = random.uniform(0.3, 0.7)
            col   = random.choice([(120,210,255),(60,160,255),(200,240,255),(255,255,255)])
            self._particles.append({
                'x': px, 'y': py,
                'vx': math.cos(angle)*spd, 'vy': math.sin(angle)*spd,
                'life': life, 'max_life': life, 'color': col,
                'sz': random.randint(2, 6),
            })

    def _spawn_blink_particles(self, px: float, py: float):
        for _ in range(16):
            angle = random.uniform(0, math.pi * 2)
            spd   = random.uniform(40, 120)
            life  = random.uniform(0.2, 0.5)
            col   = random.choice([(80,180,255),(120,200,255),(255,255,255),(0,120,220)])
            self._particles.append({
                'x': px, 'y': py,
                'vx': math.cos(angle)*spd, 'vy': math.sin(angle)*spd,
                'life': life, 'max_life': life, 'color': col,
                'sz': random.randint(2, 5),
            })

    def _update_particles(self, dt: float):
        for p in self._particles:
            p['x']    += p['vx'] * dt
            p['y']    += p['vy'] * dt
            p['vy']   += 200 * dt
            p['vx']   *= max(0.0, 1 - 3 * dt)
            p['life'] -= dt
        self._particles = [p for p in self._particles if p['life'] > 0]

    def _draw_particles(self):
        play_h = SCREEN_HEIGHT - HUD_HEIGHT
        for p in self._particles:
            sx = int(p['x'] - self.camera.x)
            sy = int(p['y'] - self.camera.y)
            if not (-10 < sx < SCREEN_WIDTH + 10 and -10 < sy < play_h + 10):
                continue
            fade = p['life'] / p['max_life']
            col  = tuple(int(c * fade) for c in p['color'])
            sz   = max(1, int(p['sz'] * (0.5 + 0.5 * fade)))
            pygame.draw.circle(self.screen, col, (sx, sy), sz)
