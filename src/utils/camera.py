import pygame
from src.settings import SCREEN_WIDTH, SCREEN_HEIGHT, HUD_HEIGHT, TILE_SIZE


class Camera:
    def __init__(self):
        self.x = 0.0
        self.y = 0.0

    def update(self, target, dungeon=None, dt: float = None):
        play_h = SCREEN_HEIGHT - HUD_HEIGHT
        tx = target.x - SCREEN_WIDTH / 2
        ty = target.y - play_h / 2
        if dungeon:
            max_x = dungeon.width  * TILE_SIZE - SCREEN_WIDTH
            max_y = dungeon.height * TILE_SIZE - play_h
            tx = max(0.0, min(tx, float(max_x)))
            ty = max(0.0, min(ty, float(max_y)))
        if dt is None:
            self.x, self.y = tx, ty
        else:
            t = min(1.0, 9.0 * dt)
            self.x += (tx - self.x) * t
            self.y += (ty - self.y) * t

    def apply(self, rect):
        return rect.move(-int(self.x), -int(self.y))

    def apply_point(self, x, y):
        return x - self.x, y - self.y
