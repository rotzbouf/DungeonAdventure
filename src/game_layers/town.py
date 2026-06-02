import math
import pygame
from src.settings import (SCREEN_WIDTH, SCREEN_HEIGHT, HUD_HEIGHT, LIGHT_GRAY,
                           STATE_TOWN, STATE_PLAYING)
from src.world.town import (PLAYER_SPAWN as TOWN_PLAYER_SPAWN,
                              DUNGEON_ENTRANCE_POS, DUNGEON_INTERACT_R,
                              TOWN_BOUNDS, MERCHANT_SPECS)
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
            TownMerchant(px, py, title, spec, plvl)
            for title, spec, px, py in MERCHANT_SPECS
        ]
        self.player.x = float(TOWN_PLAYER_SPAWN[0])
        self.player.y = float(TOWN_PLAYER_SPAWN[1])
        self.player._sync_rect()

        # Close any open overlays
        self.inv_open = self.shop_open = self.char_open = False
        self.quest_open = self.skill_open = self.enchant_open = self.craft_open = False
        self._active_merchant = None

        if rest:
            self.player.hp   = float(self.player.max_hp_total)
            self.player.mana = float(self.player.max_mana_total)
            self._town_notice_msg = t("town.rested")
            self._town_notice_t   = 3.5

        # Lock camera at (0,0) for the fixed-size town view
        self.camera.x = 0.0
        self.camera.y = 0.0
        self.state    = STATE_TOWN

    def _return_to_town(self):
        """Save the game and send the player back to town to rest."""
        if self.state != STATE_PLAYING or self.player is None:
            return
        savesys.save_game(self.player, self.dungeon_level,
                          quest_log=self.quest_log,
                          skill_tree=self.player.skill_tree)
        self._enter_town(rest=True)

    def _enter_dungeon_from_town(self):
        """Leave town and enter the dungeon at the last-saved floor."""
        if self.player is None:
            return
        self._load_level(self.dungeon_level, self.player)
        self.state = STATE_PLAYING

    def _try_open_town_shop(self):
        for m in self.town_merchants:
            if m.near_player(self.player):
                self._active_merchant = m
                if m.specialty == "enchant":
                    self._enchant_screen.open()
                    self.enchant_open = True
                elif m.specialty == "craft":
                    self._craft_screen.open()
                    self.craft_open = True
                else:
                    self.shop_open = True
                return

    def _update_town(self, dt: float):
        if self.player is None:
            return
        # Player walks around town; TOWN_BOUNDS acts as a minimal wall collider
        self.player.update(dt, TOWN_BOUNDS, self.camera)
        for m in self.town_merchants:
            m.update(dt)
        self.shop.update(dt)
        self.inventory.update(dt)
        self.charscreen.update(dt)
        self._enchant_screen.update(dt)
        self._craft_screen.update(dt)
        self._town_notice_t = max(0.0, self._town_notice_t - dt)
        # Mana regen handled by player.update above

    def _draw_town(self):
        play_h = SCREEN_HEIGHT - HUD_HEIGHT
        near_entrance = (
            self.player is not None and
            math.hypot(self.player.x - DUNGEON_ENTRANCE_POS[0],
                       self.player.y - DUNGEON_ENTRANCE_POS[1]) < DUNGEON_INTERACT_R
        )
        # Background + entrance + stall names
        self.town_renderer.draw(self.screen, self._time, near_entrance)

        # Merchant sprites and interaction hints
        for m in self.town_merchants:
            m.draw(self.screen, self.camera)   # camera is zeroed in town
            if m.near_player(self.player):
                hx = int(m.x)
                hy = int(m.y) - 50
                hi_col = m._palette.get("robe_h", (220, 220, 220))
                hint = self._font_sm.render(t("town.shop_hint"), True, hi_col)
                self.screen.blit(hint, hint.get_rect(centerx=hx, centery=hy))

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

        # Overlays (inventory, shop, enchant, craft, char screen, skill tree)
        if self.enchant_open:
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
