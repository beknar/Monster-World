import pygame
import src.settings as settings
from src.settings import TILE_SIZE


class Camera:
    def __init__(self, map_width_tiles: int, map_height_tiles: int):
        self.map_width = map_width_tiles * TILE_SIZE
        self.map_height = map_height_tiles * TILE_SIZE
        self.x = 0.0
        self.y = 0.0

    def update(self, target_rect: pygame.Rect):
        """Center camera on target, clamped to map bounds.
        If the map is smaller than the screen, center the map on screen."""
        sw, sh = settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT
        self.x = target_rect.centerx - sw // 2
        self.y = target_rect.centery - sh // 2

        # If map fits within the screen, center it (no scrolling on that axis)
        if self.map_width <= sw:
            self.x = -(sw - self.map_width) // 2
        else:
            self.x = max(0, min(self.x, self.map_width - sw))

        if self.map_height <= sh:
            self.y = -(sh - self.map_height) // 2
        else:
            self.y = max(0, min(self.y, self.map_height - sh))

    def apply(self, rect: pygame.Rect) -> pygame.Rect:
        """Convert world rect to screen rect."""
        return pygame.Rect(rect.x - int(self.x), rect.y - int(self.y),
                          rect.width, rect.height)

    def apply_pos(self, pos: tuple) -> tuple:
        """Convert world position to screen position."""
        return (pos[0] - int(self.x), pos[1] - int(self.y))

    def reverse(self, screen_pos: tuple) -> tuple:
        """Convert screen position to world position."""
        return (screen_pos[0] + int(self.x), screen_pos[1] + int(self.y))

    def get_visible_rect(self) -> pygame.Rect:
        """Return the world-space rectangle currently visible on screen."""
        return pygame.Rect(int(self.x), int(self.y),
                          settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT)
