import json
import os
from enum import Enum
from src.settings import DATA_PATH


class ItemType(Enum):
    WEAPON = "weapon"
    CONSUMABLE = "consumable"
    SELLABLE = "sellable"
    ARMOR = "armor"


class ItemData:
    """Immutable item definition loaded from items.json."""

    def __init__(self, data: dict):
        self.id = data["id"]
        self.name = data["name"]
        self.type = ItemType(data["type"])
        self.icon_key = data.get("icon", "")
        self.value = data.get("value", 0)
        self.stack_max = data.get("stack_max", 20)
        self.description = data.get("description", "")
        # Consumable fields
        self.buff_type = data.get("buff_type", "")
        self.buff_value = data.get("buff_value", 0)
        self.buff_duration = data.get("buff_duration", 0)
        # Weapon fields
        self.weapon_id = data.get("weapon_id", "")
        # Armor fields
        self.armor_id = data.get("armor_id", "")


class ItemStack:
    """A stack of items in an inventory slot."""

    def __init__(self, item_data: ItemData, quantity: int = 1):
        self.item_data = item_data
        self.quantity = min(quantity, item_data.stack_max)

    def can_add(self, amount: int = 1) -> int:
        """Return how many can be added (up to stack_max)."""
        return min(amount, self.item_data.stack_max - self.quantity)

    def add(self, amount: int = 1) -> int:
        """Add items. Returns leftover that didn't fit."""
        can = self.can_add(amount)
        self.quantity += can
        return amount - can

    def remove(self, amount: int = 1) -> int:
        """Remove items. Returns actual amount removed."""
        removed = min(amount, self.quantity)
        self.quantity -= removed
        return removed


def load_item_database() -> dict:
    """Load all item definitions from items.json. Returns dict of id -> ItemData."""
    path = os.path.join(DATA_PATH, "items.json")
    with open(path, 'r') as f:
        items_list = json.load(f)
    return {item["id"]: ItemData(item) for item in items_list}
