"""Player homestead screen — stash chest, manual save and load."""
from __future__ import annotations
import pygame
from src.settings import SCREEN_WIDTH, SCREEN_HEIGHT, HUD_HEIGHT, WHITE
from src import save as savesys

# ── Palette ───────────────────────────────────────────────────────────────────
_BG        = (10,   7,   4)
_PANEL     = (18,  13,   8)
_BORDER    = (160, 110,  50)
_BORDER_LO = ( 80,  55,  25)
_HDR       = (230, 185,  80)
_SEL       = ( 50,  34,  14)
_DIM       = (110,  90,  60)
_GREEN     = ( 60, 200,  80)
_RED       = (200,  50,  50)

_Q_COLOR = {
    0: (188, 188, 188),
    1: ( 80,  80, 255),
    2: (252, 188,   0),
    3: (200, 115,   0),
}

_STASH_LIMIT = 80


class HouseScreen:
    W = 1100
    H = 680

    def __init__(self):
        self._fl = pygame.font.SysFont("monospace", 28, bold=True)
        self._fm = pygame.font.SysFont("monospace", 25, bold=True)
        self._fs = pygame.font.SysFont("monospace", 25)

        self._stash_scroll = 0
        self._pack_scroll  = 0
        self._msg          = ""
        self._msg_timer    = 0.0
        self._msg_ok       = True
        self._save_fn      = None
        self._load_fn      = None

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

    def handle_event(self, event: pygame.event.Event, player) -> bool:
        ox = SCREEN_WIDTH  // 2 - self.W // 2
        oy = (SCREEN_HEIGHT - HUD_HEIGHT) // 2 - self.H // 2

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            lx, ly = event.pos[0] - ox, event.pos[1] - oy
            self._handle_click(lx, ly, player)
            return True

        if event.type == pygame.MOUSEWHEEL:
            lx = pygame.mouse.get_pos()[0] - ox
            if lx < self.W // 2:
                self._stash_scroll = max(0, self._stash_scroll - event.y)
            else:
                self._pack_scroll = max(0, self._pack_scroll - event.y)
            return True

        return False

    # ─── Internal click handling ──────────────────────────────────────────────

    def _handle_click(self, lx: int, ly: int, player):
        hdr_h    = 62
        pad      = 14
        row_h    = 36
        split_x  = self.W // 2
        list_y0  = hdr_h + pad
        clip_h   = self.H - 80 - list_y0

        # ── Left panel: stash items ───────────────────────────────────────────
        if lx < split_x:
            stash = getattr(player, "stash", [])
            for i, item in enumerate(stash):
                iy = list_y0 + (i - self._stash_scroll) * row_h
                if list_y0 <= iy <= list_y0 + clip_h - row_h:
                    if iy <= ly <= iy + row_h - 2:
                        player.backpack.append(item)
                        player.stash.remove(item)
                        self._notify(f"Took {_item_name(item)}.", ok=True)
                        return

        # ── Right panel: backpack items ───────────────────────────────────────
        if lx >= split_x:
            for i, item in enumerate(player.backpack):
                iy = list_y0 + (i - self._pack_scroll) * row_h
                if list_y0 <= iy <= list_y0 + clip_h - row_h:
                    if iy <= ly <= iy + row_h - 2:
                        stash = getattr(player, "stash", [])
                        if len(stash) >= _STASH_LIMIT:
                            self._notify("Chest is full!", ok=False)
                            return
                        player.stash = stash
                        player.stash.append(item)
                        player.backpack.remove(item)
                        self._notify(f"Stored {_item_name(item)}.", ok=True)
                        return

        # ── Footer buttons ────────────────────────────────────────────────────
        if self._save_btn_rect().collidepoint(lx, ly):
            if self._save_fn:
                self._save_fn()
                self._notify("Game saved!", ok=True)
        elif self._load_btn_rect().collidepoint(lx, ly):
            if savesys.has_save() and self._load_fn:
                self._load_fn()

    def _save_btn_rect(self) -> pygame.Rect:
        bw, bh = 200, 38
        return pygame.Rect(self.W // 4 - bw // 2, self.H - 58, bw, bh)

    def _load_btn_rect(self) -> pygame.Rect:
        bw, bh = 200, 38
        return pygame.Rect(3 * self.W // 4 - bw // 2, self.H - 58, bw, bh)

    def _notify(self, msg: str, ok: bool = True):
        self._msg       = msg
        self._msg_ok    = ok
        self._msg_timer = 3.0

    # ─── Draw ─────────────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface, player):
        ox = SCREEN_WIDTH  // 2 - self.W // 2
        oy = (SCREEN_HEIGHT - HUD_HEIGHT) // 2 - self.H // 2

        # Dim backdrop
        ov = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT - HUD_HEIGHT), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 185))
        surface.blit(ov, (0, 0))

        panel = pygame.Surface((self.W, self.H))
        panel.fill(_BG)
        pygame.draw.rect(panel, _BORDER, (0, 0, self.W, self.H), 2)

        self._draw_header(panel)
        pygame.draw.line(panel, _BORDER_LO,
                         (self.W // 2, 62), (self.W // 2, self.H - 80), 1)
        self._draw_stash(panel, player)
        self._draw_backpack(panel, player)
        self._draw_footer(panel, player)

        surface.blit(panel, (ox, oy))

    def _draw_header(self, surf: pygame.Surface):
        pygame.draw.rect(surf, _PANEL, (0, 0, self.W, 62))
        pygame.draw.line(surf, _BORDER, (0, 62), (self.W, 62), 1)
        title = self._fl.render("YOUR  HOMESTEAD", True, _HDR)
        surf.blit(title, title.get_rect(centerx=self.W // 2, centery=31))

    def _draw_stash(self, surf: pygame.Surface, player):
        pad      = 14
        row_h    = 36
        list_y0  = 62 + pad
        clip_h   = self.H - 80 - list_y0
        split_x  = self.W // 2

        hdr = self._fm.render("CHEST  STORAGE", True, _HDR)
        surf.blit(hdr, (pad, 65))

        stash = getattr(player, "stash", [])
        if not stash:
            s = self._fs.render(
                "Chest is empty  —  click backpack items to store them", True, _DIM)
            surf.blit(s, (pad, list_y0 + 20))
        else:
            for i, item in enumerate(stash):
                iy = list_y0 + (i - self._stash_scroll) * row_h
                if iy < list_y0 or iy > list_y0 + clip_h - row_h:
                    continue
                bg = _SEL if i % 2 == 0 else _PANEL
                pygame.draw.rect(surf, bg,
                                 (pad - 2, iy, split_x - pad * 2, row_h - 2))
                col = _q_col(item)
                ns  = self._fm.render(_item_name(item), True, col)
                surf.blit(ns, (pad + 4, iy + 8))
                hint = self._fs.render("click to take", True, _DIM)
                surf.blit(hint,
                          (split_x - pad - hint.get_width() - 4, iy + 12))

        count_s = self._fs.render(
            f"{len(stash)} / {_STASH_LIMIT} items stored", True, _DIM)
        surf.blit(count_s, (pad, self.H - 80 - 18))

    def _draw_backpack(self, surf: pygame.Surface, player):
        pad      = 14
        row_h    = 36
        list_y0  = 62 + pad
        clip_h   = self.H - 80 - list_y0
        split_x  = self.W // 2
        px       = split_x + pad

        hdr = self._fm.render("YOUR  BACKPACK", True, _HDR)
        surf.blit(hdr, (px, 65))

        if not player.backpack:
            s = self._fs.render("Backpack is empty", True, _DIM)
            surf.blit(s, (px, list_y0 + 20))
            return

        for i, item in enumerate(player.backpack):
            iy = list_y0 + (i - self._pack_scroll) * row_h
            if iy < list_y0 or iy > list_y0 + clip_h - row_h:
                continue
            bg = _SEL if i % 2 == 0 else _PANEL
            pygame.draw.rect(surf, bg,
                             (px - 2, iy, self.W - split_x - pad, row_h - 2))
            col = _q_col(item)
            ns  = self._fm.render(_item_name(item), True, col)
            surf.blit(ns, (px + 4, iy + 8))
            hint = self._fs.render("click to store", True, _DIM)
            surf.blit(hint,
                      (self.W - pad - hint.get_width() - 4, iy + 12))

    def _draw_footer(self, surf: pygame.Surface, player):
        fy  = self.H - 80
        pad = 14
        pygame.draw.line(surf, _BORDER_LO, (0, fy), (self.W, fy), 1)

        # Feedback message
        if self._msg and self._msg_timer > 0:
            fade = min(1.0, self._msg_timer / 0.4)
            col  = tuple(int(c * fade) for c in (_GREEN if self._msg_ok else _RED))
            ms   = self._fm.render(self._msg, True, col)
            surf.blit(ms, ms.get_rect(centerx=self.W // 2, centery=fy + 22))

        # Save button (always enabled)
        _draw_btn(surf, self._save_btn_rect(), "SAVE GAME",
                  enabled=True,
                  col=(28, 78, 18), border=(55, 175, 38),
                  col_off=(14, 38, 9), border_off=_BORDER_LO)

        # Load button (greyed out when no save exists)
        has_sv = savesys.has_save()
        _draw_btn(surf, self._load_btn_rect(), "LOAD GAME",
                  enabled=has_sv,
                  col=(20, 40, 82), border=(48, 100, 210),
                  col_off=(10, 20, 42), border_off=_BORDER_LO)

        # Hint
        hs = self._fs.render(
            "Click items to move between chest and backpack  ·  ESC to close",
            True, _DIM)
        surf.blit(hs, hs.get_rect(centerx=self.W // 2, centery=self.H - 10))


# ── Helpers ───────────────────────────────────────────────────────────────────

def _item_name(item) -> str:
    from src.items.item import EquipItem, HealthPotion
    if isinstance(item, EquipItem):
        return item.display_name
    if isinstance(item, HealthPotion):
        return f"Health Potion (+{item.heal_amount})"
    return str(item)


def _q_col(item) -> tuple:
    from src.items.item import EquipItem
    if isinstance(item, EquipItem):
        return _Q_COLOR.get(item.quality, (188, 188, 188))
    return (160, 220, 160)


def _draw_btn(surf, btn, label, enabled,
              col, border, col_off, border_off):
    c = col if enabled else col_off
    b = border if enabled else border_off
    pygame.draw.rect(surf, c, btn)
    pygame.draw.rect(surf, b, btn, 1)
    font = pygame.font.SysFont("monospace", 24, bold=True)
    col_txt = WHITE if enabled else _DIM
    ts = font.render(label, True, col_txt)
    surf.blit(ts, ts.get_rect(center=btn.center))
