import math
import pygame
from src.settings import (SCREEN_WIDTH, SCREEN_HEIGHT, HUD_HEIGHT, LIGHT_GRAY,
                           STATE_TOWN, STATE_PLAYING)
from src.world.town import (PLAYER_SPAWN as TOWN_PLAYER_SPAWN,
                              DUNGEON_ENTRANCE_POS, DUNGEON_INTERACT_R,
                              HOUSE_POS, HOUSE_INTERACT_R,
                              TOWN_BOUNDS, MERCHANT_SPECS,
                              TOWN_W, TOWN_H, merchant_stand_pos)
from src.entities.merchant import TownMerchant
from src import save as savesys
from src.locale import t


class TownLayer:
    """Town entry/exit, merchant shop opening, town update and rendering."""

    def _enter_town(self, rest: bool = True):
        """Switch to STATE_TOWN.  Restocks town merchants and optionally heals."""
        if self.player is None:
            return
        plvl = getattr(self.player, 'level', 1)
        self.town_merchants = [
            TownMerchant(*merchant_stand_pos(px, py), title, spec, plvl)
            for title, spec, px, py in MERCHANT_SPECS
        ]
        self.player.x = float(TOWN_PLAYER_SPAWN[0])
        self.player.y = float(TOWN_PLAYER_SPAWN[1])
        self.player._sync_rect()

        # Close any open overlays
        self.inv_open = self.shop_open = self.char_open = False
        self.quest_open = self.skill_open = self.enchant_open = False
        self.craft_open = self.house_open = False
        self._active_merchant = None

        # Check "clear" quests completed by visiting floors in the dungeon
        clear_done = self.quest_log.on_town_return()
        if clear_done:
            self._apply_quest_rewards(clear_done)

        if rest:
            self.player.hp   = float(self.player.max_hp_total)
            self.player.mana = float(self.player.max_mana_total)
            self._town_notice_msg = t("town.rested")
            self._town_notice_t   = 3.5

        # Position camera so the player's spawn (near gate) is centred
        play_w = SCREEN_WIDTH
        play_h = SCREEN_HEIGHT - HUD_HEIGHT
        sx, sy = TOWN_PLAYER_SPAWN
        self.camera.x = max(0.0, min(sx - play_w / 2, float(TOWN_W - play_w)))
        self.camera.y = max(0.0, min(sy - play_h / 2, float(TOWN_H - play_h)))
        self.state    = STATE_TOWN

    def _return_to_town(self):
        """Send the player back to town to rest (save skipped in multiplayer)."""
        if self.state != STATE_PLAYING or self.player is None:
            return
        if not getattr(self, "net_client", None):
            savesys.save_game(self.player, self.dungeon_level,
                              quest_log=self.quest_log,
                              skill_tree=self.player.skill_tree)
        self._enter_town(rest=True)

    def _enter_dungeon_from_town(self):
        """Leave town and enter the dungeon."""
        if self.player is None:
            return
        nc = getattr(self, "net_client", None)
        if nc and nc.connected:
            # In multiplayer: rejoin the server's current floor
            net_floor = getattr(self, "_net_floor", self.dungeon_level)
            net_seed  = getattr(self, "_net_seed", None)
            self._load_level(net_floor, self.player, seed=net_seed)
            self.dungeon_level = net_floor
        else:
            self._load_level(self.dungeon_level, self.player)
        self.state = STATE_PLAYING

    def _try_open_town_shop(self):
        # House takes priority — open house screen if player is near
        if math.hypot(self.player.x - HOUSE_POS[0],
                      self.player.y - HOUSE_POS[1]) < HOUSE_INTERACT_R:
            self._house_screen.open(
                save_fn=lambda: savesys.save_game(
                    self.player, self.dungeon_level,
                    quest_log=self.quest_log,
                    skill_tree=self.player.skill_tree),
                load_fn=self._load_from_house,
            )
            self.house_open = True
            return

        for m in self.town_merchants:
            if m.near_player(self.player):
                self._active_merchant = m
                if m.specialty == "guild":
                    self._open_quest_giver(m)
                elif m.specialty == "enchant":
                    self._enchant_screen.open()
                    self.enchant_open = True
                elif m.specialty == "craft":
                    self._craft_screen.open()
                    self.craft_open = True
                else:
                    self.shop_open = True
                return

    def _load_from_house(self):
        """Close the house screen then reload the last save."""
        self.house_open = False
        self._continue_game()

    def _update_town(self, dt: float):
        if self.player is None:
            return
        # Smooth-follow camera clamped to town map
        play_w = SCREEN_WIDTH
        play_h = SCREEN_HEIGHT - HUD_HEIGHT
        tx = self.player.x - play_w / 2
        ty = self.player.y - play_h / 2
        tx = max(0.0, min(tx, float(TOWN_W - play_w)))
        ty = max(0.0, min(ty, float(TOWN_H - play_h)))
        lerp = min(1.0, 8.0 * dt)
        self.camera.x += (tx - self.camera.x) * lerp
        self.camera.y += (ty - self.camera.y) * lerp
        # Player walks around town; TOWN_BOUNDS acts as a minimal wall collider
        self.player.update(dt, TOWN_BOUNDS, self.camera)
        for m in self.town_merchants:
            m.update(dt)
        self.shop.update(dt)
        self.inventory.update(dt)
        self.charscreen.update(dt)
        self._enchant_screen.update(dt)
        self._craft_screen.update(dt)
        self._house_screen.update(dt)
        self._town_notice_t = max(0.0, self._town_notice_t - dt)
        # Mana regen handled by player.update above

    def _draw_town(self):
        play_h = SCREEN_HEIGHT - HUD_HEIGHT
        near_entrance = (
            self.player is not None and
            math.hypot(self.player.x - DUNGEON_ENTRANCE_POS[0],
                       self.player.y - DUNGEON_ENTRANCE_POS[1]) < DUNGEON_INTERACT_R
        )
        near_house = (
            self.player is not None and
            math.hypot(self.player.x - HOUSE_POS[0],
                       self.player.y - HOUSE_POS[1]) < HOUSE_INTERACT_R
        )
        cam_x = int(self.camera.x)
        cam_y = int(self.camera.y)

        # Background + entrance + house + stall names
        self.town_renderer.draw(self.screen, self._time, near_entrance, near_house,
                                cam_x, cam_y)

        # Merchant sprites and interaction hints
        for m in self.town_merchants:
            m.draw(self.screen, self.camera)
            if m.near_player(self.player):
                hx = int(m.x) - cam_x
                hy = int(m.y) - 58 - cam_y
                # ── High-contrast interaction badge ────────────────────────
                key_lbl  = self._font_sm.render("[F]", True, (255, 235, 80))
                act_lbl  = self._font_sm.render(t("town.shop_hint").replace("[F]", "").strip(" —").strip(),
                                                 True, (220, 210, 180))
                # Fallback: if translation already has key stripped, use full
                if not act_lbl.get_width():
                    act_lbl = self._font_sm.render(t("town.shop_hint"), True, (220, 210, 180))
                pad  = 8
                gap  = 6
                bw   = pad + key_lbl.get_width() + gap + act_lbl.get_width() + pad
                bh   = key_lbl.get_height() + pad
                bx_  = hx - bw // 2
                by_  = hy - bh // 2
                # Dark pill background
                bg   = pygame.Surface((bw, bh), pygame.SRCALPHA)
                bg.fill((0, 0, 0, 210))
                pygame.draw.rect(bg, (180, 155, 40), (0, 0, bw, bh), 2)
                self.screen.blit(bg, (bx_, by_))
                # Key badge + action text
                self.screen.blit(key_lbl, (bx_ + pad, by_ + pad // 2))
                self.screen.blit(act_lbl, (bx_ + pad + key_lbl.get_width() + gap,
                                            by_ + pad // 2))

        # Player
        self.player.draw(self.screen, self.camera)

        # HUD (bottom strip)
        self.hud.draw(self.screen, self.player, self.dungeon_level)

        # "Rested" notice
        if self._town_notice_t > 0:
            alpha = min(255, int(self._town_notice_t * 100))
            self.town_renderer.draw_return_notice(self.screen, self._town_notice_msg)
            # fade by adjusting alpha via a cover surface if needed
            _ = alpha  # alpha already baked into draw_return_notice

        # Overlays (house, inventory, shop, enchant, craft, char screen, skill tree)
        if self.quest_giver_open:
            self._quest_giver_screen.draw(self.screen)
        elif self.house_open:
            self._house_screen.draw(self.screen, self.player)
        elif self.enchant_open:
            self._enchant_screen.draw(self.screen, self.player)
        elif self.craft_open:
            self._craft_screen.draw(self.screen, self.player)
        elif self.inv_open:
            self.inventory.draw(self.screen, self.player)
        elif self.shop_open and self._active_merchant:
            self.shop.draw(self.screen, self._active_merchant, self.player)
        elif self.char_open:
            self.charscreen.draw(self.screen, self.player)
        elif self.skill_open:
            self.skillscreen.draw(self.screen, self.player)
        elif self.quest_open:
            self.questlog_ui.draw(self.screen, self.quest_log)

        # Key hints footer
        hint_line = self._font_sm.render(
            t("town.footer", n=self.dungeon_level),
            True, LIGHT_GRAY)
        hy2 = SCREEN_HEIGHT - HUD_HEIGHT - 16
        bg_s = pygame.Surface((hint_line.get_width() + 16, hint_line.get_height() + 6),
                               pygame.SRCALPHA)
        bg_s.fill((0, 0, 0, 140))
        self.screen.blit(bg_s, bg_s.get_rect(centerx=SCREEN_WIDTH // 2, centery=hy2))
        self.screen.blit(hint_line, hint_line.get_rect(
            centerx=SCREEN_WIDTH // 2, centery=hy2))
