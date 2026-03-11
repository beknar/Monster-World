# Monster World

A 2D top-down action RPG built with Python and pygame. Fight your way through 10 combat stages, level up, collect loot, shop in towns, and defeat increasingly powerful bosses.

---

## Download and Play

**If you'd like to download the executable, it is available for free here: https://beknar777.itch.io/monster-world**

---

## ⚠️ Assets Not Included

**The `newassets/` directory is not included in this repository.** It contains purchased third-party assets that cannot be redistributed:

- **Visual assets** — sprites, tilesets, and objects from [Time Fantasy](https://timefantasy.net) by finalbossblues (commercial license)
- **Music** — Fantasy RPG Complete OST by VHCMusic
- **Splash screen video/audio** — custom files (`mw1.mp3`, `mw2.mp3`, `mw-openart1.mp4`, `mw-openart2.mp4`) in `newassets/custom/`

**If you clone this repo and want to run from source, you must provide your own `newassets/` directory** with the same structure. See `CLAUDE.md` for the full asset directory reference.

---

## Features

### Four Playable Heroes
Each hero has a unique playstyle, starting weapon, stat profile, and set of unlockable abilities:

| Hero | HP | Weapon | Resource | Specialty |
|------|----|--------|----------|-----------|
| Warrior | 100 | Basic Sword (melee) | Grit | High HP tank; Lunge, Whirlwind, Blazing Sword |
| Mage | 70 | Mage Bolt (ranged magic) | Mana | Low HP glass cannon; Fireball, Lightning Bolt, Polymorph |
| Ranger | 80 | Crossbow (ranged) | Grit | Marksman; Homing Arrow, Double Fire, Cover of Darkness |
| Paladin | 120 | Basic Sword (melee) | Mana | Tankiest hero; Holy Smite, Holy Cross, Holy Shield |

Heroes level up to **20**, unlocking new spells and abilities along the way.

### Combat
- Melee weapons with directional swing arcs and ranged weapons that fire projectiles
- 14 weapons across 6 styles: swords, axes, staves, bows, guns, and legendary blades
- Class restrictions — certain weapons and armor are locked to specific heroes
- Monster proximity aggro and chain aggro — nearby monsters alert each other
- Floating damage numbers on all hits
- Monster melee attack animations with claw-slash arcs

### Spells and Abilities
- **Mage spells (11):** Light Beam, Fireball, Magic Missile, Lightning Bolt, Polymorph, Portal, Prison, and more
- **Paladin spells (6):** Holy Smite, Holy Cross, Holy Shield, Holy Healing, Resurrect
- **Warrior grit abilities (11):** Lunge, Second Wind, Action Surge, Steel Skin, Whirlwind, Blazing Sword, and combo abilities
- **Ranger grit abilities (6):** Homing Arrow, Double Fire, Trap Monster, Cover of Darkness, Third Wind
- All 4 heroes gain a **resurrection ability** at level 20 that auto-triggers on death

### Enemy AI
- 6 monster types: Wild Cat, Wild Dog, Bandit, Soldier, Guard, Commander
- Enraged chase mode — monsters that survive a hit permanently pursue the player
- **A\* pathfinding** with proactive path refresh every 1.5 seconds and line-of-sight shortcut for natural direct-chase behaviour
- Special monster states: Polymorphed, Trapped, Imprisoned, Darkened (Cover of Darkness)
- Boss encounters in every stage with scaling HP and damage

### Stage Progression
```
Combat 1 → Town 1 → Combat 2 → Town 2 → ··· → Combat 10 (Final Boss)
```
- **10 combat stages** across three biomes: Forest, Desert, Dungeon
- **9 town stages** with randomised layouts, merchants, and wandering NPCs
- Stages 8–10 feature procedurally generated dungeon mazes (recursive-backtracker algorithm)
- Boss encounters per stage — escalating from Wild Cat to a scaled Commander boss at ×2.25 strength

### Loot and Items
- Drop tables per monster type with difficulty-gated rare drops
- Destructible treasure chests — normal and locked boss chests that unlock on boss defeat
- 6 consumables (potions, mushrooms, berries), 7 sellable monster drops, 14 weapon items, 6 armor tiers
- Stackable items up to 20; weapons and armor are single-slot

### Armor System
Six tiers from Leather Armor (DEF +2) up to Full Plate (DEF +12), with class restrictions on heavier armors

### Shop System
- Interact with the Merchant NPC in each town to open a buy/sell UI
- Two-panel shop: merchant inventory on the left, player inventory on the right
- **Hold to sell** — hold the mouse button (or Xbox A button) on a stack to rapidly sell multiples
- Item tooltips with stat details on hover

### Save System
- Up to 10 named save slots (JSON files in `saves/`)
- **Autosave** written when returning to the main menu; Resume button on the main menu
- Full game state saved: hero, level, inventory, equipped items, stage progress, active buffs

### Controller Support
Full Xbox controller support with hot-plug detection. All on-screen hints adapt automatically when a controller is connected.

| Input | Action |
|-------|--------|
| Left Stick / D-pad | Move |
| A | Attack / Confirm / Buy / Sell |
| B | Interact / Pick up / Close menus |
| X | Toggle inventory |
| Y | Toggle minimap / Drop item |
| RB | Cast selected spell / ability |
| D-pad Left/Right (gameplay) | Cycle spells/abilities |
| START | Pause / Resume |

### HUD and UI
- HP, Mana/Grit, and XP bars with per-hero colour coding
- Equipped weapon and armor indicators
- Active buff icons with remaining duration
- Numbered spell/ability list with cooldown and resource status
- Toggleable minimap (M) with colour-coded entity dots
- Toggleable FPS counter (F)

### Audio
- Full Fantasy RPG OST (VHCMusic) with separate combat, town, boss, and menu tracks
- Music auto-advances to the next track in rotation when a track finishes
- WAV sound effects for attacks, pickups, UI actions, and level-up
- Music and SFX volume sliders in the pause and options menus

---

## Technology

| Component | Details |
|-----------|---------|
| **Language** | Python 3 |
| **Framework** | [pygame](https://www.pygame.org/) |
| **Rendering** | 2D sprite-based with y-sorting, viewport culling, and per-frame animation |
| **Pathfinding** | A\* on a tile-grid with Bresenham line-of-sight shortcut (`src/pathfind.py`) |
| **Data** | Stage layouts, items, weapons, drop tables, and shop inventories in JSON |
| **Audio** | `pygame.mixer` for SFX, `pygame.mixer.music` for streaming background music |
| **Save format** | JSON files in `saves/` (up to 10 slots + autosave) |
| **Resolution** | Default 1920×1200; supports 12 resolutions from 800×600 to 2560×1440 |

---

## Running from Source

> **You must provide your own `newassets/` directory.** See the Assets section above.

**Requirements:** Python 3.10+

```bash
# 1. Clone the repository
git clone https://github.com/beknar/Monster-World.git
cd Monster-World

# 2. Create and activate a virtual environment
python -m venv venv
source venv/Scripts/activate   # Windows Git Bash
# venv\Scripts\activate        # PowerShell / CMD
# source venv/bin/activate     # macOS / Linux

# 3. Install dependencies
pip install pygame opencv-python numpy

# 4. Add your own newassets/ directory, then run
python main.py
```

---

## Controls (Keyboard)

| Key | Action |
|-----|--------|
| W A S D | Move |
| Space / Left Click | Attack |
| Q | Cast selected spell / ability |
| 1 – 9 | Select spell / ability |
| E | Pick up item or interact with NPC |
| I / Tab | Toggle inventory |
| M | Toggle minimap |
| F | Toggle FPS counter |
| ESC | Pause / close menus |

---

## Building a Distributable

> **You must have a valid `newassets/` directory before building.**

```bash
source venv/Scripts/activate   # Windows Git Bash
pip install pyinstaller
python -m PyInstaller -y MonsterWorld.spec
# Output: dist/MonsterWorld.exe  (single file, ~200 MB)
```

> **Important:** Always use `python -m PyInstaller`, not bare `pyinstaller`. See `CLAUDE.md` for details.

### Save file location (distributed build)

| Platform | Location |
|----------|----------|
| Windows | `%APPDATA%\MonsterWorld\saves\` |
| macOS | `~/Library/Application Support/MonsterWorld/saves/` |
| Linux | `~/.local/share/MonsterWorld/saves/` |

---

## Project Structure

```
Monster-World/
├── main.py              # Entry point
├── MonsterWorld.spec    # PyInstaller build spec
├── src/                 # Game source code
│   ├── game.py          # Main game loop and state machine
│   ├── player.py        # Player class, movement, combat, levelling
│   ├── monster.py       # Monster AI, boss logic, pathfinding integration
│   ├── pathfind.py      # A* pathfinding and line-of-sight utilities
│   ├── shop.py          # Shop UI and buy/sell logic
│   ├── inventory.py     # 5×5 inventory grid
│   ├── weapon.py        # Weapon definitions and projectile firing
│   ├── stage.py         # Procedural stage generation
│   ├── combat.py        # Damage calculation and XP rewards
│   ├── audio.py         # Music and sound effect manager
│   ├── hud.py           # HUD bars, minimap, spell list
│   ├── savegame.py      # Save / load / delete JSON persistence
│   └── settings.py      # Constants, hero definitions, monster stats
├── data/                # JSON game data
│   ├── items.json       # All item definitions
│   ├── weapons.json     # Weapon stats
│   ├── drop_tables.json # Monster and chest loot tables
│   └── shops.json       # Shop inventories per town
└── saves/               # Save files (auto-created at runtime, not committed)
```

> `newassets/` is not shown — it must be provided separately (see Assets section above).

---

## Credits and Licensing

### Visual Assets — Time Fantasy
All tilesets, character sprites, monster sprites, NPC sprites, objects, and other visual assets were purchased from **Time Fantasy** by finalbossblues.

| | |
|---|---|
| **Product site** | [timefantasy.net](https://timefantasy.net) |
| **Artist's website** | [finalbossblues.com](https://finalbossblues.com) |
| **Twitter** | [@finalbossblues](https://twitter.com/finalbossblues) |
| **Facebook** | [finalbossblues](https://www.facebook.com/finalbossblues) |

Assets are used under the terms of the Time Fantasy commercial license. **Not included in this repository.**

### Music — Fantasy RPG Complete OST
Background music tracks are from the **Fantasy RPG Complete OST** by VHCMusic, used under their respective license terms. **Not included in this repository.**

### Code
All game code is the author's own work.
