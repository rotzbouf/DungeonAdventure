"""
Inventory screen.

Left panel   — 10 equipment slots, each showing item name + primary stat.
Right panel  — backpack grid with quality borders + comparison badges.
Tooltip      — full stat breakdown with ▲/▼/new delta vs. equipped item,
               plus a colour-coded UPGRADE / DOWNGRADE / SIMILAR verdict.
"""
from __future__ import annotations

import pygame
from src.settings import (SCREEN_WIDTH, SCREEN_HEIGHT, HUD_HEIGHT,
                           GRAY, LIGHT_GRAY, YELLOW, RED, GREEN)
from src.items.item import (EquipItem, HealthPotion,
                             SLOT_ORDER, SLOT_LABELS, Q_COLOR, QUALITY_NORMAL)
from src.locale import t, get_slot_label

# ── Panel geometry ─────────────────────────────────────────────────────────────
_PW  = 1020      # panel width
_PH  = 680       # panel height
_PX  = (SCREEN_WIDTH  - _PW) // 2
_PY  = (SCREEN_HEIGHT - HUD_HEIGHT - _PH) // 2

_LEFT_W  = 370                     # equipment-slot column width
_RIGHT_X = _PX + _LEFT_W + 12
_PAD     = 12

_SLOT_H  = 44                      # height per equipment row
_SLOT_W  = _LEFT_W - _PAD * 2

_BAG_COLS = 4
_BAG_ROWS = 3
_BAG_CELL = 70                     # backpack cell size
_BAG_GAP  = 8

# ── Palette ────────────────────────────────────────────────────────────────────
_COL_BG      = (12,  8,  4)
_COL_PANEL   = (22, 16, 10)
_COL_BORDER  = (68, 100, 176)
_COL_SLOT    = (30, 22, 14)
_COL_SLOT_H  = (50, 38, 24)
_COL_EQUIP   = (252, 188, 0)
_COL_SEP     = (45, 35, 22)

_NORMAL_COL  = Q_COLOR[QUALITY_NORMAL]
_POTION_COL  = (252, 80, 80)
_STAT_COL    = (100, 220, 100)
_FLAVOR_COL  = (140, 120, 80)

# Comparison colours
_CMP_BETTER  = ( 70, 220,  70)   # ▲ this item is better
_CMP_WORSE   = (220,  70,  70)   # ▼ this item is worse
_CMP_NEUTRAL = (110, 110, 110)   # ≈ same
_CMP_NEW     = ( 80, 200, 230)   # stat not on equipped item

# ── Stat kinds used in comparison ─────────────────────────────────────────────
def _cmp_mods():
    from src.items.item import (
        MOD_ATK, MOD_DEF, MOD_MAX_HP, MOD_MAX_MANA,
        MOD_CRIT, MOD_LIFE_STEAL, MOD_HP_REGEN,
        MOD_ATK_SPD, MOD_SPEED, MOD_THORNS, MOD_GOLD_FIND,
    )
    return [
        (MOD_ATK,        "ATK"),
        (MOD_DEF,        "DEF"),
        (MOD_MAX_HP,     "Max HP"),
        (MOD_MAX_MANA,   "Mana"),
        (MOD_CRIT,       "Crit%"),
        (MOD_LIFE_STEAL, "Life Steal%"),
        (MOD_HP_REGEN,   "HP Regen"),
        (MOD_ATK_SPD,    "Atk Spd%"),
        (MOD_SPEED,      "Move Spd%"),
        (MOD_THORNS,     "Thorns"),
        (MOD_GOLD_FIND,  "Gold Find%"),
    ]


