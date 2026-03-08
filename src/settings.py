import os
import pygame

# Display
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1200
FPS = 60
TITLE = "Monster World"

# Available resolutions for the Options screen
AVAILABLE_RESOLUTIONS = [
    (800, 600), (960, 548), (1024, 768), (1280, 720), (1280, 1024),
    (1366, 768), (1600, 900), (1600, 1200), (1680, 1050),
    (1920, 1080), (1920, 1200), (2560, 1440),
]

# Font scaling — base resolution is 1024x768; fonts scale proportionally
FONT_BASE_HEIGHT = 768

def get_font_scale() -> float:
    """Return a multiplier for font sizes based on current resolution height."""
    return SCREEN_HEIGHT / FONT_BASE_HEIGHT

def scaled_font_size(base_size: int) -> int:
    """Return a font size scaled for the current resolution."""
    return max(12, int(base_size * get_font_scale()))

def scaled_slot_size() -> int:
    """Return inventory slot size scaled for current resolution."""
    return max(32, int(INVENTORY_SLOT_SIZE * get_font_scale()))

def scaled_padding() -> int:
    """Return inventory padding scaled for current resolution."""
    return max(2, int(INVENTORY_PADDING * get_font_scale()))

# Tile
BASE_TILE_SIZE = 16
SCALE_FACTOR = 3
TILE_SIZE = BASE_TILE_SIZE * SCALE_FACTOR  # 48

# Viewport in tiles
TILES_X = SCREEN_WIDTH // TILE_SIZE   # 20
TILES_Y = SCREEN_HEIGHT // TILE_SIZE  # 15

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
GRAY = (128, 128, 128)
DARK_GRAY = (64, 64, 64)
UI_BG = (20, 20, 30, 200)
UI_BORDER = (120, 100, 80)
UI_SLOT_BG = (40, 40, 50)
UI_SLOT_HOVER = (70, 70, 90)
HP_BAR_RED = (200, 40, 40)
HP_BAR_GREEN = (40, 200, 40)
XP_BAR_BLUE = (40, 100, 220)
GOLD_COLOR = (255, 215, 0)
MANA_BAR_GREEN = (50, 200, 100)

# Ground colors per theme (slight variants for visual noise)
GROUND_COLORS = {
    "forest": [(74, 152, 58), (68, 140, 52), (80, 160, 64), (72, 148, 56)],
    "desert": [(210, 180, 120), (205, 175, 115), (215, 185, 125), (208, 178, 118)],
    "dungeon": [(90, 85, 80), (85, 80, 75), (95, 90, 85), (88, 83, 78)],
    "interior": [(139, 115, 85), (145, 120, 90), (133, 110, 80), (141, 117, 87)],
}
PATH_COLORS = {
    "forest": [(170, 130, 80), (165, 125, 75)],
    "desert": [(180, 160, 100), (175, 155, 95)],
    "dungeon": [(60, 55, 50), (65, 60, 55)],
    "interior": [(100, 85, 65), (105, 88, 68)],
}

# ---------------------------------------------------------------------------
# Asset paths — ALL under newassets/
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NEWASSETS_PATH = os.path.join(BASE_DIR, "newassets")

# Characters (TimeFantasy individual frames)
CHARS_PATH = os.path.join(NEWASSETS_PATH, "timefantasy_characters")
CHARS_FRAMES_PATH = os.path.join(CHARS_PATH, "frames")
CHARS_SHEETS_PATH = os.path.join(CHARS_PATH, "sheets")

# Tilesets
TILESETS_PATH = os.path.join(NEWASSETS_PATH, "TimeFantasy_TILES_6.24.17", "TILESETS")

# Audio
SOUNDS_PATH = os.path.join(NEWASSETS_PATH, "Sounds")
MUSIC_PATH = os.path.join(NEWASSETS_PATH, "Fantasy RPG Complete OST",
                          "Fantasy RPG Complete OST- VHCMusic")

