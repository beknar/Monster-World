import pygame
import os
import ctypes
import math
import src.settings as settings
from src.settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS, TITLE, TILE_SIZE,
    KEY_ATTACK, KEY_PICKUP, KEY_INVENTORY, KEY_INVENTORY_ALT, KEY_ESCAPE,
    KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT, KEY_SPELL,
    HERO_CHARACTERS, DEFAULT_HERO_INDEX, PLAYER_BASE_HP,
    CHARS_FRAMES_PATH, SCALE_FACTOR, AVAILABLE_RESOLUTIONS,
    COMBAT_MUSIC_ROTATION, TOWN_MUSIC_ROTATION, BOSS_MUSIC,
    BLACK, WHITE, YELLOW, GRAY, RED, GOLD_COLOR, GREEN, BLUE,
    CONTROLLER_DEADZONE, CONTROLLER_BUTTON_ATTACK, CONTROLLER_BUTTON_PICKUP,
    CONTROLLER_BUTTON_INVENTORY, CONTROLLER_BUTTON_MINIMAP,
    CONTROLLER_BUTTON_LB, CONTROLLER_BUTTON_RB,
    CONTROLLER_BUTTON_BACK, CONTROLLER_BUTTON_START,
    CONTROLLER_AXIS_LX, CONTROLLER_AXIS_LY,
    MONSTER_STATS, BOSS_HP_MULT, BOSS_DAMAGE_MULT,
    PLAYER_SPEED, BOSS_CHASE_SPEED,
    ARMOR_DEFS, SPELL_DEFS, GRIT_ABILITIES, XP_THRESHOLDS,
    STAGE_BOSSES, BOSS_STAGE_SCALING,
)
from src.player import Player
from src.camera import Camera
from src.audio import AudioManager
from src.hud import HUD
from src.combat import CombatSystem
from src.item import load_item_database, ItemType
from src.weapon import load_weapon_database
from src.loot import load_drop_tables, GroundItem, GoldDrop
from src.shop import load_shops
from src.stage import generate_stage
from src.inventory import Inventory
from src.animation import _load_and_scale
from src.projectile import Projectile
from src.savegame import (ensure_saves_dir, list_saves, save_game,
                          load_save, delete_save, MAX_SAVE_NAME_LENGTH,
                          MAX_SAVE_SLOTS,
                          save_autosave, load_autosave, has_autosave,
                          delete_autosave)


class FloatingText:
    """A damage number that floats upward and fades out in world space."""

    def __init__(self, x: float, y: float, text: str, color: tuple,
                 rise_speed: float = 60.0, duration: float = 0.8):
        self.world_x = x
        self.world_y = y
        self.text = text
        self.color = color
        self.rise_speed = rise_speed
        self.duration = duration
        self.timer = duration
        self.is_alive = True

    def update(self, dt: float):
        self.world_y -= self.rise_speed * dt
        self.timer -= dt
        if self.timer <= 0:
            self.is_alive = False

    def draw(self, surface: pygame.Surface, camera_offset: tuple,
             font: pygame.font.Font):
        if not self.is_alive:
            return
        alpha = max(0, min(255, int(255 * (self.timer / self.duration))))
        text_surf = font.render(self.text, True, self.color)
        text_surf.set_alpha(alpha)
        sx = int(self.world_x - camera_offset[0]) - text_surf.get_width() // 2
        sy = int(self.world_y - camera_offset[1]) - text_surf.get_height() // 2
        surface.blit(text_surf, (sx, sy))


