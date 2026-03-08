import pygame
import os
import math
from src.settings import (PLAYER_SPEED, PLAYER_BASE_HP, PLAYER_HP_PER_LEVEL,
                          PLAYER_BASE_DAMAGE, PLAYER_DAMAGE_PER_LEVEL,
                          PLAYER_START_LEVEL, PLAYER_PICKUP_RANGE,
                          CHARS_FRAMES_PATH, SCALE_FACTOR,
                          DIR_DOWN, DIR_LEFT, DIR_RIGHT, DIR_UP,
                          ANIM_SPEED, TILE_SIZE,
                          KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT, KEY_ATTACK,
                          XP_THRESHOLDS, DEFAULT_ATTACK_COOLDOWN,
                          ARMOR_DEFS, SPELL_DEFS, GRIT_ABILITIES)
from src.animation import AnimationSet, load_character_frames
from src.collision import resolve_movement, get_obstacle_rects_near
from src.weapon import WeaponData, load_weapon_database
from src.inventory import Inventory


# ---------------------------------------------------------------------------
# Weapon sprite helpers (created once per weapon style, shared across instances)
# ---------------------------------------------------------------------------
_weapon_cache: dict = {}  # (style, blade_color_key, angle_key) -> Surface

# Trail colors per weapon style
_TRAIL_COLORS = {
    "sword":     (255, 255, 200),
    "axe":       (255, 180, 80),
    "staff":     (160, 120, 255),
    "legendary": (255, 230, 100),
    "bow":       (200, 180, 140),
    "gun":       (255, 230, 100),
}

# Direction vectors for projectile firing
_DIR_VECTORS = {
    DIR_DOWN:  (0, 1),
    DIR_UP:    (0, -1),
    DIR_LEFT:  (-1, 0),
    DIR_RIGHT: (1, 0),
}


