"""Quest Giver UI — shown when interacting with Guild Master or dungeon wanderers."""
from __future__ import annotations

import pygame
from src.settings import SCREEN_WIDTH, SCREEN_HEIGHT, HUD_HEIGHT
from src.locale import t, t_quest_name, t_quest_desc

_BG_FILL    = (8,   6,  4, 220)
_BORDER     = (130, 105, 60)
_TITLE_COL  = (200, 170, 255)
_TEXT_COL   = (220, 205, 175)
_DIM_COL    = (110, 100,  80)
_REWARD_COL = (180, 155,  60)
_BTN_IDLE   = (50,  45,  35)
_BTN_HOV    = (80,  70,  50)
_BTN_ACCEPT = (40,  90,  40)
_BTN_HOV_A  = (60, 130,  60)
_BTN_DONE   = (30,  80,  30)


class QuestGiverScreen:
    def __init__(self):
        self._font_lg  = pygame.font.SysFont("monospace", 26, bold=True)
        self._font_md  = pygame.font.SysFont("monospace", 22, bold=True)
        self._font_sm  = pygame.font.SysFont("monospace", 20)
        self._quests:   list  = []
        self._accepted: set[str] = set()
        self._giver:    str   = ""
        self._btn_rects: list[tuple] = []  # (quest_idx, pygame.Rect)
        self._close_rect: pygame.Rect | None = None

    def open(self, quests: list, giver: str) -> None:
        self._quests   = quests
        self._giver    = giver
        self._accepted = set()
        self._btn_rects   = []
        self._close_rect  = None

    @property
    def accepted_ids(self) -> set[str]:
        return set(self._accepted)

    def handle_event(self, event: pygame.event.Event) -> str | None:
        """
        Handle mouse clicks.  Returns "close" when the close button is clicked,
        or None otherwise.  Quest accept buttons add to self._accepted.
        """
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return None
        pos = event.pos
        if self._close_rect and self._close_rect.collidepoint(pos):
            return "close"
        for idx, rect in self._btn_rects:
            if rect.collidepoint(pos):
                q = self._quests[idx]
                if q.id not in self._accepted:
                    self._accepted.add(q.id)
        return None

    def draw(self, surface: pygame.Surface) -> None:
        W = SCREEN_WIDTH
        H = SCREEN_HEIGHT - HUD_HEIGHT

        bg = pygame.Surface((W, H), pygame.SRCALPHA)
        bg.fill(_BG_FILL)
        surface.blit(bg, (0, 0))

        pw, ph = 640, min(H - 40, 520)
        px = (W - pw) // 2
        py = (H - ph) // 2

        panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
        panel.fill((14, 10, 8, 245))
        surface.blit(panel, (px, py))
        pygame.draw.rect(surface, _BORDER, (px, py, pw, ph), 2)

        # Title
        title = self._font_lg.render(
            t("quest_giver.title", name=self._giver), True, _TITLE_COL)
        surface.blit(title, (px + pw // 2 - title.get_width() // 2, py + 10))
        pygame.draw.line(surface, _BORDER, (px + 12, py + 40), (px + pw - 12, py + 40))

        sub = self._font_sm.render(t("quest_giver.subtitle"), True, _DIM_COL)
        surface.blit(sub, (px + pw // 2 - sub.get_width() // 2, py + 44))

        self._btn_rects = []
        y = py + 68
        mouse_pos = pygame.mouse.get_pos()

        for idx, q in enumerate(self._quests):
            accepted = q.id in self._accepted
            card_h = 100
            if y + card_h > py + ph - 50:
                break

            # Card background
            card_col = (22, 20, 16) if not accepted else (16, 36, 16)
            card = pygame.Surface((pw - 24, card_h), pygame.SRCALPHA)
            card.fill((*card_col, 220))
            surface.blit(card, (px + 12, y))
            border_col = _BTN_DONE if accepted else _BORDER
            pygame.draw.rect(surface, border_col, (px + 12, y, pw - 24, card_h), 1)

            # Quest name + type badge
            name_s = self._font_md.render(
                t_quest_name(q.id, q.name, floor=q.floor, giver=q.giver, relic=q.relic),
                True, _TEXT_COL)
            surface.blit(name_s, (px + 20, y + 6))
            badge_txt = t(f"quest.type.{q.type}")
            badge_col = {"fetch": (80, 160, 80), "clear": (80, 120, 200),
                         "bounty": (200, 80, 80), "kill": (200, 100, 40)}.get(q.type, _DIM_COL)
            badge_s = self._font_sm.render(badge_txt, True, badge_col)
            surface.blit(badge_s, (px + pw - 24 - badge_s.get_width() - 64, y + 8))

            # Giver attribution
            if q.giver:
                giv_s = self._font_sm.render(f"  {q.giver}", True, _DIM_COL)
                surface.blit(giv_s, (px + 20, y + 26))

            # Description
            desc_s = self._font_sm.render(
                t_quest_desc(q.id, q.required, q.target,
                             floor=q.floor, giver=q.giver, relic=q.relic) or q.desc,
                True, _DIM_COL)
            surface.blit(desc_s, (px + 20, y + 44))

            # Reward line
            rwd = t("quest.reward_xp", xp=q.reward_xp)
            if q.reward_gold:
                rwd += t("quest.reward_gold", gold=q.reward_gold)
            rwd_s = self._font_sm.render(rwd, True, _REWARD_COL)
            surface.blit(rwd_s, (px + 20, y + 64))

            # Accept button
            btn_w, btn_h = 80, 24
            btn_x = px + pw - 12 - btn_w - 6
            btn_y = y + card_h - btn_h - 6
            btn_rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)
            self._btn_rects.append((idx, btn_rect))
            if accepted:
                bc = _BTN_DONE
                label = t("quest_giver.accepted")
            else:
                hovered = btn_rect.collidepoint(mouse_pos)
                bc = _BTN_HOV_A if hovered else _BTN_ACCEPT
                label = t("quest_giver.accept")
            pygame.draw.rect(surface, bc, btn_rect)
            pygame.draw.rect(surface, _BORDER, btn_rect, 1)
            lbl_s = self._font_sm.render(label, True, (220, 220, 220))
            surface.blit(lbl_s, (btn_rect.centerx - lbl_s.get_width() // 2,
                                  btn_rect.centery - lbl_s.get_height() // 2))

            y += card_h + 8

        # Close button
        cl_w, cl_h = 140, 30
        cl_x = px + pw // 2 - cl_w // 2
        cl_y = py + ph - cl_h - 8
        self._close_rect = pygame.Rect(cl_x, cl_y, cl_w, cl_h)
        hov = self._close_rect.collidepoint(mouse_pos)
        pygame.draw.rect(surface, _BTN_HOV if hov else _BTN_IDLE, self._close_rect)
        pygame.draw.rect(surface, _BORDER, self._close_rect, 1)
        cl_s = self._font_sm.render(t("quest_giver.close"), True, _TEXT_COL)
        surface.blit(cl_s, (self._close_rect.centerx - cl_s.get_width() // 2,
                             self._close_rect.centery - cl_s.get_height() // 2))
