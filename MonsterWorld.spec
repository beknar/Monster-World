# MonsterWorld.spec
# PyInstaller spec file — produces a self-contained distributable folder.
#
# Build command (from the project root with venv active):
#   pip install pyinstaller
#   python -m PyInstaller -y MonsterWorld.spec
#
# IMPORTANT: Use "python -m PyInstaller" NOT bare "pyinstaller".
# If multiple Python versions are installed, bare "pyinstaller" may
# resolve to a different Python than "python", causing collect_all('cv2')
# to find nothing and producing "No module named 'cv2'" at runtime.
#
# The -y flag overwrites the existing dist/MonsterWorld/ folder automatically.
#
# Output: dist/MonsterWorld/  — copy this folder to distribute the game.
# The end-user needs no Python installation.
#
# Save files are stored in the user's app-data directory, NOT inside the
# bundle, so they survive updates:
#   Windows : %APPDATA%\MonsterWorld\saves\
#   macOS   : ~/Library/Application Support/MonsterWorld/saves/
#   Linux   : ~/.local/share/MonsterWorld/saves/

import os
from PyInstaller.utils.hooks import collect_all

block_cipher = None

# ── Collect cv2 (OpenCV) — binary extensions + DLLs + data ─────────────────
# collect_all() gathers everything cv2 needs: the .pyd extension, all dependent
# DLLs, any pure-Python sub-modules, and data files.  Without this, PyInstaller
# only records the module name but fails to bundle the actual binaries, causing
# "ModuleNotFoundError: No module named 'cv2'" at runtime.
cv2_datas, cv2_binaries, cv2_hiddenimports = collect_all('cv2')

# ── Data files bundled alongside the executable ─────────────────────────────
# Format: (source_path, dest_folder_inside_bundle)
# PyInstaller recursively copies directories.
added_files = [
    (os.path.join('newassets'), 'newassets'),  # sprites, tilesets, sounds, music
    (os.path.join('data'),      'data'),        # weapons.json, items.json, etc.
]

# ── Analysis ─────────────────────────────────────────────────────────────────
a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=cv2_binaries,
    datas=added_files + cv2_datas,
    hiddenimports=[
        # pygame occasionally needs these sub-modules explicitly imported
        # (pygame._view was removed in pygame 2.x — do not add it back)
        'pygame',
        'pygame.mixer',
        'pygame.font',
        'pygame.image',
        'pygame.transform',
        'pygame.draw',
        'pygame.joystick',
        # numpy (required by cv2 frame array operations)
        'numpy',
        'numpy.core',
        'numpy.core._multiarray_umath',
    ] + cv2_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Only exclude tkinter — it is large and genuinely unused.
        # Do NOT exclude stdlib modules like xml, email, http, etc.:
        # PyInstaller's own runtime hook (pyi_rth_pkgres) imports pkg_resources
        # which pulls in plistlib → xml, email, and others at startup.
        # Excluding them causes ModuleNotFoundError before any game code runs.
        'tkinter',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ── Executable ────────────────────────────────────────────────────────────────
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,   # binaries go into COLLECT below (onedir mode)
    name='MonsterWorld',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,                # compress with UPX if available (smaller bundle)
    console=False,           # no terminal window — windowed game
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='newassets/icon.ico',  # uncomment and add an .ico file to enable
)

# ── Collect (onedir bundle) ───────────────────────────────────────────────────
# Produces dist/MonsterWorld/ containing MonsterWorld.exe + all dependencies.
# Preferred over --onefile: pygame games launch much faster without needing
# to extract assets to a temp directory on every run.
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='MonsterWorld',
)
