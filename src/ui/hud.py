import math
import pygame
from src.settings import (SCREEN_WIDTH, SCREEN_HEIGHT, HUD_HEIGHT,
                           FIREBALL_MANA_COST,
                           ICE_NOVA_MANA_COST, CHAIN_LIGHTNING_MANA_COST,
                           BLINK_MANA_COST, BATTLE_CRY_MANA_COST,
                           YELLOW, LIGHT_GRAY)
from src.locale import t

# ── HUD colours ──────────────────────────────────────────────────────────────
_BG          = (0,   0,   0)
_BORDER      = (68, 100, 176)
_HEART_FULL  = (204,   0,   0)
_HEART_HI    = (252,  80,  80)
_HEART_HALF  = (140,   0,   0)
_HEART_HALF_HI = (180, 60,  60)
_HEART_EMPTY = ( 52,   0,   0)
_MAGIC_FILL  = (0,  168,   0)
_MAGIC_BG    = (0,   40,   0)
_RUPEE       = (0,  168,   0)
_RUPEE_HI    = (0,  252,   0)
_TEXT_BRIGHT = (252, 252, 252)
_TEXT_DIM    = (108, 108, 108)
_ATK_READY   = (0,  220,   0)
_ATK_WAIT    = (220, 92,   16)
_LVUP_COL    = (252, 188,   0)


def _draw_heart(surface, x, y, state):
    if state == 'full':
        c1, c2 = _HEART_FULL, _HEART_HI
    elif state == 'half':
        c1, c2 = _HEART_HALF, _HEART_HALF_HI
    else:
        c1, c2 = _HEART_EMPTY, _HEART_EMPTY
    pygame.draw.circle(surface, c1, (x + 3,  y + 3), 3)
    pygame.draw.circle(surface, c1, (x + 9,  y + 3), 3)
    pygame.draw.polygon(surface, c1, [(x, y+4), (x+12, y+4), (x+6, y+11)])
    if state != 'empty':
        pygame.draw.circle(surface, c2, (x+3, y+3), 2)
        pygame.draw.circle(surface, c2, (x+9, y+3), 2)
        pygame.draw.polygon(surface, c2, [(x+1, y+5), (x+11, y+5), (x+6, y+10)])


def _draw_rupee(surface, x, y):
    pts = [(x+4, y), (x+8, y+5), (x+4, y+12), (x, y+5)]
    pygame.draw.polygon(surface, _RUPEE,    pts)
    pygame.draw.polygon(surface, _RUPEE_HI, pts, 1)
    surface.set_at((x+3, y+4), _RUPEE_HI)
    surface.set_at((x+4, y+3), _RUPEE_HI)