# Data
DATA_PATH = os.path.join(BASE_DIR, "data")
SAVES_PATH = os.path.join(BASE_DIR, "saves")

# Sprite directions (row order in sprite sheets)
DIR_DOWN = 0
DIR_LEFT = 1
DIR_RIGHT = 2
DIR_UP = 3

# Direction name mapping for frame file loading
DIR_NAMES = {DIR_DOWN: "down", DIR_LEFT: "left", DIR_RIGHT: "right", DIR_UP: "up"}

# Animation
ANIM_SPEED = 0.15  # Seconds per frame

# Player
PLAYER_SPEED = 200.0
PLAYER_BASE_HP = 100
PLAYER_HP_PER_LEVEL = 20
PLAYER_BASE_DAMAGE = 10
PLAYER_DAMAGE_PER_LEVEL = 2
PLAYER_PICKUP_RANGE = 60
PLAYER_START_LEVEL = 1

# XP thresholds: XP_THRESHOLDS[level] = total XP needed to reach that level
XP_THRESHOLDS = [0, 0, 100, 250, 500, 800, 1200, 1700, 2300, 3000, 4000,
                 5500, 7500, 10000, 15000, 20000, 30000, 45000, 65000, 100000, 150000]
# index 20 = level 20 (max level)

# ---------------------------------------------------------------------------
# Hero characters available for selection on the main menu
# sprite_dir: subdirectory name under frames/chara/
# ---------------------------------------------------------------------------
HERO_CHARACTERS = [
    {"id": "warrior", "name": "Warrior", "sprite_dir": "chara2_1",
     "starting_weapon": "basic_sword",
     "mana_base": 0, "mana_per_level": 0,
     "grit_base": 50, "grit_per_level": 10, "grit_regen": 0.5,
     "xp_required_mult": 0.667,
     "desc": "Melee fighter. High HP, wields a sword. 50 Grit, Lunge (Q)."},
    {"id": "mage", "name": "Mage", "sprite_dir": "chara3_1",
     "hp_mult": 0.7, "starting_weapon": "mage_bolt",
     "mana_base": 50, "mana_per_level": 10, "mana_regen": 0.5,
     "desc": "Ranged caster. Low HP, fires magic bolts. 50 Mana, Light Beam spell (Q)."},
    {"id": "ranger", "name": "Ranger", "sprite_dir": "chara4_1",
     "hp_mult": 0.8, "starting_weapon": "crossbow",
     "mana_base": 0, "mana_per_level": 0,
     "grit_base": 25, "grit_per_level": 5, "grit_regen": 0.333,
     "xp_required_mult": 0.667,
     "desc": "Ranged marksman. Medium HP, wields a crossbow. 25 Grit, Homing Arrow (Q)."},
    {"id": "paladin", "name": "Paladin", "sprite_dir": "chara5_1",
     "hp_mult": 1.2,
     "mana_base": 25, "mana_per_level": 5, "mana_regen": 0.333,
     "desc": "Balanced fighter. High HP, wields a basic sword. 25 Mana, Holy Smite spell (Q)."},
]
DEFAULT_HERO_INDEX = 0

# ---------------------------------------------------------------------------
# Monster base stats
# ---------------------------------------------------------------------------
MONSTER_STATS = {
    "wild_cat":  {"hp": 15,  "damage": 5,  "speed": 90, "xp": 12,  "attack_interval": 2.0, "attack_range": 55},
    "wild_dog":  {"hp": 25,  "damage": 10, "speed": 80, "xp": 20,  "attack_interval": 1.8, "attack_range": 60},
    "bandit":    {"hp": 40,  "damage": 12, "speed": 70, "xp": 35,  "attack_interval": 1.5, "attack_range": 65},
    "soldier":   {"hp": 55,  "damage": 18, "speed": 65, "xp": 50,  "attack_interval": 1.3, "attack_range": 65},
    "guard":     {"hp": 75,  "damage": 22, "speed": 60, "xp": 70,  "attack_interval": 1.2, "attack_range": 70},
    "commander": {"hp": 120, "damage": 28, "speed": 55, "xp": 100, "attack_interval": 1.0, "attack_range": 75},
}

