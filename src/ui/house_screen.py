"""Player homestead screen — stash chest, manual save and load."""
from __future__ import annotations
import math
import pygame
from src.settings import SCREEN_WIDTH, SCREEN_HEIGHT, HUD_HEIGHT, WHITE
from src.ui.pager import draw_pager
from src.items.item import EquipItem, HealthPotion, Q_COLOR, QUALITY_NORMAL
from src import save as savesys

# ── Palette ───────────────────────────────────────────────────────────────────
_BG        = (10,   7,   4)
_PANEL     = (18,  13,   8)
_BORDER    = (160, 110,  50)
_BORDER_LO = ( 80,  55,  25)
_HDR       = (230, 185,  80)
_DIM       = (110,  90,  60)
_GREEN     = ( 60, 200,  80)
_RED       = (200,  50,  50)
_POTION_COL = (60, 200, 100)
_SLOT_COL   = (32,  24,  14)
_SLOT_H_COL = (55,  42,  22)
_SLOT_SEP   = (55,  42,  22)

# ── Grid constants ────────────────────────────────────────────────────────────
_CELL   = 62
_GAP    = 6
_STRIDE = _CELL + _GAP   # 68 px per cell

_ST_COLS = 8    # stash: 8 cols × 10 rows = 80 slots
_PK_COLS = 5    # backpack: 5 cols × 10 rows = 50 slots
_ST_CAP  = 80
_PK_CAP  = 50

_HDR_H        = 52    # title bar height
_FOOT_H       = 68    # footer height
_PAD          = 12
_GRID_Y0      = _HDR_H + 24   # grid rows start here (below sub-header label)
_PAGER_RESERVE = 32   # vertical space reserved below each grid for pager buttons


def _vis_rows(panel_h: int) -> int:
    available = panel_h - _FOOT_H - _GRID_Y0 - _PAGER_RESERVE
    return available // _STRIDE