class HUD:
    def __init__(self):
        self._font_lg = pygame.font.SysFont("monospace", 20, bold=True)
        self._font_md = pygame.font.SysFont("monospace", 14, bold=True)
        self._font_sm = pygame.font.SysFont("monospace", 12)
        self._lvup_timer  = 0.0
        self._shop_timer  = 0.0
        self._quest_msgs: list[tuple[str, float]] = []   # (text, timer)

    def notify_level_up(self):
        self._lvup_timer = 2.8

    def notify_quest(self, text: str):
        self._quest_msgs.append((text, 3.5))

    def update(self, dt: float):
        self._lvup_timer = max(0.0, self._lvup_timer - dt)
        self._shop_timer = max(0.0, self._shop_timer - dt)
        self._quest_msgs = [(t, timer - dt) for t, timer in self._quest_msgs if timer - dt > 0]

    def draw(self, surface: pygame.Surface, player, dungeon_level: int,
             ng_plus: int = 0, battle_cry_active: bool = False,
             ice_nova_cd: float = 0.0, chain_cd: float = 0.0, blink_cd: float = 0.0):
        hud_y = SCREEN_HEIGHT - HUD_HEIGHT
        pygame.draw.rect(surface, _BG, (0, hud_y, SCREEN_WIDTH, HUD_HEIGHT))
        pygame.draw.line(surface, _BORDER, (0, hud_y), (SCREEN_WIDTH, hud_y), 2)

        pad = 12
        cy  = hud_y + HUD_HEIGHT // 2

        # ── HEARTS ───────────────────────────────────────────────────────────
        hp_per_heart   = 10
        total_hearts   = max(10, math.ceil(player.max_hp_total / hp_per_heart))
        filled_hearts  = int(player.hp // hp_per_heart)
        has_half       = int(player.hp) % hp_per_heart >= 5
        hearts_per_row = 10
        heart_w, heart_h = 14, 12
        for i in range(total_hearts):
            row = i // hearts_per_row
            col = i  % hearts_per_row
            hx  = pad + col * heart_w
            hy  = hud_y + 6 + row * (heart_h + 2)
            state = ('full' if i < filled_hearts else
                     'half' if i == filled_hearts and has_half else 'empty')
            _draw_heart(surface, hx, hy, state)

        # ── MP BAR ───────────────────────────────────────────────────────────
        bar_x = pad
        bar_y = hud_y + 6 + ((total_hearts - 1) // hearts_per_row + 1) * (heart_h + 2)
        bar_w = hearts_per_row * heart_w
        bar_h = 6
        if bar_y + bar_h < SCREEN_HEIGHT - 4:
            label = self._font_sm.render(t("hud.mp"), True, _TEXT_DIM)
            surface.blit(label, (bar_x, bar_y - 1))
            bx = bar_x + 18
            pygame.draw.rect(surface, _MAGIC_BG, (bx, bar_y, bar_w - 18, bar_h))
            fw = int((bar_w - 18) * max(0, player.mana) / player.max_mana_total) if player.max_mana_total else 0
            if fw > 0:
                pygame.draw.rect(surface, _MAGIC_FILL, (bx, bar_y, fw, bar_h))
            pygame.draw.rect(surface, _BORDER, (bx, bar_y, bar_w - 18, bar_h), 1)

        # ── STATS (centre) ────────────────────────────────────────────────────
        sx = SCREEN_WIDTH // 2 - 160

        lv_txt = self._font_lg.render(f"LV {player.level}", True, YELLOW)
        surface.blit(lv_txt, (sx, hud_y + 5))

        atk_col = _ATK_READY if player.attack_ready >= 1.0 else _ATK_WAIT
        atk_txt = self._font_md.render(f"ATK {player.attack}", True, atk_col)
        def_txt = self._font_md.render(f"DEF {player.defense}", True, LIGHT_GRAY)
        surface.blit(atk_txt, (sx, hud_y + 28))
        surface.blit(def_txt, (sx + 80, hud_y + 28))

        pot_col = (252, 80, 80) if player.potions else _TEXT_DIM
        pot_txt = self._font_md.render(f"POT {len(player.potions)}", True, pot_col)
        surface.blit(pot_txt, (sx, hud_y + 46))

        # ── GOLD ─────────────────────────────────────────────────────────────
        rx = sx + 200
        _draw_rupee(surface, rx, hud_y + 8)
        gold_txt = self._font_md.render(f" x {player.gold}", True, _TEXT_BRIGHT)
        surface.blit(gold_txt, (rx + 10, hud_y + 10))

        # ── FLOOR / NG+ ───────────────────────────────────────────────────────
        fx = SCREEN_WIDTH - 200
        ng_label = f"NG+{ng_plus}" if ng_plus > 0 else ""
        fl_str   = f"{t('hud.floor_prefix')}{dungeon_level}/5  {ng_label}".strip()
        fl_col   = (180, 220, 255) if ng_plus > 0 else LIGHT_GRAY
        fl_txt   = self._font_lg.render(fl_str, True, fl_col)
        surface.blit(fl_txt, (fx, hud_y + 5))

        # ATK cooldown bar
        rdy  = player.attack_ready
        cd_w = 150
        pygame.draw.rect(surface, (32, 32, 32), (fx, hud_y + 30, cd_w, 7))
        fill = int(cd_w * rdy)
        if fill > 0:
            col = _ATK_READY if rdy >= 1.0 else _ATK_WAIT
            pygame.draw.rect(surface, col, (fx, hud_y + 30, fill, 7))
        pygame.draw.rect(surface, _BORDER, (fx, hud_y + 30, cd_w, 7), 1)
        lbl = t("hud.ready") if rdy >= 1.0 else t("hud.atk_lbl")
        surface.blit(self._font_sm.render(lbl, True, _TEXT_DIM),
                     (fx + cd_w + 4, hud_y + 29))

        # ── SPELL ICONS (row below ATK bar) ──────────────────────────────────
        st = player.skill_tree
        spells = [
            ("Z",  t("spell.fireball"),   FIREBALL_MANA_COST,        0.0,         True),
            ("X",  t("spell.ice_nova"),   ICE_NOVA_MANA_COST,         ice_nova_cd, st.has_ice_nova()),
            ("R",  t("spell.chain_ltng"), CHAIN_LIGHTNING_MANA_COST,  chain_cd,    st.has_chain_lightning()),
            ("V",  t("spell.blink"),      BLINK_MANA_COST,            blink_cd,    st.has_blink()),
            ("B",  t("spell.battle_cry"), BATTLE_CRY_MANA_COST,       0.0,         st.level("battle_cry") > 0),
        ]
        icon_x = fx - 60
        icon_y = hud_y + 46
        for key, name, cost, cd, unlocked in spells:
            if not unlocked:
                continue
            can = player.mana >= cost and cd <= 0
            kc  = (80, 200, 80) if can else (160, 50, 50)
            if name == "BattleCry" and battle_cry_active:
                kc = (252, 180, 0)
            ks = self._font_sm.render(key, True, kc)
            ns = self._font_sm.render(f":{name}", True, _TEXT_DIM)
            surface.blit(ks, (icon_x, icon_y))
            surface.blit(ns, (icon_x + ks.get_width(), icon_y))
            icon_x += ks.get_width() + ns.get_width() + 6

        # ── STATUS ICONS ─────────────────────────────────────────────────────
        _STATUS_DEFS = [
            ('poison', (30,  200,  30), t("hud.status.poison")),
            ('burn',   (252, 120,  20), t("hud.status.burn")),
            ('slow',   (60,  120, 220), t("hud.status.slow")),
            ('freeze', (80,  200, 255), t("hud.status.freeze")),
        ]
        icon_x2 = sx + 148
        for sname, scol, slabel in _STATUS_DEFS:
            if player.has_status(sname):
                t_left = player._status[sname]['timer']
                stxt   = self._font_sm.render(f"[{slabel} {t_left:.1f}s]", True, scol)
                bg_s = pygame.Surface((stxt.get_width() + 6, stxt.get_height() + 2), pygame.SRCALPHA)
                bg_s.fill((*scol, 28))
                surface.blit(bg_s, (icon_x2 - 3, hud_y + 45))
                surface.blit(stxt, (icon_x2, hud_y + 46))
                icon_x2 += stxt.get_width() + 8

        # Battle-cry active glow
        if battle_cry_active:
            msg = self._font_sm.render(t("hud.battle_cry"), True, (252, 180, 0))
            surface.blit(msg, (sx + 148, hud_y + 46))

        # ── LEVEL-UP FLASH ────────────────────────────────────────────────────
        if self._lvup_timer > 0:
            alpha = min(255, int(self._lvup_timer * 130))
            msg   = self._font_lg.render(
                t("hud.level_up", n=player.level), True, _LVUP_COL)
            msg.set_alpha(alpha)
            surface.blit(msg, msg.get_rect(
                center=(SCREEN_WIDTH // 2, (SCREEN_HEIGHT - HUD_HEIGHT) // 2 - 60)))

        # ── STAT POINTS AVAILABLE ─────────────────────────────────────────────
        if player.stat_points > 0:
            if int(pygame.time.get_ticks() / 500) % 2 == 0:
                n = player.stat_points
                sp_msg = self._font_md.render(
                    t("hud.stat_pts", n=n,
                      s="S" if n != 1 else "",
                      e="E" if n != 1 else ""),
                    True, (80, 255, 120))
                surface.blit(sp_msg, sp_msg.get_rect(
                    center=(SCREEN_WIDTH // 2, (SCREEN_HEIGHT - HUD_HEIGHT) // 2 - 38)))

        # Skill points available hint
        if player.skill_tree.skill_points > 0:
            if int(pygame.time.get_ticks() / 700) % 2 == 0:
                n = player.skill_tree.skill_points
                sp2 = self._font_md.render(
                    t("hud.skill_pts", n=n,
                      s="S" if n != 1 else "",
                      e="E" if n != 1 else ""),
                    True, (100, 160, 255))
                surface.blit(sp2, sp2.get_rect(
                    center=(SCREEN_WIDTH // 2, (SCREEN_HEIGHT - HUD_HEIGHT) // 2 - 18)))

        # ── QUEST NOTIFICATIONS ───────────────────────────────────────────────
        qy = (SCREEN_HEIGHT - HUD_HEIGHT) // 2 + 10
        for text, timer in self._quest_msgs:
            fade = min(1.0, timer / 0.6)
            alpha = int(fade * 220)
            qs = self._font_md.render(text, True, (120, 220, 120))
            qs.set_alpha(alpha)
            surface.blit(qs, qs.get_rect(center=(SCREEN_WIDTH // 2, qy)))
            qy += 24
