import math
import random
import sys
import pygame

from src.settings import (SCREEN_WIDTH, SCREEN_HEIGHT, HUD_HEIGHT, TILE_SIZE,
                           TITLE, FPS, VOID_COLOR, RED, YELLOW, WHITE,
                           LIGHT_GRAY, GRAY, GOLD_COLOR,
                           STATE_MENU, STATE_PLAYING, STATE_GAME_OVER, STATE_TOWN,
                           BOSS_FLOOR_INTERVAL,
                           ARROW_SPEED, ARROW_MAX_RANGE,
                           FIREBALL_MANA_COST, FIREBALL_SPEED, FIREBALL_MAX_RANGE,
                           FIREBALL_DAMAGE, FIREBALL_RADIUS, STATUS_BURN,
                           ICE_NOVA_MANA_COST, ICE_NOVA_DAMAGE, ICE_NOVA_RADIUS,
                           ICE_NOVA_SLOW_DUR, ICE_NOVA_COOLDOWN, STATUS_FREEZE,
                           CHAIN_LIGHTNING_MANA_COST, CHAIN_LIGHTNING_DAMAGE,
                           CHAIN_LIGHTNING_JUMPS, CHAIN_LIGHTNING_RANGE,
                           CHAIN_LIGHTNING_COOLDOWN,
                           BLINK_MANA_COST, BLINK_COOLDOWN,
                           BATTLE_CRY_MANA_COST, BATTLE_CRY_DURATION,
                           WHIRLWIND_MANA_COST)
from src.utils.camera      import Camera
from src.world.dungeon     import Dungeon
from src.world.town        import (TownRenderer, TOWN_BOUNDS,
                                   PLAYER_SPAWN as TOWN_PLAYER_SPAWN,
                                   DUNGEON_ENTRANCE_POS, DUNGEON_INTERACT_R,
                                   MERCHANT_SPECS)
from src.entities.player   import Player
from src.entities.enemy    import (get_enemy_types,
                                   Lich, DemonLord, StoneGolem,
                                   VampireLord, ElderDragon, IronColossus)
from src.entities.merchant import Merchant, TownMerchant
from src.items.item        import GoldPile, random_item, random_equip, QUALITY_RARE, QUALITY_UNIQUE, TreasureChest
from src.ui.hud            import HUD
from src.ui.minimap        import Minimap
from src.ui.inventory      import InventoryScreen
from src.ui.shop           import ShopScreen
from src.ui.charscreen     import CharScreen
from src.ui.questlog       import QuestLogScreen
from src.ui.skillscreen    import SkillScreen
from src.ui.enchant_screen import EnchantScreen
from src.quests            import QuestLog
from src import save as savesys
import src.locale as locale
from src.locale import t, t_quest_name

from src.game_layers.session    import SessionLayer
from src.game_layers.town       import TownLayer
from src.game_layers.combat     import CombatLayer
from src.game_layers.spells     import SpellLayer
from src.game_layers.projectiles import ProjectileLayer
from src.game_layers.particles  import ParticleLayer
from src.game_layers.traps      import TrapLayer
from src.game_layers.renderer   import RendererLayer


