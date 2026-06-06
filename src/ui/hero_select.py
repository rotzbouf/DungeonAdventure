"""
Hero selection screen — shown when "LOAD HERO" or "CREATE NEW HERO" is clicked.

Returns one of:
  "load:{hero_id}"   — player clicked an existing hero card
  "create"           — player clicked CREATE NEW HERO
  "back"             — player clicked BACK / pressed ESC
  None               — still open
"""
from __future__ import annotations

import math
import pygame
from src.settings import SCREEN_WIDTH, SCREEN_HEIGHT
from src.locale import t, lang
from src.assets import assets
from src.hero_classes import HERO_CLASSES

_W, _H = SCREEN_WIDTH, SCREEN_HEIGHT
_CX    = _W // 2

_GOLD  = (220, 175,   0)
_WHITE = (252, 252, 252)
_DIM   = ( 90,  80, 120)
_BG    = (  8,   5,  18)
_PANEL = ( 18,  12,  35)
_BORD  = ( 72,  50, 120)
_BORD_HV = (220, 175, 0)
_RED   = (200,  50,  50)
_RED_HV = (240,  90,  90)

_CARD_W = 260
_CARD_H = 160
_CARD_GAP = 28
_CARDS_PER_ROW = 5
_CARD_AREA_Y = 220
_MAX_ROWS = 2    # scroll if more
_VIS_ROWS = 2


