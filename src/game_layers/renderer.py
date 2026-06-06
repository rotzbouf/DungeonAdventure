import math
import random
import pygame
from src.settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, HUD_HEIGHT, TILE_SIZE,
    VOID_COLOR, RED, YELLOW, WHITE, LIGHT_GRAY, GRAY, GOLD_COLOR,
)
import src.locale as locale
from src.locale import t
from src import save as savesys
from src.version import __version__


class RendererLayer:
    """World, menu, overlay, fog, boss bar, item labels, sparks, bake helpers."""

    def _draw_world(self):
        shk_x = shk_y = 0
        if self._shake_t > 0:
            strength = self._shake_int * (self._shake_t / 0.18)
            shk_x = random.randint(-int(strength), int(strength))
            shk_y = random.randint(-int(strength), int(strength))
            self.camera.x += shk_x
            self.camera.y += shk_y

        self.dungeon.draw(self.screen, self.camera)

        # Stairs portal
        stx, sty = self.dungeon.stairs_pos
        sgx = stx - self.camera.x
        sgy = sty - self.camera.y
        play_h = SCREEN_HEIGHT - HUD_HEIGHT
        if -60 < sgx < SCREEN_WIDTH + 60 and -60 < sgy < play_h + 60:
            pulse = 0.60 + 0.40 * abs(math.sin(self._time * 2.2))
            gr    = int(52 * pulse)
            if gr > 0:
                gs = pygame.Surface((gr*2+4, gr*2+4), pygame.SRCALPHA)
                pygame.draw.circle(gs, (200,175,70, int(60*pulse)), (gr+2,gr+2), gr)
                pygame.draw.circle(gs, (240,220,110,int(100*pulse)), (gr+2,gr+2), gr//2)
                self.screen.blit(gs, (int(sgx)-gr-2, int(sgy)-gr-2))
            spoke_r = int(30 + 6*pulse)
            spoke_d = spoke_r*2+4
            ss      = pygame.Surface((spoke_d, spoke_d), pygame.SRCALPHA)
            for i in range(6):
                ang = self._time*1.1 + i*(math.pi*2/6)
                pygame.draw.line(ss, (220,195,80,int(130*pulse)),
                                 (spoke_d//2+int(math.cos(ang)*7),
                                  spoke_d//2+int(math.sin(ang)*7)),
                                 (spoke_d//2+int(math.cos(ang)*spoke_r),
                                  spoke_d//2+int(math.sin(ang)*spoke_r)), 1)
            self.screen.blit(ss, (int(sgx)-spoke_d//2, int(sgy)-spoke_d//2))

        if math.hypot(self.player.x-stx, self.player.y-sty) < TILE_SIZE*3:
            dsx, dsy = stx-self.camera.x, sty-self.camera.y
            if 0 < dsx < SCREEN_WIDTH and 0 < dsy < play_h:
                hint = self._font_sm.render(t("game.descend"), True, YELLOW)
                self.screen.blit(hint, (int(dsx)-hint.get_width()//2, max(4,int(dsy)-32)))

        for item in self.items:
            if self._is_visible(item.x, item.y):
                item.draw(self.screen, self.camera)
        for chest in self.chests:
            if self._is_visible(chest.rect.centerx, chest.rect.centery):
                chest.draw(self.screen, self.camera)
        for enemy in self.enemies:
            if self._is_visible(enemy.x, enemy.y):
                enemy.draw(self.screen, self.camera)
        for merchant in self.merchants:
            if self._is_visible(merchant.x, merchant.y):
                merchant.draw(self.screen, self.camera)
            if merchant.near_player(self.player):
                mx_s = int(merchant.x - self.camera.x)
                my_s = int(merchant.y - self.camera.y)
                if 0 < mx_s < SCREEN_WIDTH and 4 < my_s < play_h:
                    hint = self._font_sm.render(t("town.shop_hint"), True, (180,110,255))
                    self.screen.blit(hint, (mx_s-hint.get_width()//2, max(4,my_s-40)))

        self.player.draw(self.screen, self.camera)

        # Player hurt ring
        if self._player_hurt_t > 0:
            tf = 1.0 - self._player_hurt_t / 0.28
            r = int(16 + 28*tf)
            a = int(200 * (1.0-tf))
            if r > 1 and a > 0:
                hs = pygame.Surface((r*2+4, r*2+4), pygame.SRCALPHA)
                pygame.draw.circle(hs, (220,30,30,a), (r+2,r+2), r, 3)
                px_ = int(self.player.x - self.camera.x)
                py_ = int(self.player.y - self.camera.y)
                self.screen.blit(hs, (px_-r-2, py_-r-2))

        self._draw_projectiles()
        self._draw_lightning_arcs()
        self._draw_particles()
        self._draw_sconce_flames()
        self._draw_fog()
        self.screen.blit(self._vignette, (0, 0))
        self._draw_item_labels()

        # Damage numbers
        for dn in self._dmg_nums:
            tf     = dn['timer'] / dn['max_timer']
            alpha  = int(255 * min(1.0, tf * 1.6))
            if alpha <= 0:
                continue
            font  = self._font_lg if dn['big'] else self._font_md
            dx_   = int(dn['x'] - self.camera.x)
            dy_   = int(dn['y'] - self.camera.y)
            sh_   = font.render(dn['text'], True, (0,0,0))
            sh_.set_alpha(int(alpha*0.55))
            self.screen.blit(sh_, (dx_-sh_.get_width()//2+1, dy_+1))
            surf_ = font.render(dn['text'], True, dn['color'])
            surf_.set_alpha(alpha)
            self.screen.blit(surf_, (dx_-surf_.get_width()//2, dy_))
            if dn['big'] and alpha > 80:
                gw   = surf_.get_width() + 12
                gs_s = pygame.Surface((gw, surf_.get_height()+8), pygame.SRCALPHA)
                gs_s.fill((220,175,0, int(alpha*0.18)))
                self.screen.blit(gs_s, (dx_-gw//2, dy_-4))

        self.minimap.draw(self.screen, self.player, self.enemies,
                          self.dungeon.stairs_pos,
                          chests=self.chests,
                          merchants=self.merchants,
                          )
        self._draw_boss_bar()
        self.hud.draw(self.screen, self.player, self.dungeon_level,
                      battle_cry_active=self._battle_cry_timer > 0,
                      ice_nova_cd=self._ice_nova_cd,
                      chain_cd=self._chain_cd,
                      blink_cd=self._blink_cd)

        if shk_x or shk_y:
            self.camera.x -= shk_x
            self.camera.y -= shk_y

    def _draw_boss_bar(self):
        boss = next((e for e in self.enemies
                     if getattr(e, 'is_boss', False) and e.alive), None)
        if boss is None:
            return
        bar_w = 500
        bar_h = 18
        bar_x = SCREEN_WIDTH // 2 - bar_w // 2
        bar_y = 10
        pct   = max(0.0, boss.hp / boss.max_hp)
        fill_w = int(bar_w * pct)

        pygame.draw.rect(self.screen, (0, 0, 0), (bar_x - 3, bar_y - 3, bar_w + 6, bar_h + 6))
        pygame.draw.rect(self.screen, (50, 8, 8), (bar_x, bar_y, bar_w, bar_h))
        if fill_w > 0:
            col = ((180, 0, 0)     if pct > 0.50 else
                   (220, 100, 0)   if pct > 0.25 else
                   (220, 30, 30))
            pygame.draw.rect(self.screen, col, (bar_x, bar_y, fill_w, bar_h))
        pygame.draw.rect(self.screen, (160, 30, 30), (bar_x - 3, bar_y - 3, bar_w + 6, bar_h + 6), 2)

        boss_name = getattr(boss, 'BOSS_NAME', type(boss).__name__)
        lbl = self._font_boss.render(f"⚔ {boss_name.upper()} ⚔", True, (220, 175, 0))
        self.screen.blit(lbl, (SCREEN_WIDTH // 2 - lbl.get_width() // 2, bar_y + bar_h + 5))

    def _is_visible(self, wx: float, wy: float) -> bool:
        """
        Return True if world-pixel position (wx, wy) should be drawn:
        it must be within the player torch radius AND have an unobstructed
        line of sight to the player (no walls in between).
        """
        if self.player is None or self.dungeon is None:
            return True   # fallback: always draw when no state available
        dx = wx - self.player.x
        dy = wy - self.player.y
        vis_r = getattr(self, '_torch_vis_r', 360)
        # Quick squared-distance cull (avoids sqrt for most entities)
        if dx * dx + dy * dy > (vis_r + 20) ** 2:
            return False
        # Line-of-sight ray-march through dungeon grid
        return self.dungeon.has_los(self.player.x, self.player.y, wx, wy)

    # Per-theme ambient darkness colour (slightly tinted, not pure black)
    _THEME_AMBIENT = {
        "dungeon": (2,  0, 12, 206), "crypt":   (0,  2,  8, 210),
        "forge":   (12, 4,  0, 203), "inferno": (16, 0,  0, 200),
        "abyss":   (0,  8, 16, 210),
    }

    def _fog_ambient(self) -> tuple:
        from src.world.tile import _THEME_CYCLE
        idx  = ((getattr(self, 'dungeon_level', 1) - 1) // 5) % len(_THEME_CYCLE)
        return self._THEME_AMBIENT.get(_THEME_CYCLE[idx], (0, 0, 0, 208))

    def _draw_fog(self):
        play_h = SCREEN_HEIGHT - HUD_HEIGHT

        # Fill with per-theme tinted ambient darkness
        self._fog.fill(self._fog_ambient())

        px = int(self.player.x - self.camera.x)
        py = int(self.player.y - self.camera.y)

        # ── Player torch (large, warm flicker) ───────────────────────────────
        raw = (math.sin(self._time*5.3)*1.4 + math.sin(self._time*3.1)*0.6 + 2.0) / 4.0
        idx = int(raw * len(self._torch_masks)) % len(self._torch_masks)
        r, mask = self._torch_masks[idx]
        self._fog.blit(mask, (px - r, py - r), special_flags=pygame.BLEND_RGBA_SUB)

        # ── Sconce lights (smaller, independently flickering) ─────────────────
        sconces = getattr(getattr(self, 'dungeon', None), 'sconce_positions', [])
        for sx_, sy_ in sconces:
            scx = int(sx_ - self.camera.x)
            scy = int(sy_ - self.camera.y)
            if not (-140 < scx < SCREEN_WIDTH + 140 and -140 < scy < play_h + 140):
                continue
            phase = ((int(sx_) * 7 + int(sy_) * 13) % 100) * 0.0628
            fi = (math.sin(self._time * 8.7 + phase) * 0.8 +
                  math.sin(self._time * 11.3 + phase * 1.3) * 0.2 + 1.0) / 2.0
            si = int(fi * len(self._sconce_masks)) % len(self._sconce_masks)
            sr, smask = self._sconce_masks[si]
            self._fog.blit(smask, (scx - sr, scy - sr), special_flags=pygame.BLEND_RGBA_SUB)

        # ── Stairs portal glow ────────────────────────────────────────────────
        if self.dungeon:
            stx_, sty_ = self.dungeon.stairs_pos
            ssx = int(stx_ - self.camera.x)
            ssy = int(sty_ - self.camera.y)
            if -200 < ssx < SCREEN_WIDTH + 200 and -200 < ssy < play_h + 200:
                pulse_i = int(((math.sin(self._time*2.8)+1)/2) * len(self._stair_masks)) % len(self._stair_masks)
                ssr, stmask = self._stair_masks[pulse_i]
                self._fog.blit(stmask, (ssx - ssr, ssy - ssr), special_flags=pygame.BLEND_RGBA_SUB)

        self.screen.blit(self._fog, (0, 0))

        # ── Warm colour tint over player torch area ───────────────────────────
        gw   = int(r * 0.32 + math.sin(self._time*7.1)*3)
        warm = pygame.Surface((gw*2, gw*2), pygame.SRCALPHA)
        pygame.draw.circle(warm, (60, 24, 0, 26), (gw, gw), gw)
        self.screen.blit(warm, (px - gw, py - gw))

        # ── Warm tint over each visible sconce ────────────────────────────────
        for sx_, sy_ in sconces:
            scx = int(sx_ - self.camera.x)
            scy = int(sy_ - self.camera.y)
            if not (-60 < scx < SCREEN_WIDTH + 60 and -60 < scy < play_h + 60):
                continue
            sw2 = 28
            ws = pygame.Surface((sw2*2, sw2*2), pygame.SRCALPHA)
            pygame.draw.circle(ws, (62, 28, 0, 18), (sw2, sw2), sw2)
            self.screen.blit(ws, (scx - sw2, scy - sw2))

    def _draw_sconce_flames(self):
        """Animated torch flames at dungeon sconce positions."""
        play_h  = SCREEN_HEIGHT - HUD_HEIGHT
        sconces = getattr(getattr(self, 'dungeon', None), 'sconce_positions', [])
        for sx_, sy_ in sconces:
            fx = int(sx_ - self.camera.x)
            fy = int(sy_ - self.camera.y)
            if not (-20 < fx < SCREEN_WIDTH + 20 and -20 < fy < play_h + 20):
                continue
            phase   = ((int(sx_)*7 + int(sy_)*13) % 100) * 0.0628
            flicker = 0.65 + 0.35 * math.sin(self._time * 9.2 + phase)
            rf      = int(5 + 3 * flicker)
            gs = pygame.Surface((rf*4+2, rf*4+2), pygame.SRCALPHA)
            pygame.draw.circle(gs, (255, 110, 20, int(38*flicker)), (rf*2+1, rf*2+1), rf*2)
            self.screen.blit(gs, (fx - rf*2 - 1, fy - rf*2 - 1))
            pygame.draw.circle(self.screen, (255, int(155+80*flicker), 20), (fx, fy), rf)
            pygame.draw.circle(self.screen, (255, 220, 80), (fx, fy), max(1, rf//2))

    @staticmethod
    def _bake_light(radius: int) -> pygame.Surface:
        d    = radius * 2
        surf = pygame.Surface((d, d), pygame.SRCALPHA)
        for r in range(radius, -1, -3):
            a = int(200 * (1.0 - r/radius)**0.55)
            pygame.draw.circle(surf, (0,0,0,a), (radius,radius), r)
        return surf

    @staticmethod
    def _bake_vignette() -> pygame.Surface:
        w, h  = SCREEN_WIDTH, SCREEN_HEIGHT - HUD_HEIGHT
        surf  = pygame.Surface((w, h), pygame.SRCALPHA)
        depth = 200
        for i in range(depth, 0, -3):
            t = 1 - i/depth
            a = int(t**2.5 * 90)
            pygame.draw.rect(surf, (0,0,0,a),
                             (depth-i, depth-i,
                              w-2*(depth-i), h-2*(depth-i)), 3)
        return surf

    def _update_sparks(self, dt: float):
        if random.random() < dt * 10:
            l = random.uniform(1.8, 4.2)
            self._sparks.append({
                'x': random.uniform(SCREEN_WIDTH*0.25, SCREEN_WIDTH*0.75),
                'y': random.uniform(SCREEN_HEIGHT*0.55, SCREEN_HEIGHT*0.88),
                'vx': random.uniform(-18, 18),
                'vy': random.uniform(-55, -18),
                'life': l, 'max': l,
                'sz': random.uniform(1.4, 3.2),
            })
        for s in self._sparks:
            s['x']    += s['vx'] * dt
            s['y']    += s['vy'] * dt
            s['vx']   += random.uniform(-8, 8) * dt * 10
            s['life'] -= dt
        self._sparks = [s for s in self._sparks if s['life'] > 0]

    def _item_label(self, item) -> tuple:
        from src.items.item import GoldPile, HealthPotion, EquipItem
        if isinstance(item, GoldPile):
            gf = self.player.gold_find_bonus if self.player else 0
            label = f"{item.amount} Gold"
            if gf > 0:
                label += f" (+{int(gf)}%)"
            return label, GOLD_COLOR
        if isinstance(item, HealthPotion):
            return f"Health Potion  +{item.heal_amount} HP", (240,100,100)
        if isinstance(item, EquipItem):
            return item.display_name, item.quality_color
        return "Item", WHITE

    def _draw_item_labels(self):
        play_h = SCREEN_HEIGHT - HUD_HEIGHT
        for item in self.items:
            dist = math.hypot(item.x-self.player.x, item.y-self.player.y)
            if dist > TILE_SIZE * 2.5:
                continue
            fade  = 1.0 - max(0.0, dist-TILE_SIZE) / (TILE_SIZE*1.5)
            alpha = int(fade * 215)
            if alpha <= 0:
                continue
            label, col = self._item_label(item)
            sx = int(item.x - self.camera.x)
            sy = int(item.y - self.camera.y) - 20
            if not (0 < sx < SCREEN_WIDTH and 4 < sy < play_h):
                continue
            txt = self._font_sm.render(label, True, col)
            w, h = txt.get_size()
            bg = pygame.Surface((w+10, h+6), pygame.SRCALPHA)
            bg.fill((6,3,1,min(175, int(alpha*0.82))))
            self.screen.blit(bg,  (sx-(w+10)//2, sy-3))
            txt.set_alpha(alpha)
            self.screen.blit(txt, (sx-w//2, sy))

    # ── Menu decoration sprite cache ──────────────────────────────────────────
    _MENU_SPR: dict = {}

    @classmethod
    def _menu_spr(cls, path_str: str, size: int) -> "pygame.Surface | None":
        key = (path_str, size)
        if key in cls._MENU_SPR:
            return cls._MENU_SPR[key]
        import pathlib
        p = pathlib.Path(path_str)
        spr = None
        if p.exists():
            try:
                raw = pygame.image.load(str(p)).convert_alpha()
                spr = pygame.transform.scale(raw, (size, size))
            except Exception:
                pass
        cls._MENU_SPR[key] = spr
        return spr

    def _draw_menu(self):
        self.screen.fill((0, 0, 0))
        cx = SCREEN_WIDTH // 2

        _STONE    = (68, 100, 176)
        _STONE_HI = (112, 152, 220)
        _MORTAR   = (0,   8,  52)
        _GOLD     = (220, 175,   0)
        _DIM      = (90,  80, 120)

        # ── Stone border tiles ────────────────────────────────────────────────
        for ty in range(0, SCREEN_HEIGHT, TILE_SIZE):
            for tx in range(0, SCREEN_WIDTH, TILE_SIZE):
                if (tx == 0 or ty == 0 or
                        tx >= SCREEN_WIDTH - TILE_SIZE or
                        ty >= SCREEN_HEIGHT - TILE_SIZE):
                    pygame.draw.rect(self.screen, _MORTAR,
                                     (tx, ty, TILE_SIZE, TILE_SIZE))
                    pygame.draw.rect(self.screen, _STONE,
                                     (tx+1, ty+1, TILE_SIZE-2, TILE_SIZE-2))
                    pygame.draw.line(self.screen, _STONE_HI,
                                     (tx+1, ty+1), (tx+TILE_SIZE-2, ty+1))

        # ── Sparks ────────────────────────────────────────────────────────────
        for s in self._sparks:
            tf  = s['life'] / s['max']
            a   = int(min(255, tf * 230))
            r   = max(1, int(s['sz'] * tf))
            col = (min(255, int(195+tf*60)), int(105*tf*tf), 0)
            gs  = pygame.Surface((r*4+2, r*4+2), pygame.SRCALPHA)
            pygame.draw.circle(gs, (*col, a//3), (r*2+1, r*2+1), r*2)
            pygame.draw.circle(gs, (*col, a),    (r*2+1, r*2+1), r)
            self.screen.blit(gs, (int(s['x'])-r*2-1, int(s['y'])-r*2-1))

        # ── Title ─────────────────────────────────────────────────────────────
        pulse    = 0.88 + 0.12 * math.sin(self._time * 2.2)
        ycol     = tuple(int(c * pulse) for c in YELLOW)
        title_cy = int(SCREEN_HEIGHT * 0.19)
        t_sh     = self._font_xl.render("DUNGEON ADVENTURE", True, (0, 0, 0))
        t_lbl    = self._font_xl.render("DUNGEON ADVENTURE", True, ycol)
        self.screen.blit(t_sh,  t_sh.get_rect(center=(cx+3, title_cy+3)))
        self.screen.blit(t_lbl, t_lbl.get_rect(center=(cx,   title_cy)))

        # ── Subtitle ──────────────────────────────────────────────────────────
        sub_cy = int(SCREEN_HEIGHT * 0.28)
        sub    = self._font_lg.render(t("menu.subtitle"), True, WHITE)
        self.screen.blit(sub, sub.get_rect(center=(cx, sub_cy)))

        # ── Top divider ───────────────────────────────────────────────────────
        div_y = int(SCREEN_HEIGHT * 0.36)
        pygame.draw.line(self.screen, _STONE_HI, (cx-320, div_y), (cx-14, div_y), 1)
        pygame.draw.polygon(self.screen, _GOLD,
                            [(cx, div_y-7), (cx+7, div_y), (cx, div_y+7), (cx-7, div_y)])
        pygame.draw.line(self.screen, _STONE_HI, (cx+14, div_y), (cx+320, div_y), 1)

        # ── Decorative statues ────────────────────────────────────────────────
        DCSS = "assets/Dungeon Crawl Stone Soup Full"
        SPR_SIZE = 224
        statue_left  = self._menu_spr(f"{DCSS}/dungeon/statues/statue_iron.png", SPR_SIZE)
        statue_right = self._menu_spr(f"{DCSS}/dungeon/statues/statue_angel.png", SPR_SIZE)

        BTN_W  = 400
        BTN_H  = 68
        VGAP   = 20
        btn_y0 = int(SCREEN_HEIGHT * 0.41)
        btn_area_cy = btn_y0 + (3 * BTN_H + 2 * VGAP) // 2

        if statue_left:
            sy = btn_area_cy - SPR_SIZE // 2
            # Subtle amber glow behind the statue
            glow = pygame.Surface((SPR_SIZE + 40, SPR_SIZE + 40), pygame.SRCALPHA)
            ga   = int(28 + 14 * math.sin(self._time * 1.6))
            pygame.draw.ellipse(glow, (180, 130, 30, ga),
                                (0, 0, SPR_SIZE + 40, SPR_SIZE + 40))
            self.screen.blit(glow, (cx - 540 - 20, sy - 20))
            self.screen.blit(statue_left, (cx - 540, sy))

        if statue_right:
            sy = btn_area_cy - SPR_SIZE // 2
            flipped = pygame.transform.flip(statue_right, True, False)
            glow = pygame.Surface((SPR_SIZE + 40, SPR_SIZE + 40), pygame.SRCALPHA)
            ga   = int(28 + 14 * math.sin(self._time * 1.6 + 1.0))
            pygame.draw.ellipse(glow, (180, 130, 30, ga),
                                (0, 0, SPR_SIZE + 40, SPR_SIZE + 40))
            self.screen.blit(glow, (cx + 540 - SPR_SIZE - 20, sy - 20))
            self.screen.blit(flipped, (cx + 540 - SPR_SIZE, sy))

        # ── Buttons ───────────────────────────────────────────────────────────
        has_save  = savesys.has_save()
        mouse_pos = pygame.mouse.get_pos()

        _BTN_BG    = (22,  15,  40)
        _BTN_HV    = (48,  34,  78)
        _BTN_BD    = (90,  60, 160)
        _BTN_BD_HV = (220, 175,   0)
        _BTN_DIM   = (48,  42,  60)
        _BTN_BD_DIM= (40,  30,  55)

        btn_defs = [
            ("new_game", t("menu.new_game"), "[Enter]", True),
            ("continue", t("menu.continue"), "[C]",     has_save),
            ("settings", t("menu.settings"), "[S]",     True),
        ]

        self._menu_btn_rects = {}

        for i, (btn_id, label, shortcut, active) in enumerate(btn_defs):
            bx    = cx - BTN_W // 2
            by    = btn_y0 + i * (BTN_H + VGAP)
            brect = pygame.Rect(bx, by, BTN_W, BTN_H)
            self._menu_btn_rects[btn_id] = brect

            hov = active and brect.collidepoint(mouse_pos)

            if not active:
                bg_col, bd_col, txt_col = _BTN_BG, _BTN_BD_DIM, _BTN_DIM
            elif hov:
                bg_col, bd_col, txt_col = _BTN_HV, _BTN_BD_HV, YELLOW
            else:
                bg_col, bd_col, txt_col = _BTN_BG, _BTN_BD, WHITE

            # Button panel + border
            pygame.draw.rect(self.screen, bg_col, brect, border_radius=6)
            pygame.draw.rect(self.screen, bd_col, brect, 2, border_radius=6)

            # Hover: inner highlight line at top
            if hov:
                hi_r = pygame.Rect(bx+3, by+3, BTN_W-6, 2)
                pygame.draw.rect(self.screen, (255, 230, 100, 120), hi_r, border_radius=2)

            # Label
            font = self._font_lg
            lbl_s = font.render(label, True, txt_col)
            self.screen.blit(lbl_s, lbl_s.get_rect(center=brect.center))

            # Shortcut tag
            sc_col = (110, 90, 140) if active else (38, 33, 50)
            sc_s   = self._font_sm.render(shortcut, True, sc_col)
            self.screen.blit(sc_s, sc_s.get_rect(
                left=brect.right + 16, centery=brect.centery))

        # ── Bottom divider ────────────────────────────────────────────────────
        bot_y = btn_y0 + 3 * BTN_H + 2 * VGAP + 28
        pygame.draw.line(self.screen, _STONE_HI, (cx-320, bot_y), (cx-14, bot_y), 1)
        pygame.draw.polygon(self.screen, _GOLD,
                            [(cx, bot_y-7), (cx+7, bot_y), (cx, bot_y+7), (cx-7, bot_y)])
        pygame.draw.line(self.screen, _STONE_HI, (cx+14, bot_y), (cx+320, bot_y), 1)

        # ── Version ───────────────────────────────────────────────────────────
        ver_s = self._font_sm.render(f"v{__version__}", True, (70, 70, 90))
        self.screen.blit(ver_s, ver_s.get_rect(right=SCREEN_WIDTH - 14,
                                                bottom=SCREEN_HEIGHT - 8))

        # ── Language selector (bottom-left) ───────────────────────────────────
        self._lang_btn_rects = {}
        lang_lbl = self._font_sm.render(t("menu.lang_label") + ":", True, _DIM)
        lx = 20
        self.screen.blit(lang_lbl, (lx, SCREEN_HEIGHT - 28))
        lx += lang_lbl.get_width() + 8
        for code, lcode in (("en", "EN"), ("de", "DE")):
            active  = locale.lang() == code
            lc_col  = YELLOW if active else _DIM
            btn_txt = self._font_sm.render(f"[{lcode}]", True, lc_col)
            btn_r   = btn_txt.get_rect(left=lx, top=SCREEN_HEIGHT - 28)
            if active:
                bg = pygame.Surface((btn_r.width + 4, btn_r.height + 2))
                bg.fill((40, 30, 0))
                self.screen.blit(bg, (btn_r.left - 2, btn_r.top - 1))
            self.screen.blit(btn_txt, btn_r)
            self._lang_btn_rects[code] = btn_r
            lx += btn_r.width + 6

    def _draw_overlay(self, title: str, sub: str, color):
        ov = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 172))
        self.screen.blit(ov, (0, 0))
        cy = (SCREEN_HEIGHT - HUD_HEIGHT) // 2
        cx = SCREEN_WIDTH // 2
        pulse = 0.82 + 0.18*math.sin(self._time*3.5)
        pc    = tuple(int(c*pulse) for c in color)
        sh    = self._font_xl.render(title, True, (15,5,5))
        self.screen.blit(sh, sh.get_rect(center=(cx+4,cy-40)))
        ts = self._font_xl.render(title, True, pc)
        s  = self._font_lg.render(sub,   True, WHITE)
        self.screen.blit(ts, ts.get_rect(center=(cx,cy-44)))
        self.screen.blit(s,  s.get_rect(center=(cx,cy+24)))
