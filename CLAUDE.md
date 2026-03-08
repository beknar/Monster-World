# Monster World

## Project Overview

A 2D top-down action RPG built with Python and pygame. The player controls a hero character navigating through multiple stages, fighting monsters, gaining experience, leveling up, and defeating bosses.

## Tech Stack

- **Language:** Python 3
- **Framework:** pygame
- **Environment:** Python virtual environment (venv) in the project root
- **Entry point:** `main.py` (top-level)
- **DPI Scaling:** High DPI scaling is overridden via `ctypes.windll.shcore.SetProcessDpiAwareness(1)` in `game.py.__init__()` so the game renders at true pixel resolution on Windows, not scaled/blurry
- **Default Resolution:** 1920x1200 (configurable via Options screen)
- **Available Resolutions:** 800x600, 960x548, 1024x768, 1280x720, 1280x1024, 1366x768, 1600x900, 1600x1200, 1680x1050, 1920x1080, 1920x1200, 2560x1440 (changeable at runtime from the Options screen)
- **Font Scaling:** All text automatically scales with resolution. Base sizes are designed for 1024x768; at higher resolutions fonts scale up proportionally (e.g., 1.41x at 1920x1080, 1.875x at 2560x1440). Uses `settings.scaled_font_size()` and `settings.get_font_scale()`.

### Virtual Environment

```bash
python -m venv venv
source venv/Scripts/activate   # Windows Git Bash
pip install pygame
```

Always activate the venv before running or installing packages.

## Project Structure

```
claude-rpg/
├── CLAUDE.md
├── README.md                        # Public-facing project overview, install and run instructions
├── main.py                          # Game entry point
├── venv/                            # Python virtual environment
├── src/                             # Game source code
│   ├── settings.py                  # Constants, config, screen size, tile size, etc.
│   ├── game.py                      # Main game loop, state management
│   ├── player.py                    # Player class, movement, combat, leveling
│   ├── npc.py                       # NPC class, behavior patterns
│   ├── monster.py                   # Monster class, AI patterns, boss logic
│   ├── weapon.py                    # Weapon definitions, damage, range
│   ├── item.py                      # Item definitions, types (weapon, consumable, sellable, armor)
│   ├── inventory.py                 # 5x5 inventory grid, stacking, mouse interaction
│   ├── loot.py                      # Drop tables, ground item spawning and pickup
│   ├── shop.py                      # Shop UI, buy/sell logic, NPC merchant interaction
│   ├── camera.py                    # Camera/viewport following the player
│   ├── stage.py                     # Stage loading, scene layout, transitions
│   ├── collision.py                 # Collision detection between layers
│   ├── combat.py                    # Combat system, damage calc, XP rewards
│   ├── animation.py                 # Sprite sheet parsing, animation controller
│   ├── audio.py                     # Music and sound effect manager
│   ├── hud.py                       # Health bar, XP bar, level display, equipped weapon/armor, gold count
│   ├── projectile.py               # Projectile class (arrows, bullets) for ranged weapons
│   ├── pathfind.py                 # A* pathfinding for monster obstacle avoidance
│   ├── savegame.py                 # Save/Load/Delete game functionality (JSON persistence)
│   └── spritesheet.py              # Sprite sheet loading and frame extraction
├── saves/                           # Save game files (JSON, auto-created at runtime)
├── data/                            # Game data files
│   ├── stages/                      # Stage layout definitions (JSON or similar)
│   ├── weapons.json                 # Weapon stats (damage, range, speed)
│   ├── items.json                   # All item definitions (consumables, sellables, weapons)
│   ├── drop_tables.json             # Monster loot drop tables (item/gold chances per monster type)
│   └── shops.json                   # Shop inventories per town stage
└── newassets/                       # ALL game assets (sprites, tilesets, sounds, music)
    ├── heroes/                      # Player character sprites
    ├── monsters/                    # Monster and animal sprites
    ├── npcs/                        # NPC sprites
    ├── tileset/                     # Outdoor, snow, and interior tilesets
    ├── objects/                     # Game objects (potions, weapons, chests, furniture, etc.)
    ├── icons/                       # UI icons (weapons, items, status)
    ├── sounds/                      # Sound effects (WAV)
    │   ├── game/                    # In-game SFX
    │   └── menu/                    # Menu UI SFX
    └── music/                       # Background music (MP3/WAV)
```

**All game assets live under `newassets/`.** No other asset directories should be referenced. Code in `src/settings.py` must point all asset paths into this single directory tree.

## Asset Directory Reference

All assets are stored under `newassets/` at the project root. Each subdirectory is described below.

### newassets/heroes/
Player character sprites. The game supports multiple playable heroes.
- Each hero has sprite sheets for animations: idle, walk, run, melee, ranged, cast, grab, hit, die, roll, dash, teleport, itemGot
- Melee hitbox reference sheets may be available (`_melee_hitbox`)
- Character portraits and emotes (if available)
- Projectile sprites (Arrow, Boomerang, Dagger, Spear, Bomb, Fireball, Magic Missile, Ice Shard, Lightning Bolt) and breakable object sprites (Box, Pot, Grass, Wood)
- Naming convention: `{CharacterName}_{animation}.png` — sprite sheets with multiple frames per row, one row per direction

### newassets/monsters/
Monster and animal sprites used in combat stages.
- Each monster type has idle and walk/fly sprite sheets
- Small monsters use 16x16 pixel frames
- Large monsters (e.g., ogres, bosses) use 32x32 pixel frames
- Sprite sheets contain 4 frames per animation and 4 rows for 4 directions (down, left, right, up)
- Ambient animals (cow, hen, pig) may also be included with idle/walk animations
- Naming convention: `{Creature} {Variant}_{animation} ({WxH}).png`
  - Example: `Slime 01_idle (16x16).png`, `Ogre 01_walk (32x32).png`
  - **Exception:** Some creatures may use underscores instead of spaces (e.g., `Krampus_01`)

### newassets/npcs/
NPC sprites for towns and stages.
- Numbered generic NPCs (e.g., NPC 01–14) with idle/walk animations
- Townsfolk with specific roles: Alchemist, Barmaid, Bartender, Blacksmith, Farmer, Fisherman, Merchant, Kids
- NPCs use 16x24 pixel frames (16 wide, 24 tall)
- Sprite sheets: 4 frames per animation, 4 directional rows
- Naming convention: `{NPC name}_{animation} ({WxH}).png`
  - Example: `NPC 01_idle (16x24).png`, `Merchant_walk (16x24).png`

### newassets/tileset/
Tilesets for building stage backgrounds and environment.
- **Outdoor tileset:** Full packed tileset reference image plus individual tile images (trees, houses, rocks, flora, geology, fences, doors, windows)
  - Trees: small and medium variants
  - Houses: small/medium/big with open/closed door variants
  - Flora: Bush, Flowers, Leaves, Tall grass, Tree stump
  - Geology: Rocks, Wells, Chimney
- **Snow/winter tileset:** Snow-themed variants of trees, houses, rocks, bridges, cave entrance, flora
- **Interior tileset:** Indoor floors, walls, furniture patterns; tileset expansions (Bath, Bedroom, School, Workshop)
- Animated objects: Candelabrum, Candle, Fireplace, Furnace, Lamp, Torch (front/side) — each with on/off states

### newassets/objects/
Individual object sprites used as pickups, decorations, and interactive items.
- Furniture: Anvil, Barrel, Barrel_water, Crate, Stool
- Chests: big, small, mimic
- Potions: red, blue, green
- Sword, Torch
- Fences: wood, stone, metal
- Wooden signs with icons (arrow directions, beer, book, leaf, magic, potion, shield, skull, sword)
- Food: Mushrooms (variants), Crops (Berries, Carrot, Sunflower)
- Holiday/snow variants of objects (if applicable)

### newassets/icons/
UI icons for inventory, HUD, weapon/item display.
- Available at multiple sizes (e.g., 16x16, 32x32, 48x48)
- Numbered sequentially: `{number}.png`
- Used for inventory slot icons, weapon icons in the HUD, item tooltips

### newassets/sounds/
Sound effects in WAV format, split into two subdirectories.

