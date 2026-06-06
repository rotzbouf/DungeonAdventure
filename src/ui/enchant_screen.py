"""Enchantment Forge UI — lets the player add enchantments to items with open slots."""
from __future__ import annotations
import pygame
from src.settings import SCREEN_WIDTH, SCREEN_HEIGHT, HUD_HEIGHT, YELLOW, WHITE, LIGHT_GRAY
from src.items.item import EquipItem, SLOT_ORDER, SLOT_LABELS
from src.items.enchant import ENCHANTMENTS, SYNERGIES, RARITY_COLORS, RARITY_LABELS, active_synergies
from src.ui.pager import draw_pager

_BG        = (6,   4,  18)
_PANEL     = (12,  8,  30)
_BORDER    = (120, 50, 200)
_BORDER_LO = (60,  25, 110)
_HDR       = (200, 100, 255)
_SEL       = (50,  20,  90)
_SEL_HI    = (80,  30, 140)
_DIM       = (100, 80, 140)
_GOLD_COL  = (220, 175,   0)
_GREEN     = ( 60, 200,  80)
_RED       = (200,  50,  50)
_SLOT_COL  = (80,  120, 200)
_OPEN_COL  = (100, 100, 160)


class EnchantScreen:
    W  = 1100
    H  = 660

    def __init__(self):
        self._fxl  = pygame.font.SysFont("monospace", 28, bold=True)
        self._flg  = pygame.font.SysFont("monospace", 28, bold=True)
        self._fmd  = pygame.font.SysFont("monospace", 24, bold=True)
        self._fsm  = pygame.font.SysFont("monospace", 25)

        self._sel_item: EquipItem | None = None
        self._sel_enc:  str | None       = None   # enchantment ID
        self._item_scroll = 0
        self._enc_scroll  = 0
        self._msg         = ""
        self._msg_timer   = 0.0
        self._item_prev: pygame.Rect | None = None
        self._item_next: pygame.Rect | None = None
        self._enc_prev:  pygame.Rect | None = None
        self._enc_next:  pygame.Rect | None = None

    # ─── Public API ─────────────────────────────────────────────────────────────

    def open(self):
        self._sel_item    = None
        self._sel_enc     = None
        self._item_scroll = 0
        self._enc_scroll  = 0
        self._msg         = ""
        self._msg_timer   = 0.0

    def update(self, dt: float):
        if self._msg_timer > 0:
            self._msg_timer = max(0.0, self._msg_timer - dt)

    def handle_event(self, event: pygame.event.Event, player) -> bool:
        """Process one event. Returns True if the event was consumed."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN and self._sel_item and self._sel_enc:
                self._apply(player)
                return True
            if event.key in (pygame.K_UP, pygame.K_w):
                self._enc_scroll = max(0, self._enc_scroll - 1)
                return True
            if event.key in (pygame.K_DOWN, pygame.K_s):
                self._enc_scroll += 1
                return True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            ox = SCREEN_WIDTH // 2 - self.W // 2
            oy = (SCREEN_HEIGHT - HUD_HEIGHT) // 2 - self.H // 2
            self._handle_click(mx - ox, my - oy, player)
            return True

        if event.type == pygame.MOUSEWHEEL:
            mx, my = pygame.mouse.get_pos()
            ox = SCREEN_WIDTH // 2 - self.W // 2
            oy = (SCREEN_HEIGHT - HUD_HEIGHT) // 2 - self.H // 2
            lx = mx - ox
            if lx < self.W // 2:
                self._item_scroll = max(0, self._item_scroll - event.y)
            else:
                self._enc_scroll = max(0, self._enc_scroll - event.y)
            return True

        return False

    # ─── Internal helpers ───────────────────────────────────────────────────────

    def _enchantable_items(self, player) -> list[tuple[str, EquipItem]]:
        """Return (label, item) for every equipped or backpack item with open slots."""
        result: list[tuple[str, EquipItem]] = []
        for slot in SLOT_ORDER:
            item = player.equipment.get(slot)
            if isinstance(item, EquipItem) and item.open_slots > 0:
                result.append((f"[{SLOT_LABELS.get(slot, slot)}]", item))
        for item in player.backpack:
            if isinstance(item, EquipItem) and item.open_slots > 0:
                result.append(("[BAG]", item))
        return result

    def _handle_click(self, lx: int, ly: int, player):
        pad = 14
        header_h = 52
        split_x  = self.W // 2

        # ── Pager button clicks ────────────────────────────────────────────────
        _ITEM_VIS = (self.H - 80 - (header_h + pad) - 32) // 40  # items visible per page
        _ENC_VIS  = (self.H - 120 - (header_h + pad)) // 36      # enchants visible per page
        if self._item_prev and self._item_prev.collidepoint(lx, ly):
            self._item_scroll = max(0, self._item_scroll - _ITEM_VIS)
            return
        if self._item_next and self._item_next.collidepoint(lx, ly):
            items = self._enchantable_items(player)
            ms = max(0, len(items) - _ITEM_VIS)
            self._item_scroll = min(ms, self._item_scroll + _ITEM_VIS)
            return
        if self._enc_prev and self._enc_prev.collidepoint(lx, ly):
            self._enc_scroll = max(0, self._enc_scroll - _ENC_VIS)
            return
        if self._enc_next and self._enc_next.collidepoint(lx, ly):
            ms = max(0, len(ENCHANTMENTS) - _ENC_VIS)
            self._enc_scroll = min(ms, self._enc_scroll + _ENC_VIS)
            return

        # ── Left panel click (item selection) ────────────────────────────────
        if lx < split_x:
            items = self._enchantable_items(player)
            row_h = 40
            list_y0 = header_h + pad
            for i, (label, item) in enumerate(items):
                iy = list_y0 + (i - self._item_scroll) * row_h
                if list_y0 <= iy <= self.H - 80:
                    if iy <= ly <= iy + row_h - 2:
                        self._sel_item = item
                        self._sel_enc  = None
                        return

        # ── Right panel click (enchantment selection) ─────────────────────────
        if lx >= split_x and self._sel_item:
            enc_list = list(ENCHANTMENTS.values())
            row_h = 36
            list_y0 = header_h + pad
            for i, enc in enumerate(enc_list):
                iy = list_y0 + (i - self._enc_scroll) * row_h
                if list_y0 <= iy <= self.H - 110:
                    if iy <= ly <= iy + row_h - 2:
                        self._sel_enc = enc.id
                        return

        # ── Apply button ──────────────────────────────────────────────────────
        btn = self._apply_btn_rect()
        if btn and btn.collidepoint(lx, ly):
            self._apply(player)

    def _apply_btn_rect(self):
        if not (self._sel_item and self._sel_enc):
            return None
        bw, bh = 220, 36
        bx = self.W // 2 + (self.W // 2 - bw) // 2
        by = self.H - 56
        return pygame.Rect(bx, by, bw, bh)

    def _apply(self, player):
        if not (self._sel_item and self._sel_enc):
            return
        enc = ENCHANTMENTS.get(self._sel_enc)
        if not enc:
            return
        if self._sel_item.open_slots <= 0:
            self._msg = "No open slots!"
            self._msg_timer = 2.5
            return
        if player.gold < enc.cost:
            self._msg = "Not enough gold!"
            self._msg_timer = 2.5
            return
        player.gold -= enc.cost
        self._sel_item.add_enchantment(self._sel_enc)
        self._msg = f"Applied: {enc.name}!"
        self._msg_timer = 3.0
        self._sel_enc = None
        if self._sel_item.open_slots <= 0:
            self._sel_item = None

    # ─── Draw ────────────────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface, player):
        ox = SCREEN_WIDTH  // 2 - self.W // 2
        oy = (SCREEN_HEIGHT - HUD_HEIGHT) // 2 - self.H // 2

        # Overlay backdrop
        ov = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT - HUD_HEIGHT), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 180))
        surface.blit(ov, (0, 0))

        # Main panel
        panel = pygame.Surface((self.W, self.H))
        panel.fill(_BG)
        pygame.draw.rect(panel, _BORDER, (0, 0, self.W, self.H), 2)

        self._draw_header(panel)

        split_x = self.W // 2
        pygame.draw.line(panel, _BORDER_LO, (split_x, 50), (split_x, self.H - 80), 1)

        self._draw_item_panel(panel, player, split_x)
        self._draw_enchant_panel(panel, player, split_x)
        self._draw_footer(panel, player)

        surface.blit(panel, (ox, oy))

    def _draw_header(self, surf: pygame.Surface):
        pygame.draw.rect(surf, _PANEL, (0, 0, self.W, 50))
        pygame.draw.line(surf, _BORDER, (0, 50), (self.W, 50), 1)
        title = self._fxl.render("✦  ENCHANTMENT FORGE  ✦", True, _HDR)
        surf.blit(title, title.get_rect(centerx=self.W // 2, centery=25))

    def _draw_item_panel(self, surf: pygame.Surface, player, split_x: int):
        pad     = 14
        row_h   = 40
        list_y0 = 52 + pad
        clip_h  = self.H - 80 - list_y0 - 32   # 32 px reserved for pager

        # Column header
        hdr = self._fmd.render("ITEMS WITH OPEN SLOTS", True, _HDR)
        surf.blit(hdr, (pad, 54))

        items = self._enchantable_items(player)
        if not items:
            msg = self._fsm.render("No items with open slots.", True, _DIM)
            surf.blit(msg, (pad, list_y0 + 20))
            return

        for i, (label, item) in enumerate(items):
            iy = list_y0 + (i - self._item_scroll) * row_h
            if iy < list_y0 or iy > list_y0 + clip_h:
                continue

            selected = (item is self._sel_item)
            row_col  = _SEL_HI if selected else _SEL if i % 2 == 0 else _PANEL
            pygame.draw.rect(surf, row_col, (pad - 2, iy, split_x - pad * 2 + 2, row_h - 2))

            # Slot label
            slot_s = self._fsm.render(label, True, _SLOT_COL)
            surf.blit(slot_s, (pad + 2, iy + 4))

            # Item name
            name_col = item.quality_color
            name_s   = self._fmd.render(item.display_name, True, name_col)
            surf.blit(name_s, (pad + 62, iy + 4))

            # Slot count
            used  = len(item.enchantments)
            total = item.enchant_slots
            slots_str = f"{'◆' * used}{'◇' * (total - used)}"
            slots_col = _GREEN if item.open_slots > 0 else _DIM
            slots_s = self._fmd.render(slots_str, True, slots_col)
            surf.blit(slots_s, (split_x - 60, iy + 4))

            # Applied enchantments summary
            if item.enchantments:
                enc_names = ", ".join(
                    ENCHANTMENTS[eid].name for eid in item.enchantments
                    if eid in ENCHANTMENTS
                )
                enc_s = self._fsm.render(enc_names, True, _HDR)
                surf.blit(enc_s, (pad + 2, iy + 22))

        # ── Item pager ────────────────────────────────────────────────────────
        vis_per_page = max(1, clip_h // row_h)
        total_pages  = max(1, (len(items) + vis_per_page - 1) // vis_per_page)
        page         = self._item_scroll // vis_per_page + 1
        cx           = (split_x) // 2
        self._item_prev, self._item_next = draw_pager(
            surf, cx, list_y0 + clip_h + 5, page, total_pages, self._fsm)

    def _draw_enchant_panel(self, surf: pygame.Surface, player, split_x: int):
        pad     = 14
        row_h   = 36
        list_y0 = 52 + pad
        clip_h  = self.H - 120 - list_y0
        px      = split_x + pad

        hdr = self._fmd.render("ENCHANTMENTS", True, _HDR)
        surf.blit(hdr, (px, 54))

        if self._sel_item is None:
            hint = self._fsm.render("← Select an item first", True, _DIM)
            surf.blit(hint, (px, list_y0 + 20))
            return

        enc_list = list(ENCHANTMENTS.values())
        for i, enc in enumerate(enc_list):
            iy = list_y0 + (i - self._enc_scroll) * row_h
            if iy < list_y0 or iy > list_y0 + clip_h:
                continue

            selected = (enc.id == self._sel_enc)
            can_afford = player.gold >= enc.cost
            row_col = _SEL_HI if selected else _SEL if i % 2 == 0 else _PANEL
            pygame.draw.rect(surf, row_col,
                             (px - 2, iy, self.W - px - pad + 2, row_h - 2))

            # Rarity dot
            rcol = RARITY_COLORS.get(enc.rarity, WHITE)
            pygame.draw.circle(surf, rcol, (px + 6, iy + row_h // 2), 5)

            # Name
            name_s = self._fmd.render(enc.name, True, enc.color)
            surf.blit(name_s, (px + 16, iy + 2))

            # Effect summary (first line only)
            if enc.mods:
                from src.items.item import Modifier
                m = Modifier(enc.mods[0][0], enc.mods[0][1])
                eff_s = self._fsm.render(m.describe(), True, _DIM)
                surf.blit(eff_s, (px + 16, iy + 18))

            # Cost
            cost_col = _GOLD_COL if can_afford else _RED
            cost_s = self._fmd.render(f"♦{enc.cost}", True, cost_col)
            surf.blit(cost_s, (self.W - pad - cost_s.get_width() - 4, iy + 8))

        # ── Enchantment pager ─────────────────────────────────────────────────
        enc_list     = list(ENCHANTMENTS.values())
        vis_enc      = max(1, clip_h // row_h)
        enc_pages    = max(1, (len(enc_list) + vis_enc - 1) // vis_enc)
        enc_page     = self._enc_scroll // vis_enc + 1
        enc_cx       = split_x + (self.W - split_x) // 2
        self._enc_prev, self._enc_next = draw_pager(
            surf, enc_cx, list_y0 + clip_h + 5, enc_page, enc_pages, self._fsm)

        # Tooltip panel for selected enchantment
        if self._sel_enc and self._sel_enc in ENCHANTMENTS:
            self._draw_enc_tooltip(surf, split_x, player)

    def _draw_enc_tooltip(self, surf: pygame.Surface, split_x: int, player):
        enc  = ENCHANTMENTS[self._sel_enc]
        pad  = 14
        ty   = self.H - 110
        tw   = self.W // 2 - pad * 2

        pygame.draw.rect(surf, _PANEL, (split_x + pad - 2, ty, tw + 2, 100))
        pygame.draw.rect(surf, _BORDER_LO, (split_x + pad - 2, ty, tw + 2, 100), 1)

        # Full effect lines
        y = ty + 4
        rarity_col = RARITY_COLORS.get(enc.rarity, WHITE)
        rlbl = self._fsm.render(
            f"{enc.name}  [{RARITY_LABELS.get(enc.rarity, enc.rarity)}]",
            True, rarity_col)
        surf.blit(rlbl, (split_x + pad, y))
        y += 18

        for desc in enc.describe_lines():
            ds = self._fsm.render(desc, True, (120, 230, 120))
            surf.blit(ds, (split_x + pad + 8, y))
            y += 15

        # Tags / synergy hint
        tag_str = "Tags: " + ", ".join(enc.tags)
        ts = self._fsm.render(tag_str, True, (100, 100, 160))
        surf.blit(ts, (split_x + pad, y))

    def _draw_footer(self, surf: pygame.Surface, player):
        """Bottom strip: active synergies + apply button + message."""
        fy  = self.H - 78
        pad = 14
        pygame.draw.line(surf, _BORDER_LO, (0, fy), (self.W, fy), 1)

        # Active synergies summary (left half)
        all_tags = player.equipped_enchant_tags()
        syns     = active_synergies(all_tags)
        if syns:
            syn_names = "  ✦  ".join(n for n, _ in syns)
            label = self._fsm.render(f"Active synergies: {syn_names}", True, (200, 150, 255))
        else:
            label = self._fsm.render("No active synergies.", True, _DIM)
        surf.blit(label, (pad, fy + 10))

        # Gold counter
        gold_s = self._fmd.render(f"♦ {player.gold}", True, _GOLD_COL)
        surf.blit(gold_s, (pad, fy + 32))

        # Message area
        if self._msg and self._msg_timer > 0:
            fade  = min(1.0, self._msg_timer / 0.4)
            mcol  = tuple(int(c * fade) for c in (_GREEN if "Applied" in self._msg else _RED))
            ms    = self._flg.render(self._msg, True, mcol)
            surf.blit(ms, ms.get_rect(centerx=self.W // 2, centery=fy + 22))

        # Apply button
        btn = self._apply_btn_rect()
        if btn:
            enc     = ENCHANTMENTS.get(self._sel_enc)
            can_pay = enc and player.gold >= enc.cost
            bcol    = (60, 180, 60) if can_pay else (80, 30, 30)
            pygame.draw.rect(surf, bcol, btn)
            pygame.draw.rect(surf, _BORDER_LO, btn, 1)
            lbl = f"Apply  ♦{enc.cost}" if enc else "Apply"
            bs  = self._fmd.render(lbl, True, WHITE)
            surf.blit(bs, bs.get_rect(center=btn.center))
