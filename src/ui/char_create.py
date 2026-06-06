"""
Character creation screen — name input, class selection, gender toggle, portrait preview.

Returns one of:
  ("confirm", name, cls_id, gender, race)  — player clicked CREATE
  "back"                                    — player clicked BACK / pressed ESC
  None                                      — still open
"""
from __future__ import annotations

import pygame
from src.settings import SCREEN_WIDTH, SCREEN_HEIGHT
from src.locale import t, lang
from src.assets import assets
from src.hero_classes import HERO_CLASSES, CLASS_ORDER

_W, _H = SCREEN_WIDTH, SCREEN_HEIGHT
_CX    = _W // 2

_GOLD   = (220, 175,   0)
_WHITE  = (252, 252, 252)
_DIM    = ( 90,  80, 120)
_BG     = (  8,   5,  18)
_PANEL  = ( 18,  12,  35)
_BORD   = ( 72,  50, 120)
_BORD_HV= (220, 175,   0)
_ERR    = (220,  60,  60)
_GREEN  = ( 80, 200,  80)

_MAX_NAME = 20


class CharCreateScreen:
    def __init__(self):
        self._name:    str = ""
        self._cls_idx: int = 0       # index into CLASS_ORDER
        self._gender:  str = "male"
        self._race_idx: int = 0      # index into current class portrait races
        self._error:   str = ""
        self._result            = None
        self._input_active: bool = True

        # Rects populated in draw()
        self._cls_rects:    list[pygame.Rect] = []
        self._gender_rects: dict[str, pygame.Rect] = {}
        self._race_rects:   list[pygame.Rect] = []
        self._confirm_rect: pygame.Rect | None = None
        self._back_rect:    pygame.Rect | None = None

    def open(self):
        self._name       = ""
        self._cls_idx    = 0
        self._gender     = "male"
        self._race_idx   = 0
        self._error      = ""
        self._result     = None
        self._input_active = True

    def result(self):
        r = self._result
        self._result = None
        return r

    def _current_cls(self) -> str:
        return CLASS_ORDER[self._cls_idx]

    def _current_races(self) -> list[str]:
        cls_data = HERO_CLASSES[self._current_cls()]
        return list(cls_data["portraits"].keys())

    def _current_race(self) -> str:
        races = self._current_races()
        if not races:
            return "human"
        idx = min(self._race_idx, len(races) - 1)
        return races[idx]

    # ── Draw ──────────────────────────────────────────────────────────────────

    def draw(self, surf: pygame.Surface):
        # Semi-transparent overlay over the animated menu background
        ov = pygame.Surface((surf.get_width(), surf.get_height()), pygame.SRCALPHA)
        ov.fill((8, 5, 18, 210))
        surf.blit(ov, (0, 0))

        fxl = pygame.font.SysFont("monospace", 52, bold=True)
        flg = pygame.font.SysFont("monospace", 30, bold=True)
        fmd = pygame.font.SysFont("monospace", 22)
        fsm = pygame.font.SysFont("monospace", 18)

        # ── Title ─────────────────────────────────────────────────────────────
        title_s = fxl.render(t("char_create.title"), True, _GOLD)
        surf.blit(title_s, title_s.get_rect(center=(_CX, 70)))

        div_y = 120
        pygame.draw.line(surf, _BORD, (_CX - 400, div_y), (_CX - 14, div_y), 1)
        pygame.draw.polygon(surf, _GOLD,
                            [(_CX, div_y-7), (_CX+7, div_y), (_CX, div_y+7), (_CX-7, div_y)])
        pygame.draw.line(surf, _BORD, (_CX + 14, div_y), (_CX + 400, div_y), 1)

        # Layout: left panel (form) | right panel (portrait + stats)
        form_x = 200
        right_x = _CX + 60

        # ── Name input ────────────────────────────────────────────────────────
        lbl = fmd.render(t("char_create.name") + ":", True, _DIM)
        surf.blit(lbl, (form_x, 155))

        input_r = pygame.Rect(form_x, 182, 500, 46)
        bord_col = _BORD_HV if self._input_active else _BORD
        pygame.draw.rect(surf, _PANEL, input_r, border_radius=6)
        pygame.draw.rect(surf, bord_col, input_r, 2, border_radius=6)

        display = self._name
        if self._input_active and (pygame.time.get_ticks() // 500) % 2 == 0:
            display += "|"
        name_s = flg.render(display, True, _WHITE)
        surf.blit(name_s, (input_r.x + 10, input_r.y + 8))

        # ── Class tabs ────────────────────────────────────────────────────────
        cls_lbl_s = fmd.render(t("char_create.class") + ":", True, _DIM)
        surf.blit(cls_lbl_s, (form_x, 252))

        self._cls_rects = []
        TAB_W, TAB_H, TAB_GAP = 150, 46, 10
        for i, cls_id in enumerate(CLASS_ORDER):
            cls_data = HERO_CLASSES[cls_id]
            lk = "label_de" if lang() == "de" else "label"
            lbl_text = cls_data.get(lk, cls_data["label"])
            rx = form_x + i * (TAB_W + TAB_GAP)
            ry = 282
            r  = pygame.Rect(rx, ry, TAB_W, TAB_H)
            selected = (i == self._cls_idx)
            hov = r.collidepoint(pygame.mouse.get_pos())
            bg  = (48, 34, 78) if selected else ((28, 20, 55) if hov else _PANEL)
            bd  = _BORD_HV if selected else (_BORD_HV if hov else _BORD)
            pygame.draw.rect(surf, bg, r, border_radius=6)
            pygame.draw.rect(surf, bd, r, 2, border_radius=6)
            ts = fmd.render(lbl_text, True, _GOLD if selected else (_WHITE if hov else _DIM))
            surf.blit(ts, ts.get_rect(center=r.center))
            self._cls_rects.append(r)

        # Class description
        cls_data = HERO_CLASSES[self._current_cls()]
        dk = "desc_de" if lang() == "de" else "desc"
        desc = cls_data.get(dk, cls_data["desc"])
        desc_s = fsm.render(desc, True, _DIM)
        surf.blit(desc_s, (form_x, 340))

        # ── Gender toggle ─────────────────────────────────────────────────────
        gen_lbl_s = fmd.render(t("char_create.gender") + ":", True, _DIM)
        surf.blit(gen_lbl_s, (form_x, 385))

        self._gender_rects = {}
        GEN_W, GEN_H = 130, 42
        for gi, (gid, glbl_key) in enumerate([("male", "char_create.male"),
                                               ("female", "char_create.female")]):
            rx = form_x + gi * (GEN_W + 10)
            r  = pygame.Rect(rx, 415, GEN_W, GEN_H)
            sel = (self._gender == gid)
            hov = r.collidepoint(pygame.mouse.get_pos())
            bg  = (48, 34, 78) if sel else ((28, 20, 55) if hov else _PANEL)
            bd  = _BORD_HV if sel else (_BORD_HV if hov else _BORD)
            pygame.draw.rect(surf, bg, r, border_radius=6)
            pygame.draw.rect(surf, bd, r, 2, border_radius=6)
            ts = fmd.render(t(glbl_key), True, _GOLD if sel else (_WHITE if hov else _DIM))
            surf.blit(ts, ts.get_rect(center=r.center))
            self._gender_rects[gid] = r

        # ── Race selector ─────────────────────────────────────────────────────
        races = self._current_races()
        if len(races) > 1:
            race_lbl_s = fmd.render("Appearance:", True, _DIM)
            surf.blit(race_lbl_s, (form_x, 478))
            self._race_rects = []
            RACE_W, RACE_H = 120, 36
            for ri, race in enumerate(races):
                rx = form_x + ri * (RACE_W + 8)
                r  = pygame.Rect(rx, 508, RACE_W, RACE_H)
                sel = (ri == self._race_idx)
                hov = r.collidepoint(pygame.mouse.get_pos())
                bg  = (48, 34, 78) if sel else ((28, 20, 55) if hov else _PANEL)
                bd  = _BORD_HV if sel else (_BORD_HV if hov else _BORD)
                pygame.draw.rect(surf, bg, r, border_radius=6)
                pygame.draw.rect(surf, bd, r, 2, border_radius=6)
                ts = fsm.render(race.replace("_", " ").title(), True,
                                _GOLD if sel else (_WHITE if hov else _DIM))
                surf.blit(ts, ts.get_rect(center=r.center))
                self._race_rects.append(r)
        else:
            self._race_rects = []

        # ── Error message ─────────────────────────────────────────────────────
        if self._error:
            err_s = fmd.render(self._error, True, _ERR)
            surf.blit(err_s, (form_x, 565))

        # ── Portrait (right side) ──────────────────────────────────────────────
        cls_data  = HERO_CLASSES[self._current_cls()]
        portraits = cls_data["portraits"]
        races_    = list(portraits.keys())
        race      = races_[min(self._race_idx, len(races_) - 1)] if races_ else "human"
        stem      = portraits.get(race, race)
        port_surf = assets.portrait(stem, self._gender, (200, 300))

        port_x = right_x + 40
        port_y = 155
        port_r = pygame.Rect(port_x - 4, port_y - 4, 208, 308)
        pygame.draw.rect(surf, _PANEL, port_r, border_radius=8)
        pygame.draw.rect(surf, _BORD,  port_r, 2, border_radius=8)
        if port_surf:
            surf.blit(port_surf, (port_x, port_y))
        else:
            ph = fmd.render("?", True, _DIM)
            surf.blit(ph, ph.get_rect(center=port_r.center))

        # ── Stat bars (right side, below portrait) ────────────────────────────
        stats_y = port_y + 320
        stats_lbl = fmd.render(t("char_create.stats") + ":", True, _DIM)
        surf.blit(stats_lbl, (right_x, stats_y))

        BAR_W, BAR_H = 260, 18
        BAR_X = right_x
        STAT_MAX = 20.0
        stat_rows = [
            ("STR", cls_data["str_pts"]),
            ("DEX", cls_data["dex_pts"]),
            ("VIT", cls_data["vit_pts"]),
            ("ENE", cls_data["ene_pts"]),
        ]
        stat_colors = {
            "STR": (220,  80,  80),
            "DEX": ( 80, 200,  80),
            "VIT": ( 80, 140, 220),
            "ENE": (200, 140, 220),
        }
        for si, (sname, sval) in enumerate(stat_rows):
            sy = stats_y + 30 + si * 30
            lbl_s = fsm.render(f"{sname}  {sval:2d}", True, _WHITE)
            surf.blit(lbl_s, (BAR_X, sy))
            bg_r = pygame.Rect(BAR_X + 90, sy + 2, BAR_W, BAR_H)
            fill_w = int(min(1.0, sval / STAT_MAX) * BAR_W)
            fill_r = pygame.Rect(BAR_X + 90, sy + 2, fill_w, BAR_H)
            pygame.draw.rect(surf, (30, 20, 50), bg_r, border_radius=4)
            pygame.draw.rect(surf, stat_colors[sname], fill_r, border_radius=4)
            pygame.draw.rect(surf, _BORD, bg_r, 1, border_radius=4)

        # ── Bottom buttons ─────────────────────────────────────────────────────
        btn_y  = _H - 110
        BTN_W, BTN_H = 280, 54

        confirm_r = pygame.Rect(_CX - BTN_W - 20, btn_y, BTN_W, BTN_H)
        back_r    = pygame.Rect(_CX + 20,          btn_y, BTN_W, BTN_H)

        for r, lbl, accent in [(confirm_r, t("char_create.confirm"), True),
                                (back_r,   t("char_create.back"),    False)]:
            hov = r.collidepoint(pygame.mouse.get_pos())
            bg  = (48, 34, 78) if hov else _PANEL
            bd  = _BORD_HV if hov else (_BORD_HV if accent else _BORD)
            pygame.draw.rect(surf, bg, r, border_radius=8)
            pygame.draw.rect(surf, bd, r, 2, border_radius=8)
            ls  = flg.render(lbl, True, _GOLD if hov else _WHITE)
            surf.blit(ls, ls.get_rect(center=r.center))

        self._confirm_rect = confirm_r
        self._back_rect    = back_r

    # ── Events ────────────────────────────────────────────────────────────────

    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._result = "back"
                return

            if self._input_active:
                if event.key == pygame.K_BACKSPACE:
                    self._name = self._name[:-1]
                elif event.key == pygame.K_RETURN:
                    self._try_confirm()
                elif event.unicode and len(self._name) < _MAX_NAME:
                    ch = event.unicode
                    if ch.isprintable() and ch not in '\t\n\r':
                        self._name += ch

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos

            # Name input focus
            input_r = pygame.Rect(200, 182, 500, 46)
            self._input_active = input_r.collidepoint(pos)

            # Class tabs
            for i, r in enumerate(self._cls_rects):
                if r.collidepoint(pos):
                    self._cls_idx  = i
                    self._race_idx = 0

            # Gender
            for gid, r in self._gender_rects.items():
                if r.collidepoint(pos):
                    self._gender = gid

            # Race
            for ri, r in enumerate(self._race_rects):
                if r.collidepoint(pos):
                    self._race_idx = ri

            # Bottom buttons
            if self._confirm_rect and self._confirm_rect.collidepoint(pos):
                self._try_confirm()
            elif self._back_rect and self._back_rect.collidepoint(pos):
                self._result = "back"

    def _try_confirm(self):
        name = self._name.strip()
        if not name:
            self._error = t("char_create.name_empty")
            return
        cls_id = self._current_cls()
        race   = self._current_race()
        self._result = ("confirm", name, cls_id, self._gender, race)