# ---------------------------------------------------------------------------
# Armor definitions
# ---------------------------------------------------------------------------
ARMOR_DEFS = {
    "leather":     {"name": "Leather Armor", "defense": 2,  "value": 40,  "classes": ["warrior", "paladin", "mage", "ranger"], "description": "Light protection. Any class."},
    "padded":      {"name": "Padded Armor",  "defense": 4,  "value": 100, "classes": ["warrior", "paladin", "mage", "ranger"], "description": "Padded cloth. Any class."},
    "chain_shirt": {"name": "Chain Shirt",   "defense": 6,  "value": 200, "classes": ["warrior", "paladin"],                   "description": "Metal rings. Warrior/Paladin only."},
    "chain_mail":  {"name": "Chain Mail",    "defense": 8,  "value": 350, "classes": ["warrior", "paladin"],                   "description": "Full chain. Warrior/Paladin only."},
    "half_plate":  {"name": "Half Plate",    "defense": 10, "value": 550, "classes": ["warrior", "paladin"],                   "description": "Thick plates. Warrior/Paladin only."},
    "full_plate":  {"name": "Full Plate",    "defense": 12, "value": 900, "classes": ["warrior", "paladin"],                   "description": "Maximum defense. Warrior/Paladin only."},
}

# ---------------------------------------------------------------------------
# Grit ability definitions (Warrior and Ranger) — list per hero, min_level gated
# ---------------------------------------------------------------------------
GRIT_ABILITIES = {
    "warrior": [
        {"id": "lunge",          "name": "Lunge",                      "min_level": 1,  "grit_cost": 20,  "cooldown": 2.0,  "type": "lunge",         "damage_mult": 2.0, "range_bonus": 100,
         "description": "Cone AoE strike: 2x damage, extended range."},
        {"id": "second_wind",    "name": "Second Wind",                 "min_level": 3,  "grit_cost": 50,  "cooldown": 30.0, "type": "heal",          "heal": 50,
         "description": "Instantly heal 50 HP."},
        {"id": "action_surge",   "name": "Action Surge",                "min_level": 5,  "grit_cost": 60,  "cooldown": 45.0, "type": "action_surge",  "duration": 30.0,
         "description": "2x movement speed, attack speed, and damage for 30s."},
        {"id": "steel_skin",     "name": "Steel Skin",                  "min_level": 7,  "grit_cost": 70,  "cooldown": 30.0, "type": "shield",        "shield_hp": 100, "duration": 30.0,
         "description": "Absorb up to 100 points of damage."},
        {"id": "whirlwind",      "name": "Whirlwind",                   "min_level": 9,  "grit_cost": 80,  "cooldown": 30.0, "type": "whirlwind",     "range": 50, "duration": 30.0,
         "description": "Attack all nearby enemies (50px) for 30s."},
        {"id": "blazing_sword",  "name": "Blazing Sword",               "min_level": 11, "grit_cost": 90,  "cooldown": 30.0, "type": "blazing_sword", "range_bonus": 100, "duration": 30.0,
         "description": "Sword range +100px with flame visual for 30s."},
        {"id": "wind_surge",     "name": "Second Wind + Action Surge",  "min_level": 13, "grit_cost": 100, "cooldown": 45.0, "type": "combo",         "combo": ["second_wind", "action_surge"],
         "description": "Heal 50 HP and activate Action Surge simultaneously."},
        {"id": "surge_skin",     "name": "Action Surge + Steel Skin",   "min_level": 15, "grit_cost": 110, "cooldown": 45.0, "type": "combo",         "combo": ["action_surge", "steel_skin"],
         "description": "Activate Action Surge and Steel Skin simultaneously."},
        {"id": "skin_wind",      "name": "Steel Skin + Whirlwind",      "min_level": 17, "grit_cost": 120, "cooldown": 30.0, "type": "combo",         "combo": ["steel_skin", "whirlwind"],
         "description": "Activate Steel Skin and Whirlwind simultaneously."},
        {"id": "wind_blaze",     "name": "Whirlwind + Blazing Sword",   "min_level": 19, "grit_cost": 130, "cooldown": 30.0, "type": "combo",         "combo": ["whirlwind", "blazing_sword"],
         "description": "Activate Whirlwind and Blazing Sword simultaneously."},
        {"id": "blazing_resurrect", "name": "Blazing Resurrect",        "min_level": 20, "grit_cost": 140, "cooldown": 0.0,  "type": "resurrection",  "auto_trigger": True,
         "resurrect_aoe_damage_mult": 4, "resurrect_aoe_range": 220,
         "description": "Auto: rise from death dealing 4x weapon damage in 220px radius."},
    ],
    "ranger": [
        {"id": "homing_arrow",      "name": "Homing Arrow",       "min_level": 1,  "grit_cost": 15, "cooldown": 3.0,  "type": "homing_arrow",   "homing_range": 220,
         "description": "Fire an arrow that homes to the nearest enemy."},
        {"id": "double_fire",       "name": "Double Fire",         "min_level": 5,  "grit_cost": 40, "cooldown": 30.0, "type": "double_fire",    "duration": 30.0,
         "description": "Fire 2 homing shots per attack for 30s."},
        {"id": "trap_monster",      "name": "Trap Monster",        "min_level": 9,  "grit_cost": 50, "cooldown": 20.0, "type": "trap",           "duration": 30.0,
         "description": "Stop the nearest pursuing monster for 30s."},
        {"id": "cover_of_darkness", "name": "Cover of Darkness",   "min_level": 13, "grit_cost": 60, "cooldown": 30.0, "type": "cover_darkness", "duration": 30.0,
         "description": "All pursuing monsters stop chasing for 30s."},
        {"id": "third_wind",        "name": "Third Wind",          "min_level": 17, "grit_cost": 70, "cooldown": 30.0, "type": "heal_full",
         "description": "Instantly restore all HP."},
        {"id": "bestial_resurrect", "name": "Bestial Resurrect",   "min_level": 20, "grit_cost": 80, "cooldown": 0.0,  "type": "resurrection",  "auto_trigger": True,
         "description": "Auto: rise from death with full HP."},
    ],
}

