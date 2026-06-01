import math
import pygame
from src.settings import SCREEN_WIDTH, SCREEN_HEIGHT, HUD_HEIGHT, TILE_SIZE


class TrapLayer:
    """Spike trap update and rendering."""

    def _update_traps(self, dt: float):
        if not self.dungeon or not self.dungeon.trap_positions:
            return
        self._spike_timer  -= dt
        self._trap_dmg_cd   = max(0.0, self._trap_dmg_cd - dt)
        if self._spike_timer <= 0:
            if self._spike_phase == "idle":
                self._spike_phase = "warning"; self._spike_timer = 0.50
            elif self._spike_phase == "warning":
                self._spike_phase = "active";  self._spike_timer = 0.70
            else:
                self._spike_phase = "idle";    self._spike_timer = 2.5
        if self._spike_phase == "active" and self._trap_dmg_cd <= 0:
            ptx = int(self.player.x // TILE_SIZE)
            pty = int(self.player.y // TILE_SIZE)
            if (ptx, pty) in set(self.dungeon.trap_positions):
                dmg = self.player.take_damage(10)
                if dmg > 0:
                    self._dmg_nums.append({
                        'x': self.player.x, 'y': self.player.y - 28,
                        'vx': 0.0, 'text': str(dmg),
                        'timer': 0.9, 'max_timer': 0.9,
                        'color': (220, 30, 30), 'big': False,
                    })
                    self._shake_t   = 0.14; self._shake_int = 4.0
                    self._trap_dmg_cd = 0.8

    def _draw_traps(self):
        if not self.dungeon or not self.dungeon.trap_positions:
            return
        play_h = SCREEN_HEIGHT - HUD_HEIGHT
        phase  = self._spike_phase
        for tx, ty in self.dungeon.trap_positions:
            sx = tx*TILE_SIZE - int(self.camera.x)
            sy = ty*TILE_SIZE - int(self.camera.y)
            if not (-TILE_SIZE < sx < SCREEN_WIDTH+TILE_SIZE and
                    -TILE_SIZE < sy < play_h+TILE_SIZE):
                continue
            cx, cy = sx+TILE_SIZE//2, sy+TILE_SIZE//2
            if phase == "idle":
                for ox, oy in [(-5,0),(5,0),(0,-5),(0,5)]:
                    pygame.draw.circle(self.screen, (80,20,20), (cx+ox,cy+oy), 2)
            elif phase == "warning":
                pulse = abs(math.sin(self._time*14.0))
                a = int(140+115*pulse)
                ws = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
                ws.fill((220,0,0,min(255,a//3)))
                self.screen.blit(ws, (sx,sy))
                for ox, oy in [(-7,0),(7,0),(0,-7),(0,7)]:
                    pygame.draw.circle(self.screen, (220,0,0), (cx+ox,cy+oy), 3)
            else:
                as_ = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
                as_.fill((180,0,0,90))
                self.screen.blit(as_, (sx,sy))
                for ox, oy, ex_, ey_ in [(0,-4,0,-13),(0,4,0,13),(-4,0,-13,0),(4,0,13,0)]:
                    pygame.draw.line(self.screen, (120,10,10),
                                     (cx+ox,cy+oy),(cx+ex_,cy+ey_), 3)
                    pygame.draw.line(self.screen, (220,50,50),
                                     (cx+ox,cy+oy),(cx+ex_,cy+ey_), 1)
