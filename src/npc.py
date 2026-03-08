import pygame
import os
import math
import random
import src.settings as settings
from src.settings import (SCALE_FACTOR, TILE_SIZE, ANIM_SPEED, NPC_SPEED,
                          DIR_DOWN, DIR_LEFT, DIR_RIGHT, DIR_UP,
                          CHARS_FRAMES_PATH, NPC_SAYINGS)
from src.animation import AnimationSet, Animation, load_character_frames
from src.collision import resolve_movement, get_obstacle_rects_near


class NPC(pygame.sprite.Sprite):
    def __init__(self, x: float, y: float, npc_type: str = "npc1_1",
                 behavior: str = "stand", is_merchant: bool = False,
                 shop_id: str = None, patrol_points: list = None):
        super().__init__()
        self.world_x = float(x)
        self.world_y = float(y)
        self.npc_type = npc_type
        self.behavior = behavior
        self.is_merchant = is_merchant
        self.shop_id = shop_id
        self.patrol_points = patrol_points or []
        self.patrol_index = 0
        self.patrol_wait = 0.0

        self.facing = DIR_DOWN
        self.is_moving = False
        self.speed = NPC_SPEED

        # Speech bubble for non-merchant NPCs
        self.speech_text = ""
        self.speech_timer = 0.0
        self.speech_cooldown = 0.0
        self._speech_font = None  # Lazy-initialized
        self._player_was_nearby = False  # Track approach for re-greeting
        self._last_saying_index = -1  # Avoid repeating the same saying twice in a row

        # Animation — load from individual frame files
        frame_dir = os.path.join(CHARS_FRAMES_PATH, "npc", npc_type)
        if os.path.isdir(frame_dir):
            self.anim_set = load_character_frames(frame_dir, SCALE_FACTOR, ANIM_SPEED)
        else:
            self.anim_set = self._make_fallback_anim_set()

        self.image = self.anim_set.update(0)
        self.rect = self.image.get_rect(center=(int(self.world_x), int(self.world_y)))

        # Collision rect
        cw = self.rect.width * 0.7
        ch = self.rect.height * 0.4
        self.collision_rect = pygame.Rect(0, 0, int(cw), int(ch))
        self._update_collision_rect()

    def _make_fallback_anim_set(self) -> AnimationSet:
        anim_set = AnimationSet()
        size_w = 17 * SCALE_FACTOR
        size_h = 29 * SCALE_FACTOR
        for anim_name in ("idle", "walk"):
            for direction in range(4):
                placeholder = pygame.Surface((size_w, size_h), pygame.SRCALPHA)
                color = (255, 200, 50) if self.is_merchant else (50, 200, 50)
                pygame.draw.rect(placeholder, color, (2, 2, size_w - 4, size_h - 4))
                anim_set.add(anim_name, direction, Animation([placeholder], ANIM_SPEED))
        return anim_set

    def _update_collision_rect(self):
        self.collision_rect.midbottom = (int(self.world_x),
                                          int(self.world_y) + self.collision_rect.height // 2)

    def update(self, dt: float, obstacles: list = None, entities: list = None,
               player_pos: tuple = None):
        self.is_moving = False

        if self.behavior == "patrol" and self.patrol_points:
            self._do_patrol(dt, obstacles or [], entities or [])

        anim = "walk" if self.is_moving else "idle"
        self.anim_set.play(anim, self.facing)
        self.image = self.anim_set.update(dt)
        self.rect = self.image.get_rect(center=(int(self.world_x), int(self.world_y)))
        self._update_collision_rect()

        # Speech bubble logic for non-merchant NPCs
        if not self.is_merchant:
            if self.speech_timer > 0:
                self.speech_timer -= dt
                if self.speech_timer <= 0:
                    self.speech_text = ""
            if self.speech_cooldown > 0:
                self.speech_cooldown -= dt

            # Check if player is nearby
            player_nearby = False
            if player_pos:
                px, py = player_pos
                dist = math.sqrt((self.world_x - px) ** 2 + (self.world_y - py) ** 2)
                player_nearby = dist < TILE_SIZE * 3

            # Trigger speech on new approach (always, ignoring cooldown)
            # OR when cooldown expires while player stays nearby
            if player_nearby:
                if not self._player_was_nearby:
                    # Player just arrived — speak immediately
                    self._say_something()
                elif self.speech_cooldown <= 0 and self.speech_timer <= 0:
                    # Still nearby, cooldown expired — speak again
                    self._say_something()
            self._player_was_nearby = player_nearby

    def _do_patrol(self, dt, obstacles, entities):
        if self.patrol_wait > 0:
            self.patrol_wait -= dt
            return

        target = self.patrol_points[self.patrol_index]
        tx, ty = float(target[0]), float(target[1])
        ddx = tx - self.world_x
        ddy = ty - self.world_y
        dist = math.sqrt(ddx * ddx + ddy * ddy)

        if dist < 5:
            self.patrol_index = (self.patrol_index + 1) % len(self.patrol_points)
            self.patrol_wait = random.uniform(1.0, 3.0)
            return

        move_dist = self.speed * dt
        if dist > 0:
            nx = ddx / dist * move_dist
            ny = ddy / dist * move_dist

            if abs(nx) > abs(ny):
                self.facing = DIR_RIGHT if nx > 0 else DIR_LEFT
            elif ny != 0:
                self.facing = DIR_DOWN if ny > 0 else DIR_UP

            new_x = self.world_x + nx
            new_y = self.world_y + ny

            old_rect = self.collision_rect.copy()
            new_rect = old_rect.copy()
            new_rect.midbottom = (int(new_x), int(new_y) + self.collision_rect.height // 2)

            nearby = get_obstacle_rects_near(obstacles, old_rect, 80)
            resolved = resolve_movement(old_rect, new_rect, nearby)

            if resolved != old_rect:
                self.is_moving = True
                self.world_x = resolved.midbottom[0]
                self.world_y = resolved.midbottom[1] - self.collision_rect.height // 2
                self._update_collision_rect()

    def _say_something(self):
        """Pick a random saying that differs from the last one."""
        if len(NPC_SAYINGS) <= 1:
            idx = 0
        else:
            idx = self._last_saying_index
            while idx == self._last_saying_index:
                idx = random.randint(0, len(NPC_SAYINGS) - 1)
        self._last_saying_index = idx
        self.speech_text = NPC_SAYINGS[idx]
        self.speech_timer = 3.0
        self.speech_cooldown = random.uniform(6.0, 12.0)

    def is_near(self, player_rect: pygame.Rect, interact_range: int = 60) -> bool:
        """Check if player is close enough to interact."""
        center = pygame.math.Vector2(self.world_x, self.world_y)
        player_center = pygame.math.Vector2(player_rect.centerx, player_rect.centery)
        return center.distance_to(player_center) < interact_range

    def draw(self, surface: pygame.Surface, camera_offset: tuple):
        pos = (self.rect.x - int(camera_offset[0]),
               self.rect.y - int(camera_offset[1]))
        surface.blit(self.image, pos)

        # Draw merchant indicator
        if self.is_merchant:
            indicator_x = pos[0] + self.rect.width // 2 - 5
            indicator_y = pos[1] - 14
            pygame.draw.rect(surface, (255, 215, 0), (indicator_x, indicator_y, 10, 10))
            pygame.draw.rect(surface, (200, 170, 0), (indicator_x, indicator_y, 10, 10), 1)

        # Draw speech bubble
        if self.speech_text and self.speech_timer > 0:
            if self._speech_font is None:
                self._speech_font = pygame.font.Font(None, settings.scaled_font_size(18))
            text_surf = self._speech_font.render(self.speech_text, True, (30, 30, 30))
            tw, th = text_surf.get_size()
            bw = tw + 10
            bh = th + 8
            bx = pos[0] + self.rect.width // 2 - bw // 2
            by = pos[1] - bh - 16
            # Bubble background
            bubble = pygame.Surface((bw, bh), pygame.SRCALPHA)
            pygame.draw.rect(bubble, (255, 255, 255, 220), (0, 0, bw, bh),
                             border_radius=4)
            pygame.draw.rect(bubble, (80, 80, 80, 200), (0, 0, bw, bh), 1,
                             border_radius=4)
            surface.blit(bubble, (bx, by))
            surface.blit(text_surf, (bx + 5, by + 4))
            # Small triangle pointer
            cx = pos[0] + self.rect.width // 2
            pygame.draw.polygon(surface, (255, 255, 255, 220),
                                [(cx - 4, by + bh), (cx + 4, by + bh),
                                 (cx, by + bh + 5)])
