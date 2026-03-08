import pygame
import src.settings as settings
from src.settings import (WHITE, RED, GREEN, YELLOW,
                          BLACK, GRAY, GOLD_COLOR, HP_BAR_GREEN, HP_BAR_RED,
                          XP_BAR_BLUE, MANA_BAR_GREEN, GRIT_BAR_COLOR, XP_THRESHOLDS)


class HUD:
    def __init__(self):
        self.messages = []  # list of (text, timer)
        self.font = None
        self.small_font = None
        self.minimap_visible = False  # Toggle with 'M' key
        self.fps_visible = False  # Toggle with 'F' key
        self.current_fps = 0.0  # Set by game.py each frame
        self.controller_connected = False  # Updated by game.py each frame
        self.near_merchant = False  # Set by game.py when player is near a merchant

    def init_fonts(self):
        s = settings.scaled_font_size
        self.font = pygame.font.Font(None, s(24))
        self.small_font = pygame.font.Font(None, s(18))

    def show_message(self, text: str, duration: float = 2.0):
        self.messages.append([text, duration])
        if len(self.messages) > 5:
            self.messages.pop(0)

    def update(self, dt: float):
        self.messages = [[t, d - dt] for t, d in self.messages if d - dt > 0]

    def _layout(self) -> dict:
        """Compute all HUD positions/sizes scaled to current resolution."""
        scale = settings.get_font_scale()
        margin = int(10 * scale)

        # HP bar
        bar_w = int(200 * scale)
        bar_h = int(20 * scale)
        hp_x, hp_y = margin, margin

        # Mana/Grit bar (below HP bar) — rendered if player has mana or grit
        mana_h = int(14 * scale)
        mana_y = hp_y + bar_h + int(3 * scale)
        # Grit bar uses the same slot as mana (heroes never have both)
        grit_h = mana_h
        grit_y = mana_y

        # XP bar (below mana bar)
        xp_h = int(14 * scale)
        xp_y = mana_y + mana_h + int(3 * scale)

        # Level text (right of HP bar)
        level_x = hp_x + bar_w + int(15 * scale)
        level_y = hp_y

        # Gold text (right of XP bar)
        gold_x = level_x
        gold_y = xp_y

        # Weapon text (below XP bar)
        weapon_y = xp_y + xp_h + int(6 * scale)

        # Armor text (below weapon)
        armor_y = weapon_y + int(18 * scale)

        # FPS counter (below armor, only shown when toggled)
        fps_y = armor_y + int(18 * scale)

        # Buffs (below FPS or armor depending on visibility)
        buff_y_start = fps_y + (int(18 * scale) if self.fps_visible else 0)
        buff_line_h = int(16 * scale)

        # Messages (from bottom)
        msg_line_h = int(30 * scale)

        # Hint (bottom left)
        hint_y = settings.SCREEN_HEIGHT - int(20 * scale)

        return {
            'margin': margin, 'bar_w': bar_w, 'bar_h': bar_h,
            'hp_x': hp_x, 'hp_y': hp_y,
            'mana_h': mana_h, 'mana_y': mana_y,
            'grit_h': grit_h, 'grit_y': grit_y,
            'xp_h': xp_h, 'xp_y': xp_y,
            'level_x': level_x, 'level_y': level_y,
            'gold_x': gold_x, 'gold_y': gold_y,
            'weapon_x': margin, 'weapon_y': weapon_y,
            'armor_x': margin, 'armor_y': armor_y,
            'fps_x': margin, 'fps_y': fps_y,
            'buff_x': margin, 'buff_y_start': buff_y_start,
            'buff_line_h': buff_line_h,
            'msg_line_h': msg_line_h,
            'hint_y': hint_y,
        }

    def draw(self, surface: pygame.Surface, player):
        if not self.font:
            self.init_fonts()

        L = self._layout()

        # HP bar
        self._draw_bar(surface, L['hp_x'], L['hp_y'], L['bar_w'], L['bar_h'],
                       player.hp, player.max_hp,
                       HP_BAR_RED, HP_BAR_GREEN, f"HP: {player.hp}/{player.max_hp}")

        # Mana bar (only if player has max_mana > 0)
        if player.max_mana > 0:
            mana_current = int(player.mana)
            self._draw_bar(surface, L['hp_x'], L['mana_y'], L['bar_w'], L['mana_h'],
                           mana_current, player.max_mana,
                           (20, 40, 20), MANA_BAR_GREEN,
                           f"Mana: {mana_current}/{player.max_mana}")

        # Grit bar (only if player has max_grit > 0; shares slot with mana)
        if getattr(player, 'max_grit', 0) > 0:
            grit_current = int(player.grit)
            self._draw_bar(surface, L['hp_x'], L['grit_y'], L['bar_w'], L['grit_h'],
                           grit_current, player.max_grit,
                           (60, 35, 10), GRIT_BAR_COLOR,
                           f"Grit: {grit_current}/{player.max_grit}")

        # XP bar (thresholds scaled by hero's xp_required_mult)
        xp_mult = getattr(player, 'xp_required_mult', 1.0)
        xp_needed = self._get_xp_for_next(player.level, xp_mult)
        xp_current = player.xp - self._get_xp_for_current(player.level, xp_mult)
        xp_range = xp_needed - self._get_xp_for_current(player.level, xp_mult)
        if xp_range <= 0:
            xp_range = 1
            xp_current = 1
        self._draw_bar(surface, L['hp_x'], L['xp_y'], L['bar_w'], L['xp_h'],
                       xp_current, xp_range,
                       (20, 20, 60), XP_BAR_BLUE, f"XP: {player.xp}")

        # Level
        level_text = self.font.render(f"Lv. {player.level}", True, WHITE)
        surface.blit(level_text, (L['level_x'], L['level_y']))

        # Gold
        gold_text = self.font.render(f"Gold: {player.gold}", True, GOLD_COLOR)
        surface.blit(gold_text, (L['gold_x'], L['gold_y']))

        # Equipped weapon
        weapon_text = self.small_font.render(
            f"Weapon: {player.equipped_weapon.name} (DMG: {player.equipped_weapon.damage})",
            True, WHITE)
        surface.blit(weapon_text, (L['weapon_x'], L['weapon_y']))

        # Equipped armor (black box with white text for readability)
        if player.equipped_armor:
            armor_name = player.equipped_armor.get("name", "Unknown")
            armor_def = player.equipped_armor.get("defense", 0)
            armor_label = f"Armor: {armor_name} (DEF: {armor_def})"
        else:
            armor_label = "Armor: None"
        armor_text = self.small_font.render(armor_label, True, WHITE)
        ax, ay = L['armor_x'], L['armor_y']
        pad = int(3 * settings.get_font_scale())
        armor_bg = pygame.Surface(
            (armor_text.get_width() + pad * 2, armor_text.get_height() + pad * 2),
            pygame.SRCALPHA)
        armor_bg.fill((0, 0, 0, 210))
        surface.blit(armor_bg, (ax - pad, ay - pad))
        surface.blit(armor_text, (ax, ay))

        # FPS counter
        if self.fps_visible:
            fps_val = int(self.current_fps)
            fps_color = (0, 255, 0) if fps_val >= 55 else (
                (255, 255, 0) if fps_val >= 30 else (255, 60, 60))
            fps_text = self.small_font.render(f"FPS: {fps_val}", True, fps_color)
            surface.blit(fps_text, (L['fps_x'], L['fps_y']))

        # Active buffs
        x = L['buff_x']
        y = L['buff_y_start']
        for buff_type, buff_info in player.buffs.items():
            if buff_info["remaining"] > 0:
                text = self.small_font.render(
                    f"{buff_type}: +{buff_info['value']} ({buff_info['remaining']:.0f}s)",
                    True, GREEN)
                surface.blit(text, (x, y))
                y += L['buff_line_h']

        # Messages
        sw, sh = settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT
        msg_y = sh - L['msg_line_h'] * len(self.messages) - L['margin']
        for text, timer in self.messages:
            alpha = min(1.0, timer) * 255
            msg = self.font.render(text, True, YELLOW)
            msg.set_alpha(int(alpha))
            surface.blit(msg, (sw // 2 - msg.get_width() // 2, msg_y))
            msg_y += L['msg_line_h']

        # Merchant interaction prompt (above controls hint)
        if self.near_merchant:
            if self.controller_connected:
                interact_text = "Press B to Shop"
            else:
                interact_text = "Press E to Shop"
            interact = self.font.render(interact_text, True, GOLD_COLOR)
            ix = sw // 2 - interact.get_width() // 2
            iy = L['hint_y'] - interact.get_height() - int(10 * settings.get_font_scale())
            ibg = pygame.Surface((interact.get_width() + 16, interact.get_height() + 6),
                                 pygame.SRCALPHA)
            ibg.fill((0, 0, 0, 180))
            surface.blit(ibg, (ix - 8, iy - 3))
            surface.blit(interact, (ix, iy))

        # Controls hint (bottom center, with dark background for readability)
        if self.controller_connected:
            hint_text = ("Stick:Move  A:Attack  RB:Spell  D-pad L/R:Select  "
                         "B:Pickup  X:Inventory  Y:Map  Start:Menu")
        else:
            hint_text = ("WASD:Move  SPACE:Attack  Q:Spell  1-9:Select Spell  "
                         "E:Pickup  I:Inventory  M:Map  ESC:Menu")
        hint = self.font.render(hint_text, True, (220, 220, 220))
        hint_x = sw // 2 - hint.get_width() // 2
        hint_y = L['hint_y']
        # Dark semi-transparent background
        hint_bg = pygame.Surface((hint.get_width() + 16, hint.get_height() + 6), pygame.SRCALPHA)
        hint_bg.fill((0, 0, 0, 140))
        surface.blit(hint_bg, (hint_x - 8, hint_y - 3))
        surface.blit(hint, (hint_x, hint_y))

        # Spell/ability selection list (left side, below grit/mana bar)
        self.draw_spell_list(surface, player, L)

    def draw_spell_list(self, surface, player, layout: dict):
        """Draw a numbered spell/ability selection panel on the left side."""
        if not hasattr(player, 'get_castable_spells'):
            return
        castable = player.get_castable_spells()
        if not castable:
            return

        scale = settings.get_font_scale()
        font = self.small_font
        line_h = int(18 * scale)
        pad_x = int(6 * scale)
        pad_y = int(4 * scale)
        margin = layout.get('margin', int(10 * scale))

        # Start below all upper-left HUD elements:
        # weapon → armor → fps (if toggled) → active buffs → spell list
        active_buff_count = sum(
            1 for v in player.buffs.values() if v.get("remaining", 0) > 0
        ) if hasattr(player, 'buffs') else 0
        list_y = (layout['buff_y_start']
                  + active_buff_count * layout['buff_line_h']
                  + int(8 * scale))
        list_x = margin

        # Render up to 9 entries; don't need scrolling (never > 11 but only 9 shown)
        visible = castable[:9]
        for i, ab in enumerate(visible):
            ab_id = ab.get("id", "")
            ab_name = ab.get("name", ab_id)
            cost = ab.get("mana_cost", ab.get("grit_cost", 0))
            cd = player.get_ability_cooldown(ab_id) if hasattr(player, 'get_ability_cooldown') else 0
            resource = player.mana if "mana_cost" in ab else getattr(player, 'grit', 0)
            selected = (i == getattr(player, 'selected_spell_idx', 0))

            # Choose text color
            if cd > 0:
                color = (140, 140, 140)       # Gray: on cooldown
                suffix = f" ({cd:.0f}s)"
            elif resource < cost:
                color = (220, 60, 60)          # Red: not enough resource
                suffix = ""
            elif selected:
                color = GOLD_COLOR             # Gold: selected
                suffix = ""
            else:
                color = (210, 210, 210)        # White-ish: available
                suffix = ""

            unit = "mp" if "mana_cost" in ab else "grit"
            label = f"[{i+1}] {ab_name}  {cost}{unit}{suffix}"
            text_surf = font.render(label, True, color)

            row_y = list_y + i * (line_h + pad_y)

            # Draw selection highlight
            if selected:
                hl = pygame.Surface(
                    (text_surf.get_width() + pad_x * 2, text_surf.get_height() + pad_y),
                    pygame.SRCALPHA)
                hl.fill((80, 60, 0, 160))
                surface.blit(hl, (list_x - pad_x, row_y - pad_y // 2))

            surface.blit(text_surf, (list_x, row_y))

        # Show auto-trigger resurrection label if unlocked (always at bottom of list)
        auto_spells = [ab for ab in castable if ab.get("auto_trigger")]
        # These are filtered out of get_castable_spells(), so check the full available list
        if hasattr(player, 'get_available_spells'):
            for ab in player.get_available_spells():
                if ab.get("auto_trigger"):
                    ab_name = ab.get("name", ab.get("id", ""))
                    cost = ab.get("mana_cost", ab.get("grit_cost", 0))
                    unit = "mp" if "mana_cost" in ab else "grit"
                    row_y = list_y + len(visible) * (line_h + pad_y)
                    label = f"[auto] {ab_name}  {cost}{unit}"
                    text_surf = font.render(label, True, (160, 120, 220))
                    surface.blit(text_surf, (list_x, row_y))

    def _draw_bar(self, surface, x, y, w, h, value, max_value, bg_color, fill_color, text):
        pygame.draw.rect(surface, bg_color, (x, y, w, h))
        fill_w = max(0, int(w * min(value / max(max_value, 1), 1.0)))
        pygame.draw.rect(surface, fill_color, (x, y, fill_w, h))
        pygame.draw.rect(surface, WHITE, (x, y, w, h), 1)
        label = self.small_font.render(text, True, WHITE)
        surface.blit(label, (x + (w - label.get_width()) // 2, y + (h - label.get_height()) // 2))

    def _get_xp_for_next(self, level, xp_mult=1.0):
        if level + 1 < len(XP_THRESHOLDS):
            return int(XP_THRESHOLDS[level + 1] * xp_mult)
        return int((XP_THRESHOLDS[-1] + 10000) * xp_mult)

    def _get_xp_for_current(self, level, xp_mult=1.0):
        if level < len(XP_THRESHOLDS):
            return int(XP_THRESHOLDS[level] * xp_mult)
        return int(XP_THRESHOLDS[-1] * xp_mult)

    def toggle_minimap(self):
        self.minimap_visible = not self.minimap_visible

    def toggle_fps(self):
        self.fps_visible = not self.fps_visible

    def draw_minimap(self, surface: pygame.Surface, stage, player):
        """Draw a small mini-map in the top-right corner showing the stage layout."""
        if not self.minimap_visible:
            return

        scale = settings.get_font_scale()
        sw = settings.SCREEN_WIDTH

        # Mini-map size scales with resolution
        map_size = int(150 * scale)
        margin = int(10 * scale)
        # Position: top-right, below stage info text
        stage_text_h = int(30 * scale)
        mx = sw - map_size - margin
        my = margin + stage_text_h

        # Create mini-map surface
        minimap = pygame.Surface((map_size, map_size), pygame.SRCALPHA)
        minimap.fill((20, 30, 20, 180))

        # Scale factor from world to minimap
        pw = stage.pixel_width
        ph = stage.pixel_height
        if pw <= 0 or ph <= 0:
            return
        # Maintain aspect ratio
        world_max = max(pw, ph)
        ms = (map_size - 4) / world_max  # leave 2px border on each side

        offset_x = 2 + (map_size - 4 - int(pw * ms)) // 2
        offset_y = 2 + (map_size - 4 - int(ph * ms)) // 2

        # Draw boss area
        if stage.boss_area and not stage.boss_defeated:
            ba = stage.boss_area
            ba_rect = pygame.Rect(
                offset_x + int(ba.x * ms), offset_y + int(ba.y * ms),
                max(2, int(ba.width * ms)), max(2, int(ba.height * ms)))
            pygame.draw.rect(minimap, (100, 30, 30, 100), ba_rect)
            pygame.draw.rect(minimap, (200, 50, 50, 150), ba_rect, 1)

        # Draw exit portal
        if stage.exit_portal:
            ex = offset_x + int(stage.exit_portal.world_x * ms)
            ey = offset_y + int(stage.exit_portal.world_y * ms)
            pygame.draw.circle(minimap, (150, 100, 255), (ex, ey), max(3, int(4 * scale)))

        # Draw treasure chests
        for chest in stage.chests:
            if chest.is_alive:
                cx = offset_x + int(chest.world_x * ms)
                cy = offset_y + int(chest.world_y * ms)
                color = (255, 200, 40) if not chest.locked else (200, 40, 40)
                pygame.draw.rect(minimap, color, (cx - 1, cy - 1, 3, 3))

        # Draw NPCs (blue dots)
        for npc in stage.npcs:
            nx = offset_x + int(npc.world_x * ms)
            ny = offset_y + int(npc.world_y * ms)
            color = (40, 200, 255) if not npc.is_merchant else (255, 215, 0)
            pygame.draw.circle(minimap, color, (nx, ny), 2)

        # Draw monsters (red dots, boss is bigger)
        for m in stage.monsters:
            if m.is_alive:
                mmx = offset_x + int(m.world_x * ms)
                mmy = offset_y + int(m.world_y * ms)
                if m.is_boss:
                    pygame.draw.circle(minimap, (255, 60, 60), (mmx, mmy), max(3, int(4 * scale)))
                else:
                    pygame.draw.circle(minimap, (200, 50, 50), (mmx, mmy), 2)

        # Draw player (white dot, slightly larger)
        px = offset_x + int(player.world_x * ms)
        py = offset_y + int(player.world_y * ms)
        pygame.draw.circle(minimap, WHITE, (px, py), max(3, int(3 * scale)))
        pygame.draw.circle(minimap, (200, 200, 255), (px, py), max(3, int(3 * scale)), 1)

        # Border
        pygame.draw.rect(minimap, (120, 100, 80), (0, 0, map_size, map_size), 1)

        surface.blit(minimap, (mx, my))