# HUD color for grit bar
GRIT_BAR_COLOR = (180, 120, 40)  # Amber/orange

# Polymorph type downgrade chain (each type → the one to its left)
POLYMORPH_PROGRESSION = ["wild_cat", "wild_dog", "bandit", "soldier", "guard", "commander"]

# ---------------------------------------------------------------------------
# Spell definitions — list per hero, min_level gated
# ---------------------------------------------------------------------------
SPELL_DEFS = {
    "mage": [
        {"id": "light_beam",          "name": "Light Beam",         "min_level": 1,  "mana_cost": 10,  "cooldown": 1.0,  "type": "beam",           "damage": 30,  "range": 220,
         "description": "Beam of light in facing direction, hits all enemies in path."},
        {"id": "shield",              "name": "Shield",             "min_level": 3,  "mana_cost": 30,  "cooldown": 15.0, "type": "shield",          "shield_hp": 100,
         "description": "Absorb up to 100 points of damage. Disappears when depleted."},
        {"id": "fireball",            "name": "Fireball",           "min_level": 5,  "mana_cost": 50,  "cooldown": 3.0,  "type": "fireball",        "damage": 150, "range": 300, "explosion_radius": 200,
         "description": "Launches a fireball that explodes on impact (200px radius, 150 dmg)."},
        {"id": "magic_missile",       "name": "Magic Missile",      "min_level": 7,  "mana_cost": 75,  "cooldown": 4.0,  "type": "magic_missile",   "damage": 50,  "mote_count": 4,
         "description": "4 motes of light home to 4 different enemies, 50 damage each."},
        {"id": "polymorph",           "name": "Polymorph",          "min_level": 9,  "mana_cost": 100, "cooldown": 8.0,  "type": "polymorph",       "duration": 30.0,
         "description": "Transform nearest monster into a weaker type for 30s."},
        {"id": "lightning_bolt",      "name": "Lightning Bolt",     "min_level": 11, "mana_cost": 125, "cooldown": 3.0,  "type": "beam",            "damage": 300, "range": 600,
         "description": "Lightning bolt 600px long, damages all enemies in its path for 300."},
        {"id": "double_light_beam",   "name": "Double Light Beam",  "min_level": 13, "mana_cost": 150, "cooldown": 2.0,  "type": "double_beam",     "damage": 150, "range": 220,
         "description": "Two beams of light: facing direction + opposite. 150 dmg, 220px each."},
        {"id": "portal",              "name": "Portal",             "min_level": 15, "mana_cost": 175, "cooldown": 60.0, "type": "portal",
         "description": "Teleport to the last visited town stage."},
        {"id": "safespace",           "name": "Safe Space",         "min_level": 17, "mana_cost": 200, "cooldown": 30.0, "type": "safespace",
         "description": "Teleport to a safe random spot; all pursuing enemies break off."},
        {"id": "prison",              "name": "Prison",             "min_level": 19, "mana_cost": 225, "cooldown": 20.0, "type": "prison",          "duration": 30.0,
         "description": "Cage the nearest pursuing monster for 30s."},
        {"id": "arcane_resurrection", "name": "Arcane Resurrection","min_level": 20, "mana_cost": 250, "cooldown": 0.0,  "type": "resurrection",    "auto_trigger": True,
         "description": "Auto: upon death, resurrect in the last visited town (costs 250 mana)."},
    ],
    "paladin": [
        {"id": "holy_smite",        "name": "Holy Smite",        "min_level": 1,  "mana_cost": 15, "cooldown": 1.5,  "type": "aoe_circle",  "damage": 30, "range": 110,
         "description": "Burst of holy light damages all enemies in 110px radius."},
        {"id": "double_holy_smite", "name": "Double Holy Smite", "min_level": 5,  "mana_cost": 40, "cooldown": 2.0,  "type": "aoe_circle",  "damage": 30, "range": 220,
         "description": "Holy burst with doubled radius (220px)."},
        {"id": "holy_cross",        "name": "Holy Cross",        "min_level": 9,  "mana_cost": 50, "cooldown": 3.0,  "type": "holy_cross",  "damage": 40, "range": 220,
         "description": "Fire holy beams in all 4 directions (220px, 40 dmg each)."},
        {"id": "holy_shield",       "name": "Holy Shield",       "min_level": 13, "mana_cost": 60, "cooldown": 15.0, "type": "shield",      "shield_hp": 50,
         "description": "Force-field absorbs up to 50 points of damage."},
        {"id": "holy_healing",      "name": "Holy Healing",      "min_level": 17, "mana_cost": 70, "cooldown": 30.0, "type": "heal_full",
         "description": "Restore all HP instantly."},
        {"id": "resurrect",         "name": "Resurrect",         "min_level": 20, "mana_cost": 80, "cooldown": 0.0,  "type": "resurrection", "auto_trigger": True,
         "description": "Auto: upon death, resurrect in place with full HP (costs 80 mana)."},
    ],
}

