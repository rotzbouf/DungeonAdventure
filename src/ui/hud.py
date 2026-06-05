import math
import pygame
from src.settings import (SCREEN_WIDTH, SCREEN_HEIGHT, HUD_HEIGHT,
                           FIREBALL_MANA_COST,
                           ICE_NOVA_MANA_COST, CHAIN_LIGHTNING_MANA_COST,
                           BLINK_MANA_COST, BATTLE_CRY_MANA_COST,
                           YELLOW, LIGHT_GRAY)
from src.locale import t

# ── HUD colours ──────────────────────────────────────────────────────────────
_BG          = (4,   6,  14)
_BG2         = (8,  12,  28)
_BORDER      = (68, 100, 176)
_BORDER_LO   = (36,  52,  96)
_HP_FULL     = (200,  30,  30)
_HP_HI       = (255,  80,  60)
_HP_LOW      = (220,  60,   0)
_HP_CRIT     = (255,   0,   0)
_MP_FULL     = (30,  130, 220)
_MP_HI       = (80,  200, 255)
_XP_FULL     = (60,  200,  60)
_XP_HI       = (120, 255, 120)
_BAR_BG      = (20,  20,  34)
_TEXT_BRIGHT = (252, 252, 252)
_TEXT_DIM    = (110, 110, 130)
_ATK_READY   = (60,  220,  80)
_ATK_WAIT    = (220,  92,  16)
_GOLD_COL    = (220, 175,   0)
_LVUP_COL    = (252, 188,   0)


def _shadow_blit(surface, text_surf, pos, offset=2):
    """Blit a text surface with a dark drop shadow for readability."""
    sh = pygame.Surface(text_surf.get_size(), pygame.SRCALPHA)
    sh.blit(text_surf, (0, 0))
    sh.fill((0, 0, 0, 180), special_flags=pygame.BLEND_RGBA_MULT)
    surface.blit(sh, (pos[0] + offset, pos[1] + offset))
    surface.blit(text_surf, pos)


