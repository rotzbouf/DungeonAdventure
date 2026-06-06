"""
Inventory screen.

Left panel   — Human silhouette with 10 equipment slots positioned
               on the corresponding body parts.
Right panel  — Backpack grid with quality borders + ▲/▼/≈ comparison badges.
Tooltip      — Per-stat delta vs. equipped item, colour-coded verdict.
"""
from __future__ import annotations

import pygame
from src.settings import (SCREEN_WIDTH, SCREEN_HEIGHT, HUD_HEIGHT,
                           GRAY, LIGHT_GRAY, YELLOW, RED, GREEN)
from src.items.item import (EquipItem, HealthPotion,
                             SLOT_ORDER, SLOT_LABELS, Q_COLOR, QUALITY_NORMAL)
from src.locale import t, get_slot_label
from src.ui.pager import draw_pager

# ── Panel geometry ─────────────────────────────────────────────────────────────
_PW = 1060
_PH = 720
_PX = (SCREEN_WIDTH  - _PW) // 2
_PY = (SCREEN_HEIGHT - HUD_HEIGHT - _PH) // 2

_LEFT_W  = 400          # character-silhouette column width
_RIGHT_X = _PX + _LEFT_W + 10
_PAD     = 10

_BAG_COLS    = 5     # columns per row
_BAG_ROWS    = 5     # visible rows at once
_BAG_CAP     = 50   # total backpack capacity (slots)
_BAG_CELL    = 70
_BAG_GAP     = 8

# ── Equipment slot dimensions & positions ─────────────────────────────────────
# All (cx, cy) are relative to the TOP-LEFT of the character panel content area
# (i.e. relative to _PX, _PY + hdr_h).
_SW = 90     # slot width
_SH = 52     # slot height

# Silhouette is centred at x=200 within the 400px left column.
_SIL_CX = 200

# (slot_key, short_label, cx, cy)
_EQUIP_LAYOUT = [
    ("helm",   "HELM",    _SIL_CX,  40),    # head
    ("amulet", "AMULET",  330,       95),    # neck right
    ("chest",  "CHEST",   _SIL_CX, 215),    # torso centre
    ("weapon", "WEAPON",   45,      195),    # left arm
    ("shield", "SHIELD",  355,      195),    # right arm
    ("belt",   "BELT",    _SIL_CX, 300),    # waist centre
    ("gloves", "GLOVES",   45,      290),    # left wrist
    ("ring",   "RING 1",   45,      370),    # left finger
    ("ring2",  "RING 2",  355,      370),    # right finger
    ("boots",  "BOOTS",   _SIL_CX, 430),    # feet centre
]

# ── Silhouette parameters (relative to panel top-left + hdr_h) ────────────────
# All expressed as offsets from (_PX, _PY + hdr_h)
_SIL_COLOR    = (38, 30, 20)
_SIL_OUTLINE  = (55, 44, 30)

# ── Palette ────────────────────────────────────────────────────────────────────
_COL_BG      = (12,  8,  4)
_COL_PANEL   = (22, 16, 10)
_COL_BORDER  = (68, 100, 176)
_COL_SLOT    = (30, 22, 14)
_COL_SLOT_H  = (50, 38, 24)
_COL_EQUIP   = (252, 188, 0)
_COL_SEP     = (45, 35, 22)

_POTION_COL  = (252, 80, 80)
_STAT_COL    = (100, 220, 100)
_FLAVOR_COL  = (140, 120, 80)
_NORMAL_COL  = Q_COLOR[QUALITY_NORMAL]

