"""Skill Tree UI — K key opens/closes.  Click a skill box to spend a point."""
from __future__ import annotations

import pygame
from src.settings import SCREEN_WIDTH, SCREEN_HEIGHT, HUD_HEIGHT
from src.skills import SkillTree, _BY_ID, _ALL_DEFS
from src.locale import t

_BG_FILL    = (8,   6,  4, 218)
_BORDER     = (110, 88,  60)
_TITLE_COL  = (252, 188,  0)
_COMBAT_COL = (220,  80,  80)
_MAGIC_COL  = ( 80, 120, 255)
_ROGUE_COL  = ( 80, 200, 120)
_LOCKED_COL = ( 60,  55,  50)
_DIM_COL    = (100,  90,  70)

_TREE_COLORS  = {"combat": _COMBAT_COL, "magic": _MAGIC_COL, "rogue": _ROGUE_COL}
_TREE_HEADERS = {"combat": "── COMBAT ──",
                 "magic":  "── MAGIC ──",
                 "rogue":  "── ROGUE ──"}


class SkillScreen:
    def __init__(self):
        self._font_lg = pygame.font.SysFont("monospace", 24, bold=True)
        self._font_md = pygame.font.SysFont("monospace", 24, bold=True)
        self._font_sm = pygame.font.SysFont("monospace", 28)
        self._boxes:  dict[str, pygame.Rect] = {}

    def handle_click(self, mx: int, my: int, player):
        for sid, rect in self._boxes.items():
            if rect.collidepoint(mx, my):
                player.skill_tree.spend(sid)
                return

    def draw(self, surface: pygame.Surface, player):
        st: SkillTree = player.skill_tree
        W = SCREEN_WIDTH
        H = SCREEN_HEIGHT - HUD_HEIGHT

        bg = pygame.Surface((W, H), pygame.SRCALPHA)
        bg.fill(_BG_FILL)
        surface.blit(bg, (0, 0))

        pw, ph = 925, H - 36
        px = (W - pw) // 2
        py = 18
        panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
        panel.fill((12, 9, 6, 242))
        surface.blit(panel, (px, py))
        pygame.draw.rect(surface, _BORDER, (px, py, pw, ph), 2)

        # Title
        pts  = st.skill_points
        ttxt = t("skill.title_pts", n=pts,
                 s="S" if pts != 1 else "",
                 e="E" if pts != 1 else "")
        title_s = self._font_lg.render(ttxt, True, _TITLE_COL)
        surface.blit(title_s, (px + pw // 2 - title_s.get_width() // 2, py + 8))
        pygame.draw.line(surface, _BORDER, (px + 10, py + 36), (px + pw - 10, py + 36))

        self._boxes.clear()
        col_w = (pw - 20) // 3
        BOX_H = 60

        for ci, tree in enumerate(("combat", "magic", "rogue")):
            cx = px + 10 + ci * col_w
            cy = py + 48
            tcol = _TREE_COLORS[tree]

            # Header
            hdr = self._font_md.render(t(f"skill.tree.{tree}"), True, tcol)
            surface.blit(hdr, (cx + col_w // 2 - hdr.get_width() // 2, cy))
            cy += 22

            for sdef in [s for s in _ALL_DEFS if s.tree == tree]:
                lvl      = st.level(sdef.id)
                can      = st.can_spend(sdef.id)
                req_met  = (not sdef.requires) or st.is_unlocked(sdef.requires)
                unlocked = lvl > 0

                bw   = col_w - 16
                rect = pygame.Rect(cx + 8, cy, bw, BOX_H)
                self._boxes[sdef.id] = rect

                # Background
                if not req_met:
                    bg_col = (16, 13, 10)
                elif can:
                    bg_col = (30, 26, 18)
                else:
                    bg_col = (20, 17, 12)
                pygame.draw.rect(surface, bg_col, rect, border_radius=3)

                border_col = (tcol if unlocked else
                              (_BORDER if req_met else _LOCKED_COL))
                pygame.draw.rect(surface, border_col, rect, 1, border_radius=3)

                # Name
                name_col = (tcol if unlocked else
                            (_DIM_COL if req_met else _LOCKED_COL))
                skill_name = t(f"skill.{sdef.id}.name")
                ns = self._font_md.render(skill_name, True, name_col)
                surface.blit(ns, (rect.left + 6, rect.top + 5))

                # Level pips (right-aligned, left-to-right = right-to-left draw)
                for pi in range(sdef.max_level):
                    idx = sdef.max_level - 1 - pi
                    pr  = pygame.Rect(rect.right - 14 - pi * 12,
                                      rect.top + 6, 10, 10)
                    pip_col = tcol if idx < lvl else (40, 36, 28)
                    pygame.draw.rect(surface, pip_col, pr, border_radius=2)
                    pygame.draw.rect(surface, border_col, pr, 1, border_radius=2)

                # Description
                dc = (155, 145, 115) if req_met else _LOCKED_COL
                skill_desc = t(f"skill.{sdef.id}.desc")
                ds = self._font_sm.render(skill_desc, True, dc)
                surface.blit(ds, (rect.left + 6, rect.top + 24))

                # Requirement / call-to-action
                if sdef.requires and not req_met:
                    req_name = t(f"skill.{sdef.requires}.name")
                    rs = self._font_sm.render(
                        t("skill.req", name=req_name), True, _LOCKED_COL)
                    surface.blit(rs, (rect.left + 6, rect.top + 40))
                elif can:
                    hs = self._font_sm.render(
                        t("skill.click_learn"), True, (80, 180, 80))
                    surface.blit(hs, (rect.left + 6, rect.top + 40))
                elif lvl >= sdef.max_level:
                    ms = self._font_sm.render(t("skill.mastered"), True, tcol)
                    surface.blit(ms, (rect.left + 6, rect.top + 40))

                cy += BOX_H + 8

        # Footer
        hint = self._font_sm.render(t("skill.hint"), True, _DIM_COL)
        surface.blit(hint, (px + pw // 2 - hint.get_width() // 2, py + ph - 15))