class Game(SessionLayer, TownLayer, CombatLayer, SpellLayer, ProjectileLayer, ParticleLayer, TrapLayer, RendererLayer):
    def __init__(self):
        self.screen = pygame.display.set_mode(
            (SCREEN_WIDTH, SCREEN_HEIGHT),
            pygame.FULLSCREEN | pygame.HWSURFACE | pygame.DOUBLEBUF)
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()

        self._font_xl   = pygame.font.SysFont("monospace", 52, bold=True)
        self._font_lg   = pygame.font.SysFont("monospace", 30, bold=True)
        self._font_md   = pygame.font.SysFont("monospace", 22)
        self._font_sm   = pygame.font.SysFont("monospace", 16)
        self._font_boss = pygame.font.SysFont("monospace", 13, bold=True)

        self.state         = STATE_MENU
        self.dungeon_level = 1
        self.player: Player | None  = None
        self.dungeon: Dungeon | None = None
        self.enemies: list = []
        self.items:   list = []
        self.camera        = Camera()
        self.hud           = HUD()
        self.minimap       = Minimap()
        self.inventory     = InventoryScreen()
        self.shop          = ShopScreen()
        self.charscreen    = CharScreen()
        self.questlog_ui   = QuestLogScreen()
        self.skillscreen   = SkillScreen()
        self.quest_log     = QuestLog()

        self.inv_open        = False
        self.shop_open       = False
        self.char_open       = False
        self.quest_open      = False
        self.skill_open      = False
        self.enchant_open    = False
        self._enchant_screen = EnchantScreen()
        self._active_merchant: Merchant | None = None

        self._dmg_nums: list = []
        self.chests:    list = []
        self.projectiles: list = []
        self.merchants:   list = []

        # ── Town ─────────────────────────────────────────────────────────────
        self.town_renderer    = TownRenderer()
        self.town_merchants:  list = []    # TownMerchant instances
        self._town_notice_t   = 0.0        # "Rested" banner timer
        self._town_notice_msg = ""

        self._time      = 0.0
        self._shake_t   = 0.0
        self._shake_int = 0.0
        self._hitstop_t = 0.0
        self._sparks:    list = []
        self._particles: list = []
        self._lang_btn_rects: dict = {}   # populated by _draw_menu, read by events

        self._player_hurt_t    = 0.0
        self._transition_timer = 0.0
        self._transition_level: int | None = None

        self._spike_phase = "idle"
        self._spike_timer = 2.5
        self._trap_dmg_cd = 0.0

        # Spell cooldowns
        self._ice_nova_cd      = 0.0
        self._chain_cd         = 0.0
        self._blink_cd         = 0.0
        self._battle_cry_timer = 0.0   # remaining active seconds

        # Lightning arc segments for Chain Lightning visual
        self._lightning_arcs: list = []

        self._torch_masks = [(r, self._bake_light(r))
                             for r in (475, 490, 503, 513, 522)]
        self._fog      = pygame.Surface(
            (SCREEN_WIDTH, SCREEN_HEIGHT - HUD_HEIGHT), pygame.SRCALPHA)
        self._vignette = self._bake_vignette()

    # ─── Main loop ───────────────────────────────────────────────────────────────

    def run(self):
        while True:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.05)
            self._handle_events()
            self._update(dt)
            self._draw()

    # ─── Events ──────────────────────────────────────────────────────────────────

    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()

            if event.type == pygame.KEYDOWN:
                k = event.key

                if k == pygame.K_ESCAPE:
                    if self.enchant_open:self.enchant_open = False
                    elif self.inv_open:   self.inv_open   = False
                    elif self.shop_open:  self.shop_open  = False
                    elif self.char_open:  self.char_open  = False
                    elif self.quest_open: self.quest_open = False
                    elif self.skill_open: self.skill_open = False
                    elif self.state == STATE_PLAYING:
                        self.state = STATE_MENU
                    elif self.state == STATE_TOWN:
                        self.state = STATE_MENU
                    else:
                        pygame.quit(); sys.exit()

                if k == pygame.K_RETURN:
                    if self.state == STATE_MENU:
                        self._new_game()
                    elif self.state == STATE_GAME_OVER:
                        self.state = STATE_MENU

                # "Continue" from menu (only on title screen when save exists)
                if k == pygame.K_c and self.state == STATE_MENU:
                    if savesys.has_save():
                        self._continue_game()

                # Language toggle — L key on menu
                if k == pygame.K_l and self.state == STATE_MENU:
                    locale.set_lang("de" if locale.lang() == "en" else "en")

                any_overlay = (self.inv_open or self.shop_open or self.char_open
                               or self.quest_open or self.skill_open)

                # ── Town keys ──────────────────────────────────────────────
                if self.state == STATE_TOWN:
                    any_town_overlay = (self.shop_open or self.enchant_open)
                    if k == pygame.K_f and not any_town_overlay:
                        self._try_open_town_shop()
                    elif k == pygame.K_f and self.shop_open:
                        self.shop_open = False
                        self._active_merchant = None
                    elif k == pygame.K_f and self.enchant_open:
                        self.enchant_open = False
                        self._active_merchant = None
                    if k == pygame.K_e and not any_town_overlay:
                        if math.hypot(self.player.x - DUNGEON_ENTRANCE_POS[0],
                                      self.player.y - DUNGEON_ENTRANCE_POS[1]) < DUNGEON_INTERACT_R:
                            self._enter_dungeon_from_town()
                    if k in (pygame.K_i, pygame.K_TAB):
                        if not any_town_overlay:
                            self.inv_open = not self.inv_open
                    if k == pygame.K_c and not any_town_overlay and not self.inv_open:
                        self.char_open = not self.char_open
                    if k == pygame.K_k:
                        self.skill_open = not self.skill_open
                        if self.skill_open:
                            self.inv_open = self.shop_open = self.char_open = False

                # ── Dungeon keys ───────────────────────────────────────────
                if self.state == STATE_PLAYING and not any_overlay:
                    if k == pygame.K_t:
                        self._return_to_town()
                if self.state == STATE_PLAYING and not any_overlay:
                    if k == pygame.K_SPACE:
                        mods = pygame.key.get_mods()
                        if (mods & pygame.KMOD_SHIFT and
                                self.player.skill_tree.has_whirlwind() and
                                self.player.mana >= WHIRLWIND_MANA_COST):
                            self._cast_whirlwind()
                        elif self.player.has_bow:
                            self._fire_arrow()
                        else:
                            self._player_attack()
                    if k == pygame.K_z: self._cast_fireball()
                    if k == pygame.K_x: self._cast_ice_nova()
                    if k == pygame.K_r: self._cast_chain_lightning()
                    if k == pygame.K_v: self._cast_blink()
                    if k == pygame.K_b: self._cast_battle_cry()
                    if k == pygame.K_e: self._try_descend()
                    if k == pygame.K_q:
                        if self.player.use_potion():
                            self.inventory.notify(
                                t("game.used_potion", n=len(self.player.potions)))

                if self.state == STATE_PLAYING:
                    if k in (pygame.K_i, pygame.K_TAB):
                        if not self.shop_open and not self.char_open and not self.skill_open:
                            self.inv_open = not self.inv_open
                    if k == pygame.K_c and not self.shop_open and not self.inv_open:
                        self.char_open = not self.char_open
                    if k == pygame.K_j:
                        self.quest_open = not self.quest_open
                        if self.quest_open:
                            self.inv_open = self.shop_open = self.char_open = self.skill_open = False
                    if k == pygame.K_k:
                        self.skill_open = not self.skill_open
                        if self.skill_open:
                            self.inv_open = self.shop_open = self.char_open = self.quest_open = False
                    if k == pygame.K_f:
                        if self.shop_open:
                            self.shop_open = False
                        elif not any_overlay:
                            self._try_open_shop()

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.state == STATE_MENU:
                    for code, rect in self._lang_btn_rects.items():
                        if rect.collidepoint(event.pos):
                            locale.set_lang(code)
                            break

            if event.type == pygame.MOUSEBUTTONDOWN and self.state in (STATE_PLAYING, STATE_TOWN):
                if self.enchant_open:
                    self._enchant_screen.handle_event(event, self.player)
                elif self.inv_open and event.button == 1:
                    self.inventory.handle_click(*event.pos, self.player)
                elif self.shop_open and self._active_merchant:
                    self.shop.handle_click(*event.pos, event.button,
                                           self._active_merchant, self.player)
                elif self.char_open and event.button == 1:
                    self.charscreen.handle_click(*event.pos, self.player)
                elif self.skill_open and event.button == 1:
                    self.skillscreen.handle_click(*event.pos, self.player)

            if event.type == pygame.MOUSEWHEEL and self.enchant_open:
                self._enchant_screen.handle_event(event, self.player)

    # ─── Update ──────────────────────────────────────────────────────────────────

    def _update(self, dt: float):
        self._time   += dt
        self._shake_t = max(0.0, self._shake_t - dt)

        if self.state == STATE_MENU:
            self._update_sparks(dt)
            return
        if self.state == STATE_TOWN:
            self._update_town(dt)
            return
        if self.state != STATE_PLAYING:
            return

        # Spell cooldowns
        self._ice_nova_cd = max(0.0, self._ice_nova_cd - dt)
        self._chain_cd    = max(0.0, self._chain_cd    - dt)
        self._blink_cd    = max(0.0, self._blink_cd    - dt)

        # Battle cry countdown
        if self._battle_cry_timer > 0:
            self._battle_cry_timer = max(0.0, self._battle_cry_timer - dt)

        # Lightning arc lifetime
        self._lightning_arcs = [a for a in self._lightning_arcs
                                 if (a.__setitem__('timer', a['timer'] - dt) or True)
                                 and a['timer'] > 0]

        # Floor transition
        if self._transition_timer > 0:
            prev_t = self._transition_timer
            self._transition_timer -= dt
            self._player_hurt_t = max(0.0, self._player_hurt_t - dt)
            if prev_t > 0.26 >= self._transition_timer and self._transition_level:
                self._load_level(self._transition_level, self.player)
                self._transition_level = None
            return

        self._update_particles(dt)
        self.inventory.update(dt)
        self.shop.update(dt)
        self.charscreen.update(dt)

        if self.inv_open or self.shop_open or self.char_open or self.quest_open or self.skill_open:
            return

        if self._hitstop_t > 0:
            self._hitstop_t -= dt
            self.hud.update(dt)
            self.camera.update(self.player, self.dungeon, dt)
            return

        self._player_hurt_t = max(0.0, self._player_hurt_t - dt)
        self.player.update(dt, self.dungeon, self.camera)
        self.camera.update(self.player, self.dungeon, dt)
        self.hud.update(dt)

        for merchant in self.merchants:
            merchant.update(dt)

        prev_hp = self.player.hp
        for enemy in self.enemies:
            enemy.update(dt, self.player, self.dungeon)
        self.enemies = [e for e in self.enemies if e.alive]
        if self.player.hp < prev_hp:
            self._shake_t       = 0.22
            self._shake_int     = 6.0
            self._player_hurt_t = 0.28
            hit_dmg = int(prev_hp - self.player.hp)
            if hit_dmg > 0:
                self._dmg_nums.append({
                    'x': self.player.x, 'y': self.player.y - 30,
                    'vx': random.uniform(-20, 20),
                    'text': f"-{hit_dmg}",
                    'timer': 0.80, 'max_timer': 0.80,
                    'color': (220, 60, 60), 'big': False,
                })

        for item in self.items:
            if not item.collected:
                item.update(dt)
                if self.player.rect.colliderect(item.rect):
                    # Quest: gold collection
                    from src.items.item import GoldPile as _GP
                    if isinstance(item, _GP):
                        done = self.quest_log.notify("collect", "gold", item.amount)
                        self._apply_quest_rewards(done)
                    item.collect(self.player)
                    self._spawn_pickup_sparkle(item.x, item.y)
        self.items = [i for i in self.items if not i.collected]

        for chest in self.chests:
            chest.update(dt)
            if not chest.opened and self.player.rect.colliderect(chest.rect):
                chest.open(self.player, self.items, self.dungeon_level)
                self._shake_t   = 0.18
                self._shake_int = 5.0

        self._update_projectiles(dt)
        self._update_traps(dt)

        # Quest completion pop-up
        for msg in self.quest_log.pop_notifications():
            self.hud.notify_quest(msg)

        for dn in self._dmg_nums:
            dn['y']     -= 32 * dt
            dn['x']     += dn['vx'] * dt
            dn['timer'] -= dt
        self._dmg_nums = [d for d in self._dmg_nums if d['timer'] > 0]

        if not self.player.is_alive():
            savesys.delete_save()
            self.state = STATE_GAME_OVER

    # ─── Draw ────────────────────────────────────────────────────────────────────

    def _draw(self):
        self.screen.fill(VOID_COLOR)

        if self.state == STATE_MENU:
            self._draw_menu()
        elif self.state == STATE_TOWN:
            self._draw_town()
        elif self.state == STATE_PLAYING:
            self._draw_world()
            if self.inv_open:
                self.inventory.draw(self.screen, self.player)
            elif self.shop_open and self._active_merchant:
                self.shop.draw(self.screen, self._active_merchant, self.player)
            elif self.char_open:
                self.charscreen.draw(self.screen, self.player)
            elif self.quest_open:
                self.questlog_ui.draw(self.screen, self.quest_log)
            elif self.skill_open:
                self.skillscreen.draw(self.screen, self.player)
            if self._transition_timer > 0:
                raw_a = 1.0 - abs(self._transition_timer / 0.26 - 1.0)
                a_val = int(max(0, min(255, raw_a * 255)))
                if a_val > 0:
                    fade_s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
                    fade_s.fill((0, 0, 0))
                    fade_s.set_alpha(a_val)
                    self.screen.blit(fade_s, (0, 0))
        elif self.state == STATE_GAME_OVER:
            if self.dungeon is not None:
                self._draw_world()
            else:
                self.screen.fill((0, 0, 0))
            self._draw_overlay(t("game.game_over"), t("game.press_enter"), RED)

        pygame.display.flip()