_CMP_BETTER  = ( 70, 220,  70)
_CMP_WORSE   = (220,  70,  70)
_CMP_NEUTRAL = (110, 110, 110)
_CMP_NEW     = ( 80, 200, 230)


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
        self._font_xs = pygame.font.SysFont("monospace", 13)

        self._msg   = ""
        self._msg_t = 0.0
        self._scroll = 0    # first visible row index

        self._hov_equip_key: str | None = None
        self._hov_bag_idx:   int        = -1
        self._pg_prev: pygame.Rect | None = None
        self._pg_next: pygame.Rect | None = None

    # ── Public API ────────────────────────────────────────────────────────────

    def handle_scroll(self, dy: int):
        total_rows  = _BAG_CAP // _BAG_COLS
        max_scroll  = max(0, total_rows - _BAG_ROWS)
        self._scroll = max(0, min(self._scroll - dy, max_scroll))

    def notify(self, text: str):
        self._msg   = text
        self._msg_t = 2.5

    def update(self, dt: float):
        self._msg_t = max(0.0, self._msg_t - dt)
        mx, my = pygame.mouse.get_pos()
        self._hov_equip_key = self._equip_key_at(mx, my)
        self._hov_bag_idx   = self._bag_idx_at(mx, my)

    def handle_click(self, mx: int, my: int, player) -> bool:
        if self._pg_prev and self._pg_prev.collidepoint(mx, my):
            self._scroll = max(0, self._scroll - _BAG_ROWS)
            return True
        if self._pg_next and self._pg_next.collidepoint(mx, my):
            max_scroll = max(0, _BAG_CAP // _BAG_COLS - _BAG_ROWS)
            self._scroll = min(max_scroll, self._scroll + _BAG_ROWS)
            return True
        key = self._equip_key_at(mx, my)
        if key is not None and player.equipment.get(key) is not None:
            old = player.equipment[key]
            if not player.unequip(key):
                self.notify(t("inv.full"))
                return True
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

    # ── Slot geometry helpers ─────────────────────────────────────────────────

    def _slot_rect(self, key: str, hdr_h: int) -> pygame.Rect | None:
        for sk, _lbl, cx, cy in _EQUIP_LAYOUT:
            if sk == key:
                return pygame.Rect(
                    _PX + cx - _SW // 2,
                    _PY + hdr_h + cy - _SH // 2,
                    _SW, _SH,
                )
        return None

    def _equip_key_at(self, mx: int, my: int) -> str | None:
        hdr_h = 34
        for sk, _lbl, cx, cy in _EQUIP_LAYOUT:
            r = pygame.Rect(
                _PX + cx - _SW // 2,
                _PY + hdr_h + cy - _SH // 2,
                _SW, _SH,
            )
            if r.collidepoint(mx, my):
                return sk
        return None

    # ── Main draw ─────────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface, player):
        ov = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 210))
        surface.blit(ov, (0, 0))

        panel = pygame.Rect(_PX, _PY, _PW, _PH)
        pygame.draw.rect(surface, _COL_BG, panel)
        pygame.draw.rect(surface, _COL_BORDER, panel, 2)

        hdr_h = 34
        pygame.draw.rect(surface, _COL_PANEL, (_PX, _PY, _PW, hdr_h))
        pygame.draw.line(surface, _COL_BORDER,
                         (_PX, _PY + hdr_h), (_PX + _PW, _PY + hdr_h))
        title_s = self._font_lg.render(t("inv.title"), True, YELLOW)
        surface.blit(title_s, (_PX + _PAD, _PY + (hdr_h - title_s.get_height()) // 2))
        hint = self._font_xs.render(t("inv.hint"), True, GRAY)
        surface.blit(hint, (_PX + _PW - hint.get_width() - _PAD,
                             _PY + (hdr_h - hint.get_height()) // 2))

        pygame.draw.line(surface, _COL_SEP,
                         (_PX + _LEFT_W, _PY + hdr_h + 2),
                         (_PX + _LEFT_W, _PY + _PH - 4))

        self._draw_character_panel(surface, player, hdr_h)
        self._draw_backpack(surface, player, hdr_h)

        if self._msg_t > 0:
            alpha = min(255, int(self._msg_t * 180))
            msg = self._font_sm.render(self._msg, True, YELLOW)
            msg.set_alpha(alpha)
            surface.blit(msg, (_PX + _PAD, _PY + _PH - msg.get_height() - 6))

        self._draw_tooltip(surface, player)

    # ── Character silhouette panel ────────────────────────────────────────────

    def _draw_silhouette(self, surface: pygame.Surface, ox: int, oy: int):
        """
        Draw a simple human silhouette centred at (ox + _SIL_CX, oy + ...).
        ox = _PX, oy = _PY + hdr_h.
        """
        cx  = ox + _SIL_CX
        sc  = _SIL_COLOR
        so  = _SIL_OUTLINE

        def rr(x, y, w, h, outline=True):
            pygame.draw.rect(surface, sc, (cx + x, oy + y, w, h))
            if outline:
                pygame.draw.rect(surface, so, (cx + x, oy + y, w, h), 1)

        # Head
        pygame.draw.circle(surface, sc,  (cx, oy + 92), 26)
        pygame.draw.circle(surface, so,  (cx, oy + 92), 26, 1)
        # Neck
        rr(-7, 117, 14, 22)
        # Shoulders
        rr(-52, 138, 104, 14)
        # Torso
        rr(-34, 138, 68, 105)
        # Upper arms
        rr(-60, 150, 20, 75)    # left
        rr( 40, 150, 20, 75)    # right
        # Forearms
        rr(-62, 225, 20, 60)    # left
        rr( 42, 225, 20, 60)    # right
        # Belt / hips
        rr(-30, 243, 60, 16)
        rr(-38, 259, 76, 20)
        # Thighs
        rr(-36, 279, 30, 80)    # left
        rr(  6, 279, 30, 80)    # right
        # Calves
        rr(-36, 359, 28, 65)    # left
        rr(  8, 359, 28, 65)    # right
        # Feet
        rr(-44, 424, 40, 14)    # left
        rr(  4, 424, 40, 14)    # right

    def _draw_character_panel(self, surface: pygame.Surface,
                               player, hdr_h: int):
        ox = _PX
        oy = _PY + hdr_h

        self._draw_silhouette(surface, ox, oy)

        # Draw slots
        for sk, lbl, cx, cy in _EQUIP_LAYOUT:
            r    = pygame.Rect(ox + cx - _SW // 2, oy + cy - _SH // 2, _SW, _SH)
            item = player.equipment.get(sk)
            hov  = (sk == self._hov_equip_key)

            # Background
            bg = _COL_SLOT_H if hov else _COL_SLOT
            pygame.draw.rect(surface, bg, r)

            # Border: gold if equipped, dim if empty
            border_col = _COL_EQUIP if item else _COL_SEP
            pygame.draw.rect(surface, border_col, r, 2 if item else 1)

            # Slot label (very small, top edge)
            lbl_s = self._font_xs.render(lbl, True,
                                          (130, 100, 60) if item else (55, 44, 30))
            surface.blit(lbl_s, (r.left + 3, r.top + 2))

            if item is not None:
                # Tiny item sprite left-side icon
                try:
                    from src.assets import assets as _a
                    _isz = _SH - 10
                    _spr = _a.item_sprite(item.base_name, size=(_isz, _isz))
                    if _spr:
                        surface.blit(_spr, (r.left + 2, r.centery - _isz // 2))
                except Exception:
                    pass

                # Item name (right of icon, quality colour, truncated)
                name_col = item.quality_color
                name_txt = item.display_name
                max_w    = _SW - _SH - 2
                n = self._font_xs.render(name_txt, True, name_col)
                while n.get_width() > max_w and len(name_txt) > 3:
                    name_txt = name_txt[:-1]
                    n = self._font_xs.render(name_txt + "…", True, name_col)
                ny = r.top + self._font_xs.get_height() + 4
                surface.blit(n, (r.left + _SH, ny))

                # Primary stat (bottom row)
                ps = item.primary_stat
                if ps > 0:
                    is_wpn  = item.slot == "weapon"
                    ps_lbl  = f"+{ps} {'ATK' if is_wpn else 'DEF'}"
                    ps_col  = (252, 160, 100) if is_wpn else (100, 160, 252)
                    ps_s    = self._font_xs.render(ps_lbl, True, ps_col)
                    surface.blit(ps_s, (r.left + 3,
                                        r.bottom - ps_s.get_height() - 2))
            else:
                # Empty slot hint
                eh = self._font_xs.render("empty", True, (45, 36, 24))
                surface.blit(eh, eh.get_rect(center=r.center))

        # Player stats at the very bottom of the left panel
        stats_y = oy + 490
        stats = [
            (f"ATK  {player.attack}",  (252, 160, 100)),
            (f"DEF  {player.defense}", (100, 160, 252)),
            (f"LV   {player.level}",   YELLOW),
            (f"HP   {int(player.hp)}/{player.max_hp_total}", RED),
        ]
        if player.crit_chance > 0:
            stats.append((f"CRIT {int(player.crit_chance)}%", (220, 220, 80)))
        lh = self._font_xs.get_height() + 3
        col_w = _LEFT_W // 2 - _PAD
        for j, (txt, col) in enumerate(stats):
            sx = ox + _PAD + (j % 2) * col_w
            sy = stats_y + (j // 2) * lh
            surface.blit(self._font_xs.render(txt, True, col), (sx, sy))

    # ── Backpack ──────────────────────────────────────────────────────────────

    def _grid_top(self) -> int:
        return _PY + 52

    def _grid_height(self) -> int:
        return _BAG_ROWS * (_BAG_CELL + _BAG_GAP)

    def _bag_cell_rect(self, idx: int) -> pygame.Rect:
        col = idx % _BAG_COLS
        row = idx // _BAG_COLS
        x   = _RIGHT_X + _PAD + col * (_BAG_CELL + _BAG_GAP)
        y   = self._grid_top() + (row - self._scroll) * (_BAG_CELL + _BAG_GAP)
        return pygame.Rect(x, y, _BAG_CELL, _BAG_CELL)

    def _bag_idx_at(self, mx: int, my: int) -> int:
        gt = self._grid_top()
        gb = gt + self._grid_height()
        if not (gt <= my < gb):
            return -1
        for i in range(_BAG_CAP):
            r = self._bag_cell_rect(i)
            if r.collidepoint(mx, my):
                return i
        return -1

    def _bag_items(self, player) -> list:
        return player.backpack + player.potions

    def _draw_backpack(self, surface: pygame.Surface, player, hdr_h: int):
        bx    = _RIGHT_X + _PAD
        items = self._bag_items(player)
        used  = len(items)

        # ── Header: "Backpack  12 / 50" ──────────────────────────────────────
        hdr_txt = t("inv.backpack")
        hdr = self._font_md.render(hdr_txt, True, LIGHT_GRAY)
        surface.blit(hdr, (bx, _PY + hdr_h + 6))
        cap_col = (220, 80, 80) if used >= _BAG_CAP else (120, 120, 120)
        cap_s   = self._font_xs.render(f"{used} / {_BAG_CAP}", True, cap_col)
        surface.blit(cap_s, (bx + hdr.get_width() + 8,
                              _PY + hdr_h + 6 + (hdr.get_height() - cap_s.get_height()) // 2))

        # ── Grid (clipped to visible rows) ────────────────────────────────────
        gt = self._grid_top()
        gh = self._grid_height()
        old_clip = surface.get_clip()
        surface.set_clip(pygame.Rect(_RIGHT_X, gt, _PW - _LEFT_W - 10, gh))

        for i in range(_BAG_CAP):
            r = self._bag_cell_rect(i)
            if r.bottom <= gt or r.top >= gt + gh:
                continue
            hov = (i == self._hov_bag_idx)
            pygame.draw.rect(surface, _COL_SLOT_H if hov else _COL_SLOT, r)

            if i < len(items):
                item = items[i]
                if isinstance(item, EquipItem):
                    bc = item.quality_color
                    pygame.draw.rect(surface, bc, r,
                                     1 if item.quality == QUALITY_NORMAL else 2)
                    icon_rect = r.inflate(-14, -14)
                    try:
                        from src.assets import assets
                        spr = assets.item_sprite(item.base_name,
                                                  size=(icon_rect.width,
                                                        icon_rect.height))
                        if spr:
                            surface.blit(spr, icon_rect.topleft)
                        elif item.slot == "weapon":
                            item._draw_weapon_icon(surface, icon_rect, bc)
                        else:
                            item._draw_armor_icon(surface, icon_rect, bc)
                    except Exception:
                        if item.slot == "weapon":
                            item._draw_weapon_icon(surface, icon_rect, bc)
                        else:
                            item._draw_armor_icon(surface, icon_rect, bc)

                    badge_chars = {1: "M", 2: "R", 3: "U"}
                    bc_char = badge_chars.get(item.quality, "")
                    if bc_char:
                        bs = self._font_xs.render(bc_char, True, item.quality_color)
                        surface.blit(bs, (r.right - bs.get_width() - 2, r.top + 2))

                    verdict, vcol = self._quick_verdict(item, player)
                    if verdict:
                        vs  = self._font_xs.render(verdict, True, vcol)
                        vbg = pygame.Surface((vs.get_width() + 4,
                                              vs.get_height() + 2), pygame.SRCALPHA)
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

        surface.set_clip(old_clip)

        # ── Page controls ─────────────────────────────────────────────────────
        total_rows  = _BAG_CAP // _BAG_COLS   # 10
        total_pages = (total_rows + _BAG_ROWS - 1) // _BAG_ROWS   # 2
        page        = self._scroll // _BAG_ROWS + 1
        cx = _RIGHT_X + _PAD + (_BAG_COLS * (_BAG_CELL + _BAG_GAP) - _BAG_GAP) // 2
        self._pg_prev, self._pg_next = draw_pager(
            surface, cx, gt + gh + 5, page, total_pages, self._font_xs)
        si_y = gt + gh + 5 + (26 if total_pages > 1 else 0)

        # ── Potion count + extra stats ────────────────────────────────────────
        pc = len(player.potions)
        pt = self._font_sm.render(t("inv.potions", n=pc), True,
                                   _POTION_COL if pc else GRAY)
        surface.blit(pt, (bx, si_y + 2))

        sy = si_y + pt.get_height() + 10
        extras = []
        if player.crit_chance > 0:
            extras.append((f"Crit  {int(player.crit_chance)}%", (220, 220, 80)))
        if player.life_steal > 0:
            extras.append((f"Life Steal  {int(player.life_steal)}%", (220, 80, 80)))
        if player.hp_regen_rate > 0:
            extras.append((f"Regen  {player.hp_regen_rate:.1f}/s", GREEN))
        if player.gold_find_bonus > 0:
            extras.append((f"Gold Find  +{int(player.gold_find_bonus)}%", YELLOW))
        lh = self._font_xs.get_height() + 3
        for txt, col in extras:
            surface.blit(self._font_xs.render(txt, True, col), (bx, sy))
            sy += lh

    # ── Comparison helpers ────────────────────────────────────────────────────

    def _equipped_for(self, item: EquipItem, player) -> EquipItem | None:
        eq = player.equipment.get(item.slot)
        if eq is None and item.slot == "ring":
            eq = player.equipment.get("ring2")
        return eq if (eq is not None and eq is not item) else None

    def _quick_verdict(self, item: EquipItem, player) -> tuple[str, tuple]:
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
        mods   = _cmp_mods()
        result = []
        from src.items.item import MOD_ATK, MOD_DEF
        for mod_kind, label in mods:
            v1 = item.get_mod_total(mod_kind)
            v2 = equipped.get_mod_total(mod_kind)
            if mod_kind == MOD_ATK and item.slot == "weapon":
                v1 += item.base_stat; v2 += equipped.base_stat
            elif (mod_kind == MOD_DEF
                  and item.slot not in ("weapon", "ring", "amulet")):
                v1 += item.base_stat; v2 += equipped.base_stat
            if v1 == 0 and v2 == 0:
                continue
            stat_txt = f"+{v1:.0f} {label}" if v1 > 0 else f"  — {label}"
            stat_col = _STAT_COL if v1 > 0 else _CMP_NEUTRAL
            if v2 == 0 and v1 > 0:
                delta_txt, delta_col = "  ✦ new", _CMP_NEW
            elif abs(v1 - v2) < 1:
                delta_txt, delta_col = "  ≈",     _CMP_NEUTRAL
            elif v1 > v2:
                delta_txt, delta_col = f"  ▲ +{v1-v2:.0f}", _CMP_BETTER
            else:
                delta_txt, delta_col = f"  ▼ {v1-v2:.0f}",  _CMP_WORSE
            result.append((stat_txt, stat_col, delta_txt, delta_col))
        return result

    # ── Tooltip ───────────────────────────────────────────────────────────────

    def _draw_tooltip(self, surface: pygame.Surface, player):
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
        LH  = self._font_sm.get_height() + 3
        PAD = 8

        sections: list[tuple] = []
        sections.append(("header", item.display_name, item.quality_color))
        sections.append(("sub",
                         f"{get_slot_label(item.slot).title()}  ·  {item.base_name}",
                         GRAY))
        sections.append(("sep",))

        if equipped is not None:
            for stat_txt, stat_col, delta_txt, delta_col in \
                    self._build_comparison(item, equipped):
                sections.append(("cmp", stat_txt, stat_col, delta_txt, delta_col))
        else:
            for txt, col in item.stat_lines():
                sections.append(("line", txt, col))

        enc_slots = getattr(item, "enchant_slots", 0)
        encs      = getattr(item, "enchantments",  [])
        if enc_slots > 0 or encs:
            sections.append(("sep",))
            sections.append(("line",
                              f"Slots: {'◆'*len(encs)}{'◇'*(enc_slots-len(encs))}",
                              (160, 80, 255)))
            for eid in encs:
                try:
                    from src.items.enchant import ENCHANTMENTS
                    enc = ENCHANTMENTS.get(eid)
                    if enc:
                        sections.append(("line", f"  {enc.name}", (180, 100, 255)))
                except Exception:
                    pass

        fl = getattr(item, "flavor", "")
        if fl:
            sections.append(("sep",))
            sections.append(("line", f'"{fl}"', _FLAVOR_COL))

        if equipped is not None:
            sections.append(("sep",))
            delta = item.primary_stat - equipped.primary_stat
            if delta > 3:
                verdict, vcol = f"▲  UPGRADE  vs {equipped.display_name}", _CMP_BETTER
            elif delta < -3:
                verdict, vcol = f"▼  DOWNGRADE  vs {equipped.display_name}", _CMP_WORSE
            else:
                verdict, vcol = f"≈  SIMILAR  vs {equipped.display_name}", _CMP_NEUTRAL
            sections.append(("verdict", verdict, vcol))

        # Measure
        max_w = 280
        for sec in sections:
            if sec[0] == "header":
                max_w = max(max_w, self._font_md.size(sec[1])[0])
            elif sec[0] == "cmp":
                max_w = max(max_w,
                            self._font_sm.size(sec[1])[0] +
                            self._font_xs.size(sec[3])[0] + 20)
            elif sec[0] in ("line", "sub", "verdict"):
                max_w = max(max_w, self._font_sm.size(sec[1])[0])
        tw = max_w + PAD * 2

        th = PAD
        for sec in sections:
            if sec[0] == "sep":       th += 6
            elif sec[0] == "header":  th += self._font_md.get_height() + 4
            else:                     th += LH
        th += PAD

        mx, my = pygame.mouse.get_pos()
        tx = min(mx + 16, SCREEN_WIDTH  - tw - 4)
        ty = min(my - 10, SCREEN_HEIGHT - th - 4)
        ty = max(ty, 4)

        bg = pygame.Surface((tw, th), pygame.SRCALPHA)
        bg.fill((6, 3, 1, 240))
        surface.blit(bg, (tx, ty))
        pygame.draw.rect(surface, item.quality_color, (tx, ty, tw, th), 1)

        y = ty + PAD
        for sec in sections:
            kind = sec[0]
            if kind == "sep":
                pygame.draw.line(surface, _COL_SEP,
                                 (tx + PAD, y + 3), (tx + tw - PAD, y + 3))
                y += 6; continue
            if kind == "header":
                s = self._font_md.render(sec[1], True, sec[2])
                surface.blit(s, (tx + PAD, y))
                y += s.get_height() + 4; continue
            if kind == "sub":
                surface.blit(self._font_xs.render(sec[1], True, sec[2]),
                             (tx + PAD, y))
                y += LH; continue
            if kind == "cmp":
                stat_s  = self._font_sm.render(sec[1], True, sec[2])
                delta_s = self._font_xs.render(sec[3], True, sec[4])
                surface.blit(stat_s,  (tx + PAD, y))
                surface.blit(delta_s, (tx + tw - delta_s.get_width() - PAD,
                                       y + (stat_s.get_height() -
                                            delta_s.get_height()) // 2))
                y += LH; continue
            if kind == "verdict":
                vbg = pygame.Surface((tw - 2, LH + 4), pygame.SRCALPHA)
                vbg.fill((*sec[2], 40))
                surface.blit(vbg, (tx + 1, y - 2))
                surface.blit(self._font_sm.render(sec[1], True, sec[2]),
                             (tx + PAD, y))
                y += LH; continue
            if kind == "line":
                if sec[1]:
                    surface.blit(self._font_xs.render(sec[1], True, sec[2]),
                                 (tx + PAD, y))
                y += LH if sec[1] else LH // 2
