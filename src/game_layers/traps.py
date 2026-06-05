import math
import pygame
from src.settings import SCREEN_WIDTH, SCREEN_HEIGHT, HUD_HEIGHT, TILE_SIZE

# ── Trap sprite cache ──────────────────────────────────────────────────────────
_trap_surfs: dict[str, pygame.Surface | None] = {}


def _get_trap_surf(phase: str) -> pygame.Surface | None:
    """Load and cache the 40×40 trap sprite for the given phase."""
    if phase in _trap_surfs:
        return _trap_surfs[phase]
    import sys
    from pathlib import Path
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS) / "assets" / "traps"   # type: ignore
    else:
        base = Path(__file__).parent.parent.parent / "assets" / "traps"
    fname = {"idle": "trap_idle.png",
             "warning": "trap_warning.png",
             "active": "trap_active.png"}.get(phase, "trap_idle.png")
    path  = base / fname
    if path.exists():
        try:
            raw  = pygame.image.load(str(path)).convert_alpha()
            surf = pygame.transform.smoothscale(raw, (TILE_SIZE, TILE_SIZE))
            _trap_surfs[phase] = surf
            return surf
        except Exception:
            pass
    _trap_surfs[phase] = None
    return None


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
            sx = tx * TILE_SIZE - int(self.camera.x)
            sy = ty * TILE_SIZE - int(self.camera.y)
            if not (-TILE_SIZE < sx < SCREEN_WIDTH + TILE_SIZE and
                    -TILE_SIZE < sy < play_h + TILE_SIZE):
                continue

            spr = _get_trap_surf(phase)
            if spr is not None:
                self._draw_trap_sprite(spr, sx, sy, phase)
            else:
                self._draw_trap_procedural(sx, sy, phase)

    def _draw_trap_sprite(self, spr: pygame.Surface,
                           sx: int, sy: int, phase: str):
        """Draw the DCSS trap PNG with phase-appropriate tinting/glow."""
        cx = sx + TILE_SIZE // 2
        cy = sy + TILE_SIZE // 2

        if phase == "idle":
            # Semi-transparent — blends with the floor, easy to miss
            tinted = spr.copy()
            tinted.set_alpha(150)
            self.screen.blit(tinted, (sx, sy))

        elif phase == "warning":
            # Full sprite + pulsing red glow — plate is activating
            self.screen.blit(spr, (sx, sy))
            pulse = 0.5 + 0.5 * abs(math.sin(self._time * 14.0))
            gw    = TILE_SIZE
            gs    = pygame.Surface((gw * 2, gw * 2), pygame.SRCALPHA)
            pygame.draw.circle(gs, (255, 60, 0, int(90 * pulse)), (gw, gw), gw)
            self.screen.blit(gs, (cx - gw, cy - gw))

        else:  # active
            # Full sprite, bright red flash, radial burst
            self.screen.blit(spr, (sx, sy))
            flash = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
            flash.fill((200, 0, 0, 110))
            self.screen.blit(flash, (sx, sy))
            br = TILE_SIZE
            bs = pygame.Surface((br * 2, br * 2), pygame.SRCALPHA)
            pygame.draw.circle(bs, (255, 80, 0, 130), (br, br), br)
            self.screen.blit(bs, (cx - br, cy - br))

    def _draw_trap_procedural(self, sx: int, sy: int, phase: str):
        """Fallback procedural drawing when PNG sprites are absent."""
        cx, cy = sx + TILE_SIZE // 2, sy + TILE_SIZE // 2
        if phase == "idle":
            for ox, oy in [(-5, 0), (5, 0), (0, -5), (0, 5)]:
                pygame.draw.circle(self.screen, (80, 20, 20), (cx+ox, cy+oy), 2)
        elif phase == "warning":
            pulse = abs(math.sin(self._time * 14.0))
            ws    = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
            ws.fill((220, 0, 0, int(50 + 50 * pulse)))
            self.screen.blit(ws, (sx, sy))
            for ox, oy in [(-7, 0), (7, 0), (0, -7), (0, 7)]:
                pygame.draw.circle(self.screen, (220, 0, 0), (cx+ox, cy+oy), 3)
        else:
            as_ = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
            as_.fill((180, 0, 0, 90))
            self.screen.blit(as_, (sx, sy))
            for ox, oy, ex_, ey_ in [(0,-4,0,-13),(0,4,0,13),(-4,0,-13,0),(4,0,13,0)]:
                pygame.draw.line(self.screen, (120, 10, 10),
                                 (cx+ox, cy+oy), (cx+ex_, cy+ey_), 3)
                pygame.draw.line(self.screen, (220, 50, 50),
                                 (cx+ox, cy+oy), (cx+ex_, cy+ey_), 1)
