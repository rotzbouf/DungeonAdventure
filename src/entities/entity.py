import pygame


class Entity:
    def __init__(self, x: float, y: float, size: int, color: tuple):
        self.x = float(x)
        self.y = float(y)
        self.size = size
        self.color = color
        self.rect = pygame.Rect(0, 0, size, size)
        # Knockback velocity (px / s) — decays via friction each frame
        self.kbx = 0.0
        self.kby = 0.0
        # Status effects: name → {timer, tick_cd, tick_timer, magnitude}
        self._status: dict[str, dict] = {}
        self._sync_rect()

    def _sync_rect(self):
        self.rect.centerx = round(self.x)
        self.rect.centery = round(self.y)

    def apply_knockback(self, nx: float, ny: float, force: float = 240.0):
        """Impulse the entity in direction (nx, ny) with the given force (px/s)."""
        self.kbx += nx * force
        self.kby += ny * force

    # ─── Status effects ───────────────────────────────────────────────────────

    def apply_status(self, name: str, duration: float, magnitude: float = 1.0):
        """Apply or refresh a status effect.
        name      : 'poison' | 'slow' | 'burn'
        duration  : seconds the effect lasts
        magnitude : DoT damage per tick (for poison / burn), or ignored for slow
        """
        existing = self._status.get(name)
        if existing:
            existing['timer']     = max(existing['timer'], duration)
            existing['magnitude'] = max(existing['magnitude'], magnitude)
        else:
            self._status[name] = {
                'timer':      duration,
                'tick_cd':    0.7,    # seconds between DoT ticks
                'tick_timer': 0.0,
                'magnitude':  magnitude,
            }

    def tick_statuses(self, dt: float) -> int:
        """Advance all status timers. Returns total DoT damage this frame."""
        total_dmg = 0
        expired   = []
        for name, s in self._status.items():
            s['timer'] -= dt
            if s['timer'] <= 0:
                expired.append(name)
                continue
            if name in ('poison', 'burn'):
                s['tick_timer'] -= dt
                if s['tick_timer'] <= 0:
                    s['tick_timer'] += s['tick_cd']
                    total_dmg += int(s['magnitude'])
        for name in expired:
            del self._status[name]
        return total_dmg

    def has_status(self, name: str) -> bool:
        return name in self._status

    def status_tint(self) -> tuple | None:
        """Return an (R,G,B) tint colour for the active status, else None."""
        if 'poison' in self._status:
            return (30, 200, 30)
        if 'burn' in self._status:
            return (230, 80, 10)
        if 'slow' in self._status:
            return (60, 100, 220)
        return None

    def draw(self, surface: pygame.Surface, camera):
        draw_rect = camera.apply(self.rect)
        pygame.draw.rect(surface, self.color, draw_rect)