# Monster attack animation duration (seconds)
MONSTER_ATTACK_DURATION = 0.4

# Monster sprite info: category subfolder under frames/, sprite_dir name
MONSTER_SPRITES = {
    "wild_cat": {"category": "animals", "sprite_dir": "cat1"},
    "wild_dog": {"category": "animals", "sprite_dir": "dog1"},
    "bandit": {"category": "military", "sprite_dir": "military1_1"},
    "soldier": {"category": "military", "sprite_dir": "military2_1"},
    "guard": {"category": "military", "sprite_dir": "military3_1"},
    "commander": {"category": "bonus1", "sprite_dir": "bonus1_1"},
}

# Boss multipliers
BOSS_HP_MULT = 3.0
BOSS_DAMAGE_MULT = 1.5
BOSS_XP_MULT = 5.0
BOSS_GOLD_MULT = 3.0
BOSS_CHASE_DURATION = 8.0
BOSS_CHASE_SPEED = 170.0  # Less than PLAYER_SPEED

# NPC
NPC_SPEED = 60.0

# NPC speech bubble sayings (randomly chosen for wandering town NPCs)
NPC_SAYINGS = [
    "Hello!", "Good day!", "Nice weather!", "Safe travels!",
    "Nice fishing!", "Watch out for monsters!", "Stay safe!",
    "Buy some potions!", "The road ahead is dangerous.",
    "I heard the boss is tough!", "Welcome, traveler!",
    "Need supplies?", "Beautiful day, isn't it?",
    "Have you tried the mushrooms?", "Lovely town we have here.",
    "Don't forget to save your gold!", "The forest is restless.",
    "Good luck out there!", "I saw a chest in the woods!",
    "Beware the commander!", "Fine day for an adventure!",
]