class InventoryScreen:
    def __init__(self):
        self._font_lg = pygame.font.SysFont("monospace", 22, bold=True)
        self._font_md = pygame.font.SysFont("monospace", 18, bold=True)
        self._font_sm = pygame.font.SysFont("monospace", 16)
        self._font_xs = pygame.font.SysFont("monospace", 14)

        self._msg   = ""
        self._msg_t = 0.0

        self._hov_equip_key: str | None = None
        self._hov_bag_idx:   int        = -1

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
        key = self._equip_key_at(mx, my)
        if key is not None and player.equipment.get(key) is not None:
            old = player.equipment[key]
            player.unequip(key)
            self.notify(t("inv.unequipped", name=old.display_name))
            return True

        idx = self._bag_idx_at(mx, my)
        if idx < 0:
            return False
        items = self._bag_items(player)
        if idx >= len(items):
            return False
        item = items[idx]
        if isinstance(item, EquipItem):
            slot = item.slot
            key2 = slot
            if slot == "ring":
                if player.equipment.get("ring") is None:
                    key2 = "ring"
                elif player.equipment.get("ring2") is None:
                    key2 = "ring2"
                else:
                    key2 = "ring"
            old = player.equip(item, key2)
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

    # ── Main draw ─────────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface, player):
        ov = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 210))
        surface.blit(ov, (0, 0))

        panel = pygame.Rect(_PX, _PY, _PW, _PH)
        pygame.draw.rect(surface, _COL_BG, panel)
        pygame.draw.rect(surface, _COL_BORDER, panel, 2)

        # Title bar
        hdr_h = 34
        pygame.draw.rect(surface, _COL_PANEL, (_PX, _PY, _PW, hdr_h))
        pygame.draw.line(surface, _COL_BORDER,
                         (_PX, _PY + hdr_h), (_PX + _PW, _PY + hdr_h))
        title_s = self._font_lg.render(t("inv.title"), True, YELLOW)
        surface.blit(title_s, (_PX + _PAD, _PY + (hdr_h - title_s.get_height()) // 2))
        hint = self._font_xs.render(t("inv.hint"), True, GRAY)
        surface.blit(hint, (_PX + _PW - hint.get_width() - _PAD,
                             _PY + (hdr_h - hint.get_height()) // 2))

        # Vertical divider
        pygame.draw.line(surface, _COL_SEP,
                         (_PX + _LEFT_W, _PY + hdr_h + 2),
                         (_PX + _LEFT_W, _PY + _PH - 4))

        self._draw_equip_slots(surface, player, hdr_h)
        self._draw_backpack(surface, player, hdr_h)

        if self._msg_t > 0:
            alpha = min(255, int(self._msg_t * 180))
            msg   = self._font_sm.render(self._msg, True, YELLOW)
            msg.set_alpha(alpha)
            surface.blit(msg, (_PX + _PAD, _PY + _PH - msg.get_height() - 6))

        self._draw_tooltip(surface, player)

    # ── Equipment slots ───────────────────────────────────────────────────────

    def _equip_slot_rect(self, idx: int) -> pygame.Rect:
        y = _PY + 40 + idx * (_SLOT_H + 4)
        return pygame.Rect(_PX + _PAD, y, _SLOT_W, _SLOT_H)

    def _equip_key_at(self, mx: int, my: int) -> str | None:
        for i, key in enumerate(SLOT_ORDER):
            if self._equip_slot_rect(i).collidepoint(mx, my):
                return key
        return None

    def _draw_equip_slots(self, surface: pygame.Surface, player, hdr_h: int):
        for i, key in enumerate(SLOT_ORDER):
            r    = self._equip_slot_rect(i)
            item = player.equipment.get(key)
            hov  = (key == self._hov_equip_key)

            pygame.draw.rect(surface, _COL_SLOT_H if hov else _COL_SLOT, r)
            pygame.draw.rect(surface, _COL_EQUIP if item else _COL_SEP, r, 1)

            # Slot label
            lbl = self._font_xs.render(get_slot_label(key), True, GRAY)
            surface.blit(lbl, (r.left + 4, r.centery - lbl.get_height() // 2))

            if item is not None:
                # Item name
                name_col = item.quality_color
                name_txt = item.display_name
                max_w    = _SLOT_W - 80
                n = self._font_sm.render(name_txt, True, name_col)
                while n.get_width() > max_w and len(name_txt) > 4:
                    name_txt = name_txt[:-1]
                    n = self._font_sm.render(name_txt + "…", True, name_col)
                surface.blit(n, (r.left + 68, r.centery - n.get_height() // 2))

                # Primary stat badge
                ps = item.primary_stat
                if ps > 0:
                    is_wpn  = item.slot == "weapon"
                    badge   = f"+{ps} {'ATK' if is_wpn else 'DEF'}"
                    bc      = (252, 160, 100) if is_wpn else (100, 160, 252)
                    bs      = self._font_xs.render(badge, True, bc)
                    surface.blit(bs, (r.right - bs.get_width() - 4,
                                      r.centery - bs.get_height() // 2))
            else:
                empty = self._font_xs.render(t("inv.empty_slot"), True, (50, 40, 30))
                surface.blit(empty, (r.left + 68, r.centery - empty.get_height() // 2))

    # ── Backpack ──────────────────────────────────────────────────────────────

    def _bag_cell_rect(self, idx: int) -> pygame.Rect:
        col = idx % _BAG_COLS
        row = idx // _BAG_COLS
        x   = _RIGHT_X + _PAD + col * (_BAG_CELL + _BAG_GAP)
        y   = _PY + 52  + row * (_BAG_CELL + _BAG_GAP)
        return pygame.Rect(x, y, _BAG_CELL, _BAG_CELL)

    def _bag_idx_at(self, mx: int, my: int) -> int:
        for i in range(_BAG_COLS * _BAG_ROWS):
            if self._bag_cell_rect(i).collidepoint(mx, my):
                return i
        return -1

    def _bag_items(self, player) -> list:
        return player.backpack + player.potions

    def _draw_backpack(self, surface: pygame.Surface, player, hdr_h: int):
        bx = _RIGHT_X + _PAD

        hdr = self._font_md.render(t("inv.backpack"), True, LIGHT_GRAY)
        surface.blit(hdr, (bx, _PY + hdr_h + 6))

        items = self._bag_items(player)

        for i in range(_BAG_COLS * _BAG_ROWS):
            r   = self._bag_cell_rect(i)
            hov = (i == self._hov_bag_idx)
            pygame.draw.rect(surface, _COL_SLOT_H if hov else _COL_SLOT, r)

            if i < len(items):
                item = items[i]
                if isinstance(item, EquipItem):
                    bc = item.quality_color
                    pygame.draw.rect(surface, bc, r,
                                     1 if item.quality == QUALITY_NORMAL else 2)
                    # Draw icon
                    icon_rect = r.inflate(-14, -14)
                    if item.slot == "weapon":
                        item._draw_weapon_icon(surface, icon_rect, bc)
                    else:
                        item._draw_armor_icon(surface, icon_rect, bc)

                    # Quality badge (top-right)
                    badge_chars = {1: "M", 2: "R", 3: "U"}
                    bc_char = badge_chars.get(item.quality, "")
                    if bc_char:
                        bs = self._font_xs.render(bc_char, True, item.quality_color)
                        surface.blit(bs, (r.right - bs.get_width() - 2, r.top + 2))

                    # ── Comparison badge (bottom-right) ───────────────────────
                    verdict, vcol = self._quick_verdict(item, player)
                    if verdict:
                        vs = self._font_xs.render(verdict, True, vcol)
                        vbg = pygame.Surface((vs.get_width() + 4, vs.get_height() + 2),
                                             pygame.SRCALPHA)
                        vbg.fill((0, 0, 0, 160))
                        surface.blit(vbg, (r.right - vs.get_width() - 6,
                                           r.bottom - vs.get_height() - 3))
                        surface.blit(vs,  (r.right - vs.get_width() - 4,
                                           r.bottom - vs.get_height() - 2))

                elif isinstance(item, HealthPotion):
                    pygame.draw.rect(surface, _POTION_COL, r, 1)
                    lbl = self._font_sm.render("HP", True, _POTION_COL)
                    surface.blit(lbl, lbl.get_rect(center=r.center))
            else:
                pygame.draw.rect(surface, _COL_SEP, r, 1)

        # Potions count
        pot_y = _PY + 52 + _BAG_ROWS * (_BAG_CELL + _BAG_GAP) + 6
        pc    = len(player.potions)
        pt    = self._font_sm.render(t("inv.potions", n=pc), True,
                                     _POTION_COL if pc else GRAY)
        surface.blit(pt, (bx, pot_y))

        # Character stats summary
        sy = pot_y + pt.get_height() + 6
        stats = [
            (f"ATK  {player.attack}",  (252, 160, 100)),
            (f"DEF  {player.defense}", (100, 160, 252)),
            (f"HP   {int(player.hp)}/{player.max_hp_total}", RED),
            (f"LV   {player.level}",   YELLOW),
        ]
        if player.crit_chance > 0:
            stats.append((f"CRIT  {int(player.crit_chance)}%", (220, 220, 80)))
        if player.life_steal > 0:
            stats.append((f"LIFE STEAL  {int(player.life_steal)}%", (220, 80, 80)))
        if player.hp_regen_rate > 0:
            stats.append((f"REGEN  {player.hp_regen_rate:.1f}/s", GREEN))
        if player.gold_find_bonus > 0:
            stats.append((f"GF  +{int(player.gold_find_bonus)}%", YELLOW))

        cols_per_row = 2
        cell_w = (_PW - _LEFT_W - _PAD * 3) // cols_per_row
        lh = self._font_xs.get_height() + 3
        for j, (txt, col) in enumerate(stats):
            sx  = bx + (j % cols_per_row) * cell_w
            sy2 = sy  + (j // cols_per_row) * lh
            surface.blit(self._font_xs.render(txt, True, col), (sx, sy2))

    # ── Comparison helpers ────────────────────────────────────────────────────

    def _equipped_for(self, item: EquipItem, player) -> EquipItem | None:
        """Return the currently equipped item in the same slot, or None."""
        eq = player.equipment.get(item.slot)
        if eq is None and item.slot == "ring":
            eq = player.equipment.get("ring2")
        return eq if (eq is not None and eq is not item) else None

    def _quick_verdict(self, item: EquipItem, player) -> tuple[str, tuple]:
        """▲ / ▼ / ≈ badge for backpack grid cell, or ('', black) if no comparison."""
        eq = self._equipped_for(item, player)
        if eq is None:
            return "", (0, 0, 0)
        delta = item.primary_stat - eq.primary_stat
        if delta > 3:
            return "▲", _CMP_BETTER
        if delta < -3:
            return "▼", _CMP_WORSE
        return "≈", _CMP_NEUTRAL

    def _build_comparison(self, item: EquipItem,
                           equipped: EquipItem) -> list[tuple]:
        """
        Per-stat comparison lines.
        Returns list of (stat_text, text_color, delta_text, delta_color).
        """
        mods   = _cmp_mods()
        result = []

        # Always include base_stat in ATK (weapon) or DEF (armor)
        from src.items.item import MOD_ATK, MOD_DEF
        for mod_kind, label in mods:
            v1 = item.get_mod_total(mod_kind)
            v2 = equipped.get_mod_total(mod_kind)
            # Add base contribution to the primary stat
            if mod_kind == MOD_ATK and item.slot == "weapon":
                v1 += item.base_stat
                v2 += equipped.base_stat
            elif (mod_kind == MOD_DEF
                  and item.slot not in ("weapon", "ring", "amulet")):
                v1 += item.base_stat
                v2 += equipped.base_stat

            if v1 == 0 and v2 == 0:
                continue

            stat_txt = f"+{v1:.0f} {label}" if v1 > 0 else f"  — {label}"
            stat_col = _STAT_COL if v1 > 0 else _CMP_NEUTRAL

            if v2 == 0 and v1 > 0:
                delta_txt = "  ✦ new"
                delta_col = _CMP_NEW
            elif abs(v1 - v2) < 1:
                delta_txt = "  ≈"
                delta_col = _CMP_NEUTRAL
            elif v1 > v2:
                delta_txt = f"  ▲ +{v1 - v2:.0f}"
                delta_col = _CMP_BETTER
            else:
                delta_txt = f"  ▼ {v1 - v2:.0f}"
                delta_col = _CMP_WORSE

            result.append((stat_txt, stat_col, delta_txt, delta_col))

        return result

    # ── Tooltip ───────────────────────────────────────────────────────────────

    def _draw_tooltip(self, surface: pygame.Surface, player):
        # Find hovered item
        item = None
        if self._hov_equip_key is not None:
            item = player.equipment.get(self._hov_equip_key)
        elif self._hov_bag_idx >= 0:
            bag = self._bag_items(player)
            if self._hov_bag_idx < len(bag):
                item = bag[self._hov_bag_idx]
        if not isinstance(item, EquipItem):
            return

        equipped = self._equipped_for(item, player)
        LH  = self._font_sm.get_height() + 3   # line height derived from font
        XLH = self._font_xs.get_height() + 2
        PAD = 8

        # ── Build content ─────────────────────────────────────────────────────
        sections: list[tuple] = []  # (kind, *args)

        # Header
        sections.append(("header", item.display_name, item.quality_color))
        sections.append(("sub",
                         f"{get_slot_label(item.slot).title()}  ·  {item.base_name}",
                         GRAY))
        sections.append(("sep",))

        # Stats with comparison
        if equipped is not None:
            cmp_lines = self._build_comparison(item, equipped)
            for stat_txt, stat_col, delta_txt, delta_col in cmp_lines:
                sections.append(("cmp", stat_txt, stat_col, delta_txt, delta_col))
        else:
            for txt, col in item.stat_lines():
                sections.append(("line", txt, col))

        # Enchantments
        enc_slots = getattr(item, "enchant_slots", 0)
        encs      = getattr(item, "enchantments",  [])
        if enc_slots > 0 or encs:
            sections.append(("sep",))
            sections.append(("line",
                              f"Slots: {'◆' * len(encs)}{'◇' * (enc_slots - len(encs))}",
                              (160, 80, 255)))
            for eid in encs:
                try:
                    from src.items.enchant import ENCHANTMENTS
                    enc = ENCHANTMENTS.get(eid)
                    if enc:
                        sections.append(("line", f"  {enc.name}", (180, 100, 255)))
                except Exception:
                    pass

        # Flavor
        fl = getattr(item, "flavor", "")
        if fl:
            sections.append(("sep",))
            sections.append(("line", f'"{fl}"', _FLAVOR_COL))

        # Comparison verdict
        if equipped is not None:
            sections.append(("sep",))
            delta  = item.primary_stat - equipped.primary_stat
            if delta > 3:
                verdict, vcol = f"▲  UPGRADE  vs {equipped.display_name}", _CMP_BETTER
            elif delta < -3:
                verdict, vcol = f"▼  DOWNGRADE  vs {equipped.display_name}", _CMP_WORSE
            else:
                verdict, vcol = f"≈  SIMILAR  vs {equipped.display_name}", _CMP_NEUTRAL
            sections.append(("verdict", verdict, vcol))

        # ── Measure tooltip ───────────────────────────────────────────────────
        def _line_w(txt: str, big: bool = False) -> int:
            f = self._font_md if big else self._font_sm
            return f.size(txt)[0]

        max_w = 320
        for sec in sections:
            if sec[0] == "header":
                max_w = max(max_w, _line_w(sec[1], big=True))
            elif sec[0] == "cmp":
                max_w = max(max_w,
                            _line_w(sec[1]) + self._font_xs.size(sec[3])[0] + 20)
            elif sec[0] in ("line", "sub", "verdict"):
                max_w = max(max_w, _line_w(sec[1]))
        tw = max_w + PAD * 2

        # Height
        th = PAD
        for sec in sections:
            if sec[0] == "sep":
                th += 6
            elif sec[0] == "header":
                th += self._font_md.get_height() + 4
            else:
                th += LH
        th += PAD

        # Position (near mouse, clamped to screen)
        mx, my = pygame.mouse.get_pos()
        tx = min(mx + 16, SCREEN_WIDTH  - tw - 4)
        ty = min(my - 10, SCREEN_HEIGHT - th - 4)
        ty = max(ty, 4)

        # ── Draw background ───────────────────────────────────────────────────
        bg = pygame.Surface((tw, th), pygame.SRCALPHA)
        bg.fill((6, 3, 1, 240))
        surface.blit(bg, (tx, ty))
        pygame.draw.rect(surface, item.quality_color, (tx, ty, tw, th), 1)

        # ── Draw content ──────────────────────────────────────────────────────
        y = ty + PAD
        for sec in sections:
            kind = sec[0]

            if kind == "sep":
                sep_y = y + 3
                pygame.draw.line(surface, _COL_SEP,
                                 (tx + PAD, sep_y), (tx + tw - PAD, sep_y))
                y += 6
                continue

            if kind == "header":
                s = self._font_md.render(sec[1], True, sec[2])
                surface.blit(s, (tx + PAD, y))
                y += s.get_height() + 4
                continue

            if kind == "sub":
                s = self._font_xs.render(sec[1], True, sec[2])
                surface.blit(s, (tx + PAD, y))
                y += LH
                continue

            if kind == "cmp":
                # stat label (left) + delta (right, different colour)
                stat_s  = self._font_sm.render(sec[1], True, sec[2])
                delta_s = self._font_xs.render(sec[3], True, sec[4])
                surface.blit(stat_s,  (tx + PAD, y))
                surface.blit(delta_s, (tx + tw - delta_s.get_width() - PAD,
                                       y + (stat_s.get_height() - delta_s.get_height()) // 2))
                y += LH
                continue

            if kind == "verdict":
                # Coloured verdict bar
                vbg = pygame.Surface((tw - 2, LH + 4), pygame.SRCALPHA)
                vbg.fill((*sec[2], 40))
                surface.blit(vbg, (tx + 1, y - 2))
                s = self._font_sm.render(sec[1], True, sec[2])
                surface.blit(s, (tx + PAD, y))
                y += LH
                continue

            if kind == "line":
                if sec[1]:
                    s = self._font_xs.render(sec[1], True, sec[2])
                    surface.blit(s, (tx + PAD, y))
                y += LH if sec[1] else LH // 2
