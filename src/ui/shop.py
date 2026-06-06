"""
Merchant Shop Screen.

Left column  — merchant's items for sale  (click to buy).
Right column — player's backpack + potions (click to sell).
"""
from __future__ import annotations

import pygame
from src.settings import (SCREEN_WIDTH, SCREEN_HEIGHT, HUD_HEIGHT,
                           WHITE, YELLOW, GRAY, LIGHT_GRAY)
from src.items.item import EquipItem, HealthPotion
from src.entities.merchant import item_sell_price
from src.locale import t
from src.ui.inventory import (
    _cmp_mods, _COL_SEP, _STAT_COL, _FLAVOR_COL,
    _CMP_BETTER, _CMP_WORSE, _CMP_NEUTRAL, _CMP_NEW,
)

# ── Geometry ──────────────────────────────────────────────────────────────────
_PW      = 880
_PH      = 620
_HDR_H   = 54
_COL_HDR = 24    # column-header strip height
_ROW_H   = 46

# ── Palette ───────────────────────────────────────────────────────────────────
_BG     = (8,   4,  12)
_PANEL  = (18,  9,  30)
_HEADER = (36,  16,  60)
_BORDER = (80,  40, 120)
_CHDR   = (28,  12,  48)   # column header bg
_ROW_N  = (22,  11,  38)   # normal row bg
_ROW_H_COL = (38, 20,  60)  # hovered row bg
_GOLD_C = (252, 188,   0)
_BUY_C  = (60,  220,  80)   # buy price (can afford)
_CANT_C = (180,  60,  60)   # buy price (too expensive)
_SELL_C = (252, 188,   0)   # sell price


