import pygame
from src.settings import SCALE_FACTOR

class SpriteSheet:
    """Load a sprite sheet image and extract frames from it."""

    def __init__(self, path: str):
        """Load sprite sheet from file path."""
        self.sheet = pygame.image.load(path).convert_alpha()

    def get_frame(self, x: int, y: int, width: int, height: int, scale: int = SCALE_FACTOR) -> pygame.Surface:
        """Extract a single frame at pixel position (x, y) with given dimensions.
        Scales the frame by the given scale factor. If scale=1, no scaling."""
        frame = pygame.Surface((width, height), pygame.SRCALPHA)
        frame.blit(self.sheet, (0, 0), (x, y, width, height))
        if scale != 1:
            frame = pygame.transform.scale(frame, (width * scale, height * scale))
        return frame

    def get_strip(self, row: int, frame_width: int, frame_height: int,
                  num_frames: int, scale: int = SCALE_FACTOR) -> list:
        """Extract a horizontal strip of frames from a given row.
        row: which row (0-indexed), frame_width/height: size of each frame.
        Returns list of scaled pygame Surfaces."""
        frames = []
        y = row * frame_height
        for i in range(num_frames):
            x = i * frame_width
            frames.append(self.get_frame(x, y, frame_width, frame_height, scale))
        return frames