# Merchant NPC type variants (one is chosen per town for visual variety)
MERCHANT_NPC_TYPES = ["npc1_1", "npc1_2", "npc2_1", "npc3_1", "npc4_1"]

# Inventory
INVENTORY_COLS = 5
INVENTORY_ROWS = 5
INVENTORY_SLOTS = INVENTORY_COLS * INVENTORY_ROWS
MAX_STACK = 20
INVENTORY_SLOT_SIZE = 52
INVENTORY_PADDING = 4

# Shop
SHOP_BUY_MARKUP = 1.5

# Buff
DEFAULT_BUFF_DURATION = 10.0

# Weapon
DEFAULT_ATTACK_COOLDOWN = 0.5

# Ground item bob
GROUND_ITEM_BOB_SPEED = 2.0
GROUND_ITEM_BOB_AMOUNT = 4

# Stage sizes
COMBAT_STAGE_TILES = 50
TOWN_STAGE_TILES = 30  # Base size at 1024x768

def get_town_stage_tiles() -> int:
    """Return town stage tile count scaled to current resolution.
    At 1024x768 (viewport ~21x16), base 30 tiles gives ~1.4x viewport.
    Scale so the town stays ~1.5x the largest viewport dimension.
    """
    viewport_tiles_x = SCREEN_WIDTH // TILE_SIZE
    viewport_tiles_y = SCREEN_HEIGHT // TILE_SIZE
    target = int(max(viewport_tiles_x, viewport_tiles_y) * 1.5)
    return max(30, min(target, 80))

# Stage difficulty scaling per stage number
def get_stage_difficulty(stage_num: int) -> float:
    return 1.0 + (stage_num - 1) * 0.3

# Music tracks
MUSIC_TRACKS = {
    "menu": os.path.join(MUSIC_PATH, "01 Menu", "MP3", "Main Track", "MENU-LOOP.mp3"),
    "intro": os.path.join(MUSIC_PATH, "02 Intro", "MP3", "Main Track", "Intro-LOOP.mp3"),
    "main_theme": os.path.join(MUSIC_PATH, "03 Main Theme", "MP3", "Main Track",
                               "Main Theme-LOOP.mp3"),
    "enchanted_forest": os.path.join(MUSIC_PATH, "04 Enchanted Forest", "MP3", "Main Track",
                                     "Enchanted Forest.mp3"),
    "undefined": os.path.join(MUSIC_PATH, "05 Undefined", "MP3", "Main Track", "Undefined.mp3"),
    "battle": os.path.join(MUSIC_PATH, "06 Battle", "MP3", "Main Track", "Battle-LOOP.mp3"),
    "emotional": os.path.join(MUSIC_PATH, "07 Emotional Main Theme", "MP3", "Main Track",
                              "Emotional Main Theme.mp3"),
}

