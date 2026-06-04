"""
Skill Tree UI — K key opens/closes.

Three columns (Combat / Magic / Rogue) each showing 8 skills arranged
in 4 tiers.  Prerequisite edges are drawn as lines connecting parent
nodes to child nodes, giving the screen a real tree shape.

Clicking a node spends one skill point if the prerequisites are met.
Hovering shows a detailed tooltip at the bottom of the panel.
"""
from __future__ import annotations

import math
import pygame

from src.settings import SCREEN_WIDTH, SCREEN_HEIGHT, HUD_HEIGHT
from src.skills import SkillTree, _BY_ID, _ALL_DEFS, SkillDef
from src.locale  import t

# ── Panel geometry ─────────────────────────────────────────────────────────────
_PW = 1760
_PH = 760
_PX = (SCREEN_WIDTH  - _PW) // 2
_PY = (SCREEN_HEIGHT - HUD_HEIGHT - _PH) // 2

_COL_W   = 560          # width of each tree column
_COL_X   = [_PX + 20,  _PX + 600,  _PX + 1180]   # left edge of each column
_COL_Y   = _PY + 52     # top of node area (below header)

# Node size
_NW = 162    # node width
_NH =  60    # node height

# Tier Y centres (relative to _COL_Y)
_TIER_Y = {1: 80, 2: 210, 3: 345, 4: 485}

# X centres for each tier size (relative to column left)
_TIER_CX = {
    2: [145, 415],
    3: [80,  280,  475],
    1: [280],
}

# ── Palette ────────────────────────────────────────────────────────────────────
_BG_COL      = (10,  7,  4)
_PANEL_COL   = (16, 12,  8)
_BORDER_COL  = (90, 70, 45)
_TITLE_COL   = (252, 188, 0)
_DIM_COL     = (80, 70, 55)

_TREE_COL = {
    "combat": (220,  80,  60),
    "magic":  ( 80, 120, 255),
    "rogue":  ( 60, 200, 110),
}

_LOCKED_FG  = (55, 50, 42)
_LOCKED_BG  = (14, 11,  8)
_AVAIL_BG   = (28, 22, 14)
_LEVELED_BG = (20, 18, 12)
_MAXED_COL  = (220, 175, 0)

# ── Tree layout — (tier, position_in_tier) per skill ──────────────────────────
_LAYOUT: dict[str, dict[str, tuple[int, int]]] = {
    "combat": {
        "power_strike":   (1, 0),
        "toughness":      (1, 1),
        "battle_cry":     (2, 0),
        "iron_fist":      (2, 1),
        "whirlwind":      (2, 2),
        "war_shout":      (3, 0),
        "shield_mastery": (3, 1),
        "colossus":       (4, 0),
    },
    "magic": {
        "arcane_mind":       (1, 0),
        "fireball_mastery":  (1, 1),
        "ice_nova":          (2, 0),
        "mana_shield":       (2, 1),
        "chain_lightning":   (2, 2),
        "arcane_surge":      (3, 0),
        "elemental_fury":    (3, 1),
        "arcane_ascension":  (4, 0),
    },
    "rogue": {
        "crit_mastery":  (1, 0),
        "evasion":       (1, 1),
        "poison_blade":  (2, 0),
        "shadow_step":   (2, 1),
        "knife_fan":     (2, 2),
        "assassination": (3, 0),
        "shadow_arts":   (3, 1),
        "death_mark":    (4, 0),
    },
}

# Tier sizes per tree (for picking _TIER_CX)
_TIER_SIZE: dict[str, dict[int, int]] = {
    tree: {t: sum(1 for v in pos.values() if v[0] == t) for t in range(1, 5)}
    for tree, pos in _LAYOUT.items()
}


def _node_center(tree: str, sid: str, col_idx: int) -> tuple[int, int]:
    """Absolute screen centre of the node for skill *sid* in *tree*."""
    tier, pos = _LAYOUT[tree][sid]
    tier_size = _TIER_SIZE[tree][tier]
    cx_in_col = _TIER_CX[tier_size][pos]
    cy_in_col = _TIER_Y[tier]
    return (_COL_X[col_idx] + cx_in_col,
            _COL_Y         + cy_in_col)