**newassets/sounds/game/**: In-game sound effects
- Combat: Hit, Sword swing, Kill, Explosion
- Magic: Fire, Fireball, Magic, Spirit
- Player feedback: Alert, Bonus, Coin, Gold, PowerUp, Success
- Misc: Jump, MiniImpact, Strange, Secret, GameOver, Fx, Voice

**newassets/sounds/menu/**: Menu UI sound effects
- Accept, Cancel, Menu navigation sounds

### newassets/Fantasy RPG Complete OST/
Background music from the **Fantasy RPG Complete OST by VHCMusic**. All tracks are MP3, loaded from `MP3/Main Track/` within each numbered subfolder. Path root: `newassets/Fantasy RPG Complete OST/Fantasy RPG Complete OST- VHCMusic/`.

| Folder | File | Track Key | Usage |
|--------|------|-----------|-------|
| `01 Menu` | `MENU-LOOP.mp3` | `menu` | Hero choice / title screen (loops); town music rotation |
| `02 Intro` | `Intro-LOOP.mp3` | `intro` | Combat music rotation |
| `03 Main Theme` | `Main Theme-LOOP.mp3` | `main_theme` | Combat music rotation |
| `04 Enchanted Forest` | `Enchanted Forest.mp3` | `enchanted_forest` | Combat music rotation |
| `05 Undefined` | `Undefined.mp3` | `undefined` | Combat music rotation |
| `06 Battle` | `Battle-LOOP.mp3` | `battle` | Boss encounters (plays once) |
| `07 Emotional Main Theme` | `Emotional Main Theme.mp3` | `emotional` | Town music rotation, victory screen |

## Game Architecture

### Rendering Layers (bottom to top)
1. **Background layer** — Ground tiles (grass, dirt, stone, snow). Walkable by all entities.
2. **Object layer** — Trees, houses, rocks, fences, wells, barrels, crates, stumps, furniture. Collidable — no entity can walk through these. Decorative objects (flowers, tall grass) are drawn but do not block movement.
3. **Entity layer** — Player, NPCs, monsters. Collidable with each other — no entity can overlap another. Drawn with y-sorting so entities lower on screen render on top.

**Viewport culling:** `stage.draw_objects()` culls obstacles outside the visible viewport for performance. The culling rect **must use `settings.SCREEN_WIDTH` and `settings.SCREEN_HEIGHT`** (not hardcoded pixel values) so it works correctly at all resolutions. Using hardcoded dimensions causes objects to be invisible but still collidable at higher resolutions.

### Tile System
- Base tile size: 16x16 pixels, scaled up for display (e.g., 3x or 4x)
- Combat stage size: 50x50 tiles per stage
- **Town stage size:** Dynamic via `settings.get_town_stage_tiles()` — scales to ~1.5x the viewport's largest dimension. Base 30 tiles at 1024x768, up to 80 tiles at ultra-high resolutions. Obstacle and NPC counts scale proportionally with area (`size_factor = area / (30*30)`).
- Camera follows the player, showing a viewport-sized window of the stage. When the map is smaller than the screen (e.g., 50-tile combat stage at 2560x1440), the map is centered on screen instead of scrolling — preventing black borders at the edges.
- **Path generation:** Dirt paths are drawn with square, blocky tiles (`pygame.draw.rect` of `TILE_SIZE` x `TILE_SIZE`). Paths are 3 tiles wide (drawn as 3x3 tile blocks at each step). Five path patterns are randomly selected per stage: `cross` (offset center), `diagonal`, `l_shape`, `winding` (aggressive wobble), and `fork` (Y-shape). The `_draw_path_tile(rng, path_colors, tx, ty)` helper draws a single square tile; `_generate_path_between(start, end)` handles point-to-point path drawing with wobble; `_generate_winding_path()` creates more pronounced curves. Both combat and town stage seeds include a time-based component so layouts vary each playthrough.
- **Combat stage obstacles:** Forest/desert themes: trees, rocks, bushes, barrel/crate clusters, fence segments, wells, stumps, and decorative flora (flowers, tall grass). Dungeon theme: maze of `Dungeon_wall` stone blocks (see below). Decorative objects have `"decorative": True` in OBJECT_DEFS and don't block movement.
- **Dungeon maze generation (stages 8–10):** `_generate_combat_stage()` calls `_generate_dungeon_walls()` instead of the scatter-based obstacle code. The maze uses the **recursive-backtracker algorithm** on a 16×16 cell grid (each cell = 2-tile passage + 1-tile wall separator = 3 tiles/cell × 16 = 48 inner tiles, plus 1-tile outer border = 50 tiles total). Corridors are 2×2 tiles wide (96×96 px). The outer border ring is always solid. Protected zones — player spawn, exit portal, and boss area — are kept free of walls, so the boss chamber is a large open room. `Dungeon_wall` obstacles are procedurally drawn dark stone blocks (mortar lines + highlight). Player spawns at tile (2, 25) for dungeon stages instead of (3, 25).
- **Safe player spawn:** After all obstacles are placed, `_generate_combat_stage()` and `_generate_town_stage()` both call `stage._find_clear_spawn(world_x, world_y)` to guarantee the player spawn point is not blocked. The helper converts the intended spawn to tile coordinates and spirals outward (up to 8 tiles) until a 2×2-tile area free of all obstacle collision rects is found, then returns that world position. Prevents the player from spawning inside an object and getting stuck.

### Keyboard Controls

| Key / Input | Action |
|-------------|--------|
| W/A/S/D | Move player up/left/down/right |
| Attack key (e.g., Space or Left Click) | Swing equipped melee weapon / Fire ranged weapon |
| Q | Cast currently selected spell/ability |
| 1-9 | Select spell/ability by number (see Spell Selection HUD) |
| E | Pick up item/gold from the ground (when near a ground item) |
| I or Tab | Toggle inventory open/close |
| M | Toggle mini-map display (top-right corner) |
| F | Toggle FPS counter display (below armor indicator) |
| Right Mouse Button | (In inventory) Use/Wield/Eat the clicked item |
| Left Mouse Button | (In inventory) Pick up item → click another slot to place/swap, or click outside grid to drop |
| Esc | Close inventory (if open), resume game from pause menu |
| H (menu) | Open help/info screen |
| ENTER (options) | Activate selected option (Save/Load/Delete) |
| UP/DOWN (options) | Select option row |
| UP/DOWN (paused) | Navigate pause menu rows (Music, SFX, Save, Load, Return to Menu) |
| LEFT/RIGHT (paused) | Adjust selected volume slider (rows 0-1 only) |
| ENTER (paused) | Confirm selected pause row (Save / Load / Return to Menu) |
| UP/DOWN (save/load/delete dialog) | Navigate save slots |
| ENTER (save/load/delete dialog) | Confirm action (save name / load / delete) |
| Esc (dialog) | Cancel / go back to previous screen (pause or options) |
| Backspace (save dialog) | Delete last character of save name |

### Xbox Controller Support

The game auto-detects Xbox controllers via `pygame.joystick` on startup and supports hot-plug (connect/disconnect at any time). When a controller is detected, all on-screen hints switch to show controller button names. Both keyboard and controller can be used simultaneously.

**Controller constants** are defined in `src/settings.py` (`CONTROLLER_BUTTON_*`, `CONTROLLER_AXIS_*`, `CONTROLLER_DEADZONE`).

| Button / Input | Action |
|----------------|--------|
| Left Stick / D-pad | Move player (analog with deadzone 0.25) |
| A button | Attack (tap or hold for continuous fire) / Select menu button / Buy or Sell (shop) / Use or Equip (inventory) / Activate pause or options row / Confirm save/load/delete |
| B button | Pick up item / Interact with NPC / Close inventory / Close shop / Resume from pause / Go back |
| X button | Toggle inventory (gameplay) / Options (menu) |
| Y button | Toggle mini-map / Drop item (inventory) |
| START | Pause/resume (gameplay) / Start new game (menu) / Confirm (game over/win) |
| Back / Select | Open help (menu) / Resume from pause / Go back / Close menus |
| LB | Previous hero (menu) / Switch to shop panel (shop) |
| RB | Cast currently selected spell/ability (gameplay) / Next hero (menu) / Switch to inventory panel (shop) |
| D-pad (gameplay) | Left/Right to cycle selected spell/ability; Up/Down for movement |
| D-pad (main menu) | Left/Right to select hero, Down to Resume (if available) or Start, then Help |
| D-pad (pause) | Up/Down to navigate rows 0-4; Left/Right to adjust volume sliders |
| D-pad (menus) | Navigate sliders, scroll help, select options |
| D-pad (inventory) | Navigate the 5x5 item grid |
| D-pad (shop) | Navigate shop items / inventory slots; left/right switches panels |

**Controller main menu navigation:**
- D-pad LEFT/RIGHT selects hero (same as LB/RB)
- D-pad DOWN from hero row moves to Resume button (sel=3) if autosave exists, else Start Game (sel=0); further DOWN goes to Start → Help → Exit
- D-pad UP returns through Resume (if exists) back to hero row
- D-pad LEFT/RIGHT switches between Help and Options buttons (when on that row)
- A button confirms the highlighted button (Resume, Start Game, Help, Options, or Exit); A on hero row starts game
- START always starts a new game regardless of button selection
- Selected button shows gold border; `menu_button_sel` tracks position (-1=hero row, 0=Start, 1=Help, 2=Options, 3=Resume, 4=Exit)
- Resume button (green) only shown and selectable when `has_autosave == True`
- Exit button (red) always shown; confirms with A or mouse click → `self.running = False`
- Arrow hints and bottom hint text adapt to show D-pad/LB/RB when controller is connected
- `menu_button_sel` resets to -1 when returning to menu from other states

**Controller inventory navigation:**
- D-pad moves a gold-bordered cursor through the 5x5 inventory grid
- A button uses/equips the highlighted item (same as right-click)
- Y button drops the highlighted item on the ground
- B, X, Back, or START closes inventory
- Tooltip shows next to the cursor slot with controller-specific hints

**Controller shop navigation:**
- Shop opens with cursor on the shop panel (buy side)
- D-pad UP/DOWN moves through shop items or inventory slots
- D-pad LEFT/RIGHT switches between shop and inventory panels
- LB/RB also switches panels
- A button buys (shop panel) or sells (inventory panel)
- B, Back, or START closes the shop
- Gold border highlights the active cursor position
- Panel title shows "A to sell" instead of "click to sell" when controller is connected
- Controller hints bar shown at bottom of shop overlay

**Merchant interaction hint:**
- When the player is near a merchant NPC, the HUD displays a gold-colored prompt: "Press B to Shop" (controller) or "Press E to Shop" (keyboard)
- `hud.near_merchant` flag is set by `game.py` during the NPC update loop by checking `npc.is_near()`

**Implementation details:**
- `game.py._init_controller()` initializes `pygame.joystick` and connects to the first available joystick
- `game.py._check_controller()` handles hot-plug via `JOYDEVICEADDED`/`JOYDEVICEREMOVED` events
- `game.py._get_controller_move()` reads left stick + d-pad with deadzone applied
- `game.py._handle_controller_button()` processes discrete button presses for all game states (menu, playing, inventory, shop, paused, help, options, game over, win)
- `game.py._handle_controller_hat()` processes d-pad events for main menu/options/pause/inventory/shop navigation
- `game.menu_button_sel` tracks main menu button cursor (-1=hero row, 0=Start, 1=Help, 2=Options, 3=Resume, 4=Exit)
- `player.handle_input()` accepts optional `controller_move` tuple for analog stick movement
- `hud.controller_connected` flag switches the bottom control hint between keyboard and controller text
- `hud.near_merchant` flag shows merchant interaction prompt when player is near a shop NPC
- `inventory.gamepad_cursor` tracks grid position (-1 when inactive, 0-24 when navigating)
- `inventory.gamepad_navigate(dx, dy)` moves cursor within the 5x5 grid
- `shop.gamepad_panel` / `shop.gamepad_shop_index` / `shop.gamepad_inv_index` track shop cursor state
- `shop.gamepad_navigate()`, `shop.gamepad_confirm()`, `shop.gamepad_switch_panel()` handle shop controller input
- `shop.controller_connected` flag adapts panel titles and shows controller hint bar
- All screen hints (menu, pause, options, help, game over, victory) adapt to show controller buttons when connected
- Help screen includes full keyboard and controller reference tables

### Main Menu and Character Selection

The game starts with a **main menu** screen before gameplay begins. The menu has:

1. **Title** — The game name displayed prominently
2. **Character selection** — The player chooses their hero before starting:
   - All available hero characters are shown side by side (using idle animation or portrait from `newassets/heroes/`)
   - The player uses **Left/Right arrow keys** or clicks to highlight a hero
   - Each hero displays their **name** above their sprite (offset scales with font height to avoid overlapping the highlight box)
   - The **selected hero's description** (abilities, HP, weapon type) is shown below the hero row (positioned below the tallest hero sprite)
   - The currently highlighted hero is visually emphasized (larger, bordered, or glowing)
   - Press **Enter** or click **"Start Game"** to begin with the selected hero
3. **Start Game button** — Begins a new game with the chosen character. Button auto-sizes to fit text at any resolution.
4. **Help button** and **Options button** — Displayed side by side below the Start button, auto-sized to fit text with scaled gap between them. Layout uses `_menu_layout()` shared between draw and click handler.
5. **Exit Game button** — Red-styled button below the Help/Options row (at ~82% of screen height). Click or press A with controller sel=4 to quit the application (`self.running = False`). The two hint lines at the bottom are anchored below `exit_rect.bottom` (not at fixed y-percentages) so they never overlap the button at any resolution.
6. **Help screen** — Opens a scrollable help/info screen (also accessible via **H** key or **Back** button on controller) showing:
   - All hero characters with their starting HP, movement speed, default weapon, mana/grit, all spells/abilities (with level requirements), and description
   - Levelling table with columns (Level Up, Total XP, XP Needed, War/Rgr XP) — shows all 19 level-up steps from `XP_THRESHOLDS` (max level 20). War/Rgr XP column shows 2/3 of base values for Warrior and Ranger. Note that Warrior & Ranger need only 2/3 of base XP.
   - Full weapon list using pixel-based column positions (Name, Damage, Range, Speed, Type, Classes) — columns scale with resolution and stay aligned with their headers
   - All items with descriptions and gold values (consumables, sellables, weapon items, armor items)
   - Armor table with columns (Name, Defense, Value, Class) showing all 6 armor tiers from `ARMOR_DEFS`. Includes armor damage formula and class restriction notes.
   - Enemies table with columns (Enemy, HP, Damage, Speed) showing all monster types and their base stats from `MONSTER_STATS`. Boss Encounters by Stage table shows columns (Stage, Boss, Scale, HP, Damage) for all 10 stages using `STAGE_BOSSES` and `BOSS_STAGE_SCALING`. Stages 6–10 highlighted in orange.
   - Spells table with columns (Name, Hero, Lv, Damage, Mana, Type) showing all spells from `SPELL_DEFS` with min-level and auto-trigger tags. Includes spell descriptions and casting instructions (1-9 keys / D-pad L/R to select, Q / RB to cast). Per-hero mana and full spell list (with level reqs) shown under each hero in the HEROES section.
   - Grit Abilities table with columns (Name, Hero, Lv, Grit, CD) showing all abilities from `GRIT_ABILITIES` with min-level and auto-trigger tags. Per-hero grit and full ability list shown under each hero in the HEROES section.
   - Full keyboard controls reference table (Action / Key columns)
   - Full Xbox controller reference table (Action / Button columns)
   - Content starts below the Back button to avoid overlap at high resolutions
   - Scrollable via mouse wheel, UP/DOWN arrow keys, or D-pad; ESC, H, B, or Back to return to menu
5. **Options button** — Opens a settings screen with:
   - Music Volume slider (click, LEFT/RIGHT keys)
   - SFX Volume slider (click, LEFT/RIGHT keys)
   - Resolution selector (LEFT/RIGHT to cycle: 800x600, 960x548, 1024x768, 1280x720, 1280x1024, 1366x768, 1600x900, 1600x1200, 1680x1050, 1920x1080, 1920x1200, 2560x1440; click dots to select)
   - Save Game button (only shown when a game is in progress) — opens save dialog
   - Load Game button — opens load dialog
   - Delete Save button — opens delete dialog
   - UP/DOWN to select option; ENTER or A button to activate; LEFT/RIGHT to adjust sliders; ESC or Back to return to menu
   - Resolution changes take effect immediately and update all UI layouts (fonts, sliders, buttons, row spacing)
   - Options rows are dynamic: `_options_rows()` returns `["music", "sfx", "resolution", "save", "load", "delete"]` when a game is active, or omits `"save"` when no game. `pause_slider_sel` indexes into this list.
6. **Background music** — `MENU-LOOP.mp3` from `newassets/Fantasy RPG Complete OST/.../01 Menu/MP3/Main Track/` (track key `"menu"`, loops indefinitely via `audio.play_music("menu")`)

All playable heroes are defined in `src/settings.py` (e.g., `HERO_CHARACTERS` list). The selected hero determines which sprite sheets are loaded for the player throughout the game. Heroes can have per-hero stat overrides:
- `hp_mult`: HP multiplier (default 1.0). E.g., Mage has 0.7 (70 HP at level 1).
- `starting_weapon`: Starting weapon ID (default "basic_sword"). E.g., Warrior starts with "basic_sword", Mage starts with "mage_bolt" (ranged staff), Ranger starts with "crossbow", Paladin starts with "basic_sword".
- `mana_base`: Starting mana (default 0). E.g., Mage has 50, Paladin has 25.
- `mana_per_level`: Mana gained per level (default 0). E.g., Mage gets +10/level, Paladin gets +5/level.
- `xp_required_mult`: Fraction of base XP thresholds needed to level (default 1.0). Warrior and Ranger use 0.667 (2/3 of base XP). Applied in `player.gain_xp()` and the HUD XP bar.
- `desc`: Short description shown on the character selection screen (abilities, HP, weapon type).

**Hero defaults:**

| Hero | Starting Weapon | HP Mult | Base HP | Mana | Mana/Lvl | Mana Regen | Grit | Grit/Lvl | Grit Regen | XP Mult | Speed | Description |
|------|----------------|---------|---------|------|----------|------------|------|----------|------------|---------|-------|-------------|
| Warrior | Basic Sword (melee) | 1.0 | 100 | 0 | 0 | — | 50 | +10 | 0.5/sec | 0.667 | 200 | High HP, melee fighter, Lunge (Q) |
| Mage | Mage Bolt (ranged magic) | 0.7 | 70 | 50 | +10 | 0.5/sec (1 per 2s) | 0 | 0 | — | 1.0 | 200 | Low HP, fires magic bolts, Light Beam spell |
| Ranger | Crossbow (ranged) | 0.8 | 80 | 0 | 0 | — | 25 | +5 | 0.333/sec | 0.667 | 200 | Medium HP, ranged marksman, Homing Arrow (Q) |
| Paladin | Basic Sword (melee) | 1.2 | 120 | 25 | +5 | 0.333/sec (1 per 3s) | 0 | 0 | — | 1.0 | 200 | Balanced fighter, tanky, Holy Smite spell |

The Mage hero fires purple magic projectiles instead of swinging a melee weapon, and has fewer hit points to balance the ranged advantage. The Ranger fires crossbow bolts at range with slightly reduced HP (80). The Paladin has the highest starting HP (120). The Warrior and Ranger use Grit for their special abilities; the Mage and Paladin use Mana for spells. Heroes never have both Grit and Mana.

### Movement
- **Player:** WASD controls. Has walk and idle animations for 4 directions. Speed is always slightly faster than any boss.
- **NPCs:** Either stand still (idle animation) or patrol in defined patterns (walk animation). In towns, ~40% of NPCs patrol while the rest stand idle.
- **Monsters:** Either stand still (idle animation) or move in defined patterns. Bosses can chase the player. **Any non-boss monster that survives a hit permanently switches to enraged chase mode**, following the player at its full speed until it dies (`is_enraged` flag set in `take_damage()`, handled by `_do_enraged_chase()` in `update()`). **Proximity aggro:** if a player walks within `PROXIMITY_AGGRO_RANGE = 150` pixels of any idle non-boss monster, the monster immediately becomes enraged and starts chasing. **Chain aggro:** when a monster first becomes enraged (from damage or proximity), it activates all idle non-boss monsters within `CHAIN_AGGRO_RANGE = 120` pixels, causing them to also enrage — this propagates transitively within one frame via the `_just_enraged` flag checked in `game.py` after each monster update. **A\* obstacle avoidance:** when an enraged monster or boss gets stuck behind an obstacle (no movement progress for 0.5 seconds), it triggers `_recompute_path()` which uses A\* (`src/pathfind.py`) to compute a tile-grid path around the obstacle. The monster then follows waypoints until clear, then resumes direct chase. Path is recomputed at most every 2 seconds.
- All entities have **multi-frame idle animations** (4-frame breathing cycle: stand→walk1→stand→walk2 at 2.5x slower speed) even when stationary, so they never look frozen.
- All moving entities use walk/run animations while in motion.

### Collision
- Entities cannot move through object-layer tiles (trees, houses, rocks, etc.)
- Entities cannot move through each other (player, NPCs, monsters)
- Use axis-aligned bounding box (AABB) collision detection
- Object collision rects are shrunk by 20% per side (`inflate_ip(-shrink*2, -shrink*2)` where `shrink = int(TILE_SIZE * 0.2)`) so they better match the visible sprite size rather than covering the full tile
- **Monster collision rects:** 85% of sprite width and 70% of sprite height (was 70%/50%), centered on the sprite. This makes melee and ranged attacks connect more reliably when they visually appear to hit. `src/monster.py` `__init__()`: `self.collision_rect = pygame.Rect(0, 0, int(w * 0.85), int(h * 0.70))`.
- **Projectile collision rects:** 16×16 pixels (was 8×8), centered on the projectile position. `src/projectile.py`: `self.collision_rect = pygame.Rect(0, 0, 16, 16)`.
- **Decorative objects (Flowers, Tall_grass) are NOT the cause of invisible collisions.** They have `"decorative": True` in `OBJECT_DEFS` and are never added to `stage.obstacle_rects`, so they have no collision at all. `draw_objects()` uses `settings.SCREEN_WIDTH/HEIGHT` (not hardcoded values) for viewport culling, so rendering correctly covers the visible area at all resolutions. If invisible collisions occur, the most likely cause is a non-decorative obstacle whose sprite is fully occluded by an adjacent larger object (e.g., a rock hidden behind a tree) — both have independent collision rects.

### Combat System
- Player attacks with equipped weapon using an attack key
- Weapons have: damage value, range (pixels/tiles), attack speed, sound effect
- Weapon swing plays a sound effect; hits play a separate hit sound
- Damage is applied to any monster within the weapon's range and attack hitbox
- **Damage formula (player taking damage):** `actual = max(1, raw_damage - armor_defense - buff_defense)`. Armor defense comes from equipped armor (permanent), buff defense comes from Iron Mushroom consumable (temporary). Minimum 1 damage always gets through.
- **Floating damage numbers:** When the player deals damage to a monster, a yellow floating number appears at the monster's position showing the damage dealt. When the player takes damage from a monster (contact or attack), a red floating number appears at the player's position showing actual damage taken. Numbers rise upward and fade out over 0.8 seconds. Implemented via `FloatingText` class in `game.py`.
- **Monster proximity attacks:** Monsters have an `attack_interval` and `attack_range` (defined per type in `MONSTER_STATS` in `settings.py`). When a monster is within its attack range of the player, it performs a melee attack with a visual claw-slash arc. Each monster type has different attack timing (wild_cat: 2.0s, commander: 1.0s) and range (55–75 pixels). Monster attack cooldowns are staggered randomly at spawn to avoid simultaneous attacks.
- Monsters can also damage the player on direct collision contact (fallback)
- `combat.process_monster_contact()` returns a list of `(actual_damage, monster_x, monster_y)` tuples for spawning floating damage numbers. `player.take_damage()` returns `int` actual damage dealt (after armor reduction).
- Player default weapon: basic sword (from `newassets/objects/Sword.png`)
- On monster death: award XP, roll drop table for gold/items, spawn drops at death position

### Grit System and Abilities

Warrior and Ranger use Grit to power their special abilities. Grit values are defined per hero in `HERO_CHARACTERS` (`grit_base`, `grit_per_level`, `grit_regen`) and ability definitions are in `GRIT_ABILITIES` dict in `settings.py`.

**Grit mechanics:**
- `player.grit` (float): Current grit. `player.max_grit` (int): Maximum grit.
- Heroes with `grit_base = 0` (Mage, Paladin) have no grit bar and cannot use grit abilities.
- Grit regenerates passively: Warrior 0.5/sec (1 per 2s), Ranger 0.333/sec (1 per 3s).
- **Grit per kill (scaled by difficulty):** Each monster killed restores `max(3, difficulty × 3)` grit (capped at max), processed in `combat.process_kills()`. Stage 1 monsters give 3 grit; stage 10 monsters give ~11 grit.
- On level up, `max_grit` recalculates and grit fully restores.
- `player.use_grit(cost)` returns True if enough grit, False otherwise.
- Grit is saved/loaded with the game state.

**Grit HUD bar:**
- Amber/orange bar (`GRIT_BAR_COLOR = (180, 120, 40)`) displayed in the same vertical slot as the mana bar (heroes never have both).
- Only shown when `player.max_grit > 0`.
- Shows "Grit: {current}/{max}" text centered on the bar.

**Multi-ability system:** `GRIT_ABILITIES` in `settings.py` is a dict `{hero_id: [list of ability dicts]}`. Each entry has `id`, `name`, `min_level`, `grit_cost`, `cooldown`, `type`, and type-specific params. Abilities unlock as the hero levels up; only abilities with `min_level <= player.level` are available.

**Warrior abilities (11 total, min_level 1–20):**

| Ability | min_level | Grit Cost | Cooldown | Type |
|---------|-----------|-----------|----------|------|
| Lunge | 1 | 20 | 2.0s | Cone AoE, 2× damage, +100 range |
| Second Wind | 3 | 50 | 30.0s | Heal 50 HP |
| Action Surge | 5 | 60 | 45.0s | 2× speed + damage for 30s |
| Steel Skin | 7 | 70 | 30.0s | Shield 100 HP for 30s |
| Whirlwind | 9 | 80 | 30.0s | 50px AoE on every melee swing for 30s |
| Blazing Sword | 11 | 90 | 30.0s | +100px melee range with animated flames for 30s |
| Wind Surge (combo) | 13 | 100 | 45.0s | Second Wind + Action Surge |
| Surge Skin (combo) | 15 | 110 | 45.0s | Action Surge + Steel Skin |
| Skin Wind (combo) | 17 | 120 | 30.0s | Steel Skin + Whirlwind |
| Wind Blaze (combo) | 19 | 130 | 30.0s | Whirlwind + Blazing Sword |
| Blazing Resurrect | 20 | 140 | auto | Auto-trigger on death: revive + 4× weapon dmg in 220px AoE |

**Ranger abilities (6 total, min_level 1–20):**

| Ability | min_level | Grit Cost | Cooldown | Type |
|---------|-----------|-----------|----------|------|
| Homing Arrow | 1 | 15 | 3.0s | Arrow steers to nearest enemy |
| Double Fire | 5 | 40 | 30.0s | Second homing projectile on every shot for 30s |
| Trap Monster | 9 | 50 | 20.0s | Freeze nearest chasing monster for 30s |
| Cover of Darkness | 13 | 60 | 30.0s | All chasing monsters stop chasing for 30s |
| Third Wind | 17 | 70 | 30.0s | Full HP restore |
| Bestial Resurrect | 20 | 80 | auto | Auto-trigger on death: revive in place |

**Grit controls:**
- **Keyboard:** Q key (`KEY_SPELL = pygame.K_q`) → casts **currently selected** ability
- **1–9 keys:** Select ability by number (see Spell Selection HUD)
- **Controller:** RB button (`CONTROLLER_BUTTON_RB = 5`) → casts selected ability
- **D-pad Left/Right (gameplay):** Cycle through unlocked abilities
- Per-ability cooldowns tracked in `player.ability_cooldowns` dict. "Not enough grit!" HUD message shown when grit is insufficient.

**Implementation:**
- `player.grit_regen` (float): Per-hero passive regen in grit/sec. Applied in `update_buffs()` each frame.
- `player._ability_list`: List of ability dicts from `GRIT_ABILITIES[hero_id]`.
- `player.ability_cooldowns`: Dict `{ability_id: remaining_cooldown}`.
- `player.selected_spell_idx`: Index into `get_castable_spells()`.
- `player.get_castable_spells()`: Returns abilities with `min_level <= player.level` (non-auto-trigger only).
- `player.get_selected_ability()`: Returns currently selected ability dict.
- `player.select_ability_by_number(n)`, `player.cycle_ability(direction)`: Input handlers.
- `player.lunge_active` (bool): Set True briefly during Lunge cone hit calculation to double damage.
- `player.action_surge_timer`, `whirlwind_timer`, `blazing_sword_timer`, `double_fire_timer` (float): Remaining seconds for timed ability buffs.
- `SpellEffect("cone", ...)`: Filled red triangle + orange outline + highlight line, fading over `duration` seconds.
- `Projectile(homing=True)`: Enables steering in `update()` toward nearest monster or `target_monster`.

### Mana System and Spells

Heroes can have mana, which powers spells. Mana values are defined per hero in `HERO_CHARACTERS` (`mana_base`, `mana_per_level`) and spell definitions are in `SPELL_DEFS` dict in `settings.py`.

**Mana mechanics:**
- `player.mana` (float): Current mana. `player.max_mana` (int): Maximum mana.
- Heroes with `mana_base = 0` (Warrior, Ranger) have no mana bar and cannot cast spells.
- Mana regenerates passively at a hero-specific rate defined by `mana_regen` in `HERO_CHARACTERS`: Mage regenerates 0.5 mana/sec (1 mana per 2 seconds), Paladin regenerates 0.333 mana/sec (1 mana per 3 seconds). Heroes with no mana (Warrior, Ranger) omit `mana_regen` (defaults to 0.0).
- **Mana per kill (scaled by difficulty):** Each monster killed restores `max(3, difficulty × 3)` mana (capped at max), processed in `combat.process_kills()`. Stage 1 monsters give 3 mana; stage 10 monsters give ~11 mana.
- On level up, `max_mana` recalculates and mana fully restores.
- `player.use_mana(cost)` returns True if enough mana, False otherwise.
- Mana is saved/loaded with the game state.

**Mana HUD bar:**
- Green bar (`MANA_BAR_GREEN = (50, 200, 100)`) displayed between HP and XP bars.
- Only shown when `player.max_mana > 0`.
- Shows "Mana: {current}/{max}" text centered on the bar.

**Multi-spell system:** `SPELL_DEFS` in `settings.py` is a dict `{hero_id: [list of spell dicts]}`. Each entry has `id`, `name`, `min_level`, `mana_cost`, `cooldown`, `type`, and type-specific params. Spells unlock as the hero levels up.

**Mage spells (11 total, min_level 1–20):**

| Spell | min_level | Mana Cost | Cooldown | Type |
|-------|-----------|-----------|----------|------|
| Light Beam | 1 | 10 | 1.0s | Beam (220px line) |
| Shield | 3 | 30 | 15.0s | Absorb 100 HP damage |
| Fireball | 5 | 50 | 3.0s | Projectile, 150 dmg, 200px explosion AoE |
| Magic Missile | 7 | 75 | 4.0s | 4 homing motes, 50 dmg each |
| Polymorph | 9 | 100 | 8.0s | Transform nearest monster to weaker type |
| Lightning Bolt | 11 | 125 | 3.0s | Beam (600px, 300 dmg) |
| Double Light Beam | 13 | 150 | 2.0s | Beams in facing + opposite direction |
| Portal | 15 | 175 | 60.0s | Teleport to last visited town |
| Safe Space | 17 | 200 | 30.0s | Teleport to clear area, break all chases |
| Prison | 19 | 225 | 20.0s | Imprison nearest monster for 30s (cannot move or attack) |
| Arcane Resurrection | 20 | 250 | auto | Auto-trigger on death: revive + portal to last town |

**Paladin spells (6 total, min_level 1–20):**

| Spell | min_level | Mana Cost | Cooldown | Type |
|-------|-----------|-----------|----------|------|
| Holy Smite | 1 | 15 | 1.5s | AoE circle 110px radius, 30 dmg |
| Double Holy Smite | 5 | 40 | 2.0s | AoE circle 220px radius, 30 dmg |
| Holy Cross | 9 | 50 | 3.0s | Beams in all 4 directions |
| Holy Shield | 13 | 60 | 15.0s | Absorb 50 HP damage |
| Holy Healing | 17 | 70 | 30.0s | Full HP restore |
| Resurrect | 20 | 80 | auto | Auto-trigger on death: revive in place |

**Spell controls:**
- **Keyboard:** Q key (`KEY_SPELL = pygame.K_q`) → casts **currently selected** spell
- **1–9 keys:** Select spell by number
- **Controller:** RB button (`CONTROLLER_BUTTON_RB = 5`) → casts selected spell
- **D-pad Left/Right (gameplay):** Cycle through unlocked spells
- Per-spell cooldowns tracked in `player.spell_cooldowns` dict. "Not enough mana!" HUD message shown when mana is insufficient.

**Implementation:**
- `player.mana_regen` (float): Per-hero passive mana regeneration rate in mana/sec. Applied in `update_buffs()` each frame.
- `player._spell_list`: List of spell dicts from `SPELL_DEFS[hero_id]`.
- `player.spell_cooldowns`: Dict `{spell_id: remaining_cooldown}`.
- `player.selected_spell_idx`: Index into `get_castable_spells()`.
- `player.get_castable_spells()`: Returns spells with `min_level <= player.level` (non-auto-trigger only).
- `game._activate_selected_ability()`: Unified Q/RB dispatch → `_cast_ability(ab)` or `_use_grit_ability_by_def(ab)`.
- `game._cast_ability(ab)`: Dispatches on `ab["type"]`: beam, aoe_circle, shield, fireball, magic_missile, polymorph, double_beam, holy_cross, portal, safespace, prison, heal_full, resurrection.
- `game._trigger_fireball_explosion(proj)`: AoE circle damage + visual when fireball `_exploded` flag is set.
- `SpellEffect` class (in `game.py`): Timer-based visual effect with `draw()` method supporting "beam", "aoe_circle", and "cone" types. Alpha fades over duration.
- `_beam_hitbox()`: Module-level helper creating a thin `pygame.Rect` along the beam direction for collision detection.
- `game.spell_effects`: List tracking active spell visuals, updated/drawn each frame.

### Shield System

The shield system absorbs raw incoming damage before armor is applied.

- `player.shield_hp` (int): Current shield absorption points (0 = no shield).
- When damage is taken, `shield_hp` absorbs first: `absorbed = min(shield_hp, raw_damage)`. Any remaining damage proceeds through armor calculation.
- Shields are set by spells/abilities: Mage Shield = 100 HP, Paladin Holy Shield = 50 HP, Warrior Steel Skin = 100 HP.
- **Visual:** Pulsing blue circle drawn around the player while `shield_hp > 0`. The circle is centered at the sprite's vertical midpoint (`py - TILE_SIZE * 0.75`, i.e. half the 1.5×TILE_SIZE sprite height above the feet) with radius `TILE_SIZE * 1.05 + pulse * 4` (~50–54 px at TILE_SIZE=48). This ensures the shield bubble visually covers the full character sprite rather than just the lower half. Implemented in `game._draw_persistent_buffs()`.
- Shield HP is saved/loaded with game state.
- **Blazing Sword visual:** While `blazing_sword_timer > 0`, `_draw_persistent_buffs()` draws 6 animated flame-polygon "tongues" extending 100px from the player in their facing direction. Each tongue uses three nested polygon layers (deep red → orange → yellow) that flicker independently via `sin(time + index)` phase offsets, plus a bright white-yellow core line. No external library required — rendered entirely with `pygame.draw.polygon` and a full-screen SRCALPHA surface.

### Spell Selection HUD

A numbered spell/ability list is drawn on the **left side of the screen** below all other upper-left HUD elements.

- Each row: `[N] SpellName  {cost}mp/grit`
- **Gold background + gold text:** Currently selected spell
- **Gray text:** Ability on cooldown (with remaining seconds shown)
- **Red text:** Not enough mana/grit to cast
- **White-ish text:** Available and not selected
- **Purple text (below list):** Auto-trigger resurrection (unlocked, cannot be manually cast)
- Up to 9 entries shown (max 9 visible at once with number keys 1–9)
- Selection changes are instant (no button press needed to activate the selection itself)
- Implemented in `hud.draw_spell_list()`, called from `hud.draw()`.
- **Positioning:** The list starts at `buff_y_start + active_buff_count * buff_line_h + 8px` — that is, directly below the weapon line, armor line, FPS counter (when visible), and any currently active consumable buffs. This prevents the spell list from overlapping the weapon/armor/buff text in the upper-left corner. `buff_y_start` already accounts for whether the FPS counter is visible.

### Resurrection System

All 4 hero classes gain a resurrection ability at level 20. These **auto-trigger on death** when selected and when the hero has enough resources.

- **Selection:** The resurrection ability appears in the spell list marked `[auto]`. It cannot be manually cast. Place it in focus by selecting it and it will fire automatically when the player dies.
- **Resource check:** `_get_selected_resurrection()` in `game.py` checks `player.get_auto_spell()` and resource availability before game-over.
- **Per-hero behavior:**
  - **Mage – Arcane Resurrection** (250 mana): Revive + portal to last visited town. Note: Mage max mana at level 20 = 240, so this requires mana from potions/other sources to actually trigger.
  - **Paladin – Resurrect** (80 mana): Revive in place.
  - **Warrior – Blazing Resurrect** (140 grit): Revive + deal 4× weapon damage to all monsters within 220px.
  - **Ranger – Bestial Resurrect** (80 grit): Revive in place.

### Monster States

Spells and abilities can apply special states to monsters:

**Polymorph** (Mage spell, level 9):
- Transforms the nearest monster (including bosses) to the next-weaker type in `POLYMORPH_PROGRESSION = ["wild_cat", "wild_dog", "bandit", "soldier", "guard", "commander"]`.
- Example: soldier → bandit, guard → soldier. A commander boss → guard-type boss.
- **Boss polymorph:** Bosses can now be targeted (previously excluded). When a boss is polymorphed, the `is_boss` flag is preserved and `BOSS_HP_MULT` / `BOSS_DAMAGE_MULT` are re-applied to the new type's base stats. The `_original_is_boss` attribute saves the flag for restoration. On revert, the boss returns to its original type with `is_boss` restored, at half HP with `is_enraged = True`. HUD shows "Boss Polymorphed to {new_type}!" message.
- Duration: 30 seconds. On revert, monster returns at half its original HP with `is_enraged = True`.
- Visual: Purple pulsing ring around the monster.
- `monster.polymorph(new_type, duration)` and `_revert_polymorph()` methods in `monster.py`.

**Trap** (Ranger ability, level 9):
- Freezes the nearest chasing/enraged monster for 30 seconds. Monster can still attack if player is in range, but cannot move.
- On release: `is_enraged = True` (immediately chases).
- Visual: Orange ring around the monster.
- `monster.is_trapped`, `monster.trap_timer`.

**Prison** (Mage spell, level 19):
- Imprisons the nearest chasing/enraged monster for 30 seconds. Monster cannot move OR attack.
- On release: `is_enraged = True`.
- Visual: Cage bar lines drawn over the monster.
- `monster.is_imprisoned`, `monster.prison_timer`.

**Cover of Darkness** (Ranger ability, level 13):
- Applies `is_darkened = True` to all chasing/enraged monsters for 30 seconds.
- While darkened: `is_enraged = False`, `is_chasing = False` — monsters stand idle.
- Visual: Dark blue ring around affected monsters.
- `monster.is_darkened`, `monster.darkened_timer`.

### Weapons
Define in `data/weapons.json`. Each weapon has:
- `name`: Display name
- `damage`: Base damage value
- `range`: Attack reach in pixels/tiles
- `speed`: Attack cooldown
- `style`: Weapon visual style — one of `"sword"`, `"axe"`, `"staff"`, `"legendary"`, `"bow"`, `"gun"` — determines the procedural weapon graphic, trail color, and inventory icon
- `blade_color`: RGB color array for the weapon's blade/head (e.g., `[190, 200, 220]`)
- `icon`: Icon pack reference (used in HUD)
- `sound_swing`: Sound effect for swinging/firing
- `sound_hit`: Sound effect on contact
- `projectile_speed` (ranged only): Projectile travel speed in pixels/sec. A weapon is considered ranged if `projectile_speed > 0`.
- `projectile_style` (ranged only): `"arrow"`, `"bullet"`, or `"magic"`
- `dual_attack` (optional, bool): If `true`, the weapon performs a melee swing AND fires a projectile simultaneously on each attack. Used by Battle Staff. Checked via `weapon.is_dual` property in `src/weapon.py`. In `game._do_attack()`, dual weapons execute the full melee combat pass and then additionally spawn a projectile.
- `classes` (optional): List of hero IDs that can wield this weapon. Omitted or empty = all heroes. E.g., `["warrior"]`, `["warrior", "paladin"]`. Enforced in `player.equip_weapon()` — returns `False` on failure (same pattern as armor), showing "Cannot wield {name}!" in the HUD.

**Weapon class restrictions:**

| Weapon | Classes |
|--------|---------|
| Basic Sword | All |
| Steel Sword | All |
| Iron Sword | Warrior |
| Long Sword | Warrior |
| Legendary Blade | Warrior, Paladin |
| Mythic Blade | Warrior, Paladin |
| Great Axe | Paladin |
| War Axe | Paladin |
| Magic Staff | Mage |
| Battle Staff | Mage |
| Mage Bolt Staff | Mage |
| Hunter's Bow | Ranger |
| Crossbow | Ranger |
| Flintlock Pistol | Ranger |

Warrior and Paladin both start with Basic Sword. Class restrictions are shown in the Help screen WEAPONS table (Classes column).

**Melee weapon styles:** Each melee style draws a distinct shape via `_create_weapon_surface()` in `src/player.py`:
- **sword**: Standard blade + guard + handle (default). Trail: white/yellow.
- **axe**: Short handle + wide triangular axe head. Trail: orange.
- **staff**: Thin pole with glowing orb on top. Trail: purple/blue.
- **legendary**: Longer sword with golden guard, bright blade, and glow aura. Trail: gold.

**Ranged weapon styles:** Ranged weapons fire projectiles instead of melee swings. Any weapon with `projectile_speed > 0` is ranged (checked via `is_ranged` property in `weapon.py`):
- **bow**: Curved wooden arc + string. Fires arrow projectiles. Recoil animation on fire.
- **gun**: Metal barrel + body + handle. Fires bullet projectiles with muzzle flash effect.
- **staff (ranged)**: Staff with `projectile_speed > 0` (e.g., mage_bolt). Fires magic projectiles (purple glowing orb). Staff visual with purple muzzle flash.

**Dual-attack weapons** (`dual_attack: true` in `weapons.json`): Perform a melee swing AND fire a projectile on the same attack input. The weapon is not considered purely ranged — `is_ranged` returns `True` (projectile_speed > 0) but `is_dual` also returns `True`. In `_do_attack()`, the melee hitbox is calculated first, then a projectile is spawned in the player's facing direction. Currently only: **Battle Staff** (Mage, 40 dmg, 300px range, projectile_speed 350, magic style).

Weapon surfaces are cached by `(style, blade_color, angle)` to maintain 60 FPS performance.

**Projectile system** (`src/projectile.py`):
- Projectiles travel in the player's facing direction at `projectile_speed`
- **Projectile collision rect: 16×16 pixels** (centered on projectile center). This wider hitbox gives more reliable hit detection when visually near a monster.
- Projectiles collide with obstacles (walls, objects), monsters, and treasure chests
- On monster hit: apply damage, destroy projectile
- On chest hit: apply damage to chest, destroy projectile; if chest is destroyed, spawn loot
- Projectiles have a max range (weapon `range` field) and despawn after traveling that distance
- Arrow sprites: elongated triangle with shaft and fletching, gray trail
- Bullet sprites: small bright circle with glow, golden trail
- Magic sprites: purple/blue glowing orb with outer glow, purple trail
- All projectile styles have trailing particle effects

Bigger/rarer weapons deal more damage and may have more range. Player starts with a default weapon based on their hero class (Warrior: basic sword, Mage: mage bolt staff, Ranger: crossbow, Paladin: basic sword).

### A* Pathfinding (`src/pathfind.py`)

Lightweight A* pathfinding used by enraged monsters and bosses to navigate around obstacles. Uses **proactive pathfinding** — paths are always maintained and refreshed every 1.5 seconds rather than waiting for a monster to get completely stuck first.

**Module functions:**
- `build_walkable_grid(obstacles, grid_cols, grid_rows, tile_size)` — Rasterises a list of obstacle `pygame.Rect`s onto a 2D boolean grid (`True` = walkable). Grid is sized to the stage's tile dimensions.
- `astar(grid, start, goal)` — Standard heap-based A* on the boolean grid with 4-directional movement. Returns a list of `(col, row)` tile coordinates from start to goal inclusive, or `None` if no path exists. Clamps out-of-bounds start/goal to grid edges and snaps blocked tiles to nearest walkable via BFS.
- `has_los(grid, start_tile, goal_tile)` — Bresenham line-of-sight check on the tile grid. Returns `True` if the straight line between two tiles passes through no blocked tiles. Used as a performance shortcut: when LOS is clear, the monster chases directly without needing to follow A* waypoints.
- `_nearest_walkable(grid, x, y, cols, rows)` — BFS outward to find the nearest walkable tile (used internally to handle blocked start/goal positions).

**Integration in `src/monster.py`:**
- **Proactive approach:** When `is_enraged` first becomes `True` (from damage, proximity aggro, or chase start), `_path_recompute_timer` is reset to 0, triggering an immediate A* path computation on the next update frame.
- **1.5s refresh:** Every 1.5 seconds during chase, `_recompute_path()` recomputes the A* path regardless of whether the monster is moving or stuck. This eliminates the "stuck for 0.5s before routing" delay of the previous approach.
- **LOS shortcut:** Each frame, `has_los()` checks for a clear direct line to the player. If LOS is clear, the monster chases directly (natural movement); if blocked, it follows the A* waypoint path.
- **Dynamic grid size:** `_recompute_path()` derives grid size from actual obstacle extents (`max obstacle tile + 2`) instead of a hardcoded 50×50 — correctly covers both combat stages (50 tiles) and large town stages (up to 80 tiles). Capped at 120 to bound computation cost.
- State fields on Monster: `stuck_path` (list of world-coord tuples), `stuck_path_idx` (int), `_path_recompute_timer` (float).
- Constants in `src/settings.py`: `PROXIMITY_AGGRO_RANGE = 150` (px), `CHAIN_AGGRO_RANGE = 120` (px).

### Items

Items are defined in `data/items.json`. Every item has:
- `id`: Unique identifier
- `name`: Display name
- `type`: One of `weapon`, `consumable`, `sellable`, `armor`
- `icon`: Path to icon from icon pack (used in inventory, ground, shop)
- `value`: Gold value (for buying/selling)
- `stack_max`: Maximum stack size (default 20, weapons/armor stack to 1)
- `description`: Short tooltip text
- `weapon_id` (weapon items only): Links to weapon definition in `data/weapons.json`
- `armor_id` (armor items only): Links to armor definition in `ARMOR_DEFS` in `settings.py`

**Item types:**

| Type | Behavior | Examples |
|------|----------|---------|
| `weapon` | Can be wielded via right-click in inventory. Replaces currently equipped weapon. Old weapon goes back into inventory. Does not stack (stack of 1). Has a `weapon_id` field linking to `data/weapons.json`. | Swords, axes, staves, legendary blades, bows, guns |
| `consumable` | Eaten/used via right-click in inventory. Grants a short-term buff (HP regen, damage boost, speed boost) for a set duration. Removed from inventory on use. Stackable up to 20. **Heal items are NOT consumed when HP is already full** — the game shows "HP is already full!" and the item is kept. | Potions (red=HP, blue=damage, green=speed), Berries, Mushrooms |
| `sellable` | No direct use — exists to be sold for gold at shop NPCs. Stackable up to 20. | Monster parts, gems, trinkets, junk drops |
| `armor` | Can be equipped via right-click in inventory. Replaces currently equipped armor. Old armor goes back into inventory. Does not stack (stack of 1). Has an `armor_id` field linking to `ARMOR_DEFS` in `settings.py`. Class restrictions apply — if a hero cannot wear the armor, shows "Cannot wear {name}!" message. | Leather Armor, Padded Armor, Chain Shirt, Chain Mail, Half Plate, Full Plate |

**Consumable buffs:**
- Each consumable defines a `buff_type` (heal, damage_up, speed_up, defense_up), `buff_value`, and `buff_duration` (seconds)
- Only one buff of each type can be active at a time; consuming another of the same type refreshes the duration
- Active buffs shown as small icons on the HUD with remaining duration

**Visual assets for items:**
- Potions: `newassets/objects/Potion_red.png`, `Potion_blue.png`, `Potion_green.png`
- Sword: `newassets/objects/Sword.png`
- Food: `newassets/objects/Mushroom_1-4.png`, Crops (Berries, Carrot, Sunflower)
- Chests (loot containers): `newassets/objects/Chest_big.png`, `Chest_small.png`
- Icons for inventory UI: `newassets/icons/`

**Sellable item procedural icons** (40×40 SRCALPHA surfaces generated in `game._load_item_icons()`):
- **`cat_fang`** — Curved ivory fang: narrow tapered polygon with rounded root, dark pointed tip, center groove line, red root band at top.
- **`bandit_coin`** — Crude bronze/gold coin: outer jagged circle (12-point star polygon), inner flat circle, rough "X" mark in center, dark gold palette.
- **`dog_pelt`** — Animal hide: irregular 10-point brown polygon (asymmetric, scraggly), lighter inner concentric polygon, short dark "fur" lines radiating from edges.
- **`soldier_medal`** — Ribbon medal: red/blue vertical ribbon strip at top, circular gold medal body below, small 5-pointed star in center, thin border ring.
- **`guard_badge`** — Shield badge: hexagonal dark-blue badge shape, gold horizontal bar across upper third, white 5-pointed star in lower half, silver border, gold outer ring.
- **`commander_insignia`** — Military insignia: dark navy circle background, gold spread-wing shape (two angled polygons), center gold circle, 5 gold sunburst rays radiating above the wings.
- **`crystal`** — Glowing gem: tall 6-sided icy blue diamond polygon, lighter left facet, white top highlight facet, sparkle lines, three concentric alpha-circle glow halos in cyan/blue. Icons are keyed by `"icon"` field in `data/items.json` and looked up in `game._item_icons` dict.

### Armor System

Armor provides permanent damage reduction. Defined in `ARMOR_DEFS` dict in `settings.py`. Six tiers of armor with increasing defense values and class restrictions.

**Armor tiers:**

| Armor | Defense | Value | Classes |
|-------|---------|-------|---------|
| Leather Armor | +2 | 40g | All (Warrior, Paladin, Mage, Ranger) |
| Padded Armor | +4 | 100g | All (Warrior, Paladin, Mage, Ranger) |
| Chain Shirt | +6 | 200g | Warrior, Paladin only |
| Chain Mail | +8 | 350g | Warrior, Paladin only |
| Half Plate | +10 | 550g | Warrior, Paladin only |
| Full Plate | +12 | 900g | Warrior, Paladin only |

**Armor mechanics:**
- Player has `equipped_armor` attribute (dict with armor info, or `None`)
- `player.equip_armor(armor_id)` method handles equipping: returns old armor dict, `False` for class restriction failure, or `None` if no previous armor
- Class restriction checked via `player.hero_id` against `ARMOR_DEFS[armor_id]["classes"]`
- Damage formula: `actual = max(1, raw_damage - armor_defense - buff_defense)`
- Armor defense is permanent (until swapped); buff defense from Iron Mushroom is temporary
- **HUD indicator:** Armor name and DEF value shown below weapon indicator in white text on a black semi-transparent box for readability. "Armor: None" shown in the same style when no armor is equipped.

**Armor icons (procedural, 40x40 pixels):**
- `armor_leather` — Brown shield shape
- `armor_padded` — Tan shield with quilting lines
- `armor_chain` — Silver shield with ring pattern
- `armor_plate` — Steel shield with gold cross emblem

**Armor in drop tables:**
- wild_cat/wild_dog: leather 2-3%
- bandit: padded 3%
- soldier: chain_shirt 3%
- guard: chain_mail 4%
- commander: half_plate 4% (stage 6+), full_plate 2% (stage 9+)
- treasure_chest: chain_shirt 10% (stage 1+), chain_mail 8% (stage 3+), half_plate 6% (stage 5+), mythic_blade 5% (stage 7+), full_plate 4% (stage 9+)
- boss_treasure_chest: half_plate 12% (stage 3+), legendary_blade 10% (stage 5+), full_plate 8% (stage 7+)

**Armor in shops (progression by town):**
- town_1-2: Leather Armor
- town_3-4: Padded Armor, Chain Shirt
- town_5-6: Chain Shirt, Chain Mail
- town_7-8: Chain Mail, Half Plate
- town_9: Full Plate

**Help screen:** ARMOR table between ITEMS and ENEMIES sections shows all 6 tiers with Name, Defense, Value, and Class columns. Armor items also listed under "Armor Items" subsection in the ITEMS section.

### Gold

- Gold is a currency tracked as a simple integer on the player (not an inventory item)
- Gold can be found on the ground as a pickup (uses Coin sound: `newassets/sounds/game/Coin.wav`)
- Gold drops from killed monsters (amount varies by monster type/level)
- Gold is spent at shops in town stages
- Gold count displayed on the HUD

### Inventory System

- **Grid:** 5 columns x 5 rows = 25 slots
- **Stacking:** Identical items stack in the same slot up to 20. Weapons do not stack (1 per slot).
- **Toggle:** Press `I` or `Tab` to open/close the inventory overlay
- **Mouse interaction (when inventory is open):**
  - **Right-click** a slot: Use the item (wield weapon, eat consumable). When wielding a weapon, the currently equipped weapon is placed back into the same inventory slot. Sellable items show a "Cannot use" tooltip.
  - **Left-click** a slot (no held item): Pick up the item stack onto the cursor
  - **Left-click** a slot (holding an item): Place held item into slot. If slot has a different item, swap them. If same stackable item, merge stacks.
  - **Left-click** outside the grid (holding an item): Drop held item onto the ground
  - Closing inventory while holding an item puts it back into inventory (or drops if inventory is full)
- **Full inventory:** If inventory is full and player tries to pick up an item, show a "Inventory full" message on the HUD. Item remains on the ground.
- **Inventory UI:** Rendered as a centered overlay with a semi-transparent background. Each slot shows the item icon and stack count (if > 1). Hovering a slot shows a tooltip with item name, type, and description. Held item follows the cursor.
- **Controller inventory navigation:** D-pad moves a gold-bordered cursor through the grid (`inventory.gamepad_cursor`). A button uses/equips item. Y button drops item. B/X/Back/START closes inventory. Tooltip appears next to cursor slot with controller-specific hints. Cursor activates (index 0) when inventory is opened via controller and deactivates (-1) on close.
- **Resolution scaling:** Inventory slot sizes and padding scale with resolution via `settings.scaled_slot_size()` and `settings.scaled_padding()`. Layout is recalculated on `toggle()` and `draw()`. Shop inventory panel also uses these scaled values.

### Loot and Pickups

**Ground items:**
- Items and gold can exist on the ground as small sprites at a world position
- Ground items have a subtle bobbing animation or glow to make them visible
- Press `E` when the player is within pickup range to collect the nearest ground item
- Pickup plays a sound: `newassets/sounds/game/Coin.wav` for gold, `newassets/sounds/game/Bonus.wav` for items
- **Pickup messages show the item name:** "Picked up Red Potion", "Picked up 15 Gold", "Picked up Iron Sword". `combat.try_pickup()` returns a descriptive string (or `None`) instead of a boolean.

**Monster drops:**
- When a monster dies, it may drop gold and/or items based on its drop table (`data/drop_tables.json`)
- **CRITICAL:** Drop table keys must exactly match the monster type strings used in `STAGE_MONSTERS` and `STAGE_BOSSES` in `settings.py`. Current valid keys: `wild_cat`, `wild_dog`, `bandit`, `soldier`, `guard`, `commander`.
- Drop table defines: list of possible drops, each with `item_id`, `chance` (0.0-1.0), `quantity_min`/`quantity_max`, and optional `min_difficulty`
- **`min_difficulty`:** If present on a drop entry, the item is skipped when `difficulty < min_difficulty`. Used by chest tables AND commander drops to gate weapon/armor drops to appropriate stages. Filtered in `loot.roll_drops()`.
- Gold drop: `gold_min` and `gold_max` per monster type
- Weapon items can drop from tougher monsters (e.g., iron_sword from bandits, legendary_blade from commanders at stage 7+)
- Armor items can drop from monsters (leather from wild animals, chain from soldiers, plate from commanders at stage 6+) and treasure chests
- Boss monsters have richer drop tables (rare weapons, more gold, more items)
- Drops spawn at the monster's death position

**Commander drop table (boss-only, stages 6–10):**

| Item | Chance | min_difficulty | First available |
|------|--------|----------------|-----------------|
| Commander Insignia (sellable) | 60% | — | Stage 6 |
| Crystal (sellable) | 20% | — | Stage 6 |
| Red Potion | 30% | — | Stage 6 |
| Great Axe (45 dmg, Paladin) | 8% | 2.5 | Stage 6 |
| Flintlock (42 dmg, Ranger) | 4% | 2.5 | Stage 6 |
| Half Plate (DEF 10) | 4% | 2.5 | Stage 6 |
| Legendary Blade (60 dmg, Warrior/Paladin) | 4% | 2.8 | Stage 7 |
| Full Plate (DEF 12) | 2% | 3.4 | Stage 9 |

**Treasure chests:**
- Destructible treasure chests are scattered randomly across combat stages (3-6 per stage)
- Chests are solid objects — entities cannot walk through them
- Player destroys chests by attacking them (same attack key as monsters). Chests have HP (30-50, scaling with stage difficulty)
- On destruction, chests drop gold and items using the chest's `drop_table_key` attribute (`treasure_chest` or `boss_treasure_chest`) from `data/drop_tables.json`
- Chests can drop enhanced "chest weapons" with 2x the range of monster attack ranges (110-150px vs monster 55-75px)
- Chest weapons: Long Sword (range 110), War Axe (range 120), Mythic Blade (range 130), Battle Staff (range 150)
- **Chest drops scale with stage difficulty** via `min_difficulty` thresholds on weapon/armor entries. Potions always drop; weapons and armor unlock at stage-appropriate difficulty tiers:
  - 1.0 (stage 1+): Hunter's Bow, Chain Shirt | Boss: Battle Staff, War Axe
  - 1.6 (stage 3+): Long Sword, Crossbow, Chain Mail | Boss: Flintlock, Mythic Blade, Half Plate
  - 2.2 (stage 5+): Battle Staff, War Axe, Flintlock, Half Plate | Boss: Legendary Blade
  - 2.8 (stage 7+): Mythic Blade | Boss: Full Plate
  - 3.4 (stage 9+): Full Plate | Boss: —
- **Normal chests:** Procedural brown box with gold trim. Placed away from player start, exit portal, boss area, and existing obstacles.
- **Boss area chests:** 2-4 golden chests with red gem lock placed inside the boss encounter area. These are `locked=True` until the boss is defeated — they cannot take damage from melee or projectile attacks while locked. On boss defeat, `stage.unlock_boss_chests()` is called: chests switch to green gem (unlocked) and become breakable. Boss chests use the `boss_treasure_chest` drop table with higher gold (30-80) and better rare weapon/armor drop rates. Boss chests unlock gear one tier earlier than normal chests.
- A visual shake effect plays when a chest is hit, and a destruction sound plays when broken
- Locked chests display a red lock indicator above the chest sprite

### Shops and Town Stages

**Stage progression:** Combat and town stages alternate:
```
Stage 1 (combat) → Town 1 (shop) → Stage 2 (combat) → Town 2 (shop) → ... → Stage 10 (final boss)
```

**Town stages:**
- Smaller maps (e.g., 30x30 to 50x50 tiles) with no hostile monsters
- **Randomized layout each playthrough** — town stage seeds include a time-based component (`int(time.time() * 1000) % 999999`) so the layout is different every time. Combat stage seeds remain deterministic.
- **Fully randomized map geometry**: Player start and exit positions are randomly placed on different sides (top/bottom/left/right). Obstacles are scattered randomly with biome-appropriate palettes.
- **Town biome matches the preceding combat stage** — `generate_stage()` uses `STAGE_THEMES.get(stage_num, "forest")` for towns, so stages 1–4 towns are forest, stages 5–7 towns are desert, and stages 8–10 towns are dungeon. Ground/path colors and obstacle palettes change accordingly:
  - **Forest** (stages 1–4): barrels, crates, stumps, bushes; flowers and tall grass decoration; wells
  - **Desert** (stages 5–7): barrels, crates, rocks; flowers and small rock decoration; wells
  - **Dungeon** (stages 8–10): barrels, crates, stumps; flowers decoration; no wells
- Use interior or outdoor village tilesets from `newassets/tileset/`
- **Merchant NPC varies per town** — each town randomly selects a merchant sprite type from `MERCHANT_NPC_TYPES` in `settings.py`, placed at a random position in the town center area
- Contains 3-5 flavor NPCs; ~40% wander on patrol routes, the rest stand idle. NPCs are placed in obstacle-free positions, and patrol points are guaranteed to be offset from the NPC's spawn position (no zero-distance patrols).
- **NPC speech bubbles** — non-merchant NPCs display random speech bubbles (from `NPC_SAYINGS` in `settings.py`) when the player approaches (within 3 tiles). Bubbles appear for 3 seconds with a cooldown of 6-12 seconds. NPCs detect when the player *enters* their range (approach detection via `_player_was_nearby` flag) and always speak immediately on new approach (ignoring cooldown). While the player stays nearby, additional sayings trigger after the cooldown expires. NPCs always pick a different saying from the last one (`_last_saying_index` avoids repeats). Sayings include greetings like "Hello!", "Good day!", "Nice fishing!", "Watch out for monsters!", etc.
- Background music: town rotation from `TOWN_MUSIC_ROTATION` (`menu`, `emotional`) via the Fantasy RPG Complete OST

**Shop system:**
- Player approaches a Merchant NPC and presses `E` (keyboard) or `B` (controller) to open the shop UI
- A gold-colored proximity hint ("Press E to Shop" / "Press B to Shop") appears when near a merchant
- Shop UI has two panels side by side:
  - **Left panel — Shop inventory:** Items the merchant sells, each with a name, icon, and gold price. Click to buy (if player has enough gold).
  - **Right panel — Player inventory:** The player's 5x5 inventory grid. Click an item to sell it for its gold value.
- **Item tooltip panel:** When the cursor (mouse hover or gamepad) rests on any item in either panel, a description panel appears above the two panels showing: item name + type, description text, stat lines (consumable effects with duration, armor DEF + class restrictions), and buy/sell price. Implemented in `shop._build_item_tooltip_lines()` and `shop._draw_tooltip_panel()`.
- **Controller shop navigation:** D-pad navigates items, A button buys/sells, LB/RB or D-pad left/right switches panels, B/Back/START closes shop. Gold cursor highlights active item. Panel titles adapt to show controller instructions.
- Shop inventories defined in `data/shops.json` per town stage. Later towns sell better/rarer items at higher prices.
- Selling price = item `value`. Buying price = item `value` (or a markup, e.g., 1.5x value).
- **Hold-to-sell (mouse):** Holding the left mouse button on a player inventory slot in the shop continuously sells items from that slot. Initial delay: 0.5 seconds before repeat begins; then one item sold every 0.12 seconds until the stack is empty or the button is released. Implemented via `shop.update(dt, mouse_pos, player, audio)` called each frame, using `pygame.mouse.get_pressed()[0]` and tracking `_sell_hold_timer`, `_sell_hold_slot`, `_sell_hold_triggered` state. `game.py` calls `self.active_shop.update(dt, pygame.mouse.get_pos(), self.player, self.audio)` when the shop is open.
- **Hold-to-sell (controller):** Holding the A button while the gamepad cursor is on the inventory panel continuously sells items with the same timing (0.5s initial delay, 0.12s repeat). Tracked via `_shop_ctrl_hold_timer`, `_shop_ctrl_hold_triggered`, `_shop_ctrl_hold_initial`, `_shop_ctrl_hold_interval` in `game.py`. Checked each frame using `joystick.get_button(CONTROLLER_BUTTON_ATTACK)` in the shop update block.
- **Shop inventory hover tooltip:** Fixed if/elif priority bug — previously `gamepad_panel == "shop"` (always True by default) prevented mouse-hover inventory tooltips from appearing. Now mouse hover state (`hovered_inv_slot`, `hovered_shop_item`) takes highest priority over gamepad panel state, so hovering the player inventory always shows the correct item tooltip.
- Weapons, armor, consumables, and sellable items can be bought and sold. Armor progresses from leather (early towns) to full plate (final town).
- Sound effects: `newassets/sounds/game/Gold1.wav` for transactions, `newassets/sounds/menu/Accept1.wav` for confirm

### Experience and Leveling
- Monsters award XP on death. Higher-level monsters give more XP.
- XP thresholds increase per level: level 2 = 100 XP, level 3 = 250 XP, ..., **level 20 = 150,000 XP**. Full table in `XP_THRESHOLDS` in `settings.py`.
- **Maximum level is 20.** New spells/abilities unlock at levels 3, 5, 7, 9, 11, 13, 15, 17, 19, and 20.
- **Per-hero XP multiplier:** `xp_required_mult` in `HERO_CHARACTERS` scales how much XP is needed to level. Warrior and Ranger have `xp_required_mult: 0.667` (need only 2/3 of base XP). Mage and Paladin default to 1.0. Applied in `player.gain_xp()` and the HUD XP bar via `hud._get_xp_for_next/current(level, xp_mult)`.
- On level up: max HP increases, damage may increase. HUD message shown if a new spell/ability just unlocked.
- Display current level, XP progress, and HP on the HUD

### Death Animation

When the player's HP reaches 0 (and no resurrection ability fires), the game enters `STATE_DYING` for 1.5 seconds before transitioning to `STATE_GAME_OVER`. No hero die-sprite sheets exist in the asset library, so the death animation is procedural.

**Visual effect** (`game._draw_dying()`):
- The world is drawn normally in the background (other entities remain visible)
- The player sprite is drawn with:
  - **Red tint** — increasing from 0 → 190 alpha overlay as `t` goes 0 → 1
  - **Fade out** — alpha subtracted proportionally so the sprite becomes transparent by the end
  - **Spin** — the sprite rotates clockwise 0 → 180 degrees over the 1.5s duration
- After 1.5 seconds, transitions to `STATE_GAME_OVER` which draws the red "GAME OVER" overlay

**Game states involved:**
- `STATE_DYING = "dying"` — new state added between `STATE_PLAYING` and `STATE_GAME_OVER`
- `game._dying_timer` (float): elapsed seconds in dying state
- `game._dying_duration = 1.5`: duration of the animation
- All player input is blocked during `STATE_DYING` (the state has no input handlers)
- Music auto-continue is suppressed in `STATE_DYING` (same as `STATE_GAME_OVER`)

### Hit Points
- **Player:** Starts with base HP, gains more per level
- **Monsters:** HP scales with monster type and level. Small monsters (slime, bat) have low HP. Large monsters (ogre) have high HP.
- **Bosses:** Significantly more HP than regular monsters. May also deal more damage.
- **NPCs:** Have HP but are not typically attackable (friendly)

### Entity Speeds
- Player speed > Boss speed (player can always outrun a boss)
- Regular monsters may be slower or equal to player
- NPCs move slowly on patrol routes
- **Regular monster enrage:** Any non-boss monster that survives a hit permanently switches to chasing the player at its full `self.speed`. Overrides stand and patrol behaviours. No timer — lasts until the monster dies.
- **Boss chase behavior:** Boss follows player for `BOSS_CHASE_DURATION` seconds at `BOSS_CHASE_SPEED` after entering chase range or taking damage, then stops.

### Stages
- **Minimum 10 combat stages**, each is a 50x50 tile map
- **Intermediate town stages** between each combat stage (see "Shops and Town Stages" above)
- Full progression: Combat 1 → Town 1 → Combat 2 → Town 2 → ... → Combat 10 (final boss)
- Total stages: ~19 (10 combat + 9 town)
- Each combat stage has an exit point (portal, door, path edge) leading to the next town stage
- Each town stage has an exit leading to the next combat stage
- Each combat stage has a **boss encounter area** — either:
  - A cluster of tightly packed enemies, OR
  - A single large boss creature with enhanced damage/HP
- The **final boss** (stage 10) can chase the player
- Monster difficulty and loot quality increase with each stage
- Use varied tilesets across stages from `newassets/tileset/`:
  - Forest stages: grass tileset + trees
  - Snow stages: snow tileset
  - Interior/village stages: interior tileset

### Boss Encounters
- Boss area is a distinct section of each stage
- Boss music (`Battle-LOOP.mp3`, track key `"battle"`, from the Fantasy RPG Complete OST `06 Battle` folder) plays when entering a boss area **or when the boss is actively chasing the player** (even outside the boss area). The `boss_chasing` flag in `game.py` checks if any boss monster has `is_chasing=True`. Boss music continues as long as the player is in the boss area OR the boss is pursuing them.
- **Boss music stops on boss death:** When the boss is defeated, combat music rotation resumes immediately. `_on_music_ended()` in `game.py` checks both `self.in_boss_area` and `self.boss_chasing` before replaying boss music. Re-entering the boss area after the boss is dead does not trigger boss music.
- Normal exploration music resumes after boss is defeated and is no longer chasing
- Final boss: large creature (e.g., Ogre or Krampus), can chase player, stops chasing after a set duration
- **Boss area monster spacing:** Extra monsters in the boss area must be placed at least `TILE_SIZE * 4` pixels away from the boss center to prevent entity-entity collision from trapping the boss. Monsters are placed around the edges of the boss area, not on top of the boss.
- **Boss area treasure chests:** 2-4 locked golden chests spawn inside the boss area. They unlock when the boss is defeated, showing a HUD message. See "Treasure chests" under Loot and Pickups.

**Boss progression by stage** (`STAGE_BOSSES` + `BOSS_STAGE_SCALING` in `settings.py`):

Each stage uses a different boss type for stages 1–5, escalating through all 6 monster tiers. Stages 6–10 reuse the commander but apply a `BOSS_STAGE_SCALING` multiplier on top of the standard `BOSS_HP_MULT` (×3) and `BOSS_DAMAGE_MULT` (×1.5). The `boss_scale` parameter is passed to `Monster.__init__()` and applied after the base boss multipliers.

| Stage | Boss Type | Scale | Boss HP | Boss Damage |
|-------|-----------|-------|---------|-------------|
| 1 | Wild Cat | ×1.0 | 45 | 8 |
| 2 | Wild Dog | ×1.0 | 75 | 15 |
| 3 | Bandit | ×1.0 | 120 | 18 |
| 4 | Soldier | ×1.0 | 165 | 27 |
| 5 | Guard | ×1.0 | 225 | 33 |
| 6 | Commander | ×1.0 | 360 | 42 |
| 7 | Commander | ×1.25 | 450 | 53 |
| 8 | Commander | ×1.5 | 540 | 63 |
| 9 | Commander | ×1.75 | 630 | 74 |
| 10 | Commander | ×2.25 | 810 | 95 |

**Implementation:** `stage.py` looks up `BOSS_STAGE_SCALING[stage_num]` and passes it as `boss_scale` to `Monster()`. `Monster.__init__()` applies: `hp = int(base_hp * difficulty * BOSS_HP_MULT * boss_scale)`. Help screen shows a per-stage boss table (Stage / Boss / Scale / HP / Damage columns) with stages 6–10 highlighted in orange.

### Audio System
- **Background music:** Each combat/town stage plays a track once (no looping) from a rotation list, so music varies per stage:
  - **Combat stages:** Rotate through `COMBAT_MUSIC_ROTATION` = [main_theme, enchanted_forest, undefined, intro]
  - **Town stages:** Rotate through `TOWN_MUSIC_ROTATION` = [menu, emotional]
  - **Boss encounters:** Play `BOSS_MUSIC` = "battle" once when entering boss area
  - **Menu/title screen:** Loops indefinitely
  - **Victory screen:** Plays "emotional" once
- **Music auto-continue:** When a track finishes playing (`MUSIC_END_EVENT` via `pygame.mixer.music.set_endevent()`), the next track from the rotation list plays automatically. No silence between tracks. Handler: `_on_music_ended()` in `game.py`.
- Music rotation indices reset on new game and advance with each stage transition
- `audio.py` checks `pygame.mixer.music.get_busy()` to allow replaying a track after it finishes
- **Sound effects:** Played on weapon swings, hits, kills, item pickups, gold pickups, shop transactions, inventory actions, level-ups, menu navigation
- **Volume sliders:** The first two rows of the pause menu (press ESC during gameplay). Music and SFX sliders adjusted via:
  - **Mouse click** on the slider bar to set volume
  - **UP/DOWN arrow keys** to navigate rows, **LEFT/RIGHT** to adjust by 10%
  - Volume persists for the session (default: music 50%, SFX 60%)
- Use MP3 format for music (smaller file size)
- Use WAV for effects (low latency)
- Sound effects loaded from `newassets/sounds/`; music loaded from `newassets/Fantasy RPG Complete OST/Fantasy RPG Complete OST- VHCMusic/` subfolders (`MUSIC_TRACKS` dict in `settings.py`)
- pygame.mixer for sound effects, pygame.mixer.music for background music

### Save/Load/Delete System

Save, Load, and Delete features are accessible from both the **Options screen** (main menu) and the **Pause menu** (during gameplay). Implemented in `src/savegame.py` (file I/O) and `src/game.py` (UI dialogs).

**Save files:** Stored as JSON in `saves/` directory at project root. Up to 10 named save slots (`save_0.json` through `save_9.json`). A separate **autosave file** (`saves/autosave.json`) is written automatically when exiting to the main menu. Directory created automatically on startup.

**Pause menu rows (always 5 rows during gameplay):**

| Row | Label | Input |
|-----|-------|-------|
| 0 | Music (slider) | LEFT/RIGHT adjusts volume |
| 1 | SFX (slider) | LEFT/RIGHT adjusts volume |
| 2 | Save Game | ENTER/A opens save dialog |
| 3 | Load Game | ENTER/A opens load dialog |
| 4 | Return to Menu | ENTER/A auto-saves then returns to menu |

Rows 0–1 are sliders; rows 2–4 are button rows. ESC always resumes immediately (no row needed). Controller START also resumes.

**Options screen rows (dynamic):**

| Row | ID | Condition | Input |
|-----|----|-----------|-------|
| 0 | music | Always shown | LEFT/RIGHT adjusts volume |
| 1 | sfx | Always shown | LEFT/RIGHT adjusts volume |
| 2 | resolution | Always shown | LEFT/RIGHT cycles resolutions |
| 3 | save | Only when game in progress (`player` alive) | ENTER/A opens save dialog |
| 4 | load | Always shown | ENTER/A opens load dialog |
| 5 | delete | Always shown | ENTER/A opens delete dialog |

`_options_rows()` returns the dynamic list; `pause_slider_sel` indexes into it. Row count adjusts (5 or 6) based on whether "save" is available.

**Autosave system:**
- `_exit_to_menu()` writes an autosave whenever the player leaves an active game to the main menu (via "Return to Menu" row in pause). The autosave captures the full game state (same as a manual save).
- On startup, `has_autosave()` checks whether `saves/autosave.json` exists. If so, a **green "Resume" button** appears on the main menu above "Start Game".
- Clicking Resume (or pressing A on controller with Resume highlighted) calls `_load_from_autosave()`, which restores game state and **deletes the autosave** so it isn't stale.
- `self.has_autosave` (bool) tracks whether the autosave file exists; updated after save and after delete.

**Main menu with Resume:**
- Resume button displayed when `self.has_autosave == True`, at 57% of screen height.
- Controller `menu_button_sel = 3` is Resume. D-pad DOWN from hero row goes to Resume first (if autosave exists), then to Start on next DOWN. D-pad UP from Start goes to Resume (if exists) before returning to hero row.
- Green border when not selected, gold border when highlighted by controller.

**Main menu Exit Game button:**
- Red-styled button below the Help/Options row (at ~82% of screen height), always visible.
- Controller `menu_button_sel = 4`. D-pad DOWN from Help/Options row reaches Exit; D-pad DOWN from Exit wraps to hero row.
- A button (controller) or click (mouse) sets `self.running = False` to quit. Sound: `menu_cancel`.
- Controls hint and enter hint lines are anchored `hint_gap` pixels below `exit_rect.bottom` (relative positioning) rather than fixed y-percentages, so they never overlap the button at any resolution.

**Game states:** `STATE_SAVE_DIALOG`, `STATE_LOAD_DIALOG`, `STATE_DELETE_DIALOG` — overlay states drawn on top of either the options screen or the pause overlay depending on `dialog_return_state`.

**`dialog_return_state`:** Tracks which state to return to after ESC in a dialog. Set to `STATE_OPTIONS` by `_activate_options_row()` and to `STATE_PAUSED` by `_activate_pause_row()`. All dialog ESC handlers and click-outside-panel handlers use this value instead of hardcoding `STATE_OPTIONS`.

**Save dialog flow:**
1. Player selects a slot (1-10) with UP/DOWN or D-pad
2. Presses ENTER to open text input for naming (up to 20 chars)
3. Types a name, presses ENTER to confirm or ESC to cancel
4. On controller: A button auto-names ("Save {N}" or existing name) and saves immediately
5. `_execute_save()` calls `save_game()` from `savegame.py`, then returns to `dialog_return_state`

**Load dialog flow:**
1. Shows occupied slots with save info; empty slots are grayed out and skipped
2. UP/DOWN navigates only occupied slots (`_dialog_cursor_next/prev_occupied()`)
3. ENTER/A loads the selected save and goes to `STATE_PLAYING`; ESC/B cancels to `dialog_return_state`
4. `_execute_load()` reconstructs player and game state from save data

**Delete dialog flow:**
1. Shows occupied slots; empty slots grayed out
2. ENTER/A on an occupied slot shows confirmation: "Delete '{name}'?"
3. ENTER/A confirms deletion; ESC/B cancels to `dialog_return_state`
4. `_execute_delete()` calls `delete_save()` from `savegame.py`

**What is saved:**
- Hero identity (hero_id, hero_name, selected_hero_index)
- Player stats (level, xp, hp, max_hp, mana, gold, base_damage)
- Equipped weapon (weapon_id string, reloaded from `weapon_db`)
- Equipped armor (armor_id string, reloaded from `ARMOR_DEFS`)
- Active buffs (type, value, remaining duration)
- Full inventory (25 slots, each `{item_id, quantity}` or null, reloaded from `item_db`)
- Stage progress (stage_num, stage_type)
- Music rotation indices (combat_music_index, town_music_index)
- **Multi-spell state:** selected_spell_idx, shield_hp, action_surge_timer, whirlwind_timer, blazing_sword_timer, double_fire_timer, last_town_num
- Save metadata (name, timestamp, version)

**What is NOT saved (regenerated on load):**
- Stage layout (procedurally regenerated from stage_num + stage_type)
- Player position (placed at stage start position)
- Ground items, gold drops, projectiles, floating texts (cleared on stage load)
- Monster positions and HP (regenerated)
- Camera (recreated from stage dimensions)

**Save file JSON structure:**
```json
{
  "version": 1,
  "name": "My Save",
  "timestamp": "2026-03-04 15:30:00",
  "hero_id": "warrior",
  "hero_name": "Warrior",
  "selected_hero_index": 0,
  "level": 5, "xp": 1200, "hp": 80, "max_hp": 100,
  "mana": 50,
  "grit": 30,
  "gold": 350, "base_damage": 18,
  "equipped_weapon_id": "iron_sword",
  "equipped_armor_id": "chain_shirt",
  "buffs": {},
  "inventory": [{"item_id": "potion_red", "quantity": 3}, null, ...],
  "stage_num": 3, "stage_type": "combat",
  "combat_music_index": 2, "town_music_index": 1
}
```

**Mouse support in dialogs:**
- Click a slot row to select (save: opens name input; load: immediately loads; delete: asks confirmation)
- Click outside the panel to cancel/close
- Text input field is editable by keyboard during save name entry

**Controller support in dialogs:**
- D-pad UP/DOWN navigates slots
- A button confirms (save/load/delete)
- B or Back button cancels
- Save dialog auto-generates name on controller (no on-screen keyboard needed)

**Error handling:**
- Corrupted save files: `list_saves()` and `load_save()` wrap JSON parsing in try/except, returning None on error
- Missing item/weapon IDs: skipped gracefully on load (item not added to inventory)
- Save file versioning: `"version": 1` field for future migration support

**Implementation files:**
- `src/savegame.py`: `ensure_saves_dir()`, `list_saves()`, `save_game()`, `load_save()`, `delete_save()`, `save_autosave()`, `load_autosave()`, `has_autosave()`, `delete_autosave()`, constants `MAX_SAVE_SLOTS=10`, `MAX_SAVE_NAME_LENGTH=20`, `AUTOSAVE_PATH`
- `src/game.py`: `_options_rows()`, `_activate_options_row()`, `_activate_pause_row()`, `_exit_to_menu()`, `_load_from_autosave()`, `_save_dialog_layout()`, `_draw_save_dialog()`, `_draw_load_dialog()`, `_draw_delete_dialog()`, `_handle_dialog_click()`, `_execute_save()`, `_execute_load()`, `_execute_delete()`, `_get_game_state_dict()`, `_start_save_name_input()`, `_dialog_cursor_next/prev_occupied()`
- `src/settings.py`: `SAVES_PATH` constant
- Dialog tracking attributes: `save_slots_cache`, `dialog_cursor`, `save_name_input`, `save_name_editing`, `delete_confirm`, `dialog_return_state`, `has_autosave`
- `TEXTINPUT` event handler in `handle_events()` for save name text input

## Sprite Sheet Conventions

All character and monster sprites are **sprite sheets** (multiple frames in a single PNG). To extract frames:
1. Read the dimensions from the filename, e.g., `(16x16)` means each frame is 16x16 pixels
2. The sprite sheet width / frame width = number of frames
3. Animate by cycling through frames at a consistent frame rate
4. Most sheets have 4 rows for 4 directions (down, left, right, up) — verify per asset

### Scale Selection
- Use **1x / 100%** assets as the base, then scale up in-engine for the display resolution
- Alternatively, use **2x / 200%** assets if targeting a higher resolution display
- Be consistent: pick one scale for all assets and stick with it

## Code Conventions

- Use Python type hints for function signatures
- Classes for game entities (Player, Monster, NPC, Weapon)
- pygame sprite groups for rendering and collision
- Constants in `src/settings.py` (TILE_SIZE, SCREEN_WIDTH, SCREEN_HEIGHT, FPS, scale factor, AVAILABLE_RESOLUTIONS, etc.)
- Modules that need dynamic resolution access (camera, hud, inventory, shop) use `import src.settings as settings` and reference `settings.SCREEN_WIDTH`/`settings.SCREEN_HEIGHT`. Resolution changes via `game.py._change_resolution()` update the settings module and recreate the display.
- **Font scaling:** All font creation uses `settings.scaled_font_size(base_size)` which scales relative to the base resolution height (768px). Font sizes are recalculated on resolution change: `game.py._create_fonts()` recreates game fonts, `hud.init_fonts()` recreates HUD fonts, and NPC speech fonts are lazily re-created on next draw. Base font sizes: title=64, big=48, standard=28, small=20, HUD=24, HUD small=18, NPC speech=18. Minimum font size is clamped to 12px.
- **Scaled UI layout:** All UI screens use `settings.get_font_scale()` to scale layout elements proportionally. Shared layout methods ensure draw and click handler use identical rects:
  - **HUD:** `hud._layout()` computes all HUD positions (HP/Mana/XP bars, level, gold, weapon, armor, FPS, buffs, messages, hint) scaled via `get_font_scale()`. No hardcoded pixel positions — all elements space correctly at any resolution. Mana bar (green, `MANA_BAR_GREEN`) shown between HP and XP bars only for heroes with `max_mana > 0`. Armor indicator shown below weapon line as white text on a black semi-transparent box ("Armor: Leather Armor (DEF: 2)" or "Armor: None") for readability against any background. FPS counter shown below armor when toggled on (green ≥55, yellow ≥30, red <30). Buffs shift down when FPS is visible. Control hints include 'Q:Spell' (keyboard) / 'RB:Spell' (controller). Control hints are rendered with the standard font (not small), centered at the bottom with a dark semi-transparent background for readability at all resolutions. Includes 'M:Map' control hint.
  - **Mini-map:** `hud.draw_minimap()` renders a toggleable overlay in the top-right corner (below stage info). Shows the entire stage scaled down with color-coded dots: white=player, red=monsters, larger red=boss, blue=NPCs, gold=merchants, yellow=chests, red squares=locked chests, purple=exit portal, dark red rect=boss area. Size scales with resolution (`150 * scale`). Toggled via `hud.toggle_minimap()` from 'M' key.
  - **FPS counter:** `hud.toggle_fps()` toggles `hud.fps_visible`. When visible, shows "FPS: {value}" below the armor indicator. Color-coded: green (≥55 FPS), yellow (≥30 FPS), red (<30 FPS). `hud.current_fps` is set by `game.py` from `clock.get_fps()` each frame. Toggled via 'F' key during gameplay.
  - **Pause screen:** `game._pause_layout()` computes all pause screen positions scaled via `get_font_scale()`. Slider width, height, knob radius, label gap, and row gap all scale proportionally — labels never overlap sliders at any resolution.
  - **Inventory:** Slot sizes via `settings.scaled_slot_size()`, padding via `settings.scaled_padding()`. Layout recalculated on `toggle()` and `draw()`.
  - **Shop:** `shop._recalc_layout()` scales panel width, panel height, row height, icon size, slot size, and title height. Called on `open()` to pick up current resolution. Uses a smaller font for in-slot price/quantity text to avoid occlusion.
  - **Options screen:** `_options_layout()` computes row spacing, slider sizes, button sizes, dot radii, arrow offsets. Row gaps are derived from actual font height so labels and controls never overlap.
  - **Main menu:** `_menu_layout()` computes button rects sized to fit rendered text (Start, Help, Options). Help and Options buttons are spaced with a scaled gap. Hero name offset above sprites scales with font height. Hero spacing scales with resolution.
  - **Help screen:** `_help_back_rect()` sizes the Back button to fit text. Content starts below the Back button (`back_rect.bottom + padding`). Weapons, armor, and enemies tables use pixel-based column positions (scaled) instead of character padding for proper alignment with proportional fonts.
  - **All Back buttons** auto-size to fit the "Back" text at any resolution.
- All asset paths in `src/settings.py` must point into `newassets/` — no other asset directories
- Stage data stored externally (JSON) so stages can be edited without code changes
- Keep game loop in `src/game.py`: handle input -> update -> draw -> clock tick
