"""
Inventory screen.

Left panel  — 10 equipment slots (weapon · shield · helm · chest · gloves ·
               boots · belt · ring×2 · amulet) with colour-coded item names.
Right panel — backpack grid (12 slots) + potion count.
Tooltip     — full stat breakdown when hovering any item.
"""
from __future__ import annotations

import pygame
from src.settings import (SCREEN_WIDTH, SCREEN_HEIGHT, HUD_HEIGHT,
                           GRAY, LIGHT_GRAY,
                           YELLOW, RED, GREEN)
from src.items.item import (EquipItem, HealthPotion,
                             SLOT_ORDER, SLOT_LABELS, Q_COLOR, QUALITY_NORMAL)
from src.locale import t, get_slot_label

# ── Panel geometry ─────────────────────────────────────────────────────────────
_PW   = 700
_PH   = 460
_PX   = (SCREEN_WIDTH  - _PW) // 2
_PY   = (SCREEN_HEIGHT - HUD_HEIGHT - _PH) // 2

_LEFT_W  = 290       # equipment-slot panel width
_RIGHT_X = _PX + _LEFT_W + 10
_PAD     = 10

_SLOT_H  = 34        # height of each equipment row
_SLOT_W  = _LEFT_W - _PAD * 2

_BAG_COLS  = 4
_BAG_ROWS  = 3
_BAG_CELL  = 56      # backpack cell size (px)
_BAG_GAP   = 6

# ── Colours ───────────────────────────────────────────────────────────────────
_COL_BG     = (12,  8,  4)
_COL_PANEL  = (22, 16, 10)
_COL_BORDER = (68, 100, 176)     # same blue as dungeon walls
_COL_SLOT   = (30, 22, 14)
_COL_SLOT_H = (50, 38, 24)
_COL_EQUIP  = (252, 188, 0)      # gold border on equipped slot
_COL_SEP    = (45, 35, 22)

_NORMAL_COL   = Q_COLOR[QUALITY_NORMAL]
_POTION_COL   = (252,  80,  80)
_STAT_COL     = (100, 220, 100)
_FLAVOR_COL   = (140, 120,  80)

# ── Tooltip constants ─────────────────────────────────────────────────────────
_TIP_MAX_W  = 280
_TIP_PAD    = 6
_TIP_LINE_H = 14


