import math
import random
import sys
import pygame

from src.settings import (SCREEN_WIDTH, SCREEN_HEIGHT, HUD_HEIGHT, TILE_SIZE,
                           TITLE, FPS, VOID_COLOR, RED, YELLOW, WHITE,
                           LIGHT_GRAY, GRAY, GOLD_COLOR,
                           STATE_MENU, STATE_PLAYING, STATE_GAME_OVER, STATE_TOWN,
                           STATE_HERO_SELECT, STATE_CHAR_CREATE,
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
from src.ui.enchant_screen  import EnchantScreen
from src.ui.craft_screen    import CraftScreen
from src.ui.house_screen    import HouseScreen
from src.ui.settings_screen     import SettingsScreen
from src.ui.perk_screen         import PerkScreen
from src.ui.quest_giver_screen  import QuestGiverScreen
from src.ui.hero_select         import HeroSelectScreen
from src.ui.char_create         import CharCreateScreen
from src.settings_manager   import game_settings
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
from src.game_layers.renderer   import RendererLayer


class Game(SessionLayer, TownLayer, CombatLayer, SpellLayer, ProjectileLayer, ParticleLayer, RendererLayer):
    def __init__(self, net_client=None):
        self.screen = game_settings.apply_display()
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()

        self._font_xl   = pygame.font.SysFont("monospace", 64, bold=True)
        self._font_lg   = pygame.font.SysFont("monospace", 38, bold=True)
        self._font_md   = pygame.font.SysFont("monospace", 28)
        self._font_sm   = pygame.font.SysFont("monospace", 20)
        self._font_boss = pygame.font.SysFont("monospace", 16, bold=True)

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
        self.craft_open      = False
        self._craft_screen   = CraftScreen()
        self.house_open         = False
        self._house_screen      = HouseScreen()
        self.settings_open      = False
        self._settings_screen   = SettingsScreen()
        self.perk_open              = False
        self._perk_screen           = PerkScreen()
        self.quest_giver_open       = False
        self._quest_giver_screen    = QuestGiverScreen()
        self._hero_select           = HeroSelectScreen()
        self._char_create           = CharCreateScreen()
        self._active_wanderer       = None   # WandererNPC | TownMerchant (guild)
        self._active_merchant: Merchant | None = None

        # Migrate single legacy save → per-hero saves/ directory
        savesys.migrate_legacy_save()

        # ── Multiplayer ───────────────────────────────────────────────────────
        self.net_client = net_client          # NetworkClient | None
        self._pending_net_client = None       # NetworkClient connecting in background
        self.remote_players: dict = {}        # pid → RemotePlayer proxies
        self._net_floor: int       = 1        # server's current floor
        self._net_seed:  int | None = None    # server's current dungeon seed

        self._paused_state: str | None = None   # state before ESC → menu

        self._dmg_nums:   list = []
        self.chests:      list = []
        self.projectiles: list = []
        self.merchants:   list = []
        self.wanderers:   list = []
        self.decorations: list = []

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
        self._settings_btn_rect = None    # populated by _draw_menu
        self._menu_btn_rects:  dict = {}  # populated by _draw_menu, read by events

        self._player_hurt_t    = 0.0
        self._transition_timer = 0.0
        self._transition_level: int | None = None

        # Spell cooldowns
        self._ice_nova_cd      = 0.0
        self._chain_cd         = 0.0
        self._blink_cd         = 0.0
        self._battle_cry_timer = 0.0   # remaining active seconds

        self._inv_full_cd = 0.0   # cooldown between "inventory full" notifications

        # Lightning arc segments for Chain Lightning visual
        self._lightning_arcs: list = []

        # Torch radii reduced (~340 px ≈ 8.5 tiles) for tighter fog of war.
        # _torch_vis_r is the maximum radius used for the LoS distance cull.
        _torch_r = (325, 336, 346, 336, 326)
        self._torch_masks  = [(r, self._bake_light(r)) for r in _torch_r]
        self._torch_vis_r  = max(_torch_r)
        self._sconce_masks = [(r, self._bake_light(r))
                              for r in (108, 114, 120, 114)]
        self._stair_masks  = [(r, self._bake_light(r))
                              for r in (148, 156, 162, 156)]
        self._fog      = pygame.Surface(
            (SCREEN_WIDTH, SCREEN_HEIGHT - HUD_HEIGHT), pygame.SRCALPHA)
        self._vignette = self._bake_vignette()

        # If a net_client was provided, jump straight into the dungeon
        if net_client:
            self._start_net_game()

    # ─── Perk system ─────────────────────────────────────────────────────────────

    def _open_next_perk_pick(self):
        """Build perk choices and show the pick screen."""
        import random
        from src.perks import roll_perk_choices
        level   = self.player.level
        choices = roll_perk_choices(level, self.player.perks,
                                    rng=random.Random(level + len(self.player.perks)))
        if choices:
            self._perk_screen.open(choices, level)
            self.perk_open = True

    # ─── Display settings ────────────────────────────────────────────────────────

    def _apply_display_settings(self):
        """Called by SettingsScreen when fullscreen/window mode changes."""
        self.screen = game_settings.apply_display()
        # Rebuild surfaces that use a fixed pixel size
        self._fog      = pygame.Surface(
            (SCREEN_WIDTH, SCREEN_HEIGHT - HUD_HEIGHT), pygame.SRCALPHA)
        self._vignette = self._bake_vignette()

    def _connect_to_server(self, host: str, port: int, name: str):
        """Start a background network connection; returns the NetworkClient immediately."""
        from src.network.client import NetworkClient
        from src import save as savesys
        player_data = savesys.load_game()
        nc = NetworkClient(host, port, name, player_data=player_data)
        self._pending_net_client = nc
        return nc

    # ─── Quest giver ─────────────────────────────────────────────────────────────

    def _open_quest_giver(self, npc) -> None:
        """Open the quest giver screen for a wanderer or the Guild Master."""
        floor = self.dungeon_level
        quests = self.quest_log.add_npc_quests(floor, npc.title)
        if not quests:
            return
        self._quest_giver_screen.open(quests, npc.title)
        self._active_wanderer   = npc
        self.quest_giver_open   = True
        self.inv_open = self.shop_open = self.char_open = False
        self.quest_open = self.skill_open = False

    def _close_quest_giver(self) -> None:
        """Accept chosen quests and close the quest giver screen."""
        accepted_ids = self._quest_giver_screen.accepted_ids
        all_offered  = self._quest_giver_screen._quests
        for q in all_offered:
            if q.id in accepted_ids:
                self.quest_log.add_quest(q)
                self.hud.notify_quest(t("quest_giver.accepted_msg", name=q.name))
        self.quest_giver_open = False
        self._active_wanderer = None

    def _try_open_wanderer(self) -> None:
        """Check if player is near a wanderer NPC; open quest screen if so."""
        if self.player is None:
            return
        for w in getattr(self, 'wanderers', []):
            if w.near_player(self.player):
                self._open_quest_giver(w)
                return

    # ─── Net HUD ─────────────────────────────────────────────────────────────────

    def _draw_net_badge(self):
        """Small 'MULTIPLAYER' badge + player count in the top-right corner."""
        n_players = 1 + len(self.remote_players)   # self + remotes
        badge_txt = f"MULTIPLAYER  {n_players} players"
        col       = (80, 220, 120)
        s = self._font_sm.render(badge_txt, True, col)
        bx = SCREEN_WIDTH - s.get_width() - 18
        by = 8
        bg = pygame.Surface((s.get_width() + 14, s.get_height() + 6), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 160))
        self.screen.blit(bg, (bx - 7, by - 3))
        self.screen.blit(s, (bx, by))

    # ─── Main loop ───────────────────────────────────────────────────────────────

    def run(self):
        while True:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.05)
            self._handle_events()
            self._update(dt)
            self._draw()

    # ─── Events ──────────────────────────────────────────────────────────────────

    @staticmethod
    def _scale_event(event: pygame.event.Event) -> pygame.event.Event:
        """Re-map event.pos from physical-window to logical (1920×1080) coords."""
        if game_settings._windowed_size is None:
            return event
        if event.type not in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP,
                               pygame.MOUSEMOTION):
            return event
        pos = getattr(event, "pos", None)
        if pos is None:
            return event
        sp = game_settings.scale_pos(pos)
        return pygame.event.Event(event.type, {**event.__dict__, "pos": sp})

    def _handle_events(self):
        game_settings.apply_pending_resize()
        for _raw_event in pygame.event.get():
            event = self._scale_event(_raw_event)
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()

            if event.type == pygame.KEYDOWN:
                k = event.key

                # Perk screen blocks ALL other input until player picks
                if self.perk_open:
                    chosen_id = self._perk_screen.handle_event(event)
                    if chosen_id:
                        self.player.perks.append(chosen_id)
                        self.player._perk_picks_pending -= 1
                        if self.player._perk_picks_pending <= 0:
                            self.perk_open = False
                        else:
                            self._open_next_perk_pick()
                    continue   # block all other key handling while open

                # Char-create screen owns all keyboard input (name typing, etc.)
                if self.state == STATE_CHAR_CREATE and not self.settings_open:
                    self._char_create.handle_event(event)
                    continue

                if k == pygame.K_ESCAPE:
                    if self.settings_open and self._settings_screen.is_listening:
                        self._settings_screen.handle_event(event)
                    elif self.settings_open:       self.settings_open    = False
                    elif self.house_open:          self.house_open       = False
                    elif self.enchant_open:        self.enchant_open     = False
                    elif self.craft_open:          self.craft_open       = False
                    elif self.quest_giver_open:    self._close_quest_giver()
                    elif self.inv_open:            self.inv_open         = False
                    elif self.shop_open:           self.shop_open        = False
                    elif self.char_open:           self.char_open        = False
                    elif self.quest_open:          self.quest_open       = False
                    elif self.skill_open:          self.skill_open       = False
                    elif self.state == STATE_HERO_SELECT:
                        self._hero_select.handle_event(event)
                    elif self.state == STATE_PLAYING:
                        self._paused_state = STATE_PLAYING
                        self.state = STATE_MENU
                    elif self.state == STATE_TOWN:
                        self._paused_state = STATE_TOWN
                        self.state = STATE_MENU
                    elif self.state == STATE_MENU and self._paused_state:
                        self.state = self._paused_state
                        self._paused_state = None
                    else:
                        pygame.quit(); sys.exit()

                if k == pygame.K_RETURN:
                    if self.craft_open:
                        self._craft_screen.handle_event(event, self.player)
                    elif self.state == STATE_MENU:
                        self._open_char_create()
                    elif self.state == STATE_GAME_OVER:
                        self.state = STATE_MENU

                # "Load hero" from menu (only when saves exist)
                if k == pygame.K_c and self.state == STATE_MENU:
                    if savesys.has_save():
                        self._open_hero_select()

                # Language toggle — L key on menu
                if k == pygame.K_l and self.state == STATE_MENU:
                    locale.set_lang("de" if locale.lang() == "en" else "en")

                # Settings screen — S key on menu
                if k == pygame.K_s and self.state == STATE_MENU and not self.settings_open:
                    self.settings_open = True
                    self._settings_screen.open(apply_display_fn=self._apply_display_settings,
                                               connect_fn=self._connect_to_server)

                # Forward all events to settings screen when open
                if self.settings_open:
                    self._settings_screen.handle_event(event)
                    continue

                any_overlay = (self.inv_open or self.shop_open or self.char_open
                               or self.quest_open or self.skill_open
                               or self.quest_giver_open)

                # ── Town keys ──────────────────────────────────────────────
                if self.state == STATE_TOWN:
                    any_town_overlay = (self.shop_open or self.enchant_open
                                        or self.craft_open or self.house_open
                                        or self.quest_giver_open)
                    _ki = game_settings.key("interact")
                    if k == _ki and not any_town_overlay:
                        self._try_open_town_shop()
                    elif k == _ki and self.shop_open:
                        self.shop_open = False
                        self._active_merchant = None
                    elif k == _ki and self.enchant_open:
                        self.enchant_open = False
                        self._active_merchant = None
                    elif k == _ki and self.craft_open:
                        self.craft_open = False
                        self._active_merchant = None
                    elif k == _ki and self.quest_giver_open:
                        self._close_quest_giver()
                    if k == game_settings.key("descend") and not any_town_overlay:
                        if math.hypot(self.player.x - DUNGEON_ENTRANCE_POS[0],
                                      self.player.y - DUNGEON_ENTRANCE_POS[1]) < DUNGEON_INTERACT_R:
                            self._enter_dungeon_from_town()
                    if k in (game_settings.key("inventory"), pygame.K_TAB):
                        if not any_town_overlay:
                            self.inv_open = not self.inv_open
                    if k == game_settings.key("character") and not any_town_overlay and not self.inv_open:
                        self.char_open = not self.char_open
                    if k == game_settings.key("skills"):
                        self.skill_open = not self.skill_open
                        if self.skill_open:
                            self.inv_open = self.shop_open = self.char_open = False
                    if k == game_settings.key("quests") and not any_town_overlay:
                        self.quest_open = not self.quest_open

                # ── Dungeon keys ───────────────────────────────────────────
                if self.state == STATE_PLAYING and not any_overlay:
                    if k == game_settings.key("return_town"):
                        self._return_to_town()
                if self.state == STATE_PLAYING and not any_overlay and not self.net_client:
                    if k == game_settings.key("attack"):
                        mods = pygame.key.get_mods()
                        if (mods & pygame.KMOD_SHIFT and
                                self.player.skill_tree.has_whirlwind() and
                                self.player.mana >= WHIRLWIND_MANA_COST):
                            self._cast_whirlwind()
                        elif self.player.has_bow:
                            self._fire_arrow()
                        else:
                            self._player_attack()
                    if k == game_settings.key("spell_fireball"):    self._cast_fireball()
                    if k == game_settings.key("spell_ice_nova"):    self._cast_ice_nova()
                    if k == game_settings.key("spell_chain"):       self._cast_chain_lightning()
                    if k == game_settings.key("spell_blink"):       self._cast_blink()
                    if k == game_settings.key("spell_battle_cry"):  self._cast_battle_cry()
                    if k == game_settings.key("descend"):           self._try_descend()
                    if k == game_settings.key("potion"):
                        if self.player.use_potion():
                            self.inventory.notify(
                                t("game.used_potion", n=len(self.player.potions)))

                if self.state == STATE_PLAYING:
                    if k in (game_settings.key("inventory"), pygame.K_TAB):
                        if not self.shop_open and not self.char_open and not self.skill_open:
                            self.inv_open = not self.inv_open
                    if k == game_settings.key("character") and not self.shop_open and not self.inv_open:
                        self.char_open = not self.char_open
                    if k == game_settings.key("quests"):
                        self.quest_open = not self.quest_open
                        if self.quest_open:
                            self.inv_open = self.shop_open = self.char_open = self.skill_open = False
                    if k == game_settings.key("skills"):
                        self.skill_open = not self.skill_open
                        if self.skill_open:
                            self.inv_open = self.shop_open = self.char_open = self.quest_open = False
                    if k == game_settings.key("interact"):
                        if self.shop_open:
                            self.shop_open = False
                        elif self.quest_giver_open:
                            self._close_quest_giver()
                        elif not any_overlay:
                            self._try_open_shop()
                            if not self.shop_open:
                                self._try_open_wanderer()

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.perk_open:
                    chosen_id = self._perk_screen.handle_event(event)
                    if chosen_id:
                        self.player.perks.append(chosen_id)
                        self.player._perk_picks_pending -= 1
                        if self.player._perk_picks_pending <= 0:
                            self.perk_open = False
                        else:
                            self._open_next_perk_pick()
                    continue
                if self.settings_open:
                    self._settings_screen.handle_event(event)
                    continue
                if self.state == STATE_MENU:
                    for btn_id, brect in self._menu_btn_rects.items():
                        if brect.collidepoint(event.pos):
                            if btn_id == "resume":
                                self.state = self._paused_state
                                self._paused_state = None
                            elif btn_id == "new_game":
                                self._open_char_create()
                            elif btn_id == "continue":
                                if savesys.has_save():
                                    self._open_hero_select()
                            elif btn_id == "settings":
                                self.settings_open = True
                                self._settings_screen.open(
                                    apply_display_fn=self._apply_display_settings,
                                    connect_fn=self._connect_to_server)
                            break
                if self.state == STATE_HERO_SELECT:
                    self._hero_select.handle_event(event)
                if self.state == STATE_CHAR_CREATE:
                    self._char_create.handle_event(event)
                    for code, rect in self._lang_btn_rects.items():
                        if rect.collidepoint(event.pos):
                            locale.set_lang(code)
                            game_settings.language = code
                            game_settings.save()
                            break

            if event.type == pygame.MOUSEBUTTONDOWN and self.state in (STATE_PLAYING, STATE_TOWN):
                if self.quest_giver_open:
                    result = self._quest_giver_screen.handle_event(event)
                    if result == "close":
                        self._close_quest_giver()
                elif self.house_open:
                    self._house_screen.handle_event(event, self.player)
                elif self.enchant_open:
                    self._enchant_screen.handle_event(event, self.player)
                elif self.craft_open:
                    self._craft_screen.handle_event(event, self.player)
                elif self.inv_open and event.button == 1:
                    self.inventory.handle_click(*event.pos, self.player)
                elif self.shop_open and self._active_merchant:
                    self.shop.handle_click(*event.pos, event.button,
                                           self._active_merchant, self.player)
                elif self.char_open and event.button == 1:
                    self.charscreen.handle_click(*event.pos, self.player)
                elif self.skill_open and event.button == 1:
                    self.skillscreen.handle_click(*event.pos, self.player)

            if event.type == pygame.MOUSEMOTION and self.perk_open:
                self._perk_screen.handle_event(event)

            if event.type == pygame.MOUSEWHEEL and self.settings_open:
                self._settings_screen.handle_event(event)
            if event.type == pygame.MOUSEWHEEL and self.shop_open:
                self.shop.handle_scroll(event.y, *pygame.mouse.get_pos())
            if event.type == pygame.MOUSEWHEEL and self.inv_open:
                self.inventory.handle_scroll(event.y)
            if event.type == pygame.MOUSEWHEEL and self.house_open:
                self._house_screen.handle_event(event, self.player)
            if event.type == pygame.MOUSEWHEEL and self.enchant_open:
                self._enchant_screen.handle_event(event, self.player)
            if event.type == pygame.MOUSEWHEEL and self.craft_open:
                self._craft_screen.handle_event(event, self.player)

    # ─── Network mode ────────────────────────────────────────────────────────────

    def _start_net_game(self):
        """Called once at startup when net_client is provided."""
        welcome = self.net_client.latest_state
        if not welcome:
            return
        self._net_floor    = welcome["floor"]
        self._net_seed     = welcome.get("seed")
        self.dungeon_level = self._net_floor
        self.quest_log     = QuestLog()
        self._battle_cry_timer = 0.0
        self._ice_nova_cd = self._chain_cd = self._blink_cd = 0.0
        sx = float(welcome.get("start_x", 0))
        sy = float(welcome.get("start_y", 0))
        self.player = Player(sx, sy)
        self._load_level(self._net_floor, self.player, seed=self._net_seed)
        self.state = STATE_PLAYING

    def _net_send_input(self, in_town: bool = False):
        """Capture current keyboard state and send it to the server."""
        keys = pygame.key.get_pressed()
        if in_town:
            self.net_client.send_input({"in_town": True})
            return
        # Aim angle from mouse
        aim_angle = 0.0
        if self.player:
            mx, my = pygame.mouse.get_pos()
            wx = mx + self.camera.x
            wy = my + self.camera.y
            aim_angle = math.atan2(wy - self.player.y, wx - self.player.x)
        self.net_client.send_input({
            "up":              bool(keys[game_settings.key("move_up")]    or keys[pygame.K_UP]),
            "down":            bool(keys[game_settings.key("move_down")]  or keys[pygame.K_DOWN]),
            "left":            bool(keys[game_settings.key("move_left")]  or keys[pygame.K_LEFT]),
            "right":           bool(keys[game_settings.key("move_right")] or keys[pygame.K_RIGHT]),
            "attack":          bool(keys[game_settings.key("attack")]),
            "spell_fireball":  bool(keys[game_settings.key("spell_fireball")]),
            "spell_ice_nova":  bool(keys[game_settings.key("spell_ice_nova")]),
            "spell_chain":     bool(keys[game_settings.key("spell_chain")]),
            "spell_blink":     bool(keys[game_settings.key("spell_blink")]),
            "spell_battle_cry":bool(keys[game_settings.key("spell_battle_cry")]),
            "use_potion":      bool(keys[game_settings.key("potion")]),
            "descend":         bool(keys[game_settings.key("descend")]),
            "aim_angle":       aim_angle,
        })

    def _net_update(self, dt: float):
        """Update loop for network client mode."""
        # 1. Forward inputs
        self._net_send_input()

        # 2. Local player movement prediction — runs at render frame-rate
        #    for smooth feel; server state is a soft correction below.
        if self.player and self.dungeon:
            self.player.update(dt, self.dungeon, self.camera)

        # 3. Floor changes (must be applied before state snapshot)
        for fc in self.net_client.pop_floor_changes():
            self._net_floor    = fc["floor"]
            self._net_seed     = fc["seed"]
            self.dungeon_level = self._net_floor
            self._load_level(self._net_floor, self.player, seed=self._net_seed)
            self.enemies         = []
            self.items           = []
            self.remote_players  = {}

        # 4. Apply latest server snapshot (reconciliation + remote entities)
        state = self.net_client.latest_state
        if state and state.get("type") == "state":
            self._apply_net_state(state, dt)

        # 5. Interpolate remote entities
        for rp in self.remote_players.values():
            rp.interpolate(dt)
        for e in self.enemies:
            if hasattr(e, "interpolate"):
                e.interpolate(dt)

        # 6. Process server events (damage numbers, XP, etc.) + particles
        self._process_net_events(self.net_client.pop_events())
        self._update_particles(dt)

        # 7. Chat / notifications
        for line in self.net_client.pop_chat():
            self.hud.notify_quest(line)

        # 8. Animate damage numbers
        for dn in self._dmg_nums:
            dn["y"]     -= 32 * dt
            dn["x"]     += dn.get("vx", 0) * dt
            dn["timer"] -= dt
        self._dmg_nums = [d for d in self._dmg_nums if d["timer"] > 0]

        self.hud.update(dt)
        if self.player and self.dungeon:
            self.camera.update(self.player, self.dungeon)

        # 9. Detect disconnect
        if not self.net_client.connected and self.net_client.error:
            self.hud.notify_quest(f"Disconnected: {self.net_client.error}")
            self.state = STATE_MENU

    def _apply_net_state(self, state: dict, dt: float = 0.0):
        """Reconcile local state with authoritative server snapshot."""
        from src.network.client import GhostEnemy, GhostItem, RemotePlayer
        my_pid = self.net_client.pid

        # ── Players ───────────────────────────────────────────────────────────
        _SNAP_THRESHOLD = 96.0   # px: hard-snap if further than this
        seen_pids: set[int] = set()
        for pdata in state.get("players", []):
            pid = pdata["pid"]
            seen_pids.add(pid)
            if pid == my_pid and self.player:
                # Soft correction — blend toward server position
                sx_, sy_ = float(pdata["x"]), float(pdata["y"])
                dx = sx_ - self.player.x
                dy = sy_ - self.player.y
                dist = math.hypot(dx, dy)
                if dist > _SNAP_THRESHOLD:
                    self.player.x = sx_
                    self.player.y = sy_
                elif dist > 1.0:
                    self.player.x += dx * 0.25
                    self.player.y += dy * 0.25
                self.player._sync_rect()
                # Always trust server for HP / mana / gold / level
                self.player.hp    = float(pdata["hp"])
                self.player.mana  = float(pdata["mana"])
                self.player.level = pdata.get("level", self.player.level)
                self.player.gold  = pdata.get("gold",  self.player.gold)
            else:
                if pid not in self.remote_players:
                    self.remote_players[pid] = RemotePlayer(
                        pid, pdata.get("name", "???"))
                self.remote_players[pid].update_from(pdata)
        self.remote_players = {k: v for k, v in self.remote_players.items()
                               if k in seen_pids and k != my_pid}

        # ── Enemies ───────────────────────────────────────────────────────────
        existing = {e.net_id: e for e in self.enemies if hasattr(e, "net_id")}
        new_enemies = []
        for edata in state.get("enemies", []):
            eid = edata["eid"]
            if eid in existing:
                ge = existing[eid]
                ge.update_target(float(edata["x"]), float(edata["y"]),
                                 float(edata["hp"]))
                new_enemies.append(ge)
            else:
                ge = GhostEnemy(eid, edata["kind"],
                                edata["x"], edata["y"],
                                edata["hp"], edata["max_hp"],
                                is_boss=edata.get("boss", False),
                                is_elite=edata.get("elite", False))
                new_enemies.append(ge)
        self.enemies = new_enemies

        # ── Items ─────────────────────────────────────────────────────────────
        existing_items = {i.net_id: i for i in self.items if hasattr(i, "net_id")}
        new_items = []
        for idata in state.get("items", []):
            iid = idata["iid"]
            if iid in existing_items:
                new_items.append(existing_items[iid])
            else:
                new_items.append(GhostItem(
                    iid, idata["kind"], idata["x"], idata["y"]))
        self.items = new_items

    def _process_net_events(self, events: list[dict]):
        """Translate server events into client-side feedback."""
        import random as _rnd
        from src.settings import YELLOW, WHITE
        for evt in events:
            k = evt.get("k")
            if k == "hit":
                eid = evt.get("eid")
                enemy = next((e for e in self.enemies
                              if hasattr(e, "net_id") and e.net_id == eid), None)
                if enemy:
                    col_name = evt.get("col", "")
                    col = ((120, 210, 255) if col_name == "ice" else
                           (180, 220, 255) if col_name == "lightning" else
                           (252, 130,  20) if col_name == "fire" else
                           (YELLOW if evt.get("crit") else WHITE))
                    self._dmg_nums.append({
                        "x": enemy.x, "y": enemy.y - 22,
                        "vx": _rnd.uniform(-12, 12),
                        "text": str(evt.get("dmg", 0)),
                        "timer": 1.1, "max_timer": 1.1,
                        "color": col, "big": bool(evt.get("crit")),
                    })
            elif k == "kill":
                pid = evt.get("pid")
                if pid == self.net_client.pid:
                    if evt.get("leveled"):
                        self.hud.notify_level_up()
                    # Death particles at kill location
                    ex = evt.get("x", 0); ey = evt.get("y", 0)
                    self._spawn_death_particles_at(ex, ey)
            elif k == "spell":
                spell = evt.get("spell", "")
                if spell == "ice_nova":
                    self._spawn_ice_particles(
                        evt.get("x", 0), evt.get("y", 0))
                elif spell == "blink" and evt.get("pid") == self.net_client.pid:
                    self._spawn_blink_particles(
                        evt.get("ox", 0), evt.get("oy", 0))
                    self._spawn_blink_particles(
                        evt.get("x", 0), evt.get("y", 0))

    def _spawn_death_particles_at(self, ex: float, ey: float):
        """Spawn death particles at an arbitrary world position."""
        import random as _rnd, math as _math
        for _ in range(10):
            angle = _rnd.uniform(0, _math.pi * 2)
            spd   = _rnd.uniform(40, 140)
            life  = _rnd.uniform(0.2, 0.5)
            col   = _rnd.choice([(200, 50, 50), (240, 100, 20), (180, 30, 30)])
            self._particles.append({
                "x": ex, "y": ey,
                "vx": _math.cos(angle) * spd, "vy": _math.sin(angle) * spd,
                "life": life, "max_life": life,
                "color": col, "sz": _rnd.randint(2, 5),
            })

    # ─── Update ──────────────────────────────────────────────────────────────────

    def _update(self, dt: float):
        self._time   += dt
        self._shake_t = max(0.0, self._shake_t - dt)

        if self.state in (STATE_MENU, STATE_HERO_SELECT, STATE_CHAR_CREATE):
            self._update_sparks(dt)
            if self.settings_open:
                self._settings_screen.update(dt)

            if self.state == STATE_HERO_SELECT:
                r = self._hero_select.result()
                if r == "back":
                    self.state = STATE_MENU
                elif r == "create":
                    self._open_char_create()
                elif r and r.startswith("load:"):
                    hero_id = r[5:]
                    self._load_hero(hero_id)
                    self.state = STATE_TOWN

            elif self.state == STATE_CHAR_CREATE:
                r = self._char_create.result()
                if r == "back":
                    self.state = STATE_MENU
                elif isinstance(r, tuple) and r[0] == "confirm":
                    _, name, cls_id, gender, race = r
                    self._new_hero(name, cls_id, gender)
                    self.state = STATE_TOWN

            # Transition to multiplayer game once background connection succeeds
            if self._pending_net_client is not None:
                nc = self._pending_net_client
                if nc.connected:
                    self._pending_net_client = None
                    self.net_client = nc
                    self.settings_open = False
                    self._start_net_game()
                    self.state = STATE_PLAYING
                elif nc.error:
                    self._pending_net_client = None
            return

        # Open perk screen if a milestone level-up just happened
        if (not self.perk_open and self.player is not None
                and self.player._perk_picks_pending > 0):
            self._open_next_perk_pick()
        if self.state == STATE_TOWN:
            # In multiplayer: keep sending in_town signal so server skips us
            if self.net_client and self.net_client.connected:
                self._net_send_input(in_town=True)
            self._update_town(dt)
            return
        if self.state != STATE_PLAYING:
            return

        # Perk screen pauses all simulation while a choice is pending
        if self.perk_open:
            self._perk_screen.update(dt)
            return

        # Network client mode — skip all local simulation
        if self.net_client:
            self._net_update(dt)
            return

        # Spell cooldowns
        self._ice_nova_cd = max(0.0, self._ice_nova_cd - dt)
        self._chain_cd    = max(0.0, self._chain_cd    - dt)
        self._blink_cd    = max(0.0, self._blink_cd    - dt)
        self._inv_full_cd = max(0.0, self._inv_full_cd - dt)

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
        for wanderer in getattr(self, 'wanderers', []):
            wanderer.update(dt)

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
                    from src.items.item import GoldPile as _GP, QuestItem as _QI
                    if isinstance(item, _GP):
                        done = self.quest_log.notify("collect", "gold", item.amount)
                        self._apply_quest_rewards(done)
                    if item.collect(self.player):
                        self._spawn_pickup_sparkle(item.x, item.y)
                        # Quest: fetch item collected
                        if isinstance(item, _QI) and item.quest_trigger:
                            ev, tag = item.quest_trigger
                            done = self.quest_log.notify(ev, tag)
                            self._apply_quest_rewards(done)
                    else:
                        if self._inv_full_cd <= 0:
                            self.hud.notify(t("inv.full"), color=(255, 120, 40))
                            self.inventory.notify(t("inv.full"))
                            self._inv_full_cd = 3.0
        self.items = [i for i in self.items if not i.collected]

        for chest in self.chests:
            chest.update(dt)
            if not chest.opened and self.player.rect.colliderect(chest.rect):
                chest.open(self.player, self.items, self.dungeon_level, self.dungeon)
                self._shake_t   = 0.18
                self._shake_int = 5.0

        self._update_projectiles(dt)

        # Quest completion pop-up
        for msg in self.quest_log.pop_notifications():
            self.hud.notify_quest(msg)

        for dn in self._dmg_nums:
            dn['y']     -= 32 * dt
            dn['x']     += dn['vx'] * dt
            dn['timer'] -= dt
        self._dmg_nums = [d for d in self._dmg_nums if d['timer'] > 0]

        if not self.player.is_alive():
            hero_id = getattr(self.player, "hero_id", "")
            if hero_id:
                savesys.delete_hero(hero_id)
            else:
                savesys.delete_save()
            self.state = STATE_GAME_OVER

    # ─── Hero flow helpers ────────────────────────────────────────────────────────

    def _open_char_create(self):
        self._paused_state = None
        self._char_create.open()
        self.state = STATE_CHAR_CREATE

    def _open_hero_select(self):
        self._paused_state = None
        self._hero_select.open(savesys.list_heroes())
        self.state = STATE_HERO_SELECT

    # ─── Draw ────────────────────────────────────────────────────────────────────

    def _draw(self):
        self.screen.fill(VOID_COLOR)

        if self.state == STATE_MENU:
            self._draw_menu()
            if self.settings_open:
                self._settings_screen.draw(self.screen)
        elif self.state == STATE_HERO_SELECT:
            self._draw_menu()   # animated background
            self._hero_select.draw(self.screen, self._time)
        elif self.state == STATE_CHAR_CREATE:
            self._draw_menu()   # animated background
            self._char_create.draw(self.screen)
        elif self.state == STATE_TOWN:
            self._draw_town()
        elif self.state == STATE_PLAYING:
            self._draw_world()
            # Perk pick screen (drawn on top of the world, blocks all input)
            if self.perk_open:
                self._perk_screen.draw(self.screen)
            # Remote players drawn on top of the world in network mode
            if self.net_client:
                for rp in self.remote_players.values():
                    rp.draw(self.screen, self.camera)
                # Multiplayer HUD badge (top-left corner)
                self._draw_net_badge()
            if self.quest_giver_open:
                self._quest_giver_screen.draw(self.screen)
            elif self.inv_open:
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

        if game_settings._windowed_size:
            pygame.transform.scale(self.screen, game_settings._windowed_size,
                                   pygame.display.get_surface())
        pygame.display.flip()