# Music rotation: each stage gets a different track (no back-to-back repeats)
COMBAT_MUSIC_ROTATION = ["main_theme", "enchanted_forest", "undefined", "intro"]
TOWN_MUSIC_ROTATION = ["menu", "emotional"]
BOSS_MUSIC = "battle"

# Sound effects
SFX_PATHS = {
    "sword_swing": os.path.join(SOUNDS_PATH, "Game", "Sword.wav"),
    "sword_swing2": os.path.join(SOUNDS_PATH, "Game", "Sword2.wav"),
    "hit": os.path.join(SOUNDS_PATH, "Game", "Hit.wav"),
    "hit2": os.path.join(SOUNDS_PATH, "Game", "Hit1.wav"),
    "hit3": os.path.join(SOUNDS_PATH, "Game", "Hit2.wav"),
    "kill": os.path.join(SOUNDS_PATH, "Game", "Kill.wav"),
    "coin": os.path.join(SOUNDS_PATH, "Game", "Coin.wav"),
    "gold": os.path.join(SOUNDS_PATH, "Game", "Gold1.wav"),
    "bonus": os.path.join(SOUNDS_PATH, "Game", "Bonus.wav"),
    "powerup": os.path.join(SOUNDS_PATH, "Game", "PowerUp1.wav"),
    "gameover": os.path.join(SOUNDS_PATH, "Game", "GameOver.wav"),
    "success": os.path.join(SOUNDS_PATH, "Game", "Success1.wav"),
    "alert": os.path.join(SOUNDS_PATH, "Game", "Alert.wav"),
    "menu_accept": os.path.join(SOUNDS_PATH, "Menu", "Accept.wav"),
    "menu_cancel": os.path.join(SOUNDS_PATH, "Menu", "Cancel.wav"),
    "menu_move": os.path.join(SOUNDS_PATH, "Menu", "Menu1.wav"),
    "magic": os.path.join(SOUNDS_PATH, "Game", "Magic1.wav"),
    "fireball": os.path.join(SOUNDS_PATH, "Game", "Fireball.wav"),
    "explosion": os.path.join(SOUNDS_PATH, "Game", "Explosion.wav"),
}

# Key bindings
KEY_UP = pygame.K_w
KEY_DOWN = pygame.K_s
KEY_LEFT = pygame.K_a
KEY_RIGHT = pygame.K_d
KEY_ATTACK = pygame.K_SPACE
KEY_PICKUP = pygame.K_e
KEY_INVENTORY = pygame.K_i
KEY_INVENTORY_ALT = pygame.K_TAB
KEY_ESCAPE = pygame.K_ESCAPE
KEY_SPELL = pygame.K_q

# ---------------------------------------------------------------------------
# Xbox Controller button mappings (standard SDL/XInput layout)
# ---------------------------------------------------------------------------
CONTROLLER_DEADZONE = 0.25
CONTROLLER_BUTTON_ATTACK = 0      # A button
CONTROLLER_BUTTON_PICKUP = 1      # B button
CONTROLLER_BUTTON_INVENTORY = 2   # X button
CONTROLLER_BUTTON_MINIMAP = 3     # Y button
CONTROLLER_BUTTON_LB = 4          # Left Bumper
CONTROLLER_BUTTON_RB = 5          # Right Bumper
CONTROLLER_BUTTON_BACK = 6        # Back / Select
CONTROLLER_BUTTON_START = 7       # Start
CONTROLLER_AXIS_LX = 0            # Left stick horizontal
CONTROLLER_AXIS_LY = 1            # Left stick vertical