class HouseScreen:
    W = 1200
    H = 760

    def __init__(self):
        self._fl  = pygame.font.SysFont("monospace", 26, bold=True)
        self._fm  = pygame.font.SysFont("monospace", 21, bold=True)
        self._fs  = pygame.font.SysFont("monospace", 19)
        self._fxs = pygame.font.SysFont("monospace", 15, bold=True)

        self._vis = _vis_rows(self.H)   # 8 (reserves 32 px below each grid for pager)
        self._stash_scroll = 0
        self._pack_scroll  = 0
        self._hov_stash    = -1
        self._hov_pack     = -1
        self._stash_prev: pygame.Rect | None = None
        self._stash_next: pygame.Rect | None = None
        self._pack_prev:  pygame.Rect | None = None
        self._pack_next:  pygame.Rect | None = None
        self._msg          = ""
        self._msg_timer    = 0.0
        self._msg_ok       = True
        self._save_fn      = None
        self._load_fn      = None

    # ── Public API ────────────────────────────────────────────────────────────

    def open(self, save_fn=None, load_fn=None):
        self._stash_scroll = 0
        self._pack_scroll  = 0
        self._msg          = ""
        self._msg_timer    = 0.0
        self._save_fn      = save_fn
        self._load_fn      = load_fn

    def update(self, dt: float):
        if self._msg_timer > 0:
            self._msg_timer = max(0.0, self._msg_timer - dt)

        # Update hover from current mouse pos
        ox, oy = self._origin()
        mx, my = pygame.mouse.get_pos()
        lx, ly = mx - ox, my - oy
        self._hov_stash = self._stash_idx_at(lx, ly)
        self._hov_pack  = self._pack_idx_at(lx, ly)

    def handle_event(self, event: pygame.event.Event, player) -> bool:
        ox, oy = self._origin()

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            lx, ly = event.pos[0] - ox, event.pos[1] - oy
            self._handle_click(lx, ly, player)
            return True

        if event.type == pygame.MOUSEWHEEL:
            lx = pygame.mouse.get_pos()[0] - ox
            stash_rows = math.ceil(_ST_CAP / _ST_COLS)
            pack_rows  = math.ceil(_PK_CAP / _PK_COLS)
            if lx < self.W // 2:
                ms = max(0, stash_rows - self._vis)
                self._stash_scroll = max(0, min(self._stash_scroll - event.y, ms))
            else:
                ms = max(0, pack_rows - self._vis)
                self._pack_scroll = max(0, min(self._pack_scroll - event.y, ms))
            return True

        return False

    # ── Geometry helpers ──────────────────────────────────────────────────────

    def _origin(self) -> tuple[int, int]:
        ox = SCREEN_WIDTH  // 2 - self.W // 2
        oy = (SCREEN_HEIGHT - HUD_HEIGHT) // 2 - self.H // 2
        return ox, oy

    def _stash_cell_rect(self, idx: int) -> pygame.Rect:
        col = idx % _ST_COLS
        row = idx // _ST_COLS
        x   = _PAD + col * _STRIDE
        y   = _GRID_Y0 + (row - self._stash_scroll) * _STRIDE
        return pygame.Rect(x, y, _CELL, _CELL)

    def _pack_cell_rect(self, idx: int) -> pygame.Rect:
        col = idx % _PK_COLS
        row = idx // _PK_COLS
        x   = self.W // 2 + _PAD + col * _STRIDE
        y   = _GRID_Y0 + (row - self._pack_scroll) * _STRIDE
        return pygame.Rect(x, y, _CELL, _CELL)

    def _grid_clip_left(self) -> pygame.Rect:
        grid_h = self._vis * _STRIDE - _GAP
        return pygame.Rect(_PAD, _GRID_Y0, self.W // 2 - _PAD, grid_h)

    def _grid_clip_right(self) -> pygame.Rect:
        grid_h = self._vis * _STRIDE - _GAP
        rx = self.W // 2 + _PAD
        return pygame.Rect(rx, _GRID_Y0, self.W - rx - _PAD, grid_h)

    def _stash_idx_at(self, lx: int, ly: int) -> int:
        clip = self._grid_clip_left()
        if not clip.collidepoint(lx, ly):
            return -1
        for i in range(_ST_CAP):
            if self._stash_cell_rect(i).collidepoint(lx, ly):
                return i
        return -1

    def _pack_idx_at(self, lx: int, ly: int) -> int:
        clip = self._grid_clip_right()
        if not clip.collidepoint(lx, ly):
            return -1
        for i in range(_PK_CAP):
            if self._pack_cell_rect(i).collidepoint(lx, ly):
                return i
        return -1

    # ── Click handling ────────────────────────────────────────────────────────

    def _handle_click(self, lx: int, ly: int, player):
        stash = getattr(player, "stash", [])

        # ── Pager buttons ─────────────────────────────────────────────────────
        stash_rows = math.ceil(_ST_CAP / _ST_COLS)
        pack_rows  = math.ceil(_PK_CAP / _PK_COLS)
        max_st = max(0, stash_rows - self._vis)
        max_pk = max(0, pack_rows  - self._vis)
        if self._stash_prev and self._stash_prev.collidepoint(lx, ly):
            self._stash_scroll = max(0, self._stash_scroll - self._vis)
            return
        if self._stash_next and self._stash_next.collidepoint(lx, ly):
            self._stash_scroll = min(max_st, self._stash_scroll + self._vis)
            return
        if self._pack_prev and self._pack_prev.collidepoint(lx, ly):
            self._pack_scroll = max(0, self._pack_scroll - self._vis)
            return
        if self._pack_next and self._pack_next.collidepoint(lx, ly):
            self._pack_scroll = min(max_pk, self._pack_scroll + self._vis)
            return

        # Stash → take item into backpack
        si = self._stash_idx_at(lx, ly)
        if si >= 0 and si < len(stash):
            item = stash[si]
            if player.inventory_full():
                self._notify("Backpack is full!", ok=False)
                return
            player.backpack.append(item)
            player.stash.remove(item)
            self._notify(f"Took {_item_name(item)}.", ok=True)
            return

        # Backpack → store item in stash
        pi = self._pack_idx_at(lx, ly)
        if pi >= 0 and pi < len(player.backpack):
            item = player.backpack[pi]
            if len(stash) >= _ST_CAP:
                self._notify("Chest is full!", ok=False)
                return
            player.stash = stash
            player.stash.append(item)
            player.backpack.remove(item)
            self._notify(f"Stored {_item_name(item)}.", ok=True)
            return

        # Footer buttons
        if self._save_btn_rect().collidepoint(lx, ly):
            if self._save_fn:
                self._save_fn()
                self._notify("Game saved!", ok=True)
        elif self._load_btn_rect().collidepoint(lx, ly):
            if savesys.has_save() and self._load_fn:
                self._load_fn()

    def _save_btn_rect(self) -> pygame.Rect:
        bw, bh = 200, 36
        return pygame.Rect(self.W // 4 - bw // 2, self.H - 52, bw, bh)

    def _load_btn_rect(self) -> pygame.Rect:
        bw, bh = 200, 36
        return pygame.Rect(3 * self.W // 4 - bw // 2, self.H - 52, bw, bh)

    def _notify(self, msg: str, ok: bool = True):
        self._msg       = msg
        self._msg_ok    = ok
        self._msg_timer = 3.0

    # ── Draw ──────────────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface, player):
        ox, oy = self._origin()

        ov = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT - HUD_HEIGHT), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 185))
        surface.blit(ov, (0, 0))

        panel = pygame.Surface((self.W, self.H))
        panel.fill(_BG)
        pygame.draw.rect(panel, _BORDER, (0, 0, self.W, self.H), 2)

        self._draw_header(panel)
        pygame.draw.line(panel, _BORDER_LO,
                         (self.W // 2, _HDR_H), (self.W // 2, self.H - _FOOT_H), 1)
        self._draw_stash(panel, player)
        self._draw_backpack(panel, player)
        self._draw_footer(panel)

        surface.blit(panel, (ox, oy))

    def _draw_header(self, surf: pygame.Surface):
        pygame.draw.rect(surf, _PANEL, (0, 0, self.W, _HDR_H))
        pygame.draw.line(surf, _BORDER, (0, _HDR_H), (self.W, _HDR_H), 1)
        title = self._fl.render("YOUR  HOMESTEAD", True, _HDR)
        surf.blit(title, title.get_rect(centerx=self.W // 2, centery=_HDR_H // 2))

    # ── Stash grid ────────────────────────────────────────────────────────────

    def _draw_stash(self, surf: pygame.Surface, player):
        stash = getattr(player, "stash", [])

        # Sub-header
        hdr = self._fm.render(f"CHEST STORAGE  —  {len(stash)} / {_ST_CAP}", True, _HDR)
        surf.blit(hdr, (_PAD, _HDR_H + 4))

        clip = self._grid_clip_left()
        old  = surf.get_clip()
        surf.set_clip(clip)

        for i in range(_ST_CAP):
            r   = self._stash_cell_rect(i)
            if r.bottom <= clip.top or r.top >= clip.bottom:
                continue
            hov = (i == self._hov_stash)
            pygame.draw.rect(surf, _SLOT_H_COL if hov else _SLOT_COL, r)

            if i < len(stash):
                self._draw_cell_item(surf, r, stash[i], hov)
            else:
                pygame.draw.rect(surf, _SLOT_SEP, r, 1)

        surf.set_clip(old)
        self._draw_pager_grid(surf, _ST_CAP, _ST_COLS, self._stash_scroll,
                              self._grid_clip_left(), "_stash_prev", "_stash_next")

    # ── Backpack grid ─────────────────────────────────────────────────────────

    def _draw_backpack(self, surf: pygame.Surface, player):
        pack = player.backpack

        # Sub-header
        rx  = self.W // 2 + _PAD
        hdr = self._fm.render(f"YOUR BACKPACK  —  {len(pack)} / {_PK_CAP}", True, _HDR)
        surf.blit(hdr, (rx, _HDR_H + 4))

        clip = self._grid_clip_right()
        old  = surf.get_clip()
        surf.set_clip(clip)

        for i in range(_PK_CAP):
            r   = self._pack_cell_rect(i)
            if r.bottom <= clip.top or r.top >= clip.bottom:
                continue
            hov = (i == self._hov_pack)
            pygame.draw.rect(surf, _SLOT_H_COL if hov else _SLOT_COL, r)

            if i < len(pack):
                self._draw_cell_item(surf, r, pack[i], hov)
            else:
                pygame.draw.rect(surf, _SLOT_SEP, r, 1)

        surf.set_clip(old)
        self._draw_pager_grid(surf, _PK_CAP, _PK_COLS, self._pack_scroll,
                              self._grid_clip_right(), "_pack_prev", "_pack_next")

    # ── Cell renderer (shared) ────────────────────────────────────────────────

    def _draw_cell_item(self, surf: pygame.Surface, r: pygame.Rect, item, hov: bool):
        if isinstance(item, EquipItem):
            bc = item.quality_color
            pygame.draw.rect(surf, bc, r,
                             1 if item.quality == QUALITY_NORMAL else 2)
            icon_rect = r.inflate(-12, -12)
            try:
                from src.assets import assets
                spr = assets.item_sprite(item.base_name,
                                         size=(icon_rect.width, icon_rect.height))
                if spr:
                    surf.blit(spr, icon_rect.topleft)
                elif item.slot == "weapon":
                    item._draw_weapon_icon(surf, icon_rect, bc)
                else:
                    item._draw_armor_icon(surf, icon_rect, bc)
            except Exception:
                if item.slot == "weapon":
                    item._draw_weapon_icon(surf, icon_rect, bc)
                else:
                    item._draw_armor_icon(surf, icon_rect, bc)

            # Quality badge (top-right corner)
            badge = {1: "M", 2: "R", 3: "U"}.get(item.quality, "")
            if badge:
                bs = self._fxs.render(badge, True, item.quality_color)
                surf.blit(bs, (r.right - bs.get_width() - 2, r.top + 2))

        elif isinstance(item, HealthPotion):
            pygame.draw.rect(surf, _POTION_COL, r, 1)
            lbl = self._fs.render("HP", True, _POTION_COL)
            surf.blit(lbl, lbl.get_rect(center=r.center))

    # ── Page controls ─────────────────────────────────────────────────────────

    def _draw_pager_grid(self, surf, cap, cols, scroll, clip_rect, btn_prev_attr, btn_next_attr):
        total_rows  = math.ceil(cap / cols)
        total_pages = max(1, math.ceil(total_rows / self._vis))
        page        = scroll // self._vis + 1
        cx          = clip_rect.centerx
        y           = clip_rect.bottom + 5
        prev_r, next_r = draw_pager(surf, cx, y, page, total_pages, self._fxs)
        setattr(self, btn_prev_attr, prev_r)
        setattr(self, btn_next_attr, next_r)

    # ── Footer ────────────────────────────────────────────────────────────────

    def _draw_footer(self, surf: pygame.Surface):
        fy = self.H - _FOOT_H
        pygame.draw.line(surf, _BORDER_LO, (0, fy), (self.W, fy), 1)

        if self._msg and self._msg_timer > 0:
            fade = min(1.0, self._msg_timer / 0.4)
            col  = tuple(int(c * fade) for c in (_GREEN if self._msg_ok else _RED))
            ms   = self._fm.render(self._msg, True, col)
            surf.blit(ms, ms.get_rect(centerx=self.W // 2, centery=fy + 18))

        _draw_btn(surf, self._save_btn_rect(), "SAVE GAME",
                  enabled=True,
                  col=(28, 78, 18), border=(55, 175, 38),
                  col_off=(14, 38, 9), border_off=_BORDER_LO)

        has_sv = savesys.has_save()
        _draw_btn(surf, self._load_btn_rect(), "LOAD GAME",
                  enabled=has_sv,
                  col=(20, 40, 82), border=(48, 100, 210),
                  col_off=(10, 20, 42), border_off=_BORDER_LO)

        hs = self._fs.render(
            "Click items to move between chest and backpack  ·  ESC to close",
            True, _DIM)
        surf.blit(hs, hs.get_rect(centerx=self.W // 2, centery=self.H - 10))


# ── Helpers ───────────────────────────────────────────────────────────────────

def _item_name(item) -> str:
    if isinstance(item, EquipItem):
        return item.display_name
    if isinstance(item, HealthPotion):
        return f"Health Potion (+{item.heal_amount})"
    return str(item)


def _draw_btn(surf, btn, label, enabled,
              col, border, col_off, border_off):
    c = col if enabled else col_off
    b = border if enabled else border_off
    pygame.draw.rect(surf, c, btn)
    pygame.draw.rect(surf, b, btn, 1)
    font = pygame.font.SysFont("monospace", 22, bold=True)
    ts = font.render(label, True, WHITE if enabled else _DIM)
    surf.blit(ts, ts.get_rect(center=btn.center))
