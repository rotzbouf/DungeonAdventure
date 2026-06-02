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
from src.ui.craft_screen   import CraftScreen
from src.ui.house_screen   import HouseScreen
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
    def __init__(self, net_client=None):
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
        self.craft_open      = False
        self._craft_screen   = CraftScreen()
        self.house_open      = False
        self._house_screen   = HouseScreen()
        self._active_merchant: Merchant | None = None

        # ── Multiplayer ───────────────────────────────────────────────────────
        self.net_client = net_client          # NetworkClient | None
        self.remote_players: dict = {}        # pid → RemotePlayer proxies

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

        # If a net_client was provided, jump straight into the dungeon
        if net_client:
            self._start_net_game()

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

    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()

            if event.type == pygame.KEYDOWN:
                k = event.key

                if k == pygame.K_ESCAPE:
                    if self.house_open:   self.house_open   = False
                    elif self.enchant_open: self.enchant_open = False
                    elif self.craft_open: self.craft_open  = False
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
                    if self.craft_open:
                        self._craft_screen.handle_event(event, self.player)
                    elif self.state == STATE_MENU:
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
                    any_town_overlay = (self.shop_open or self.enchant_open
                                        or self.craft_open or self.house_open)
                    if k == pygame.K_f and not any_town_overlay:
                        self._try_open_town_shop()
                    elif k == pygame.K_f and self.shop_open:
                        self.shop_open = False
                        self._active_merchant = None
                    elif k == pygame.K_f and self.enchant_open:
                        self.enchant_open = False
                        self._active_merchant = None
                    elif k == pygame.K_f and self.craft_open:
                        self.craft_open = False
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
                if self.house_open:
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
        self.dungeon_level = welcome["floor"]
        self.quest_log     = QuestLog()
        self._battle_cry_timer = 0.0
        self._ice_nova_cd = self._chain_cd = self._blink_cd = 0.0
        sx = float(welcome.get("start_x", 0))
        sy = float(welcome.get("start_y", 0))
        self.player = Player(sx, sy)
        self._load_level(self.dungeon_level, self.player,
                         seed=welcome.get("seed"))
        self.state = STATE_PLAYING

    def _net_send_input(self):
        """Capture current keyboard state and send it to the server."""
        keys = pygame.key.get_pressed()
        self.net_client.send_input({
            "up":     bool(keys[pygame.K_w] or keys[pygame.K_UP]),
            "down":   bool(keys[pygame.K_s] or keys[pygame.K_DOWN]),
            "left":   bool(keys[pygame.K_a] or keys[pygame.K_LEFT]),
            "right":  bool(keys[pygame.K_d] or keys[pygame.K_RIGHT]),
            "attack": bool(keys[pygame.K_SPACE]),
        })

    def _net_update(self, dt: float):
        """Update loop for network client mode — no local simulation."""
        # Forward inputs every frame
        self._net_send_input()

        # Apply the latest server snapshot
        state = self.net_client.latest_state
        if state and state.get("type") == "state":
            self._apply_net_state(state)

        # Show server chat/events on the HUD
        for line in self.net_client.pop_chat():
            self.hud.notify_quest(line)

        self.hud.update(dt)
        if self.player and self.dungeon:
            self.camera.update(self.player, self.dungeon)

        # Detect disconnect
        if not self.net_client.connected and self.net_client.error:
            self.hud.notify_quest(f"Disconnected: {self.net_client.error}")
            self.state = STATE_MENU

    def _apply_net_state(self, state: dict):
        """Overwrite local entity state with the authoritative server snapshot."""
        from src.network.client import GhostEnemy, GhostItem, RemotePlayer
        my_pid = self.net_client.pid

        # ── Players ───────────────────────────────────────────────────────────
        seen_pids: set[int] = set()
        for pdata in state.get("players", []):
            pid = pdata["pid"]
            seen_pids.add(pid)
            if pid == my_pid:
                self.player.x    = float(pdata["x"])
                self.player.y    = float(pdata["y"])
                self.player.hp   = float(pdata["hp"])
                self.player.mana = float(pdata["mana"])
                self.player._sync_rect()
                self.player.level = pdata.get("level", self.player.level)
                self.player.gold  = pdata.get("gold",  self.player.gold)
            else:
                if pid not in self.remote_players:
                    self.remote_players[pid] = RemotePlayer(pid,
                                                            pdata.get("name", "???"))
                self.remote_players[pid].update_from(pdata)
        self.remote_players = {k: v for k, v in self.remote_players.items()
                               if k in seen_pids}

        # ── Enemies ───────────────────────────────────────────────────────────
        existing = {e.net_id: e for e in self.enemies if hasattr(e, "net_id")}
        new_enemies = []
        for edata in state.get("enemies", []):
            eid = edata["eid"]
            if eid in existing:
                ge    = existing[eid]
                ge.x  = float(edata["x"])
                ge.y  = float(edata["y"])
                ge.hp = float(edata["hp"])
                ge._sync_rect()
                new_enemies.append(ge)
            else:
                new_enemies.append(GhostEnemy(
                    eid, edata["kind"],
                    edata["x"], edata["y"],
                    edata["hp"], edata["max_hp"],
                    is_boss=edata.get("boss", False),
                    is_elite=edata.get("elite", False),
                ))
        self.enemies = new_enemies

        # ── Items ─────────────────────────────────────────────────────────────
        existing_items = {i.net_id: i for i in self.items
                          if hasattr(i, "net_id")}
        new_items = []
        for idata in state.get("items", []):
            iid = idata["iid"]
            if iid in existing_items:
                new_items.append(existing_items[iid])
            else:
                new_items.append(GhostItem(
                    iid, idata["kind"], idata["x"], idata["y"]))
        self.items = new_items

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

        # Network client mode — skip all local simulation
        if self.net_client:
            self._net_update(dt)
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
            # Remote players drawn on top of the world in network mode
            if self.net_client:
                for rp in self.remote_players.values():
                    rp.draw(self.screen, self.camera)
                # Multiplayer HUD badge (top-left corner)
                self._draw_net_badge()
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