def _create_weapon_surface(style: str = "sword",
                           blade_color: tuple = (190, 200, 220)) -> pygame.Surface:
    """Draw a weapon pointing UP on a transparent surface.
    Supports styles: sword, axe, staff, legendary."""
    handle_color = (100, 70, 40)
    guard_color = (160, 140, 60)

    if style == "axe":
        w, h = 16, 28
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        # Long handle
        pygame.draw.rect(surf, handle_color, (w // 2 - 2, 10, 4, h - 10))
        # Axe head (wide triangle on top)
        head_color = blade_color
        pygame.draw.polygon(surf, head_color, [
            (w // 2 - 1, 10), (w // 2 + 7, 0), (w // 2 + 7, 10)])
        pygame.draw.polygon(surf, head_color, [
            (w // 2 - 1, 10), (w // 2 + 7, 20), (w // 2 + 7, 10)])
        # Edge highlight
        pygame.draw.line(surf, (200, 210, 220), (w // 2 + 6, 1), (w // 2 + 6, 19), 1)
        return surf

    elif style == "staff":
        w, h = 10, 32
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        # Pole
        pygame.draw.rect(surf, (110, 80, 50), (w // 2 - 2, 8, 4, h - 8))
        # Orb on top
        orb_color = blade_color
        pygame.draw.circle(surf, orb_color, (w // 2, 5), 5)
        # Orb glow
        glow = (min(255, orb_color[0] + 60), min(255, orb_color[1] + 60),
                min(255, orb_color[2] + 60))
        pygame.draw.circle(surf, glow, (w // 2 - 1, 4), 2)
        return surf

    elif style == "legendary":
        w, h = 14, 32
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        # Glow aura (drawn first, behind blade)
        glow_surf = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(glow_surf, (255, 240, 150, 60), (w // 2 - 4, 0, 8, h - 8))
        surf.blit(glow_surf, (0, 0))
        # Handle
        pygame.draw.rect(surf, (80, 60, 30), (w // 2 - 2, h - 7, 4, 7))
        # Golden guard
        pygame.draw.rect(surf, (220, 180, 40), (1, h - 9, w - 2, 3))
        # Blade
        blade_w = 5
        bx = w // 2 - blade_w // 2
        pygame.draw.rect(surf, blade_color, (bx, 2, blade_w, h - 11))
        # Blade highlight
        pygame.draw.line(surf, (255, 255, 255), (w // 2, 3), (w // 2, h - 12), 1)
        # Blade tip
        pygame.draw.polygon(surf, blade_color,
                            [(bx, 2), (w // 2, 0), (bx + blade_w, 2)])
        return surf

    else:  # "sword" (default)
        w, h = 12, 28
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        handle_h = 6
        pygame.draw.rect(surf, handle_color, (w // 2 - 2, h - handle_h, 4, handle_h))
        guard_y = h - handle_h - 2
        pygame.draw.rect(surf, guard_color, (1, guard_y, w - 2, 3))
        blade_top = 1
        blade_bot = guard_y
        blade_w = 4
        bx = w // 2 - blade_w // 2
        pygame.draw.rect(surf, blade_color, (bx, blade_top, blade_w, blade_bot - blade_top))
        pygame.draw.line(surf, (230, 235, 245), (w // 2, blade_top + 2),
                         (w // 2, blade_bot - 2), 1)
        pygame.draw.polygon(surf, blade_color,
                            [(bx, blade_top), (w // 2, 0), (bx + blade_w, blade_top)])
        return surf


def _create_bow_surface(blade_color: tuple = (140, 100, 60)) -> pygame.Surface:
    """Draw a bow pointing UP on a transparent surface."""
    w, h = 14, 28
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    # Bow arc (curved wood)
    pygame.draw.arc(surf, blade_color, (0, 2, 12, 24), -1.2, 1.2, 2)
    # String
    pygame.draw.line(surf, (200, 200, 200), (6, 3), (6, 25), 1)
    return surf


def _create_gun_surface(blade_color: tuple = (80, 80, 90)) -> pygame.Surface:
    """Draw a gun pointing UP on a transparent surface."""
    w, h = 10, 22
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    # Barrel
    pygame.draw.rect(surf, blade_color, (3, 0, 4, 14))
    # Barrel tip highlight
    pygame.draw.rect(surf, (140, 140, 150), (4, 0, 2, 2))
    # Body/receiver
    pygame.draw.rect(surf, blade_color, (2, 12, 6, 4))
    # Handle (angled down)
    pygame.draw.polygon(surf, (100, 70, 40), [
        (3, 16), (7, 16), (6, 22), (2, 22)])
    return surf


def _get_weapon_rotated(style: str, blade_color: tuple, angle: float) -> pygame.Surface:
    """Return a rotated weapon surface (cached by style + color + angle)."""
    color_key = blade_color[:3]  # Ensure tuple of 3
    key = (style, color_key, int(angle))
    if key not in _weapon_cache:
        if style == "bow":
            base = _create_bow_surface(blade_color)
        elif style == "gun":
            base = _create_gun_surface(blade_color)
        else:
            base = _create_weapon_surface(style, blade_color)
        _weapon_cache[key] = pygame.transform.rotate(base, angle)
    return _weapon_cache[key]


# Sword carry angles per direction (0 = up, 90 = left, etc.)
_SWORD_CARRY = {
    DIR_DOWN:  {"angle": 180, "offset": (12, 8)},
    DIR_UP:    {"angle": 0, "offset": (-10, -6)},
    DIR_LEFT:  {"angle": 90, "offset": (-16, 4)},
    DIR_RIGHT: {"angle": -90, "offset": (16, 4)},
}

# Attack swing: angles in standard math convention (0=right, 90=up, 180=left, -90=down)
# The sword arcs from "start" to "end" in the direction the player faces.
# px/py = pivot offset from player center toward the facing direction.
_SWORD_SWING = {
    DIR_DOWN:  {"start": -30,  "end": -150, "px": 0,   "py": 10},
    DIR_UP:    {"start": 150,  "end": 30,   "px": 0,   "py": -10},
    DIR_LEFT:  {"start": 120,  "end": 240,  "px": -10, "py": 0},
    DIR_RIGHT: {"start": 60,   "end": -60,  "px": 10,  "py": 0},
}
SWING_RADIUS = 34  # Distance from pivot to sword tip on the arc

ATTACK_DURATION = 0.3  # Seconds for attack animation


class Player(pygame.sprite.Sprite):
    def __init__(self, x: float, y: float, hero_info: dict):
        """Create a player.

        hero_info: dict with keys 'id', 'name', 'sprite_dir'
            (from HERO_CHARACTERS in settings).
        """
        super().__init__()
        self.world_x = float(x)
        self.world_y = float(y)
        self.character = hero_info["name"]
        self.sprite_dir = hero_info["sprite_dir"]

        # Per-hero stat multipliers
        self.hp_mult = hero_info.get("hp_mult", 1.0)

        # Stats
        self.level = PLAYER_START_LEVEL
        self.xp = 0
        self.max_hp = int(PLAYER_BASE_HP * self.hp_mult)
        self.hp = self.max_hp
        self.gold = 0
        self.base_damage = PLAYER_BASE_DAMAGE
        self.speed = PLAYER_SPEED

        # Hero class id (for armor restrictions)
        self.hero_id = hero_info["id"]

        # Mana system
        self.mana_base = hero_info.get("mana_base", 0)
        self.mana_per_level = hero_info.get("mana_per_level", 0)
        self.mana_regen = hero_info.get("mana_regen", 0.0)  # mana/sec (0 = no regen)
        self.max_mana = self.mana_base
        self.mana = float(self.max_mana)
        self.spell_cooldown = 0.0  # kept for backward compat; primary tracking via spell_cooldowns

        # Multi-spell system: list of spell defs for this hero (from SPELL_DEFS[hero_id])
        self._spell_list = list(SPELL_DEFS.get(self.hero_id, []))
        # spell_cooldowns: {spell_id: remaining_cooldown_seconds}
        self.spell_cooldowns: dict = {}
        # Backward-compat: self.spell points to the currently selected spell or first spell
        self.spell = self._spell_list[0] if self._spell_list else None

        # Grit system (Warrior and Ranger)
        self.grit_base = hero_info.get("grit_base", 0)
        self.grit_per_level = hero_info.get("grit_per_level", 0)
        self.grit_regen = hero_info.get("grit_regen", 0.0)  # grit/sec
        self.max_grit = self.grit_base
        self.grit = float(self.max_grit)
        self.grit_cooldown = 0.0  # kept for backward compat
        # Multi-ability system: list of ability defs for this hero (from GRIT_ABILITIES[hero_id])
        self._ability_list = list(GRIT_ABILITIES.get(self.hero_id, []))
        # ability_cooldowns: {ability_id: remaining_cooldown_seconds}
        self.ability_cooldowns: dict = {}
        # Backward-compat: grit_ability points to first ability or None
        self.grit_ability = self._ability_list[0] if self._ability_list else None
        self.lunge_active = False  # Set True during a Lunge strike
        self.xp_required_mult = hero_info.get("xp_required_mult", 1.0)

        # Spell / ability selection index (into get_castable_spells())
        self.selected_spell_idx = 0

        # Shield system: absorbs raw damage before armor
        self.shield_hp = 0  # remaining absorption points

        # Timed ability states (seconds remaining; 0 = inactive)
        self.action_surge_timer = 0.0
        self.whirlwind_timer = 0.0
        self.blazing_sword_timer = 0.0
        self.double_fire_timer = 0.0

        # Inventory and equipment
        self.inventory = Inventory()
        self.equipped_armor = None  # dict with id, name, defense, etc. or None
        weapon_db = load_weapon_database()
        starting_weapon_id = hero_info.get("starting_weapon", "basic_sword")
        self.equipped_weapon = weapon_db.get(starting_weapon_id, weapon_db.get("basic_sword"))
        self.weapon_db = weapon_db

        # Combat
        self.attack_cooldown = 0.0
        self.is_attacking = False
        self.attack_timer = 0.0
        self.facing = DIR_DOWN

        # Buffs: dict of buff_type -> {"value": float, "remaining": float}
        self.buffs = {}

        # Animation — load from individual frame files
        frame_dir = os.path.join(CHARS_FRAMES_PATH, "chara", self.sprite_dir)
        self.anim_set = load_character_frames(frame_dir, SCALE_FACTOR, ANIM_SPEED)

        self.image = self.anim_set.update(0)
        self.rect = self.image.get_rect(center=(int(self.world_x), int(self.world_y)))

        # Collision rect (smaller than sprite for forgiving movement)
        self.collision_rect = pygame.Rect(0, 0, TILE_SIZE * 0.6, TILE_SIZE * 0.4)
        self._update_collision_rect()

        # State
        self.is_alive = True
        self.is_moving = False

        # Slash trail points (for the attack arc visual)
        self._slash_trail: list = []  # list of (x, y, alpha) for the trail

    def _update_collision_rect(self):
        self.collision_rect.midbottom = (int(self.world_x), int(self.world_y) + TILE_SIZE // 3)

    def handle_input(self, keys, dt: float, obstacles: list, entities: list,
                     controller_move: tuple = None):
        """Process WASD movement and controller input."""
        if not self.is_alive:
            return

        dx, dy = 0.0, 0.0
        speed = self.get_effective_speed()

        if keys[KEY_UP]:
            dy -= speed * dt
            self.facing = DIR_UP
        if keys[KEY_DOWN]:
            dy += speed * dt
            self.facing = DIR_DOWN
        if keys[KEY_LEFT]:
            dx -= speed * dt
            self.facing = DIR_LEFT
        if keys[KEY_RIGHT]:
            dx += speed * dt
            self.facing = DIR_RIGHT

        # Controller stick/d-pad movement (additive with keyboard)
        if controller_move and (dx == 0 and dy == 0):
            cmx, cmy = controller_move
            if cmx != 0 or cmy != 0:
                dx = cmx * speed * dt
                dy = cmy * speed * dt
                # Set facing based on dominant axis
                if abs(cmx) > abs(cmy):
                    self.facing = DIR_RIGHT if cmx > 0 else DIR_LEFT
                elif abs(cmy) > 0:
                    self.facing = DIR_DOWN if cmy > 0 else DIR_UP

        self.is_moving = dx != 0 or dy != 0

        if self.is_moving:
            # Normalize diagonal movement
            if dx != 0 and dy != 0:
                factor = 0.7071  # 1/sqrt(2)
                dx *= factor
                dy *= factor

            # Try movement with collision
            new_x = self.world_x + dx
            new_y = self.world_y + dy

            old_rect = self.collision_rect.copy()
            new_rect = old_rect.copy()
            new_rect.midbottom = (int(new_x), int(new_y) + TILE_SIZE // 3)

            nearby_obstacles = get_obstacle_rects_near(obstacles, old_rect)

            # Also check entity collision
            entity_rects = []
            for e in entities:
                if e is self:
                    continue
                er = getattr(e, 'collision_rect', getattr(e, 'rect', None))
                if er:
                    entity_rects.append(er)

            all_blockers = nearby_obstacles + entity_rects
            resolved = resolve_movement(old_rect, new_rect, all_blockers)

            self.world_x = resolved.midbottom[0]
            self.world_y = resolved.midbottom[1] - TILE_SIZE // 3
            self._update_collision_rect()

    def attack(self) -> pygame.Rect | None:
        """Attempt to attack. Returns attack hitbox rect or None if on cooldown
        or if weapon is ranged (ranged weapons spawn projectiles instead)."""
        if not self.is_alive or self.attack_cooldown > 0:
            return None

        # Action Surge halves the attack cooldown
        base_cooldown = self.equipped_weapon.speed * self.get_attack_cooldown_mult()
        self.attack_cooldown = base_cooldown
        self.is_attacking = True
        self.attack_timer = ATTACK_DURATION
        self._slash_trail = []  # Reset slash trail for new attack

        # Ranged weapons don't create a melee hitbox
        if self.equipped_weapon.is_ranged:
            return None

        # Create attack hitbox in front of player based on facing direction
        wpn_range = self.equipped_weapon.range
        if self.lunge_active:
            wpn_range += 100
        if self.blazing_sword_timer > 0:
            wpn_range += 50  # Blazing Sword extends range
        hx, hy = self.world_x, self.world_y
        hw, hh = wpn_range, TILE_SIZE * 0.8

        if self.facing == DIR_UP:
            hy -= wpn_range
            hw, hh = TILE_SIZE * 0.8, wpn_range
        elif self.facing == DIR_DOWN:
            hy += TILE_SIZE // 2
            hw, hh = TILE_SIZE * 0.8, wpn_range
        elif self.facing == DIR_LEFT:
            hx -= wpn_range
        elif self.facing == DIR_RIGHT:
            hx += TILE_SIZE // 2

        return pygame.Rect(int(hx - hw // 2), int(hy - hh // 2), int(hw), int(hh))

    def get_projectile_info(self) -> dict | None:
        """Get info for spawning a projectile. Call after attack() for ranged weapons.
        Returns dict with spawn_x, spawn_y, direction, speed, damage, range, style
        or None if not a ranged weapon."""
        if not self.equipped_weapon.is_ranged:
            return None
        dir_vec = _DIR_VECTORS[self.facing]
        # Spawn projectile slightly in front of player
        offset = TILE_SIZE * 0.5
        return {
            "spawn_x": self.world_x + dir_vec[0] * offset,
            "spawn_y": self.world_y + dir_vec[1] * offset,
            "direction": dir_vec,
            "speed": self.equipped_weapon.projectile_speed,
            "damage": self.get_damage(),
            "max_range": self.equipped_weapon.range,
            "style": self.equipped_weapon.projectile_style,
        }

    # -----------------------------------------------------------------------
    # Multi-spell / multi-ability system
    # -----------------------------------------------------------------------

    def get_available_spells(self) -> list:
        """All spells/abilities unlocked at the current level (including auto-trigger)."""
        src = self._spell_list if self._spell_list else self._ability_list
        return [s for s in src if s.get("min_level", 1) <= self.level]

    def get_castable_spells(self) -> list:
        """Spells/abilities shown in the HUD list (excludes auto_trigger resurrections)."""
        return [s for s in self.get_available_spells() if not s.get("auto_trigger")]

    def get_auto_spell(self):
        """Return the resurrection ability if it is both selected and has auto_trigger."""
        all_avail = self.get_available_spells()
        for s in all_avail:
            if s.get("auto_trigger"):
                return s
        return None

    def get_selected_ability(self):
        """Return the currently selected castable spell/ability dict, or None."""
        castable = self.get_castable_spells()
        if not castable:
            return None
        idx = min(self.selected_spell_idx, len(castable) - 1)
        return castable[idx]

    def select_ability_by_number(self, n: int):
        """Select spell/ability by 1-based index (from number key press)."""
        castable = self.get_castable_spells()
        if 1 <= n <= len(castable):
            self.selected_spell_idx = n - 1

    def cycle_ability(self, direction: int):
        """Cycle selection forward (+1) or backward (-1)."""
        castable = self.get_castable_spells()
        if castable:
            self.selected_spell_idx = (self.selected_spell_idx + direction) % len(castable)

    def get_ability_cooldown(self, ability_id: str) -> float:
        """Return remaining cooldown seconds for a spell/ability."""
        return max(self.spell_cooldowns.get(ability_id, 0.0),
                   self.ability_cooldowns.get(ability_id, 0.0))

    def set_ability_cooldown(self, ability_id: str, duration: float):
        """Set cooldown for a spell or grit ability by id."""
        if self._spell_list:
            self.spell_cooldowns[ability_id] = duration
        else:
            self.ability_cooldowns[ability_id] = duration

    def get_damage(self) -> int:
        dmg = self.base_damage + self.equipped_weapon.damage
        buff = self.buffs.get("damage_up")
        if buff and buff["remaining"] > 0:
            dmg += int(buff["value"])
        if self.lunge_active:
            dmg *= 2
        if self.action_surge_timer > 0:
            dmg *= 2
        return int(dmg)

    def get_effective_speed(self) -> float:
        speed = self.speed
        buff = self.buffs.get("speed_up")
        if buff and buff["remaining"] > 0:
            speed *= (1.0 + buff["value"] / 100.0)
        if self.action_surge_timer > 0:
            speed *= 2.0
        return speed

    def get_attack_cooldown_mult(self) -> float:
        """Return attack cooldown multiplier (0.5 = twice as fast during Action Surge)."""
        return 0.5 if self.action_surge_timer > 0 else 1.0

    def take_damage(self, amount: int) -> int:
        """Take damage. Shield absorbs first, then armor, then HP. Returns actual damage taken."""
        if not self.is_alive:
            return 0
        # Shield absorbs raw damage before armor
        if self.shield_hp > 0:
            absorbed = min(self.shield_hp, amount)
            self.shield_hp -= absorbed
            amount -= absorbed
            if amount <= 0:
                return 0  # fully blocked by shield
        defense = 0
        # Armor defense (permanent while equipped)
        if self.equipped_armor:
            defense += self.equipped_armor.get("defense", 0)
        # Buff defense (temporary)
        buff = self.buffs.get("defense_up")
        if buff and buff["remaining"] > 0:
            defense += int(buff["value"])
        actual = max(1, amount - defense)
        self.hp = max(0, self.hp - actual)
        if self.hp <= 0:
            self.is_alive = False
        return actual

    def heal(self, amount: int):
        self.hp = min(self.max_hp, self.hp + amount)

    def use_mana(self, cost: int) -> bool:
        """Consume mana. Returns True if successful, False if not enough."""
        if self.mana < cost:
            return False
        self.mana -= cost
        return True

    def use_grit(self, cost: int) -> bool:
        """Consume grit. Returns True if successful, False if not enough."""
        if self.grit < cost:
            return False
        self.grit -= cost
        return True

    def gain_xp(self, amount: int) -> bool:
        """Add XP. Returns True if leveled up."""
        MAX_LEVEL = len(XP_THRESHOLDS) - 1  # 20
        if self.level >= MAX_LEVEL:
            return False  # Already at max level
        self.xp += amount
        raw_threshold = (XP_THRESHOLDS[self.level + 1]
                         if self.level + 1 < len(XP_THRESHOLDS)
                         else XP_THRESHOLDS[-1])
        next_threshold = int(raw_threshold * self.xp_required_mult)
        if self.xp >= next_threshold:
            prev_level = self.level
            self.level += 1
            self.max_hp = int((PLAYER_BASE_HP + (self.level - 1) * PLAYER_HP_PER_LEVEL)
                              * self.hp_mult)
            self.hp = self.max_hp  # Full heal on level up
            self.base_damage = PLAYER_BASE_DAMAGE + (self.level - 1) * PLAYER_DAMAGE_PER_LEVEL
            # Mana growth on level up
            if self.mana_per_level > 0:
                self.max_mana = self.mana_base + (self.level - 1) * self.mana_per_level
                self.mana = float(self.max_mana)  # Full mana restore on level up
            # Grit growth on level up
            if self.grit_per_level > 0:
                self.max_grit = self.grit_base + (self.level - 1) * self.grit_per_level
                self.grit = float(self.max_grit)  # Full grit restore on level up
            # Track newly unlocked spells/abilities
            prev_count = len([s for s in (self._spell_list or self._ability_list)
                               if s.get("min_level", 1) <= prev_level])
            new_count = len([s for s in (self._spell_list or self._ability_list)
                              if s.get("min_level", 1) <= self.level])
            self._new_spells_at_levelup = new_count - prev_count  # checked by game.py
            return True
        self._new_spells_at_levelup = 0
        return False

    def gain_gold(self, amount: int):
        self.gold += amount

    def apply_buff(self, buff_type: str, value: float, duration: float):
        if buff_type == "heal":
            self.heal(int(value))
            return
        self.buffs[buff_type] = {"value": value, "remaining": duration}

    def update_buffs(self, dt: float):
        for buff_type in list(self.buffs.keys()):
            self.buffs[buff_type]["remaining"] -= dt
            if self.buffs[buff_type]["remaining"] <= 0:
                del self.buffs[buff_type]

        # Per-spell cooldown dicts (multi-spell system)
        for key in list(self.spell_cooldowns.keys()):
            self.spell_cooldowns[key] = max(0.0, self.spell_cooldowns[key] - dt)
        for key in list(self.ability_cooldowns.keys()):
            self.ability_cooldowns[key] = max(0.0, self.ability_cooldowns[key] - dt)

        # Spell cooldown (legacy, kept for compat)
        if self.spell_cooldown > 0:
            self.spell_cooldown = max(0.0, self.spell_cooldown - dt)

        # Passive mana regen (hero-specific rate: Mage 0.5/sec, Paladin 0.333/sec)
        if self.mana_regen > 0 and self.mana < self.max_mana:
            self.mana = min(float(self.max_mana), self.mana + self.mana_regen * dt)

        # Grit cooldown (legacy, kept for compat)
        if self.grit_cooldown > 0:
            self.grit_cooldown = max(0.0, self.grit_cooldown - dt)

        # Passive grit regen (Warrior 0.5/sec, Ranger 0.333/sec)
        if self.grit_regen > 0 and self.grit < self.max_grit:
            self.grit = min(float(self.max_grit), self.grit + self.grit_regen * dt)

        # Timed ability timers
        if self.action_surge_timer > 0:
            self.action_surge_timer = max(0.0, self.action_surge_timer - dt)
        if self.whirlwind_timer > 0:
            self.whirlwind_timer = max(0.0, self.whirlwind_timer - dt)
        if self.blazing_sword_timer > 0:
            self.blazing_sword_timer = max(0.0, self.blazing_sword_timer - dt)
        if self.double_fire_timer > 0:
            self.double_fire_timer = max(0.0, self.double_fire_timer - dt)

    def equip_weapon(self, weapon_id: str):
        """Equip a weapon by ID. Returns the old WeaponData on success,
        False if the hero's class cannot wield it, or None if weapon not found."""
        new_weapon = self.weapon_db.get(weapon_id)
        if not new_weapon:
            return None
        if new_weapon.classes and self.hero_id not in new_weapon.classes:
            return False  # Class restriction failed
        old = self.equipped_weapon
        self.equipped_weapon = new_weapon
        return old

    def equip_armor(self, armor_id: str):
        """Equip armor by ID. Returns old armor dict, None if no old armor,
        or False if class restriction prevents equipping."""
        armor_def = ARMOR_DEFS.get(armor_id)
        if not armor_def:
            return None
        if self.hero_id not in armor_def.get("classes", []):
            return False  # Class restriction failed
        old = self.equipped_armor
        self.equipped_armor = {"id": armor_id, **armor_def}
        return old

    def update(self, dt: float):
        """Update animations and cooldowns."""
        self.update_buffs(dt)

        if self.attack_cooldown > 0:
            self.attack_cooldown -= dt
        if self.attack_timer > 0:
            self.attack_timer -= dt
            if self.attack_timer <= 0:
                self.is_attacking = False

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

    def draw(self, surface: pygame.Surface, camera_offset: tuple):
        cam_x, cam_y = int(camera_offset[0]), int(camera_offset[1])
        pos = (self.rect.x - cam_x, self.rect.y - cam_y)
        cx = int(self.world_x) - cam_x  # Player center on screen
        cy = int(self.world_y) - cam_y

        # --- Draw character sprite ---
        surface.blit(self.image, pos)

        # --- Draw weapon ---
        if self.is_alive:
            if self.is_attacking:
                if self.equipped_weapon.is_ranged:
                    self._draw_ranged_attack(surface, cx, cy)
                else:
                    self._draw_weapon_swing(surface, cx, cy)
            else:
                self._draw_weapon_carry(surface, cx, cy)

        # --- Draw HP bar above player ---
        if self.is_alive:
            bar_w = TILE_SIZE
            bar_h = 4
            bx = pos[0] + (self.rect.width - bar_w) // 2
            by = pos[1] - 8
            pygame.draw.rect(surface, (60, 0, 0), (bx, by, bar_w, bar_h))
            fill = max(0, int(bar_w * self.hp / max(self.max_hp, 1)))
            pygame.draw.rect(surface, (0, 200, 0), (bx, by, fill, bar_h))

    def _draw_weapon_carry(self, surface: pygame.Surface, cx: int, cy: int):
        """Draw the equipped weapon held at the player's side (idle/walk)."""
        wpn = self.equipped_weapon
        info = _SWORD_CARRY[self.facing]
        weapon_img = _get_weapon_rotated(wpn.style, wpn.blade_color, info["angle"])
        ox, oy = info["offset"]
        sx = cx + ox - weapon_img.get_width() // 2
        sy = cy + oy - weapon_img.get_height() // 2
        surface.blit(weapon_img, (sx, sy))

    def _draw_weapon_swing(self, surface: pygame.Surface, cx: int, cy: int):
        """Draw the equipped weapon mid-swing and a slash arc trail.

        Angles are in standard math convention (0=right, 90=up, 180=left).
        Screen-space Y is inverted so we use: tip_y = cy - sin(angle) * radius.
        Pygame rotation for the weapon: pygame_rot = standard_angle - 90.
        """
        wpn = self.equipped_weapon
        swing = _SWORD_SWING[self.facing]
        # Progress 0..1 through the attack
        progress = 1.0 - (self.attack_timer / ATTACK_DURATION)
        progress = max(0.0, min(1.0, progress))

        # Interpolate angle in standard math convention
        start_a = swing["start"]
        end_a = swing["end"]
        current_angle = start_a + (end_a - start_a) * progress

        # Weapon pivot point (offset from player center toward facing)
        px = cx + swing["px"]
        py = cy + swing["py"]

        # Rotate weapon so blade points outward along the arc
        pygame_rot = current_angle - 90
        weapon_img = _get_weapon_rotated(wpn.style, wpn.blade_color, pygame_rot)

        # Position the weapon center partway along the arc
        arm_len = 20
        rad = math.radians(current_angle)
        sx = px + math.cos(rad) * arm_len - weapon_img.get_width() // 2
        sy = py - math.sin(rad) * arm_len - weapon_img.get_height() // 2
        surface.blit(weapon_img, (int(sx), int(sy)))

        # --- Draw slash arc trail (color depends on weapon style) ---
        trail_color = _TRAIL_COLORS.get(wpn.style, (255, 255, 200))
        arc_radius = SWING_RADIUS
        num_trail = 8
        for i in range(num_trail):
            t = progress - i * 0.06
            if t < 0:
                continue
            t = max(0.0, min(1.0, t))
            a = start_a + (end_a - start_a) * t
            rad_t = math.radians(a)
            tx = px + math.cos(rad_t) * arc_radius
            ty = py - math.sin(rad_t) * arc_radius
            alpha = max(0, 255 - i * 40)
            trail_size = max(2, 6 - i)
            trail_surf = pygame.Surface((trail_size * 2, trail_size * 2), pygame.SRCALPHA)
            pygame.draw.circle(trail_surf, (*trail_color, alpha),
                               (trail_size, trail_size), trail_size)
            surface.blit(trail_surf, (int(tx - trail_size), int(ty - trail_size)))

    def _draw_ranged_attack(self, surface: pygame.Surface, cx: int, cy: int):
        """Draw ranged weapon with a brief recoil animation during attack."""
        wpn = self.equipped_weapon
        info = _SWORD_CARRY[self.facing]
        weapon_img = _get_weapon_rotated(wpn.style, wpn.blade_color, info["angle"])
        ox, oy = info["offset"]

        # Recoil: push weapon back slightly then return
        progress = 1.0 - (self.attack_timer / ATTACK_DURATION)
        progress = max(0.0, min(1.0, progress))
        recoil = math.sin(progress * math.pi) * 6  # peaks at mid-attack

        # Recoil direction is opposite to facing
        dir_vec = _DIR_VECTORS[self.facing]
        rx = -dir_vec[0] * recoil
        ry = -dir_vec[1] * recoil

        sx = cx + ox + rx - weapon_img.get_width() // 2
        sy = cy + oy + ry - weapon_img.get_height() // 2
        surface.blit(weapon_img, (int(sx), int(sy)))

        # Small muzzle flash / string release effect
        if progress < 0.3:
            flash_x = cx + dir_vec[0] * 20
            flash_y = cy + dir_vec[1] * 20
            flash_surf = pygame.Surface((8, 8), pygame.SRCALPHA)
            alpha = int(255 * (1.0 - progress / 0.3))
            if wpn.style == "gun":
                pygame.draw.circle(flash_surf, (255, 230, 100, alpha), (4, 4), 4)
            elif wpn.projectile_style == "magic":
                pygame.draw.circle(flash_surf, (160, 100, 255, alpha), (4, 4), 4)
            else:
                pygame.draw.circle(flash_surf, (200, 200, 220, alpha), (4, 4), 3)
            surface.blit(flash_surf, (int(flash_x - 4), int(flash_y - 4)))