# ---------------------------------------------------------------------------
# Tileset object definitions for stage decoration
# Objects are extracted from the packed tilesets or fall back to colored shapes.
# collision: size in base tiles
# color: fallback color if tileset extraction fails
# tileset_region: (tileset_filename, x, y, w, h) in pixels for extraction
# ---------------------------------------------------------------------------
OBJECT_DEFS = {
    "Tree_medium": {
        "collision": (1, 1), "color": (40, 100, 40),
        "tileset_region": ("outside.png", 384, 128, 32, 48),
    },
    "Tree_small": {
        "collision": (1, 1), "color": (50, 120, 50),
        "tileset_region": ("outside.png", 320, 192, 32, 48),
    },
    "Rock_large": {
        "collision": (1, 1), "color": (120, 110, 100),
        "tileset_region": ("outside.png", 112, 80, 16, 16),
    },
    "Rock_small": {
        "collision": (1, 1), "color": (140, 130, 120),
        "tileset_region": ("outside.png", 128, 80, 16, 16),
    },
    "Bush": {
        "collision": (1, 1), "color": (60, 140, 40),
        "tileset_region": ("outside.png", 192, 32, 16, 16),
    },
    "Barrel": {
        "collision": (1, 1), "color": (139, 90, 43),
        "tileset_region": ("outside.png", 96, 16, 16, 32),
    },
    "Crate": {
        "collision": (1, 1), "color": (160, 120, 60),
        "tileset_region": ("outside.png", 112, 32, 16, 16),
    },
    "Fence": {
        "collision": (1, 1), "color": (100, 70, 40),
        "tileset_region": ("outside.png", 48, 80, 16, 16),
    },
    "Well": {
        "collision": (1, 1), "color": (100, 100, 110),
        "tileset_region": ("outside.png", 48, 304, 16, 16),
    },
    "Stump": {
        "collision": (1, 1), "color": (110, 75, 40),
        "tileset_region": ("outside.png", 752, 352, 16, 16),
    },
    "Flowers": {
        "collision": (1, 1), "color": (220, 120, 160),
        "tileset_region": ("outside.png", 128, 64, 16, 16),
        "decorative": True,
    },
    "Tall_grass": {
        "collision": (1, 1), "color": (60, 160, 50),
        "tileset_region": ("outside.png", 176, 64, 16, 16),
        "decorative": True,
    },
    "Dungeon_wall": {
        # Procedurally drawn dark stone block — no tileset extraction
        "collision": (1, 1), "color": (58, 52, 56),
    },
}

# Stage themes per combat stage number
STAGE_THEMES = {
    1: "forest", 2: "forest", 3: "forest", 4: "forest",
    5: "desert", 6: "desert", 7: "desert",
    8: "dungeon", 9: "dungeon", 10: "dungeon",
}

# Stage music per theme
STAGE_MUSIC = {
    "forest": "main_theme",
    "desert": "enchanted_forest",
    "dungeon": "main_theme",
    "interior": "menu",
}

# Monsters available per stage theme
STAGE_MONSTERS = {
    "forest": ["wild_cat", "wild_dog", "bandit"],
    "desert": ["wild_dog", "bandit", "soldier"],
    "dungeon": ["soldier", "guard", "bandit"],
}

# Boss type per combat stage (one monster type per stage, escalating)
STAGE_BOSSES = {
    1: "wild_cat", 2: "wild_dog", 3: "bandit", 4: "soldier", 5: "guard",
    6: "commander", 7: "commander", 8: "commander", 9: "commander", 10: "commander",
}

# Extra HP/damage multiplier applied on top of BOSS_HP_MULT / BOSS_DAMAGE_MULT
# for stages where the same boss type repeats (stages 6-10 all use commander)
BOSS_STAGE_SCALING = {
    1: 1.0, 2: 1.0, 3: 1.0, 4: 1.0, 5: 1.0,
    6: 1.0, 7: 1.25, 8: 1.5, 9: 1.75, 10: 2.25,
}