def _gradient_bar(surface, x, y, w, h, pct, col_fill, col_hi, col_bg, border):
    pygame.draw.rect(surface, col_bg, (x, y, w, h))
    fw = max(0, int(w * pct))
    if fw > 0:
        pygame.draw.rect(surface, col_fill, (x, y, fw, h))
        hi_h = max(1, h // 3)
        hi_col = tuple(min(255, c + 60) for c in col_fill)
        pygame.draw.rect(surface, hi_col, (x, y, fw, hi_h))
        sh_col = tuple(max(0, c - 30) for c in col_fill)
        pygame.draw.rect(surface, sh_col, (x, y + h - hi_h, fw, hi_h))
    pygame.draw.rect(surface, border, (x, y, w, h), 1)


class HUD:
    def __init__(self):
        self._font_xl    = pygame.font.SysFont("monospace", 28, bold=True)
        self._font_lg    = pygame.font.SysFont("monospace", 28, bold=True)
        self._font_md    = pygame.font.SysFont("monospace", 24, bold=True)
        self._font_sm    = pygame.font.SysFont("monospace", 25)
        self._font_badge = pygame.font.SysFont("monospace", 17, bold=True)
        self._lvup_timer  = 0.0
        self._shop_timer  = 0.0
        self._quest_msgs: list[tuple[str, float]] = []

    def notify_level_up(self):
        self._lvup_timer = 2.8

    def notify_quest(self, text: str):
        self._quest_msgs.append((text, 3.5))

    def update(self, dt: float):
        self._lvup_timer = max(0.0, self._lvup_timer - dt)
        self._shop_timer = max(0.0, self._shop_timer - dt)
        self._quest_msgs = [(txt, timer - dt) for txt, timer in self._quest_msgs if timer - dt > 0]

    def draw(self, surface: pygame.Surface, player, dungeon_level: int,
             battle_cry_active: bool = False,
             ice_nova_cd: float = 0.0, chain_cd: float = 0.0, blink_cd: float = 0.0):
        hud_y = SCREEN_HEIGHT - HUD_HEIGHT

        # ── Panel background with subtle gradient ────────────────────────────
        panel = pygame.Surface((SCREEN_WIDTH, HUD_HEIGHT), pygame.SRCALPHA)
        panel.fill((*_BG, 245))
        for i in range(HUD_HEIGHT // 2):
            alpha = int(20 * (1.0 - i / (HUD_HEIGHT // 2)))
            pygame.draw.line(panel, (255, 255, 255, alpha), (0, i), (SCREEN_WIDTH, i))
        surface.blit(panel, (0, hud_y))
        pygame.draw.line(surface, _BORDER, (0, hud_y), (SCREEN_WIDTH, hud_y), 2)
        pygame.draw.line(surface, _BORDER_LO, (0, hud_y + 2), (SCREEN_WIDTH, hud_y + 2), 1)

        pad = 18
        cy  = hud_y + HUD_HEIGHT // 2

        # ── LEFT SECTION: HP + MP bars ───────────────────────────────────────
        bar_w = 300
        bar_h = 20

        # HP bar
        hp_pct = max(0.0, player.hp / player.max_hp_total)
        hp_col = (_HP_CRIT if hp_pct < 0.25 else
                  _HP_LOW  if hp_pct < 0.50 else _HP_FULL)
        bx = pad
        by = hud_y + 14
        _gradient_bar(surface, bx, by, bar_w, bar_h, hp_pct, hp_col, _HP_HI, _BAR_BG, _BORDER_LO)
        hp_txt = self._font_md.render(
            f"HP  {int(player.hp)}/{player.max_hp_total}", True, _TEXT_BRIGHT)
        _shadow_blit(surface, hp_txt, (bx + bar_w // 2 - hp_txt.get_width() // 2, by + 2))

        # MP bar
        mp_pct = max(0.0, player.mana / player.max_mana_total) if player.max_mana_total else 0.0
        my_ = by + bar_h + 6
        _gradient_bar(surface, bx, my_, bar_w, 14, mp_pct, _MP_FULL, _MP_HI, _BAR_BG, _BORDER_LO)
        mp_txt = self._font_sm.render(
            f"MP  {int(player.mana)}/{player.max_mana_total}", True, _TEXT_BRIGHT)
        _shadow_blit(surface, mp_txt, (bx + bar_w // 2 - mp_txt.get_width() // 2, my_ + 1))

        # XP bar (thin strip below MP)
        xp_pct = min(1.0, player.xp / player.xp_to_next) if player.xp_to_next else 1.0
        xy_ = my_ + 14 + 4
        _gradient_bar(surface, bx, xy_, bar_w, 8, xp_pct, _XP_FULL, _XP_HI, _BAR_BG, _BORDER_LO)
        xp_lbl = self._font_sm.render(f"XP", True, _TEXT_DIM)
        _shadow_blit(surface, xp_lbl, (bx - 2, xy_))

        # Potion count
        pot_col = (252, 100, 80) if player.potions else _TEXT_DIM
        pot_txt = self._font_sm.render(
            f"POT {len(player.potions)}", True, pot_col)
        _shadow_blit(surface, pot_txt, (bx + bar_w + 10, by + 2))

        # ── CENTER-LEFT: Level + stats ────────────────────────────────────────
        sx = pad + bar_w + 110

        lv_txt = self._font_xl.render(f"LV {player.level}", True, YELLOW)
        _shadow_blit(surface, lv_txt, (sx, hud_y + 8))

        atk_col = _ATK_READY if player.attack_ready >= 1.0 else _ATK_WAIT
        atk_txt = self._font_md.render(f"ATK {player.attack}", True, atk_col)
        def_txt = self._font_md.render(f"DEF {player.defense}", True, LIGHT_GRAY)
        _shadow_blit(surface, atk_txt, (sx, hud_y + 34))
        _shadow_blit(surface, def_txt, (sx + 100, hud_y + 34))

        # ATK cooldown bar
        rdy = player.attack_ready
        cd_w = 180
        cd_y = hud_y + 56
        _gradient_bar(surface, sx, cd_y, cd_w, 8, rdy,
                      _ATK_READY if rdy >= 1.0 else _ATK_WAIT,
                      _TEXT_BRIGHT, _BAR_BG, _BORDER_LO)
        lbl = t("hud.ready") if rdy >= 1.0 else t("hud.atk_lbl")
        _shadow_blit(surface, self._font_sm.render(lbl, True, _TEXT_DIM),
                     (sx + cd_w + 5, cd_y - 1))

        # ── CENTER: Gold + status effects ─────────────────────────────────────
        gx = sx + 280
        gold_icon = self._font_lg.render("♦", True, _GOLD_COL)
        _shadow_blit(surface, gold_icon, (gx, hud_y + 8))
        gold_txt = self._font_lg.render(f" {player.gold}", True, _TEXT_BRIGHT)
        _shadow_blit(surface, gold_txt, (gx + gold_icon.get_width(), hud_y + 8))

        # Status effects
        _STATUS_DEFS = [
            ('poison', (50, 220, 50),   t("hud.status.poison")),
            ('burn',   (252, 120, 20),  t("hud.status.burn")),
            ('slow',   (60, 120, 220),  t("hud.status.slow")),
            ('freeze', (100, 220, 255), t("hud.status.freeze")),
        ]
        sx2 = gx
        for sname, scol, slabel in _STATUS_DEFS:
            if player.has_status(sname):
                tl = player._status[sname]['timer']
                stxt = self._font_sm.render(f"[{slabel} {tl:.1f}s]", True, scol)
                bg_s = pygame.Surface((stxt.get_width() + 6, stxt.get_height() + 2), pygame.SRCALPHA)
                bg_s.fill((*scol, 30))
                surface.blit(bg_s, (sx2 - 3, hud_y + 54))
                _shadow_blit(surface, stxt, (sx2, hud_y + 55))
                sx2 += stxt.get_width() + 10

        if battle_cry_active:
            msg = self._font_sm.render(t("hud.battle_cry"), True, (252, 180, 0))
            _shadow_blit(surface, msg, (sx2, hud_y + 55))

        # ── RIGHT SECTION: Floor + spells ─────────────────────────────────────
        fx = SCREEN_WIDTH - 380

        fl_str = f"{t('hud.floor_prefix')}{dungeon_level}"
        fl_txt = self._font_xl.render(fl_str, True, LIGHT_GRAY)
        _shadow_blit(surface, fl_txt, (fx, hud_y + 8))

        # Pending point badges — compact, steady, right of the floor label
        bx = fx + fl_txt.get_width() + 14
        by = hud_y + 13
        if player.stat_points > 0:
            lbl = self._font_badge.render(
                f"+{player.stat_points}pt [C]", True, (70, 215, 90))
            bg = pygame.Rect(bx - 4, by - 2, lbl.get_width() + 8, lbl.get_height() + 4)
            pygame.draw.rect(surface, (0, 36, 8),  bg, border_radius=3)
            pygame.draw.rect(surface, (30, 100, 40), bg, 1, border_radius=3)
            surface.blit(lbl, (bx, by))
            bx += lbl.get_width() + 16
        if player.skill_tree.skill_points > 0:
            lbl = self._font_badge.render(
                f"+{player.skill_tree.skill_points}sk [K]", True, (90, 150, 255))
            bg = pygame.Rect(bx - 4, by - 2, lbl.get_width() + 8, lbl.get_height() + 4)
            pygame.draw.rect(surface, (6, 10, 40),  bg, border_radius=3)
            pygame.draw.rect(surface, (30, 50, 110), bg, 1, border_radius=3)
            surface.blit(lbl, (bx, by))

        # Spell icons
        st = player.skill_tree
        spells = [
            ("Z",  t("spell.fireball"),   FIREBALL_MANA_COST,       0.0,        True),
            ("X",  t("spell.ice_nova"),   ICE_NOVA_MANA_COST,        ice_nova_cd, st.has_ice_nova()),
            ("R",  t("spell.chain_ltng"), CHAIN_LIGHTNING_MANA_COST, chain_cd,   st.has_chain_lightning()),
            ("V",  t("spell.blink"),      BLINK_MANA_COST,           blink_cd,   st.has_blink()),
            ("B",  t("spell.battle_cry"), BATTLE_CRY_MANA_COST,      0.0,        st.level("battle_cry") > 0),
        ]
        icon_x = fx
        icon_y = hud_y + 42
        for key, name, cost, cd, unlocked in spells:
            if not unlocked:
                continue
            can = player.mana >= cost and cd <= 0
            kc  = (80, 210, 80) if can else (160, 50, 50)
            if name == "BattleCry" and battle_cry_active:
                kc = (252, 180, 0)
            ks = self._font_sm.render(f"[{key}]", True, kc)
            ns = self._font_sm.render(f" {name}", True, _TEXT_DIM)
            _shadow_blit(surface, ks, (icon_x, icon_y))
            _shadow_blit(surface, ns, (icon_x + ks.get_width(), icon_y))
            icon_x += ks.get_width() + ns.get_width() + 8

        # ── OVERLAY MESSAGES ──────────────────────────────────────────────────
        play_cy = (SCREEN_HEIGHT - HUD_HEIGHT) // 2

        if self._lvup_timer > 0:
            alpha = min(255, int(self._lvup_timer * 130))
            msg   = self._font_xl.render(
                t("hud.level_up", n=player.level), True, _LVUP_COL)
            msg.set_alpha(alpha)
            pos = msg.get_rect(center=(SCREEN_WIDTH // 2, play_cy - 60))
            _shadow_blit(surface, msg, pos.topleft)

        qy = play_cy + 10
        for txt, timer in self._quest_msgs:
            fade = min(1.0, timer / 0.6)
            alpha = int(fade * 220)
            qs = self._font_lg.render(txt, True, (140, 230, 140))
            qs.set_alpha(alpha)
            pos = qs.get_rect(center=(SCREEN_WIDTH // 2, qy))
            _shadow_blit(surface, qs, pos.topleft)
            qy += 28
