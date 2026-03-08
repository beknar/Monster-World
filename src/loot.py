import pygame
import json
import os
import random
import math
from src.settings import (DATA_PATH, SCALE_FACTOR, TILE_SIZE,
                          GROUND_ITEM_BOB_SPEED, GROUND_ITEM_BOB_AMOUNT,
                          GOLD_COLOR, YELLOW, BOSS_GOLD_MULT)
from src.item import ItemData


class GroundItem(pygame.sprite.Sprite):
    """An item lying on the ground that can be picked up."""

    def __init__(self, x: float, y: float, item_data: ItemData, quantity: int,
                 icon: pygame.Surface):
        super().__init__()
        self.item_data = item_data
        self.quantity = quantity
        self.icon = icon
        self.world_x = x
        self.world_y = y
        self.bob_timer = random.uniform(0, math.pi * 2)
        self.image = icon
        self.rect = self.image.get_rect(center=(int(x), int(y)))

    def update(self, dt: float):
        self.bob_timer += dt * GROUND_ITEM_BOB_SPEED
        bob_offset = math.sin(self.bob_timer) * GROUND_ITEM_BOB_AMOUNT
        self.rect.center = (int(self.world_x), int(self.world_y + bob_offset))

    def draw(self, surface: pygame.Surface, camera_offset: tuple):
        pos = (self.rect.x - int(camera_offset[0]),
               self.rect.y - int(camera_offset[1]))
        surface.blit(self.image, pos)


class GoldDrop(pygame.sprite.Sprite):
    """Gold lying on the ground."""

    def __init__(self, x: float, y: float, amount: int):
        super().__init__()
        self.amount = amount
        self.world_x = x
        self.world_y = y
        self.bob_timer = random.uniform(0, math.pi * 2)
        # Create simple gold coin visual
        size = 12 * SCALE_FACTOR // 2
        self.image = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(self.image, GOLD_COLOR, (size // 2, size // 2), size // 2)
        pygame.draw.circle(self.image, YELLOW, (size // 2, size // 2), size // 3)
        self.rect = self.image.get_rect(center=(int(x), int(y)))

    def update(self, dt: float):
        self.bob_timer += dt * GROUND_ITEM_BOB_SPEED
        bob_offset = math.sin(self.bob_timer) * GROUND_ITEM_BOB_AMOUNT
        self.rect.center = (int(self.world_x), int(self.world_y + bob_offset))

    def draw(self, surface: pygame.Surface, camera_offset: tuple):
        pos = (self.rect.x - int(camera_offset[0]),
               self.rect.y - int(camera_offset[1]))
        surface.blit(self.image, pos)


def load_drop_tables() -> dict:
    """Load monster drop tables from drop_tables.json."""
    path = os.path.join(DATA_PATH, "drop_tables.json")
    with open(path, 'r') as f:
        return json.load(f)


def roll_drops(monster_type: str, drop_tables: dict, item_db: dict,
               is_boss: bool = False, difficulty: float = 1.0) -> tuple:
    """Roll loot for a killed monster.
    Returns (gold_amount, list of (ItemData, quantity) tuples)."""
    table = drop_tables.get(monster_type, {})

    gold_min = table.get("gold_min", 1)
    gold_max = table.get("gold_max", 5)
    gold = random.randint(gold_min, gold_max)
    gold = int(gold * difficulty)
    if is_boss:
        gold = int(gold * BOSS_GOLD_MULT)

    items = []
    for drop in table.get("drops", []):
        min_diff = drop.get("min_difficulty", 0.0)
        if difficulty < min_diff:
            continue
        chance = drop["chance"]
        if is_boss:
            chance = min(1.0, chance * 2)  # Bosses have double drop rates
        if random.random() < chance:
            item_id = drop["item_id"]
            item_data = item_db.get(item_id)
            if item_data:
                qty = random.randint(drop["quantity_min"], drop["quantity_max"])
                items.append((item_data, qty))

    return gold, items