class ShopScreen:
    def __init__(self):
        self._fonts_init  = False
        self._notify_msg  = ""
        self._notify_t    = 0.0

    # ── Init ──────────────────────────────────────────────────────────────────

    def _init_fonts(self):
        if self._fonts_init:
            return
        self._font_lg    = pygame.font.SysFont("monospace", 25, bold=True)
        self._font_md    = pygame.font.SysFont("monospace", 24, bold=True)
        self._font_sm    = pygame.font.SysFont("monospace", 25)
        self._font_tt    = pygame.font.SysFont("monospace", 24, bold=True)  # tooltip header
        self._font_tt_sm = pygame.font.SysFont("monospace", 18, bold=True)  # tooltip stats
        self._font_xs    = pygame.font.SysFont("monospace", 13)             # tooltip deltas
        self._fonts_init = True

    def notify(self, msg: str, duration: float = 2.5):
        self._notify_msg = msg
        self._notify_t   = duration

    def update(self, dt: float):
        self._notify_t = max(0.0, self._notify_t - dt)

    # ── Geometry helpers ──────────────────────────────────────────────────────

    def _panel(self) -> pygame.Rect:
        x = (SCREEN_WIDTH  - _PW) // 2
        y = (SCREEN_HEIGHT - HUD_HEIGHT - _PH) // 2
        return pygame.Rect(x, y, _PW, _PH)

    def _buy_col(self, panel: pygame.Rect) -> pygame.Rect:
        return pygame.Rect(panel.x, panel.y + _HDR_H,
                           _PW // 2, _PH - _HDR_H)

    def _sell_col(self, panel: pygame.Rect) -> pygame.Rect:
        return pygame.Rect(panel.x + _PW // 2, panel.y + _HDR_H,
                           _PW - _PW // 2, _PH - _HDR_H)

    def _buy_row(self, idx: int, buy_col: pygame.Rect) -> pygame.Rect:
        y = buy_col.y + _COL_HDR + idx * _ROW_H
        return pygame.Rect(buy_col.x + 4, y, buy_col.w - 8, _ROW_H - 3)

    def _sell_row(self, idx: int, sell_col: pygame.Rect) -> pygame.Rect:
        y = sell_col.y + _COL_HDR + idx * _ROW_H
        return pygame.Rect(sell_col.x + 4, y, sell_col.w - 8, _ROW_H - 3)

    # ── Item display helpers ──────────────────────────────────────────────────

    @staticmethod
    def _label(item) -> tuple[str, tuple]:
        if isinstance(item, HealthPotion):
            return t("shop.health_pot", n=item.heal_amount), (240, 100, 100)
        if isinstance(item, EquipItem):
            return item.display_name, item.quality_color
        return "Item", WHITE

    # ── Draw ──────────────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface, merchant, player):
        self._init_fonts()
        panel    = self._panel()
        buy_col  = self._buy_col(panel)
        sell_col = self._sell_col(panel)
        mx, my   = pygame.mouse.get_pos()

        # ── Overlay ───────────────────────────────────────────────────────────
        overlay = pygame.Surface(
            (SCREEN_WIDTH, SCREEN_HEIGHT - HUD_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 155))
        surface.blit(overlay, (0, 0))

        # ── Panel background ──────────────────────────────────────────────────
        pygame.draw.rect(surface, _PANEL, panel)
        pygame.draw.rect(surface, _BORDER, panel, 2)

        # ── Header bar ────────────────────────────────────────────────────────
        hdr_r = pygame.Rect(panel.x, panel.y, panel.w, _HDR_H)
        pygame.draw.rect(surface, _HEADER, hdr_r)
        pygame.draw.line(surface, _BORDER,
                         (panel.x, panel.y + _HDR_H),
                         (panel.right, panel.y + _HDR_H), 1)

        title = self._font_lg.render(f"☆  {merchant.get_title()}  ☆", True, (180, 110, 255))
        surface.blit(title, title.get_rect(
            centerx=panel.centerx, centery=panel.y + 18))

        gold_s = self._font_md.render(t("shop.gold", n=player.gold), True, _GOLD_C)
        surface.blit(gold_s, gold_s.get_rect(
            right=panel.right - 12, centery=panel.y + 18))

        hint_s = self._font_sm.render(t("shop.hint"), True, GRAY)
        surface.blit(hint_s, hint_s.get_rect(
            centerx=panel.centerx, centery=panel.y + 40))

        # ── Column divider ────────────────────────────────────────────────────
        mid_x = panel.x + _PW // 2
        pygame.draw.line(surface, _BORDER,
                         (mid_x, panel.y + _HDR_H),
                         (mid_x, panel.bottom), 1)

        # ── Column headers ────────────────────────────────────────────────────
        for col_r, label in [(buy_col, t("shop.for_sale")), (sell_col, t("shop.sell_items"))]:
            ch_r = pygame.Rect(col_r.x, col_r.y, col_r.w, _COL_HDR)
            pygame.draw.rect(surface, _CHDR, ch_r)
            pygame.draw.line(surface, _BORDER,
                             (col_r.x, col_r.y + _COL_HDR),
                             (col_r.right, col_r.y + _COL_HDR), 1)
            hdr_txt = self._font_md.render(label, True, LIGHT_GRAY)
            surface.blit(hdr_txt, hdr_txt.get_rect(
                centerx=col_r.centerx, centery=col_r.y + _COL_HDR // 2))

        # ── Tooltip item (set during row rendering) ───────────────────────────
        tooltip_item = None

        # ── Buy column — merchant stock ───────────────────────────────────────
        for idx, item in enumerate(merchant.stock):
            r = self._buy_row(idx, buy_col)
            if r.bottom > panel.bottom - 4:
                break
            hovered = r.collidepoint(mx, my)
            if hovered:
                tooltip_item = item
            pygame.draw.rect(surface, _ROW_H_COL if hovered else _ROW_N, r)
            pygame.draw.rect(surface, _BORDER, r, 1)

            name, col = self._label(item)
            price     = merchant.price_of(item)
            p_col     = _BUY_C if player.gold >= price else _CANT_C

            n_surf = self._font_md.render(name, True, col)
            p_surf = self._font_sm.render(f"{price} g", True, p_col)
            surface.blit(n_surf, (r.x + 6, r.y + 5))
            surface.blit(p_surf, (r.right - p_surf.get_width() - 6, r.y + 16))

            # Small type badge on second line
            if isinstance(item, EquipItem):
                badge = self._font_sm.render(
                    item.base_name, True, (100, 100, 140))
                surface.blit(badge, (r.x + 6, r.y + 26))

        # ── Sell column — player backpack + potions ───────────────────────────
        sellable = list(player.backpack) + list(player.potions)
        for idx, item in enumerate(sellable):
            r = self._sell_row(idx, sell_col)
            if r.bottom > panel.bottom - 4:
                break
            hovered = r.collidepoint(mx, my)
            if hovered:
                tooltip_item = item
            pygame.draw.rect(surface, _ROW_H_COL if hovered else _ROW_N, r)
            pygame.draw.rect(surface, _BORDER, r, 1)

            name, col = self._label(item)
            sell_val  = item_sell_price(item)

            n_surf = self._font_md.render(name, True, col)
            s_surf = self._font_sm.render(f"{sell_val} g", True, _SELL_C)
            surface.blit(n_surf, (r.x + 6, r.y + 5))
            surface.blit(s_surf, (r.right - s_surf.get_width() - 6, r.y + 16))

            if isinstance(item, EquipItem):
                badge = self._font_sm.render(
                    item.base_name, True, (100, 100, 140))
                surface.blit(badge, (r.x + 6, r.y + 26))

        # ── Notification bar ──────────────────────────────────────────────────
        if self._notify_t > 0:
            alpha = min(255, int(self._notify_t * 160))
            msg_s = self._font_md.render(self._notify_msg, True, YELLOW)
            msg_s.set_alpha(alpha)
            surface.blit(msg_s, msg_s.get_rect(
                centerx=panel.centerx, y=panel.bottom - 20))

        # ── Tooltip ───────────────────────────────────────────────────────────
        if tooltip_item:
            self._draw_tooltip(surface, tooltip_item, player, (mx, my))

    # ── Comparison helpers (mirrors inventory logic) ──────────────────────────

    @staticmethod
    def _equipped_for(item: EquipItem, player) -> EquipItem | None:
        eq = player.equipment.get(item.slot)
        if eq is None and item.slot == "ring":
            eq = player.equipment.get("ring2")
        return eq if eq is not None else None

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
                    sections.append(("cmp", stat_txt, stat_col,
                                     delta_txt, delta_col))
            else:
                for txt, col in item.stat_lines():
                    sections.append(("line", txt, col))
        else:
            for txt, col in item.stat_lines():
                sections.append(("line", txt, col))

        encs = getattr(item, "enchantments", [])
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

        # Measure width
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

        # Measure height
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
        """
        button 1 = left  → buy from merchant
        button 3 = right → sell from player backpack
        Returns True if an action was taken.
        """
        panel    = self._panel()
        buy_col  = self._buy_col(panel)
        sell_col = self._sell_col(panel)

        # ── Buy ───────────────────────────────────────────────────────────────
        if button == 1:
            for idx, item in enumerate(merchant.stock):
                r = self._buy_row(idx, buy_col)
                if r.bottom > panel.bottom - 4:
                    break
                if r.collidepoint(mx, my):
                    price = merchant.price_of(item)
                    if player.gold >= price:
                        player.gold -= price
                        merchant.stock.remove(item)
                        player.add_item(item)
                        name, _ = self._label(item)
                        self.notify(t("shop.bought", name=name))
                    else:
                        self.notify(t("shop.need_gold", n=price - player.gold))
                    return True

        # ── Sell ──────────────────────────────────────────────────────────────
        if button in (1, 3):
            sellable = list(player.backpack) + list(player.potions)
            for idx, item in enumerate(sellable):
                r = self._sell_row(idx, sell_col)
                if r.bottom > panel.bottom - 4:
                    break
                if r.collidepoint(mx, my):
                    val = item_sell_price(item)
                    player.gold += val
                    if item in player.backpack:
                        player.backpack.remove(item)
                    elif item in player.potions:
                        player.potions.remove(item)
                    name, _ = self._label(item)
                    self.notify(t("shop.sold", name=name, n=val))
                    return True

        return False
