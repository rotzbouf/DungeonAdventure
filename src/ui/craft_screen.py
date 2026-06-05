"""Workshop UI — two tabs: CRAFT and DISASSEMBLE."""
from __future__ import annotations
import pygame
from src.settings import SCREEN_WIDTH, SCREEN_HEIGHT, HUD_HEIGHT, YELLOW, WHITE, LIGHT_GRAY
from src.items.item import EquipItem, SLOT_ORDER, SLOT_LABELS, QUALITY_RARE, QUALITY_UNIQUE
from src.items.materials import (
    MATERIALS, RECIPES, Recipe,
    disassemble, execute_recipe,
)

# ── Palette ───────────────────────────────────────────────────────────────────
_BG      = (8,   6,  14)
_PANEL   = (14, 12,  24)
_BORDER  = (100, 70, 180)
_BORDER_LO = (50, 35, 90)
_HDR     = (180, 140, 255)
_SEL     = (40,  25,  70)
_SEL_HI  = (70,  45, 120)
_DIM     = (90,  80, 120)
_GOLD    = (220, 175,   0)
_GREEN   = ( 60, 200,  80)
_RED     = (200,  50,  50)
_ORANGE  = (240, 130,  30)
_TAB_ACT = (70,  45, 120)
_TAB_IN  = (25,  18,  44)

_MAT_COLORS = {m.id: m.color for m in MATERIALS.values()}

_Q_COLOR = {
    0: (188, 188, 188),
    1: ( 80,  80, 255),
    2: (252, 188,   0),
    3: (200, 115,   0),
}


