"""Shared prev/next page control for scrollable UI panels."""
from __future__ import annotations
import pygame


def draw_pager(surf: pygame.Surface, cx: int, y: int,
               page: int, total_pages: int,
               font: pygame.font.Font) -> tuple:
    """Draw  [◀ PREV]  Page X / Y  [NEXT ▶]  centred at *cx*, top at *y*.

    Returns (prev_rect, next_rect).  Both are None when total_pages <= 1
    (nothing to page through) — callers should check before storing.
    """
    if total_pages <= 1:
        return None, None

    BW, BH, GAP = 70, 20, 8
    pg_s = font.render(f"Page {page} / {total_pages}", True, (145, 125, 82))
    total_w = BW + GAP + pg_s.get_width() + GAP + BW
    x0 = cx - total_w // 2

    prev_r = pygame.Rect(x0, y, BW, BH)
    next_r = pygame.Rect(x0 + BW + GAP + pg_s.get_width() + GAP, y, BW, BH)

    for r, lbl, on in [(prev_r, "◀ PREV", page > 1), (next_r, "NEXT ▶", page < total_pages)]:
        bg  = (50, 38, 24) if on else (24, 18, 10)
        brd = (108, 78, 44) if on else (44, 34, 20)
        tc  = (165, 142, 98) if on else (50, 38, 24)
        pygame.draw.rect(surf, bg, r)
        pygame.draw.rect(surf, brd, r, 1)
        ts = font.render(lbl, True, tc)
        surf.blit(ts, ts.get_rect(center=r.center))

    surf.blit(pg_s, (x0 + BW + GAP, y + (BH - pg_s.get_height()) // 2))
    return prev_r, next_r
