import os
import pygame
from src.settings import DIR_DOWN, DIR_LEFT, DIR_RIGHT, DIR_UP, DIR_NAMES, SCALE_FACTOR


class Animation:
    """Cycles through a list of frames at a given speed."""

    def __init__(self, frames: list, speed: float = 0.15):
        self.frames = frames
        self.speed = speed  # seconds per frame
        self.timer = 0.0
        self.index = 0

    def update(self, dt: float):
        self.timer += dt
        if self.timer >= self.speed:
            self.timer -= self.speed
            self.index = (self.index + 1) % len(self.frames)

    def get_frame(self) -> pygame.Surface:
        return self.frames[self.index]

    def reset(self):
        self.timer = 0.0
        self.index = 0


class AnimationSet:
    """Manages multiple named animations with directional variants.
    Usage: add("idle", DIR_DOWN, animation), then play("idle", DIR_DOWN)."""

    def __init__(self):
        self.animations = {}  # (name, direction) -> Animation
        self.current_name = None
        self.current_dir = 0

    def add(self, name: str, direction: int, animation: Animation):
        self.animations[(name, direction)] = animation
        if self.current_name is None:
            self.current_name = name
            self.current_dir = direction

    def play(self, name: str, direction: int):
        """Switch to a different animation/direction. Resets if changed."""
        if name != self.current_name or direction != self.current_dir:
            self.current_name = name
            self.current_dir = direction
            anim = self.animations.get((name, direction))
            if anim:
                anim.reset()

    def update(self, dt: float) -> pygame.Surface:
        """Update current animation and return the current frame."""
        anim = self.animations.get((self.current_name, self.current_dir))
        if anim:
            anim.update(dt)
            return anim.get_frame()
        # Fallback: return first available frame
        for a in self.animations.values():
            return a.get_frame()
        return pygame.Surface((48, 48), pygame.SRCALPHA)


# ---------------------------------------------------------------------------
# Utility: load individual frame files from a TimeFantasy character directory
# ---------------------------------------------------------------------------

def _load_and_scale(path: str, scale: int) -> pygame.Surface:
    """Load a PNG frame, convert to RGBA, and scale."""
    img = pygame.image.load(path)
    # Convert palette-mode images to RGBA for proper transparency
    if img.get_alpha() is None and img.get_colorkey() is None:
        img = img.convert_alpha()
    else:
        img = img.convert_alpha()
    if scale != 1:
        w, h = img.get_size()
        img = pygame.transform.scale(img, (w * scale, h * scale))
    return img


def load_character_frames(base_dir: str, scale: int = SCALE_FACTOR,
                          anim_speed: float = 0.15) -> AnimationSet:
    """Load all animation frames from a TimeFantasy character directory.

    Expects files like:
        down_stand.png, down_walk1.png, down_walk2.png
        left_stand.png, left_walk1.png, left_walk2.png
        right_stand.png, right_walk1.png, right_walk2.png
        up_stand.png, up_walk1.png, up_walk2.png
    Optionally: pose1.png, pose2.png, pose3.png (used for melee attack)

    Returns a fully populated AnimationSet with:
        "idle"  — single stand frame per direction
        "walk"  — 4-frame cycle: walk1, stand, walk2, stand
        "melee" — pose frames if available, else stand frame
    """
    anim_set = AnimationSet()

    for direction in (DIR_DOWN, DIR_LEFT, DIR_RIGHT, DIR_UP):
        dir_name = DIR_NAMES[direction]

        # --- Load stand and walk frames for this direction ---
        stand_path = os.path.join(base_dir, f"{dir_name}_stand.png")
        walk1_path = os.path.join(base_dir, f"{dir_name}_walk1.png")
        walk2_path = os.path.join(base_dir, f"{dir_name}_walk2.png")

        # If left frames don't exist, mirror right frames
        if direction == DIR_LEFT and not os.path.exists(stand_path):
            right_stand = os.path.join(base_dir, "right_stand.png")
            right_walk1 = os.path.join(base_dir, "right_walk1.png")
            right_walk2 = os.path.join(base_dir, "right_walk2.png")
            try:
                stand = pygame.transform.flip(_load_and_scale(right_stand, scale), True, False)
                walk1 = pygame.transform.flip(_load_and_scale(right_walk1, scale), True, False)
                walk2 = pygame.transform.flip(_load_and_scale(right_walk2, scale), True, False)
            except Exception:
                stand = _make_placeholder(scale)
                walk1 = stand
                walk2 = stand
        else:
            try:
                stand = _load_and_scale(stand_path, scale)
                walk1 = _load_and_scale(walk1_path, scale)
                walk2 = _load_and_scale(walk2_path, scale)
            except Exception:
                stand = _make_placeholder(scale)
                walk1 = stand
                walk2 = stand

        # Idle: gentle breathing cycle using walk frames at slower speed
        anim_set.add("idle", direction,
                     Animation([stand, walk1, stand, walk2], anim_speed * 2.5))

        # Walk: 4-frame cycle (walk1 → stand → walk2 → stand)
        anim_set.add("walk", direction, Animation([walk1, stand, walk2, stand], anim_speed))

        # Melee: pose frames (non-directional) or stand flash
        if direction == DIR_DOWN:
            # Only load pose once, reuse for all directions
            pose_frames = []
            for i in range(1, 4):
                pose_path = os.path.join(base_dir, f"pose{i}.png")
                if os.path.exists(pose_path):
                    try:
                        pose_frames.append(_load_and_scale(pose_path, scale))
                    except Exception:
                        pass
            if not pose_frames:
                pose_frames = [stand]
            # Store for reuse
            _pose_cache = pose_frames

        anim_set.add("melee", direction,
                      Animation(_pose_cache if direction == DIR_DOWN else
                                (pose_frames if 'pose_frames' in dir() else [stand]),
                                0.08))

    # Fix melee for all directions to use the same pose frames
    pose_anim = anim_set.animations.get(("melee", DIR_DOWN))
    if pose_anim:
        for d in (DIR_LEFT, DIR_RIGHT, DIR_UP):
            anim_set.animations[("melee", d)] = Animation(
                list(pose_anim.frames), pose_anim.speed)

    return anim_set


def _make_placeholder(scale: int, color: tuple = (100, 100, 200)) -> pygame.Surface:
    """Create a colored rectangle placeholder frame."""
    w = 17 * scale
    h = 29 * scale
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(surf, color, (2, 2, w - 4, h - 4))
    return surf
