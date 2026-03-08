import pygame
import random
import os
import time
from src.settings import (
    TILE_SIZE, SCALE_FACTOR,
    COMBAT_STAGE_TILES, TOWN_STAGE_TILES,
    GROUND_COLORS, PATH_COLORS,
    STAGE_THEMES, STAGE_MONSTERS, STAGE_BOSSES, BOSS_STAGE_SCALING,
    MONSTER_STATS, TILESETS_PATH, OBJECT_DEFS,
    get_stage_difficulty, MERCHANT_NPC_TYPES,
    get_town_stage_tiles
)
from src.monster import Monster
from src.npc import NPC


class Obstacle(pygame.sprite.Sprite):
    """A static obstacle on the object layer (tree, rock, house, etc.)."""

    def __init__(self, x: int, y: int, image: pygame.Surface,
                 collision_w: int, collision_h: int):
        super().__init__()
        self.image = image
        self.rect = self.image.get_rect(topleft=(x, y))
        # Collision rect at bottom portion of the image
        self.collision_rect = pygame.Rect(
            x, y + self.rect.height - collision_h,
            collision_w, collision_h
        )

    def draw(self, surface: pygame.Surface, camera_offset: tuple):
        pos = (self.rect.x - int(camera_offset[0]),
               self.rect.y - int(camera_offset[1]))
        surface.blit(self.image, pos)