class CraftScreen:
    W = 1120
    H = 700

    def __init__(self):
        self._fl  = pygame.font.SysFont("monospace", 28, bold=True)
        self._fm  = pygame.font.SysFont("monospace", 25, bold=True)
        self._fs  = pygame.font.SysFont("monospace", 25)

        self._tab        = "craft"       # "craft" | "disassemble"
        self._sel_recipe: Recipe | None  = None
        self._sel_item:   EquipItem | None = None   # disassemble target
        self._target_item: EquipItem | None = None  # reforge / add_slot target
        self._recipe_scroll = 0
        self._item_scroll   = 0
        self._msg       = ""
        self._msg_timer = 0.0
        self._msg_ok    = True
        self._disassemble_preview: dict[str, int] = {}   # cached yield for selected item

    # ─── Public ──────────────────────────────────────────────────────────────

    def open(self):
        self._tab = "craft"
        self._sel_recipe = None
        self._sel_item   = None
        self._target_item = None
        self._recipe_scroll = 0
        self._item_scroll   = 0
        self._msg = ""
        self._msg_timer = 0.0
        self._disassemble_preview = {}

    def update(self, dt: float):
        if self._msg_timer > 0:
            self._msg_timer = max(0.0, self._msg_timer - dt)

    def handle_event(self, event: pygame.event.Event, player) -> bool:
        ox = SCREEN_WIDTH  // 2 - self.W // 2
        oy = (SCREEN_HEIGHT - HUD_HEIGHT) // 2 - self.H // 2

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                if self._tab == "craft" and self._sel_recipe:
                    self._do_craft(player)
                elif self._tab == "disassemble" and self._sel_item:
                    self._do_disassemble(player)
                return True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            lx, ly = event.pos[0] - ox, event.pos[1] - oy
            self._handle_click(lx, ly, player)
            return True

        if event.type == pygame.MOUSEWHEEL:
            mx, my = pygame.mouse.get_pos()
            lx = mx - ox
            if lx < self.W // 2:
                if self._tab == "craft":
                    self._recipe_scroll = max(0, self._recipe_scroll - event.y)
                else:
                    self._item_scroll = max(0, self._item_scroll - event.y)
            return True

        return False

    # ─── Internals ───────────────────────────────────────────────────────────

    def _backpack_items(self, player) -> list[EquipItem]:
        return [i for i in player.backpack if isinstance(i, EquipItem)]

    def _can_afford(self, recipe: Recipe, player) -> bool:
        mats = getattr(player, "materials", {})
        return all(mats.get(m, 0) >= q for m, q in recipe.cost.items())

    def _handle_click(self, lx: int, ly: int, player):
        hdr_h   = 88
        pad     = 14
        split_x = self.W // 2

        # ── Tab buttons ───────────────────────────────────────────────────────
        if ly < hdr_h:
            tw = self.W // 2 - pad
            if pad <= lx <= pad + tw:
                self._tab = "craft"
                self._sel_recipe = None
                self._sel_item   = None
                self._target_item = None
            elif split_x <= lx <= split_x + tw:
                self._tab = "disassemble"
                self._sel_recipe = None
                self._sel_item   = None
            return

        row_h  = 44
        list_y0 = hdr_h + pad
        clip_h  = self.H - 120 - list_y0

        # ── CRAFT tab ─────────────────────────────────────────────────────────
        if self._tab == "craft":
            # Left: recipe list
            if lx < split_x:
                for i, recipe in enumerate(RECIPES):
                    iy = list_y0 + (i - self._recipe_scroll) * row_h
                    if list_y0 <= iy <= list_y0 + clip_h:
                        if iy <= ly <= iy + row_h - 2:
                            self._sel_recipe  = recipe
                            self._target_item = None
                            return

            # Right: target item picker (for reforge / add_slot)
            if lx >= split_x and self._sel_recipe and self._sel_recipe.needs_target:
                items = self._backpack_items(player)
                if self._sel_recipe.id == "reforge":
                    items = [i for i in items if i.quality in (QUALITY_RARE, QUALITY_UNIQUE)]
                for i, item in enumerate(items):
                    iy = list_y0 + (i - self._item_scroll) * row_h + 130
                    if iy <= ly <= iy + row_h - 2:
                        self._target_item = item
                        return

            # Apply button
            btn = self._craft_btn_rect()
            if btn and btn.collidepoint(lx, ly):
                self._do_craft(player)

        # ── DISASSEMBLE tab ───────────────────────────────────────────────────
        else:
            items = self._backpack_items(player)
            if lx < split_x:
                for i, item in enumerate(items):
                    iy = list_y0 + (i - self._item_scroll) * row_h
                    if list_y0 <= iy <= list_y0 + clip_h:
                        if iy <= ly <= iy + row_h - 2:
                            self._sel_item = item
                            self._disassemble_preview = disassemble(item)
                            return

            btn = self._disassemble_btn_rect()
            if btn and btn.collidepoint(lx, ly):
                self._do_disassemble(player)

    def _craft_btn_rect(self):
        if not self._sel_recipe:
            return None
        bw, bh = 220, 36
        bx = self.W // 2 + (self.W // 2 - bw) // 2
        by = self.H - 52
        return pygame.Rect(bx, by, bw, bh)

    def _disassemble_btn_rect(self):
        if not self._sel_item:
            return None
        bw, bh = 240, 36
        bx = self.W // 2 + (self.W // 2 - bw) // 2
        by = self.H - 52
        return pygame.Rect(bx, by, bw, bh)

    def _do_craft(self, player):
        if not self._sel_recipe:
            return
        try:
            msg = execute_recipe(self._sel_recipe, player, self._target_item)
            self._msg       = msg
            self._msg_ok    = True
            self._target_item = None
            # If target was reforged/slot-added and no longer valid, deselect
        except ValueError as e:
            self._msg    = str(e)
            self._msg_ok = False
        self._msg_timer = 3.0

    def _do_disassemble(self, player):
        if not self._sel_item or self._sel_item not in player.backpack:
            return
        yield_ = disassemble(self._sel_item)
        mats = getattr(player, "materials", {})
        for m, q in yield_.items():
            mats[m] = mats.get(m, 0) + q
        player.materials = mats
        player.backpack.remove(self._sel_item)
        name = self._sel_item.display_name
        self._sel_item           = None
        self._disassemble_preview = {}
        self._msg                = f"Disassembled {name}!"
        self._msg_ok    = True
        self._msg_timer = 3.0

    # ─── Draw ────────────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface, player):
        ox = SCREEN_WIDTH  // 2 - self.W // 2
        oy = (SCREEN_HEIGHT - HUD_HEIGHT) // 2 - self.H // 2

        # Backdrop
        ov = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT - HUD_HEIGHT), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 185))
        surface.blit(ov, (0, 0))

        panel = pygame.Surface((self.W, self.H))
        panel.fill(_BG)
        pygame.draw.rect(panel, _BORDER, (0, 0, self.W, self.H), 2)

        self._draw_header(panel)
        split_x = self.W // 2
        pygame.draw.line(panel, _BORDER_LO, (split_x, 88), (split_x, self.H - 70), 1)

        if self._tab == "craft":
            self._draw_craft_left(panel)
            self._draw_craft_right(panel, player)
        else:
            self._draw_disassemble_left(panel, player)
            self._draw_disassemble_right(panel, player)

        self._draw_footer(panel, player)
        surface.blit(panel, (ox, oy))

    def _draw_header(self, surf):
        pygame.draw.rect(surf, _PANEL, (0, 0, self.W, 88))
        pygame.draw.line(surf, _BORDER, (0, 88), (self.W, 88), 1)

        title = self._fl.render("⚒  WORKSHOP", True, _HDR)
        surf.blit(title, title.get_rect(centerx=self.W // 2, centery=24))

        # Tabs
        pad  = 14
        tw   = self.W // 2 - pad * 2
        tabs = [("craft", "CRAFT"), ("disassemble", "DISASSEMBLE")]
        for i, (tid, tlabel) in enumerate(tabs):
            tx   = pad if i == 0 else self.W // 2
            rect = pygame.Rect(tx, 48, tw, 32)
            col  = _TAB_ACT if self._tab == tid else _TAB_IN
            pygame.draw.rect(surf, col, rect)
            pygame.draw.rect(surf, _BORDER_LO, rect, 1)
            ts = self._fm.render(tlabel, True, _HDR if self._tab == tid else _DIM)
            surf.blit(ts, ts.get_rect(center=rect.center))

    def _draw_craft_left(self, surf):
        pad     = 14
        row_h   = 44
        list_y0 = 88 + pad
        clip_h  = self.H - 120 - list_y0
        split_x = self.W // 2

        col_hdr = self._fs.render("RECIPES", True, _HDR)
        surf.blit(col_hdr, (pad, 91))

        for i, recipe in enumerate(RECIPES):
            iy = list_y0 + (i - self._recipe_scroll) * row_h
            if iy < list_y0 or iy > list_y0 + clip_h:
                continue
            selected = (recipe is self._sel_recipe)
            bg = _SEL_HI if selected else (_SEL if i % 2 == 0 else _PANEL)
            pygame.draw.rect(surf, bg, (pad - 2, iy, split_x - pad * 2, row_h - 2))

            name_col   = WHITE
            name_s = self._fm.render(recipe.name, True, name_col)
            surf.blit(name_s, (pad + 4, iy + 4))

            # Cost summary on right of row
            cx = split_x - pad - 6
            for mat, qty in reversed(list(recipe.cost.items())):
                mat_col = MATERIALS[mat].color
                cs = self._fs.render(f"×{qty}", True, mat_col)
                cx -= cs.get_width()
                surf.blit(cs, (cx, iy + 14))
                cx -= 14
                pygame.draw.circle(surf, mat_col, (cx + 5, iy + 18), 5)
                cx -= 10

    def _draw_craft_right(self, surf, player):
        pad     = 14
        split_x = self.W // 2
        px      = split_x + pad
        list_y0 = 88 + pad

        # Materials inventory (always visible at top-right)
        mats = getattr(player, "materials", {})
        mat_hdr = self._fs.render("YOUR MATERIALS", True, _HDR)
        surf.blit(mat_hdr, (px, 92))
        my = 110
        for mid, mat in MATERIALS.items():
            qty  = mats.get(mid, 0)
            col  = mat.color if qty > 0 else _DIM
            pygame.draw.circle(surf, col, (px + 8, my + 7), 6)
            ms = self._fs.render(f"{mat.name:<16} {qty:>3}", True, col)
            surf.blit(ms, (px + 20, my))
            my += 18
        pygame.draw.line(surf, _BORDER_LO, (px, my + 4), (self.W - pad, my + 4), 1)

        if self._sel_recipe is None:
            hint = self._fs.render("← Select a recipe", True, _DIM)
            surf.blit(hint, (px, my + 16))
            return

        r = self._sel_recipe
        ry = my + 14

        # Recipe name + description
        ns = self._fm.render(r.name, True, _HDR)
        surf.blit(ns, (px, ry)); ry += 22
        for word_line in _wrap(r.desc, self.W // 2 - pad * 2, self._fs):
            ds = self._fs.render(word_line, True, LIGHT_GRAY)
            surf.blit(ds, (px, ry)); ry += 16
        ry += 6

        # Cost list
        cost_hdr = self._fs.render("REQUIRES:", True, _HDR)
        surf.blit(cost_hdr, (px, ry)); ry += 16
        for mid, qty in r.cost.items():
            mat      = MATERIALS[mid]
            have     = mats.get(mid, 0)
            enough   = have >= qty
            col_have = _GREEN if enough else _RED
            line = f"  {mat.name}: {have}/{qty}"
            ls = self._fs.render(line, True, col_have)
            surf.blit(ls, (px, ry)); ry += 16
        ry += 4

        # Target picker (reforge / add_slot)
        if r.needs_target:
            tp_hdr = self._fs.render("SELECT TARGET ITEM:", True, _HDR)
            surf.blit(tp_hdr, (px, ry)); ry += 18
            items = self._backpack_items(player)
            if r.id == "reforge":
                items = [i for i in items if i.quality in (QUALITY_RARE, QUALITY_UNIQUE)]
            for j, item in enumerate(items):
                iy = ry + j * 32
                selected = (item is self._target_item)
                bg = _SEL_HI if selected else (_SEL if j % 2 == 0 else _PANEL)
                pygame.draw.rect(surf, bg, (px - 2, iy, self.W - split_x - pad, 30))
                col = _Q_COLOR.get(item.quality, WHITE)
                is_ = self._fs.render(item.display_name, True, col)
                surf.blit(is_, (px + 4, iy + 7))

    def _draw_disassemble_left(self, surf, player):
        pad     = 14
        row_h   = 44
        list_y0 = 88 + pad
        clip_h  = self.H - 120 - list_y0
        split_x = self.W // 2

        col_hdr = self._fs.render("BACKPACK ITEMS", True, _HDR)
        surf.blit(col_hdr, (pad, 91))

        items = self._backpack_items(player)
        if not items:
            ns = self._fs.render("Backpack is empty.", True, _DIM)
            surf.blit(ns, (pad, list_y0 + 20))
            return

        for i, item in enumerate(items):
            iy = list_y0 + (i - self._item_scroll) * row_h
            if iy < list_y0 or iy > list_y0 + clip_h:
                continue
            selected = (item is self._sel_item)
            bg = _SEL_HI if selected else (_SEL if i % 2 == 0 else _PANEL)
            pygame.draw.rect(surf, bg, (pad - 2, iy, split_x - pad * 2, row_h - 2))

            col = _Q_COLOR.get(item.quality, WHITE)
            ns  = self._fm.render(item.display_name, True, col)
            surf.blit(ns, (pad + 4, iy + 4))
            slot_s = self._fs.render(SLOT_LABELS.get(item.slot, item.slot), True, _DIM)
            surf.blit(slot_s, (pad + 4, iy + 24))

    def _draw_disassemble_right(self, surf, player):
        pad     = 14
        split_x = self.W // 2
        px      = split_x + pad
        ry      = 88 + pad + 10

        if self._sel_item is None:
            hint = self._fs.render("← Select an item to disassemble", True, _DIM)
            surf.blit(hint, (px, ry + 20))
            return

        item = self._sel_item
        col  = _Q_COLOR.get(item.quality, WHITE)
        ns   = self._fm.render(item.display_name, True, col)
        surf.blit(ns, (px, ry)); ry += 24

        for stat_line, stat_col in item.stat_lines()[:8]:
            if not stat_line:
                ry += 6; continue
            ss = self._fs.render(stat_line, True, stat_col)
            surf.blit(ss, (px + 8, ry)); ry += 16
        ry += 8

        pygame.draw.line(surf, _BORDER_LO, (px, ry), (self.W - pad, ry), 1)
        ry += 10

        yh = self._fs.render("WILL YIELD:", True, _HDR)
        surf.blit(yh, (px, ry)); ry += 18
        for mid, qty in self._disassemble_preview.items():
            mat = MATERIALS[mid]
            col = mat.color
            pygame.draw.circle(surf, col, (px + 8, ry + 7), 6)
            ys  = self._fs.render(f"{mat.name}  ×{qty}", True, col)
            surf.blit(ys, (px + 20, ry)); ry += 18

        # Warning
        ry += 8
        ws = self._fs.render("⚠ Disassembly is permanent.", True, _ORANGE)
        surf.blit(ws, (px, ry))

    def _draw_footer(self, surf, player):
        fy = self.H - 70
        pad = 14
        pygame.draw.line(surf, _BORDER_LO, (0, fy), (self.W, fy), 1)

        # Message
        if self._msg and self._msg_timer > 0:
            fade = min(1.0, self._msg_timer / 0.4)
            col  = tuple(int(c * fade) for c in (_GREEN if self._msg_ok else _RED))
            ms   = self._fm.render(self._msg, True, col)
            surf.blit(ms, ms.get_rect(centerx=self.W // 2, centery=fy + 20))

        # Action button
        if self._tab == "craft":
            btn = self._craft_btn_rect()
            if btn:
                r = self._sel_recipe
                can = r and self._can_afford(r, player) and (
                    not r.needs_target or self._target_item is not None)
                lbl = f"Craft  {r.name}" if r else "Craft"
                _draw_btn(surf, btn, lbl, can)
        else:
            btn = self._disassemble_btn_rect()
            if btn:
                _draw_btn(surf, btn, f"Disassemble", True, danger=True)

        # Hint
        hs = self._fs.render("ENTER to confirm  ·  ESC to close", True, _DIM)
        surf.blit(hs, (pad, fy + 50))


def _draw_btn(surf, btn, label, enabled, danger=False):
    if danger:
        col = (100, 30, 30) if enabled else (40, 20, 20)
        border = (180, 50, 50) if enabled else _BORDER_LO
    else:
        col    = (30, 100, 50) if enabled else (20, 40, 30)
        border = (60, 200, 80) if enabled else _BORDER_LO
    pygame.draw.rect(surf, col, btn)
    pygame.draw.rect(surf, border, btn, 1)
    font = pygame.font.SysFont("monospace", 24, bold=True)
    ts   = font.render(label, True, WHITE)
    surf.blit(ts, ts.get_rect(center=btn.center))


def _wrap(text: str, max_w: int, font) -> list[str]:
    words  = text.split()
    lines  = []
    cur    = ""
    for w in words:
        test = (cur + " " + w).strip()
        if font.size(test)[0] <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines
