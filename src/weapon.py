import json
import os
from src.settings import DATA_PATH, DEFAULT_ATTACK_COOLDOWN


class WeaponData:
    """Weapon definition loaded from weapons.json."""

    def __init__(self, data: dict):
        self.id = data["id"]
        self.name = data["name"]
        self.damage = data["damage"]
        self.range = data["range"]
        self.speed = data.get("speed", DEFAULT_ATTACK_COOLDOWN)
        self.icon_key = data.get("icon", "")
        self.style = data.get("style", "sword")
        self.blade_color = tuple(data.get("blade_color", [190, 200, 220]))
        self.sound_swing = data.get("sound_swing", "sword_swing")
        self.sound_hit = data.get("sound_hit", "hit")
        # Ranged weapon properties
        self.projectile_speed = data.get("projectile_speed", 0)
        self.projectile_style = data.get("projectile_style", "arrow")
        # Dual-attack: fires a projectile AND does a melee swing simultaneously
        self.dual_attack = data.get("dual_attack", False)
        # Class restriction: list of hero IDs that can wield this weapon. Empty = all heroes.
        self.classes = data.get("classes", [])

    @property
    def is_ranged(self) -> bool:
        """Whether this weapon fires projectiles instead of melee swings."""
        return self.projectile_speed > 0

    @property
    def is_dual(self) -> bool:
        """Whether this weapon fires a projectile AND does melee simultaneously."""
        return self.dual_attack


def load_weapon_database() -> dict:
    """Load all weapon definitions from weapons.json. Returns dict of id -> WeaponData."""
    path = os.path.join(DATA_PATH, "weapons.json")
    with open(path, 'r') as f:
        weapons_list = json.load(f)
    return {w["id"]: WeaponData(w) for w in weapons_list}
