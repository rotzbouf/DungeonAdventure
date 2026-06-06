"""
Merchant Shop Screen.

Left column  — merchant's items for sale  (click to buy).
Right column — player's backpack + potions (click to sell).

Both columns display items as icon-grid cells matching the inventory style:
quality-bordered boxes with sprites, price overlays, and comparison badges.
"""
from __future__ import annotations

import pygame
from src.settings import (SCREEN_WIDTH, SCREEN_HEIGHT, HUD_HEIGHT,
                           WHITE, YELLOW, GRAY, LIGHT_GRAY)
from src.items.item import EquipItem, HealthPotion, QUALITY_NORMAL
from src.entities.merchant import item_sell_price
from src.locale import t
from src.ui.pager import draw_pager
from src.ui.inventory import (
    _cmp_mods, _COL_SEP, _STAT_COL, _FLAVOR_COL,
    _CMP_BETTER, _CMP_WORSE, _CMP_NEUTRAL, _CMP_NEW,
    _COL_SLOT, _COL_SLOT_H,
)

# ── Panel geometry ─────────────────────────────────────────────────────────────
_PW     = 920
_PH     = 640
_HDR_H  = 54
_COL_H  = 24    # column-header strip height

# ── Item grid geometry ─────────────────────────────────────────────────────────
_CELL   = 70    # cell width & height (matches inventory)
_GAP    = 6     # gap between cells
_COLS   = 5     # cells per row per column

# ── Palette ───────────────────────────────────────────────────────────────────
_BG     = (8,   4,  12)
_PANEL  = (18,  9,  30)
_HEADER = (36,  16,  60)
_BORDER = (80,  40, 120)
_CHDR   = (28,  12,  48)
_GOLD_C = (252, 188,   0)
_BUY_C  = ( 60, 220,  80)
_CANT_C = (180,  60,  60)
_SELL_C = (252, 188,   0)
_POT_C  = (252,  80,  80)


