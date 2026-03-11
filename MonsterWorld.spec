# MonsterWorld.spec
# PyInstaller spec file — produces a single self-contained executable.
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
# The -y flag overwrites the existing dist/MonsterWorld.exe automatically.
#
# Output: dist/MonsterWorld.exe — single file, distribute this alone.
# The end-user needs no Python installation and no extra folders.
#
# Startup note: on each launch Windows extracts all assets to a temp
# folder before the game starts. This adds a few seconds to startup time
# compared to onedir mode. The extraction folder is cleaned up on exit.
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
# IMPORTANT: run via "python -m PyInstaller" so collect_all() uses the same
# Python that has cv2 installed — bare "pyinstaller" may use a different one.
cv2_datas, cv2_binaries, cv2_hiddenimports = collect_all('cv2')

# ── Data files embedded inside the executable ────────────────────────────────
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

# ── Executable (onefile mode) ─────────────────────────────────────────────────
# All binaries, data, and assets are packed directly into MonsterWorld.exe.
# No COLLECT step — output is a single file at dist/MonsterWorld.exe.
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,      # embed all DLLs and .pyd extensions into the exe
    a.zipfiles,
    a.datas,         # embed newassets/, data/, cv2 data into the exe
    name='MonsterWorld',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,        # compress with UPX if available (smaller exe)
    console=False,   # no terminal window — windowed game
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='newassets/icon.ico',  # uncomment and add an .ico file to enable
)
