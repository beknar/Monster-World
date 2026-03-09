import pygame
import math
import src.settings as settings
from src.item import ItemData, ItemStack, ItemType
from src.settings import (INVENTORY_COLS, INVENTORY_ROWS, INVENTORY_SLOTS,
                          UI_BG, UI_BORDER, UI_SLOT_BG, UI_SLOT_HOVER,
                          WHITE, YELLOW, GRAY, BLACK, GOLD_COLOR)


class Inventory:
    def __init__(self):
        self.slots = [None] * INVENTORY_SLOTS  # Each is ItemStack or None
        self.is_open = False
        self.hovered_slot = -1
        # Held item for drag-and-drop between slots
        self.held_item = None  # ItemStack or None
        # Gamepad cursor for controller navigation (-1 = inactive)
        self.gamepad_cursor = -1
        # Calculate UI position (centered on screen)
        self._recalc_rect()

    def _recalc_rect(self):
        slot_size = settings.scaled_slot_size()
        padding = settings.scaled_padding()
        title_h = int(30 * settings.get_font_scale())
        total_w = INVENTORY_COLS * (slot_size + padding) + padding
        total_h = INVENTORY_ROWS * (slot_size + padding) + padding + title_h
        self.rect = pygame.Rect(
            (settings.SCREEN_WIDTH - total_w) // 2,
            (settings.SCREEN_HEIGHT - total_h) // 2,
            total_w, total_h
        )

    def toggle(self):
        self._recalc_rect()
        self.is_open = not self.is_open
        self.hovered_slot = -1

    def close(self):
        self.is_open = False
        self.hovered_slot = -1
        # Put held item back into inventory if possible
        if self.held_item:
            leftover = self.add_item(self.held_item.item_data, self.held_item.quantity)
            if leftover > 0:
                self.held_item.quantity = leftover
            else:
                self.held_item = None

    def add_item(self, item_data: ItemData, quantity: int = 1) -> int:
        """Add item(s) to inventory. Returns leftover quantity that didn't fit."""
        remaining = quantity

        # First, try to stack with existing items of same type
        if item_data.stack_max > 1:
            for i, slot in enumerate(self.slots):
                if remaining <= 0:
                    break
                if slot and slot.item_data.id == item_data.id:
                    remaining = slot.add(remaining)

        # Then, fill empty slots
        for i in range(len(self.slots)):
            if remaining <= 0:
                break
            if self.slots[i] is None:
                amount = min(remaining, item_data.stack_max)
                self.slots[i] = ItemStack(item_data, amount)
                remaining -= amount

        return remaining

    def remove_item(self, slot_index: int, quantity: int = 1) -> ItemStack | None:
        """Remove quantity from a slot. Returns ItemStack of what was removed, or None."""
        if slot_index < 0 or slot_index >= INVENTORY_SLOTS:
            return None
        slot = self.slots[slot_index]
        if slot is None:
            return None
        removed = slot.remove(quantity)
        result = ItemStack(slot.item_data, removed) if removed > 0 else None
        if slot.quantity <= 0:
            self.slots[slot_index] = None
        return result

    def get_slot(self, slot_index: int) -> ItemStack | None:
        if 0 <= slot_index < INVENTORY_SLOTS:
            return self.slots[slot_index]
        return None

    def set_slot(self, slot_index: int, item_data: ItemData, quantity: int = 1):
        """Directly set a slot to a specific item and quantity."""
        if 0 <= slot_index < INVENTORY_SLOTS:
            self.slots[slot_index] = ItemStack(item_data, quantity)

    def is_full(self) -> bool:
        return all(s is not None for s in self.slots)

    def pick_up_slot(self, slot_index: int) -> bool:
        """Pick up the entire stack from a slot onto the cursor. Returns True if picked up."""
        if slot_index < 0 or slot_index >= INVENTORY_SLOTS:
            return False
        stack = self.slots[slot_index]
        if stack is None:
            return False
        self.held_item = stack
        self.slots[slot_index] = None
        return True

    def place_held(self, slot_index: int) -> bool:
        """Place held item into slot. Swaps if slot is occupied (different item).
        Stacks if same item. Returns True if action taken."""
        if self.held_item is None:
            return False
        if slot_index < 0 or slot_index >= INVENTORY_SLOTS:
            return False
        target = self.slots[slot_index]
        if target is None:
            self.slots[slot_index] = self.held_item
            self.held_item = None
            return True
        elif target.item_data.id == self.held_item.item_data.id and target.item_data.stack_max > 1:
            leftover = target.add(self.held_item.quantity)
            if leftover <= 0:
                self.held_item = None
            else:
                self.held_item.quantity = leftover
            return True
        else:
            self.slots[slot_index] = self.held_item
            self.held_item = target
            return True

    def drop_held(self) -> ItemStack | None:
        """Drop held item onto the ground. Returns the ItemStack or None."""
        if self.held_item is None:
            return None
        dropped = self.held_item
        self.held_item = None
        return dropped

    def get_slot_at_pos(self, mouse_pos: tuple) -> int:
        """Given screen mouse position, return slot index or -1."""
        if not self.rect.collidepoint(mouse_pos):
            return -1
        slot_size = settings.scaled_slot_size()
        padding = settings.scaled_padding()
        title_h = int(30 * settings.get_font_scale())
        mx = mouse_pos[0] - self.rect.x - padding
        my = mouse_pos[1] - self.rect.y - title_h
        if mx < 0 or my < 0:
            return -1
        col = int(mx // (slot_size + padding))
        row = int(my // (slot_size + padding))
        if col < 0 or col >= INVENTORY_COLS or row < 0 or row >= INVENTORY_ROWS:
            return -1
        idx = row * INVENTORY_COLS + col
        if idx >= INVENTORY_SLOTS:
            return -1
        return idx

    def update_hover(self, mouse_pos: tuple):
        self.hovered_slot = self.get_slot_at_pos(mouse_pos)

    def gamepad_navigate(self, dx: int, dy: int):
        """Move the gamepad cursor by (dx, dy) grid units."""
        if self.gamepad_cursor < 0:
            self.gamepad_cursor = 0
            return
        col = self.gamepad_cursor % INVENTORY_COLS
        row = self.gamepad_cursor // INVENTORY_COLS
        col = max(0, min(INVENTORY_COLS - 1, col + dx))
        row = max(0, min(INVENTORY_ROWS - 1, row + dy))
        self.gamepad_cursor = row * INVENTORY_COLS + col

    def draw(self, surface: pygame.Surface, item_icons: dict, font: pygame.font.Font):
        if not self.is_open:
            return

        slot_size = settings.scaled_slot_size()
        padding = settings.scaled_padding()
        title_h = int(30 * settings.get_font_scale())

        # Recalc rect in case resolution changed
        self._recalc_rect()

        # Background overlay
        overlay = pygame.Surface((settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        surface.blit(overlay, (0, 0))

        # Inventory panel background
        panel = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        panel.fill(UI_BG)
        surface.blit(panel, (self.rect.x, self.rect.y))
        pygame.draw.rect(surface, UI_BORDER, self.rect, 2)

        # Title
        title = font.render("Inventory", True, WHITE)
        surface.blit(title, (self.rect.x + (self.rect.width - title.get_width()) // 2,
                            self.rect.y + 6))

        # Draw slots
        for i in range(INVENTORY_SLOTS):
            row = i // INVENTORY_COLS
            col = i % INVENTORY_COLS
            sx = self.rect.x + padding + col * (slot_size + padding)
            sy = self.rect.y + title_h + row * (slot_size + padding)
            slot_rect = pygame.Rect(sx, sy, slot_size, slot_size)

            # Slot background
            is_hovered = (i == self.hovered_slot or i == self.gamepad_cursor)
            color = UI_SLOT_HOVER if is_hovered else UI_SLOT_BG
            pygame.draw.rect(surface, color, slot_rect)
            pygame.draw.rect(surface, UI_BORDER, slot_rect, 1)
            # Gamepad cursor highlight
            if i == self.gamepad_cursor:
                pygame.draw.rect(surface, GOLD_COLOR, slot_rect, 2)

            # Item icon and count
            stack = self.slots[i]
            if stack:
                icon = item_icons.get(stack.item_data.icon_key)
                if icon:
                    scaled_icon = pygame.transform.scale(
                        icon, (slot_size - 8, slot_size - 8))
                    ix = sx + 4
                    iy = sy + 4
                    surface.blit(scaled_icon, (ix, iy))

                if stack.quantity > 1:
                    count_text = font.render(str(stack.quantity), True, WHITE)
                    surface.blit(count_text, (sx + slot_size - count_text.get_width() - 2,
                                             sy + slot_size - count_text.get_height()))

        # Tooltip for hovered slot or gamepad cursor (only when not holding an item)
        tooltip_slot = self.hovered_slot if self.hovered_slot >= 0 else self.gamepad_cursor
        if tooltip_slot >= 0 and self.held_item is None:
            stack = self.slots[tooltip_slot]
            if stack:
                self._draw_tooltip(surface, stack, font)

        # Draw held item at cursor position (gamepad = cursor slot center; mouse = mouse pos)
        if self.held_item:
            if self.gamepad_cursor >= 0:
                # Draw held item floating above the current gamepad cursor slot
                row = self.gamepad_cursor // INVENTORY_COLS
                col = self.gamepad_cursor % INVENTORY_COLS
                cx = self.rect.x + padding + col * (slot_size + padding) + slot_size // 2
                cy = self.rect.y + title_h + row * (slot_size + padding) + slot_size // 2
                mx, my = cx, cy - slot_size  # float item above the slot
            else:
                mx, my = pygame.mouse.get_pos()
            icon = item_icons.get(self.held_item.item_data.icon_key)
            if icon:
                surface.blit(icon, (mx - icon.get_width() // 2,
                                    my - icon.get_height() // 2))
            if self.held_item.quantity > 1:
                count_text = font.render(str(self.held_item.quantity), True, WHITE)
                surface.blit(count_text, (mx + 6, my + 6))

        # Controller hints below inventory
        if self.gamepad_cursor >= 0:
            hint_font = pygame.font.Font(None, settings.scaled_font_size(18))
            if self.held_item:
                hint_text = "A:Place  Y:Drop to Ground  D-pad:Navigate  B/X:Cancel"
            else:
                hint_text = "A:Pick Up  Y:Use/Equip  D-pad:Navigate  B/X:Close"
            hint = hint_font.render(hint_text, True, GRAY)
            surface.blit(hint, (self.rect.centerx - hint.get_width() // 2,
                                self.rect.bottom + 8))

    def _draw_tooltip(self, surface: pygame.Surface, stack: ItemStack, font: pygame.font.Font):
        if self.gamepad_cursor >= 0:
            if self.held_item:
                action_hint = "A: Place here | Y: Drop to ground"
            else:
                action_hint = "A: Pick Up | Y: Use/Equip"
        else:
            action_hint = "Right-click: Use | Left-click: Pick up/Move"
        lines = [
            stack.item_data.name,
            f"Type: {stack.item_data.type.value}",
            stack.item_data.description,
            f"Value: {stack.item_data.value}g",
            action_hint,
        ]
        max_w = max(font.size(l)[0] for l in lines) + 16
        h = len(lines) * (font.get_height() + 2) + 8
        # Position tooltip near gamepad cursor slot or mouse
        if self.gamepad_cursor >= 0:
            slot_size = settings.scaled_slot_size()
            padding = settings.scaled_padding()
            title_h = int(30 * settings.get_font_scale())
            col = self.gamepad_cursor % INVENTORY_COLS
            row = self.gamepad_cursor // INVENTORY_COLS
            mx = self.rect.x + padding + (col + 1) * (slot_size + padding)
            my = self.rect.y + title_h + row * (slot_size + padding)
        else:
            mx, my = pygame.mouse.get_pos()
        tx = min(mx + 15, settings.SCREEN_WIDTH - max_w - 5)
        ty = min(my + 15, settings.SCREEN_HEIGHT - h - 5)

        tip_surface = pygame.Surface((max_w, h), pygame.SRCALPHA)
        tip_surface.fill((20, 20, 30, 230))
        surface.blit(tip_surface, (tx, ty))
        pygame.draw.rect(surface, UI_BORDER, (tx, ty, max_w, h), 1)

        y = ty + 4
        for i, line in enumerate(lines):
            color = YELLOW if i == 0 else GRAY
            text = font.render(line, True, color)
            surface.blit(text, (tx + 8, y))
            y += font.get_height() + 2