def _node_rect(tree: str, sid: str, col_idx: int) -> pygame.Rect:
    cx, cy = _node_center(tree, sid, col_idx)
    return pygame.Rect(cx - _NW // 2, cy - _NH // 2, _NW, _NH)


class SkillScreen:
    def __init__(self):
        self._font_title = pygame.font.SysFont("monospace", 22, bold=True)
        self._font_tree  = pygame.font.SysFont("monospace", 18, bold=True)
        self._font_node  = pygame.font.SysFont("monospace", 14, bold=True)
        self._font_sm    = pygame.font.SysFont("monospace", 13)
        self._font_tip   = pygame.font.SysFont("monospace", 15)

        self._boxes: dict[str, pygame.Rect] = {}   # sid → screen Rect
        self._hovered: str | None = None

    # ── Public API ────────────────────────────────────────────────────────────

    def handle_click(self, mx: int, my: int, player):
        for sid, rect in self._boxes.items():
            if rect.collidepoint(mx, my):
                player.skill_tree.spend(sid)
                return

    def draw(self, surface: pygame.Surface, player):
        st   = player.skill_tree
        W, H = SCREEN_WIDTH, SCREEN_HEIGHT - HUD_HEIGHT

        # Full-screen dim
        ov = pygame.Surface((W, H), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 200))
        surface.blit(ov, (0, 0))

        # Panel background
        pygame.draw.rect(surface, _BG_COL, (_PX, _PY, _PW, _PH))
        pygame.draw.rect(surface, _BORDER_COL, (_PX, _PY, _PW, _PH), 2)

        # Title bar
        pygame.draw.rect(surface, _PANEL_COL, (_PX, _PY, _PW, 46))
        pygame.draw.line(surface, _BORDER_COL,
                         (_PX, _PY + 46), (_PX + _PW, _PY + 46))
        pts = st.skill_points
        ttxt = t("skill.title_pts", n=pts,
                 s="S" if pts != 1 else "",
                 e="E" if pts != 1 else "")
        title_s = self._font_title.render(ttxt, True, _TITLE_COL)
        surface.blit(title_s,
                     title_s.get_rect(centerx=_PX + _PW // 2, centery=_PY + 23))

        # Track hover
        mx, my = pygame.mouse.get_pos()
        self._hovered = None
        self._boxes.clear()

        # Column separators
        for cx in [_COL_X[1] - 10, _COL_X[2] - 10]:
            pygame.draw.line(surface, (_BORDER_COL[0] // 2,
                                        _BORDER_COL[1] // 2,
                                        _BORDER_COL[2] // 2),
                             (cx, _PY + 48), (cx, _PY + _PH - 60), 1)

        for ci, tree in enumerate(("combat", "magic", "rogue")):
            self._draw_tree(surface, tree, ci, st, mx, my)

        # Tooltip area (bottom strip)
        self._draw_tooltip(surface, st)

        # Footer hint
        hint = self._font_sm.render(t("skill.hint"), True, _DIM_COL)
        surface.blit(hint, hint.get_rect(centerx=_PX + _PW // 2,
                                          centery=_PY + _PH - 14))

    # ── Tree rendering ────────────────────────────────────────────────────────

    def _draw_tree(self, surface: pygame.Surface, tree: str, ci: int,
                   st: SkillTree, mx: int, my: int):
        tcol    = _TREE_COL[tree]
        col_cx  = _COL_X[ci] + _COL_W // 2

        # Column header
        hdr_s = self._font_tree.render(t(f"skill.tree.{tree}"), True, tcol)
        surface.blit(hdr_s, hdr_s.get_rect(centerx=col_cx, centery=_PY + 68))

        # Draw prerequisite edges (BEFORE nodes so they appear behind)
        for sdef in _ALL_DEFS:
            if sdef.tree != tree or not sdef.requires:
                continue
            parent_cx, parent_cy = _node_center(tree, sdef.requires, ci)
            child_cx,  child_cy  = _node_center(tree, sdef.id,       ci)

            parent_unlocked = st.is_unlocked(sdef.requires)
            child_unlocked  = st.is_unlocked(sdef.id)

            if parent_unlocked and child_unlocked:
                line_col = tcol
                line_w   = 3
            elif parent_unlocked:
                line_col = tuple(c // 2 for c in tcol)
                line_w   = 2
            else:
                line_col = (45, 40, 32)
                line_w   = 1

            # Draw a curve-ish connector using a mid-point
            mid_y = (parent_cy + child_cy) // 2
            # Straight line with a small decorative dot at midpoint
            pygame.draw.line(surface, line_col,
                             (parent_cx, parent_cy + _NH // 2),
                             (child_cx,  child_cy  - _NH // 2), line_w)
            # Small diamond at midpoint
            dm_x = (parent_cx + child_cx) // 2
            dm_y = mid_y
            if abs(parent_cx - child_cx) > 10:
                pts_d = [(dm_x, dm_y - 4), (dm_x + 4, dm_y),
                         (dm_x, dm_y + 4), (dm_x - 4, dm_y)]
                pygame.draw.polygon(surface, line_col, pts_d)

        # Draw skill nodes
        for sdef in _ALL_DEFS:
            if sdef.tree != tree:
                continue
            rect = _node_rect(tree, sdef.id, ci)
            self._boxes[sdef.id] = rect
            if rect.collidepoint(mx, my):
                self._hovered = sdef.id
            self._draw_node(surface, sdef, rect, st, tcol)

    def _draw_node(self, surface: pygame.Surface, sdef: SkillDef,
                   rect: pygame.Rect, st: SkillTree, tcol: tuple):
        lvl      = st.level(sdef.id)
        can      = st.can_spend(sdef.id)
        req_met  = (not sdef.requires) or st.is_unlocked(sdef.requires)
        unlocked = lvl > 0
        maxed    = (lvl >= sdef.max_level)
        hov      = (sdef.id == self._hovered)

        # Background
        if not req_met:
            bg = _LOCKED_BG
        elif hov:
            bg = tuple(min(255, c + 12) for c in _AVAIL_BG)
        elif unlocked:
            bg = _LEVELED_BG
        else:
            bg = _AVAIL_BG
        pygame.draw.rect(surface, bg, rect, border_radius=5)

        # Border
        if maxed:
            border = _MAXED_COL
            bw = 2
        elif unlocked:
            border = tcol
            bw = 2
        elif req_met and can:
            pulse = int(180 + 60 * abs(math.sin(pygame.time.get_ticks() * 0.003)))
            border = tuple(min(255, int(tcol[i] * pulse / 255)) for i in range(3))
            bw = 2
        elif req_met:
            border = _BORDER_COL
            bw = 1
        else:
            border = (40, 36, 28)
            bw = 1
        pygame.draw.rect(surface, border, rect, bw, border_radius=5)

        # Skill name
        name_col = (_MAXED_COL if maxed else
                    tcol       if unlocked or (req_met and can) else
                    _LOCKED_FG)
        name_txt = t(f"skill.{sdef.id}.name")
        name_s   = self._font_node.render(name_txt, True, name_col)
        # Truncate if needed
        max_name_w = rect.width - _NH - 6
        while name_s.get_width() > max_name_w and len(name_txt) > 3:
            name_txt = name_txt[:-1]
            name_s   = self._font_node.render(name_txt + "…", True, name_col)
        surface.blit(name_s, (rect.left + 6, rect.top + 6))

        # Level pips / MAX badge
        if maxed:
            max_s = self._font_sm.render("MAX", True, _MAXED_COL)
            surface.blit(max_s, (rect.right - max_s.get_width() - 5,
                                  rect.top + 6))
        else:
            for pi in range(sdef.max_level):
                pr = pygame.Rect(rect.right - 12 - pi * 14,
                                 rect.top + 6, 10, 10)
                pip_col = tcol if pi < lvl else (40, 35, 28)
                pygame.draw.rect(surface, pip_col, pr, border_radius=2)
                pygame.draw.rect(surface, border, pr, 1, border_radius=2)

        # Short description line
        desc_col = (140, 128, 98) if req_met else _LOCKED_FG
        desc_txt = t(f"skill.{sdef.id}.desc")
        desc_s   = self._font_sm.render(desc_txt, True, desc_col)
        # Truncate to fit
        max_desc_w = rect.width - 8
        if desc_s.get_width() > max_desc_w:
            desc_txt = desc_txt[: int(max_desc_w / self._font_sm.size("W")[0])]
            desc_s   = self._font_sm.render(desc_txt + "…", True, desc_col)
        surface.blit(desc_s, (rect.left + 6,
                               rect.top + rect.height - desc_s.get_height() - 4))

        # Tier indicator (small, top-right corner of locked nodes)
        if not req_met:
            tier_s = self._font_sm.render(f"T{sdef.tier}", True, (50, 45, 38))
            surface.blit(tier_s, (rect.right - tier_s.get_width() - 3,
                                   rect.bottom - tier_s.get_height() - 3))

    # ── Tooltip strip ─────────────────────────────────────────────────────────

    def _draw_tooltip(self, surface: pygame.Surface, st: SkillTree):
        """Draw a fixed tooltip strip at the bottom of the panel."""
        tip_h = 52
        tip_y = _PY + _PH - 60
        pygame.draw.line(surface, _BORDER_COL,
                         (_PX + 10, tip_y), (_PX + _PW - 10, tip_y))

        if self._hovered is None:
            return
        sdef = _BY_ID.get(self._hovered)
        if sdef is None:
            return

        lvl     = st.level(sdef.id)
        can     = st.can_spend(sdef.id)
        req_met = (not sdef.requires) or st.is_unlocked(sdef.requires)
        tcol    = _TREE_COL[sdef.tree]

        x = _PX + 16
        y = tip_y + 8

        # Name + level
        name_str = t(f"skill.{sdef.id}.name")
        lvl_str  = f"  [{lvl}/{sdef.max_level}]"
        name_s   = self._font_tip.render(name_str, True, tcol)
        lvl_s    = self._font_sm.render(lvl_str,  True, _DIM_COL)
        surface.blit(name_s, (x, y))
        surface.blit(lvl_s,  (x + name_s.get_width(), y + 2))

        # Description
        desc_s = self._font_sm.render(t(f"skill.{sdef.id}.desc"), True,
                                       (175, 160, 120))
        surface.blit(desc_s, (x, y + self._font_tip.get_height() + 3))

        # Status on right side
        if lvl >= sdef.max_level:
            status_s = self._font_sm.render("MASTERED", True, _MAXED_COL)
        elif can:
            status_s = self._font_sm.render("Click to learn (+1 level)",
                                             True, (80, 200, 80))
        elif not req_met:
            req_name = t(f"skill.{sdef.requires}.name") if sdef.requires else "?"
            status_s = self._font_sm.render(f"Requires: {req_name}",
                                             True, (180, 80, 80))
        else:
            status_s = self._font_sm.render("No skill points", True, _DIM_COL)
        surface.blit(status_s,
                     ((_PX + _PW - status_s.get_width() - 16), y + 4))
