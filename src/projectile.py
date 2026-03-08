import pygame
import math
from src.settings import TILE_SIZE


class Projectile(pygame.sprite.Sprite):
    """A projectile (arrow, bullet) that travels in a direction and damages monsters."""

    def __init__(self, x: float, y: float, direction: tuple, speed: float,
                 damage: int, max_range: float, style: str = "arrow",
                 homing: bool = False, target_monster=None,
                 explodes: bool = False, explosion_radius: float = 0):
        super().__init__()
        self.world_x = float(x)
        self.world_y = float(y)
        self.vx = direction[0] * speed
        self.vy = direction[1] * speed
        self._speed = speed  # Stored for homing speed normalisation
        self.damage = damage
        self.max_range = max_range
        self.distance_traveled = 0.0
        self.style = style
        self.homing = homing
        self.target_monster = target_monster  # Specific monster to home toward (magic missile)
        self.explodes = explodes              # True if projectile explodes on contact
        self.explosion_radius = explosion_radius
        self._exploded = False               # Set True when explosion is triggered
        self.is_alive = True

        # Calculate angle for drawing
        self.angle = math.degrees(math.atan2(-direction[1], direction[0]))

        # Create projectile sprite
        self.image = self._create_sprite()
        self.rect = self.image.get_rect(center=(int(x), int(y)))

        # Collision rect — enlarged for more forgiving hit detection
        self.collision_rect = pygame.Rect(0, 0, 16, 16)
        self.collision_rect.center = (int(x), int(y))

    def _create_sprite(self) -> pygame.Surface:
        """Create a procedural projectile sprite based on style."""
        if self.style == "magic":
            # Purple/blue glowing orb
            size = 14
            surf = pygame.Surface((size, size), pygame.SRCALPHA)
            # Outer glow
            pygame.draw.circle(surf, (120, 60, 200, 100), (size // 2, size // 2), 6)
            # Core
            pygame.draw.circle(surf, (160, 100, 255), (size // 2, size // 2), 4)
            # Bright center
            pygame.draw.circle(surf, (220, 200, 255), (size // 2, size // 2), 2)
            return surf
        elif self.style == "bullet":
            # Small bright circle
            size = 10
            surf = pygame.Surface((size, size), pygame.SRCALPHA)
            pygame.draw.circle(surf, (255, 230, 100), (size // 2, size // 2), 4)
            pygame.draw.circle(surf, (255, 255, 200), (size // 2, size // 2), 2)
            return surf
        else:
            # Arrow: elongated triangle pointing right, then rotated
            w, h = 16, 6
            surf = pygame.Surface((w, h), pygame.SRCALPHA)
            # Shaft
            pygame.draw.line(surf, (140, 100, 60), (0, h // 2), (w - 4, h // 2), 2)
            # Arrowhead
            pygame.draw.polygon(surf, (200, 200, 220), [
                (w, h // 2), (w - 6, 0), (w - 6, h)])
            # Fletching
            pygame.draw.line(surf, (200, 50, 50), (1, 0), (3, h // 2), 1)
            pygame.draw.line(surf, (200, 50, 50), (1, h), (3, h // 2), 1)
            # Rotate to match direction
            return pygame.transform.rotate(surf, self.angle)

    def update(self, dt: float, obstacles: list, monsters: list,
               chests: list = None) -> tuple:
        """Move projectile and check collisions.
        Returns (monster_hits, chest_hits) where:
          monster_hits = list of (monster, killed) tuples
          chest_hits = list of (chest, destroyed) tuples"""
        if not self.is_alive:
            return [], []

        # Homing: steer toward a specific target or nearest living monster
        if self.homing and monsters:
            # Use target_monster if set and still alive, else find nearest
            nearest = None
            if self.target_monster is not None and self.target_monster.is_alive:
                nearest = self.target_monster
            else:
                nearest_dist = float('inf')
                for m in monsters:
                    if not m.is_alive:
                        continue
                    mx = getattr(m, 'world_x', m.rect.centerx)
                    my = getattr(m, 'world_y', m.rect.centery)
                    d = ((mx - self.world_x) ** 2 + (my - self.world_y) ** 2) ** 0.5
                    if d < nearest_dist:
                        nearest_dist = d
                        nearest = m
            if nearest:
                mx = getattr(nearest, 'world_x', nearest.rect.centerx)
                my = getattr(nearest, 'world_y', nearest.rect.centery)
                dx = mx - self.world_x
                dy = my - self.world_y
                dist = max((dx ** 2 + dy ** 2) ** 0.5, 0.001)
                target_vx = (dx / dist) * self._speed
                target_vy = (dy / dist) * self._speed
                # Blend current velocity toward target (turn rate 6 rad/s)
                blend = min(6.0 * dt, 1.0)
                self.vx += (target_vx - self.vx) * blend
                self.vy += (target_vy - self.vy) * blend
                # Re-normalise to constant speed
                cur_speed = (self.vx ** 2 + self.vy ** 2) ** 0.5
                if cur_speed > 0:
                    self.vx = (self.vx / cur_speed) * self._speed
                    self.vy = (self.vy / cur_speed) * self._speed
                # Update draw angle to match new direction
                self.angle = math.degrees(math.atan2(-self.vy, self.vx))
                self.image = self._create_sprite()

        # Move
        move_x = self.vx * dt
        move_y = self.vy * dt
        self.world_x += move_x
        self.world_y += move_y
        self.distance_traveled += math.sqrt(move_x * move_x + move_y * move_y)

        # Update rects
        self.rect.center = (int(self.world_x), int(self.world_y))
        self.collision_rect.center = (int(self.world_x), int(self.world_y))

        # Check max range
        if self.distance_traveled >= self.max_range:
            self.is_alive = False
            return [], []

        # Build set of chest collision rects so we can skip them in obstacle check
        chest_rects = set()
        if chests:
            for chest in chests:
                if chest.is_alive:
                    chest_rects.add(id(chest.collision_rect))

        # Check chest collision BEFORE obstacles (chests are also in obstacle_rects)
        if chests:
            for chest in chests:
                if not chest.is_alive:
                    continue
                if getattr(chest, 'locked', False):
                    continue
                if self.collision_rect.colliderect(chest.collision_rect):
                    destroyed = chest.take_damage(self.damage)
                    self.is_alive = False
                    return [], [(chest, destroyed)]

        # Check obstacle collision (skip rects belonging to living chests)
        for obs in obstacles:
            if id(obs) in chest_rects:
                continue
            if self.collision_rect.colliderect(obs):
                if self.explodes and not self._exploded:
                    self._exploded = True
                self.is_alive = False
                return [], []

        # Check monster collision
        hits = []
        for monster in monsters:
            if not monster.is_alive:
                continue
            monster_rect = getattr(monster, 'collision_rect', monster.rect)
            if self.collision_rect.colliderect(monster_rect):
                if self.explodes and not self._exploded:
                    # Fireball: trigger explosion without dealing direct hit damage
                    # (explosion damage handled in game.py _trigger_fireball_explosion)
                    self._exploded = True
                    self.is_alive = False
                    return [], []
                killed = monster.take_damage(self.damage)
                hits.append((monster, killed))
                self.is_alive = False
                return hits, []

        return [], []

    def draw(self, surface: pygame.Surface, camera_offset: tuple):
        if not self.is_alive:
            return
        cam_x, cam_y = int(camera_offset[0]), int(camera_offset[1])
        draw_x = self.rect.x - cam_x
        draw_y = self.rect.y - cam_y
        surface.blit(self.image, (draw_x, draw_y))

        # Trail effect
        trail_len = 3
        for i in range(1, trail_len + 1):
            alpha = max(0, 150 - i * 50)
            tx = int(self.world_x - self.vx * 0.02 * i) - cam_x
            ty = int(self.world_y - self.vy * 0.02 * i) - cam_y
            trail_surf = pygame.Surface((6, 6), pygame.SRCALPHA)
            if self.style == "magic":
                color = (160, 100, 255, alpha)
            elif self.style == "bullet":
                color = (255, 230, 100, alpha)
            else:
                color = (200, 200, 220, alpha)
            pygame.draw.circle(trail_surf, color, (3, 3), 3 - i)
            surface.blit(trail_surf, (tx - 3, ty - 3))
