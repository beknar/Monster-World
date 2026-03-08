import pygame
import json
import os
import src.settings as settings
from src.settings import (DATA_PATH, SHOP_BUY_MARKUP,
                          INVENTORY_COLS, ARMOR_DEFS,
                          UI_BG, UI_BORDER, UI_SLOT_BG, UI_SLOT_HOVER,
                          WHITE, YELLOW, GRAY, RED, GREEN, GOLD_COLOR, BLACK)
from src.item import ItemData, ItemStack, ItemType


class ShopEntry:
    def __init__(self, item_data: ItemData, stock: int):
        self.item_data = item_data
        self.stock = stock
        self.buy_price = int(item_data.value * SHOP_BUY_MARKUP)


class Shop:
    def __init__(self, shop_data: dict, item_db: dict):
        self.name = shop_data.get("name", "Shop")
        self.entries = []
        for entry in shop_data.get("items", []):
            item_data = item_db.get(entry["item_id"])
            if item_data:
                self.entries.append(ShopEntry(item_data, entry.get("stock", 99)))
        self.is_open = False
        self.hovered_shop_item = -1
        self.hovered_inv_slot = -1
        self.message = ""
        self.message_timer = 0.0

        # Gamepad cursor state
        self.gamepad_panel = "shop"  # "shop" or "inv"
        self.gamepad_shop_index = 0
        self.gamepad_inv_index = 0
        self.controller_connected = False  # Set by game.py

        # Layout
        self._recalc_layout()

    def _recalc_layout(self):
        sw, sh = settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT
        scale = settings.get_font_scale()

        self.slot_size = settings.scaled_slot_size()
        self.slot_padding = settings.scaled_padding()
        self.row_height = int(32 * scale)
        self.icon_size = int(24 * scale)
        self.title_height = int(35 * scale)

        # Panel width scales with resolution but caps at half screen
        panel_w = min(int(420 * scale), sw // 2 - 20)
        # Panel height: accommodate inventory grid or shop items
        inv_grid_h = (self.title_height + 5 * (self.slot_size + self.slot_padding)
                      + self.slot_padding + 10)
        shop_items_h = self.title_height + len(self.entries) * self.row_height + 20
        panel_h = min(max(inv_grid_h, shop_items_h, int(400 * scale)), sh - 40)

        self.shop_rect = pygame.Rect(sw // 2 - panel_w - 10,
                                      (sh - panel_h) // 2,
                                      panel_w, panel_h)
        self.inv_rect = pygame.Rect(sw // 2 + 10,
                                     (sh - panel_h) // 2,
                                     panel_w, panel_h)

    def open(self):
        self._recalc_layout()
        self.is_open = True
        self.gamepad_panel = "shop"
        self.gamepad_shop_index = 0
        self.gamepad_inv_index = 0

    def close(self):
        self.is_open = False
        self.message = ""

    def update(self, dt: float, mouse_pos: tuple):
        if self.message_timer > 0:
            self.message_timer -= dt
            if self.message_timer <= 0:
                self.message = ""

        # Update hover states
        self.hovered_shop_item = -1
        self.hovered_inv_slot = -1
        if self.shop_rect.collidepoint(mouse_pos):
            rel_y = mouse_pos[1] - self.shop_rect.y - self.title_height
            if rel_y >= 0:
                idx = int(rel_y // self.row_height)
                if 0 <= idx < len(self.entries):
                    self.hovered_shop_item = idx
        elif self.inv_rect.collidepoint(mouse_pos):
            rel_x = mouse_pos[0] - self.inv_rect.x - 10
            rel_y = mouse_pos[1] - self.inv_rect.y - self.title_height
            if rel_x >= 0 and rel_y >= 0:
                col = int(rel_x // (self.slot_size + self.slot_padding))
                row = int(rel_y // (self.slot_size + self.slot_padding))
                if 0 <= col < INVENTORY_COLS and 0 <= row < 5:
                    self.hovered_inv_slot = row * INVENTORY_COLS + col

    def handle_click(self, mouse_pos: tuple, button: int, player, audio) -> bool:
        """Handle mouse click in shop. Returns True if something happened."""
        if not self.is_open:
            return False

        if button == 1:  # Left click
            # Buy from shop
            if self.hovered_shop_item >= 0:
                entry = self.entries[self.hovered_shop_item]
                if entry.stock <= 0:
                    self._show_message("Out of stock!")
                    return True
                if player.gold < entry.buy_price:
                    self._show_message("Not enough gold!")
                    return True
                leftover = player.inventory.add_item(entry.item_data, 1)
                if leftover > 0:
                    self._show_message("Inventory full!")
                    return True
                player.gold -= entry.buy_price
                entry.stock -= 1
                audio.play_sfx("gold")
                self._show_message(f"Bought {entry.item_data.name}")
                return True

            # Sell from inventory
            if self.hovered_inv_slot >= 0:
                stack = player.inventory.get_slot(self.hovered_inv_slot)
                if stack:
                    sell_price = stack.item_data.value
                    player.inventory.remove_item(self.hovered_inv_slot, 1)
                    player.gold += sell_price
                    audio.play_sfx("coin")
                    self._show_message(f"Sold for {sell_price}g")
                    return True

        return False

    def gamepad_navigate(self, dx: int, dy: int):
        """Move the gamepad cursor within the current panel."""
        if self.gamepad_panel == "shop":
            self.gamepad_shop_index = max(0, min(
                len(self.entries) - 1, self.gamepad_shop_index + dy))
            # Left/right switches panel
            if dx > 0:
                self.gamepad_panel = "inv"
        else:
            # Inventory grid navigation
            col = self.gamepad_inv_index % INVENTORY_COLS
            row = self.gamepad_inv_index // INVENTORY_COLS
            col = max(0, min(INVENTORY_COLS - 1, col + dx))
            row = max(0, min(4, row + dy))
            self.gamepad_inv_index = row * INVENTORY_COLS + col
            # Left from column 0 switches to shop panel
            if dx < 0 and col == 0:
                self.gamepad_panel = "shop"

    def gamepad_switch_panel(self, direction: int = 1):
        """Switch between shop and inventory panels (LB/RB)."""
        if direction < 0:
            self.gamepad_panel = "shop"
        else:
            self.gamepad_panel = "inv"

    def gamepad_confirm(self, player, audio):
        """Confirm buy/sell at the current gamepad cursor position."""
        if self.gamepad_panel == "shop":
            # Buy from shop
            idx = self.gamepad_shop_index
            if 0 <= idx < len(self.entries):
                entry = self.entries[idx]
                if entry.stock <= 0:
                    self._show_message("Out of stock!")
                    return
                if player.gold < entry.buy_price:
                    self._show_message("Not enough gold!")
                    return
                leftover = player.inventory.add_item(entry.item_data, 1)
                if leftover > 0:
                    self._show_message("Inventory full!")
                    return
                player.gold -= entry.buy_price
                entry.stock -= 1
                audio.play_sfx("gold")
                self._show_message(f"Bought {entry.item_data.name}")
        else:
            # Sell from inventory
            idx = self.gamepad_inv_index
            if 0 <= idx < 25:
                stack = player.inventory.get_slot(idx)
                if stack:
                    sell_price = stack.item_data.value
                    player.inventory.remove_item(idx, 1)
                    player.gold += sell_price
                    audio.play_sfx("coin")
                    self._show_message(f"Sold for {sell_price}g")

    def _show_message(self, text: str):
        self.message = text
        self.message_timer = 2.0

    def _build_item_tooltip_lines(self, item_data: ItemData,
                                  buy_price: int = None) -> list:
        """Return a list of (text, color) lines describing an item."""
        lines = []
        type_label = item_data.type.value.capitalize()
        lines.append((f"{item_data.name}  [{type_label}]", GOLD_COLOR))

        if item_data.description:
            lines.append((item_data.description, WHITE))

        if item_data.type == ItemType.CONSUMABLE:
            if item_data.buff_type == "heal":
                lines.append((f"Restores {int(item_data.buff_value)} HP", GREEN))
            elif item_data.buff_type == "damage_up":
                lines.append((
                    f"+{int(item_data.buff_value)} Damage  ({int(item_data.buff_duration)}s)",
                    (255, 180, 80)))
            elif item_data.buff_type == "speed_up":
                lines.append((
                    f"+{int(item_data.buff_value)} Speed  ({int(item_data.buff_duration)}s)",
                    (80, 220, 255)))
            elif item_data.buff_type == "defense_up":
                lines.append((
                    f"+{int(item_data.buff_value)} Defense  ({int(item_data.buff_duration)}s)",
                    (180, 220, 255)))

        elif item_data.type == ItemType.ARMOR and item_data.armor_id:
            armor_def = ARMOR_DEFS.get(item_data.armor_id, {})
            if armor_def:
                classes = ", ".join(c.capitalize() for c in armor_def.get("classes", []))
                lines.append((
                    f"DEF +{armor_def.get('defense', 0)}  |  Classes: {classes}",
                    (180, 220, 255)))

        if buy_price is not None:
            lines.append((f"Buy: {buy_price}g  |  Sell value: {item_data.value}g",
                          GOLD_COLOR))
        else:
            lines.append((f"Sell for: {item_data.value}g", GOLD_COLOR))
        return lines

    def _draw_tooltip_panel(self, surface, font, lines: list, ref_rect: pygame.Rect):
        """Draw a tooltip panel above ref_rect showing item info lines."""
        if not lines:
            return
        scale = settings.get_font_scale()
        small_font = pygame.font.Font(None, settings.scaled_font_size(18))
        line_h = int(20 * scale)
        pad = int(8 * scale)
        panel_w = ref_rect.width * 2 + 20  # spans both panels
        panel_h = len(lines) * line_h + pad * 2
        panel_x = ref_rect.x
        panel_y = ref_rect.y - panel_h - int(6 * scale)

        # Clamp to screen top
        if panel_y < int(4 * scale):
            panel_y = int(4 * scale)

        bg = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        bg.fill((20, 20, 30, 220))
        surface.blit(bg, (panel_x, panel_y))
        pygame.draw.rect(surface, UI_BORDER,
                         pygame.Rect(panel_x, panel_y, panel_w, panel_h), 1)

        for i, (text, color) in enumerate(lines):
            lbl = (font if i == 0 else small_font).render(text, True, color)
            surface.blit(lbl, (panel_x + pad, panel_y + pad + i * line_h))

    def draw(self, surface: pygame.Surface, player, item_icons: dict,
             font: pygame.font.Font):
        if not self.is_open:
            return

        # Overlay
        sw, sh = settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        surface.blit(overlay, (0, 0))

        # Shop panel
        self._draw_shop_panel(surface, font, item_icons, player.gold)
        # Player inventory panel
        self._draw_inv_panel(surface, player, item_icons, font)

        # Item tooltip above the panels (shows hovered or gamepad-selected item)
        tooltip_lines = []
        if self.gamepad_panel == "shop" or self.hovered_shop_item >= 0:
            idx = (self.gamepad_shop_index if self.gamepad_panel == "shop"
                   else self.hovered_shop_item)
            if 0 <= idx < len(self.entries):
                entry = self.entries[idx]
                tooltip_lines = self._build_item_tooltip_lines(
                    entry.item_data, buy_price=entry.buy_price)
        elif self.gamepad_panel == "inv" or self.hovered_inv_slot >= 0:
            idx = (self.gamepad_inv_index if self.gamepad_panel == "inv"
                   else self.hovered_inv_slot)
            stack = player.inventory.get_slot(idx)
            if stack:
                tooltip_lines = self._build_item_tooltip_lines(stack.item_data)
        if tooltip_lines:
            self._draw_tooltip_panel(surface, font, tooltip_lines, self.shop_rect)

        # Message
        if self.message:
            msg = font.render(self.message, True, YELLOW)
            surface.blit(msg, (sw // 2 - msg.get_width() // 2,
                              self.shop_rect.bottom + 10))

        # Controller hints at bottom
        if self.controller_connected:
            hint_font = pygame.font.Font(None, settings.scaled_font_size(18))
            hint_text = ("A:Buy/Sell  B:Close  LB/RB:Switch Panel  "
                         "D-pad:Navigate")
            hint = hint_font.render(hint_text, True, GRAY)
            surface.blit(hint, (sw // 2 - hint.get_width() // 2,
                                self.shop_rect.bottom + 30))

    def _draw_shop_panel(self, surface, font, item_icons, player_gold):
        panel = pygame.Surface((self.shop_rect.width, self.shop_rect.height), pygame.SRCALPHA)
        panel.fill(UI_BG)
        surface.blit(panel, (self.shop_rect.x, self.shop_rect.y))
        pygame.draw.rect(surface, UI_BORDER, self.shop_rect, 2)

        title = font.render(f"{self.name} (Gold: {player_gold})", True, GOLD_COLOR)
        surface.blit(title, (self.shop_rect.x + 10, self.shop_rect.y + 8))

        y = self.shop_rect.y + self.title_height
        for i, entry in enumerate(self.entries):
            row_rect = pygame.Rect(self.shop_rect.x + 5, y,
                                   self.shop_rect.width - 10, self.row_height - 2)
            is_hovered = (i == self.hovered_shop_item or
                          (self.gamepad_panel == "shop"
                           and i == self.gamepad_shop_index))
            if is_hovered:
                pygame.draw.rect(surface, UI_SLOT_HOVER, row_rect)
            # Gamepad cursor gold border
            if (self.controller_connected and self.gamepad_panel == "shop"
                    and i == self.gamepad_shop_index):
                pygame.draw.rect(surface, GOLD_COLOR, row_rect, 2)

            icon = item_icons.get(entry.item_data.icon_key)
            if icon:
                small = pygame.transform.scale(icon, (self.icon_size, self.icon_size))
                surface.blit(small, (row_rect.x + 4,
                                     y + (self.row_height - self.icon_size) // 2))

            name = font.render(entry.item_data.name, True, WHITE)
            surface.blit(name, (row_rect.x + self.icon_size + 12,
                               y + (self.row_height - name.get_height()) // 2))

            stock_text = f"x{entry.stock}" if entry.stock < 99 else ""
            price_color = GREEN if entry.stock > 0 else RED
            price = font.render(f"{entry.buy_price}g {stock_text}", True, price_color)
            surface.blit(price, (row_rect.right - price.get_width() - 5,
                                y + (self.row_height - price.get_height()) // 2))

            y += self.row_height

    def _draw_inv_panel(self, surface, player, item_icons, font):
        panel = pygame.Surface((self.inv_rect.width, self.inv_rect.height), pygame.SRCALPHA)
        panel.fill(UI_BG)
        surface.blit(panel, (self.inv_rect.x, self.inv_rect.y))
        pygame.draw.rect(surface, UI_BORDER, self.inv_rect, 2)

        if self.controller_connected:
            title = font.render("Your Items (A to sell)", True, WHITE)
        else:
            title = font.render("Your Items (click to sell)", True, WHITE)
        surface.blit(title, (self.inv_rect.x + 10, self.inv_rect.y + 8))

        # Use a smaller font for price/quantity inside slots
        small_font_size = settings.scaled_font_size(14)
        small_font = pygame.font.Font(None, small_font_size)

        for i in range(25):
            row = i // INVENTORY_COLS
            col = i % INVENTORY_COLS
            sx = self.inv_rect.x + 10 + col * (self.slot_size + self.slot_padding)
            sy = self.inv_rect.y + self.title_height + row * (self.slot_size + self.slot_padding)
            slot_rect = pygame.Rect(sx, sy, self.slot_size, self.slot_size)

            is_hovered = (i == self.hovered_inv_slot or
                          (self.gamepad_panel == "inv"
                           and i == self.gamepad_inv_index))
            color = UI_SLOT_HOVER if is_hovered else UI_SLOT_BG
            pygame.draw.rect(surface, color, slot_rect)
            pygame.draw.rect(surface, UI_BORDER, slot_rect, 1)
            # Gamepad cursor gold border
            if (self.controller_connected and self.gamepad_panel == "inv"
                    and i == self.gamepad_inv_index):
                pygame.draw.rect(surface, GOLD_COLOR, slot_rect, 2)

            stack = player.inventory.get_slot(i)
            if stack:
                icon = item_icons.get(stack.item_data.icon_key)
                if icon:
                    scaled_icon = pygame.transform.scale(
                        icon, (self.slot_size - 8, self.slot_size - 8))
                    ix = sx + 4
                    iy = sy + 4
                    surface.blit(scaled_icon, (ix, iy))
                if stack.quantity > 1:
                    ct = small_font.render(str(stack.quantity), True, WHITE)
                    surface.blit(ct, (sx + self.slot_size - ct.get_width() - 2,
                                     sy + self.slot_size - ct.get_height()))
                # Show sell price
                price = small_font.render(f"{stack.item_data.value}g", True, GOLD_COLOR)
                surface.blit(price, (sx + 2, sy + 2))


def load_shops(item_db: dict) -> dict:
    """Load all shop definitions. Returns dict of shop_id -> Shop."""
    path = os.path.join(DATA_PATH, "shops.json")
    with open(path, 'r') as f:
        shops_data = json.load(f)
    return {shop_id: Shop(data, item_db) for shop_id, data in shops_data.items()}