class ShopScreen:
    def __init__(self):
        self._fonts_init = False
        self._notify_msg = ""
        self._notify_t   = 0.0
        self._buy_scroll  = 0   # first visible row in buy column
        self._sell_scroll = 0   # first visible row in sell column
        self._buy_prev:  pygame.Rect | None = None
        self._buy_next:  pygame.Rect | None = None
        self._sell_prev: pygame.Rect | None = None
        self._sell_next: pygame.Rect | None = None

    # ── Init ──────────────────────────────────────────────────────────────────

    def _init_fonts(self):
        if self._fonts_init:
            return
        self._font_lg    = pygame.font.SysFont("monospace", 25, bold=True)
        self._font_md    = pygame.font.SysFont("monospace", 20, bold=True)
        self._font_sm    = pygame.font.SysFont("monospace", 18)
        self._font_xs    = pygame.font.SysFont("monospace", 13)
        self._font_tt    = pygame.font.SysFont("monospace", 20, bold=True)
        self._font_tt_sm = pygame.font.SysFont("monospace", 16, bold=True)
        self._fonts_init = True

    def notify(self, msg: str, duration: float = 2.5):
        self._notify_msg = msg
        self._notify_t   = duration

    def update(self, dt: float):
        self._notify_t = max(0.0, self._notify_t - dt)

    def handle_scroll(self, dy: int, mx: int, my: int):
        panel    = self._panel()
        mid_x    = panel.x + _PW // 2
        buy_rows  = _max_visible_rows(panel)
        sell_rows = buy_rows
        if mx < mid_x:
            self._buy_scroll  = max(0, self._buy_scroll  - dy)
        else:
            self._sell_scroll = max(0, self._sell_scroll - dy)

    # ── Geometry ──────────────────────────────────────────────────────────────

    def _panel(self) -> pygame.Rect:
        x = (SCREEN_WIDTH  - _PW) // 2
        y = (SCREEN_HEIGHT - HUD_HEIGHT - _PH) // 2
        return pygame.Rect(x, y, _PW, _PH)

    def _grid_origin(self, col_rect: pygame.Rect) -> tuple[int, int]:
        """Top-left pixel where the grid starts inside col_rect."""
        pad_x = (col_rect.w - (_COLS * _CELL + (_COLS - 1) * _GAP)) // 2
        return col_rect.x + pad_x, col_rect.y + _COL_H + 6

    def _cell_rect(self, col_rect: pygame.Rect, idx: int,
                   scroll: int = 0) -> pygame.Rect:
        col = idx % _COLS
        row = idx // _COLS - scroll
        gx, gy = self._grid_origin(col_rect)
        return pygame.Rect(
            gx + col * (_CELL + _GAP),
            gy + row * (_CELL + _GAP),
            _CELL, _CELL,
        )

    def _cell_idx_at(self, col_rect: pygame.Rect, mx: int, my: int,
                     n_items: int, scroll: int) -> int:
        panel   = self._panel()
        clip_y0 = col_rect.y + _COL_H + 6
        clip_y1 = panel.bottom - 28
        if not (clip_y0 <= my < clip_y1):
            return -1
        for i in range(n_items):
            r = self._cell_rect(col_rect, i, scroll)
            if r.collidepoint(mx, my):
                return i
        return -1

    # ── Draw ──────────────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface, merchant, player):
        self._init_fonts()
        panel  = self._panel()
        mid_x  = panel.x + _PW // 2
        mx, my = pygame.mouse.get_pos()

        # Overlay
        ov = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT - HUD_HEIGHT), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 155))
        surface.blit(ov, (0, 0))

        # Panel
        pygame.draw.rect(surface, _PANEL, panel)
        pygame.draw.rect(surface, _BORDER, panel, 2)

        # Header bar
        hdr_r = pygame.Rect(panel.x, panel.y, panel.w, _HDR_H)
        pygame.draw.rect(surface, _HEADER, hdr_r)
        pygame.draw.line(surface, _BORDER,
                         (panel.x, panel.y + _HDR_H),
                         (panel.right, panel.y + _HDR_H), 1)
        title = self._font_lg.render(f"☆  {merchant.get_title()}  ☆", True, (180, 110, 255))
        surface.blit(title, title.get_rect(centerx=panel.centerx, centery=panel.y + 18))
        gold_s = self._font_md.render(t("shop.gold", n=player.gold), True, _GOLD_C)
        surface.blit(gold_s, gold_s.get_rect(right=panel.right - 12, centery=panel.y + 18))
        hint_s = self._font_xs.render(t("shop.hint"), True, GRAY)
        surface.blit(hint_s, hint_s.get_rect(centerx=panel.centerx, centery=panel.y + 40))

        # Column divider
        pygame.draw.line(surface, _BORDER,
                         (mid_x, panel.y + _HDR_H), (mid_x, panel.bottom), 1)

        # Column rects (below header bar)
        buy_col  = pygame.Rect(panel.x,   panel.y + _HDR_H, _PW // 2, _PH - _HDR_H)
        sell_col = pygame.Rect(mid_x,     panel.y + _HDR_H, _PW - _PW // 2, _PH - _HDR_H)

        # Column headers
        for col_r, label in [(buy_col, t("shop.for_sale")),
                              (sell_col, t("shop.sell_items"))]:
            ch_r = pygame.Rect(col_r.x, col_r.y, col_r.w, _COL_H)
            pygame.draw.rect(surface, _CHDR, ch_r)
            pygame.draw.line(surface, _BORDER,
                             (col_r.x, col_r.y + _COL_H),
                             (col_r.right, col_r.y + _COL_H), 1)
            ht = self._font_md.render(label, True, LIGHT_GRAY)
            surface.blit(ht, ht.get_rect(centerx=col_r.centerx,
                                          centery=col_r.y + _COL_H // 2))

        # Reserve bottom strip for pager buttons
        clip_bottom  = panel.bottom - 28
        pager_btn_y  = panel.bottom - 24

        # ── Buy column (merchant stock) ───────────────────────────────────────
        tooltip_item  = None
        tooltip_is_buy = False

        vis_rows = _max_visible_rows(panel)
        max_buy_scroll = max(0, _ceil_div(len(merchant.stock), _COLS) - vis_rows)
        self._buy_scroll = min(self._buy_scroll, max_buy_scroll)

        old_clip = surface.get_clip()
        surface.set_clip(pygame.Rect(buy_col.x, buy_col.y + _COL_H,
                                     buy_col.w, buy_col.h - _COL_H))
        for idx, item in enumerate(merchant.stock):
            r = self._cell_rect(buy_col, idx, self._buy_scroll)
            if r.top >= clip_bottom:
                break
            hov = r.collidepoint(mx, my) and r.bottom <= clip_bottom
            if hov:
                tooltip_item  = item
                tooltip_is_buy = True
            price  = merchant.price_of(item)
            p_col  = _BUY_C if player.gold >= price else _CANT_C
            self._draw_cell(surface, r, item, f"{price}g", p_col, hov, player)
        surface.set_clip(old_clip)

        # ── Sell column (player backpack + potions) ───────────────────────────
        sellable = list(player.backpack) + list(player.potions)
        max_sell_scroll = max(0, _ceil_div(len(sellable), _COLS) - vis_rows)
        self._sell_scroll = min(self._sell_scroll, max_sell_scroll)

        surface.set_clip(pygame.Rect(sell_col.x, sell_col.y + _COL_H,
                                     sell_col.w, sell_col.h - _COL_H))
        for idx, item in enumerate(sellable):
            r = self._cell_rect(sell_col, idx, self._sell_scroll)
            if r.top >= clip_bottom:
                break
            hov = r.collidepoint(mx, my) and r.bottom <= clip_bottom
            if hov:
                tooltip_item   = item
                tooltip_is_buy = False
            val = item_sell_price(item)
            self._draw_cell(surface, r, item, f"{val}g", _SELL_C, hov, player)
        surface.set_clip(old_clip)

        # ── Pager buttons (below grid in each column) ─────────────────────────
        buy_rows  = _ceil_div(len(merchant.stock), _COLS)
        buy_pages = max(1, _ceil_div(buy_rows, vis_rows))
        buy_page  = self._buy_scroll // vis_rows + 1
        self._buy_prev, self._buy_next = draw_pager(
            surface, buy_col.centerx, pager_btn_y, buy_page, buy_pages, self._font_xs)

        sell_rows  = _ceil_div(len(sellable), _COLS)
        sell_pages = max(1, _ceil_div(sell_rows, vis_rows))
        sell_page  = self._sell_scroll // vis_rows + 1
        self._sell_prev, self._sell_next = draw_pager(
            surface, sell_col.centerx, pager_btn_y, sell_page, sell_pages, self._font_xs)

        # Notification
        if self._notify_t > 0:
            alpha = min(255, int(self._notify_t * 160))
            msg_s = self._font_md.render(self._notify_msg, True, YELLOW)
            msg_s.set_alpha(alpha)
            surface.blit(msg_s, msg_s.get_rect(centerx=panel.centerx,
                                                 y=panel.bottom - 20))

        # Tooltip
        if tooltip_item:
            self._draw_tooltip(surface, tooltip_item, player, (mx, my))

    def _draw_cell(self, surface: pygame.Surface, r: pygame.Rect,
                   item, price_txt: str, price_col: tuple,
                   hovered: bool, player):
        # Background
        pygame.draw.rect(surface, _COL_SLOT_H if hovered else _COL_SLOT, r)

        if isinstance(item, HealthPotion):
            pygame.draw.rect(surface, _POT_C, r, 2 if hovered else 1)
            lbl = self._font_sm.render("HP", True, _POT_C)
            surface.blit(lbl, lbl.get_rect(center=r.center))
        elif isinstance(item, EquipItem):
            # Quality border
            bc = item.quality_color
            pygame.draw.rect(surface, bc, r,
                             2 if item.quality != QUALITY_NORMAL else 1)

            # Sprite / fallback icon
            icon_r = r.inflate(-14, -14)
            try:
                from src.assets import assets
                spr = assets.item_sprite(item.base_name,
                                         size=(icon_r.width, icon_r.height))
                if spr:
                    surface.blit(spr, icon_r.topleft)
                elif item.slot == "weapon":
                    item._draw_weapon_icon(surface, icon_r, bc)
                else:
                    item._draw_armor_icon(surface, icon_r, bc)
            except Exception:
                if item.slot == "weapon":
                    item._draw_weapon_icon(surface, icon_r, bc)
                else:
                    item._draw_armor_icon(surface, icon_r, bc)

            # Quality badge (M / R / U) top-right
            badge = {1: "M", 2: "R", 3: "U"}.get(item.quality, "")
            if badge:
                bs = self._font_xs.render(badge, True, bc)
                surface.blit(bs, (r.right - bs.get_width() - 2, r.top + 2))

            # Comparison verdict bottom-left (▲/▼/≈ vs equipped)
            verdict, vcol = self._quick_verdict(item, player)
            if verdict:
                vs  = self._font_xs.render(verdict, True, vcol)
                vbg = pygame.Surface((vs.get_width() + 4,
                                      vs.get_height() + 2), pygame.SRCALPHA)
                vbg.fill((0, 0, 0, 160))
                surface.blit(vbg, (r.left + 1, r.bottom - vs.get_height() - 3))
                surface.blit(vs,  (r.left + 3, r.bottom - vs.get_height() - 2))
        else:
            pygame.draw.rect(surface, _BORDER, r, 1)

        # Price overlay — bottom-right
        ps = self._font_xs.render(price_txt, True, price_col)
        pbg = pygame.Surface((ps.get_width() + 4, ps.get_height() + 2), pygame.SRCALPHA)
        pbg.fill((0, 0, 0, 180))
        surface.blit(pbg, (r.right - ps.get_width() - 5, r.bottom - ps.get_height() - 2))
        surface.blit(ps,  (r.right - ps.get_width() - 3, r.bottom - ps.get_height() - 1))

    # ── Comparison helpers ────────────────────────────────────────────────────

    @staticmethod
    def _equipped_for(item: EquipItem, player) -> EquipItem | None:
        eq = player.equipment.get(item.slot)
        if eq is None and item.slot == "ring":
            eq = player.equipment.get("ring2")
        return eq if eq is not None else None

    def _quick_verdict(self, item: EquipItem, player) -> tuple[str, tuple]:
        if not isinstance(item, EquipItem):
            return "", (0, 0, 0)
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
        from src.items.item import MOD_ATK, MOD_DEF
        result = []
        for mod_kind, label in _cmp_mods():
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

    def _draw_tooltip(self, surface: pygame.Surface, item, player, pos: tuple):
        if not isinstance(item, EquipItem):
            return

        equipped = self._equipped_for(item, player)
        LH  = self._font_tt_sm.get_height() + 3
        PAD = 8

        sections: list[tuple] = []
        sections.append(("header", item.display_name, item.quality_color))
        sections.append(("sub", f"{item.slot.title()}  ·  {item.base_name}", GRAY))
        sections.append(("sep",))

        if equipped is not None:
            rows = self._build_comparison(item, equipped)
            if rows:
                for stat_txt, stat_col, delta_txt, delta_col in rows:
                    sections.append(("cmp", stat_txt, stat_col, delta_txt, delta_col))
            else:
                for txt, col in item.stat_lines():
                    sections.append(("line", txt, col))
        else:
            for txt, col in item.stat_lines():
                sections.append(("line", txt, col))

        encs      = getattr(item, "enchantments", [])
        enc_slots = getattr(item, "enchant_slots", 0)
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
        else:
            sections.append(("sep",))
            sections.append(("line", "(nothing equipped in this slot)", _CMP_NEUTRAL))

        # Measure
        max_w = 260
        for sec in sections:
            if sec[0] == "header":
                max_w = max(max_w, self._font_tt.size(sec[1])[0])
            elif sec[0] == "cmp":
                max_w = max(max_w,
                            self._font_tt_sm.size(sec[1])[0] +
                            self._font_xs.size(sec[3])[0] + 20)
            elif sec[0] in ("line", "sub", "verdict"):
                max_w = max(max_w, self._font_tt_sm.size(sec[1])[0])
        tw = max_w + PAD * 2

        th = PAD
        for sec in sections:
            if sec[0] == "sep":       th += 6
            elif sec[0] == "header":  th += self._font_tt.get_height() + 4
            else:                     th += LH
        th += PAD

        mx, my = pos
        tx = min(mx + 16, SCREEN_WIDTH  - tw - 4)
        ty = min(my - 10, SCREEN_HEIGHT - HUD_HEIGHT - th - 4)
        ty = max(ty, 4)

        bg = pygame.Surface((tw, th), pygame.SRCALPHA)
        bg.fill((6, 3, 14, 245))
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
                s = self._font_tt.render(sec[1], True, sec[2])
                surface.blit(s, (tx + PAD, y))
                y += s.get_height() + 4; continue
            if kind == "sub":
                surface.blit(self._font_xs.render(sec[1], True, sec[2]),
                             (tx + PAD, y))
                y += LH; continue
            if kind == "cmp":
                stat_s  = self._font_tt_sm.render(sec[1], True, sec[2])
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
                surface.blit(self._font_tt_sm.render(sec[1], True, sec[2]),
                             (tx + PAD, y))
                y += LH; continue
            if kind == "line":
                surface.blit(self._font_tt_sm.render(sec[1], True, sec[2]),
                             (tx + PAD, y))
                y += LH

    # ── Click handling ────────────────────────────────────────────────────────

    def handle_click(self, mx: int, my: int, button: int,
                     merchant, player) -> bool:
        panel    = self._panel()
        mid_x    = panel.x + _PW // 2
        buy_col  = pygame.Rect(panel.x, panel.y + _HDR_H, _PW // 2,     _PH - _HDR_H)
        sell_col = pygame.Rect(mid_x,   panel.y + _HDR_H, _PW - _PW // 2, _PH - _HDR_H)

        # ── Pager button clicks ────────────────────────────────────────────────
        if button == 1:
            vis  = _max_visible_rows(panel)
            if self._buy_prev and self._buy_prev.collidepoint(mx, my):
                self._buy_scroll = max(0, self._buy_scroll - vis)
                return True
            if self._buy_next and self._buy_next.collidepoint(mx, my):
                ms = max(0, _ceil_div(len(merchant.stock), _COLS) - vis)
                self._buy_scroll = min(ms, self._buy_scroll + vis)
                return True
            if self._sell_prev and self._sell_prev.collidepoint(mx, my):
                self._sell_scroll = max(0, self._sell_scroll - vis)
                return True
            if self._sell_next and self._sell_next.collidepoint(mx, my):
                sellable = list(player.backpack) + list(player.potions)
                ms = max(0, _ceil_div(len(sellable), _COLS) - vis)
                self._sell_scroll = min(ms, self._sell_scroll + vis)
                return True

        # Buy — left-click on merchant stock
        if button == 1 and mx < mid_x:
            idx = self._cell_idx_at(buy_col, mx, my,
                                    len(merchant.stock), self._buy_scroll)
            if idx >= 0:
                item  = merchant.stock[idx]
                price = merchant.price_of(item)
                if player.gold >= price:
                    player.gold -= price
                    merchant.stock.remove(item)
                    player.add_item(item)
                    self.notify(t("shop.bought", name=_label(item)[0]))
                else:
                    self.notify(t("shop.need_gold", n=price - player.gold))
                return True

        # Sell — left or right-click on player backpack
        if button in (1, 3) and mx >= mid_x:
            sellable = list(player.backpack) + list(player.potions)
            idx = self._cell_idx_at(sell_col, mx, my,
                                    len(sellable), self._sell_scroll)
            if idx >= 0:
                item = sellable[idx]
                val  = item_sell_price(item)
                player.gold += val
                if item in player.backpack:
                    player.backpack.remove(item)
                elif item in player.potions:
                    player.potions.remove(item)
                self.notify(t("shop.sold", name=_label(item)[0], n=val))
                return True

        return False


# ── Module helpers ─────────────────────────────────────────────────────────────

def _label(item) -> tuple[str, tuple]:
    if isinstance(item, HealthPotion):
        return t("shop.health_pot", n=item.heal_amount), (240, 100, 100)
    if isinstance(item, EquipItem):
        return item.display_name, item.quality_color
    return "Item", (200, 200, 200)


def _max_visible_rows(panel: pygame.Rect) -> int:
    grid_h = panel.h - _HDR_H - _COL_H - 6
    return max(1, grid_h // (_CELL + _GAP))


def _ceil_div(a: int, b: int) -> int:
    return (a + b - 1) // b
