import math
import pygame
from src.settings import TILE_SIZE, PLAYER_PICKUP_RANGE


class CombatSystem:
    def __init__(self, audio_manager):
        self.audio = audio_manager

    def player_attack(self, player, monsters: list, chests: list = None) -> tuple:
        """Process player attack against monsters and chests.

        Returns (monster_hits, chest_hits) where:
          monster_hits = list of (monster, killed) tuples
          chest_hits = list of (chest, destroyed) tuples
        """
        attack_rect = player.attack()
        if attack_rect is None:
            return [], []

        self.audio.play_sfx(player.equipped_weapon.sound_swing)

        hits = []
        for monster in monsters:
            if not monster.is_alive:
                continue
            monster_rect = getattr(monster, 'collision_rect', monster.rect)
            if attack_rect.colliderect(monster_rect):
                damage = player.get_damage()
                killed = monster.take_damage(damage)
                self.audio.play_sfx(player.equipped_weapon.sound_hit)
                hits.append((monster, killed))

        chest_hits = []
        if chests:
            for chest in chests:
                if not chest.is_alive:
                    continue
                if getattr(chest, 'locked', False):
                    continue
                if attack_rect.colliderect(chest.collision_rect):
                    damage = player.get_damage()
                    destroyed = chest.take_damage(damage)
                    self.audio.play_sfx(player.equipped_weapon.sound_hit)
                    chest_hits.append((chest, destroyed))

        return hits, chest_hits

    def process_monster_contact(self, player, monsters: list) -> list:
        """Check monster contact damage AND proximity-based active attacks.
        Returns list of (actual_damage, monster_x, monster_y) for floating numbers."""
        if not player.is_alive:
            return []

        damage_events = []
        player_rect = player.collision_rect
        px, py = player.world_x, player.world_y

        for monster in monsters:
            if not monster.is_alive:
                continue

            # --- Proximity attack: monster actively attacks when flagged ---
            if monster.attack_hit_pending:
                monster.attack_hit_pending = False
                dx = px - monster.world_x
                dy = py - monster.world_y
                dist = math.sqrt(dx * dx + dy * dy)
                # Apply damage if player is still within attack range (+ small buffer)
                if dist < monster.attack_range * 1.3:
                    actual = player.take_damage(monster.damage)
                    self.audio.play_sfx("hit")
                    if actual:
                        damage_events.append((actual, monster.world_x, monster.world_y))
                continue  # Skip contact check this frame since we just attacked

            # --- Contact damage: walking into each other ---
            if not monster.can_deal_contact_damage():
                continue
            monster_rect = getattr(monster, 'collision_rect', monster.rect)
            if player_rect.colliderect(monster_rect):
                actual = player.take_damage(monster.damage)
                monster.deal_contact_damage()
                self.audio.play_sfx("hit")
                if actual:
                    damage_events.append((actual, monster.world_x, monster.world_y))

        return damage_events

    def process_kills(self, hits: list, player, drop_tables: dict, item_db: dict,
                      ground_items_group, gold_drops_group, item_icons: dict,
                      difficulty: float = 1.0):
        """Process killed monsters: award XP, spawn drops."""
        from src.loot import roll_drops, GroundItem, GoldDrop

        for monster, killed in hits:
            if killed:
                self.audio.play_sfx("kill")
                leveled = player.gain_xp(monster.xp_value)
                if leveled:
                    self.audio.play_sfx("powerup")

                # Grit on kill (Warrior and Ranger) — scaled by monster difficulty, min 3
                if getattr(player, 'max_grit', 0) > 0:
                    grit_gain = max(3.0, monster.difficulty * 3.0)
                    player.grit = min(float(player.max_grit), player.grit + grit_gain)

                # Mana on kill (Mage and Paladin) — scaled by monster difficulty, min 3
                if getattr(player, 'max_mana', 0) > 0:
                    mana_gain = max(3.0, monster.difficulty * 3.0)
                    player.mana = min(float(player.max_mana), player.mana + mana_gain)

                # Roll drops
                gold, items = roll_drops(monster.monster_type, drop_tables, item_db,
                                        is_boss=monster.is_boss, difficulty=difficulty)

                if gold > 0:
                    drop = GoldDrop(monster.world_x, monster.world_y, gold)
                    gold_drops_group.add(drop)

                for item_data, qty in items:
                    icon = item_icons.get(item_data.icon_key)
                    if icon is None:
                        icon = pygame.Surface((24, 24), pygame.SRCALPHA)
                        pygame.draw.rect(icon, (200, 200, 200), (2, 2, 20, 20))
                    drop = GroundItem(
                        monster.world_x + pygame.math.Vector2(1, 0).rotate(
                            len(ground_items_group) * 45).x * 20,
                        monster.world_y + pygame.math.Vector2(1, 0).rotate(
                            len(ground_items_group) * 45).y * 20,
                        item_data, qty, icon
                    )
                    ground_items_group.add(drop)

    def try_pickup(self, player, ground_items_group, gold_drops_group, audio) -> str | None:
        """Try to pick up the nearest ground item or gold.
        Returns a descriptive string of what was picked up, or None."""
        player_center = pygame.math.Vector2(player.world_x, player.world_y)
        pickup_range = PLAYER_PICKUP_RANGE

        # Check gold first
        nearest_gold = None
        nearest_dist = pickup_range
        for gold_drop in gold_drops_group:
            dist = player_center.distance_to(
                pygame.math.Vector2(gold_drop.world_x, gold_drop.world_y))
            if dist < nearest_dist:
                nearest_dist = dist
                nearest_gold = gold_drop

        if nearest_gold:
            amount = nearest_gold.amount
            player.gain_gold(amount)
            nearest_gold.kill()
            audio.play_sfx("coin")
            return f"Picked up {amount} Gold"

        # Check items
        nearest_item = None
        nearest_dist = pickup_range
        for item in ground_items_group:
            dist = player_center.distance_to(
                pygame.math.Vector2(item.world_x, item.world_y))
            if dist < nearest_dist:
                nearest_dist = dist
                nearest_item = item

        if nearest_item:
            leftover = player.inventory.add_item(nearest_item.item_data, nearest_item.quantity)
            picked_qty = nearest_item.quantity - leftover
            if picked_qty > 0:
                item_name = nearest_item.item_data.name
                if leftover > 0:
                    nearest_item.quantity = leftover
                else:
                    nearest_item.kill()
                audio.play_sfx("bonus")
                if picked_qty > 1:
                    return f"Picked up {item_name} x{picked_qty}"
                return f"Picked up {item_name}"

        return None