class HeroSelectScreen:
    def __init__(self):
        self._heroes: list[dict] = []
        self._scroll = 0          # in rows
        self._hovered: str | None = None
        self._delete_pending: str | None = None  # hero_id awaiting confirm
        self._time = 0.0
        self._result: str | None = None

        # Button rects populated in draw()
        self._back_rect:   pygame.Rect | None = None
        self._create_rect: pygame.Rect | None = None
        self._card_rects:  dict[str, pygame.Rect] = {}
        self._del_rects:   dict[str, pygame.Rect] = {}
        self._yes_rect:    pygame.Rect | None = None
        self._no_rect:     pygame.Rect | None = None

    def open(self, heroes: list[dict]):
        from src import save as savesys
        self._heroes = savesys.list_heroes()
        self._scroll = 0
        self._hovered = None
        self._delete_pending = None
        self._result = None

    def result(self) -> str | None:
        r = self._result
        self._result = None
        return r

    # ── Draw ──────────────────────────────────────────────────────────────────

    def draw(self, surf: pygame.Surface, t_val: float):
        self._time = t_val

        # Semi-transparent overlay over the menu background
        ov = pygame.Surface((surf.get_width(), surf.get_height()), pygame.SRCALPHA)
        ov.fill((8, 5, 18, 210))
        surf.blit(ov, (0, 0))

        fxl = pygame.font.SysFont("monospace", 52, bold=True)
        flg = pygame.font.SysFont("monospace", 30, bold=True)
        fmd = pygame.font.SysFont("monospace", 22)
        fsm = pygame.font.SysFont("monospace", 18)

        # ── Title ─────────────────────────────────────────────────────────────
        title_s = fxl.render(t("hero_select.title"), True, _GOLD)
        surf.blit(title_s, title_s.get_rect(center=(_CX, 80)))

        # ── Divider ───────────────────────────────────────────────────────────
        div_y = 130
        pygame.draw.line(surf, _BORD, (_CX - 400, div_y), (_CX - 14, div_y), 1)
        pygame.draw.polygon(surf, _GOLD,
                            [(_CX, div_y-7), (_CX+7, div_y), (_CX, div_y+7), (_CX-7, div_y)])
        pygame.draw.line(surf, _BORD, (_CX + 14, div_y), (_CX + 400, div_y), 1)

        # ── Hero cards ────────────────────────────────────────────────────────
        self._card_rects.clear()
        self._del_rects.clear()

        heroes = self._heroes
        total_rows = math.ceil(len(heroes) / _CARDS_PER_ROW) if heroes else 0
        vis_heroes = heroes[self._scroll * _CARDS_PER_ROW :
                            (self._scroll + _VIS_ROWS) * _CARDS_PER_ROW]

        area_x0 = _CX - (_CARDS_PER_ROW * (_CARD_W + _CARD_GAP) - _CARD_GAP) // 2

        for idx, hero in enumerate(vis_heroes):
            col = idx % _CARDS_PER_ROW
            row = idx // _CARDS_PER_ROW
            cx  = area_x0 + col * (_CARD_W + _CARD_GAP)
            cy  = _CARD_AREA_Y + row * (_CARD_H + _CARD_GAP)
            card_r = pygame.Rect(cx, cy, _CARD_W, _CARD_H)

            hid    = hero["hero_id"]
            hov    = card_r.collidepoint(pygame.mouse.get_pos())
            bg_col = (28, 20, 55) if hov else _PANEL
            bd_col = _BORD_HV if hov else _BORD

            pygame.draw.rect(surf, bg_col,  card_r, border_radius=8)
            pygame.draw.rect(surf, bd_col,  card_r, 2, border_radius=8)

            # Portrait (small, top-right of card)
            cls_data = HERO_CLASSES.get(hero["hero_class"], HERO_CLASSES["warrior"])
            portraits = cls_data["portraits"]
            race = next(iter(portraits))
            portrait = assets.portrait(portraits[race], hero["gender"], (64, 96))
            if portrait:
                surf.blit(portrait, (cx + _CARD_W - 72, cy + 8))

            # Hero name
            name_s = flg.render(hero["hero_name"], True, _GOLD if hov else _WHITE)
            surf.blit(name_s, (cx + 10, cy + 10))

            # Class label
            lk = "label_de" if lang() == "de" else "label"
            cls_lbl = cls_data.get(lk, cls_data["label"])
            cls_s = fmd.render(cls_lbl, True, _DIM)
            surf.blit(cls_s, (cx + 10, cy + 46))

            # Level / floor
            lv_s = fsm.render(t("hero_select.level", n=hero["level"]), True, _WHITE)
            fl_s = fsm.render(t("hero_select.floor", n=hero["dungeon_level"]), True, _DIM)
            surf.blit(lv_s, (cx + 10, cy + _CARD_H - 48))
            surf.blit(fl_s, (cx + 10, cy + _CARD_H - 28))

            # Delete button (×)
            del_r = pygame.Rect(cx + _CARD_W - 28, cy + 4, 24, 24)
            del_hov = del_r.collidepoint(pygame.mouse.get_pos())
            pygame.draw.rect(surf, (60, 20, 20) if del_hov else _PANEL, del_r, border_radius=4)
            pygame.draw.rect(surf, _RED_HV if del_hov else _RED, del_r, 1, border_radius=4)
            x_s = fsm.render("✕", True, _RED_HV if del_hov else _RED)
            surf.blit(x_s, x_s.get_rect(center=del_r.center))

            self._card_rects[hid] = card_r
            self._del_rects[hid]  = del_r

        # ── "No heroes" message ───────────────────────────────────────────────
        if not heroes:
            msg = fmd.render("No saved heroes.  Create your first hero!", True, _DIM)
            surf.blit(msg, msg.get_rect(center=(_CX, _CARD_AREA_Y + 80)))

        # ── Bottom buttons ────────────────────────────────────────────────────
        btn_y  = _H - 110
        BTN_W, BTN_H = 300, 54

        create_r = pygame.Rect(_CX - BTN_W - 20, btn_y, BTN_W, BTN_H)
        back_r   = pygame.Rect(_CX + 20,          btn_y, BTN_W, BTN_H)

        for r, lbl in [(create_r, t("hero_select.create")),
                       (back_r,   t("hero_select.back"))]:
            hov = r.collidepoint(pygame.mouse.get_pos())
            pygame.draw.rect(surf, (48, 34, 78) if hov else _PANEL, r, border_radius=8)
            pygame.draw.rect(surf, _BORD_HV if hov else _BORD, r, 2, border_radius=8)
            ls  = flg.render(lbl, True, _GOLD if hov else _WHITE)
            surf.blit(ls, ls.get_rect(center=r.center))

        self._create_rect = create_r
        self._back_rect   = back_r

        # ── Delete confirmation modal ──────────────────────────────────────────
        if self._delete_pending:
            hero_data = next((h for h in heroes
                              if h["hero_id"] == self._delete_pending), None)
            name = hero_data["hero_name"] if hero_data else "?"
            self._draw_confirm(surf, flg, fmd, name)

    def _draw_confirm(self, surf, flg, fmd, name: str):
        # Dim overlay
        ov = pygame.Surface((_W, _H), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 160))
        surf.blit(ov, (0, 0))

        box_w, box_h = 560, 200
        box = pygame.Rect(_CX - box_w // 2, _H // 2 - box_h // 2, box_w, box_h)
        pygame.draw.rect(surf, _PANEL, box, border_radius=12)
        pygame.draw.rect(surf, _BORD,  box, 2, border_radius=12)

        msg = t("hero_select.confirm_delete", name=name)
        ms  = fmd.render(msg, True, _WHITE)
        surf.blit(ms, ms.get_rect(center=(_CX, box.top + 60)))

        yes_r = pygame.Rect(_CX - 230, box.top + 110, 200, 48)
        no_r  = pygame.Rect(_CX + 30,  box.top + 110, 200, 48)

        for r, lbl, base_col in [(yes_r, t("hero_select.yes"), _RED),
                                  (no_r,  t("hero_select.no"),  _BORD)]:
            hov = r.collidepoint(pygame.mouse.get_pos())
            bg  = (60, 20, 20) if (hov and base_col == _RED) else \
                  (48, 34, 78) if hov else _PANEL
            pygame.draw.rect(surf, bg, r, border_radius=8)
            pygame.draw.rect(surf, _RED_HV if (hov and base_col == _RED) else \
                             (_BORD_HV if hov else base_col), r, 2, border_radius=8)
            ls = fmd.render(lbl, True, _WHITE)
            surf.blit(ls, ls.get_rect(center=r.center))

        self._yes_rect = yes_r
        self._no_rect  = no_r

    # ── Events ────────────────────────────────────────────────────────────────

    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self._delete_pending:
                    self._delete_pending = None
                else:
                    self._result = "back"

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos

            # Confirm modal buttons
            if self._delete_pending:
                if self._yes_rect and self._yes_rect.collidepoint(pos):
                    from src import save as savesys
                    savesys.delete_hero(self._delete_pending)
                    self._delete_pending = None
                    self._heroes = savesys.list_heroes()
                elif self._no_rect and self._no_rect.collidepoint(pos):
                    self._delete_pending = None
                return

            # Delete buttons (check before card so the × eats the click)
            for hid, del_r in self._del_rects.items():
                if del_r.collidepoint(pos):
                    self._delete_pending = hid
                    return

            # Hero cards
            for hid, card_r in self._card_rects.items():
                if card_r.collidepoint(pos):
                    self._result = f"load:{hid}"
                    return

            # Bottom buttons
            if self._create_rect and self._create_rect.collidepoint(pos):
                self._result = "create"
            elif self._back_rect and self._back_rect.collidepoint(pos):
                self._result = "back"