class SpellEffect:
    """Visual effect for spell casting (beam, expanding circle, cone, etc.)."""

    def __init__(self, effect_type: str, x: float, y: float,
                 direction: tuple, range_val: float, duration: float = 0.4,
                 cone_half_width: float = 25.0):
        self.effect_type = effect_type  # "beam", "aoe_circle", or "cone"
        self.world_x = x
        self.world_y = y
        self.direction = direction  # (dx, dy) tuple for beams/cones
        self.range_val = range_val
        self.cone_half_width = cone_half_width  # half-width at cone tip for "cone" type
        self.duration = duration
        self.timer = duration
        self.is_alive = True

    def update(self, dt: float):
        self.timer -= dt
        if self.timer <= 0:
            self.is_alive = False

    def draw(self, surface: pygame.Surface, camera_offset: tuple):
        if not self.is_alive:
            return
        alpha = int(255 * (self.timer / self.duration))
        cam_x, cam_y = int(camera_offset[0]), int(camera_offset[1])
        sx = int(self.world_x) - cam_x
        sy = int(self.world_y) - cam_y

        if self.effect_type == "beam":
            # Draw a bright beam line from player in direction
            dx, dy = self.direction
            end_x = sx + int(dx * self.range_val)
            end_y = sy + int(dy * self.range_val)
            # Glow (wider, transparent)
            beam_surf = pygame.Surface(
                (settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT), pygame.SRCALPHA)
            pygame.draw.line(beam_surf, (255, 255, 200, alpha // 2),
                             (sx, sy), (end_x, end_y), 8)
            # Core (bright, narrow)
            pygame.draw.line(beam_surf, (255, 255, 255, alpha),
                             (sx, sy), (end_x, end_y), 3)
            surface.blit(beam_surf, (0, 0))

        elif self.effect_type == "aoe_circle":
            # Draw expanding circle of light
            progress = 1.0 - (self.timer / self.duration)
            radius = int(self.range_val * min(1.0, progress * 2))
            if radius < 1:
                return
            circle_surf = pygame.Surface(
                (radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA)
            center = (radius + 2, radius + 2)
            # Outer glow
            pygame.draw.circle(circle_surf, (255, 255, 150, alpha // 3),
                               center, radius)
            # Ring
            if radius > 3:
                pygame.draw.circle(circle_surf, (255, 255, 200, alpha),
                                   center, radius, 3)
            # Bright center
            pygame.draw.circle(circle_surf, (255, 255, 255, alpha // 2),
                               center, max(3, radius // 3))
            surface.blit(circle_surf, (sx - radius - 2, sy - radius - 2))

        elif self.effect_type == "cone":
            # Draw a filled red cone (triangle) in the facing direction
            dx, dy = self.direction
            length = self.range_val
            half_w = self.cone_half_width
            # Perpendicular direction (rotated 90°)
            perp_x, perp_y = -dy, dx
            tip = (sx, sy)
            left = (sx + int(dx * length + perp_x * half_w),
                    sy + int(dy * length + perp_y * half_w))
            right = (sx + int(dx * length - perp_x * half_w),
                     sy + int(dy * length - perp_y * half_w))
            cone_surf = pygame.Surface(
                (settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT), pygame.SRCALPHA)
            # Filled cone (semi-transparent red)
            pygame.draw.polygon(cone_surf, (255, 50, 50, alpha // 2),
                                [tip, left, right])
            # Bright outline
            pygame.draw.polygon(cone_surf, (255, 160, 80, alpha),
                                [tip, left, right], 2)
            # Central highlight line
            tip_far = (sx + int(dx * length), sy + int(dy * length))
            pygame.draw.line(cone_surf, (255, 220, 150, alpha),
                             tip, tip_far, 2)
            surface.blit(cone_surf, (0, 0))


def _beam_hitbox(px: float, py: float, direction: tuple,
                 range_val: float) -> pygame.Rect:
    """Create a thin rectangle along the beam direction for collision."""
    dx, dy = direction
    if abs(dx) > abs(dy):  # Horizontal beam
        x = px if dx > 0 else px - range_val
        return pygame.Rect(int(x), int(py - 8), int(range_val), 16)
    else:  # Vertical beam
        y = py if dy > 0 else py - range_val
        return pygame.Rect(int(px - 8), int(y), 16, int(range_val))


class Game:
    """Main game class managing the game loop and state."""

    # Game states
    STATE_MENU = "menu"
    STATE_HELP = "help"
    STATE_OPTIONS = "options"
    STATE_PLAYING = "playing"
    STATE_INVENTORY = "inventory"
    STATE_SHOP = "shop"
    STATE_PAUSED = "paused"
    STATE_GAME_OVER = "game_over"
    STATE_WIN = "win"
    STATE_SAVE_DIALOG = "save_dialog"
    STATE_LOAD_DIALOG = "load_dialog"
    STATE_DELETE_DIALOG = "delete_dialog"

    def __init__(self):
        # Override high DPI scaling on Windows so the game renders at true resolution
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass

        pygame.init()
        pygame.display.set_caption(TITLE)
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.running = True
        self.state = self.STATE_MENU

        # Fonts (scaled to resolution)
        self._create_fonts()

        # Systems
        self.audio = AudioManager()
        self.hud = HUD()
        self.combat = CombatSystem(self.audio)

        # Data
        self.item_db = load_item_database()
        self.weapon_db = load_weapon_database()
        self.drop_tables = load_drop_tables()
        self.shops = load_shops(self.item_db)

        # Item icons cache
        self.item_icons = {}
        self._load_item_icons()

        # Character selection
        self.selected_hero_index = DEFAULT_HERO_INDEX
        self.menu_button_sel = -1  # -1=hero row, 0=Start, 1=Help, 2=Options
        self.hero_previews = []  # List of (idle_surface, name) for menu
        self._load_hero_previews()

        # Pause menu volume slider selection (0=music, 1=sfx)
        self.pause_slider_sel = 0

        # Resolution tracking (default 1024x768 = index 2)
        self.resolution_index = 2  # Index into AVAILABLE_RESOLUTIONS

        # Help screen scroll
        self.help_scroll_y = 0

        # Stage tracking
        self.current_stage_num = 1
        self.current_stage_type = "combat"  # "combat" or "town"
        self.total_combat_stages = 10

        # Game objects (initialized on new game)
        self.player = None
        self.camera = None
        self.stage = None
        self.ground_items = pygame.sprite.Group()
        self.gold_drops = pygame.sprite.Group()
        self.projectiles = []  # Active projectiles (arrows, bullets)
        self.floating_texts = []  # Active floating damage numbers
        self.spell_effects = []  # Active spell visual effects

        # Boss music tracking
        self.in_boss_area = False
        self.boss_chasing = False  # Track if any boss is actively chasing player

        # Music rotation tracking
        self.combat_music_index = 0
        self.town_music_index = 0

        # Active shop reference
        self.active_shop = None

        # Save/Load/Delete dialog state
        self.save_slots_cache = [None] * MAX_SAVE_SLOTS
        self.dialog_cursor = 0
        self.save_name_input = ""
        self.save_name_editing = False
        self.delete_confirm = False
        # Which state to return to after closing a save/load/delete dialog.
        # Options dialogs return to STATE_OPTIONS; pause dialogs return to STATE_PAUSED.
        self.dialog_return_state = self.STATE_OPTIONS
        ensure_saves_dir()

        # Autosave tracking (written on exit-to-menu, loaded via Resume)
        self.has_autosave = has_autosave()

        # Track last visited town stage number (for Portal spell / Arcane Resurrection)
        self.last_town_num = 0

        # Controller support
        self.joystick = None
        self.controller_connected = False
        self._init_controller()

        # Play menu music
        self.audio.play_music("menu")

    def _create_fonts(self):
        """Create all fonts scaled to the current resolution."""
        s = settings.scaled_font_size
        self.font = pygame.font.Font(None, s(28))
        self.big_font = pygame.font.Font(None, s(48))
        self.small_font = pygame.font.Font(None, s(20))
        self.title_font = pygame.font.Font(None, s(64))

    def _init_controller(self):
        """Initialize joystick subsystem and detect Xbox controllers."""
        pygame.joystick.init()
        if pygame.joystick.get_count() > 0:
            self.joystick = pygame.joystick.Joystick(0)
            self.joystick.init()
            self.controller_connected = True
        else:
            self.joystick = None
            self.controller_connected = False

    def _check_controller(self):
        """Re-check for controller connection (hot-plug support)."""
        count = pygame.joystick.get_count()
        if count > 0 and not self.controller_connected:
            self.joystick = pygame.joystick.Joystick(0)
            self.joystick.init()
            self.controller_connected = True
        elif count == 0 and self.controller_connected:
            self.joystick = None
            self.controller_connected = False

    def _get_controller_move(self) -> tuple:
        """Return (dx_norm, dy_norm) from controller left stick and d-pad.
        Values are -1.0 to 1.0 per axis, with deadzone applied."""
        if not self.joystick:
            return (0.0, 0.0)
        dx, dy = 0.0, 0.0

        # Left analog stick
        try:
            ax = self.joystick.get_axis(CONTROLLER_AXIS_LX)
            ay = self.joystick.get_axis(CONTROLLER_AXIS_LY)
            if abs(ax) > CONTROLLER_DEADZONE:
                dx = ax
            if abs(ay) > CONTROLLER_DEADZONE:
                dy = ay
        except Exception:
            pass

        # D-pad (hat 0) overrides stick if pressed
        try:
            if self.joystick.get_numhats() > 0:
                hx, hy = self.joystick.get_hat(0)
                if hx != 0:
                    dx = float(hx)
                if hy != 0:
                    dy = float(-hy)  # Hat Y is inverted (up=1)
        except Exception:
            pass

        return (dx, dy)

    def _controller_button(self, button: int) -> bool:
        """Check if a controller button is currently pressed."""
        if not self.joystick:
            return False
        try:
            return self.joystick.get_button(button)
        except Exception:
            return False

    def _next_combat_track(self) -> str:
        """Return the next combat music track from the rotation."""
        track = COMBAT_MUSIC_ROTATION[self.combat_music_index % len(COMBAT_MUSIC_ROTATION)]
        self.combat_music_index += 1
        return track

    def _next_town_track(self) -> str:
        """Return the next town music track from the rotation."""
        track = TOWN_MUSIC_ROTATION[self.town_music_index % len(TOWN_MUSIC_ROTATION)]
        self.town_music_index += 1
        return track

    def _on_music_ended(self):
        """Called when a music track finishes. Auto-continues to the next track."""
        # Don't auto-continue in menu, game over, or win states (they manage their own music)
        if self.state in (self.STATE_MENU, self.STATE_GAME_OVER, self.STATE_WIN):
            return
        # If in boss area or boss is chasing, replay boss music only if boss is still alive
        if self.in_boss_area or self.boss_chasing:
            if not self.stage.boss_defeated:
                self.audio.play_music(BOSS_MUSIC, loops=0)
            else:
                track = self._next_combat_track()
                self.audio.play_music(track, loops=0)
                return
        elif self.current_stage_type == "combat":
            track = self._next_combat_track()
            self.audio.play_music(track, loops=0)
        else:
            track = self._next_town_track()
            self.audio.play_music(track, loops=0)

    def _load_hero_previews(self):
        """Load hero idle sprites for the character selection screen."""
        self.hero_previews = []
        preview_scale = SCALE_FACTOR + 2  # Larger for menu display
        for hero in HERO_CHARACTERS:
            frame_dir = os.path.join(CHARS_FRAMES_PATH, "chara", hero["sprite_dir"])
            stand_path = os.path.join(frame_dir, "down_stand.png")
            try:
                img = _load_and_scale(stand_path, preview_scale)
                self.hero_previews.append((img, hero["name"]))
            except Exception:
                # Placeholder
                size = 17 * preview_scale
                placeholder = pygame.Surface((size, int(size * 1.7)), pygame.SRCALPHA)
                pygame.draw.rect(placeholder, (100, 100, 200),
                                 (4, 4, size - 8, int(size * 1.7) - 8))
                self.hero_previews.append((placeholder, hero["name"]))

    def _load_item_icons(self):
        """Load/create item icons for inventory display."""
        icon_size = 40
        # Without individual object PNGs, create colored placeholder icons
        icon_defs = {
            "potion_red": (220, 40, 40),
            "potion_blue": (40, 80, 220),
            "potion_green": (40, 180, 40),
            "mushroom": (180, 140, 100),
            "mushroom2": (160, 120, 80),
            "berries": (200, 50, 100),
        }

        for key, color in icon_defs.items():
            img = pygame.Surface((icon_size, icon_size), pygame.SRCALPHA)
            if "potion" in key:
                # Potion shape
                pygame.draw.rect(img, color, (12, 8, 16, 24), border_radius=4)
                pygame.draw.rect(img, (200, 200, 200), (14, 4, 12, 8))
            elif "mushroom" in key:
                pygame.draw.ellipse(img, color, (6, 4, 28, 18))
                pygame.draw.rect(img, (160, 140, 120), (16, 18, 8, 18))
            elif "berries" in key:
                for ox, oy in [(12, 12), (20, 16), (16, 22), (24, 10)]:
                    pygame.draw.circle(img, color, (ox, oy), 6)
            else:
                pygame.draw.rect(img, color, (4, 4, icon_size - 8, icon_size - 8))
            self.item_icons[key] = img

        # --- Distinct weapon icons per style ---
        # Sword icon: blade + guard + handle (gray steel)
        img = pygame.Surface((icon_size, icon_size), pygame.SRCALPHA)
        pygame.draw.rect(img, (190, 200, 220), (18, 4, 4, 22))  # blade
        pygame.draw.polygon(img, (190, 200, 220), [(18, 4), (20, 1), (22, 4)])  # tip
        pygame.draw.line(img, (230, 235, 245), (20, 6), (20, 22), 1)  # highlight
        pygame.draw.rect(img, (160, 140, 60), (12, 25, 16, 3))  # guard
        pygame.draw.rect(img, (100, 70, 40), (18, 28, 4, 8))  # handle
        self.item_icons["weapon_sword"] = img

        # Axe icon: handle + wide axe head
        img = pygame.Surface((icon_size, icon_size), pygame.SRCALPHA)
        pygame.draw.rect(img, (100, 70, 40), (19, 12, 3, 24))  # handle
        pygame.draw.polygon(img, (140, 150, 170), [  # axe head
            (20, 6), (32, 2), (32, 18), (20, 14)])
        pygame.draw.line(img, (200, 210, 220), (31, 3), (31, 17), 1)  # edge
        self.item_icons["weapon_axe"] = img

        # Staff icon: pole + glowing orb
        img = pygame.Surface((icon_size, icon_size), pygame.SRCALPHA)
        pygame.draw.rect(img, (110, 80, 50), (19, 12, 3, 26))  # pole
        pygame.draw.circle(img, (160, 80, 220), (20, 9), 7)  # orb
        pygame.draw.circle(img, (200, 140, 255), (19, 7), 3)  # orb highlight
        self.item_icons["weapon_staff"] = img

        # Legendary blade icon: golden guard + bright blade + glow aura
        img = pygame.Surface((icon_size, icon_size), pygame.SRCALPHA)
        # Glow aura
        glow = pygame.Surface((icon_size, icon_size), pygame.SRCALPHA)
        pygame.draw.rect(glow, (255, 240, 150, 50), (14, 2, 12, 26))
        img.blit(glow, (0, 0))
        pygame.draw.rect(img, (255, 240, 180), (18, 3, 5, 21))  # blade
        pygame.draw.polygon(img, (255, 240, 180), [(18, 3), (20, 0), (23, 3)])  # tip
        pygame.draw.line(img, (255, 255, 255), (20, 5), (20, 20), 1)  # highlight
        pygame.draw.rect(img, (220, 180, 40), (12, 24, 16, 3))  # golden guard
        pygame.draw.rect(img, (80, 60, 30), (18, 27, 4, 8))  # handle
        self.item_icons["weapon_legendary"] = img

        # Bow icon: curved arc + string + arrow
        img = pygame.Surface((icon_size, icon_size), pygame.SRCALPHA)
        # Bow arc
        pygame.draw.arc(img, (140, 100, 60), (8, 4, 18, 32), -1.2, 1.2, 2)
        # String
        pygame.draw.line(img, (200, 200, 200), (17, 6), (17, 34), 1)
        # Arrow
        pygame.draw.line(img, (180, 160, 120), (18, 20), (32, 20), 2)
        pygame.draw.polygon(img, (200, 200, 220), [(32, 20), (28, 17), (28, 23)])
        self.item_icons["weapon_bow"] = img

        # Gun icon: barrel + body + handle
        img = pygame.Surface((icon_size, icon_size), pygame.SRCALPHA)
        # Barrel
        pygame.draw.rect(img, (80, 80, 90), (4, 16, 24, 5))
        # Barrel tip
        pygame.draw.rect(img, (120, 120, 130), (2, 17, 4, 3))
        # Body
        pygame.draw.rect(img, (80, 80, 90), (22, 14, 10, 9))
        # Handle
        pygame.draw.polygon(img, (100, 70, 40), [
            (26, 23), (32, 23), (30, 34), (24, 34)])
        # Trigger guard
        pygame.draw.arc(img, (80, 80, 90), (22, 22, 10, 10), -1.5, 1.5, 1)
        self.item_icons["weapon_gun"] = img

        # Default sellable icon
        img = pygame.Surface((icon_size, icon_size), pygame.SRCALPHA)
        pygame.draw.rect(img, (200, 180, 100), (4, 4, icon_size - 8, icon_size - 8))
        pygame.draw.rect(img, (160, 140, 60), (4, 4, icon_size - 8, icon_size - 8), 2)
        self.item_icons["sellable"] = img

        # --- Armor icons (shield shapes) ---
        # Leather armor: brown shield
        img = pygame.Surface((icon_size, icon_size), pygame.SRCALPHA)
        pygame.draw.polygon(img, (139, 90, 43), [
            (20, 4), (6, 10), (6, 22), (20, 36), (34, 22), (34, 10)])
        pygame.draw.polygon(img, (110, 70, 30), [
            (20, 4), (6, 10), (6, 22), (20, 36), (34, 22), (34, 10)], 2)
        pygame.draw.line(img, (160, 110, 60), (20, 8), (20, 32), 1)
        self.item_icons["armor_leather"] = img

        # Padded armor: tan shield with quilting lines
        img = pygame.Surface((icon_size, icon_size), pygame.SRCALPHA)
        pygame.draw.polygon(img, (210, 190, 140), [
            (20, 4), (6, 10), (6, 22), (20, 36), (34, 22), (34, 10)])
        pygame.draw.polygon(img, (170, 150, 100), [
            (20, 4), (6, 10), (6, 22), (20, 36), (34, 22), (34, 10)], 2)
        for qy in [14, 20, 26]:
            pygame.draw.line(img, (180, 160, 110), (10, qy), (30, qy), 1)
        self.item_icons["armor_padded"] = img

        # Chain armor: silver shield with ring pattern
        img = pygame.Surface((icon_size, icon_size), pygame.SRCALPHA)
        pygame.draw.polygon(img, (160, 165, 175), [
            (20, 4), (6, 10), (6, 22), (20, 36), (34, 22), (34, 10)])
        pygame.draw.polygon(img, (120, 125, 135), [
            (20, 4), (6, 10), (6, 22), (20, 36), (34, 22), (34, 10)], 2)
        for rx, ry in [(14, 13), (20, 13), (26, 13), (11, 19), (17, 19),
                       (23, 19), (29, 19), (14, 25), (20, 25), (26, 25)]:
            pygame.draw.circle(img, (190, 195, 205), (rx, ry), 3, 1)
        self.item_icons["armor_chain"] = img

        # Plate armor: steel shield with gold cross
        img = pygame.Surface((icon_size, icon_size), pygame.SRCALPHA)
        pygame.draw.polygon(img, (180, 185, 200), [
            (20, 4), (6, 10), (6, 22), (20, 36), (34, 22), (34, 10)])
        pygame.draw.polygon(img, (140, 145, 160), [
            (20, 4), (6, 10), (6, 22), (20, 36), (34, 22), (34, 10)], 2)
        pygame.draw.line(img, (220, 180, 40), (20, 10), (20, 30), 2)
        pygame.draw.line(img, (220, 180, 40), (12, 18), (28, 18), 2)
        # Highlight
        pygame.draw.line(img, (220, 225, 240), (10, 11), (18, 7), 1)
        self.item_icons["armor_plate"] = img

    def new_game(self):
        """Start a new game with the selected hero character."""
        self.current_stage_num = 1
        self.current_stage_type = "combat"
        self.ground_items = pygame.sprite.Group()
        self.gold_drops = pygame.sprite.Group()
        self.projectiles = []
        self.floating_texts = []
        self.spell_effects = []
        self.in_boss_area = False
        self.active_shop = None

        self._load_stage()

        # Create player with selected hero
        sx, sy = self.stage.player_start
        selected_hero = HERO_CHARACTERS[self.selected_hero_index]
        self.player = Player(sx, sy, selected_hero)

        # Give player a couple starting potions
        potion = self.item_db.get("potion_red")
        if potion:
            self.player.inventory.add_item(potion, 3)

        self.camera = Camera(self.stage.width, self.stage.height)
        self.state = self.STATE_PLAYING

        # Play stage music (rotation, no loop)
        self.combat_music_index = 0
        self.town_music_index = 0
        music = self._next_combat_track()
        self.audio.play_music(music, loops=0)

    def _load_stage(self):
        """Generate and load the current stage."""
        self.stage = generate_stage(self.current_stage_num,
                                    self.current_stage_type,
                                    self.item_db)
        self.ground_items = pygame.sprite.Group()
        self.gold_drops = pygame.sprite.Group()
        self.projectiles = []
        self.floating_texts = []
        self.spell_effects = []
        self.in_boss_area = False

    def advance_stage(self):
        """Move to the next stage."""
        if self.current_stage_type == "combat":
            if self.current_stage_num >= self.total_combat_stages:
                self.state = self.STATE_WIN
                self.audio.play_music("emotional", loops=0)
                return
            # Go to town
            self.current_stage_type = "town"
            self.last_town_num = self.current_stage_num  # track last visited town
        else:
            # Go to next combat stage
            self.current_stage_num += 1
            self.current_stage_type = "combat"

        self._load_stage()
        sx, sy = self.stage.player_start
        self.player.world_x = sx
        self.player.world_y = sy
        self.player.is_alive = True

        self.camera = Camera(self.stage.width, self.stage.height)

        # Play appropriate music (rotation, no loop)
        if self.current_stage_type == "combat":
            music = self._next_combat_track()
            self.audio.play_music(music, loops=0)
        else:
            music = self._next_town_track()
            self.audio.play_music(music, loops=0)

        self.hud.show_message(
            f"Stage {self.current_stage_num} - "
            f"{'Town' if self.current_stage_type == 'town' else 'Combat'}")

    def run(self):
        """Main game loop."""
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            dt = min(dt, 0.05)  # Cap delta time

            self.handle_events()
            self.update(dt)
            self.draw()

        pygame.quit()

    def handle_events(self):
        """Process all pygame events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return

            if event.type == self.audio.MUSIC_END_EVENT:
                self._on_music_ended()

            # Controller hot-plug detection
            if event.type in (pygame.JOYDEVICEADDED, pygame.JOYDEVICEREMOVED):
                self._check_controller()

            if event.type == pygame.KEYDOWN:
                self._handle_keydown(event)

            if event.type == pygame.JOYBUTTONDOWN:
                self._handle_controller_button(event)

            if event.type == pygame.JOYHATMOTION:
                self._handle_controller_hat(event)

            if event.type == pygame.TEXTINPUT:
                if (self.state == self.STATE_SAVE_DIALOG
                        and self.save_name_editing):
                    if len(self.save_name_input) < MAX_SAVE_NAME_LENGTH:
                        if event.text.isprintable():
                            self.save_name_input += event.text

            if event.type == pygame.MOUSEWHEEL:
                if self.state == self.STATE_HELP:
                    self.help_scroll_y = max(0, self.help_scroll_y - event.y * 40)

            if event.type == pygame.MOUSEBUTTONDOWN:
                self._handle_mouse_click(event)

    def _handle_keydown(self, event):
        if self.state == self.STATE_MENU:
            if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                self.new_game()
            elif event.key == pygame.K_LEFT:
                self.selected_hero_index = (self.selected_hero_index - 1) % len(HERO_CHARACTERS)
                self.audio.play_sfx("menu_move")
            elif event.key == pygame.K_RIGHT:
                self.selected_hero_index = (self.selected_hero_index + 1) % len(HERO_CHARACTERS)
                self.audio.play_sfx("menu_move")
            elif event.key == pygame.K_h:
                self.help_scroll_y = 0
                self.state = self.STATE_HELP
                self.audio.play_sfx("menu_accept")
            elif event.key == pygame.K_ESCAPE:
                self.running = False

        elif self.state == self.STATE_HELP:
            if event.key == pygame.K_ESCAPE or event.key == pygame.K_h:
                self.state = self.STATE_MENU
                self.audio.play_sfx("menu_cancel")
            elif event.key == pygame.K_UP:
                self.help_scroll_y = max(0, self.help_scroll_y - 40)
            elif event.key == pygame.K_DOWN:
                self.help_scroll_y += 40

        elif self.state == self.STATE_OPTIONS:
            rows = self._options_rows()
            num_rows = len(rows)
            if event.key == pygame.K_ESCAPE:
                self.state = self.STATE_MENU
                self.audio.play_sfx("menu_cancel")
            elif event.key == pygame.K_UP:
                self.pause_slider_sel = (self.pause_slider_sel - 1) % num_rows
                self.audio.play_sfx("menu_move")
            elif event.key == pygame.K_DOWN:
                self.pause_slider_sel = (self.pause_slider_sel + 1) % num_rows
                self.audio.play_sfx("menu_move")
            elif event.key == pygame.K_RETURN:
                self._activate_options_row(rows)
            elif event.key == pygame.K_LEFT:
                cur_row = rows[self.pause_slider_sel] if self.pause_slider_sel < num_rows else ""
                if cur_row == "music":
                    self.audio.set_music_volume(self.audio.music_volume - 0.1)
                elif cur_row == "sfx":
                    self.audio.set_sfx_volume(self.audio.sfx_volume - 0.1)
                    self.audio.play_sfx("menu_move")
                elif cur_row == "resolution":
                    new_idx = max(0, self.resolution_index - 1)
                    if new_idx != self.resolution_index:
                        self._change_resolution(new_idx)
                        self.audio.play_sfx("menu_move")
            elif event.key == pygame.K_RIGHT:
                cur_row = rows[self.pause_slider_sel] if self.pause_slider_sel < num_rows else ""
                if cur_row == "music":
                    self.audio.set_music_volume(self.audio.music_volume + 0.1)
                elif cur_row == "sfx":
                    self.audio.set_sfx_volume(self.audio.sfx_volume + 0.1)
                    self.audio.play_sfx("menu_move")
                elif cur_row == "resolution":
                    new_idx = min(len(AVAILABLE_RESOLUTIONS) - 1,
                                  self.resolution_index + 1)
                    if new_idx != self.resolution_index:
                        self._change_resolution(new_idx)
                        self.audio.play_sfx("menu_move")

        elif self.state == self.STATE_SAVE_DIALOG:
            if self.save_name_editing:
                if event.key == pygame.K_RETURN:
                    self._execute_save()
                elif event.key == pygame.K_ESCAPE:
                    self.save_name_editing = False
                    self.audio.play_sfx("menu_cancel")
                elif event.key == pygame.K_BACKSPACE:
                    self.save_name_input = self.save_name_input[:-1]
            else:
                if event.key == pygame.K_UP:
                    self.dialog_cursor = (self.dialog_cursor - 1) % MAX_SAVE_SLOTS
                    self.audio.play_sfx("menu_move")
                elif event.key == pygame.K_DOWN:
                    self.dialog_cursor = (self.dialog_cursor + 1) % MAX_SAVE_SLOTS
                    self.audio.play_sfx("menu_move")
                elif event.key == pygame.K_RETURN:
                    self._start_save_name_input()
                elif event.key == pygame.K_ESCAPE:
                    self.state = self.dialog_return_state
                    self.audio.play_sfx("menu_cancel")

        elif self.state == self.STATE_LOAD_DIALOG:
            if event.key == pygame.K_UP:
                self._dialog_cursor_prev_occupied()
            elif event.key == pygame.K_DOWN:
                self._dialog_cursor_next_occupied()
            elif event.key == pygame.K_RETURN:
                self._execute_load()
            elif event.key == pygame.K_ESCAPE:
                self.state = self.dialog_return_state
                self.audio.play_sfx("menu_cancel")

        elif self.state == self.STATE_DELETE_DIALOG:
            if self.delete_confirm:
                if event.key == pygame.K_RETURN:
                    self._execute_delete()
                elif event.key == pygame.K_ESCAPE:
                    self.delete_confirm = False
                    self.audio.play_sfx("menu_cancel")
            else:
                if event.key == pygame.K_UP:
                    self._dialog_cursor_prev_occupied()
                elif event.key == pygame.K_DOWN:
                    self._dialog_cursor_next_occupied()
                elif event.key == pygame.K_RETURN:
                    if self.save_slots_cache[self.dialog_cursor]:
                        self.delete_confirm = True
                        self.audio.play_sfx("menu_move")
                elif event.key == pygame.K_ESCAPE:
                    self.state = self.dialog_return_state
                    self.audio.play_sfx("menu_cancel")

        elif self.state == self.STATE_PLAYING:
            if event.key == KEY_INVENTORY or event.key == KEY_INVENTORY_ALT:
                self.player.inventory.toggle()
                if self.player.inventory.is_open:
                    self.state = self.STATE_INVENTORY
            elif event.key == KEY_ESCAPE:
                self.state = self.STATE_PAUSED
            elif event.key == KEY_PICKUP:
                self._try_pickup()
            elif event.key == KEY_ATTACK:
                self._do_attack()
            elif event.key == pygame.K_m:
                self.hud.toggle_minimap()
            elif event.key == pygame.K_f:
                self.hud.toggle_fps()
            elif event.key == KEY_SPELL:
                self._activate_selected_ability()
            elif pygame.K_1 <= event.key <= pygame.K_9:
                # Number keys 1-9 select spell/ability slot
                idx = event.key - pygame.K_0
                self.player.select_ability_by_number(idx)
                self.audio.play_sfx("menu_move")

        elif self.state == self.STATE_INVENTORY:
            if (event.key == KEY_INVENTORY or event.key == KEY_INVENTORY_ALT
                    or event.key == KEY_ESCAPE):
                # Drop held item on ground if couldn't fit back
                held = self.player.inventory.held_item
                self.player.inventory.close()
                if self.player.inventory.held_item:
                    self._drop_held_item(self.player.inventory.held_item)
                    self.player.inventory.held_item = None
                self.state = self.STATE_PLAYING

        elif self.state == self.STATE_SHOP:
            if event.key == KEY_ESCAPE:
                if self.active_shop:
                    self.active_shop.close()
                self.active_shop = None
                self.state = self.STATE_PLAYING

        elif self.state == self.STATE_PAUSED:
            # Pause rows: 0=music, 1=sfx, 2=save, 3=load, 4=return to menu
            _PAUSE_ROWS = 5
            if event.key == KEY_ESCAPE:
                self.state = self.STATE_PLAYING
            elif event.key == pygame.K_UP:
                self.pause_slider_sel = (self.pause_slider_sel - 1) % _PAUSE_ROWS
                self.audio.play_sfx("menu_move")
            elif event.key == pygame.K_DOWN:
                self.pause_slider_sel = (self.pause_slider_sel + 1) % _PAUSE_ROWS
                self.audio.play_sfx("menu_move")
            elif event.key == pygame.K_LEFT:
                if self.pause_slider_sel == 0:
                    self.audio.set_music_volume(self.audio.music_volume - 0.1)
                elif self.pause_slider_sel == 1:
                    self.audio.set_sfx_volume(self.audio.sfx_volume - 0.1)
                    self.audio.play_sfx("menu_move")
            elif event.key == pygame.K_RIGHT:
                if self.pause_slider_sel == 0:
                    self.audio.set_music_volume(self.audio.music_volume + 0.1)
                elif self.pause_slider_sel == 1:
                    self.audio.set_sfx_volume(self.audio.sfx_volume + 0.1)
                    self.audio.play_sfx("menu_move")
            elif event.key == pygame.K_RETURN:
                self._activate_pause_row()

        elif self.state in (self.STATE_GAME_OVER, self.STATE_WIN):
            if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                self.menu_button_sel = -1
                self.state = self.STATE_MENU
                self.audio.play_music("menu")

    def _handle_controller_button(self, event):
        """Handle controller button press events."""
        btn = event.button

        if self.state == self.STATE_MENU:
            if btn == CONTROLLER_BUTTON_START:
                self.new_game()
            elif btn == CONTROLLER_BUTTON_ATTACK:
                # A button — confirm selected button or start game
                if self.menu_button_sel == 3 and self.has_autosave:
                    self._load_from_autosave()
                elif self.menu_button_sel == 0 or self.menu_button_sel == -1:
                    self.new_game()
                elif self.menu_button_sel == 1:
                    self.help_scroll_y = 0
                    self.state = self.STATE_HELP
                    self.audio.play_sfx("menu_accept")
                elif self.menu_button_sel == 2:
                    self.pause_slider_sel = 0
                    self.state = self.STATE_OPTIONS
                    self.audio.play_sfx("menu_accept")
                elif self.menu_button_sel == 4:
                    self.audio.play_sfx("menu_cancel")
                    self.running = False
            elif btn == CONTROLLER_BUTTON_LB:
                self.selected_hero_index = (self.selected_hero_index - 1) % len(HERO_CHARACTERS)
                self.audio.play_sfx("menu_move")
            elif btn == CONTROLLER_BUTTON_RB:
                self.selected_hero_index = (self.selected_hero_index + 1) % len(HERO_CHARACTERS)
                self.audio.play_sfx("menu_move")
            elif btn == CONTROLLER_BUTTON_BACK:
                self.help_scroll_y = 0
                self.state = self.STATE_HELP
                self.audio.play_sfx("menu_accept")
            elif btn == CONTROLLER_BUTTON_INVENTORY:
                self.pause_slider_sel = 0
                self.state = self.STATE_OPTIONS
                self.audio.play_sfx("menu_accept")

        elif self.state == self.STATE_HELP:
            if btn in (CONTROLLER_BUTTON_BACK, CONTROLLER_BUTTON_PICKUP):
                self.state = self.STATE_MENU
                self.audio.play_sfx("menu_cancel")

        elif self.state == self.STATE_OPTIONS:
            if btn in (CONTROLLER_BUTTON_BACK, CONTROLLER_BUTTON_PICKUP):
                self.state = self.STATE_MENU
                self.audio.play_sfx("menu_cancel")
            elif btn == CONTROLLER_BUTTON_ATTACK:
                self._activate_options_row(self._options_rows())

        elif self.state == self.STATE_SAVE_DIALOG:
            if btn == CONTROLLER_BUTTON_ATTACK:
                if not self.save_name_editing:
                    # Auto-name for controller users
                    slot = self.dialog_cursor
                    existing = self.save_slots_cache[slot]
                    self.save_name_input = existing["name"] if existing else f"Save {slot + 1}"
                    self._execute_save()
            elif btn in (CONTROLLER_BUTTON_PICKUP, CONTROLLER_BUTTON_BACK):
                if self.save_name_editing:
                    self.save_name_editing = False
                else:
                    self.state = self.dialog_return_state
                self.audio.play_sfx("menu_cancel")

        elif self.state == self.STATE_LOAD_DIALOG:
            if btn == CONTROLLER_BUTTON_ATTACK:
                self._execute_load()
            elif btn in (CONTROLLER_BUTTON_PICKUP, CONTROLLER_BUTTON_BACK):
                self.state = self.dialog_return_state
                self.audio.play_sfx("menu_cancel")

        elif self.state == self.STATE_DELETE_DIALOG:
            if btn == CONTROLLER_BUTTON_ATTACK:
                if self.delete_confirm:
                    self._execute_delete()
                elif self.save_slots_cache[self.dialog_cursor]:
                    self.delete_confirm = True
                    self.audio.play_sfx("menu_move")
            elif btn in (CONTROLLER_BUTTON_PICKUP, CONTROLLER_BUTTON_BACK):
                if self.delete_confirm:
                    self.delete_confirm = False
                else:
                    self.state = self.dialog_return_state
                self.audio.play_sfx("menu_cancel")

        elif self.state == self.STATE_PLAYING:
            if btn == CONTROLLER_BUTTON_ATTACK:
                self._do_attack()
            elif btn == CONTROLLER_BUTTON_PICKUP:
                self._try_pickup()
            elif btn == CONTROLLER_BUTTON_INVENTORY:
                self.player.inventory.toggle()
                if self.player.inventory.is_open:
                    self.player.inventory.gamepad_cursor = 0
                    self.state = self.STATE_INVENTORY
            elif btn == CONTROLLER_BUTTON_MINIMAP:
                self.hud.toggle_minimap()
            elif btn == CONTROLLER_BUTTON_RB:
                self._activate_selected_ability()
            elif btn == CONTROLLER_BUTTON_START:
                self.state = self.STATE_PAUSED

        elif self.state == self.STATE_INVENTORY:
            if btn in (CONTROLLER_BUTTON_INVENTORY, CONTROLLER_BUTTON_PICKUP,
                       CONTROLLER_BUTTON_BACK, CONTROLLER_BUTTON_START):
                self.player.inventory.gamepad_cursor = -1
                held = self.player.inventory.held_item
                self.player.inventory.close()
                if self.player.inventory.held_item:
                    self._drop_held_item(self.player.inventory.held_item)
                    self.player.inventory.held_item = None
                self.state = self.STATE_PLAYING
            elif btn == CONTROLLER_BUTTON_ATTACK:
                # A button: use/wield item at gamepad cursor
                cursor = self.player.inventory.gamepad_cursor
                if 0 <= cursor < 25:
                    stack = self.player.inventory.get_slot(cursor)
                    if stack:
                        self._use_item(cursor)
            elif btn == CONTROLLER_BUTTON_MINIMAP:
                # Y button: drop item at gamepad cursor
                cursor = self.player.inventory.gamepad_cursor
                if 0 <= cursor < 25:
                    stack = self.player.inventory.get_slot(cursor)
                    if stack:
                        self._drop_item(cursor)

        elif self.state == self.STATE_SHOP:
            if btn in (CONTROLLER_BUTTON_BACK, CONTROLLER_BUTTON_START,
                       CONTROLLER_BUTTON_PICKUP):
                if self.active_shop:
                    self.active_shop.close()
                self.active_shop = None
                self.state = self.STATE_PLAYING
            elif btn == CONTROLLER_BUTTON_ATTACK and self.active_shop:
                # A button: buy or sell at cursor
                self.active_shop.gamepad_confirm(self.player, self.audio)
            elif btn == CONTROLLER_BUTTON_LB and self.active_shop:
                self.active_shop.gamepad_switch_panel(-1)
                self.audio.play_sfx("menu_move")
            elif btn == CONTROLLER_BUTTON_RB and self.active_shop:
                self.active_shop.gamepad_switch_panel(1)
                self.audio.play_sfx("menu_move")

        elif self.state == self.STATE_PAUSED:
            if btn == CONTROLLER_BUTTON_START:
                self.state = self.STATE_PLAYING
            elif btn == CONTROLLER_BUTTON_ATTACK:
                # A button confirms the selected pause row
                self._activate_pause_row()
            elif btn == CONTROLLER_BUTTON_BACK:
                # Back always resumes (quick escape)
                self.state = self.STATE_PLAYING

        elif self.state in (self.STATE_GAME_OVER, self.STATE_WIN):
            if btn in (CONTROLLER_BUTTON_START, CONTROLLER_BUTTON_ATTACK):
                self.menu_button_sel = -1
                self.state = self.STATE_MENU
                self.audio.play_music("menu")

    def _handle_controller_hat(self, event):
        """Handle D-pad (hat) events for menu/options/pause navigation."""
        if not event.value:
            return
        hx, hy = event.value

        if self.state == self.STATE_PLAYING:
            # D-pad L/R cycles spell/ability selection during gameplay
            if hx != 0:
                self.player.cycle_ability(hx)
                self.audio.play_sfx("menu_move")
            return  # D-pad up/down during gameplay not used here

        if self.state == self.STATE_MENU:
            if self.menu_button_sel == -1:
                # On hero row — LEFT/RIGHT selects hero, DOWN goes to buttons
                if hx < 0:
                    self.selected_hero_index = (self.selected_hero_index - 1) % len(HERO_CHARACTERS)
                    self.audio.play_sfx("menu_move")
                elif hx > 0:
                    self.selected_hero_index = (self.selected_hero_index + 1) % len(HERO_CHARACTERS)
                    self.audio.play_sfx("menu_move")
                elif hy < 0:  # D-pad down
                    # Go to Resume first (sel=3) if autosave exists, else Start (sel=0)
                    self.menu_button_sel = 3 if self.has_autosave else 0
                    self.audio.play_sfx("menu_move")
            elif self.menu_button_sel == 3:
                # On Resume button row (only reachable when has_autosave)
                if hy > 0:  # D-pad up → back to hero row
                    self.menu_button_sel = -1
                    self.audio.play_sfx("menu_move")
                elif hy < 0:  # D-pad down → Start button
                    self.menu_button_sel = 0
                    self.audio.play_sfx("menu_move")
            elif self.menu_button_sel == 4:
                # On Exit Game button row
                if hy > 0:  # D-pad up → Help/Options row
                    self.menu_button_sel = 1
                    self.audio.play_sfx("menu_move")
                elif hy < 0:  # D-pad down → wrap back to hero row
                    self.menu_button_sel = -1
                    self.audio.play_sfx("menu_move")
            else:
                # On Start(0)/Help(1)/Options(2) button row
                if hy > 0:  # D-pad up
                    if self.menu_button_sel == 0:
                        # Go to Resume (sel=3) if exists, else hero row
                        self.menu_button_sel = 3 if self.has_autosave else -1
                    else:
                        self.menu_button_sel = 0  # Help/Options → Start
                    self.audio.play_sfx("menu_move")
                elif hy < 0:  # D-pad down
                    if self.menu_button_sel == 0:
                        self.menu_button_sel = 1  # Start → Help
                    elif self.menu_button_sel in (1, 2):
                        self.menu_button_sel = 4  # Help/Options → Exit
                    self.audio.play_sfx("menu_move")
                elif hx < 0:  # D-pad left
                    if self.menu_button_sel == 2:
                        self.menu_button_sel = 1  # Options → Help
                        self.audio.play_sfx("menu_move")
                elif hx > 0:  # D-pad right
                    if self.menu_button_sel == 1:
                        self.menu_button_sel = 2  # Help → Options
                        self.audio.play_sfx("menu_move")

        elif self.state == self.STATE_HELP:
            if hy > 0:  # D-pad up
                self.help_scroll_y = max(0, self.help_scroll_y - 40)
            elif hy < 0:  # D-pad down
                self.help_scroll_y += 40

        elif self.state == self.STATE_OPTIONS:
            rows = self._options_rows()
            num_rows = len(rows)
            if hy > 0:  # D-pad up
                self.pause_slider_sel = (self.pause_slider_sel - 1) % num_rows
                self.audio.play_sfx("menu_move")
            elif hy < 0:  # D-pad down
                self.pause_slider_sel = (self.pause_slider_sel + 1) % num_rows
                self.audio.play_sfx("menu_move")
            elif hx < 0:  # D-pad left
                cur_row = rows[self.pause_slider_sel] if self.pause_slider_sel < num_rows else ""
                if cur_row == "music":
                    self.audio.set_music_volume(self.audio.music_volume - 0.1)
                elif cur_row == "sfx":
                    self.audio.set_sfx_volume(self.audio.sfx_volume - 0.1)
                    self.audio.play_sfx("menu_move")
                elif cur_row == "resolution":
                    new_idx = max(0, self.resolution_index - 1)
                    if new_idx != self.resolution_index:
                        self._change_resolution(new_idx)
                        self.audio.play_sfx("menu_move")
            elif hx > 0:  # D-pad right
                cur_row = rows[self.pause_slider_sel] if self.pause_slider_sel < num_rows else ""
                if cur_row == "music":
                    self.audio.set_music_volume(self.audio.music_volume + 0.1)
                elif cur_row == "sfx":
                    self.audio.set_sfx_volume(self.audio.sfx_volume + 0.1)
                    self.audio.play_sfx("menu_move")
                elif cur_row == "resolution":
                    new_idx = min(len(AVAILABLE_RESOLUTIONS) - 1,
                                  self.resolution_index + 1)
                    if new_idx != self.resolution_index:
                        self._change_resolution(new_idx)
                        self.audio.play_sfx("menu_move")

        elif self.state in (self.STATE_SAVE_DIALOG, self.STATE_LOAD_DIALOG,
                            self.STATE_DELETE_DIALOG):
            if self.state == self.STATE_SAVE_DIALOG and self.save_name_editing:
                return  # No hat navigation during text input
            if hy > 0:  # D-pad up
                if self.state == self.STATE_SAVE_DIALOG:
                    self.dialog_cursor = (self.dialog_cursor - 1) % MAX_SAVE_SLOTS
                else:
                    self._dialog_cursor_prev_occupied()
                self.audio.play_sfx("menu_move")
            elif hy < 0:  # D-pad down
                if self.state == self.STATE_SAVE_DIALOG:
                    self.dialog_cursor = (self.dialog_cursor + 1) % MAX_SAVE_SLOTS
                else:
                    self._dialog_cursor_next_occupied()
                self.audio.play_sfx("menu_move")

        elif self.state == self.STATE_INVENTORY:
            # D-pad navigates the inventory grid
            dx = 1 if hx > 0 else (-1 if hx < 0 else 0)
            dy = -1 if hy > 0 else (1 if hy < 0 else 0)  # hat Y inverted
            if dx != 0 or dy != 0:
                self.player.inventory.gamepad_navigate(dx, dy)
                self.audio.play_sfx("menu_move")

        elif self.state == self.STATE_SHOP:
            if self.active_shop:
                dx = 1 if hx > 0 else (-1 if hx < 0 else 0)
                dy = -1 if hy > 0 else (1 if hy < 0 else 0)  # hat Y inverted
                if dx != 0 or dy != 0:
                    self.active_shop.gamepad_navigate(dx, dy)
                    self.audio.play_sfx("menu_move")

        elif self.state == self.STATE_PAUSED:
            # Pause rows: 0=music, 1=sfx, 2=save, 3=load, 4=return to menu
            _PAUSE_ROWS = 5
            if hy > 0:  # D-pad up
                self.pause_slider_sel = (self.pause_slider_sel - 1) % _PAUSE_ROWS
                self.audio.play_sfx("menu_move")
            elif hy < 0:  # D-pad down
                self.pause_slider_sel = (self.pause_slider_sel + 1) % _PAUSE_ROWS
                self.audio.play_sfx("menu_move")
            elif hx < 0:  # D-pad left — adjusts volume sliders only
                if self.pause_slider_sel == 0:
                    self.audio.set_music_volume(self.audio.music_volume - 0.1)
                elif self.pause_slider_sel == 1:
                    self.audio.set_sfx_volume(self.audio.sfx_volume - 0.1)
                    self.audio.play_sfx("menu_move")
            elif hx > 0:  # D-pad right — adjusts volume sliders only
                if self.pause_slider_sel == 0:
                    self.audio.set_music_volume(self.audio.music_volume + 0.1)
                elif self.pause_slider_sel == 1:
                    self.audio.set_sfx_volume(self.audio.sfx_volume + 0.1)
                    self.audio.play_sfx("menu_move")

    def _handle_mouse_click(self, event):
        if self.state == self.STATE_HELP:
            if event.button == 1:
                # Back button top-left (scaled)
                back_rect = self._help_back_rect()
                if back_rect.collidepoint(event.pos):
                    self.state = self.STATE_MENU
                    self.audio.play_sfx("menu_cancel")
            return

        if self.state == self.STATE_OPTIONS:
            if event.button == 1:
                mx, my = event.pos
                # Back button (scaled to fit text)
                scale = settings.get_font_scale()
                back_text_w = self.font.size("Back")[0]
                btn_w = max(100, back_text_w + int(32 * scale))
                btn_h = max(35, self.font.get_height() + int(16 * scale))
                back_rect = pygame.Rect(20, 20, btn_w, btn_h)
                if back_rect.collidepoint(mx, my):
                    self.state = self.STATE_MENU
                    self.audio.play_sfx("menu_cancel")
                    return
                # Volume sliders and button rows
                self._handle_options_slider_click(mx, my)
            return

        if self.state in (self.STATE_SAVE_DIALOG, self.STATE_LOAD_DIALOG,
                          self.STATE_DELETE_DIALOG):
            if event.button == 1:
                self._handle_dialog_click(event.pos)
            return

        if self.state == self.STATE_MENU:
            # Check if clicking on a hero preview
            self._handle_menu_click(event)

        elif self.state == self.STATE_PLAYING:
            if event.button == 1:  # Left click: attack
                self._do_attack()

        elif self.state == self.STATE_INVENTORY:
            slot = self.player.inventory.get_slot_at_pos(event.pos)
            if event.button == 1:  # Left click: pick up / place / swap / drop
                if self.player.inventory.held_item is None:
                    # Nothing held — pick up from clicked slot
                    if slot >= 0:
                        stack = self.player.inventory.get_slot(slot)
                        if stack:
                            self.player.inventory.pick_up_slot(slot)
                            self.audio.play_sfx("bonus")
                else:
                    # Holding an item
                    if slot >= 0:
                        # Place or swap into the target slot
                        self.player.inventory.place_held(slot)
                        self.audio.play_sfx("bonus")
                    else:
                        # Clicked outside grid — drop held item on ground
                        dropped = self.player.inventory.drop_held()
                        if dropped:
                            self._drop_held_item(dropped)
            elif event.button == 3:  # Right click: use/wield/eat
                if slot >= 0 and self.player.inventory.held_item is None:
                    stack = self.player.inventory.get_slot(slot)
                    if stack:
                        self._use_item(slot)

        elif self.state == self.STATE_PAUSED:
            if event.button == 1:
                self._handle_pause_click(event.pos)

        elif self.state == self.STATE_SHOP:
            if self.active_shop:
                self.active_shop.handle_click(event.pos, event.button,
                                              self.player, self.audio)

    def _handle_menu_click(self, event):
        """Handle mouse clicks on the character selection screen."""
        if event.button != 1:
            return
        mx, my = event.pos
        (sw, sh, cx, scale, font_h, small_font_h, pad_x, pad_y,
         total_heroes, spacing, start_x, hero_y,
         start_rect, help_rect, options_rect, resume_rect, exit_rect) = self._menu_layout()

        # Check hero preview positions
        for i in range(total_heroes):
            hx = start_x + i * spacing
            preview_img = self.hero_previews[i][0]
            pw, ph = preview_img.get_size()
            hero_rect = pygame.Rect(hx - pw // 2, hero_y - ph // 2, pw, ph)
            if hero_rect.collidepoint(mx, my):
                self.selected_hero_index = i
                self.audio.play_sfx("menu_move")
                return

        # Check resume button (only when autosave exists)
        if self.has_autosave and resume_rect.collidepoint(mx, my):
            self._load_from_autosave()
            return

        # Check start button
        if start_rect.collidepoint(mx, my):
            self.new_game()

        # Check help button
        if help_rect.collidepoint(mx, my):
            self.help_scroll_y = 0
            self.state = self.STATE_HELP
            self.audio.play_sfx("menu_accept")

        # Check options button
        if options_rect.collidepoint(mx, my):
            self.pause_slider_sel = 0
            self.state = self.STATE_OPTIONS
            self.audio.play_sfx("menu_accept")

        # Check exit button
        if exit_rect.collidepoint(mx, my):
            self.audio.play_sfx("menu_cancel")
            self.running = False

    def _use_item(self, slot: int):
        """Use an item from inventory."""
        stack = self.player.inventory.get_slot(slot)
        if not stack:
            return

        item = stack.item_data
        if item.type == ItemType.CONSUMABLE:
            # Don't consume a heal item when HP is already full
            if item.buff_type == "heal" and self.player.hp >= self.player.max_hp:
                self.hud.show_message("HP is already full!")
                return
            self.player.apply_buff(item.buff_type, item.buff_value,
                                   item.buff_duration)
            self.player.inventory.remove_item(slot, 1)
            self.audio.play_sfx("powerup")
            self.hud.show_message(f"Used {item.name}")

        elif item.type == ItemType.WEAPON:
            if item.weapon_id:
                old_weapon = self.player.equip_weapon(item.weapon_id)
                if old_weapon is False:
                    # Class restriction
                    self.hud.show_message(f"Cannot wield {item.name}!")
                    self.audio.play_sfx("menu_cancel")
                else:
                    self.player.inventory.remove_item(slot, 1)
                    # Put old weapon back into the same inventory slot
                    if old_weapon:
                        for iid, idata in self.item_db.items():
                            if (idata.type == ItemType.WEAPON
                                    and idata.weapon_id == old_weapon.id):
                                self.player.inventory.set_slot(slot, idata, 1)
                                break
                    self.audio.play_sfx("menu_accept")
                    self.hud.show_message(f"Equipped {item.name}")

        elif item.type == ItemType.ARMOR:
            if item.armor_id:
                result = self.player.equip_armor(item.armor_id)
                if result is False:
                    # Class restriction
                    self.hud.show_message(f"Cannot wear {item.name}!")
                    self.audio.play_sfx("menu_cancel")
                else:
                    self.player.inventory.remove_item(slot, 1)
                    # Put old armor back into the same inventory slot
                    if result is not None:
                        old_armor_id = result["id"]
                        for iid, idata in self.item_db.items():
                            if (idata.type == ItemType.ARMOR
                                    and idata.armor_id == old_armor_id):
                                self.player.inventory.set_slot(slot, idata, 1)
                                break
                    self.audio.play_sfx("menu_accept")
                    self.hud.show_message(f"Equipped {item.name}")

        elif item.type == ItemType.SELLABLE:
            self.hud.show_message("Cannot use this item. Sell it at a shop!")

    def _drop_item(self, slot: int):
        """Drop an item from inventory onto the ground."""
        removed = self.player.inventory.remove_item(slot, 1)
        if removed:
            icon = self.item_icons.get(removed.item_data.icon_key)
            if icon is None:
                icon = pygame.Surface((24, 24), pygame.SRCALPHA)
                pygame.draw.rect(icon, (200, 200, 200), (2, 2, 20, 20))
            ground_item = GroundItem(self.player.world_x + 30,
                                     self.player.world_y + 30,
                                     removed.item_data, removed.quantity, icon)
            self.ground_items.add(ground_item)
            self.audio.play_sfx("bonus")

    def _drop_held_item(self, stack):
        """Drop a held ItemStack onto the ground."""
        icon = self.item_icons.get(stack.item_data.icon_key)
        if icon is None:
            icon = pygame.Surface((24, 24), pygame.SRCALPHA)
            pygame.draw.rect(icon, (200, 200, 200), (2, 2, 20, 20))
        ground_item = GroundItem(self.player.world_x + 30,
                                 self.player.world_y + 30,
                                 stack.item_data, stack.quantity, icon)
        self.ground_items.add(ground_item)
        self.audio.play_sfx("bonus")

    def _spawn_floating_text(self, x: float, y: float, text: str, color: tuple):
        """Spawn a floating damage number at a world position."""
        self.floating_texts.append(FloatingText(x, y - 20, text, color))

    def _try_pickup(self):
        """Try to pick up nearby items or interact with NPCs."""
        # Check NPC interaction first
        for npc in self.stage.npcs:
            if npc.is_merchant and npc.is_near(self.player.collision_rect):
                shop = self.shops.get(npc.shop_id)
                if shop:
                    shop.open()
                    self.active_shop = shop
                    self.state = self.STATE_SHOP
                    self.audio.play_sfx("menu_accept")
                    return

        # Try item/gold pickup
        pickup_msg = self.combat.try_pickup(self.player, self.ground_items,
                                            self.gold_drops, self.audio)
        if pickup_msg:
            self.hud.show_message(pickup_msg)
        elif self.player.inventory.is_full():
            self.hud.show_message("Inventory full!")

    def _do_attack(self):
        """Process player attack against monsters and chests."""
        if self.player.equipped_weapon.is_ranged:
            # Ranged attack: spawn projectile
            attack_rect = self.player.attack()  # Sets cooldown, returns None
            if self.player.is_attacking:
                proj_info = self.player.get_projectile_info()
                if proj_info:
                    proj = Projectile(
                        proj_info["spawn_x"], proj_info["spawn_y"],
                        proj_info["direction"], proj_info["speed"],
                        proj_info["damage"], proj_info["max_range"],
                        proj_info["style"]
                    )
                    self.projectiles.append(proj)
                    self.audio.play_sfx(self.player.equipped_weapon.sound_swing)
                    # Double Fire: spawn a second homing projectile alongside
                    if self.player.double_fire_timer > 0:
                        homing_proj = Projectile(
                            proj_info["spawn_x"], proj_info["spawn_y"],
                            proj_info["direction"], proj_info["speed"],
                            proj_info["damage"], proj_info["max_range"],
                            proj_info["style"], homing=True
                        )
                        self.projectiles.append(homing_proj)
        else:
            # Melee attack
            hits, chest_hits = self.combat.player_attack(
                self.player, list(self.stage.monsters), self.stage.chests)
            if hits:
                damage = self.player.get_damage()
                for monster, killed in hits:
                    self._spawn_floating_text(
                        monster.world_x, monster.world_y,
                        str(damage), (255, 255, 100))  # Yellow
                self.combat.process_kills(
                    hits, self.player, self.drop_tables, self.item_db,
                    self.ground_items, self.gold_drops, self.item_icons,
                    self.stage.difficulty
                )
            if chest_hits:
                self._process_chest_hits(chest_hits)
            # Whirlwind: additionally hit all monsters in 50px radius on each swing
            if self.player.whirlwind_timer > 0 and self.player.is_attacking:
                self._do_whirlwind_attack()

    def _process_chest_hits(self, chest_hits: list):
        """Handle destroyed treasure chests: spawn loot, remove from stage."""
        from src.loot import roll_drops, GroundItem, GoldDrop

        for chest, destroyed in chest_hits:
            if destroyed:
                self.audio.play_sfx("kill")
                table_key = getattr(chest, 'drop_table_key', 'treasure_chest')
                gold, items = roll_drops(table_key, self.drop_tables,
                                         self.item_db, difficulty=self.stage.difficulty)
                if gold > 0:
                    drop = GoldDrop(chest.world_x, chest.world_y, gold)
                    self.gold_drops.add(drop)

                for item_data, qty in items:
                    icon = self.item_icons.get(item_data.icon_key)
                    if icon is None:
                        icon = pygame.Surface((24, 24), pygame.SRCALPHA)
                        pygame.draw.rect(icon, (200, 200, 200), (2, 2, 20, 20))
                    drop = GroundItem(
                        chest.world_x + pygame.math.Vector2(1, 0).rotate(
                            len(self.ground_items) * 45).x * 20,
                        chest.world_y + pygame.math.Vector2(1, 0).rotate(
                            len(self.ground_items) * 45).y * 20,
                        item_data, qty, icon
                    )
                    self.ground_items.add(drop)

                # Remove chest collision rect and from chest list
                if chest.collision_rect in self.stage.obstacle_rects:
                    self.stage.obstacle_rects.remove(chest.collision_rect)
                self.stage.chests.remove(chest)

    def _use_grit_ability(self):
        """Use the player's grit-powered ability (Warrior: Lunge, Ranger: Homing Arrow)."""
        from src.projectile import Projectile
        if not self.player.is_alive or not self.player.grit_ability:
            return
        ability = self.player.grit_ability

        if self.player.grit_cooldown > 0:
            return

        if not self.player.use_grit(ability["grit_cost"]):
            self.hud.show_message("Not enough grit!")
            return

        self.player.grit_cooldown = ability["cooldown"]

        if self.player.hero_id == "warrior":
            # Lunge: cone AoE strike with +100 range, 2x damage, 25px half-width
            from src.settings import DIR_DOWN, DIR_LEFT, DIR_RIGHT, DIR_UP
            _dir_vecs = {
                DIR_DOWN: (0, 1), DIR_LEFT: (-1, 0),
                DIR_RIGHT: (1, 0), DIR_UP: (0, -1),
            }
            direction = _dir_vecs.get(self.player.facing, (0, 1))
            dx, dy = direction
            cone_length = self.player.equipped_weapon.range + ability.get("range_bonus", 100)
            cone_half_w = 25.0

            # Compute half-angle for cone hit detection
            half_angle = math.atan2(cone_half_w, cone_length)

            self.player.lunge_active = True
            lunge_damage = self.player.get_damage()  # 2x while flag is set
            self.player.lunge_active = False

            # Hit all monsters inside the cone
            hits = []
            for monster in self.stage.monsters:
                if not monster.is_alive:
                    continue
                mx = getattr(monster, 'world_x', monster.rect.centerx)
                my = getattr(monster, 'world_y', monster.rect.centery)
                vx = mx - self.player.world_x
                vy = my - self.player.world_y
                dist = (vx ** 2 + vy ** 2) ** 0.5
                if dist > cone_length or dist < 1:
                    continue
                dot = max(-1.0, min(1.0, (vx * dx + vy * dy) / dist))
                if math.acos(dot) <= half_angle:
                    killed = monster.take_damage(lunge_damage)
                    hits.append((monster, killed))
                    self._spawn_floating_text(
                        mx, my, str(lunge_damage), (255, 220, 50))

            # Hit unlocked chests inside the cone
            chest_hits = []
            for chest in self.stage.chests:
                if not chest.is_alive or getattr(chest, 'locked', False):
                    continue
                mx = getattr(chest, 'world_x', chest.rect.centerx)
                my = getattr(chest, 'world_y', chest.rect.centery)
                vx = mx - self.player.world_x
                vy = my - self.player.world_y
                dist = (vx ** 2 + vy ** 2) ** 0.5
                if dist > cone_length or dist < 1:
                    continue
                dot = max(-1.0, min(1.0, (vx * dx + vy * dy) / dist))
                if math.acos(dot) <= half_angle:
                    destroyed = chest.take_damage(lunge_damage)
                    chest_hits.append((chest, destroyed))

            if hits:
                self.combat.process_kills(
                    hits, self.player, self.drop_tables, self.item_db,
                    self.ground_items, self.gold_drops, self.item_icons,
                    self.stage.difficulty)
            if chest_hits:
                self._process_chest_hits(chest_hits)

            # Trigger attack animation
            self.player.is_attacking = True
            self.player.attack_timer = 0.3

            # Spawn red cone visual
            self.spell_effects.append(
                SpellEffect("cone", self.player.world_x, self.player.world_y,
                            direction, cone_length, duration=0.35,
                            cone_half_width=cone_half_w))
            self.audio.play_sfx(self.player.equipped_weapon.sound_swing)

        elif self.player.hero_id == "ranger":
            # Homing Arrow: fire a projectile that steers toward the nearest enemy
            dir_vecs = {0: (0, 1), 1: (-1, 0), 2: (1, 0), 3: (0, -1)}
            direction = dir_vecs.get(self.player.facing, (0, 1))
            offset = TILE_SIZE * 0.5
            proj = Projectile(
                self.player.world_x + direction[0] * offset,
                self.player.world_y + direction[1] * offset,
                direction,
                self.player.equipped_weapon.projectile_speed,
                self.player.get_damage(),
                ability.get("homing_range", 220),
                style=self.player.equipped_weapon.projectile_style,
                homing=True,
            )
            self.projectiles.append(proj)
            # Trigger attack animation
            self.player.is_attacking = True
            self.player.attack_timer = 0.3
            self.audio.play_sfx(self.player.equipped_weapon.sound_swing)

    def _cast_spell(self):
        """Process spell casting by the player."""
        if not self.player.is_alive or not self.player.spell:
            return
        spell = self.player.spell

        # Check cooldown
        if self.player.spell_cooldown > 0:
            return

        # Check mana
        if not self.player.use_mana(spell["mana_cost"]):
            self.hud.show_message("Not enough mana!")
            return

        # Set cooldown
        self.player.spell_cooldown = spell["cooldown"]

        # Get facing direction vector
        dir_vecs = {0: (0, 1), 1: (-1, 0), 2: (1, 0), 3: (0, -1)}
        direction = dir_vecs.get(self.player.facing, (0, 1))
        damage = spell["damage"]

        if spell["type"] == "beam":
            # Light Beam: instant line damage in facing direction
            px, py = self.player.world_x, self.player.world_y
            beam_range = spell["range"]
            beam_rect = _beam_hitbox(px, py, direction, beam_range)

            for monster in list(self.stage.monsters):
                if not monster.is_alive:
                    continue
                mrect = getattr(monster, 'collision_rect', monster.rect)
                if beam_rect.colliderect(mrect):
                    killed = monster.take_damage(damage)
                    self._spawn_floating_text(monster.world_x, monster.world_y,
                                              str(damage), (255, 255, 200))
                    if killed:
                        self.combat.process_kills(
                            [(monster, True)], self.player, self.drop_tables,
                            self.item_db, self.ground_items, self.gold_drops,
                            self.item_icons, self.stage.difficulty)

            # Damage unlocked treasure chests in beam path
            chest_hits = []
            for chest in list(self.stage.chests):
                if not chest.is_alive or getattr(chest, 'locked', False):
                    continue
                if beam_rect.colliderect(chest.collision_rect):
                    destroyed = chest.take_damage(damage)
                    chest_hits.append((chest, destroyed))
            if chest_hits:
                self._process_chest_hits(chest_hits)

            # Visual effect
            self.spell_effects.append(
                SpellEffect("beam", px, py, direction, beam_range))
            self.audio.play_sfx("magic")

        elif spell["type"] == "aoe_circle":
            # Holy Smite: circle damage around caster
            px, py = self.player.world_x, self.player.world_y
            radius = spell["range"]

            for monster in list(self.stage.monsters):
                if not monster.is_alive:
                    continue
                mx = getattr(monster, 'world_x', monster.rect.centerx)
                my = getattr(monster, 'world_y', monster.rect.centery)
                dist = ((mx - px) ** 2 + (my - py) ** 2) ** 0.5
                if dist <= radius:
                    killed = monster.take_damage(damage)
                    self._spawn_floating_text(monster.world_x, monster.world_y,
                                              str(damage), (255, 255, 200))
                    if killed:
                        self.combat.process_kills(
                            [(monster, True)], self.player, self.drop_tables,
                            self.item_db, self.ground_items, self.gold_drops,
                            self.item_icons, self.stage.difficulty)

            # Damage unlocked treasure chests in radius
            chest_hits = []
            for chest in list(self.stage.chests):
                if not chest.is_alive or getattr(chest, 'locked', False):
                    continue
                cx = chest.world_x
                cy = chest.world_y
                dist = ((cx - px) ** 2 + (cy - py) ** 2) ** 0.5
                if dist <= radius:
                    destroyed = chest.take_damage(damage)
                    chest_hits.append((chest, destroyed))
            if chest_hits:
                self._process_chest_hits(chest_hits)

            # Visual effect
            self.spell_effects.append(
                SpellEffect("aoe_circle", px, py, direction, radius))
            self.audio.play_sfx("magic")

    # -----------------------------------------------------------------------
    # Multi-spell / multi-ability dispatch (new system)
    # -----------------------------------------------------------------------

    def _activate_selected_ability(self):
        """Cast the currently selected spell or grit ability."""
        if not self.player or not self.player.is_alive:
            return
        ab = self.player.get_selected_ability()
        if ab is None:
            return
        if "mana_cost" in ab:
            self._cast_ability(ab)
        else:
            self._use_grit_ability_by_def(ab)

    def _apply_beam_damage(self, damage: int, direction: tuple,
                           beam_range: float, px: float, py: float):
        """Helper: apply beam damage + spawn floating text + process kills/chests."""
        beam_rect = _beam_hitbox(px, py, direction, beam_range)
        hits = []
        for monster in list(self.stage.monsters):
            if not monster.is_alive:
                continue
            mrect = getattr(monster, 'collision_rect', monster.rect)
            if beam_rect.colliderect(mrect):
                killed = monster.take_damage(damage)
                self._spawn_floating_text(monster.world_x, monster.world_y,
                                          str(damage), (255, 255, 200))
                hits.append((monster, killed))
        if hits:
            self.combat.process_kills(hits, self.player, self.drop_tables,
                                      self.item_db, self.ground_items,
                                      self.gold_drops, self.item_icons,
                                      self.stage.difficulty)
        chest_hits = []
        for chest in list(self.stage.chests):
            if not chest.is_alive or getattr(chest, 'locked', False):
                continue
            if beam_rect.colliderect(chest.collision_rect):
                destroyed = chest.take_damage(damage)
                chest_hits.append((chest, destroyed))
        if chest_hits:
            self._process_chest_hits(chest_hits)

    def _apply_circle_damage(self, damage: int, radius: float,
                             px: float, py: float):
        """Helper: apply AoE circle damage + spawn floating text + process kills/chests."""
        hits = []
        for monster in list(self.stage.monsters):
            if not monster.is_alive:
                continue
            mx = getattr(monster, 'world_x', monster.rect.centerx)
            my = getattr(monster, 'world_y', monster.rect.centery)
            dist = ((mx - px) ** 2 + (my - py) ** 2) ** 0.5
            if dist <= radius:
                killed = monster.take_damage(damage)
                self._spawn_floating_text(monster.world_x, monster.world_y,
                                          str(damage), (255, 255, 200))
                hits.append((monster, killed))
        if hits:
            self.combat.process_kills(hits, self.player, self.drop_tables,
                                      self.item_db, self.ground_items,
                                      self.gold_drops, self.item_icons,
                                      self.stage.difficulty)
        chest_hits = []
        for chest in list(self.stage.chests):
            if not chest.is_alive or getattr(chest, 'locked', False):
                continue
            cx, cy = chest.world_x, chest.world_y
            if ((cx - px) ** 2 + (cy - py) ** 2) ** 0.5 <= radius:
                destroyed = chest.take_damage(damage)
                chest_hits.append((chest, destroyed))
        if chest_hits:
            self._process_chest_hits(chest_hits)

    def _cast_ability(self, ab: dict):
        """Cast a mana-based spell defined by ab dict."""
        if not self.player.is_alive:
            return
        ab_id = ab["id"]
        cd = self.player.get_ability_cooldown(ab_id)
        if cd > 0:
            return
        if not self.player.use_mana(ab["mana_cost"]):
            self.hud.show_message("Not enough mana!")
            return
        self.player.set_ability_cooldown(ab_id, ab["cooldown"])

        dir_vecs = {0: (0, 1), 1: (-1, 0), 2: (1, 0), 3: (0, -1)}
        direction = dir_vecs.get(self.player.facing, (0, 1))
        px, py = self.player.world_x, self.player.world_y
        damage = ab.get("damage", 0)
        ab_type = ab["type"]

        if ab_type == "beam":
            self._apply_beam_damage(damage, direction, ab["range"], px, py)
            self.spell_effects.append(SpellEffect("beam", px, py, direction, ab["range"]))
            self.audio.play_sfx("magic")

        elif ab_type == "aoe_circle":
            self._apply_circle_damage(damage, ab["range"], px, py)
            self.spell_effects.append(SpellEffect("aoe_circle", px, py, direction, ab["range"]))
            self.audio.play_sfx("magic")

        elif ab_type == "double_beam":
            opp = (-direction[0], -direction[1])
            self._apply_beam_damage(damage, direction, ab["range"], px, py)
            self._apply_beam_damage(damage, opp, ab["range"], px, py)
            self.spell_effects.append(SpellEffect("beam", px, py, direction, ab["range"]))
            self.spell_effects.append(SpellEffect("beam", px, py, opp, ab["range"]))
            self.audio.play_sfx("magic")

        elif ab_type == "holy_cross":
            for d in [(0, 1), (0, -1), (-1, 0), (1, 0)]:
                self._apply_beam_damage(damage, d, ab["range"], px, py)
                self.spell_effects.append(SpellEffect("beam", px, py, d, ab["range"]))
            self.audio.play_sfx("magic")

        elif ab_type == "shield":
            self.player.shield_hp = ab["shield_hp"]
            self.spell_effects.append(SpellEffect("aoe_circle", px, py, direction, 30))
            self.audio.play_sfx("magic")
            self.hud.show_message("Shield active!")

        elif ab_type == "heal_full":
            self.player.hp = self.player.max_hp
            self.spell_effects.append(SpellEffect("aoe_circle", px, py, direction, 60))
            self.audio.play_sfx("success")
            self.hud.show_message("HP fully restored!")

        elif ab_type == "fireball":
            from src.projectile import Projectile
            offset = 20
            proj = Projectile(
                px + direction[0] * offset,
                py + direction[1] * offset,
                direction,
                speed=300,
                damage=damage,
                max_range=ab["range"],
                style="magic",
                explodes=True,
                explosion_radius=ab.get("explosion_radius", 200),
            )
            self.projectiles.append(proj)
            self.audio.play_sfx("magic")

        elif ab_type == "magic_missile":
            from src.projectile import Projectile
            # Collect living monsters sorted by distance
            alive_monsters = [m for m in self.stage.monsters if m.is_alive]
            alive_monsters.sort(key=lambda m: (m.world_x - px)**2 + (m.world_y - py)**2)
            mote_count = ab.get("mote_count", 4)
            if not alive_monsters:
                self.hud.show_message("No targets!")
                # Refund mana and cooldown
                self.player.mana = min(self.player.max_mana,
                                       self.player.mana + ab["mana_cost"])
                self.player.set_ability_cooldown(ab_id, 0.0)
                return
            # Distribute motes round-robin across available monsters
            targets = [alive_monsters[i % len(alive_monsters)] for i in range(mote_count)]
            import math as _math
            for i, target in enumerate(targets):
                # Slightly spread spawn angle so motes fan out visually
                angle_offset = (i - mote_count / 2.0) * 0.15
                dx = direction[0] * _math.cos(angle_offset) - direction[1] * _math.sin(angle_offset)
                dy = direction[0] * _math.sin(angle_offset) + direction[1] * _math.cos(angle_offset)
                mag = (dx*dx + dy*dy)**0.5 or 1
                d = (dx/mag, dy/mag)
                proj = Projectile(
                    px + d[0] * 16, py + d[1] * 16,
                    d, speed=280, damage=damage,
                    max_range=400, style="magic",
                    homing=True, target_monster=target,
                )
                self.projectiles.append(proj)
            self.audio.play_sfx("magic")

        elif ab_type == "polymorph":
            from src.settings import POLYMORPH_PROGRESSION
            # Find nearest living non-boss monster
            target = None
            best = float('inf')
            for m in self.stage.monsters:
                if not m.is_alive or m.is_boss:
                    continue
                d = (m.world_x - px)**2 + (m.world_y - py)**2
                if d < best:
                    best = d
                    target = m
            if target:
                # Downgrade type
                cur = getattr(target, 'monster_type', None)
                if cur in POLYMORPH_PROGRESSION:
                    idx = POLYMORPH_PROGRESSION.index(cur)
                    new_type = POLYMORPH_PROGRESSION[max(0, idx - 1)]
                else:
                    new_type = "wild_cat"
                target.polymorph(new_type, duration=ab.get("duration", 30.0))
                self.spell_effects.append(
                    SpellEffect("aoe_circle", target.world_x, target.world_y,
                                direction, 40))
                self.hud.show_message(f"Polymorphed to {new_type}!")
            else:
                self.hud.show_message("No targets!")
                self.player.mana = min(self.player.max_mana,
                                       self.player.mana + ab["mana_cost"])
                self.player.set_ability_cooldown(ab_id, 0.0)
            self.audio.play_sfx("magic")

        elif ab_type == "portal":
            self._transition_to_last_town()

        elif ab_type == "safespace":
            self._do_safespace()

        elif ab_type == "prison":
            # Find nearest chasing/enraged living non-boss monster
            target = None
            best = float('inf')
            for m in self.stage.monsters:
                if not m.is_alive or m.is_boss:
                    continue
                if not (getattr(m, 'is_chasing', False) or
                        getattr(m, 'is_enraged', False)):
                    continue
                d = (m.world_x - px)**2 + (m.world_y - py)**2
                if d < best:
                    best = d
                    target = m
            if target:
                target.is_imprisoned = True
                target.prison_timer = ab.get("duration", 30.0)
                self.hud.show_message("Monster imprisoned!")
                self.audio.play_sfx("magic")
            else:
                self.hud.show_message("No pursuing target!")
                self.player.mana = min(self.player.max_mana,
                                       self.player.mana + ab["mana_cost"])
                self.player.set_ability_cooldown(ab_id, 0.0)

        elif ab_type == "resurrection":
            # Auto-trigger only — cannot be cast manually; show hint
            self.hud.show_message("(Auto-triggers on death)")

    def _use_grit_ability_by_def(self, ab: dict):
        """Use a grit-based ability defined by ab dict."""
        from src.projectile import Projectile
        if not self.player.is_alive:
            return
        ab_id = ab["id"]
        cd = self.player.get_ability_cooldown(ab_id)
        if cd > 0:
            return
        if not self.player.use_grit(ab["grit_cost"]):
            self.hud.show_message("Not enough grit!")
            return
        self.player.set_ability_cooldown(ab_id, ab["cooldown"])
        self._execute_grit_ability(ab)

    def _execute_grit_ability(self, ab: dict):
        """Execute the actual effect of a grit ability (also used by combo)."""
        from src.projectile import Projectile
        import math as _math
        from src.settings import DIR_DOWN, DIR_LEFT, DIR_RIGHT, DIR_UP
        _dir_vecs = {DIR_DOWN: (0,1), DIR_LEFT: (-1,0), DIR_RIGHT: (1,0), DIR_UP: (0,-1)}
        direction = _dir_vecs.get(self.player.facing, (0, 1))
        dx, dy = direction
        px, py = self.player.world_x, self.player.world_y
        ab_type = ab["type"]

        if ab_type == "lunge":
            cone_length = self.player.equipped_weapon.range + ab.get("range_bonus", 100)
            cone_half_w = 25.0
            half_angle = _math.atan2(cone_half_w, cone_length)
            self.player.lunge_active = True
            lunge_damage = self.player.get_damage()
            self.player.lunge_active = False
            hits = []
            for monster in self.stage.monsters:
                if not monster.is_alive:
                    continue
                mx = getattr(monster, 'world_x', monster.rect.centerx)
                my = getattr(monster, 'world_y', monster.rect.centery)
                vx, vy = mx - px, my - py
                dist = (vx**2 + vy**2)**0.5
                if dist > cone_length or dist < 1:
                    continue
                dot = max(-1.0, min(1.0, (vx*dx + vy*dy) / dist))
                if _math.acos(dot) <= half_angle:
                    killed = monster.take_damage(lunge_damage)
                    hits.append((monster, killed))
                    self._spawn_floating_text(mx, my, str(lunge_damage), (255, 220, 50))
            chest_hits = []
            for chest in self.stage.chests:
                if not chest.is_alive or getattr(chest, 'locked', False):
                    continue
                mx = getattr(chest, 'world_x', chest.rect.centerx)
                my = getattr(chest, 'world_y', chest.rect.centery)
                vx, vy = mx - px, my - py
                dist = (vx**2 + vy**2)**0.5
                if dist > cone_length or dist < 1:
                    continue
                dot = max(-1.0, min(1.0, (vx*dx + vy*dy) / dist))
                if _math.acos(dot) <= half_angle:
                    destroyed = chest.take_damage(lunge_damage)
                    chest_hits.append((chest, destroyed))
            if hits:
                self.combat.process_kills(hits, self.player, self.drop_tables,
                                          self.item_db, self.ground_items,
                                          self.gold_drops, self.item_icons,
                                          self.stage.difficulty)
            if chest_hits:
                self._process_chest_hits(chest_hits)
            self.player.is_attacking = True
            self.player.attack_timer = 0.3
            self.spell_effects.append(SpellEffect(
                "cone", px, py, direction, cone_length,
                duration=0.35, cone_half_width=cone_half_w))
            self.audio.play_sfx(self.player.equipped_weapon.sound_swing)

        elif ab_type == "homing_arrow":
            offset = TILE_SIZE * 0.5
            proj = Projectile(
                px + direction[0] * offset, py + direction[1] * offset,
                direction,
                self.player.equipped_weapon.projectile_speed,
                self.player.get_damage(),
                ab.get("homing_range", 220),
                style=self.player.equipped_weapon.projectile_style,
                homing=True,
            )
            self.projectiles.append(proj)
            self.player.is_attacking = True
            self.player.attack_timer = 0.3
            self.audio.play_sfx(self.player.equipped_weapon.sound_swing)

        elif ab_type == "heal":
            self.player.hp = min(self.player.max_hp,
                                 self.player.hp + ab.get("heal", 50))
            self.spell_effects.append(SpellEffect("aoe_circle", px, py, direction, 40))
            self.audio.play_sfx("success")
            self.hud.show_message(f"Healed {ab.get('heal', 50)} HP!")

        elif ab_type == "heal_full":
            self.player.hp = self.player.max_hp
            self.spell_effects.append(SpellEffect("aoe_circle", px, py, direction, 60))
            self.audio.play_sfx("success")
            self.hud.show_message("HP fully restored!")

        elif ab_type == "action_surge":
            self.player.action_surge_timer = ab.get("duration", 30.0)
            self.spell_effects.append(SpellEffect("aoe_circle", px, py, direction, 50))
            self.audio.play_sfx("powerup")
            self.hud.show_message("Action Surge! 2x speed + damage!")

        elif ab_type == "shield":
            self.player.shield_hp = ab.get("shield_hp", 100)
            self.spell_effects.append(SpellEffect("aoe_circle", px, py, direction, 40))
            self.audio.play_sfx("magic")
            self.hud.show_message(f"Shield: {ab.get('shield_hp', 100)} HP absorbed!")

        elif ab_type == "whirlwind":
            self.player.whirlwind_timer = ab.get("duration", 30.0)
            self.spell_effects.append(SpellEffect("aoe_circle", px, py, direction,
                                                  ab.get("range", 50)))
            self.audio.play_sfx("powerup")
            self.hud.show_message("Whirlwind! Striking all nearby enemies!")

        elif ab_type == "blazing_sword":
            self.player.blazing_sword_timer = ab.get("duration", 30.0)
            self.spell_effects.append(SpellEffect("beam", px, py, direction, 50,
                                                  duration=0.3))
            self.audio.play_sfx("powerup")
            self.hud.show_message("Blazing Sword! Extended range laser!")

        elif ab_type == "double_fire":
            self.player.double_fire_timer = ab.get("duration", 30.0)
            self.audio.play_sfx("powerup")
            self.hud.show_message("Double Fire! 2 homing shots per attack!")

        elif ab_type == "trap":
            target = None
            best = float('inf')
            for m in self.stage.monsters:
                if not m.is_alive or m.is_boss:
                    continue
                if not (getattr(m, 'is_chasing', False) or
                        getattr(m, 'is_enraged', False)):
                    continue
                d = (m.world_x - px)**2 + (m.world_y - py)**2
                if d < best:
                    best = d
                    target = m
            if target:
                target.is_trapped = True
                target.trap_timer = ab.get("duration", 30.0)
                self.hud.show_message("Monster trapped!")
                self.audio.play_sfx("magic")
            else:
                self.hud.show_message("No pursuing target!")
                # Refund
                self.player.grit = min(self.player.max_grit,
                                       self.player.grit + ab["grit_cost"])
                self.player.set_ability_cooldown(ab["id"], 0.0)

        elif ab_type == "cover_darkness":
            count = 0
            for m in self.stage.monsters:
                if not m.is_alive:
                    continue
                if getattr(m, 'is_chasing', False) or getattr(m, 'is_enraged', False):
                    m.is_darkened = True
                    m.darkened_timer = ab.get("duration", 30.0)
                    count += 1
            if count:
                self.hud.show_message(f"Cover of Darkness! {count} enemies blinded!")
            else:
                self.hud.show_message("No pursuing enemies!")
            self.audio.play_sfx("magic")

        elif ab_type == "combo":
            # Execute each sub-ability by id (no extra cooldown/cost)
            for sub_id in ab.get("combo", []):
                sub_ab = next((a for a in self.player._ability_list if a["id"] == sub_id), None)
                if sub_ab:
                    self._execute_grit_ability(sub_ab)

        elif ab_type == "resurrection":
            self.hud.show_message("(Auto-triggers on death)")

    def _do_whirlwind_attack(self):
        """Called during melee attack while Whirlwind is active: hit all in 50px radius."""
        px, py = self.player.world_x, self.player.world_y
        radius = 50
        hits = []
        for monster in list(self.stage.monsters):
            if not monster.is_alive:
                continue
            mx = getattr(monster, 'world_x', monster.rect.centerx)
            my = getattr(monster, 'world_y', monster.rect.centery)
            if ((mx - px)**2 + (my - py)**2)**0.5 <= radius:
                killed = monster.take_damage(self.player.get_damage())
                self._spawn_floating_text(mx, my, str(self.player.get_damage()),
                                          (255, 220, 50))
                hits.append((monster, killed))
        if hits:
            self.combat.process_kills(hits, self.player, self.drop_tables,
                                      self.item_db, self.ground_items,
                                      self.gold_drops, self.item_icons,
                                      self.stage.difficulty)

    # -----------------------------------------------------------------------
    # Resurrection methods
    # -----------------------------------------------------------------------

    def _get_selected_resurrection(self):
        """Return the selected auto-trigger resurrection ability if affordable, else None."""
        if not self.player:
            return None
        auto_ab = self.player.get_auto_spell()
        if not auto_ab:
            return None
        cost = auto_ab.get("mana_cost", auto_ab.get("grit_cost", 0))
        resource = (self.player.mana if "mana_cost" in auto_ab
                    else self.player.grit)
        if resource >= cost:
            return auto_ab
        return None

    def _trigger_resurrection(self, ab: dict):
        """Resurrect the player based on hero type."""
        cost = ab.get("mana_cost", ab.get("grit_cost", 0))
        if "mana_cost" in ab:
            self.player.mana = max(0, self.player.mana - cost)
        else:
            self.player.grit = max(0, self.player.grit - cost)

        self.player.is_alive = True
        self.player.hp = self.player.max_hp

        hero = self.player.hero_id
        if hero == "mage":
            self._transition_to_last_town()
        elif hero == "paladin":
            self.hud.show_message("Holy light restores you!")
            self.audio.play_sfx("success")
        elif hero == "warrior":
            self._blazing_resurrect_aoe()
            self.hud.show_message("You rise in blazing glory!")
            self.audio.play_sfx("success")
        elif hero == "ranger":
            self.hud.show_message("You spring back to life!")
            self.audio.play_sfx("success")

    def _trigger_fireball_explosion(self, proj):
        """Handle AoE explosion when a fireball projectile hits something."""
        radius = getattr(proj, 'explosion_radius', 200)
        px, py = proj.world_x, proj.world_y
        damage = proj.damage  # Fireball damage from spell definition
        hits = []
        for monster in list(self.stage.monsters):
            if not monster.is_alive:
                continue
            mx = getattr(monster, 'world_x', monster.rect.centerx)
            my = getattr(monster, 'world_y', monster.rect.centery)
            dist = ((mx - px) ** 2 + (my - py) ** 2) ** 0.5
            if dist <= radius:
                killed = monster.take_damage(damage)
                self._spawn_floating_text(mx, my, str(damage), (255, 140, 30))
                hits.append((monster, killed))
        if hits:
            self.combat.process_kills(hits, self.player, self.drop_tables,
                                      self.item_db, self.ground_items,
                                      self.gold_drops, self.item_icons,
                                      self.stage.difficulty)
        # Explosion visual (large orange expanding circle)
        self.spell_effects.append(SpellEffect(
            "aoe_circle", px, py, (0, 1), radius, duration=0.6))
        self.audio.play_sfx("fireball")

    def _blazing_resurrect_aoe(self):
        """Warrior Blazing Resurrect: deal 4x weapon damage in 220px radius."""
        damage = self.player.get_damage() * 4
        px, py = self.player.world_x, self.player.world_y
        self._apply_circle_damage(damage, 220, px, py)
        self.spell_effects.append(
            SpellEffect("aoe_circle", px, py, (0, 1), 220))

    def _transition_to_last_town(self):
        """Portal / Arcane Resurrection: teleport to last visited town."""
        target_num = max(1, self.last_town_num)
        self.current_stage_num = target_num
        self.current_stage_type = "town"
        # Clear transient state
        self.projectiles = []
        self.floating_texts = []
        self.spell_effects = []
        self.ground_items = pygame.sprite.Group()
        self.gold_drops = pygame.sprite.Group()
        self._load_stage()
        sx, sy = self.stage.player_start
        self.player.world_x = sx
        self.player.world_y = sy
        self.player.is_alive = True
        self.camera = Camera(self.stage.width, self.stage.height)
        self.in_boss_area = False
        track = self._next_town_track()
        self.audio.play_music(track, loops=0)
        self.hud.show_message(f"Transported to Town {target_num}!")

    def _do_safespace(self):
        """Safe Space spell: teleport player to a clear random spot, clear chases."""
        import random as _random
        # Try to find a clear position away from monsters and obstacles
        found = False
        for _ in range(50):
            tx = _random.randint(3, self.stage.width // TILE_SIZE - 3) * TILE_SIZE
            ty = _random.randint(3, self.stage.height // TILE_SIZE - 3) * TILE_SIZE
            # Check not near any monster
            clear = True
            for m in self.stage.monsters:
                if not m.is_alive:
                    continue
                if ((m.world_x - tx)**2 + (m.world_y - ty)**2)**0.5 < 100:
                    clear = False
                    break
            if not clear:
                continue
            # Use stage helper if available
            new_pos = self.stage._find_clear_spawn(tx, ty)
            self.player.world_x = new_pos[0]
            self.player.world_y = new_pos[1]
            found = True
            break
        if not found:
            # Fallback: just move slightly from current position
            self.player.world_x += TILE_SIZE * 3
        # Break all chases
        for m in self.stage.monsters:
            if not m.is_alive:
                continue
            m.is_chasing = False
            m.is_enraged = False
            m.is_darkened = True
            m.darkened_timer = 5.0  # brief pause before they can re-engage
        self.spell_effects.append(SpellEffect(
            "aoe_circle", self.player.world_x, self.player.world_y,
            (0, 1), 60))
        self.audio.play_sfx("success")
        self.hud.show_message("Safe Space! Enemies disengaged!")

    def update(self, dt: float):
        """Update game state."""
        if self.state == self.STATE_PLAYING:
            self._update_playing(dt)
        elif self.state == self.STATE_INVENTORY:
            self.player.inventory.update_hover(pygame.mouse.get_pos())
            self.hud.update(dt)
        elif self.state == self.STATE_SHOP:
            if self.active_shop:
                self.active_shop.update(dt, pygame.mouse.get_pos())
            self.hud.update(dt)

    def _update_playing(self, dt: float):
        """Update gameplay state."""
        keys = pygame.key.get_pressed()

        # Continuous attack while holding space, left mouse button, or controller A
        mouse_buttons = pygame.mouse.get_pressed()
        controller_attack = self._controller_button(CONTROLLER_BUTTON_ATTACK)
        if ((keys[KEY_ATTACK] or mouse_buttons[0] or controller_attack)
                and self.player.attack_cooldown <= 0):
            self._do_attack()

        # Player movement (keyboard + controller)
        controller_move = self._get_controller_move()
        all_entities = self.stage.get_all_entities()
        self.player.handle_input(keys, dt, self.stage.obstacle_rects, all_entities,
                                 controller_move=controller_move)
        self.player.update(dt)

        # Camera
        self.camera.update(self.player.rect)

        # Monsters
        player_pos = (self.player.world_x, self.player.world_y)
        for monster in self.stage.monsters:
            monster.update(dt, player_pos, self.stage.obstacle_rects, all_entities)

        # NPCs
        self.hud.near_merchant = False
        for npc in self.stage.npcs:
            npc.update(dt, self.stage.obstacle_rects, all_entities,
                       player_pos=player_pos)
            # Check if player is near a merchant for interaction hint
            if npc.is_merchant and npc.is_near(self.player.collision_rect):
                self.hud.near_merchant = True

        # Monster contact damage
        damage_events = self.combat.process_monster_contact(
            self.player, list(self.stage.monsters))
        for dmg, mx, my in damage_events:
            self._spawn_floating_text(
                self.player.world_x, self.player.world_y,
                str(dmg), (255, 80, 80))  # Red for damage to player

        # Treasure chests
        for chest in self.stage.chests:
            chest.update(dt)

        # Projectiles
        for proj in self.projectiles[:]:
            hits, chest_hits = proj.update(dt, self.stage.obstacle_rects,
                                           list(self.stage.monsters),
                                           self.stage.chests)
            # Fireball explosion: triggered when _exploded flag is set
            if getattr(proj, '_exploded', False):
                self._trigger_fireball_explosion(proj)
            if hits:
                # Process kills from projectile hits
                for monster, killed in hits:
                    self._spawn_floating_text(
                        monster.world_x, monster.world_y,
                        str(proj.damage), (255, 255, 100))  # Yellow
                self.combat.process_kills(
                    hits, self.player, self.drop_tables, self.item_db,
                    self.ground_items, self.gold_drops, self.item_icons,
                    self.stage.difficulty
                )
                self.audio.play_sfx(self.player.equipped_weapon.sound_hit)
            if chest_hits:
                self._process_chest_hits(chest_hits)
            if not proj.is_alive:
                self.projectiles.remove(proj)

        # Ground items
        for item in self.ground_items:
            item.update(dt)
        for gold in self.gold_drops:
            gold.update(dt)

        # Update floating damage numbers
        for ft in self.floating_texts[:]:
            ft.update(dt)
            if not ft.is_alive:
                self.floating_texts.remove(ft)

        # Update spell visual effects
        for se in self.spell_effects[:]:
            se.update(dt)
            if not se.is_alive:
                self.spell_effects.remove(se)

        # Check player death — try resurrection first
        if not self.player.is_alive:
            res_ab = self._get_selected_resurrection()
            if res_ab:
                self._trigger_resurrection(res_ab)
                if self.player.is_alive:
                    return  # resurrection succeeded, continue playing
            self.state = self.STATE_GAME_OVER
            self.audio.play_sfx("gameover")
            self.audio.stop_music()
            return

        # Boss area and boss chase music
        was_in_boss = self.in_boss_area
        was_boss_defeated = self.stage.boss_defeated
        was_boss_chasing = self.boss_chasing
        self.in_boss_area = (self.stage.stage_type == "combat"
                             and self.stage.is_in_boss_area(self.player.rect))

        # Check if any boss is actively chasing the player
        self.boss_chasing = False
        if self.stage.stage_type == "combat" and not self.stage.boss_defeated:
            for m in self.stage.monsters:
                if m.is_boss and m.is_alive and m.is_chasing:
                    self.boss_chasing = True
                    break

        # Determine if boss music should be playing
        should_play_boss = ((self.in_boss_area or self.boss_chasing)
                            and not self.stage.boss_defeated)
        was_playing_boss = ((was_in_boss or was_boss_chasing)
                            and not was_boss_defeated)

        if should_play_boss and not was_playing_boss:
            self.audio.play_music(BOSS_MUSIC, loops=0)
        elif not should_play_boss and was_playing_boss:
            music = self._next_combat_track()
            self.audio.play_music(music, loops=0)

        # Check if boss was just defeated — unlock boss chests and switch music
        if (self.stage.stage_type == "combat" and not was_boss_defeated
                and self.stage.check_boss_defeated()):
            self.stage.unlock_boss_chests()
            self.hud.show_message("Boss defeated! Treasure chests unlocked!")
            if self.in_boss_area or self.boss_chasing:
                music = self._next_combat_track()
                self.audio.play_music(music, loops=0)

        # Check exit
        if self.stage.exit_portal:
            if self.stage.exit_portal.check_player(self.player.collision_rect):
                if self.stage.stage_type == "town" or self.stage.check_boss_defeated():
                    self.advance_stage()
                else:
                    self.hud.show_message("Defeat the boss first!")

        # HUD
        self.hud.update(dt)

        # Remove dead monsters after delay
        for m in list(self.stage.monsters):
            if not m.is_alive and m.death_timer > 1.0:
                self.stage.monsters.remove(m)

    def draw(self):
        """Render the current frame."""
        self.screen.fill(BLACK)

        if self.state == self.STATE_MENU:
            self._draw_menu()
        elif self.state == self.STATE_HELP:
            self._draw_help()
        elif self.state == self.STATE_OPTIONS:
            self._draw_options()
        elif self.state in (self.STATE_SAVE_DIALOG, self.STATE_LOAD_DIALOG,
                            self.STATE_DELETE_DIALOG):
            # Draw the appropriate background depending on where the dialog came from
            if self.dialog_return_state == self.STATE_PAUSED:
                self._draw_game()
                self._draw_pause()
            else:
                self._draw_options()  # Options screen as background
            if self.state == self.STATE_SAVE_DIALOG:
                self._draw_save_dialog()
            elif self.state == self.STATE_LOAD_DIALOG:
                self._draw_load_dialog()
            elif self.state == self.STATE_DELETE_DIALOG:
                self._draw_delete_dialog()
        elif self.state in (self.STATE_PLAYING, self.STATE_INVENTORY,
                            self.STATE_SHOP, self.STATE_PAUSED):
            self._draw_game()
            if self.state == self.STATE_INVENTORY:
                self.player.inventory.draw(self.screen, self.item_icons, self.font)
                self._draw_overlay_messages()
            elif self.state == self.STATE_SHOP and self.active_shop:
                self.active_shop.controller_connected = self.controller_connected
                self.active_shop.draw(self.screen, self.player,
                                      self.item_icons, self.font)
                self._draw_overlay_messages()
            elif self.state == self.STATE_PAUSED:
                self._draw_pause()
        elif self.state == self.STATE_GAME_OVER:
            self._draw_game()
            self._draw_game_over()
        elif self.state == self.STATE_WIN:
            self._draw_game()
            self._draw_win()

        pygame.display.flip()

    def _menu_layout(self):
        """Compute menu screen layout rects (shared by draw and click handler)."""
        sw, sh = SCREEN_WIDTH, SCREEN_HEIGHT
        cx = sw // 2
        scale = settings.get_font_scale()
        font_h = self.font.get_height()
        small_font_h = self.small_font.get_height()
        pad_x = int(16 * scale)
        pad_y = int(8 * scale)

        # Hero section
        total_heroes = len(self.hero_previews)
        spacing = min(int(120 * scale), (sw - 60) // max(total_heroes, 1))
        total_width = (total_heroes - 1) * spacing
        start_x = cx - total_width // 2
        hero_y = int(sh * 0.38)

        # Resume button (shown above Start when autosave exists) — sel=3
        resume_text_w = self.font.size("Resume")[0]
        resume_btn_w = resume_text_w + pad_x * 2
        resume_btn_h = font_h + pad_y * 2
        resume_btn_y = int(sh * 0.57)
        resume_rect = pygame.Rect(cx - resume_btn_w // 2, resume_btn_y,
                                  resume_btn_w, resume_btn_h)

        # Start button — sized to fit text; shifted down slightly when Resume shown
        start_text_w = self.font.size("Start Game")[0]
        start_btn_w = start_text_w + pad_x * 2
        start_btn_h = font_h + pad_y * 2
        start_btn_y = int(sh * 0.66)
        start_rect = pygame.Rect(cx - start_btn_w // 2, start_btn_y,
                                 start_btn_w, start_btn_h)

        # Help and Options buttons — sized to fit text with gap between them
        help_text_w = self.font.size("Help (H)")[0]
        options_text_w = self.font.size("Options")[0]
        small_btn_h = font_h + pad_y * 2
        help_btn_w = help_text_w + pad_x * 2
        options_btn_w = options_text_w + pad_x * 2
        btn_gap = int(20 * scale)
        buttons_total = help_btn_w + btn_gap + options_btn_w
        small_btn_y = int(sh * 0.76)
        help_rect = pygame.Rect(cx - buttons_total // 2, small_btn_y,
                                help_btn_w, small_btn_h)
        options_rect = pygame.Rect(help_rect.right + btn_gap, small_btn_y,
                                   options_btn_w, small_btn_h)

        # Exit Game button — below help/options row, red styling; sel=4
        exit_text_w = self.font.size("Exit Game")[0]
        exit_btn_w = exit_text_w + pad_x * 2
        exit_btn_h = font_h + pad_y * 2
        exit_btn_y = int(sh * 0.82)
        exit_rect = pygame.Rect(cx - exit_btn_w // 2, exit_btn_y,
                                exit_btn_w, exit_btn_h)

        return (sw, sh, cx, scale, font_h, small_font_h, pad_x, pad_y,
                total_heroes, spacing, start_x, hero_y,
                start_rect, help_rect, options_rect, resume_rect, exit_rect)

    def _draw_menu(self):
        """Draw title screen with character selection."""
        (sw, sh, cx, scale, font_h, small_font_h, pad_x, pad_y,
         total_heroes, spacing, start_x, hero_y,
         start_rect, help_rect, options_rect, resume_rect, exit_rect) = self._menu_layout()

        # Title
        title = self.title_font.render("Monster World", True, WHITE)
        self.screen.blit(title, (cx - title.get_width() // 2, int(sh * 0.06)))

        # "Choose your hero" subtitle
        sub = self.font.render("Choose your hero", True, GRAY)
        self.screen.blit(sub, (cx - sub.get_width() // 2, int(sh * 0.16)))

        # Arrow hints
        if self.controller_connected:
            arrow_hint_text = "< D-pad / LB / RB >"
        else:
            arrow_hint_text = "< LEFT / RIGHT >"
        arrow_hint = self.small_font.render(arrow_hint_text, True, GRAY)
        self.screen.blit(arrow_hint, (cx - arrow_hint.get_width() // 2, int(sh * 0.21)))

        # Draw hero previews
        name_gap = font_h + int(12 * scale)  # space above sprite for name

        for i, (img, name) in enumerate(self.hero_previews):
            hx = start_x + i * spacing
            is_selected = (i == self.selected_hero_index)
            pw, ph = img.get_size()

            # Draw selection highlight
            if is_selected:
                highlight_rect = pygame.Rect(hx - pw // 2 - 8, hero_y - ph // 2 - 8,
                                             pw + 16, ph + 16)
                pygame.draw.rect(self.screen, GOLD_COLOR, highlight_rect, 3,
                                 border_radius=6)
                # Glow effect
                glow = pygame.Surface((pw + 24, ph + 24), pygame.SRCALPHA)
                pygame.draw.rect(glow, (255, 215, 0, 40),
                                 (0, 0, pw + 24, ph + 24), border_radius=8)
                self.screen.blit(glow, (hx - pw // 2 - 12, hero_y - ph // 2 - 12))

            # Draw hero name ABOVE highlight box
            name_color = GOLD_COLOR if is_selected else GRAY
            name_surf = self.font.render(name, True, name_color)
            self.screen.blit(name_surf,
                             (hx - name_surf.get_width() // 2,
                              hero_y - ph // 2 - name_gap))

            # Draw hero sprite
            draw_x = hx - pw // 2
            draw_y = hero_y - ph // 2
            self.screen.blit(img, (draw_x, draw_y))

        # Draw selected hero description below the hero row
        sel_hero = HERO_CHARACTERS[self.selected_hero_index]
        desc_text = sel_hero.get("desc", "")
        if desc_text:
            hp_mult = sel_hero.get("hp_mult", 1.0)
            base_hp = int(PLAYER_BASE_HP * hp_mult)
            desc_full = f"{desc_text}  (HP: {base_hp})"
            desc_surf = self.small_font.render(desc_full, True, WHITE)
            # Position below the tallest hero sprite
            max_ph = max(img.get_height() for img, _ in self.hero_previews)
            desc_y = hero_y + max_ph // 2 + int(16 * scale)
            self.screen.blit(desc_surf, (cx - desc_surf.get_width() // 2, desc_y))

        # Determine which button is highlighted by controller
        sel = self.menu_button_sel if self.controller_connected else -1

        # Resume button (only when an autosave exists) — controller sel=3
        if self.has_autosave:
            res_border = GOLD_COLOR if sel == 3 else (100, 200, 100)
            res_fill = (30, 80, 30) if sel == 3 else (20, 60, 20)
            res_bw = 3 if sel == 3 else 2
            pygame.draw.rect(self.screen, res_fill, resume_rect, border_radius=8)
            pygame.draw.rect(self.screen, res_border, resume_rect, res_bw, border_radius=8)
            res_text = self.font.render("Resume", True, WHITE)
            self.screen.blit(res_text, (resume_rect.centerx - res_text.get_width() // 2,
                                        resume_rect.centery - res_text.get_height() // 2))

        # Start button
        start_border = GOLD_COLOR if sel == 0 else GOLD_COLOR
        start_fill = (80, 80, 50) if sel == 0 else (60, 60, 80)
        start_bw = 3 if sel == 0 else 2
        pygame.draw.rect(self.screen, start_fill, start_rect, border_radius=8)
        pygame.draw.rect(self.screen, start_border, start_rect, start_bw, border_radius=8)
        btn_text = self.font.render("Start Game", True, WHITE)
        self.screen.blit(btn_text, (start_rect.centerx - btn_text.get_width() // 2,
                                    start_rect.centery - btn_text.get_height() // 2))

        # Help button
        help_border = GOLD_COLOR if sel == 1 else GRAY
        help_fill = (80, 80, 50) if sel == 1 else (50, 50, 70)
        help_bw = 3 if sel == 1 else 2
        pygame.draw.rect(self.screen, help_fill, help_rect, border_radius=8)
        pygame.draw.rect(self.screen, help_border, help_rect, help_bw, border_radius=8)
        help_text = self.font.render("Help (H)", True, WHITE)
        self.screen.blit(help_text, (help_rect.centerx - help_text.get_width() // 2,
                                     help_rect.centery - help_text.get_height() // 2))

        # Options button
        opt_border = GOLD_COLOR if sel == 2 else GRAY
        opt_fill = (80, 80, 50) if sel == 2 else (50, 50, 70)
        opt_bw = 3 if sel == 2 else 2
        pygame.draw.rect(self.screen, opt_fill, options_rect, border_radius=8)
        pygame.draw.rect(self.screen, opt_border, options_rect, opt_bw, border_radius=8)
        options_text = self.font.render("Options", True, WHITE)
        self.screen.blit(options_text, (options_rect.centerx - options_text.get_width() // 2,
                                        options_rect.centery - options_text.get_height() // 2))

        # Exit Game button — red styling, controller sel=4
        exit_border = GOLD_COLOR if sel == 4 else (180, 50, 50)
        exit_fill = (100, 30, 30) if sel == 4 else (70, 20, 20)
        exit_bw = 3 if sel == 4 else 2
        pygame.draw.rect(self.screen, exit_fill, exit_rect, border_radius=8)
        pygame.draw.rect(self.screen, exit_border, exit_rect, exit_bw, border_radius=8)
        exit_text_surf = self.font.render("Exit Game", True, WHITE)
        self.screen.blit(exit_text_surf, (exit_rect.centerx - exit_text_surf.get_width() // 2,
                                          exit_rect.centery - exit_text_surf.get_height() // 2))

        # Controls hint and enter hint — anchored below the exit button so they
        # never overlap it at any resolution.
        hint_gap = max(6, int(8 * scale))
        ctrl_y = exit_rect.bottom + hint_gap
        if self.controller_connected:
            controls_text = ("Stick/D-pad:Move  A:Attack  B:Pickup  "
                             "X:Inventory  Start:Pause")
        else:
            controls_text = ("WASD:Move  SPACE:Attack  E:Pickup  "
                             "I:Inventory  ESC:Pause")
        ctrl = self.small_font.render(controls_text, True, GRAY)
        self.screen.blit(ctrl, (cx - ctrl.get_width() // 2, ctrl_y))

        # Enter hint — one line below the controls hint
        enter_y = ctrl_y + small_font_h + max(4, int(4 * scale))
        if self.controller_connected:
            enter_hint = self.small_font.render(
                "D-pad/LB/RB: Navigate  |  A: Select  |  START: Start Game",
                True, WHITE)
        else:
            enter_hint = self.small_font.render("Press ENTER to start", True, WHITE)
        self.screen.blit(enter_hint, (cx - enter_hint.get_width() // 2, enter_y))

    def _help_back_rect(self):
        """Return the scaled Back button rect for the help screen."""
        scale = settings.get_font_scale()
        back_text_w = self.font.size("Back")[0]
        btn_w = max(100, back_text_w + int(32 * scale))
        btn_h = max(35, self.font.get_height() + int(16 * scale))
        return pygame.Rect(20, 20, btn_w, btn_h)

    def _draw_help(self):
        """Draw the help/info screen with characters, weapons, and items."""
        self.screen.fill((15, 15, 25))
        scale = settings.get_font_scale()

        # Back button rect determines where content starts
        back_rect = self._help_back_rect()
        content_top = back_rect.bottom + int(16 * scale)
        left_margin = int(40 * scale)

        # Build content lines: (text, color, font) or tuple for table rows
        # Each entry is either a simple line or a list of (text, x_offset, color)
        lines = []  # Each: (text, color, font) or ("__TABLE__", columns, font)

        def add_header(text):
            lines.append((text, GOLD_COLOR, self.big_font))

        def add_subheader(text):
            lines.append((text, YELLOW, self.font))

        def add_line(text, color=WHITE):
            lines.append((text, color, self.small_font))

        def add_blank():
            lines.append(("", WHITE, self.small_font))

        def add_table_row(columns, color=WHITE):
            """Add a row where each column is (text, x_pixel_offset)."""
            lines.append(("__TABLE__", columns, color, self.small_font))

        # --- HEROES ---
        add_header("HEROES")
        add_blank()
        for hero in HERO_CHARACTERS:
            hp_mult = hero.get("hp_mult", 1.0)
            base_hp = int(PLAYER_BASE_HP * hp_mult)
            weapon_id = hero.get("starting_weapon", "basic_sword")
            weapon = self.weapon_db.get(weapon_id)
            weapon_name = weapon.name if weapon else weapon_id
            add_subheader(hero["name"])
            add_line(f"  HP: {base_hp}   Speed: {int(PLAYER_SPEED)}   Starting Weapon: {weapon_name}")
            mana_base = hero.get("mana_base", 0)
            mana_per_lvl = hero.get("mana_per_level", 0)
            if mana_base > 0:
                add_line(f"  Mana: {mana_base} (+{mana_per_lvl}/level)", (50, 200, 100))
                hero_spells = SPELL_DEFS.get(hero["id"], [])
                for sdef in hero_spells:
                    dmg = sdef.get("damage", 0)
                    cost = sdef.get("mana_cost", 0)
                    desc = sdef.get("description", "")
                    lvl_req = sdef.get("min_level", 1)
                    auto = " [auto]" if sdef.get("auto_trigger") else ""
                    add_line(f"  Lv{lvl_req} {sdef['name']}{auto} - {dmg} dmg, "
                             f"{cost} mana. {desc}",
                             (200, 200, 255))
            grit_base = hero.get("grit_base", 0)
            grit_per_lvl = hero.get("grit_per_level", 0)
            if grit_base > 0:
                add_line(f"  Grit: {grit_base} (+{grit_per_lvl}/level)", (180, 120, 40))
                hero_abilities = GRIT_ABILITIES.get(hero["id"], [])
                for adef in hero_abilities:
                    cost = adef.get("grit_cost", 0)
                    desc = adef.get("description", "")
                    lvl_req = adef.get("min_level", 1)
                    auto = " [auto]" if adef.get("auto_trigger") else ""
                    add_line(f"  Lv{lvl_req} {adef['name']}{auto} - {cost} grit. {desc}",
                             (255, 200, 100))
            add_line(f"  {hero.get('desc', '')}", GRAY)
            add_blank()

        # --- LEVELLING ---
        add_header("LEVELLING")
        add_blank()
        add_line("  XP is earned by killing monsters. Warrior & Ranger need only 2/3 of base XP to level.", GRAY)
        add_blank()
        xp_col_level = 0
        xp_col_total = int(120 * scale)
        xp_col_gain  = int(240 * scale)
        xp_col_wrrng = int(360 * scale)
        add_table_row([
            ("Level Up", xp_col_level),
            ("Total XP", xp_col_total),
            ("XP Needed", xp_col_gain),
            ("War/Rgr XP", xp_col_wrrng),
        ], GRAY)
        xp_sep_end = xp_col_wrrng + int(100 * scale)
        xp_dash_count = xp_sep_end // max(1, self.small_font.size("-")[0])
        add_table_row([("-" * max(1, xp_dash_count), 0)], GRAY)
        for lvl in range(1, len(XP_THRESHOLDS) - 1):
            total_xp   = XP_THRESHOLDS[lvl + 1]
            gain_xp    = XP_THRESHOLDS[lvl + 1] - XP_THRESHOLDS[lvl]
            wr_total   = int(total_xp * 0.667)
            add_table_row([
                (f"{lvl} → {lvl + 1}", xp_col_level),
                (f"{total_xp:,}", xp_col_total),
                (f"{gain_xp:,}", xp_col_gain),
                (f"{wr_total:,}", xp_col_wrrng),
            ])
        add_blank()

        # --- WEAPONS ---
        add_header("WEAPONS")
        add_blank()
        # Pixel-based column positions for weapons table
        col_name = 0
        col_dmg = int(180 * scale)
        col_rng = int(250 * scale)
        col_spd = int(320 * scale)
        col_type = int(390 * scale)
        col_cls = int(460 * scale)

        add_table_row([
            ("Name", col_name), ("Damage", col_dmg), ("Range", col_rng),
            ("Speed", col_spd), ("Type", col_type), ("Classes", col_cls),
        ], GRAY)
        # Separator: dashes under each column header
        sep_end = col_cls + int(120 * scale)
        dash_count = sep_end // max(1, self.small_font.size("-")[0])
        add_table_row([("-" * max(1, dash_count), 0)], GRAY)
        for wid, weapon in self.weapon_db.items():
            ranged = "Ranged" if weapon.is_ranged else "Melee"
            if weapon.classes:
                cls_labels = {"warrior": "War", "paladin": "Pal",
                              "mage": "Mage", "ranger": "Rgr"}
                cls_str = "/".join(cls_labels.get(c, c.capitalize())
                                   for c in weapon.classes)
            else:
                cls_str = "All"
            add_table_row([
                (weapon.name, col_name),
                (str(weapon.damage), col_dmg),
                (str(weapon.range), col_rng),
                (f"{weapon.speed}s", col_spd),
                (ranged, col_type),
                (cls_str, col_cls),
            ])
        add_blank()

        # --- ITEMS ---
        add_header("ITEMS")
        add_blank()
        add_subheader("Consumables")
        for iid, item in self.item_db.items():
            if item.type.value == "consumable":
                add_line(f"  {item.name} - {item.description}  (Value: {item.value}g)")
        add_blank()
        add_subheader("Sellable Items")
        for iid, item in self.item_db.items():
            if item.type.value == "sellable":
                add_line(f"  {item.name} - Value: {item.value}g", (200, 200, 160))
        add_blank()
        add_subheader("Weapon Items")
        for iid, item in self.item_db.items():
            if item.type.value == "weapon":
                add_line(
                    f"  {item.name} - {item.description}  (Value: {item.value}g)",
                    (180, 200, 255)
                )
        add_blank()
        add_subheader("Armor Items")
        for iid, item in self.item_db.items():
            if item.type.value == "armor":
                add_line(
                    f"  {item.name} - {item.description}  (Value: {item.value}g)",
                    (140, 180, 255)
                )
        add_blank()

        # --- ARMOR ---
        add_header("ARMOR")
        add_blank()
        armor_col_name = 0
        armor_col_def = int(180 * scale)
        armor_col_val = int(260 * scale)
        armor_col_cls = int(340 * scale)
        add_table_row([
            ("Name", armor_col_name), ("Defense", armor_col_def),
            ("Value", armor_col_val), ("Class", armor_col_cls),
        ], GRAY)
        armor_sep_end = armor_col_cls + int(120 * scale)
        armor_dash_count = armor_sep_end // max(1, self.small_font.size("-")[0])
        add_table_row([("-" * max(1, armor_dash_count), 0)], GRAY)
        for armor_id, armor_info in ARMOR_DEFS.items():
            classes = ", ".join(c.title() for c in armor_info["classes"])
            add_table_row([
                (armor_info["name"], armor_col_name),
                (f"+{armor_info['defense']}", armor_col_def),
                (f"{armor_info['value']}g", armor_col_val),
                (classes, armor_col_cls),
            ])
        add_blank()
        add_line("  Armor reduces incoming damage. Damage formula: max(1, raw - armor_def - buff_def)", GRAY)
        add_line("  Warriors/Paladins can wear all armor. Mages/Rangers: Leather & Padded only.", GRAY)
        add_blank()

        # --- ENEMIES ---
        add_header("ENEMIES")
        add_blank()
        enemy_col_name = 0
        enemy_col_hp = int(180 * scale)
        enemy_col_dmg = int(280 * scale)
        enemy_col_spd = int(380 * scale)
        add_table_row([
            ("Enemy", enemy_col_name), ("HP", enemy_col_hp),
            ("Damage", enemy_col_dmg), ("Speed", enemy_col_spd),
        ], GRAY)
        enemy_sep_end = enemy_col_spd + int(80 * scale)
        enemy_dash_count = enemy_sep_end // max(1, self.small_font.size("-")[0])
        add_table_row([("-" * max(1, enemy_dash_count), 0)], GRAY)
        # Display names for monster types
        enemy_display_names = {
            "wild_cat": "Wild Cat",
            "wild_dog": "Wild Dog",
            "bandit": "Bandit",
            "soldier": "Soldier",
            "guard": "Guard",
            "commander": "Commander",
        }
        for monster_type, stats in MONSTER_STATS.items():
            display_name = enemy_display_names.get(monster_type, monster_type.replace("_", " ").title())
            add_table_row([
                (display_name, enemy_col_name),
                (str(stats["hp"]), enemy_col_hp),
                (str(stats["damage"]), enemy_col_dmg),
                (str(stats["speed"]), enemy_col_spd),
            ])
        add_blank()
        add_subheader("Boss Encounters by Stage")
        add_line(f"  Bosses chase the player at speed {int(BOSS_CHASE_SPEED)}.  "
                 f"Base multipliers: {BOSS_HP_MULT:.0f}x HP, {BOSS_DAMAGE_MULT:.1f}x Damage.", GRAY)
        add_line("  Stages 6-10 apply an additional scaling multiplier on top of base boss stats.", GRAY)
        add_blank()
        boss_col_stage  = 0
        boss_col_type   = int(60  * scale)
        boss_col_scale  = int(190 * scale)
        boss_col_hp     = int(270 * scale)
        boss_col_dmg    = int(350 * scale)
        add_table_row([
            ("Stage", boss_col_stage), ("Boss",  boss_col_type),
            ("Scale",  boss_col_scale), ("HP",   boss_col_hp),
            ("Damage", boss_col_dmg),
        ], GRAY)
        boss_sep_end = boss_col_dmg + int(80 * scale)
        boss_dash_count = boss_sep_end // max(1, self.small_font.size("-")[0])
        add_table_row([("-" * max(1, boss_dash_count), 0)], GRAY)
        for stage_num in range(1, 11):
            btype  = STAGE_BOSSES.get(stage_num, "commander")
            bscale = BOSS_STAGE_SCALING.get(stage_num, 1.0)
            bstats = MONSTER_STATS.get(btype, MONSTER_STATS["wild_cat"])
            bhp    = int(bstats["hp"]     * BOSS_HP_MULT     * bscale)
            bdmg   = int(bstats["damage"] * BOSS_DAMAGE_MULT * bscale)
            dname  = enemy_display_names.get(btype, btype.replace("_", " ").title())
            scale_str = f"x{bscale:.2f}".rstrip("0").rstrip(".")
            row_color = (255, 160, 80) if stage_num == 10 else (255, 200, 130) if stage_num >= 6 else WHITE
            add_table_row([
                (str(stage_num),  boss_col_stage),
                (dname,           boss_col_type),
                (scale_str,       boss_col_scale),
                (str(bhp),        boss_col_hp),
                (str(bdmg),       boss_col_dmg),
            ], row_color)
        add_blank()

        # --- SPELLS ---
        add_header("SPELLS")
        add_blank()
        spell_col_name = 0
        spell_col_hero = int(150 * scale)
        spell_col_lvl  = int(230 * scale)
        spell_col_dmg  = int(290 * scale)
        spell_col_mana = int(350 * scale)
        spell_col_type = int(420 * scale)
        add_table_row([
            ("Name", spell_col_name), ("Hero", spell_col_hero),
            ("Lv", spell_col_lvl), ("Damage", spell_col_dmg),
            ("Mana", spell_col_mana), ("Type", spell_col_type),
        ], GRAY)
        spell_sep_end = spell_col_type + int(80 * scale)
        spell_dash_count = spell_sep_end // max(1, self.small_font.size("-")[0])
        add_table_row([("-" * max(1, spell_dash_count), 0)], GRAY)
        for hero_id, spell_list in SPELL_DEFS.items():
            for sdef in spell_list:
                auto_tag = "[auto]" if sdef.get("auto_trigger") else ""
                name_str = f"{sdef['name']} {auto_tag}".strip()
                add_table_row([
                    (name_str, spell_col_name),
                    (hero_id.capitalize(), spell_col_hero),
                    (str(sdef.get("min_level", 1)), spell_col_lvl),
                    (str(sdef.get("damage", 0)), spell_col_dmg),
                    (str(sdef.get("mana_cost", 0)), spell_col_mana),
                    (sdef.get("type", "").replace("_", " ").title(), spell_col_type),
                ])
                desc = sdef.get("description", "")
                if desc:
                    add_line(f"  {desc}", GRAY)
        add_blank()
        add_line("  Select spells with 1-9 keys or D-pad L/R. Cast with Q or RB.", (200, 200, 255))
        add_blank()

        # --- GRIT ABILITIES ---
        add_header("GRIT ABILITIES")
        add_blank()
        grit_col_name = 0
        grit_col_hero = int(150 * scale)
        grit_col_lvl  = int(230 * scale)
        grit_col_cost = int(290 * scale)
        grit_col_cd   = int(360 * scale)
        add_table_row([
            ("Name", grit_col_name), ("Hero", grit_col_hero),
            ("Lv", grit_col_lvl), ("Grit", grit_col_cost),
            ("CD", grit_col_cd),
        ], GRAY)
        grit_sep_end = grit_col_cd + int(80 * scale)
        grit_dash_count = grit_sep_end // max(1, self.small_font.size("-")[0])
        add_table_row([("-" * max(1, grit_dash_count), 0)], GRAY)
        for hero_id, ability_list in GRIT_ABILITIES.items():
            for adef in ability_list:
                auto_tag = "[auto]" if adef.get("auto_trigger") else ""
                name_str = f"{adef['name']} {auto_tag}".strip()
                cd_val = adef.get("cooldown", 0)
                cd_str = "auto" if adef.get("auto_trigger") else f"{cd_val:.0f}s"
                add_table_row([
                    (name_str, grit_col_name),
                    (hero_id.capitalize(), grit_col_hero),
                    (str(adef.get("min_level", 1)), grit_col_lvl),
                    (str(adef.get("grit_cost", 0)), grit_col_cost),
                    (cd_str, grit_col_cd),
                ])
                desc = adef.get("description", "")
                if desc:
                    add_line(f"  {desc}", GRAY)
        add_blank()
        add_line("  Warrior & Ranger gain +3 grit per kill. Select abilities with 1-9 or D-pad L/R.", (255, 200, 100))
        add_blank()

        # --- CONTROLS ---
        add_header("KEYBOARD CONTROLS")
        add_blank()
        ctrl_col_action = 0
        ctrl_col_key = int(180 * scale)
        add_table_row([("Action", ctrl_col_action), ("Key", ctrl_col_key)], GRAY)
        add_table_row([("-" * 40, 0)], GRAY)
        kb_controls = [
            ("Move", "W / A / S / D"),
            ("Attack", "SPACE or Left Click"),
            ("Cast Spell", "Q"),
            ("Pick up / Interact", "E"),
            ("Inventory", "I or TAB"),
            ("Toggle Mini-map", "M"),
            ("Toggle FPS Counter", "F"),
            ("Pause / Menu", "ESC"),
            ("Use Item (inventory)", "Right Click"),
            ("Hero Select (menu)", "LEFT / RIGHT arrows"),
            ("Scroll Help", "Mouse Wheel or UP / DOWN"),
        ]
        for action, key in kb_controls:
            add_table_row([(action, ctrl_col_action), (key, ctrl_col_key)])
        add_blank()

        add_header("XBOX CONTROLLER")
        add_blank()
        add_line("  Connect an Xbox controller to enable gamepad controls.", GRAY)
        add_line("  The game auto-detects controllers on startup and hot-plug.", GRAY)
        add_blank()
        add_table_row([("Action", ctrl_col_action), ("Button", ctrl_col_key)], GRAY)
        add_table_row([("-" * 40, 0)], GRAY)
        gp_controls = [
            ("Move", "Left Stick or D-pad"),
            ("Attack", "A button"),
            ("Cast Spell", "RB button"),
            ("Pick up / Interact", "B button"),
            ("Inventory", "X button"),
            ("Toggle Mini-map", "Y button"),
            ("Pause / Resume", "START button"),
            ("Hero Select (menu)", "LB / RB or D-pad L/R"),
            ("Menu Buttons (menu)", "D-pad UP / DOWN"),
            ("Select (menu)", "A button"),
            ("Start Game (menu)", "A or START"),
            ("Help (menu)", "Back button"),
            ("Options (menu)", "X button"),
            ("Back / Quit", "B or Back button"),
            ("Scroll Help", "D-pad UP / DOWN"),
        ]
        for action, button in gp_controls:
            add_table_row([(action, ctrl_col_action), (button, ctrl_col_key)])
        add_blank()

        add_blank()
        add_line("Scroll with mouse wheel or UP/DOWN keys.  Press ESC or H to go back.", GRAY)

        # Render into a surface and blit with scroll offset
        sw, sh = SCREEN_WIDTH, SCREEN_HEIGHT
        line_height = settings.scaled_font_size(22)
        total_height = len(lines) * line_height + 80
        max_scroll = max(0, total_height - sh + content_top)
        self.help_scroll_y = min(self.help_scroll_y, max_scroll)

        y = content_top - self.help_scroll_y
        for entry in lines:
            if entry[0] == "__TABLE__":
                # Table row: columns at pixel positions
                _, columns, color, font = entry
                if -30 < y < sh + 10:
                    for col_text, col_x in columns:
                        surf = font.render(col_text, True, color)
                        self.screen.blit(surf, (left_margin + col_x, y))
            else:
                text, color, font = entry
                if -30 < y < sh + 10:
                    surf = font.render(text, True, color)
                    self.screen.blit(surf, (left_margin, y))
            y += line_height

        # Back button (always on screen, drawn last so it overlaps scrolling content)
        pygame.draw.rect(self.screen, (60, 60, 80), back_rect, border_radius=6)
        pygame.draw.rect(self.screen, GRAY, back_rect, 2, border_radius=6)
        back_text = self.font.render("Back", True, WHITE)
        self.screen.blit(back_text, (back_rect.centerx - back_text.get_width() // 2,
                                     back_rect.centery - back_text.get_height() // 2))

        # Scroll indicator
        if max_scroll > 0:
            bar_h = max(20, int(sh * sh / total_height))
            bar_y = int(60 + (sh - 80) * self.help_scroll_y / max_scroll)
            bar_y = min(bar_y, sh - bar_h - 10)
            pygame.draw.rect(self.screen, (80, 80, 100),
                             (sw - 12, bar_y, 6, bar_h), border_radius=3)

    def _options_rows(self):
        """Return list of option row IDs based on current game state."""
        rows = ["music", "sfx", "resolution"]
        if self.player is not None and self.player.is_alive:
            rows.append("save")
        rows.extend(["load", "delete"])
        return rows

    def _options_layout(self):
        """Compute options screen layout values (shared by draw and click handler)."""
        sw, sh = SCREEN_WIDTH, SCREEN_HEIGHT
        scale = settings.get_font_scale()
        slider_w = min(int(200 * scale), sw - 80)
        slider_x = sw // 2 - slider_w // 2
        slider_h = max(14, int(14 * scale))
        font_h = self.font.get_height()
        label_gap = font_h + int(6 * scale)
        knob_r = max(9, int(9 * scale))
        dot_r = max(6, int(6 * scale))
        row_gap = label_gap + slider_h + max(20, int(30 * scale))
        row_start = int(sh * 0.30)
        return (sw, sh, scale, slider_w, slider_x, slider_h,
                font_h, label_gap, knob_r, dot_r, row_gap, row_start)

    def _draw_options(self):
        """Draw the options screen with volume sliders and resolution picker."""
        (sw, sh, scale, slider_w, slider_x, slider_h,
         font_h, label_gap, knob_r, dot_r, row_gap, row_start) = self._options_layout()
        self.screen.fill((15, 15, 25))

        title = self.big_font.render("OPTIONS", True, GOLD_COLOR)
        self.screen.blit(title, (sw // 2 - title.get_width() // 2, int(sh * 0.12)))

        for idx, (label, volume) in enumerate([
            ("Music Volume", self.audio.music_volume),
            ("SFX Volume", self.audio.sfx_volume),
        ]):
            sy = row_start + idx * row_gap
            is_sel = (idx == self.pause_slider_sel)
            label_color = GOLD_COLOR if is_sel else WHITE
            lbl = self.font.render(f"{label}: {int(volume * 100)}%", True, label_color)
            self.screen.blit(lbl, (sw // 2 - lbl.get_width() // 2, sy - label_gap))

            # Slider track
            track_rect = pygame.Rect(slider_x, sy, slider_w, slider_h)
            pygame.draw.rect(self.screen, (60, 60, 80), track_rect, border_radius=6)
            pygame.draw.rect(self.screen, GRAY, track_rect, 1, border_radius=6)

            # Slider fill
            fill_w = int(slider_w * volume)
            if fill_w > 0:
                fill_rect = pygame.Rect(slider_x, sy, fill_w, slider_h)
                fill_color = GOLD_COLOR if is_sel else (100, 180, 100)
                pygame.draw.rect(self.screen, fill_color, fill_rect, border_radius=6)

            # Slider knob
            knob_x = slider_x + fill_w
            pygame.draw.circle(self.screen, WHITE, (knob_x, sy + slider_h // 2), knob_r)
            if is_sel:
                pygame.draw.circle(self.screen, GOLD_COLOR,
                                   (knob_x, sy + slider_h // 2), knob_r, 2)

        # Resolution selector (row index 2)
        res_y = row_start + 2 * row_gap
        is_sel = (self.pause_slider_sel == 2)
        label_color = GOLD_COLOR if is_sel else WHITE
        cur_res = AVAILABLE_RESOLUTIONS[self.resolution_index]
        res_label = self.font.render(
            f"Resolution: {cur_res[0]}x{cur_res[1]}", True, label_color)
        self.screen.blit(res_label, (sw // 2 - res_label.get_width() // 2,
                                     res_y - label_gap))

        # Left/right arrows for resolution
        arrow_color = GOLD_COLOR if is_sel else GRAY
        arrow_y = res_y
        arrow_offset = int(25 * scale)
        # Left arrow
        if self.resolution_index > 0:
            left_arrow = self.font.render("<", True, arrow_color)
            self.screen.blit(left_arrow, (slider_x - arrow_offset,
                                          arrow_y - left_arrow.get_height() // 2))
        # Right arrow
        if self.resolution_index < len(AVAILABLE_RESOLUTIONS) - 1:
            right_arrow = self.font.render(">", True, arrow_color)
            self.screen.blit(right_arrow, (slider_x + slider_w + int(12 * scale),
                                           arrow_y - right_arrow.get_height() // 2))

        # Resolution dots
        for i, (rw, rh) in enumerate(AVAILABLE_RESOLUTIONS):
            rx = slider_x + int(slider_w * i / max(len(AVAILABLE_RESOLUTIONS) - 1, 1))
            is_current = (i == self.resolution_index)
            dot_color = GOLD_COLOR if is_current else (60, 60, 80)
            pygame.draw.circle(self.screen, dot_color, (rx, arrow_y), dot_r)
            if is_current:
                pygame.draw.circle(self.screen, WHITE, (rx, arrow_y), dot_r, 2)

        # Save / Load / Delete button rows
        rows = self._options_rows()
        btn_labels = {"save": "Save Game", "load": "Load Game", "delete": "Delete Save"}
        for row_id in rows:
            if row_id in btn_labels:
                row_idx = rows.index(row_id)
                btn_y = row_start + row_idx * row_gap
                is_sel = (self.pause_slider_sel == row_idx)
                label_color = GOLD_COLOR if is_sel else WHITE
                btn_label = self.font.render(btn_labels[row_id], True, label_color)
                btn_rect = pygame.Rect(
                    sw // 2 - slider_w // 2, btn_y - font_h // 2,
                    slider_w, font_h + int(12 * scale))
                pygame.draw.rect(self.screen, (60, 60, 80), btn_rect, border_radius=6)
                border_color = GOLD_COLOR if is_sel else GRAY
                pygame.draw.rect(self.screen, border_color, btn_rect, 2, border_radius=6)
                self.screen.blit(btn_label,
                                 (btn_rect.centerx - btn_label.get_width() // 2,
                                  btn_rect.centery - btn_label.get_height() // 2))

        # Hints
        if self.controller_connected:
            hint = self.small_font.render(
                "D-pad: navigate  |  A: select  |  B: back", True, GRAY)
        else:
            hint = self.small_font.render(
                "UP/DOWN select  |  LEFT/RIGHT adjust  |  ENTER activate  |  Click",
                True, GRAY)
        self.screen.blit(hint, (sw // 2 - hint.get_width() // 2,
                                int(sh * 0.88)))

        # Back button (sized to fit text)
        back_text = self.font.render("Back", True, WHITE)
        btn_w = max(100, back_text.get_width() + int(32 * scale))
        btn_h = max(35, self.font.get_height() + int(16 * scale))
        back_rect = pygame.Rect(20, 20, btn_w, btn_h)
        pygame.draw.rect(self.screen, (60, 60, 80), back_rect, border_radius=6)
        pygame.draw.rect(self.screen, GRAY, back_rect, 2, border_radius=6)
        self.screen.blit(back_text, (back_rect.centerx - back_text.get_width() // 2,
                                     back_rect.centery - back_text.get_height() // 2))

        if self.controller_connected:
            esc_hint = self.small_font.render("B or Back to go back", True, GRAY)
        else:
            esc_hint = self.small_font.render("ESC to go back", True, GRAY)
        self.screen.blit(esc_hint, (sw // 2 - esc_hint.get_width() // 2,
                                    int(sh * 0.93)))

    def _handle_options_slider_click(self, mx: int, my: int):
        """Handle mouse click on options screen volume sliders and resolution."""
        (sw, sh, scale, slider_w, slider_x, slider_h,
         font_h, label_gap, knob_r, dot_r, row_gap, row_start) = self._options_layout()

        # Music slider
        music_y = row_start
        music_rect = pygame.Rect(slider_x, music_y, slider_w, slider_h)
        if music_rect.collidepoint(mx, my):
            self.pause_slider_sel = 0
            vol = (mx - slider_x) / slider_w
            self.audio.set_music_volume(vol)
            return

        # SFX slider
        sfx_y = row_start + row_gap
        sfx_rect = pygame.Rect(slider_x, sfx_y, slider_w, slider_h)
        if sfx_rect.collidepoint(mx, my):
            self.pause_slider_sel = 1
            vol = (mx - slider_x) / slider_w
            self.audio.set_sfx_volume(vol)
            self.audio.play_sfx("menu_move")
            return

        # Resolution dots
        res_y = row_start + 2 * row_gap
        hit_r = max(12, int(12 * scale))
        for i, (rw, rh) in enumerate(AVAILABLE_RESOLUTIONS):
            rx = slider_x + int(slider_w * i / max(len(AVAILABLE_RESOLUTIONS) - 1, 1))
            if abs(mx - rx) < hit_r and abs(my - res_y) < hit_r:
                self.pause_slider_sel = 2
                if i != self.resolution_index:
                    self._change_resolution(i)
                    self.audio.play_sfx("menu_move")
                return

        # Left/right arrows for resolution
        arrow_y = res_y
        arrow_offset = int(25 * scale)
        arrow_hit = max(25, int(25 * scale))
        left_rect = pygame.Rect(slider_x - arrow_offset - 5,
                                arrow_y - arrow_hit // 2, arrow_hit, arrow_hit)
        right_rect = pygame.Rect(slider_x + slider_w + int(8 * scale),
                                 arrow_y - arrow_hit // 2, arrow_hit, arrow_hit)
        if left_rect.collidepoint(mx, my) and self.resolution_index > 0:
            self.pause_slider_sel = 2
            self._change_resolution(self.resolution_index - 1)
            self.audio.play_sfx("menu_move")
            return
        if (right_rect.collidepoint(mx, my)
                and self.resolution_index < len(AVAILABLE_RESOLUTIONS) - 1):
            self.pause_slider_sel = 2
            self._change_resolution(self.resolution_index + 1)
            self.audio.play_sfx("menu_move")
            return

        # Save / Load / Delete button rows
        rows = self._options_rows()
        btn_ids = {"save", "load", "delete"}
        for row_id in rows:
            if row_id in btn_ids:
                row_idx = rows.index(row_id)
                btn_y = row_start + row_idx * row_gap
                btn_rect = pygame.Rect(
                    sw // 2 - slider_w // 2, btn_y - font_h // 2,
                    slider_w, font_h + int(12 * scale))
                if btn_rect.collidepoint(mx, my):
                    self.pause_slider_sel = row_idx
                    self._activate_options_row(rows)
                    return

    def _change_resolution(self, res_index: int):
        """Change the screen resolution and update all dependent modules."""
        global SCREEN_WIDTH, SCREEN_HEIGHT
        res_index = max(0, min(res_index, len(AVAILABLE_RESOLUTIONS) - 1))
        self.resolution_index = res_index
        w, h = AVAILABLE_RESOLUTIONS[res_index]

        # Update settings module
        settings.SCREEN_WIDTH = w
        settings.SCREEN_HEIGHT = h
        settings.TILES_X = w // TILE_SIZE
        settings.TILES_Y = h // TILE_SIZE

        # Update game.py module-level names
        SCREEN_WIDTH = w
        SCREEN_HEIGHT = h

        # Recreate display
        self.screen = pygame.display.set_mode((w, h))

        # Recreate fonts at new scale
        self._create_fonts()
        self.hud.init_fonts()

        # Recalculate inventory layout
        if self.player and self.player.inventory:
            self.player.inventory._recalc_rect()

        # Recalculate shop layouts
        if self.active_shop:
            self.active_shop._recalc_layout()
        for shop in self.shops.values():
            shop._recalc_layout()

    # ------------------------------------------------------------------
    # Save / Load / Delete dialog helpers
    # ------------------------------------------------------------------

    def _activate_options_row(self, rows):
        """Activate the currently selected options row (save/load/delete)."""
        if self.pause_slider_sel >= len(rows):
            return
        row_id = rows[self.pause_slider_sel]
        # Always return to Options after dialogs opened from the Options screen
        self.dialog_return_state = self.STATE_OPTIONS
        if row_id == "save":
            self.save_slots_cache = list_saves()
            self.dialog_cursor = 0
            self.save_name_editing = False
            self.save_name_input = ""
            self.state = self.STATE_SAVE_DIALOG
            self.audio.play_sfx("menu_accept")
        elif row_id == "load":
            self.save_slots_cache = list_saves()
            self.dialog_cursor = 0
            # Move cursor to first occupied slot
            for i in range(MAX_SAVE_SLOTS):
                if self.save_slots_cache[i]:
                    self.dialog_cursor = i
                    break
            self.state = self.STATE_LOAD_DIALOG
            self.audio.play_sfx("menu_accept")
        elif row_id == "delete":
            self.save_slots_cache = list_saves()
            self.dialog_cursor = 0
            self.delete_confirm = False
            for i in range(MAX_SAVE_SLOTS):
                if self.save_slots_cache[i]:
                    self.dialog_cursor = i
                    break
            self.state = self.STATE_DELETE_DIALOG
            self.audio.play_sfx("menu_accept")

    # ------------------------------------------------------------------
    # Pause menu row activation
    # ------------------------------------------------------------------

    def _activate_pause_row(self):
        """Activate the currently selected pause menu row (rows 2-4 only).

        Row 0 (music) and row 1 (sfx) are handled directly by key/hat handlers.
        """
        row = self.pause_slider_sel
        if row == 2:  # Save Game
            if self.player:
                self.save_slots_cache = list_saves()
                self.dialog_cursor = 0
                self.save_name_editing = False
                self.save_name_input = ""
                self.dialog_return_state = self.STATE_PAUSED
                self.state = self.STATE_SAVE_DIALOG
                self.audio.play_sfx("menu_accept")
        elif row == 3:  # Load Game
            self.save_slots_cache = list_saves()
            self.dialog_cursor = 0
            for i in range(MAX_SAVE_SLOTS):
                if self.save_slots_cache[i]:
                    self.dialog_cursor = i
                    break
            self.dialog_return_state = self.STATE_PAUSED
            self.state = self.STATE_LOAD_DIALOG
            self.audio.play_sfx("menu_accept")
        elif row == 4:  # Return to Menu
            self._exit_to_menu()

    def _exit_to_menu(self):
        """Auto-save current progress and return to the main menu.

        Called from the pause menu 'Return to Menu' row and any other code
        path that exits to the main menu from an active game.
        """
        if self.player:
            # Write an autosave so the player can Resume from the main menu
            state_dict = self._get_game_state_dict()
            if save_autosave(state_dict):
                self.has_autosave = True
        self.menu_button_sel = -1
        self.state = self.STATE_MENU
        self.audio.play_music("menu")

    def _load_from_autosave(self):
        """Load the autosave file and begin playing.

        Called by the Resume button on the main menu.
        """
        save_data = load_autosave()
        if not save_data:
            self.hud.show_message("No autosave found!")
            return

        # Restore game state (mirrors _execute_load)
        self.selected_hero_index = save_data.get("selected_hero_index", 0)
        self.current_stage_num = save_data.get("stage_num", 1)
        self.current_stage_type = save_data.get("stage_type", "combat")
        self.combat_music_index = save_data.get("combat_music_index", 0)
        self.town_music_index = save_data.get("town_music_index", 0)

        # Clear transient game objects
        self.ground_items = pygame.sprite.Group()
        self.gold_drops = pygame.sprite.Group()
        self.projectiles = []
        self.floating_texts = []
        self.spell_effects = []
        self.in_boss_area = False

        # Regenerate stage
        self._load_stage()
        sx, sy = self.stage.player_start

        # Create player
        hero_idx = min(self.selected_hero_index, len(HERO_CHARACTERS) - 1)
        selected_hero = HERO_CHARACTERS[hero_idx]
        self.player = Player(sx, sy, selected_hero)

        # Restore player stats
        self.player.level = save_data.get("level", 1)
        self.player.xp = save_data.get("xp", 0)
        self.player.max_hp = save_data.get("max_hp", self.player.max_hp)
        self.player.hp = save_data.get("hp", self.player.max_hp)
        self.player.gold = save_data.get("gold", 0)
        self.player.base_damage = save_data.get("base_damage", self.player.base_damage)

        # Restore mana
        if self.player.mana_per_level > 0:
            self.player.max_mana = (self.player.mana_base
                                    + (self.player.level - 1) * self.player.mana_per_level)
        self.player.mana = float(save_data.get("mana", self.player.max_mana))

        # Restore grit
        if self.player.grit_per_level > 0:
            self.player.max_grit = (self.player.grit_base
                                    + (self.player.level - 1) * self.player.grit_per_level)
        self.player.grit = float(save_data.get("grit", self.player.max_grit))

        # Restore weapon
        weapon_id = save_data.get("equipped_weapon_id", "")
        if weapon_id and weapon_id in self.weapon_db:
            self.player.equipped_weapon = self.weapon_db[weapon_id]

        # Restore armor
        armor_id = save_data.get("equipped_armor_id", "")
        if armor_id and armor_id in ARMOR_DEFS:
            self.player.equip_armor(armor_id)

        # Restore inventory
        self.player.inventory.slots = [None] * 25
        inv_data = save_data.get("inventory", [])
        for i, slot_data in enumerate(inv_data):
            if i >= 25:
                break
            if slot_data and isinstance(slot_data, dict):
                item_id = slot_data.get("item_id", "")
                quantity = slot_data.get("quantity", 1)
                item = self.item_db.get(item_id)
                if item:
                    from src.item import ItemStack
                    self.player.inventory.slots[i] = ItemStack(item, quantity)

        # Restore buffs
        self.player.buffs = save_data.get("buffs", {})

        # Restore multi-spell system state
        self.player.selected_spell_idx = save_data.get("selected_spell_idx", 0)
        self.player.shield_hp = save_data.get("shield_hp", 0)
        self.player.action_surge_timer = save_data.get("action_surge_timer", 0.0)
        self.player.whirlwind_timer = save_data.get("whirlwind_timer", 0.0)
        self.player.blazing_sword_timer = save_data.get("blazing_sword_timer", 0.0)
        self.player.double_fire_timer = save_data.get("double_fire_timer", 0.0)
        self.last_town_num = save_data.get("last_town_num", 0)

        # Camera and state
        self.camera = Camera(self.stage.width, self.stage.height)
        self.state = self.STATE_PLAYING

        # Delete the autosave now that it's been consumed
        delete_autosave()
        self.has_autosave = False

        # Play appropriate music
        if self.current_stage_type == "combat":
            music = self._next_combat_track()
        else:
            music = self._next_town_track()
        self.audio.play_music(music, loops=0)

        self.hud.show_message("Game resumed!")
        self.audio.play_sfx("menu_accept")

    def _dialog_cursor_next_occupied(self):
        """Move dialog cursor to next occupied save slot."""
        start = self.dialog_cursor
        for i in range(1, MAX_SAVE_SLOTS + 1):
            idx = (start + i) % MAX_SAVE_SLOTS
            if self.save_slots_cache[idx]:
                self.dialog_cursor = idx
                return

    def _dialog_cursor_prev_occupied(self):
        """Move dialog cursor to previous occupied save slot."""
        start = self.dialog_cursor
        for i in range(1, MAX_SAVE_SLOTS + 1):
            idx = (start - i) % MAX_SAVE_SLOTS
            if self.save_slots_cache[idx]:
                self.dialog_cursor = idx
                return

    def _start_save_name_input(self):
        """Begin text input for naming a save."""
        slot = self.dialog_cursor
        existing = self.save_slots_cache[slot]
        self.save_name_input = existing["name"] if existing else f"Save {slot + 1}"
        self.save_name_editing = True
        self.audio.play_sfx("menu_accept")

    def _get_game_state_dict(self) -> dict:
        """Build the full game state dict for saving."""
        inv_data = []
        for slot in self.player.inventory.slots:
            if slot is None:
                inv_data.append(None)
            else:
                inv_data.append({
                    "item_id": slot.item_data.id,
                    "quantity": slot.quantity
                })

        weapon_id = ""
        if self.player.equipped_weapon:
            weapon_id = self.player.equipped_weapon.id

        armor_id = ""
        if self.player.equipped_armor:
            armor_id = self.player.equipped_armor.get("id", "")

        return {
            "hero_id": self.player.hero_id,
            "hero_name": self.player.character,
            "selected_hero_index": self.selected_hero_index,
            "level": self.player.level,
            "xp": self.player.xp,
            "hp": self.player.hp,
            "max_hp": self.player.max_hp,
            "mana": int(self.player.mana),
            "grit": int(self.player.grit),
            "gold": self.player.gold,
            "base_damage": self.player.base_damage,
            "equipped_weapon_id": weapon_id,
            "equipped_armor_id": armor_id,
            "buffs": dict(self.player.buffs),
            "inventory": inv_data,
            "stage_num": self.current_stage_num,
            "stage_type": self.current_stage_type,
            "combat_music_index": self.combat_music_index,
            "town_music_index": self.town_music_index,
            # Multi-spell system state
            "selected_spell_idx": getattr(self.player, 'selected_spell_idx', 0),
            "shield_hp": getattr(self.player, 'shield_hp', 0),
            "action_surge_timer": getattr(self.player, 'action_surge_timer', 0.0),
            "whirlwind_timer": getattr(self.player, 'whirlwind_timer', 0.0),
            "blazing_sword_timer": getattr(self.player, 'blazing_sword_timer', 0.0),
            "double_fire_timer": getattr(self.player, 'double_fire_timer', 0.0),
            "last_town_num": getattr(self, 'last_town_num', 0),
        }

    def _execute_save(self):
        """Save the game to the selected slot."""
        name = self.save_name_input.strip() or f"Save {self.dialog_cursor + 1}"
        state_dict = self._get_game_state_dict()
        success = save_game(self.dialog_cursor, name, state_dict)
        if success:
            self.audio.play_sfx("menu_accept")
            self.hud.show_message("Game saved!")
        else:
            self.audio.play_sfx("alert")
            self.hud.show_message("Save failed!")
        self.save_name_editing = False
        self.save_slots_cache = list_saves()
        self.state = self.dialog_return_state

    def _execute_load(self):
        """Load the game from the selected slot."""
        if not self.save_slots_cache[self.dialog_cursor]:
            self.audio.play_sfx("alert")
            return
        save_data = load_save(self.dialog_cursor)
        if not save_data:
            self.audio.play_sfx("alert")
            self.hud.show_message("Load failed!")
            return

        # Restore game state
        self.selected_hero_index = save_data.get("selected_hero_index", 0)
        self.current_stage_num = save_data.get("stage_num", 1)
        self.current_stage_type = save_data.get("stage_type", "combat")
        self.combat_music_index = save_data.get("combat_music_index", 0)
        self.town_music_index = save_data.get("town_music_index", 0)

        # Regenerate stage
        self._load_stage()
        sx, sy = self.stage.player_start

        # Create player with saved hero
        hero_idx = min(self.selected_hero_index, len(HERO_CHARACTERS) - 1)
        selected_hero = HERO_CHARACTERS[hero_idx]
        self.player = Player(sx, sy, selected_hero)

        # Restore player stats
        self.player.level = save_data.get("level", 1)
        self.player.xp = save_data.get("xp", 0)
        self.player.max_hp = save_data.get("max_hp", self.player.max_hp)
        self.player.hp = save_data.get("hp", self.player.max_hp)
        self.player.gold = save_data.get("gold", 0)
        self.player.base_damage = save_data.get("base_damage",
                                                 self.player.base_damage)

        # Restore mana (recalculate max_mana for current level)
        if self.player.mana_per_level > 0:
            self.player.max_mana = (self.player.mana_base
                                    + (self.player.level - 1) * self.player.mana_per_level)
        self.player.mana = float(save_data.get("mana", self.player.max_mana))

        # Restore grit (recalculate max_grit for current level)
        if self.player.grit_per_level > 0:
            self.player.max_grit = (self.player.grit_base
                                    + (self.player.level - 1) * self.player.grit_per_level)
        self.player.grit = float(save_data.get("grit", self.player.max_grit))

        # Restore weapon
        weapon_id = save_data.get("equipped_weapon_id", "")
        if weapon_id and weapon_id in self.weapon_db:
            self.player.equipped_weapon = self.weapon_db[weapon_id]

        # Restore armor
        armor_id = save_data.get("equipped_armor_id", "")
        if armor_id and armor_id in ARMOR_DEFS:
            self.player.equip_armor(armor_id)

        # Restore inventory
        self.player.inventory.slots = [None] * 25
        inv_data = save_data.get("inventory", [])
        for i, slot_data in enumerate(inv_data):
            if i >= 25:
                break
            if slot_data and isinstance(slot_data, dict):
                item_id = slot_data.get("item_id", "")
                quantity = slot_data.get("quantity", 1)
                item = self.item_db.get(item_id)
                if item:
                    from src.item import ItemStack
                    self.player.inventory.slots[i] = ItemStack(item, quantity)

        # Restore buffs
        self.player.buffs = save_data.get("buffs", {})

        # Restore multi-spell system state
        self.player.selected_spell_idx = save_data.get("selected_spell_idx", 0)
        self.player.shield_hp = save_data.get("shield_hp", 0)
        self.player.action_surge_timer = save_data.get("action_surge_timer", 0.0)
        self.player.whirlwind_timer = save_data.get("whirlwind_timer", 0.0)
        self.player.blazing_sword_timer = save_data.get("blazing_sword_timer", 0.0)
        self.player.double_fire_timer = save_data.get("double_fire_timer", 0.0)
        self.last_town_num = save_data.get("last_town_num", 0)

        # Set up camera and start playing
        self.camera = Camera(self.stage.width, self.stage.height)
        self.state = self.STATE_PLAYING

        # Play appropriate music
        if self.current_stage_type == "combat":
            music = self._next_combat_track()
        else:
            music = self._next_town_track()
        self.audio.play_music(music, loops=0)

        self.hud.show_message("Game loaded!")
        self.audio.play_sfx("menu_accept")

    def _execute_delete(self):
        """Delete the save at the selected slot."""
        delete_save(self.dialog_cursor)
        self.audio.play_sfx("menu_cancel")
        self.hud.show_message("Save deleted.")
        self.delete_confirm = False
        self.save_slots_cache = list_saves()
        # Move cursor to next occupied slot if current was deleted
        if not self.save_slots_cache[self.dialog_cursor]:
            for i in range(MAX_SAVE_SLOTS):
                if self.save_slots_cache[i]:
                    self.dialog_cursor = i
                    break

    def _save_dialog_layout(self):
        """Compute save/load/delete dialog panel dimensions."""
        sw, sh = SCREEN_WIDTH, SCREEN_HEIGHT
        scale = settings.get_font_scale()
        font_h = self.font.get_height()
        panel_w = min(int(500 * scale), sw - 40)
        slot_h = max(int(48 * scale), font_h * 2 + int(8 * scale))
        slot_margin = int(4 * scale)
        title_h = int(45 * scale)
        extra_h = int(70 * scale)   # room for hints / text input below slots
        # Panel height grows with slot count so all 10 rows are visible
        needed_h = title_h + MAX_SAVE_SLOTS * (slot_h + slot_margin) + extra_h
        panel_h = min(needed_h, sh - 40)
        panel_x = (sw - panel_w) // 2
        panel_y = max(10, (sh - panel_h) // 2)
        return (sw, sh, scale, panel_w, panel_h, panel_x, panel_y,
                font_h, slot_h, slot_margin, title_h)

    def _draw_save_dialog(self):
        """Draw the save game dialog overlay."""
        (sw, sh, scale, panel_w, panel_h, panel_x, panel_y,
         font_h, slot_h, slot_margin, title_h) = self._save_dialog_layout()

        # Dark overlay
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))

        # Panel background
        panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)
        pygame.draw.rect(self.screen, (25, 25, 40), panel_rect, border_radius=8)
        pygame.draw.rect(self.screen, GOLD_COLOR, panel_rect, 2, border_radius=8)

        # Title
        title = self.big_font.render("SAVE GAME", True, GOLD_COLOR)
        self.screen.blit(title, (panel_x + panel_w // 2 - title.get_width() // 2,
                                  panel_y + int(8 * scale)))

        # Slot rows
        slots_y = panel_y + title_h
        for i in range(MAX_SAVE_SLOTS):
            sy = slots_y + i * (slot_h + slot_margin)
            slot_rect = pygame.Rect(panel_x + int(10 * scale), sy,
                                     panel_w - int(20 * scale), slot_h)
            is_sel = (i == self.dialog_cursor)

            # Background
            bg_color = (45, 45, 65) if is_sel else (35, 35, 50)
            pygame.draw.rect(self.screen, bg_color, slot_rect, border_radius=4)
            border_color = GOLD_COLOR if is_sel else (60, 60, 80)
            pygame.draw.rect(self.screen, border_color, slot_rect, 2, border_radius=4)

            save = self.save_slots_cache[i]
            if save:
                # Occupied slot
                name_text = self.font.render(save["name"], True, YELLOW)
                self.screen.blit(name_text, (slot_rect.x + int(8 * scale),
                                              slot_rect.y + int(4 * scale)))
                info = f"Lv.{save['level']} {save['hero_name']} | Stage {save['stage_num']} | {save['gold']}g"
                info_text = self.small_font.render(info, True, GRAY)
                self.screen.blit(info_text, (slot_rect.x + int(8 * scale),
                                              slot_rect.y + font_h + int(2 * scale)))
                # Timestamp right-aligned
                ts = self.small_font.render(save["timestamp"], True, (100, 100, 120))
                self.screen.blit(ts, (slot_rect.right - ts.get_width() - int(8 * scale),
                                       slot_rect.y + int(4 * scale)))
            else:
                empty = self.font.render(f"Slot {i + 1} - (Empty)", True, (80, 80, 100))
                self.screen.blit(empty, (slot_rect.x + int(8 * scale),
                                          slot_rect.centery - empty.get_height() // 2))

        # Text input area (below slots)
        input_y = slots_y + MAX_SAVE_SLOTS * (slot_h + slot_margin) + int(6 * scale)
        if self.save_name_editing:
            label = self.font.render("Enter save name:", True, WHITE)
            self.screen.blit(label, (panel_x + int(10 * scale), input_y))
            input_rect = pygame.Rect(panel_x + int(10 * scale),
                                      input_y + font_h + int(4 * scale),
                                      panel_w - int(20 * scale),
                                      font_h + int(10 * scale))
            pygame.draw.rect(self.screen, (20, 20, 35), input_rect, border_radius=4)
            pygame.draw.rect(self.screen, GOLD_COLOR, input_rect, 2, border_radius=4)
            # Text with blinking cursor
            cursor_char = "|" if (pygame.time.get_ticks() // 500) % 2 == 0 else ""
            text_surf = self.font.render(self.save_name_input + cursor_char,
                                          True, WHITE)
            self.screen.blit(text_surf, (input_rect.x + int(6 * scale),
                                          input_rect.centery - text_surf.get_height() // 2))
        else:
            # Hints
            if self.controller_connected:
                hint = self.small_font.render(
                    "D-pad: select slot  |  A: save  |  B: cancel", True, GRAY)
            else:
                hint = self.small_font.render(
                    "UP/DOWN: select slot  |  ENTER: save  |  ESC: cancel",
                    True, GRAY)
            self.screen.blit(hint, (panel_x + panel_w // 2 - hint.get_width() // 2,
                                     input_y))

    def _draw_load_dialog(self):
        """Draw the load game dialog overlay."""
        (sw, sh, scale, panel_w, panel_h, panel_x, panel_y,
         font_h, slot_h, slot_margin, title_h) = self._save_dialog_layout()

        # Dark overlay
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))

        # Panel background
        panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)
        pygame.draw.rect(self.screen, (25, 25, 40), panel_rect, border_radius=8)
        pygame.draw.rect(self.screen, GOLD_COLOR, panel_rect, 2, border_radius=8)

        # Title
        title = self.big_font.render("LOAD GAME", True, GOLD_COLOR)
        self.screen.blit(title, (panel_x + panel_w // 2 - title.get_width() // 2,
                                  panel_y + int(8 * scale)))

        # Slot rows
        slots_y = panel_y + title_h
        any_occupied = any(self.save_slots_cache)
        for i in range(MAX_SAVE_SLOTS):
            sy = slots_y + i * (slot_h + slot_margin)
            slot_rect = pygame.Rect(panel_x + int(10 * scale), sy,
                                     panel_w - int(20 * scale), slot_h)
            save = self.save_slots_cache[i]
            is_sel = (i == self.dialog_cursor) and save is not None

            bg_color = (45, 45, 65) if is_sel else (35, 35, 50)
            pygame.draw.rect(self.screen, bg_color, slot_rect, border_radius=4)
            border_color = GOLD_COLOR if is_sel else (60, 60, 80)
            pygame.draw.rect(self.screen, border_color, slot_rect, 2, border_radius=4)

            if save:
                name_text = self.font.render(save["name"], True, YELLOW)
                self.screen.blit(name_text, (slot_rect.x + int(8 * scale),
                                              slot_rect.y + int(4 * scale)))
                info = f"Lv.{save['level']} {save['hero_name']} | Stage {save['stage_num']} | {save['gold']}g"
                info_text = self.small_font.render(info, True, GRAY)
                self.screen.blit(info_text, (slot_rect.x + int(8 * scale),
                                              slot_rect.y + font_h + int(2 * scale)))
                ts = self.small_font.render(save["timestamp"], True, (100, 100, 120))
                self.screen.blit(ts, (slot_rect.right - ts.get_width() - int(8 * scale),
                                       slot_rect.y + int(4 * scale)))
            else:
                empty = self.font.render(f"Slot {i + 1} - (Empty)", True, (60, 60, 75))
                self.screen.blit(empty, (slot_rect.x + int(8 * scale),
                                          slot_rect.centery - empty.get_height() // 2))

        # Hints
        hint_y = slots_y + MAX_SAVE_SLOTS * (slot_h + slot_margin) + int(6 * scale)
        if not any_occupied:
            msg = self.font.render("No saved games found.", True, GRAY)
            self.screen.blit(msg, (panel_x + panel_w // 2 - msg.get_width() // 2,
                                    hint_y))
        else:
            if self.controller_connected:
                hint = self.small_font.render(
                    "D-pad: select  |  A: load  |  B: cancel", True, GRAY)
            else:
                hint = self.small_font.render(
                    "UP/DOWN: select  |  ENTER: load  |  ESC: cancel",
                    True, GRAY)
            self.screen.blit(hint, (panel_x + panel_w // 2 - hint.get_width() // 2,
                                     hint_y))

    def _draw_delete_dialog(self):
        """Draw the delete save dialog overlay."""
        (sw, sh, scale, panel_w, panel_h, panel_x, panel_y,
         font_h, slot_h, slot_margin, title_h) = self._save_dialog_layout()

        # Dark overlay
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))

        # Panel background
        panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)
        pygame.draw.rect(self.screen, (25, 25, 40), panel_rect, border_radius=8)
        pygame.draw.rect(self.screen, RED, panel_rect, 2, border_radius=8)

        # Title
        title = self.big_font.render("DELETE SAVE", True, RED)
        self.screen.blit(title, (panel_x + panel_w // 2 - title.get_width() // 2,
                                  panel_y + int(8 * scale)))

        # Slot rows
        slots_y = panel_y + title_h
        any_occupied = any(self.save_slots_cache)
        for i in range(MAX_SAVE_SLOTS):
            sy = slots_y + i * (slot_h + slot_margin)
            slot_rect = pygame.Rect(panel_x + int(10 * scale), sy,
                                     panel_w - int(20 * scale), slot_h)
            save = self.save_slots_cache[i]
            is_sel = (i == self.dialog_cursor) and save is not None

            bg_color = (55, 35, 35) if is_sel else (35, 35, 50)
            pygame.draw.rect(self.screen, bg_color, slot_rect, border_radius=4)
            border_color = RED if is_sel else (60, 60, 80)
            pygame.draw.rect(self.screen, border_color, slot_rect, 2, border_radius=4)

            if save:
                name_text = self.font.render(save["name"], True, YELLOW)
                self.screen.blit(name_text, (slot_rect.x + int(8 * scale),
                                              slot_rect.y + int(4 * scale)))
                info = f"Lv.{save['level']} {save['hero_name']} | Stage {save['stage_num']} | {save['gold']}g"
                info_text = self.small_font.render(info, True, GRAY)
                self.screen.blit(info_text, (slot_rect.x + int(8 * scale),
                                              slot_rect.y + font_h + int(2 * scale)))
                ts = self.small_font.render(save["timestamp"], True, (100, 100, 120))
                self.screen.blit(ts, (slot_rect.right - ts.get_width() - int(8 * scale),
                                       slot_rect.y + int(4 * scale)))
            else:
                empty = self.font.render(f"Slot {i + 1} - (Empty)", True, (60, 60, 75))
                self.screen.blit(empty, (slot_rect.x + int(8 * scale),
                                          slot_rect.centery - empty.get_height() // 2))

        # Confirmation or hints
        hint_y = slots_y + MAX_SAVE_SLOTS * (slot_h + slot_margin) + int(6 * scale)
        if self.delete_confirm and self.save_slots_cache[self.dialog_cursor]:
            save_name = self.save_slots_cache[self.dialog_cursor]["name"]
            warn = self.font.render(f'Delete "{save_name}"?', True, RED)
            self.screen.blit(warn, (panel_x + panel_w // 2 - warn.get_width() // 2,
                                     hint_y))
            if self.controller_connected:
                conf = self.small_font.render("A: confirm  |  B: cancel", True, GRAY)
            else:
                conf = self.small_font.render("ENTER: confirm  |  ESC: cancel",
                                               True, GRAY)
            self.screen.blit(conf, (panel_x + panel_w // 2 - conf.get_width() // 2,
                                     hint_y + font_h + int(4 * scale)))
        elif not any_occupied:
            msg = self.font.render("No saved games to delete.", True, GRAY)
            self.screen.blit(msg, (panel_x + panel_w // 2 - msg.get_width() // 2,
                                    hint_y))
        else:
            if self.controller_connected:
                hint = self.small_font.render(
                    "D-pad: select  |  A: delete  |  B: cancel", True, GRAY)
            else:
                hint = self.small_font.render(
                    "UP/DOWN: select  |  ENTER: delete  |  ESC: cancel",
                    True, GRAY)
            self.screen.blit(hint, (panel_x + panel_w // 2 - hint.get_width() // 2,
                                     hint_y))

    def _handle_dialog_click(self, pos):
        """Handle mouse click in save/load/delete dialog."""
        (sw, sh, scale, panel_w, panel_h, panel_x, panel_y,
         font_h, slot_h, slot_margin, title_h) = self._save_dialog_layout()
        mx, my = pos

        # Check if click is outside panel (cancel)
        panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)
        if not panel_rect.collidepoint(mx, my):
            if self.state == self.STATE_SAVE_DIALOG and self.save_name_editing:
                self.save_name_editing = False
            elif self.state == self.STATE_DELETE_DIALOG and self.delete_confirm:
                self.delete_confirm = False
            else:
                self.state = self.dialog_return_state
            self.audio.play_sfx("menu_cancel")
            return

        # Check slot clicks
        slots_y = panel_y + title_h
        for i in range(MAX_SAVE_SLOTS):
            sy = slots_y + i * (slot_h + slot_margin)
            slot_rect = pygame.Rect(panel_x + int(10 * scale), sy,
                                     panel_w - int(20 * scale), slot_h)
            if slot_rect.collidepoint(mx, my):
                if self.state == self.STATE_SAVE_DIALOG:
                    if self.save_name_editing:
                        self.save_name_editing = False
                    self.dialog_cursor = i
                    self._start_save_name_input()
                elif self.state == self.STATE_LOAD_DIALOG:
                    if self.save_slots_cache[i]:
                        self.dialog_cursor = i
                        self._execute_load()
                elif self.state == self.STATE_DELETE_DIALOG:
                    if self.save_slots_cache[i]:
                        if self.dialog_cursor == i and self.delete_confirm:
                            self._execute_delete()
                        else:
                            self.dialog_cursor = i
                            self.delete_confirm = True
                            self.audio.play_sfx("menu_move")
                return

    def _draw_persistent_buffs(self, cam):
        """Draw persistent buff/state visuals on top of entities."""
        import math as _math
        cam_x, cam_y = int(cam[0]), int(cam[1])
        now = pygame.time.get_ticks()
        player = self.player
        px = int(player.world_x) - cam_x
        py = int(player.world_y) - cam_y

        # --- Shield bubble ---
        if player.shield_hp > 0:
            pulse = 0.5 + 0.5 * _math.sin(now * 0.005)
            radius = int(26 + pulse * 4)
            shield_surf = pygame.Surface((radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA)
            center = (radius + 2, radius + 2)
            alpha_outer = int(60 + pulse * 40)
            alpha_ring = int(160 + pulse * 80)
            pygame.draw.circle(shield_surf, (80, 140, 255, alpha_outer), center, radius)
            pygame.draw.circle(shield_surf, (180, 210, 255, alpha_ring), center, radius, 3)
            self.screen.blit(shield_surf, (px - radius - 2, py - radius - 2))

        # --- Whirlwind ring (rotating dots around player) ---
        if player.whirlwind_timer > 0:
            ring_radius = 50
            dot_count = 8
            ring_surf = pygame.Surface(
                (ring_radius * 2 + 8, ring_radius * 2 + 8), pygame.SRCALPHA)
            for i in range(dot_count):
                angle = (now * 0.003 + i * (2 * _math.pi / dot_count)) % (2 * _math.pi)
                dot_x = ring_radius + 4 + int(ring_radius * _math.cos(angle))
                dot_y = ring_radius + 4 + int(ring_radius * _math.sin(angle))
                alpha = int(120 + 120 * _math.sin(now * 0.004 + i))
                pygame.draw.circle(ring_surf, (255, 180, 40, max(30, alpha)), (dot_x, dot_y), 4)
            self.screen.blit(ring_surf, (px - ring_radius - 4, py - ring_radius - 4))

        # --- Blazing Sword flames (animated polygons along weapon facing direction) ---
        if player.blazing_sword_timer > 0:
            from src.settings import DIR_DOWN, DIR_LEFT, DIR_RIGHT, DIR_UP
            _dir_vecs = {
                DIR_DOWN: (0, 1), DIR_LEFT: (-1, 0),
                DIR_RIGHT: (1, 0), DIR_UP: (0, -1),
            }
            fdx, fdy = _dir_vecs.get(player.facing, (0, 1))
            # Perpendicular axis for flame width
            perp_x, perp_y = -fdy, fdx
            flame_len = 100  # matches range_bonus
            blaze_surf = pygame.Surface(
                (settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT), pygame.SRCALPHA)
            # Draw 6 flame tongues along the weapon direction
            num_tongues = 6
            for fi in range(num_tongues):
                phase = now * 0.006 + fi * 1.05
                flicker = 0.65 + 0.35 * _math.sin(phase)
                t = fi / num_tongues  # 0.0 (near player) to ~0.83
                # Base of this tongue along weapon axis
                bx = px + int(fdx * flame_len * t * 0.9)
                by = py + int(fdy * flame_len * t * 0.9)
                # Tip length shrinks toward the end of the blade
                tip_dist = int(flame_len * (0.38 + 0.22 * (1.0 - t)) * flicker)
                tip_x = bx + int(fdx * tip_dist)
                tip_y = by + int(fdy * tip_dist)
                # Half-width of flame base shrinks toward tip of blade
                half_w = max(2, int((11 - t * 7) * flicker))
                # Three nested layers: outer deep-red, mid orange, inner yellow
                for flame_rgb, w_mult, alpha in [
                    ((255, 55,  0),  1.00, 170),
                    ((255, 145, 20), 0.60, 200),
                    ((255, 235, 70), 0.28, 230),
                ]:
                    hw = max(1, int(half_w * w_mult))
                    pts = [
                        (bx + int(perp_x * hw), by + int(perp_y * hw)),
                        (bx - int(perp_x * hw), by - int(perp_y * hw)),
                        (tip_x, tip_y),
                    ]
                    pygame.draw.polygon(blaze_surf, (*flame_rgb, alpha), pts)
            # Bright core line along full flame length
            core_pulse = int(180 + 60 * _math.sin(now * 0.01))
            pygame.draw.line(blaze_surf, (255, 255, 180, core_pulse),
                             (px, py),
                             (px + int(fdx * flame_len), py + int(fdy * flame_len)), 2)
            self.screen.blit(blaze_surf, (0, 0))

        # --- Action Surge glow (speed lines around player) ---
        if player.action_surge_timer > 0:
            pulse3 = 0.5 + 0.5 * _math.sin(now * 0.01)
            glow_r = int(20 + pulse3 * 6)
            glow_surf = pygame.Surface((glow_r * 2 + 4, glow_r * 2 + 4), pygame.SRCALPHA)
            center_g = (glow_r + 2, glow_r + 2)
            pygame.draw.circle(glow_surf, (255, 200, 50, int(80 + pulse3 * 60)),
                               center_g, glow_r)
            pygame.draw.circle(glow_surf, (255, 240, 150, int(180 + pulse3 * 60)),
                               center_g, glow_r, 2)
            self.screen.blit(glow_surf, (px - glow_r - 2, py - glow_r - 2))

        # --- Prison cages and polymorph indicators per monster ---
        for monster in self.stage.monsters:
            if not monster.is_alive:
                continue
            mx = int(monster.world_x) - cam_x
            my = int(monster.world_y) - cam_y

            # Prison cage bars
            if getattr(monster, 'is_imprisoned', False):
                cage_w, cage_h = 30, 36
                cage_surf = pygame.Surface((cage_w + 4, cage_h + 4), pygame.SRCALPHA)
                bar_color = (120, 80, 40, 200)
                bar_alpha = int(160 + 80 * _math.sin(now * 0.004))
                bar_color = (120, 80, 40, bar_alpha)
                # Horizontal bars
                for bar_y in [4, cage_h // 2 + 2, cage_h]:
                    pygame.draw.line(cage_surf, bar_color, (2, bar_y), (cage_w + 2, bar_y), 2)
                # Vertical bars
                for bar_x in [2, cage_w // 3 + 2, 2 * cage_w // 3 + 2, cage_w + 2]:
                    pygame.draw.line(cage_surf, bar_color, (bar_x, 4), (bar_x, cage_h), 2)
                self.screen.blit(cage_surf, (mx - cage_w // 2 - 2, my - cage_h - 2))

            # Polymorph purple glow
            elif getattr(monster, 'is_polymorphed', False):
                poly_surf = pygame.Surface((40, 40), pygame.SRCALPHA)
                pulse_p = 0.5 + 0.5 * _math.sin(now * 0.005)
                alpha_p = int(80 + pulse_p * 80)
                pygame.draw.circle(poly_surf, (180, 60, 220, alpha_p), (20, 20), 18, 3)
                self.screen.blit(poly_surf, (mx - 20, my - 20))

            # Trap indicator (orange glow)
            elif getattr(monster, 'is_trapped', False):
                trap_surf = pygame.Surface((36, 36), pygame.SRCALPHA)
                pulse_t = 0.5 + 0.5 * _math.sin(now * 0.007)
                alpha_t = int(100 + pulse_t * 80)
                pygame.draw.circle(trap_surf, (255, 140, 0, alpha_t), (18, 18), 16, 3)
                self.screen.blit(trap_surf, (mx - 18, my - 18))

            # Darkened indicator (dark blue pulse)
            elif getattr(monster, 'is_darkened', False):
                dark_surf = pygame.Surface((36, 36), pygame.SRCALPHA)
                pulse_d = 0.5 + 0.5 * _math.sin(now * 0.003)
                alpha_d = int(60 + pulse_d * 80)
                pygame.draw.circle(dark_surf, (30, 30, 120, alpha_d), (18, 18), 16, 3)
                self.screen.blit(dark_surf, (mx - 18, my - 18))

    def _draw_game(self):
        """Draw the game world."""
        self.hud.controller_connected = self.controller_connected
        cam = (self.camera.x, self.camera.y)

        # Ground layer
        self.stage.draw_ground(self.screen, cam)

        # Exit portal (below objects)
        self.stage.draw_exit(self.screen, cam)

        # Object layer
        self.stage.draw_objects(self.screen, cam)

        # Treasure chests
        for chest in self.stage.chests:
            chest.draw(self.screen, cam)

        # Ground items and gold
        for item in self.ground_items:
            item.draw(self.screen, cam)
        for gold in self.gold_drops:
            gold.draw(self.screen, cam)

        # Projectiles
        for proj in self.projectiles:
            proj.draw(self.screen, cam)

        # Entity layer (y-sorted)
        entities = []
        entities.append(self.player)
        for m in self.stage.monsters:
            entities.append(m)
        for n in self.stage.npcs:
            entities.append(n)

        # Sort by y position for depth
        entities.sort(key=lambda e: e.world_y)

        for entity in entities:
            entity.draw(self.screen, cam)

        # Floating damage numbers
        for ft in self.floating_texts:
            ft.draw(self.screen, cam, self.font)

        # Spell visual effects
        for se in self.spell_effects:
            se.draw(self.screen, cam)

        # Persistent buff/state visuals (shield, whirlwind, blazing sword, etc.)
        self._draw_persistent_buffs(cam)

        # Boss area indicator
        if (self.stage.stage_type == "combat" and self.stage.boss_area
                and not self.stage.boss_defeated):
            ba = self.stage.boss_area
            screen_rect = pygame.Rect(
                ba.x - int(cam[0]), ba.y - int(cam[1]), ba.width, ba.height)
            pygame.draw.rect(self.screen, (200, 50, 50, 100), screen_rect, 2)

        # HUD
        self.hud.current_fps = self.clock.get_fps()
        self.hud.draw(self.screen, self.player)

        # Stage info
        stage_text = self.small_font.render(
            f"Stage {self.current_stage_num} "
            f"({'Town' if self.current_stage_type == 'town' else 'Combat'})",
            True, WHITE)
        self.screen.blit(stage_text, (SCREEN_WIDTH - stage_text.get_width() - 10, 10))

        # Mini-map
        self.hud.draw_minimap(self.screen, self.stage, self.player)

    def _pause_layout(self):
        """Compute pause screen layout values (shared by draw and click handler).

        Pause rows: 0=music slider, 1=sfx slider, 2=Save, 3=Load, 4=Return to Menu.
        Rows 0-1 are sliders; rows 2-4 are selectable buttons.
        """
        sw, sh = SCREEN_WIDTH, SCREEN_HEIGHT
        scale = settings.get_font_scale()
        slider_w = min(int(220 * scale), sw - 80)
        slider_x = sw // 2 - slider_w // 2
        slider_h = max(12, int(14 * scale))
        font_h = self.font.get_height()
        label_gap = font_h + int(6 * scale)
        knob_r = max(8, int(9 * scale))
        # Tighter row gap to fit 5 rows between title (0.25 sh) and bottom
        row_gap = label_gap + slider_h + max(12, int(18 * scale))
        row_start = int(sh * 0.36)
        return (sw, sh, scale, slider_w, slider_x, slider_h,
                font_h, label_gap, knob_r, row_gap, row_start)

    def _handle_pause_click(self, pos):
        """Handle mouse click on pause screen rows (sliders or buttons)."""
        mx, my = pos
        (sw, sh, scale, slider_w, slider_x, slider_h,
         font_h, label_gap, knob_r, row_gap, row_start) = self._pause_layout()

        # Rows 0-1: volume sliders
        for idx in range(2):
            sy = row_start + idx * row_gap
            rect = pygame.Rect(slider_x, sy, slider_w, slider_h)
            if rect.collidepoint(mx, my):
                self.pause_slider_sel = idx
                vol = max(0.0, min(1.0, (mx - slider_x) / slider_w))
                if idx == 0:
                    self.audio.set_music_volume(vol)
                else:
                    self.audio.set_sfx_volume(vol)
                    self.audio.play_sfx("menu_move")
                return

        # Rows 2-4: button rows (Save, Load, Return to Menu)
        btn_h = font_h + int(12 * scale)
        for idx in range(2, 5):
            sy = row_start + idx * row_gap
            btn_rect = pygame.Rect(slider_x, sy - btn_h // 2,
                                   slider_w, btn_h)
            if btn_rect.collidepoint(mx, my):
                self.pause_slider_sel = idx
                self._activate_pause_row()
                return

    def _draw_pause(self):
        """Draw the pause overlay with volume sliders and action buttons."""
        (sw, sh, scale, slider_w, slider_x, slider_h,
         font_h, label_gap, knob_r, row_gap, row_start) = self._pause_layout()
        cx = sw // 2
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))

        title = self.big_font.render("PAUSED", True, WHITE)
        self.screen.blit(title, (cx - title.get_width() // 2, int(sh * 0.18)))

        # ── Rows 0-1: Volume sliders ──────────────────────────────────────────
        for idx, (label, volume) in enumerate([
            ("Music", self.audio.music_volume),
            ("SFX", self.audio.sfx_volume),
        ]):
            sy = row_start + idx * row_gap
            is_sel = (idx == self.pause_slider_sel)
            label_color = GOLD_COLOR if is_sel else WHITE
            lbl = self.font.render(f"{label}: {int(volume * 100)}%", True, label_color)
            self.screen.blit(lbl, (cx - lbl.get_width() // 2, sy - label_gap))

            # Slider track
            track_rect = pygame.Rect(slider_x, sy, slider_w, slider_h)
            pygame.draw.rect(self.screen, (60, 60, 80), track_rect, border_radius=6)
            pygame.draw.rect(self.screen, GRAY, track_rect, 1, border_radius=6)

            # Slider fill
            fill_w = int(slider_w * volume)
            if fill_w > 0:
                fill_rect = pygame.Rect(slider_x, sy, fill_w, slider_h)
                fill_color = GOLD_COLOR if is_sel else (100, 180, 100)
                pygame.draw.rect(self.screen, fill_color, fill_rect, border_radius=6)

            # Slider knob
            knob_x = slider_x + fill_w
            pygame.draw.circle(self.screen, WHITE, (knob_x, sy + slider_h // 2), knob_r)
            if is_sel:
                pygame.draw.circle(self.screen, GOLD_COLOR,
                                   (knob_x, sy + slider_h // 2), knob_r, 2)

        # ── Rows 2-4: Action buttons ──────────────────────────────────────────
        btn_labels = ["Save Game", "Load Game", "Return to Menu"]
        btn_h = font_h + int(12 * scale)
        for i, label in enumerate(btn_labels):
            idx = i + 2  # row index
            sy = row_start + idx * row_gap
            is_sel = (idx == self.pause_slider_sel)
            btn_rect = pygame.Rect(slider_x, sy - btn_h // 2, slider_w, btn_h)

            # Button background
            if is_sel:
                pygame.draw.rect(self.screen, (70, 60, 20), btn_rect, border_radius=6)
                pygame.draw.rect(self.screen, GOLD_COLOR, btn_rect, 2, border_radius=6)
            else:
                pygame.draw.rect(self.screen, (40, 40, 55), btn_rect, border_radius=6)
                pygame.draw.rect(self.screen, GRAY, btn_rect, 1, border_radius=6)

            btn_surf = self.font.render(label, True, GOLD_COLOR if is_sel else WHITE)
            self.screen.blit(btn_surf, (cx - btn_surf.get_width() // 2,
                                        sy - btn_surf.get_height() // 2))

        # ── Bottom hint ───────────────────────────────────────────────────────
        if self.controller_connected:
            hint = self.small_font.render(
                "START: resume  |  D-pad: navigate  |  A: confirm  |  "
                "LEFT/RIGHT: adjust volume", True, GRAY)
        else:
            hint = self.small_font.render(
                "ESC: resume  |  UP/DOWN: navigate  |  ENTER: confirm  |  "
                "LEFT/RIGHT: adjust volume", True, GRAY)
        self.screen.blit(hint, (cx - hint.get_width() // 2, sh - hint.get_height() - int(16 * scale)))

    def _draw_game_over(self):
        sw, sh = SCREEN_WIDTH, SCREEN_HEIGHT
        cx = sw // 2
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((100, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))

        title = self.big_font.render("GAME OVER", True, RED)
        self.screen.blit(title, (cx - title.get_width() // 2, int(sh * 0.35)))

        stats = self.font.render(
            f"Level {self.player.level} | Gold: {self.player.gold} | "
            f"Stage {self.current_stage_num}", True, WHITE)
        self.screen.blit(stats, (cx - stats.get_width() // 2, int(sh * 0.48)))

        if self.controller_connected:
            hint = self.font.render("Press A or START to return to menu", True, GRAY)
        else:
            hint = self.font.render("Press ENTER to return to menu", True, GRAY)
        self.screen.blit(hint, (cx - hint.get_width() // 2, int(sh * 0.56)))

    def _draw_win(self):
        sw, sh = SCREEN_WIDTH, SCREEN_HEIGHT
        cx = sw // 2
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((0, 50, 100, 150))
        self.screen.blit(overlay, (0, 0))

        title = self.big_font.render("VICTORY!", True, GOLD_COLOR)
        self.screen.blit(title, (cx - title.get_width() // 2, int(sh * 0.30)))

        sub = self.font.render("You have conquered all 10 stages!", True, WHITE)
        self.screen.blit(sub, (cx - sub.get_width() // 2, int(sh * 0.42)))

        stats = self.font.render(
            f"Final Level: {self.player.level} | Gold: {self.player.gold}",
            True, YELLOW)
        self.screen.blit(stats, (cx - stats.get_width() // 2, int(sh * 0.50)))

        if self.controller_connected:
            hint = self.font.render("Press A or START to return to menu", True, GRAY)
        else:
            hint = self.font.render("Press ENTER to return to menu", True, GRAY)
        self.screen.blit(hint, (cx - hint.get_width() // 2, int(sh * 0.58)))

    def _draw_overlay_messages(self):
        """Draw HUD messages on top of inventory/shop overlays so feedback is visible."""
        if not self.hud.font:
            self.hud.init_fonts()
        for text, timer in self.hud.messages:
            alpha = min(1.0, timer) * 255
            msg = self.big_font.render(text, True, YELLOW)
            msg.set_alpha(int(alpha))
            self.screen.blit(msg, (SCREEN_WIDTH // 2 - msg.get_width() // 2, 60))