class InventoryScreen:
    def __init__(self):
        self._font_lg  = pygame.font.SysFont("monospace", 18, bold=True)
        self._font_md  = pygame.font.SysFont("monospace", 14, bold=True)
        self._font_sm  = pygame.font.SysFont("monospace", 12)
        self._font_xs  = pygame.font.SysFont("monospace", 11)

        self._msg    = ""
        self._msg_t  = 0.0

        # Hover tracking
        self._hov_equip_key: str | None  = None   # equipment slot key
        self._hov_bag_idx:   int         = -1      # backpack index

    # ── Public API ────────────────────────────────────────────────────────────

    def notify(self, text: str):
        self._msg   = text
        self._msg_t = 2.5

    def update(self, dt: float):
        self._msg_t = max(0.0, self._msg_t - dt)
        mx, my = pygame.mouse.get_pos()
        self._hov_equip_key = self._equip_key_at(mx, my)
        self._hov_bag_idx   = self._bag_idx_at(mx, my)

    def handle_click(self, mx: int, my: int, player) -> bool:
        # Click on equipment slot → unequip
        key = self._equip_key_at(mx, my)
        if key is not None and player.equipment.get(key) is not None:
            old = player.equipment[key]
            player.unequip(key)
            self.notify(t("inv.unequipped", name=old.display_name))
            return True

        # Click on backpack item → equip / use
        idx = self._bag_idx_at(mx, my)
        if idx < 0:
            return False
        items = self._bag_items(player)
        if idx >= len(items):
            return False
        item = items[idx]
        if isinstance(item, EquipItem):
            # Find slot key
            slot = item.slot
            key2 = slot
            if slot == "ring":
                if player.equipment.get("ring") is None:
                    key2 = "ring"
                elif player.equipment.get("ring2") is None:
                    key2 = "ring2"
                else:
                    key2 = "ring"   # overwrite ring1
            old  = player.equip(item, key2)
            if old:
                player.backpack.append(old)
            self.notify(t("inv.equipped", name=item.display_name))
        elif isinstance(item, HealthPotion):
            if player.hp < player.max_hp_total:
                player.potions.remove(item)
                player.heal(item.heal_amount)
                self.notify(t("inv.used_potion", n=item.heal_amount))
            else:
                self.notify(t("inv.full_hp"))
        return True

    def draw(self, surface: pygame.Surface, player):
        # ── Dimmed overlay ────────────────────────────────────────────────────
        ov = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 200))
        surface.blit(ov, (0, 0))

        # ── Main panel ────────────────────────────────────────────────────────
        panel = pygame.Rect(_PX, _PY, _PW, _PH)
        pygame.draw.rect(surface, _COL_BG, panel)
        pygame.draw.rect(surface, _COL_BORDER, panel, 2)

        # Title bar
        pygame.draw.rect(surface, _COL_PANEL,
                         (_PX, _PY, _PW, 28))
        pygame.draw.line(surface, _COL_BORDER,
                         (_PX, _PY + 28), (_PX + _PW, _PY + 28))
        title_s = self._font_lg.render(t("inv.title"), True, YELLOW)
        surface.blit(title_s, (_PX + _PAD, _PY + 5))
        hint = self._font_xs.render(t("inv.hint"), True, GRAY)
        surface.blit(hint, (_PX + _PW - hint.get_width() - _PAD, _PY + 9))

        # Vertical divider
        dx = _PX + _LEFT_W
        pygame.draw.line(surface, _COL_SEP, (dx, _PY + 30), (dx, _PY + _PH - 4))

        # ── Left: equipment slots ─────────────────────────────────────────────
        self._draw_equip_slots(surface, player)

        # ── Right: backpack + potions ─────────────────────────────────────────
        self._draw_backpack(surface, player)

        # ── Status message ────────────────────────────────────────────────────
        if self._msg_t > 0:
            alpha = min(255, int(self._msg_t * 180))
            msg   = self._font_sm.render(self._msg, True, YELLOW)
            msg.set_alpha(alpha)
            surface.blit(msg, (_PX + _PAD, _PY + _PH - 18))

        # ── Tooltip ───────────────────────────────────────────────────────────
        self._draw_tooltip(surface, player)

    # ── Equipment slots panel ─────────────────────────────────────────────────

    def _equip_slot_rect(self, idx: int) -> pygame.Rect:
        y = _PY + 34 + idx * (_SLOT_H + 3)
        return pygame.Rect(_PX + _PAD, y, _SLOT_W, _SLOT_H)

    def _equip_key_at(self, mx: int, my: int) -> str | None:
        for i, key in enumerate(SLOT_ORDER):
            if self._equip_slot_rect(i).collidepoint(mx, my):
                return key
        return None

    def _draw_equip_slots(self, surface: pygame.Surface, player):
        for i, key in enumerate(SLOT_ORDER):
            r    = self._equip_slot_rect(i)
            item = player.equipment.get(key)
            hov  = (key == self._hov_equip_key)

            bg = _COL_SLOT_H if hov else _COL_SLOT
            pygame.draw.rect(surface, bg, r)

            if item is not None:
                pygame.draw.rect(surface, _COL_EQUIP, r, 1)   # gold border
            else:
                pygame.draw.rect(surface, _COL_SEP, r, 1)

            # Slot label
            lbl = self._font_xs.render(get_slot_label(key), True, GRAY)
            surface.blit(lbl, (r.left + 3, r.top + 2))

            # Item name (colour-coded by quality)
            if item is not None:
                name_col = item.quality_color
                name_txt = item.display_name
                # Truncate if needed
                n = self._font_sm.render(name_txt, True, name_col)
                while n.get_width() > _SLOT_W - 60 and len(name_txt) > 4:
                    name_txt = name_txt[:-1]
                    n = self._font_sm.render(name_txt + "…", True, name_col)
                surface.blit(n, (r.left + 64, r.centery - n.get_height() // 2))
                # Primary stat badge
                ps = item.primary_stat
                if ps > 0:
                    is_wpn  = item.slot == "weapon"
                    ps_lbl  = f"+{ps} {'ATK' if is_wpn else 'DEF'}"
                    ps_surf = self._font_xs.render(ps_lbl, True,
                                                   (252, 160, 100) if is_wpn else (100, 160, 252))
                    surface.blit(ps_surf, (r.right - ps_surf.get_width() - 3,
                                           r.centery - ps_surf.get_height() // 2))
            else:
                empty = self._font_xs.render(t("inv.empty_slot"), True, (50, 40, 30))
                surface.blit(empty, (r.left + 64, r.centery - empty.get_height() // 2))

    # ── Backpack panel ────────────────────────────────────────────────────────

    def _bag_cell_rect(self, idx: int) -> pygame.Rect:
        col = idx % _BAG_COLS
        row = idx // _BAG_COLS
        x   = _RIGHT_X + _PAD + col * (_BAG_CELL + _BAG_GAP)
        y   = _PY + 36  + row * (_BAG_CELL + _BAG_GAP)
        return pygame.Rect(x, y, _BAG_CELL, _BAG_CELL)

    def _bag_idx_at(self, mx: int, my: int) -> int:
        for i in range(_BAG_COLS * _BAG_ROWS):
            if self._bag_cell_rect(i).collidepoint(mx, my):
                return i
        return -1

    def _bag_items(self, player) -> list:
        return player.backpack + player.potions

    def _draw_backpack(self, surface: pygame.Surface, player):
        bx = _RIGHT_X + _PAD
        by = _PY + 36

        # Section header
        hdr = self._font_md.render(t("inv.backpack"), True, LIGHT_GRAY)
        surface.blit(hdr, (bx, _PY + 36 - 16))

        items = self._bag_items(player)

        for i in range(_BAG_COLS * _BAG_ROWS):
            r   = self._bag_cell_rect(i)
            hov = (i == self._hov_bag_idx)
            bg  = _COL_SLOT_H if hov else _COL_SLOT
            pygame.draw.rect(surface, bg, r)

            if i < len(items):
                item = items[i]
                # Border by quality
                if isinstance(item, EquipItem):
                    bc = item.quality_color
                    pygame.draw.rect(surface, bc, r, 1 if item.quality == QUALITY_NORMAL else 2)
                    # Icon: draw item's ground shape scaled to cell
                    icon_rect = r.inflate(-12, -12)
                    item._draw_armor_icon(surface, icon_rect, bc) if item.slot != "weapon" \
                        else item._draw_weapon_icon(surface, icon_rect, bc)
                    # Quality initial badge (M/R/U)
                    badge_chars = {1: "M", 2: "R", 3: "U"}
                    bc_char = badge_chars.get(item.quality, "")
                    if bc_char:
                        badge = self._font_xs.render(bc_char, True, item.quality_color)
                        surface.blit(badge, (r.right - badge.get_width() - 2, r.top + 2))
                elif isinstance(item, HealthPotion):
                    pygame.draw.rect(surface, _POTION_COL, r, 1)
                    lbl = self._font_sm.render("HP", True, _POTION_COL)
                    surface.blit(lbl, lbl.get_rect(center=r.center))
            else:
                pygame.draw.rect(surface, _COL_SEP, r, 1)

        # Potion summary below grid
        pot_y = _PY + 36 + _BAG_ROWS * (_BAG_CELL + _BAG_GAP) + 4
        pc = len(player.potions)
        col = _POTION_COL if pc else GRAY
        pot_txt = self._font_sm.render(t("inv.potions", n=pc), True, col)
        surface.blit(pot_txt, (bx, pot_y))

        # Character stats summary below potions
        sy = pot_y + 20
        stats = [
            (f"ATK {player.attack}",   (252, 160, 100)),
            (f"DEF {player.defense}",  (100, 160, 252)),
            (f"HP  {int(player.hp)}/{player.max_hp_total}", RED),
            (f"LV  {player.level}",    YELLOW),
        ]
        if player.crit_chance > 0:
            stats.append((f"CRIT {int(player.crit_chance)}%", (220, 220, 80)))
        if player.life_steal > 0:
            stats.append((f"LS {int(player.life_steal)}%",    (220, 80,  80)))
        if player.hp_regen_rate > 0:
            stats.append((f"REGEN {player.hp_regen_rate:.1f}/s", GREEN))
        if player.gold_find_bonus > 0:
            stats.append((f"GF +{int(player.gold_find_bonus)}%", YELLOW))

        cols_per_row = 2
        cell_w = (_PW - _LEFT_W - _PAD * 3) // cols_per_row
        for j, (txt, col2) in enumerate(stats):
            sx = bx + (j % cols_per_row) * cell_w
            sy2 = sy + (j // cols_per_row) * 16
            s = self._font_xs.render(txt, True, col2)
            surface.blit(s, (sx, sy2))

    # ── Tooltip ───────────────────────────────────────────────────────────────

    def _draw_tooltip(self, surface: pygame.Surface, player):
        # Find the hovered item
        item = None
        if self._hov_equip_key is not None:
            item = player.equipment.get(self._hov_equip_key)
        elif self._hov_bag_idx >= 0:
            bag = self._bag_items(player)
            if self._hov_bag_idx < len(bag):
                item = bag[self._hov_bag_idx]

        if not isinstance(item, EquipItem):
            return

        # Build tooltip lines
        lines: list[tuple[str, tuple]] = []
        # Name header
        lines.append((item.display_name, item.quality_color))
        # Slot
        lines.append((f"{get_slot_label(item.slot).title()}  —  {item.base_name}",
                      GRAY))
        lines.append(("", GRAY))  # spacer
        # All stat lines
        lines.extend(item.stat_lines())

        # Comparison with equipped item in same slot
        eq_key  = item.slot
        eq_item = player.equipment.get(eq_key) or player.equipment.get("ring2")
        if eq_item and eq_item is not item:
            lines.append(("", GRAY))
            lines.append((t("inv.vs_equipped"), (80, 80, 80)))
            lines.append((eq_item.display_name, eq_item.quality_color))
            for ml in eq_item.stat_lines():
                if ml[0]:
                    lines.append((f"  {ml[0]}", (80, 80, 80)))

        # Measure tooltip size
        tw = max((_TIP_MAX_W,
                  *(self._font_sm.size(l[0])[0] + _TIP_PAD * 2 for l in lines)))
        th = len(lines) * _TIP_LINE_H + _TIP_PAD * 2

        # Position near mouse, clamp to screen
        mx, my = pygame.mouse.get_pos()
        tx = min(mx + 14, SCREEN_WIDTH  - tw - 4)
        ty = min(my - 8,  SCREEN_HEIGHT - th - 4)
        ty = max(ty, 4)

        # Draw background
        bg = pygame.Surface((tw, th), pygame.SRCALPHA)
        bg.fill((8, 4, 0, 230))
        surface.blit(bg, (tx, ty))
        pygame.draw.rect(surface, item.quality_color, (tx, ty, tw, th), 1)

        # Draw lines
        y = ty + _TIP_PAD
        for txt, col in lines:
            if not txt:
                y += _TIP_LINE_H // 2
                continue
            s = self._font_xs.render(txt, True, col)
            surface.blit(s, (tx + _TIP_PAD, y))
            y += _TIP_LINE_H