class TreasureChest(pygame.sprite.Sprite):
    """A destructible treasure chest that drops loot when destroyed."""

    CHEST_BASE_HP = 30

    def __init__(self, x: int, y: int, difficulty: float = 1.0, locked: bool = False):
        super().__init__()
        self.world_x = float(x)
        self.world_y = float(y)
        self.hp = int(self.CHEST_BASE_HP * (1.0 + difficulty * 0.4))
        self.max_hp = self.hp
        self.is_alive = True
        self.shake_timer = 0.0
        self.locked = locked
        self.drop_table_key = "boss_treasure_chest" if locked else "treasure_chest"

        if locked:
            self._create_locked_sprite()
        else:
            self._create_normal_sprite()

        self.image = self.base_image
        self.rect = self.image.get_rect(center=(int(x), int(y)))
        size = TILE_SIZE
        self.collision_rect = pygame.Rect(
            int(x) - size // 2 + 4, int(y) - size // 2 + 10,
            size - 8, size - 14
        )

    def _create_normal_sprite(self):
        """Create standard brown chest sprite."""
        size = TILE_SIZE
        self.base_image = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.rect(self.base_image, (120, 80, 30), (4, 10, size - 8, size - 14))
        pygame.draw.rect(self.base_image, (140, 95, 35), (2, 6, size - 4, 12))
        pygame.draw.rect(self.base_image, (220, 180, 40), (2, 6, size - 4, 12), 2)
        pygame.draw.rect(self.base_image, (220, 180, 40), (4, 10, size - 8, size - 14), 2)
        pygame.draw.rect(self.base_image, (220, 180, 40), (size // 2 - 4, 14, 8, 8))
        pygame.draw.rect(self.base_image, (180, 140, 20), (size // 2 - 2, 16, 4, 4))

    def _create_locked_sprite(self):
        """Create golden boss chest sprite with red gem lock."""
        size = TILE_SIZE
        self.base_image = pygame.Surface((size, size), pygame.SRCALPHA)
        # Golden body
        pygame.draw.rect(self.base_image, (180, 150, 40), (4, 10, size - 8, size - 14))
        # Golden lid
        pygame.draw.rect(self.base_image, (220, 190, 50), (2, 6, size - 4, 12))
        # Bright gold trim
        pygame.draw.rect(self.base_image, (255, 230, 80), (2, 6, size - 4, 12), 2)
        pygame.draw.rect(self.base_image, (255, 230, 80), (4, 10, size - 8, size - 14), 2)
        # Red gem lock
        pygame.draw.rect(self.base_image, (255, 230, 80), (size // 2 - 5, 13, 10, 10))
        pygame.draw.circle(self.base_image, (200, 40, 40), (size // 2, 18), 3)

    def _create_unlocked_sprite(self):
        """Redraw golden chest with green gem to show it's unlockable."""
        size = TILE_SIZE
        self.base_image = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.rect(self.base_image, (180, 150, 40), (4, 10, size - 8, size - 14))
        pygame.draw.rect(self.base_image, (220, 190, 50), (2, 6, size - 4, 12))
        pygame.draw.rect(self.base_image, (255, 230, 80), (2, 6, size - 4, 12), 2)
        pygame.draw.rect(self.base_image, (255, 230, 80), (4, 10, size - 8, size - 14), 2)
        pygame.draw.rect(self.base_image, (255, 230, 80), (size // 2 - 5, 13, 10, 10))
        pygame.draw.circle(self.base_image, (40, 200, 40), (size // 2, 18), 3)

    def unlock(self):
        """Unlock a boss chest after the boss is defeated."""
        self.locked = False
        self._create_unlocked_sprite()
        self.image = self.base_image

    def take_damage(self, amount: int) -> bool:
        """Apply damage. Returns True if chest was destroyed."""
        if self.locked:
            return False
        self.hp = max(0, self.hp - amount)
        self.shake_timer = 0.15
        if self.hp <= 0:
            self.is_alive = False
            return True
        return False

    def update(self, dt: float):
        if self.shake_timer > 0:
            self.shake_timer -= dt

    def draw(self, surface: pygame.Surface, camera_offset: tuple):
        if not self.is_alive:
            return
        sx = self.rect.x - int(camera_offset[0])
        sy = self.rect.y - int(camera_offset[1])
        # Shake offset when hit
        if self.shake_timer > 0:
            import math as _m
            shake = int(_m.sin(self.shake_timer * 40) * 3)
            sx += shake
        surface.blit(self.image, (sx, sy))

        # Lock indicator above chest
        if self.locked:
            lock_size = max(8, TILE_SIZE // 5)
            lock_x = sx + TILE_SIZE // 2 - lock_size // 2
            lock_y = sy - lock_size - 2
            pygame.draw.rect(surface, (200, 40, 40), (lock_x, lock_y, lock_size, lock_size))
            pygame.draw.rect(surface, (255, 230, 80), (lock_x, lock_y, lock_size, lock_size), 1)

        # HP bar when damaged
        if self.hp < self.max_hp:
            bar_w = TILE_SIZE - 8
            bar_h = 3
            bx = sx + 4
            by = sy - 4
            pygame.draw.rect(surface, (60, 0, 0), (bx, by, bar_w, bar_h))
            fill = max(0, int(bar_w * self.hp / max(self.max_hp, 1)))
            pygame.draw.rect(surface, (200, 160, 40), (bx, by, fill, bar_h))


class ExitPortal(pygame.sprite.Sprite):
    """Exit point that takes the player to the next stage."""

    def __init__(self, x: int, y: int):
        super().__init__()
        size = TILE_SIZE * 2
        self.image = pygame.Surface((size, size), pygame.SRCALPHA)
        # Draw a glowing portal
        pygame.draw.ellipse(self.image, (100, 50, 200, 180), (4, 4, size - 8, size - 8))
        pygame.draw.ellipse(self.image, (150, 100, 255, 200), (12, 12, size - 24, size - 24))
        pygame.draw.ellipse(self.image, (200, 180, 255), (12, 12, size - 24, size - 24), 2)
        self.rect = self.image.get_rect(center=(x, y))
        self.world_x = x
        self.world_y = y

    def draw(self, surface: pygame.Surface, camera_offset: tuple):
        pos = (self.rect.x - int(camera_offset[0]),
               self.rect.y - int(camera_offset[1]))
        surface.blit(self.image, pos)

    def check_player(self, player_rect: pygame.Rect) -> bool:
        return self.rect.colliderect(player_rect)


# ---------------------------------------------------------------------------
# Tileset object image cache
# ---------------------------------------------------------------------------
_tileset_cache: dict = {}   # tileset filename -> Surface
_obj_img_cache: dict = {}   # obj_name -> Surface


def _get_tileset(filename: str) -> pygame.Surface | None:
    """Load and cache a tileset PNG."""
    if filename in _tileset_cache:
        return _tileset_cache[filename]
    path = os.path.join(TILESETS_PATH, filename)
    try:
        surf = pygame.image.load(path).convert_alpha()
        _tileset_cache[filename] = surf
        return surf
    except Exception:
        _tileset_cache[filename] = None
        return None


def _get_object_image(obj_name: str) -> pygame.Surface:
    """Extract an object sprite from a tileset, or return a colored fallback."""
    if obj_name in _obj_img_cache:
        return _obj_img_cache[obj_name]

    obj_def = OBJECT_DEFS.get(obj_name)
    if not obj_def:
        fallback = _make_fallback_obj(obj_name)
        _obj_img_cache[obj_name] = fallback
        return fallback

    region = obj_def.get("tileset_region")
    if region:
        ts_file, rx, ry, rw, rh = region
        tileset = _get_tileset(ts_file)
        if tileset:
            try:
                sub = tileset.subsurface(pygame.Rect(rx, ry, rw, rh))
                scaled = pygame.transform.scale(sub, (rw * SCALE_FACTOR, rh * SCALE_FACTOR))
                _obj_img_cache[obj_name] = scaled
                return scaled
            except Exception:
                pass

    # Fallback
    color = obj_def.get("color", (100, 100, 100)) if obj_def else (100, 100, 100)
    fallback = _make_fallback_obj(obj_name, color)
    _obj_img_cache[obj_name] = fallback
    return fallback


def _make_fallback_obj(obj_name: str, color: tuple = (100, 100, 100)) -> pygame.Surface:
    obj_def = OBJECT_DEFS.get(obj_name, {"collision": (1, 1)})
    cw = obj_def["collision"][0]
    ch = obj_def["collision"][1]
    w = max(cw, 1) * TILE_SIZE
    h = max(ch, 1) * TILE_SIZE
    if "Tree" in obj_name:
        h = int(h * 1.5)  # Trees are taller than their collision
    img = pygame.Surface((w, h), pygame.SRCALPHA)
    if "Tree" in obj_name:
        pygame.draw.ellipse(img, color, (4, 4, w - 8, h - 8))
    elif "Rock" in obj_name:
        pygame.draw.ellipse(img, color, (2, 2, w - 4, h - 4))
    elif "Dungeon_wall" in obj_name:
        # Stone block with mortar lines and highlight
        pygame.draw.rect(img, color, (0, 0, w, h))
        mortar = (36, 32, 34)
        pygame.draw.rect(img, mortar, (0, 0, w, 2))          # top mortar
        pygame.draw.rect(img, mortar, (0, h - 2, w, 2))      # bottom mortar
        pygame.draw.rect(img, mortar, (0, 0, 2, h))           # left mortar
        pygame.draw.rect(img, mortar, (w - 2, 0, 2, h))      # right mortar
        highlight = (78, 72, 76)
        pygame.draw.rect(img, highlight, (2, 2, w - 4, 3))   # top highlight
        pygame.draw.rect(img, highlight, (2, 2, 3, h - 4))   # left highlight
    else:
        pygame.draw.rect(img, color, (2, 2, w - 4, h - 4))
    return img


# ---------------------------------------------------------------------------
# Stage class
# ---------------------------------------------------------------------------

class Stage:
    """A game stage with ground, objects, monsters, NPCs, and an exit."""

    def __init__(self, stage_num: int, stage_type: str, theme: str):
        self.stage_num = stage_num
        self.stage_type = stage_type  # "combat" or "town"
        self.theme = theme
        self.difficulty = get_stage_difficulty(stage_num)

        if stage_type == "combat":
            self.width = COMBAT_STAGE_TILES
            self.height = COMBAT_STAGE_TILES
        else:
            town_size = get_town_stage_tiles()
            self.width = town_size
            self.height = town_size

        self.pixel_width = self.width * TILE_SIZE
        self.pixel_height = self.height * TILE_SIZE

        # Ground tile colors (pre-generated for performance)
        self.ground_surface = None

        # Game objects
        self.obstacles = []  # list of Obstacle sprites
        self.obstacle_rects = []  # list of pygame.Rects for collision
        self.monsters = pygame.sprite.Group()
        self.npcs = pygame.sprite.Group()
        self.chests = []  # list of TreasureChest objects
        self.exit_portal = None
        self.player_start = (0, 0)

        # Boss area
        self.boss_area = None  # pygame.Rect or None
        self.boss_defeated = False

    def generate(self, item_db: dict = None):
        """Procedurally generate the stage content."""
        # Both combat and town stages use time-based seed for variety each game
        seed = (self.stage_num * 12345 + hash(self.stage_type)
                + int(time.time() * 1000) % 999999)
        rng = random.Random(seed)

        self._generate_ground(rng)

        if self.stage_type == "combat":
            self._generate_combat_stage(rng)
        else:
            self._generate_town_stage(rng)

    def _generate_ground(self, rng: random.Random):
        """Generate the ground tile surface with varied path patterns."""
        self.ground_surface = pygame.Surface(
            (self.pixel_width, self.pixel_height))
        colors = GROUND_COLORS.get(self.theme, GROUND_COLORS["forest"])
        path_colors = PATH_COLORS.get(self.theme, PATH_COLORS["forest"])

        # Fill with base ground color variants
        for ty in range(self.height):
            for tx in range(self.width):
                color = rng.choice(colors)
                rect = pygame.Rect(tx * TILE_SIZE, ty * TILE_SIZE,
                                   TILE_SIZE, TILE_SIZE)
                pygame.draw.rect(self.ground_surface, color, rect)

        # Choose a path pattern
        pattern = rng.choice(["cross", "diagonal", "l_shape", "winding", "fork"])
        self._generate_path_pattern(rng, path_colors, pattern)

    def _generate_path_pattern(self, rng, path_colors, pattern: str):
        """Generate paths based on the selected pattern type."""
        w, h = self.width, self.height

        if pattern == "cross":
            # Cross with randomized center
            cx = rng.randint(w // 3, 2 * w // 3)
            cy = rng.randint(h // 3, 2 * h // 3)
            self._generate_path_between(rng, path_colors, (0, cy), (w, cy))
            self._generate_path_between(rng, path_colors, (cx, 0), (cx, h))

        elif pattern == "diagonal":
            # Two diagonal paths crossing
            self._generate_path_between(rng, path_colors,
                (rng.randint(0, 3), rng.randint(0, 3)),
                (w - rng.randint(1, 4), h - rng.randint(1, 4)))
            self._generate_path_between(rng, path_colors,
                (w - rng.randint(1, 4), rng.randint(0, 3)),
                (rng.randint(0, 3), h - rng.randint(1, 4)))

        elif pattern == "l_shape":
            # L-shaped paths
            mid_x = rng.randint(w // 3, 2 * w // 3)
            mid_y = rng.randint(h // 3, 2 * h // 3)
            self._generate_path_between(rng, path_colors, (0, mid_y), (mid_x, mid_y))
            self._generate_path_between(rng, path_colors, (mid_x, mid_y), (mid_x, h))
            # Second L in opposite direction
            mid_x2 = rng.randint(w // 4, 3 * w // 4)
            mid_y2 = rng.randint(h // 4, 3 * h // 4)
            self._generate_path_between(rng, path_colors, (mid_x2, 0), (mid_x2, mid_y2))
            self._generate_path_between(rng, path_colors, (mid_x2, mid_y2), (w, mid_y2))

        elif pattern == "winding":
            # Single winding path with aggressive wobble
            start_side = rng.choice(["left", "top"])
            if start_side == "left":
                self._generate_winding_path(rng, path_colors,
                    (0, rng.randint(h // 4, 3 * h // 4)),
                    (w, rng.randint(h // 4, 3 * h // 4)),
                    horizontal=True)
            else:
                self._generate_winding_path(rng, path_colors,
                    (rng.randint(w // 4, 3 * w // 4), 0),
                    (rng.randint(w // 4, 3 * w // 4), h),
                    horizontal=False)

        elif pattern == "fork":
            # Y-shaped: one path splits into two
            mid_x = w // 2
            mid_y = h // 2
            self._generate_path_between(rng, path_colors, (0, mid_y), (mid_x, mid_y))
            self._generate_path_between(rng, path_colors,
                (mid_x, mid_y), (w, rng.randint(2, h // 3)))
            self._generate_path_between(rng, path_colors,
                (mid_x, mid_y), (w, rng.randint(2 * h // 3, h - 2)))

    def _draw_path_tile(self, rng, path_colors, tx: int, ty: int):
        """Draw a single path tile (square) at tile position."""
        color = rng.choice(path_colors)
        px = tx * TILE_SIZE
        py = ty * TILE_SIZE
        pygame.draw.rect(self.ground_surface, color,
                         (px, py, TILE_SIZE, TILE_SIZE))

    def _generate_path_between(self, rng, path_colors, start: tuple, end: tuple):
        """Draw a winding path between two tile positions using square tiles."""
        x, y = start[0], start[1]
        ex, ey = end[0], end[1]

        steps = max(abs(ex - x), abs(ey - y), 1)
        for step in range(steps + 1):
            t = step / max(steps, 1)
            tx = int(x + (ex - x) * t)
            ty = int(y + (ey - y) * t)
            # Add wobble perpendicular to path direction
            if abs(ex - x) > abs(ey - y):
                ty += rng.choice([-1, 0, 0, 0, 1])
            else:
                tx += rng.choice([-1, 0, 0, 0, 1])
            tx = max(2, min(self.width - 3, tx))
            ty = max(2, min(self.height - 3, ty))

            # Draw a 2-tile-wide path for visibility
            for ox in range(-1, 2):
                for oy in range(-1, 2):
                    ptx = tx + ox
                    pty = ty + oy
                    if 0 <= ptx < self.width and 0 <= pty < self.height:
                        self._draw_path_tile(rng, path_colors, ptx, pty)

    def _generate_winding_path(self, rng, path_colors, start, end, horizontal):
        """Create a path with more pronounced curves/bends using square tiles."""
        x, y = start
        ex, ey = end

        if horizontal:
            while x < ex:
                for ox in range(-1, 2):
                    for oy in range(-1, 2):
                        ptx = x + ox
                        pty = y + oy
                        if 0 <= ptx < self.width and 0 <= pty < self.height:
                            self._draw_path_tile(rng, path_colors, ptx, pty)
                x += 1
                y += rng.choice([-2, -1, 0, 0, 1, 2])
                y = max(2, min(self.height - 3, y))
        else:
            while y < ey:
                for ox in range(-1, 2):
                    for oy in range(-1, 2):
                        ptx = x + ox
                        pty = y + oy
                        if 0 <= ptx < self.width and 0 <= pty < self.height:
                            self._draw_path_tile(rng, path_colors, ptx, pty)
                y += 1
                x += rng.choice([-2, -1, 0, 0, 1, 2])
                x = max(2, min(self.width - 3, x))

    def _place_obstacle(self, obj_name: str, tx: int, ty: int):
        """Place an obstacle at tile position (tx, ty)."""
        img = _get_object_image(obj_name)
        obj_def = OBJECT_DEFS.get(obj_name, {"collision": (1, 1)})
        cw = obj_def["collision"][0] * TILE_SIZE
        ch = obj_def["collision"][1] * TILE_SIZE

        px = tx * TILE_SIZE
        py = ty * TILE_SIZE - (img.get_height() - ch)  # Align bottom

        obstacle = Obstacle(px, py, img, cw, ch)
        self.obstacles.append(obstacle)
        # Decorative objects don't block movement
        if not obj_def.get("decorative", False):
            # Shrink collision rect to better match visual sprite size
            shrink = int(TILE_SIZE * 0.2)
            obstacle.collision_rect.inflate_ip(-shrink * 2, -shrink * 2)
            self.obstacle_rects.append(obstacle.collision_rect)

    def _is_area_clear(self, tx: int, ty: int, w: int, h: int) -> bool:
        """Check if a tile area is free of obstacles."""
        test_rect = pygame.Rect(tx * TILE_SIZE, ty * TILE_SIZE,
                                w * TILE_SIZE, h * TILE_SIZE)
        for r in self.obstacle_rects:
            if test_rect.colliderect(r):
                return False
        return True

    def _find_clear_spawn(self, world_x: float, world_y: float) -> tuple:
        """Return a world position guaranteed to be clear of all obstacles.

        Starts at the given tile and spirals outward (up to 8 tiles away)
        until a 2×2-tile area free of obstacles is found.  Prevents the
        player from spawning inside an object and getting stuck.
        """
        start_tx = int(world_x // TILE_SIZE)
        start_ty = int(world_y // TILE_SIZE)
        for radius in range(9):
            for dx in range(-radius, radius + 1):
                for dy in range(-radius, radius + 1):
                    # Only check the outermost ring at each radius
                    if radius > 0 and abs(dx) < radius and abs(dy) < radius:
                        continue
                    tx = start_tx + dx
                    ty = start_ty + dy
                    if tx < 1 or ty < 1 or tx >= self.width - 2 or ty >= self.height - 2:
                        continue
                    if self._is_area_clear(tx, ty, 2, 2):
                        return (float(tx * TILE_SIZE), float(ty * TILE_SIZE))
        return (world_x, world_y)  # Fallback: original position unchanged

    def _generate_combat_stage(self, rng: random.Random):
        """Generate a combat stage with monsters, obstacles, boss area, and exit."""
        w, h = self.width, self.height

        # Player start: left side (dungeon uses tile 2 to align with maze passage)
        if self.theme == "dungeon":
            self.player_start = (2 * TILE_SIZE, (h // 2) * TILE_SIZE)
        else:
            self.player_start = (3 * TILE_SIZE, (h // 2) * TILE_SIZE)

        # Exit portal: right side
        exit_x = (w - 3) * TILE_SIZE
        exit_y = (h // 2) * TILE_SIZE
        self.exit_portal = ExitPortal(exit_x, exit_y)

        # Boss area: right-center area (scaled for 50x50 map)
        boss_tx = w - 15
        boss_ty = h // 2 - 5
        boss_w, boss_h = 12, 10
        self.boss_area = pygame.Rect(boss_tx * TILE_SIZE, boss_ty * TILE_SIZE,
                                     boss_w * TILE_SIZE, boss_h * TILE_SIZE)

        if self.theme == "dungeon":
            # Dungeon: generate a recursive-backtracker maze of stone walls
            # (replaces the border + scattered-obstacle generation used by other themes)
            self._generate_dungeon_walls(rng)
        else:
            # Forest / desert: place border + scattered obstacles
            self._place_border(rng)

        if self.theme != "dungeon":
            # Place scattered obstacles (scaled down for 50x50)
            tree_types = ["Tree_medium", "Tree_small"]
            rock_types = ["Rock_large", "Rock_small"]

            num_trees = rng.randint(30, 50)
            num_rocks = rng.randint(10, 20)
            num_bushes = rng.randint(8, 15)

        if self.theme != "dungeon":
            placed_positions = set()

            for _ in range(num_trees):
                for _attempt in range(20):
                    tx = rng.randint(2, w - 4)
                    ty = rng.randint(2, h - 4)
                    if (tx, ty) in placed_positions:
                        continue
                    if abs(tx - 3) < 4 and abs(ty - h // 2) < 4:
                        continue
                    if abs(tx - (w - 3)) < 4 and abs(ty - h // 2) < 4:
                        continue
                    if self.boss_area and self.boss_area.collidepoint(
                            tx * TILE_SIZE, ty * TILE_SIZE):
                        continue
                    if self._is_area_clear(tx, ty, 2, 2):
                        self._place_obstacle(rng.choice(tree_types), tx, ty)
                        placed_positions.add((tx, ty))
                        break

            for _ in range(num_rocks):
                for _attempt in range(20):
                    tx = rng.randint(2, w - 3)
                    ty = rng.randint(2, h - 3)
                    if (tx, ty) in placed_positions:
                        continue
                    if abs(tx - 3) < 3 and abs(ty - h // 2) < 3:
                        continue
                    if self._is_area_clear(tx, ty, 1, 1):
                        self._place_obstacle(rng.choice(rock_types), tx, ty)
                        placed_positions.add((tx, ty))
                        break

            for _ in range(num_bushes):
                for _attempt in range(15):
                    tx = rng.randint(2, w - 3)
                    ty = rng.randint(2, h - 3)
                    if (tx, ty) not in placed_positions and self._is_area_clear(tx, ty, 1, 1):
                        self._place_obstacle("Bush", tx, ty)
                        placed_positions.add((tx, ty))
                        break

            # --- Additional obstacle variety ---

            # Barrel/Crate clusters (2-4 groups of 2-4 objects)
            num_clusters = rng.randint(2, 4)
            for _ in range(num_clusters):
                for _attempt in range(20):
                    base_tx = rng.randint(4, w - 6)
                    base_ty = rng.randint(4, h - 6)
                    if abs(base_tx - 3) < 4 and abs(base_ty - h // 2) < 4:
                        continue
                    if abs(base_tx - (w - 3)) < 4 and abs(base_ty - h // 2) < 4:
                        continue
                    if self.boss_area and self.boss_area.collidepoint(
                            base_tx * TILE_SIZE, base_ty * TILE_SIZE):
                        continue
                    if not self._is_area_clear(base_tx, base_ty, 1, 1):
                        continue
                    # Place a cluster of barrels and crates
                    cluster_size = rng.randint(2, 4)
                    for ci in range(cluster_size):
                        ctx = base_tx + rng.randint(0, 1)
                        cty = base_ty + rng.randint(0, 1)
                        if (ctx, cty) not in placed_positions and self._is_area_clear(ctx, cty, 1, 1):
                            self._place_obstacle(rng.choice(["Barrel", "Crate"]), ctx, cty)
                            placed_positions.add((ctx, cty))
                    break

            # Fence segments (1-3 lines of 2-4 fence tiles)
            num_fences = rng.randint(1, 3)
            for _ in range(num_fences):
                for _attempt in range(20):
                    ftx = rng.randint(4, w - 8)
                    fty = rng.randint(4, h - 8)
                    if abs(ftx - 3) < 4 and abs(fty - h // 2) < 4:
                        continue
                    if self.boss_area and self.boss_area.collidepoint(
                            ftx * TILE_SIZE, fty * TILE_SIZE):
                        continue
                    fence_len = rng.randint(2, 4)
                    horizontal = rng.random() > 0.5
                    can_place = True
                    fence_tiles = []
                    for fi in range(fence_len):
                        fx = ftx + (fi if horizontal else 0)
                        fy = fty + (0 if horizontal else fi)
                        if (fx, fy) in placed_positions or not self._is_area_clear(fx, fy, 1, 1):
                            can_place = False
                            break
                        fence_tiles.append((fx, fy))
                    if can_place and fence_tiles:
                        for fx, fy in fence_tiles:
                            self._place_obstacle("Fence", fx, fy)
                            placed_positions.add((fx, fy))
                        break

            # Wells (0-2 per stage)
            num_wells = rng.randint(0, 2)
            for _ in range(num_wells):
                for _attempt in range(20):
                    tx = rng.randint(4, w - 5)
                    ty = rng.randint(4, h - 5)
                    if (tx, ty) in placed_positions:
                        continue
                    if abs(tx - 3) < 4 and abs(ty - h // 2) < 4:
                        continue
                    if self.boss_area and self.boss_area.collidepoint(
                            tx * TILE_SIZE, ty * TILE_SIZE):
                        continue
                    if self._is_area_clear(tx, ty, 1, 1):
                        self._place_obstacle("Well", tx, ty)
                        placed_positions.add((tx, ty))
                        break

            # Stumps (2-5 per stage)
            num_stumps = rng.randint(2, 5)
            for _ in range(num_stumps):
                for _attempt in range(15):
                    tx = rng.randint(3, w - 4)
                    ty = rng.randint(3, h - 4)
                    if (tx, ty) not in placed_positions and self._is_area_clear(tx, ty, 1, 1):
                        self._place_obstacle("Stump", tx, ty)
                        placed_positions.add((tx, ty))
                        break

            # Decorative flora (10-20 flowers/tall_grass, non-blocking)
            num_flora = rng.randint(10, 20)
            flora_types = ["Flowers", "Tall_grass"]
            for _ in range(num_flora):
                for _attempt in range(10):
                    tx = rng.randint(2, w - 3)
                    ty = rng.randint(2, h - 3)
                    if (tx, ty) not in placed_positions:
                        self._place_obstacle(rng.choice(flora_types), tx, ty)
                        placed_positions.add((tx, ty))
                        break

        # Place monsters (scaled for 50x50)
        available_types = STAGE_MONSTERS.get(self.theme, ["wild_cat"])
        num_monsters = 8 + self.stage_num * 3
        behaviors = ["stand", "patrol"]

        for _ in range(num_monsters):
            for _attempt in range(30):
                tx = rng.randint(4, w - 5)
                ty = rng.randint(4, h - 5)
                mx = tx * TILE_SIZE + TILE_SIZE // 2
                my = ty * TILE_SIZE + TILE_SIZE // 2
                if self.boss_area and self.boss_area.collidepoint(mx, my):
                    continue
                if abs(tx - 3) < 5 and abs(ty - h // 2) < 5:
                    continue
                if not self._is_area_clear(tx, ty, 1, 1):
                    continue

                mtype = rng.choice(available_types)
                behavior = rng.choice(behaviors)
                patrol_pts = []
                if behavior == "patrol":
                    for _ in range(rng.randint(2, 4)):
                        px = mx + rng.randint(-3, 3) * TILE_SIZE
                        py = my + rng.randint(-3, 3) * TILE_SIZE
                        patrol_pts.append([px, py])

                monster = Monster(mx, my, mtype, behavior=behavior,
                                  patrol_points=patrol_pts,
                                  difficulty=self.difficulty)
                self.monsters.add(monster)
                break

        # Place boss
        boss_type = STAGE_BOSSES.get(self.stage_num, "commander")
        boss_scale = BOSS_STAGE_SCALING.get(self.stage_num, 1.0)
        boss_x = self.boss_area.centerx
        boss_y = self.boss_area.centery
        boss = Monster(boss_x, boss_y, boss_type, behavior="stand",
                       is_boss=True, difficulty=self.difficulty,
                       boss_scale=boss_scale)
        self.monsters.add(boss)

        # Add extra monsters in boss area — spaced away from the boss
        min_boss_dist = TILE_SIZE * 4  # Minimum distance from boss center
        for _ in range(2 + self.stage_num):
            for _attempt in range(30):
                bx = boss_x + rng.randint(-5, 5) * TILE_SIZE
                by = boss_y + rng.randint(-4, 4) * TILE_SIZE
                # Must be inside the boss area
                if not self.boss_area.collidepoint(bx, by):
                    continue
                # Must be far enough from boss to avoid collision stuck
                dist_to_boss = ((bx - boss_x) ** 2 + (by - boss_y) ** 2) ** 0.5
                if dist_to_boss < min_boss_dist:
                    continue
                mtype = rng.choice(available_types)
                m = Monster(bx, by, mtype, behavior="stand",
                            difficulty=self.difficulty)
                self.monsters.add(m)
                break

        # Place treasure chests
        num_chests = rng.randint(3, 6)
        for _ in range(num_chests):
            for _attempt in range(30):
                tx = rng.randint(4, w - 5)
                ty = rng.randint(4, h - 5)
                cx = tx * TILE_SIZE + TILE_SIZE // 2
                cy = ty * TILE_SIZE + TILE_SIZE // 2
                # Not near player start
                if abs(tx - 3) < 5 and abs(ty - h // 2) < 5:
                    continue
                # Not near exit
                if abs(tx - (w - 3)) < 4 and abs(ty - h // 2) < 4:
                    continue
                # Not in boss area
                if self.boss_area and self.boss_area.collidepoint(cx, cy):
                    continue
                # Not on existing obstacles
                if not self._is_area_clear(tx, ty, 1, 1):
                    continue
                chest = TreasureChest(cx, cy, difficulty=self.difficulty)
                self.chests.append(chest)
                self.obstacle_rects.append(chest.collision_rect)
                break

        # Place boss area treasure chests (locked until boss is defeated)
        boss_tx = (self.boss_area.x // TILE_SIZE)
        boss_ty = (self.boss_area.y // TILE_SIZE)
        boss_tw = (self.boss_area.width // TILE_SIZE)
        boss_th = (self.boss_area.height // TILE_SIZE)
        min_boss_chest_dist = TILE_SIZE * 3
        num_boss_chests = rng.randint(2, 4)
        for _ in range(num_boss_chests):
            for _attempt in range(30):
                btx = rng.randint(boss_tx + 1, boss_tx + boss_tw - 2)
                bty = rng.randint(boss_ty + 1, boss_ty + boss_th - 2)
                bcx = btx * TILE_SIZE + TILE_SIZE // 2
                bcy = bty * TILE_SIZE + TILE_SIZE // 2
                if not self.boss_area.collidepoint(bcx, bcy):
                    continue
                dist = ((bcx - boss_x) ** 2 + (bcy - boss_y) ** 2) ** 0.5
                if dist < min_boss_chest_dist:
                    continue
                if not self._is_area_clear(btx, bty, 1, 1):
                    continue
                chest = TreasureChest(bcx, bcy, difficulty=self.difficulty,
                                      locked=True)
                self.chests.append(chest)
                self.obstacle_rects.append(chest.collision_rect)
                break

        # Guarantee player spawn is not blocked by any obstacle
        self.player_start = self._find_clear_spawn(*self.player_start)

    def _generate_dungeon_walls(self, rng: random.Random):
        """Generate a dungeon maze of stone walls using the recursive-backtracker algorithm.

        Cell layout (cell size = 3 tiles: 2 passage + 1 wall separator):
        - Outer border: tile 0 and tile 49 in each axis (always solid wall)
        - Inner 48×48 tiles split into 16×16 cells (MAZE_W×MAZE_H)
        - Cell (c, r) has 2×2 passage tiles at [1+3c, 1+3c+1] × [1+3r, 1+3r+1]
        - Right separator at tile-col 1+3c+2; bottom separator at tile-row 1+3r+2

        Protected zones (no wall placed):
        - Player spawn: 4×4 tile radius around player_start
        - Exit portal: 4×4 tile radius around exit
        - Boss area rect (becomes an open chamber)

        The outer border is always solid regardless of protection zones.
        """
        w, h = self.width, self.height
        STEP = 3       # Tiles per cell: 2 passage + 1 wall column/row
        OX = 1         # Inner area offset (tile 0 = outer border)
        MAZE_W = (w - 2) // STEP   # 16 for a 50-wide stage
        MAZE_H = (h - 2) // STEP   # 16 for a 50-tall stage

        # ---- Recursive-backtracker DFS ----
        # right_wall[c][r] = True  → wall between cell (c,r) and (c+1,r) exists
        # bottom_wall[c][r] = True → wall between cell (c,r) and (c,r+1) exists
        right_wall  = [[True] * MAZE_H for _ in range(MAZE_W)]
        bottom_wall = [[True] * MAZE_H for _ in range(MAZE_W)]
        visited     = [[False] * MAZE_H for _ in range(MAZE_W)]

        start_mc = 0
        start_mr = MAZE_H // 2          # Middle row (~row 8)
        stack = [(start_mc, start_mr)]
        visited[start_mc][start_mr] = True

        while stack:
            mc, mr = stack[-1]
            dirs = []
            if mc > 0 and not visited[mc - 1][mr]:           dirs.append((-1,  0))
            if mc < MAZE_W - 1 and not visited[mc + 1][mr]:  dirs.append(( 1,  0))
            if mr > 0 and not visited[mc][mr - 1]:           dirs.append(( 0, -1))
            if mr < MAZE_H - 1 and not visited[mc][mr + 1]:  dirs.append(( 0,  1))

            if dirs:
                dc, dr = rng.choice(dirs)
                nmc, nmr = mc + dc, mr + dr
                # Carve: remove the shared wall
                if dc ==  1: right_wall[mc][mr]   = False   # right wall of (mc,mr)
                if dc == -1: right_wall[nmc][mr]  = False   # right wall of (mc-1,mr)
                if dr ==  1: bottom_wall[mc][mr]  = False   # bottom wall of (mc,mr)
                if dr == -1: bottom_wall[mc][nmr] = False   # bottom wall of (mc,mr-1)
                visited[nmc][nmr] = True
                stack.append((nmc, nmr))
            else:
                stack.pop()

        # ---- Protected-zone helpers ----
        player_tx = self.player_start[0] // TILE_SIZE
        player_ty = self.player_start[1] // TILE_SIZE
        exit_tx   = (w - 3)
        exit_ty   = h // 2
        boss_rect = self.boss_area  # pygame.Rect in pixels

        def _is_protected(tx: int, ty: int) -> bool:
            """True if this tile should be kept clear (no wall placed)."""
            if abs(tx - player_tx) < 4 and abs(ty - player_ty) < 4:
                return True
            if abs(tx - exit_tx) < 4 and abs(ty - exit_ty) < 4:
                return True
            if boss_rect:
                tile_px = pygame.Rect(tx * TILE_SIZE, ty * TILE_SIZE,
                                      TILE_SIZE, TILE_SIZE)
                if boss_rect.colliderect(tile_px):
                    return True
            return False

        placed: set = set()

        def _place_wall(tx: int, ty: int, force: bool = False):
            """Place a Dungeon_wall at tile (tx, ty) unless protected (or already placed)."""
            if not (0 <= tx < w and 0 <= ty < h):
                return
            if (tx, ty) in placed:
                return
            if force or not _is_protected(tx, ty):
                self._place_obstacle("Dungeon_wall", tx, ty)
                placed.add((tx, ty))

        # ---- Outer border (always solid) ----
        for tx in range(w):
            _place_wall(tx, 0,     force=True)
            _place_wall(tx, h - 1, force=True)
        for ty in range(1, h - 1):
            _place_wall(0,     ty, force=True)
            _place_wall(w - 1, ty, force=True)

        # ---- Internal maze walls ----
        for mc in range(MAZE_W):
            ox_cell = OX + mc * STEP       # passage start column for this cell
            ox_wall = OX + mc * STEP + 2   # wall column to the right of this cell

            for mr in range(MAZE_H):
                oy_cell = OX + mr * STEP       # passage start row for this cell
                oy_wall = OX + mr * STEP + 2   # wall row below this cell

                # Right-side vertical wall separator
                if mc == MAZE_W - 1 or right_wall[mc][mr]:
                    for dy in range(STEP - 1):   # 2 tiles tall (passage height)
                        _place_wall(ox_wall, oy_cell + dy)

                # Bottom horizontal wall separator
                if mr == MAZE_H - 1 or bottom_wall[mc][mr]:
                    for dx in range(STEP - 1):   # 2 tiles wide (passage width)
                        _place_wall(ox_cell + dx, oy_wall)

                # Corner pillar at intersection of wall grid
                _place_wall(ox_wall, oy_wall)

    def _place_border(self, rng: random.Random):
        """Place obstacles around the stage border."""
        w, h = self.width, self.height
        border_objs = ["Rock_large", "Rock_small", "Tree_small"]

        for tx in range(0, w, 2):
            self._place_obstacle(rng.choice(border_objs), tx, 0)
            self._place_obstacle(rng.choice(border_objs), tx, h - 1)
        for ty in range(0, h, 2):
            self._place_obstacle(rng.choice(border_objs), 0, ty)
            self._place_obstacle(rng.choice(border_objs), w - 1, ty)

    def _generate_town_stage(self, rng: random.Random):
        """Generate a town stage with shops and NPCs. Layout is randomized."""
        w, h = self.width, self.height

        # Randomize player start and exit positions for variety
        side = rng.choice(["bottom", "top", "left", "right"])
        if side == "bottom":
            self.player_start = ((w // 2) * TILE_SIZE, (h - 3) * TILE_SIZE)
            exit_x, exit_y = (w // 2) * TILE_SIZE, 3 * TILE_SIZE
        elif side == "top":
            self.player_start = ((w // 2) * TILE_SIZE, 3 * TILE_SIZE)
            exit_x, exit_y = (w // 2) * TILE_SIZE, (h - 3) * TILE_SIZE
        elif side == "left":
            self.player_start = (3 * TILE_SIZE, (h // 2) * TILE_SIZE)
            exit_x, exit_y = (w - 3) * TILE_SIZE, (h // 2) * TILE_SIZE
        else:
            self.player_start = ((w - 3) * TILE_SIZE, (h // 2) * TILE_SIZE)
            exit_x, exit_y = 3 * TILE_SIZE, (h // 2) * TILE_SIZE

        self.exit_portal = ExitPortal(exit_x, exit_y)

        # Scale obstacle/NPC counts with town area
        size_factor = (w * h) / (30 * 30)

        # Biome-appropriate obstacle palettes so the town visually matches
        # the combat stage that preceded it.
        if self.theme == "desert":
            scatter_objs = ["Barrel", "Crate", "Rock_large", "Rock_small"]
            deco_objs = ["Flowers", "Rock_small"]
        elif self.theme == "dungeon":
            scatter_objs = ["Barrel", "Crate", "Stump"]
            deco_objs = ["Flowers"]
        else:  # forest (default)
            scatter_objs = ["Barrel", "Crate", "Stump", "Bush"]
            deco_objs = ["Flowers", "Tall_grass"]

        # Scatter obstacles (barrels, crates, theme-specific objects)
        num_barrels = rng.randint(int(4 * size_factor), int(10 * size_factor))
        for _ in range(num_barrels):
            tx = rng.randint(3, w - 4)
            ty = rng.randint(3, h - 4)
            if self._is_area_clear(tx, ty, 1, 1):
                self._place_obstacle(rng.choice(scatter_objs), tx, ty)

        # Some fences
        num_fences = rng.randint(0, int(3 * size_factor))
        for _ in range(num_fences):
            ftx = rng.randint(4, w - 8)
            fty = rng.randint(4, h - 8)
            fence_len = rng.randint(2, 4)
            horiz = rng.random() > 0.5
            for fi in range(fence_len):
                fx = ftx + (fi if horiz else 0)
                fy = fty + (0 if horiz else fi)
                if self._is_area_clear(fx, fy, 1, 1):
                    self._place_obstacle("Fence", fx, fy)

        # Wells (scale with area; skip in dungeon theme)
        if self.theme != "dungeon":
            num_wells = max(0, rng.randint(0, int(2 * size_factor)))
            for _ in range(num_wells):
                tx = rng.randint(5, w - 6)
                ty = rng.randint(5, h - 6)
                if self._is_area_clear(tx, ty, 1, 1):
                    self._place_obstacle("Well", tx, ty)

        # Decorative flora (biome-specific)
        for _ in range(rng.randint(int(5 * size_factor), int(12 * size_factor))):
            tx = rng.randint(2, w - 3)
            ty = rng.randint(2, h - 3)
            self._place_obstacle(rng.choice(deco_objs), tx, ty)

        # Place border
        self._place_border(rng)

        # Place merchant NPC (different type per town)
        shop_id = f"town_{self.stage_num}"
        merchant_type = rng.choice(MERCHANT_NPC_TYPES)
        merchant_x = rng.randint(w // 3, 2 * w // 3) * TILE_SIZE
        merchant_y = rng.randint(h // 3, 2 * h // 3) * TILE_SIZE
        merchant = NPC(merchant_x, merchant_y, npc_type=merchant_type,
                       behavior="stand", is_merchant=True, shop_id=shop_id)
        self.npcs.add(merchant)

        # Place flavor NPCs (scales with area)
        # 25-50% of NPCs should walk around (patrol), the rest stand still
        npc_types = ["npc2_1", "npc3_1", "npc4_1", "npc1_2"]
        num_npcs = rng.randint(int(3 * size_factor), int(5 * size_factor))
        for i in range(num_npcs):
            # Find a clear position for the NPC (not inside obstacles)
            nx, ny = None, None
            for _attempt in range(20):
                cx = rng.randint(4, w - 5) * TILE_SIZE
                cy = rng.randint(4, h - 5) * TILE_SIZE
                test_rect = pygame.Rect(cx - TILE_SIZE // 2, cy - TILE_SIZE // 2,
                                        TILE_SIZE, TILE_SIZE)
                if not any(test_rect.colliderect(r) for r in self.obstacle_rects):
                    nx, ny = cx, cy
                    break
            if nx is None:
                continue  # Couldn't find clear spot, skip this NPC
            ntype = rng.choice(npc_types)
            patrol = []
            # 40% chance of patrol (within user's 25-50% range)
            if rng.random() < 0.4:
                for _ in range(rng.randint(2, 4)):
                    # Ensure patrol points are NOT at the NPC's own position
                    for _try in range(10):
                        ox = rng.choice([-4, -3, -2, -1, 1, 2, 3, 4])
                        oy = rng.choice([-4, -3, -2, -1, 1, 2, 3, 4])
                        px = nx + ox * TILE_SIZE
                        py = ny + oy * TILE_SIZE
                        # Keep within map bounds
                        if 3 * TILE_SIZE <= px <= (w - 4) * TILE_SIZE \
                                and 3 * TILE_SIZE <= py <= (h - 4) * TILE_SIZE:
                            patrol.append([px, py])
                            break
            npc = NPC(nx, ny, npc_type=ntype,
                      behavior="patrol" if patrol else "stand",
                      patrol_points=patrol)
            self.npcs.add(npc)

        # Guarantee player spawn is not blocked by any obstacle
        self.player_start = self._find_clear_spawn(*self.player_start)

    def unlock_boss_chests(self):
        """Unlock all locked chests in the boss area after boss defeat."""
        for chest in self.chests:
            if chest.locked:
                chest.unlock()

    def is_in_boss_area(self, rect: pygame.Rect) -> bool:
        if self.boss_area is None:
            return False
        return self.boss_area.colliderect(rect)

    def get_all_entities(self) -> list:
        """Get all monsters and NPCs as a flat list for collision checking."""
        entities = list(self.monsters)
        entities.extend(list(self.npcs))
        return entities

    def check_boss_defeated(self) -> bool:
        """Check if all bosses in the stage are dead."""
        if self.boss_defeated:
            return True
        for m in self.monsters:
            if m.is_boss and m.is_alive:
                return False
        self.boss_defeated = True
        return True

    def draw_ground(self, surface: pygame.Surface, camera_offset: tuple):
        """Draw the ground surface (only visible portion)."""
        if self.ground_surface:
            surface.blit(self.ground_surface,
                         (-int(camera_offset[0]), -int(camera_offset[1])))

    def draw_objects(self, surface: pygame.Surface, camera_offset: tuple):
        """Draw all obstacle objects."""
        import src.settings as settings
        cam_rect = pygame.Rect(int(camera_offset[0]) - TILE_SIZE,
                               int(camera_offset[1]) - TILE_SIZE,
                               settings.SCREEN_WIDTH + TILE_SIZE * 2,
                               settings.SCREEN_HEIGHT + TILE_SIZE * 2)
        for obs in self.obstacles:
            if cam_rect.colliderect(obs.rect):
                obs.draw(surface, camera_offset)

    def draw_exit(self, surface: pygame.Surface, camera_offset: tuple):
        if self.exit_portal:
            self.exit_portal.draw(surface, camera_offset)


def generate_stage(stage_num: int, stage_type: str, item_db: dict = None) -> Stage:
    """Create and populate a stage."""
    if stage_type == "combat":
        theme = STAGE_THEMES.get(stage_num, "forest")
    else:
        # Town biome matches the preceding combat stage so the environment
        # feels continuous (forest towns after forest stages, etc.)
        theme = STAGE_THEMES.get(stage_num, "forest")

    stage = Stage(stage_num, stage_type, theme)
    stage.generate(item_db)
    return stage
