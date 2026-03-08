import pygame
import os
import math
import random
from src.settings import (SCALE_FACTOR, TILE_SIZE, ANIM_SPEED,
                          DIR_DOWN, DIR_LEFT, DIR_RIGHT, DIR_UP,
                          MONSTER_STATS, MONSTER_SPRITES, CHARS_FRAMES_PATH,
                          BOSS_HP_MULT, BOSS_DAMAGE_MULT, BOSS_XP_MULT,
                          BOSS_CHASE_DURATION, BOSS_CHASE_SPEED,
                          MONSTER_ATTACK_DURATION, POLYMORPH_PROGRESSION,
                          PROXIMITY_AGGRO_RANGE, CHAIN_AGGRO_RANGE)
from src.animation import AnimationSet, Animation, load_character_frames
from src.collision import resolve_movement, get_obstacle_rects_near


class Monster(pygame.sprite.Sprite):
    def __init__(self, x: float, y: float, monster_type: str,
                 behavior: str = "stand", is_boss: bool = False,
                 patrol_points: list = None, difficulty: float = 1.0,
                 boss_scale: float = 1.0):
        super().__init__()
        self.world_x = float(x)
        self.world_y = float(y)
        self.monster_type = monster_type
        self.behavior = behavior  # "stand", "patrol", "chase" (boss only)
        self.is_boss = is_boss
        self.difficulty = difficulty

        # Stats from settings, scaled by difficulty
        stats = MONSTER_STATS.get(monster_type, MONSTER_STATS["wild_cat"])
        hp = int(stats["hp"] * difficulty)
        dmg = int(stats["damage"] * difficulty)
        if is_boss:
            hp = int(hp * BOSS_HP_MULT * boss_scale)
            dmg = int(dmg * BOSS_DAMAGE_MULT * boss_scale)

        self.max_hp = hp
        self.hp = hp
        self.damage = dmg
        self.speed = stats["speed"]
        self.xp_value = int(stats["xp"] * difficulty * (BOSS_XP_MULT if is_boss else 1.0))

        # Patrol
        self.patrol_points = patrol_points or []
        self.patrol_index = 0
        self.patrol_wait = 0.0

        # Chase (boss)
        self.chase_timer = 0.0
        self.is_chasing = False

        # Enrage: any non-boss monster that survives a hit chases the player permanently
        self.is_enraged = False
        self._just_enraged = False   # True for one frame when is_enraged first becomes True

        # Attack cooldown and proximity attack
        self.attack_interval = stats.get("attack_interval", 1.5)
        self.attack_range = stats.get("attack_range", 60)
        if is_boss:
            self.attack_range = int(self.attack_range * 1.5)
        self.attack_cooldown = random.uniform(0.5, self.attack_interval)  # Stagger initial attacks
        self.contact_damage_cooldown = 0.0
        self.is_attacking = False
        self.attack_anim_timer = 0.0
        self.attack_hit_pending = False  # Flag for combat system to process damage

        # State
        self.is_alive = True
        self.facing = DIR_DOWN
        self.is_moving = False
        self.death_timer = 0.0

        # Polymorph (type swap to weaker monster)
        self.is_polymorphed = False
        self.polymorph_timer = 0.0
        self._original_type = None
        self._original_hp = None
        self._original_damage = None
        self._original_speed = None

        # Trap (frozen in place, can still attack)
        self.is_trapped = False
        self.trap_timer = 0.0

        # Prison (frozen and cannot attack)
        self.is_imprisoned = False
        self.prison_timer = 0.0

        # Cover of darkness (stops chasing/enraging)
        self.is_darkened = False
        self.darkened_timer = 0.0

        # Pathfinding — used when monster gets stuck behind obstacles
        self.stuck_timer = 0.0          # seconds the monster has been unable to move
        self.stuck_path: list = []      # list of (world_x, world_y) waypoints
        self.stuck_path_idx: int = 0
        self._path_recompute_timer = 0.0  # cooldown before recomputing A* path

        # Animation — load from individual frame files
        self.anim_set = self._load_animations()
        self.image = self.anim_set.update(0)
        self.rect = self.image.get_rect(center=(int(self.world_x), int(self.world_y)))

        # Collision rect (enlarged for more forgiving hit detection)
        cw = self.rect.width * 0.85
        ch = self.rect.height * 0.70
        self.collision_rect = pygame.Rect(0, 0, int(cw), int(ch))
        self._update_collision_rect()

    def _load_animations(self) -> AnimationSet:
        """Load animations from TimeFantasy individual frame files."""
        sprite_info = MONSTER_SPRITES.get(self.monster_type)
        if not sprite_info:
            return self._make_fallback_anim_set()

        category = sprite_info["category"]
        sprite_dir = sprite_info["sprite_dir"]
        frame_dir = os.path.join(CHARS_FRAMES_PATH, category, sprite_dir)

        if os.path.isdir(frame_dir):
            # Boss monsters get a slightly larger scale
            scale = SCALE_FACTOR + 1 if self.is_boss else SCALE_FACTOR
            return load_character_frames(frame_dir, scale, ANIM_SPEED)

        return self._make_fallback_anim_set()

    def _make_fallback_anim_set(self) -> AnimationSet:
        """Create a colored placeholder animation set."""
        anim_set = AnimationSet()
        color = (200, 50, 50) if self.is_boss else (150, 50, 150)
        size = TILE_SIZE
        for anim_name in ("idle", "walk", "melee"):
            for direction in range(4):
                placeholder = pygame.Surface((size, size), pygame.SRCALPHA)
                pygame.draw.ellipse(placeholder, color, (2, 2, size - 4, size - 4))
                anim_set.add(anim_name, direction, Animation([placeholder], ANIM_SPEED))
        return anim_set

    def _update_collision_rect(self):
        self.collision_rect.midbottom = (int(self.world_x),
                                          int(self.world_y) + self.collision_rect.height // 2)

    def update(self, dt: float, player_pos: tuple = None, obstacles: list = None,
               entities: list = None):
        if not self.is_alive:
            self.death_timer += dt
            return

        if self.attack_cooldown > 0:
            self.attack_cooldown -= dt
        if self.contact_damage_cooldown > 0:
            self.contact_damage_cooldown -= dt

        # Tick attack animation
        if self.is_attacking:
            self.attack_anim_timer -= dt
            if self.attack_anim_timer <= 0:
                self.is_attacking = False

        # --- Polymorph timer ---
        if self.is_polymorphed:
            self.polymorph_timer -= dt
            if self.polymorph_timer <= 0:
                self._revert_polymorph()

        # --- Cover of darkness: suppress all chasing ---
        if self.is_darkened:
            self.darkened_timer -= dt
            if self.darkened_timer <= 0:
                self.is_darkened = False
            else:
                self.is_enraged = False
                self.is_chasing = False

        # --- Imprisoned / Trapped: freeze movement and (for imprisoned) attacks ---
        if self.is_imprisoned:
            self.prison_timer -= dt
            if self.prison_timer <= 0:
                self.is_imprisoned = False
                self.is_enraged = True  # immediately chase on release
            # Update idle animation only, skip movement and attacks
            self.anim_set.play("idle", self.facing)
            self.image = self.anim_set.update(dt)
            self.rect = self.image.get_rect(center=(int(self.world_x), int(self.world_y)))
            self._update_collision_rect()
            return

        if self.is_trapped:
            self.trap_timer -= dt
            if self.trap_timer <= 0:
                self.is_trapped = False
                self.is_enraged = True  # immediately chase on release
            # Can still attack but cannot move
            if player_pos and not self.is_attacking and self.attack_cooldown <= 0:
                dx = player_pos[0] - self.world_x
                dy = player_pos[1] - self.world_y
                dist = math.sqrt(dx * dx + dy * dy)
                if dist < self.attack_range:
                    self._start_attack(dx, dy)
            # Update animation only
            if self.is_attacking:
                self.anim_set.play("melee", self.facing)
            else:
                self.anim_set.play("idle", self.facing)
            self.image = self.anim_set.update(dt)
            self.rect = self.image.get_rect(center=(int(self.world_x), int(self.world_y)))
            self._update_collision_rect()
            return

        self.is_moving = False

        # --- Proximity aggro: player walking too close triggers idle monster ---
        if (player_pos and not self.is_boss and not self.is_enraged
                and not self.is_darkened):
            pdx = player_pos[0] - self.world_x
            pdy = player_pos[1] - self.world_y
            if pdx * pdx + pdy * pdy < PROXIMITY_AGGRO_RANGE * PROXIMITY_AGGRO_RANGE:
                self.is_enraged = True
                self._just_enraged = True
                self._path_recompute_timer = 0.0  # immediate path on first enrage

        if self.is_enraged and not self.is_boss and player_pos:
            self._do_enraged_chase(dt, player_pos, obstacles or [], entities or [])
        elif self.behavior == "patrol" and self.patrol_points:
            self._do_patrol(dt, obstacles or [], entities or [])
        elif self.is_boss and player_pos:
            self._do_boss_ai(dt, player_pos, obstacles or [], entities or [])
        # "stand" behavior: just idle

        # --- Proximity attack: ALL monsters attack player when nearby ---
        if player_pos and not self.is_attacking and self.attack_cooldown <= 0:
            dx = player_pos[0] - self.world_x
            dy = player_pos[1] - self.world_y
            dist = math.sqrt(dx * dx + dy * dy)
            if dist < self.attack_range:
                self._start_attack(dx, dy)

        # Update animation
        if self.is_attacking:
            self.anim_set.play("melee", self.facing)
        elif self.is_moving:
            self.anim_set.play("walk", self.facing)
        else:
            self.anim_set.play("idle", self.facing)

        self.image = self.anim_set.update(dt)
        self.rect = self.image.get_rect(center=(int(self.world_x), int(self.world_y)))
        self._update_collision_rect()

    def _start_attack(self, dx: float, dy: float):
        """Begin an attack toward the player direction."""
        # Face toward the player
        if abs(dx) > abs(dy):
            self.facing = DIR_RIGHT if dx > 0 else DIR_LEFT
        else:
            self.facing = DIR_DOWN if dy > 0 else DIR_UP

        self.is_attacking = True
        self.attack_anim_timer = MONSTER_ATTACK_DURATION
        self.attack_cooldown = self.attack_interval
        self.attack_hit_pending = True  # Combat system will pick this up

    def _do_patrol(self, dt, obstacles, entities):
        if not self.patrol_points:
            return

        if self.patrol_wait > 0:
            self.patrol_wait -= dt
            return

        target = self.patrol_points[self.patrol_index]
        tx, ty = float(target[0]), float(target[1])
        dx = tx - self.world_x
        dy = ty - self.world_y
        dist = math.sqrt(dx * dx + dy * dy)

        if dist < 5:
            self.patrol_index = (self.patrol_index + 1) % len(self.patrol_points)
            self.patrol_wait = random.uniform(1.0, 3.0)
            return

        # Move toward target
        move_dist = self.speed * dt
        if dist > 0:
            nx = dx / dist * move_dist
            ny = dy / dist * move_dist
            self._try_move(nx, ny, obstacles, entities)

    def _do_enraged_chase(self, dt, player_pos, obstacles, entities):
        """Chase the player proactively using A* paths with LOS shortcut.

        Proactive approach: a path is always maintained and refreshed every
        1.5 s rather than only after the monster gets completely stuck.
        LOS check: if there is a clear line-of-sight to the player the
        monster shortcuts directly, giving natural movement in open areas.
        """
        from src.pathfind import build_walkable_grid, astar, has_los

        dx = player_pos[0] - self.world_x
        dy = player_pos[1] - self.world_y
        dist = math.sqrt(dx * dx + dy * dy)

        self._path_recompute_timer = max(0.0, self._path_recompute_timer - dt)

        # Proactively recompute path every 1.5 s (or immediately on first chase)
        if self._path_recompute_timer <= 0 and dist > TILE_SIZE * 1.5:
            self._recompute_path(player_pos, obstacles)
            self._path_recompute_timer = 1.5

        # LOS shortcut: if direct line to player is clear, skip A* path
        _los_clear = False
        if obstacles and dist > TILE_SIZE * 0.5:
            _grid_size = max(
                50, max((obs.right // TILE_SIZE for obs in obstacles), default=50) + 2)
            _grid_size = min(_grid_size, 120)
            _los_grid = build_walkable_grid(obstacles, _grid_size, _grid_size, TILE_SIZE)
            mx = max(0, min(_grid_size - 1, int(self.world_x / TILE_SIZE)))
            my = max(0, min(_grid_size - 1, int(self.world_y / TILE_SIZE)))
            px = max(0, min(_grid_size - 1, int(player_pos[0] / TILE_SIZE)))
            py = max(0, min(_grid_size - 1, int(player_pos[1] / TILE_SIZE)))
            _los_clear = has_los(_los_grid, (mx, my), (px, py))

        if _los_clear or dist <= TILE_SIZE * 1.5:
            # Direct chase — clear LOS or very close
            if dist > TILE_SIZE * 0.5:
                nx = dx / dist * self.speed * dt
                ny = dy / dist * self.speed * dt
                self._try_move(nx, ny, obstacles, entities)
            self.stuck_path = []   # discard stale path when LOS is clear
        elif self.stuck_path:
            # Follow A* waypoints toward player
            wp = self.stuck_path[self.stuck_path_idx]
            wdx = wp[0] - self.world_x
            wdy = wp[1] - self.world_y
            wdist = math.sqrt(wdx * wdx + wdy * wdy)
            if wdist < TILE_SIZE:
                self.stuck_path_idx += 1
                if self.stuck_path_idx >= len(self.stuck_path):
                    self.stuck_path = []
            elif wdist > 0:
                nx = wdx / wdist * self.speed * dt
                ny = wdy / wdist * self.speed * dt
                self._try_move(nx, ny, obstacles, entities)
        elif dist > TILE_SIZE * 0.5:
            # Fallback direct move while path is being computed
            nx = dx / dist * self.speed * dt
            ny = dy / dist * self.speed * dt
            self._try_move(nx, ny, obstacles, entities)

    def _do_boss_ai(self, dt, player_pos, obstacles, entities):
        """Boss AI with proactive A* pathfinding and LOS shortcut (mirrors enraged logic)."""
        from src.pathfind import build_walkable_grid, has_los

        dx = player_pos[0] - self.world_x
        dy = player_pos[1] - self.world_y
        dist = math.sqrt(dx * dx + dy * dy)

        # Start chasing if player is close
        chase_range = TILE_SIZE * 8
        if dist < chase_range and not self.is_chasing:
            self.is_chasing = True
            self.chase_timer = BOSS_CHASE_DURATION
            self._path_recompute_timer = 0.0  # immediate path on chase start

        if self.is_chasing:
            self.chase_timer -= dt
            if self.chase_timer <= 0 or dist > chase_range * 2:
                self.is_chasing = False
                self.stuck_path = []
                self._path_recompute_timer = 0.0
                return

            # Move toward player using proactive pathfinding
            if dist > TILE_SIZE * 0.8:
                self._path_recompute_timer = max(0.0, self._path_recompute_timer - dt)
                if self._path_recompute_timer <= 0 and dist > TILE_SIZE * 1.5:
                    self._recompute_path(player_pos, obstacles)
                    self._path_recompute_timer = 1.5

                # LOS shortcut
                _los_clear = False
                if obstacles:
                    _grid_size = max(
                        50, max((obs.right // TILE_SIZE for obs in obstacles), default=50) + 2)
                    _grid_size = min(_grid_size, 120)
                    _los_grid = build_walkable_grid(
                        obstacles, _grid_size, _grid_size, TILE_SIZE)
                    mx = max(0, min(_grid_size - 1, int(self.world_x / TILE_SIZE)))
                    my = max(0, min(_grid_size - 1, int(self.world_y / TILE_SIZE)))
                    px = max(0, min(_grid_size - 1, int(player_pos[0] / TILE_SIZE)))
                    py = max(0, min(_grid_size - 1, int(player_pos[1] / TILE_SIZE)))
                    _los_clear = has_los(_los_grid, (mx, my), (px, py))

                if _los_clear or dist <= TILE_SIZE * 1.5:
                    self.stuck_path = []
                    nx = dx / dist * BOSS_CHASE_SPEED * dt
                    ny = dy / dist * BOSS_CHASE_SPEED * dt
                    self._try_move(nx, ny, obstacles, entities)
                elif self.stuck_path:
                    wp = self.stuck_path[self.stuck_path_idx]
                    wdx = wp[0] - self.world_x
                    wdy = wp[1] - self.world_y
                    wdist = math.sqrt(wdx * wdx + wdy * wdy)
                    if wdist < TILE_SIZE:
                        self.stuck_path_idx += 1
                        if self.stuck_path_idx >= len(self.stuck_path):
                            self.stuck_path = []
                    elif wdist > 0:
                        nx = wdx / wdist * BOSS_CHASE_SPEED * dt
                        ny = wdy / wdist * BOSS_CHASE_SPEED * dt
                        self._try_move(nx, ny, obstacles, entities)
                else:
                    nx = dx / dist * BOSS_CHASE_SPEED * dt
                    ny = dy / dist * BOSS_CHASE_SPEED * dt
                    self._try_move(nx, ny, obstacles, entities)

    def _try_move(self, dx: float, dy: float, obstacles: list, entities: list):
        """Try to move by (dx, dy) with collision checking."""
        # Update facing
        if abs(dx) > abs(dy):
            self.facing = DIR_RIGHT if dx > 0 else DIR_LEFT
        elif dy != 0:
            self.facing = DIR_DOWN if dy > 0 else DIR_UP

        new_x = self.world_x + dx
        new_y = self.world_y + dy

        old_rect = self.collision_rect.copy()
        new_rect = old_rect.copy()
        new_rect.midbottom = (int(new_x), int(new_y) + self.collision_rect.height // 2)

        nearby = get_obstacle_rects_near(obstacles, old_rect, 100)
        entity_rects = []
        for e in entities:
            if e is self:
                continue
            er = getattr(e, 'collision_rect', getattr(e, 'rect', None))
            if er:
                entity_rects.append(er)

        resolved = resolve_movement(old_rect, new_rect, nearby + entity_rects)

        if resolved != old_rect:
            self.is_moving = True
            self.world_x = resolved.midbottom[0]
            self.world_y = resolved.midbottom[1] - self.collision_rect.height // 2
            self._update_collision_rect()

    def _recompute_path(self, player_pos: tuple, obstacles: list):
        """Compute an A* path around obstacles toward the player.

        Grid size is derived from the actual obstacle extents so the path is
        accurate in both 50-tile combat stages and large town stages (up to ~80
        tiles). Capped at 120 tiles to bound computation cost.
        """
        from src.pathfind import build_walkable_grid, astar

        if obstacles:
            grid_size = max(
                50, max((obs.right // TILE_SIZE for obs in obstacles), default=50) + 2)
        else:
            grid_size = 50
        grid_size = min(grid_size, 120)

        grid = build_walkable_grid(obstacles, grid_size, grid_size, TILE_SIZE)

        mx = max(0, min(grid_size - 1, int(self.world_x / TILE_SIZE)))
        my = max(0, min(grid_size - 1, int(self.world_y / TILE_SIZE)))
        px = max(0, min(grid_size - 1, int(player_pos[0] / TILE_SIZE)))
        py = max(0, min(grid_size - 1, int(player_pos[1] / TILE_SIZE)))

        path_tiles = astar(grid, (mx, my), (px, py))

        if path_tiles and len(path_tiles) > 1:
            # Convert tile coords to world-space centre of each tile, skip tile 0 (current)
            self.stuck_path = [
                ((tx + 0.5) * TILE_SIZE, (ty + 0.5) * TILE_SIZE)
                for tx, ty in path_tiles[1:]
            ]
            self.stuck_path_idx = 0
        else:
            self.stuck_path = []

    def polymorph(self, new_type: str = None, duration: float = 30.0):
        """Transform this monster into a weaker type temporarily.

        If new_type is None, auto-selects the next-weaker type from POLYMORPH_PROGRESSION.
        Bosses retain their is_boss flag; boss multipliers are re-applied to the new type's
        base stats so they remain formidable but weaker.
        """
        if self.is_polymorphed:
            return  # Already polymorphed; ignore
        if new_type is None:
            # Auto-select next-weaker type
            try:
                idx = POLYMORPH_PROGRESSION.index(self.monster_type)
            except ValueError:
                return  # Type not in progression
            if idx == 0:
                return  # Already weakest
            new_type = POLYMORPH_PROGRESSION[idx - 1]
        new_stats = MONSTER_STATS.get(new_type)
        if not new_stats:
            return
        # Save originals
        self._original_type = self.monster_type
        self._original_hp = self.hp
        self._original_damage = self.damage
        self._original_speed = self.speed
        self._original_is_boss = self.is_boss
        # Apply new stats — bosses keep their multipliers on the weaker base stats
        self.monster_type = new_type
        base_hp = new_stats["hp"]
        base_dmg = new_stats["damage"]
        if self.is_boss:
            self.hp = int(base_hp * BOSS_HP_MULT)
            self.max_hp = self.hp
            self.damage = int(base_dmg * BOSS_DAMAGE_MULT)
        else:
            self.hp = base_hp
            self.max_hp = base_hp
            self.damage = base_dmg
        self.speed = new_stats["speed"]
        self.is_polymorphed = True
        self.polymorph_timer = duration
        self.is_chasing = False
        self.is_enraged = False
        self.stuck_path = []
        self.stuck_timer = 0.0
        # Reload sprite for new type
        self.anim_set = self._load_animations()

    def _revert_polymorph(self):
        """Restore original monster type after polymorph expires."""
        if not self.is_polymorphed or self._original_type is None:
            return
        self.monster_type = self._original_type
        self.hp = max(1, self._original_hp // 2)  # Return with half original HP
        self.max_hp = self._original_hp
        self.damage = self._original_damage
        self.speed = self._original_speed
        # Restore boss flag if it was saved
        if hasattr(self, '_original_is_boss'):
            self.is_boss = self._original_is_boss
        self.is_polymorphed = False
        self.is_enraged = True  # Immediately pursue player
        self.stuck_path = []
        self.stuck_timer = 0.0
        # Reload sprite for original type
        self.anim_set = self._load_animations()

    def take_damage(self, amount: int) -> bool:
        """Apply damage. Returns True if monster died."""
        self.hp = max(0, self.hp - amount)
        if self.hp <= 0:
            self.is_alive = False
            return True
        # Non-boss monsters permanently chase the player after surviving a hit
        if not self.is_boss:
            if not self.is_enraged:
                self._just_enraged = True
                self._path_recompute_timer = 0.0  # immediate path on first enrage
            self.is_enraged = True
        # Boss: start/extend chase timer as before
        if self.is_boss and not self.is_chasing:
            self.is_chasing = True
            self.chase_timer = BOSS_CHASE_DURATION
            self._path_recompute_timer = 0.0  # immediate path on boss chase start
        return False

    def can_deal_contact_damage(self) -> bool:
        return self.is_alive and self.contact_damage_cooldown <= 0

    def deal_contact_damage(self):
        self.contact_damage_cooldown = 1.0

    def draw(self, surface: pygame.Surface, camera_offset: tuple):
        if not self.is_alive and self.death_timer > 0.5:
            return  # Fade out after death

        cam_x, cam_y = int(camera_offset[0]), int(camera_offset[1])
        pos = (self.rect.x - cam_x, self.rect.y - cam_y)

        if not self.is_alive:
            img = self.image.copy()
            img.set_alpha(max(0, int(255 * (1.0 - self.death_timer * 2))))
            surface.blit(img, pos)
            return

        surface.blit(self.image, pos)

        # --- Attack slash visual ---
        if self.is_attacking and self.attack_anim_timer > 0:
            self._draw_attack_effect(surface, cam_x, cam_y)

        # HP bar
        bar_w = self.rect.width
        bar_h = 3 if not self.is_boss else 5
        bx = pos[0]
        by = pos[1] - 6
        pygame.draw.rect(surface, (60, 0, 0), (bx, by, bar_w, bar_h))
        fill = max(0, int(bar_w * self.hp / max(self.max_hp, 1)))
        color = (255, 50, 50) if self.is_boss else (200, 50, 50)
        pygame.draw.rect(surface, color, (bx, by, fill, bar_h))

    def _draw_attack_effect(self, surface: pygame.Surface, cam_x: int, cam_y: int):
        """Draw a claw slash arc in the direction the monster is facing."""
        cx = int(self.world_x) - cam_x
        cy = int(self.world_y) - cam_y

        # Progress 0..1 through the attack animation
        progress = 1.0 - (self.attack_anim_timer / MONSTER_ATTACK_DURATION)
        progress = max(0.0, min(1.0, progress))

        # Slash arc angles (standard math: 0=right, 90=up, 180=left, -90=down)
        if self.facing == DIR_DOWN:
            start_a, end_a = -30, -150
            ox, oy = 0, 12
        elif self.facing == DIR_UP:
            start_a, end_a = 150, 30
            ox, oy = 0, -12
        elif self.facing == DIR_LEFT:
            start_a, end_a = 120, 240
            ox, oy = -12, 0
        else:  # DIR_RIGHT
            start_a, end_a = 60, -60
            ox, oy = 12, 0

        px = cx + ox
        py = cy + oy
        arc_radius = 24 if not self.is_boss else 36

        # Draw several trail dots along the arc
        num_trail = 6
        for i in range(num_trail):
            t = progress - i * 0.07
            if t < 0:
                continue
            t = max(0.0, min(1.0, t))
            a = start_a + (end_a - start_a) * t
            rad = math.radians(a)
            tx = px + math.cos(rad) * arc_radius
            ty = py - math.sin(rad) * arc_radius
            alpha = max(0, 220 - i * 45)
            trail_size = max(2, 5 - i)
            slash_color = (255, 100, 100, alpha) if self.is_boss else (255, 180, 80, alpha)
            trail_surf = pygame.Surface((trail_size * 2, trail_size * 2), pygame.SRCALPHA)
            pygame.draw.circle(trail_surf, slash_color,
                               (trail_size, trail_size), trail_size)
            surface.blit(trail_surf, (int(tx - trail_size), int(ty - trail_size)))
