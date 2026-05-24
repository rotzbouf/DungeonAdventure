import math
import random
import sys
import pygame

from src.settings import (SCREEN_WIDTH, SCREEN_HEIGHT, HUD_HEIGHT, TILE_SIZE,
                           TITLE, FPS, VOID_COLOR, RED, ORANGE, YELLOW, WHITE,
                           LIGHT_GRAY, GRAY, GOLD_COLOR, STATE_MENU, STATE_PLAYING,
                           STATE_GAME_OVER, STATE_WIN, MAX_DUNGEON_LEVELS,
                           FIREBALL_MANA_COST, FIREBALL_SPEED, FIREBALL_MAX_RANGE,
                           FIREBALL_DAMAGE, FIREBALL_RADIUS, STATUS_BURN)
from src.utils.camera      import Camera
from src.world.dungeon     import Dungeon
from src.entities.player   import Player
from src.entities.enemy    import get_enemy_types
from src.entities.merchant import Merchant
from src.items.item        import GoldPile, random_item, TreasureChest
from src.ui.hud            import HUD
from src.ui.minimap        import Minimap
from src.ui.inventory      import InventoryScreen
from src.ui.shop           import ShopScreen
from src.ui.charscreen     import CharScreen


class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()

        self._font_xl  = pygame.font.SysFont("monospace", 52, bold=True)
        self._font_lg  = pygame.font.SysFont("monospace", 30, bold=True)
        self._font_md  = pygame.font.SysFont("monospace", 22)
        self._font_sm  = pygame.font.SysFont("monospace", 16)

        self.state          = STATE_MENU
        self.dungeon_level  = 1
        self.player: Player | None  = None
        self.dungeon: Dungeon | None = None
        self.enemies: list  = []
        self.items:   list  = []
        self.camera         = Camera()
        self.hud            = HUD()
        self.minimap        = Minimap()
        self.inventory      = InventoryScreen()
        self.shop           = ShopScreen()
        self.charscreen     = CharScreen()
        self.inv_open       = False
        self.shop_open      = False
        self.char_open      = False
        self._active_merchant: Merchant | None = None
        # Damage numbers — dict: {x, y, vx, text, timer, max_timer, color, big}
        self._dmg_nums: list = []
        self.chests:    list = []   # TreasureChest objects
        self.projectiles: list = []  # active player fireballs

        # Timing / screen-effects
        self._time      = 0.0
        self._shake_t   = 0.0
        self._shake_int = 0.0
        self._hitstop_t = 0.0       # freeze-frame duration on hit land
        self._sparks:   list = []   # menu ember particles
        self._particles: list = []  # combat death / hit particles

        # Player hurt ring flash
        self._player_hurt_t = 0.0

        # Floor-transition fade
        self._transition_timer = 0.0
        self._transition_level: int | None = None

        # Spike-trap cycle: idle → warning → active → idle …
        self._spike_phase  = "idle"    # "idle" | "warning" | "active"
        self._spike_timer  = 2.5       # seconds until next transition
        self._trap_dmg_cd  = 0.0      # per-tile damage cooldown

        # Torch / fog-of-war — rooms are fully lit; corridors stay dark.
        self._torch_masks = [(r, self._bake_light(r))
                             for r in (380, 392, 402, 410, 418)]
        self._fog = pygame.Surface(
            (SCREEN_WIDTH, SCREEN_HEIGHT - HUD_HEIGHT), pygame.SRCALPHA)
        self._vignette = self._bake_vignette()

    # ─── Level loading ───────────────────────────────────────────────────────────

    def _load_level(self, level: int, player: Player | None = None):
        from src.world.tile import set_theme
        set_theme(level)               # floor palette — also clears tile cache

        self.dungeon_level = level
        self.dungeon = Dungeon(level=level)

        sx, sy = self.dungeon.player_start
        if player is None:
            self.player = Player(sx, sy)
        else:
            self.player = player
            self.player.x, self.player.y = float(sx), float(sy)
            self.player._sync_rect()

        self.camera.update(self.player, self.dungeon)
        self.minimap.build(self.dungeon)

        etypes = get_enemy_types(level)
        self.enemies = []
        for tx, ty in self.dungeon.enemy_spawns:
            enemy = random.choice(etypes)(
                tx * TILE_SIZE + TILE_SIZE // 2,
                ty * TILE_SIZE + TILE_SIZE // 2,
            )
            enemy.scale_to_level(level)
            # 15 % chance to become an elite
            if random.random() < 0.15:
                enemy.make_elite()
            self.enemies.append(enemy)

        self.items = [random_item(tx, ty, level)
                      for tx, ty in self.dungeon.item_spawns]

        self.merchants = [
            Merchant(tx * TILE_SIZE + TILE_SIZE // 2,
                     ty * TILE_SIZE + TILE_SIZE // 2,
                     level)
            for tx, ty in self.dungeon.merchant_spawns
        ]

        # Treasure chests
        self.chests = [
            TreasureChest(tx, ty)
            for tx, ty in self.dungeon.chest_positions
        ]

        # Reset projectiles and spike phase
        self.projectiles    = []
        self._spike_phase   = "idle"
        self._spike_timer   = 2.5
        self._trap_dmg_cd   = 0.0

        self._dmg_nums        = []
        self._particles       = []
        self.inv_open         = False
        self.shop_open        = False
        self.char_open        = False
        self._active_merchant = None

    def _new_game(self):
        self._load_level(1)   # set_theme(1) inside _load_level clears cache
        self.state = STATE_PLAYING

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
                if event.key == pygame.K_ESCAPE:
                    # Close any open overlay first; only then go to menu
                    if self.inv_open:
                        self.inv_open  = False
                    elif self.shop_open:
                        self.shop_open = False
                    elif self.char_open:
                        self.char_open = False
                    elif self.state == STATE_PLAYING:
                        self.state = STATE_MENU
                    else:
                        pygame.quit(); sys.exit()

                if event.key == pygame.K_RETURN:
                    if self.state == STATE_MENU:
                        self._new_game()
                    elif self.state in (STATE_GAME_OVER, STATE_WIN):
                        self.state = STATE_MENU

                any_overlay = self.inv_open or self.shop_open or self.char_open

                if self.state == STATE_PLAYING and not any_overlay:
                    if event.key == pygame.K_SPACE:
                        self._player_attack()
                    if event.key == pygame.K_z:
                        self._cast_fireball()
                    if event.key == pygame.K_e:
                        self._try_descend()
                    if event.key == pygame.K_q:
                        if self.player.use_potion():
                            self.inventory.notify(
                                f"Used potion  (Remaining: {len(self.player.potions)})")
                    if event.key == pygame.K_f:
                        self._try_open_shop()

                if self.state == STATE_PLAYING:
                    if event.key in (pygame.K_i, pygame.K_TAB):
                        if not self.shop_open and not self.char_open:
                            self.inv_open = not self.inv_open
                    if event.key == pygame.K_c:
                        if not self.shop_open and not self.inv_open:
                            self.char_open = not self.char_open
                    if event.key == pygame.K_f and self.shop_open:
                        self.shop_open = False

            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.state == STATE_PLAYING:
                    if self.inv_open and event.button == 1:
                        self.inventory.handle_click(*event.pos, self.player)
                    elif self.shop_open and self._active_merchant:
                        self.shop.handle_click(
                            *event.pos, event.button,
                            self._active_merchant, self.player)
                    elif self.char_open and event.button == 1:
                        self.charscreen.handle_click(*event.pos, self.player)

    def _try_descend(self):
        sx, sy = self.dungeon.stairs_pos
        if math.hypot(self.player.x - sx, self.player.y - sy) < TILE_SIZE * 1.6:
            if self._transition_timer > 0:
                return   # already transitioning
            if self.dungeon_level >= MAX_DUNGEON_LEVELS:
                self.state = STATE_WIN
            else:
                self._transition_timer = 0.52
                self._transition_level = self.dungeon_level + 1

    def _try_open_shop(self):
        """Open the shop screen if the player is adjacent to a merchant."""
        for merchant in self.merchants:
            if merchant.near_player(self.player):
                self._active_merchant = merchant
                self.shop_open = True
                return

    def _player_attack(self):
        hit_list = self.player.try_attack(self.enemies)
        for enemy in hit_list:
            raw  = self.player.attack + random.randint(-2, 4)
            # ── Critical strike ──────────────────────────────────────────────
            is_crit = random.uniform(0, 100) < self.player.crit_chance
            if is_crit:
                raw = int(raw * 2)
            dmg = enemy.take_damage(raw)
            num_color = YELLOW if is_crit else WHITE
            label     = str(dmg)
            self._dmg_nums.append({
                'x': enemy.x, 'y': enemy.y - 22,
                'vx': random.uniform(-12, 12),
                'text': label,
                'timer': 1.1, 'max_timer': 1.1,
                'color': num_color, 'big': is_crit,
            })
            # ── Life steal ───────────────────────────────────────────────────
            if dmg > 0 and self.player.life_steal > 0:
                healed = max(1, int(dmg * self.player.life_steal / 100))
                self.player.heal(healed)
            # ── Knockback ────────────────────────────────────────────────────
            dist = math.hypot(enemy.x - self.player.x, enemy.y - self.player.y)
            if dist > 0:
                enemy.apply_knockback(
                    (enemy.x - self.player.x) / dist,
                    (enemy.y - self.player.y) / dist,
                    290.0,
                )
            if not enemy.alive:
                leveled = self.player.gain_xp(enemy.XP_REWARD)
                if leveled:
                    self.hud.notify_level_up()
                self._spawn_death_particles(enemy)
                self._drop_loot(enemy)
        # Hit-stop: brief world-freeze on any contact
        if hit_list:
            self._hitstop_t = max(self._hitstop_t, 0.07)

    def _cast_fireball(self):
        """Fire a fireball toward the mouse cursor (costs mana)."""
        if self.player.mana < FIREBALL_MANA_COST:
            return
        self.player.mana -= FIREBALL_MANA_COST

        mx, my = pygame.mouse.get_pos()
        # Convert screen-space mouse to world-space
        wx = mx + self.camera.x
        wy = my + self.camera.y
        dx = wx - self.player.x
        dy = wy - self.player.y
        dist = math.hypot(dx, dy)
        if dist < 1.0:
            dx, dy = math.cos(self.player.attack_angle), math.sin(self.player.attack_angle)
            dist   = 1.0
        nx, ny = dx / dist, dy / dist

        self.projectiles.append({
            'x':         self.player.x,
            'y':         self.player.y,
            'vx':        nx * FIREBALL_SPEED,
            'vy':        ny * FIREBALL_SPEED,
            'traveled':  0.0,
            'alive':     True,
            'exploding': False,
            'exp_timer': 0.0,
        })

    def _update_projectiles(self, dt: float):
        keep = []
        for fb in self.projectiles:
            if fb['exploding']:
                fb['exp_timer'] -= dt
                if fb['exp_timer'] <= 0:
                    fb['alive'] = False
                else:
                    keep.append(fb)
                continue

            step   = FIREBALL_SPEED * dt
            fb['x'] += fb['vx'] * dt
            fb['y'] += fb['vy'] * dt
            fb['traveled'] += step

            # Wall collision
            tx = int(fb['x'] // TILE_SIZE)
            ty = int(fb['y'] // TILE_SIZE)
            if not self.dungeon.is_walkable(tx, ty) or fb['traveled'] >= FIREBALL_MAX_RANGE:
                fb['exploding'] = True
                fb['exp_timer'] = 0.30
                self._fireball_explode(fb)
                keep.append(fb)
                continue

            # Enemy hit
            hit_any = False
            for enemy in self.enemies:
                if not enemy.alive:
                    continue
                d = math.hypot(enemy.x - fb['x'], enemy.y - fb['y'])
                if d < enemy.size // 2 + 8:
                    self._fireball_explode(fb)
                    fb['exploding'] = True
                    fb['exp_timer'] = 0.30
                    hit_any = True
                    break
            if hit_any:
                keep.append(fb)
                continue

            keep.append(fb)
        self.projectiles = [f for f in keep if f['alive']]

    def _fireball_explode(self, fb: dict):
        """AOE damage + burn status to all enemies in radius."""
        ex, ey = fb['x'], fb['y']
        # Spawn fire particles
        for _ in range(22):
            angle = random.uniform(0, math.pi * 2)
            spd   = random.uniform(80, 260)
            life  = random.uniform(0.25, 0.65)
            col   = random.choice([(252, 120, 20), (252, 60, 0), (252, 200, 60)])
            self._particles.append({
                'x': ex, 'y': ey,
                'vx': math.cos(angle) * spd, 'vy': math.sin(angle) * spd - 40,
                'life': life, 'max_life': life,
                'color': col, 'sz': random.randint(3, 7),
            })
        self._hitstop_t = max(self._hitstop_t, 0.05)

        for enemy in self.enemies:
            if not enemy.alive:
                continue
            d = math.hypot(enemy.x - ex, enemy.y - ey)
            if d > FIREBALL_RADIUS:
                continue
            raw = FIREBALL_DAMAGE + random.randint(-4, 8)
            dmg = enemy.take_damage(raw)
            enemy.apply_status(STATUS_BURN, 3.0, 5.0)
            self._dmg_nums.append({
                'x': enemy.x, 'y': enemy.y - 22,
                'vx': random.uniform(-8, 8),
                'text': str(dmg),
                'timer': 0.95, 'max_timer': 0.95,
                'color': (252, 130, 20), 'big': False,
            })
            if not enemy.alive:
                leveled = self.player.gain_xp(enemy.XP_REWARD)
                if leveled:
                    self.hud.notify_level_up()
                self._spawn_death_particles(enemy)
                self._drop_loot(enemy)

    def _drop_loot(self, enemy):
        from src.entities.enemy import Goblin, Skeleton, Orc, Demon
        px, py = enemy.x, enemy.y
        lvl    = self.dungeon_level

        # Quality bonus based on enemy tier (Demon = best loot)
        if isinstance(enemy, Demon):
            q_bonus = 40
        elif isinstance(enemy, Orc):
            q_bonus = 20
        elif isinstance(enemy, Skeleton):
            q_bonus = 10
        else:
            q_bonus = 0

        # Elite enemies always drop at least one item with bonus quality
        if getattr(enemy, 'is_elite', False):
            q_bonus += 30

        # Equipment drop
        if random.random() < enemy.LOOT_CHANCE:
            item = random_item(0, 0, lvl, quality_bonus=q_bonus)
            item._reposition(px + random.uniform(-14, 14),
                             py + random.uniform(-14, 14))
            self.items.append(item)

        # Gold — scaled by level and player's gold find bonus
        base_gold  = random.randint(2, 8) * lvl
        gf_mult    = 1.0 + self.player.gold_find_bonus / 100
        gold_amount = int(base_gold * gf_mult)
        gold = GoldPile(0, 0, gold_amount)
        gold._reposition(px + random.uniform(-10, 10),
                         py + random.uniform(-10, 10))
        self.items.append(gold)

        # Demons occasionally drop a second item (rare/unique only)
        if isinstance(enemy, Demon) and random.random() < 0.45:
            bonus_item = random_item(0, 0, lvl, quality_bonus=60)
            bonus_item._reposition(px + random.uniform(-18, 18),
                                   py + random.uniform(-18, 18))
            self.items.append(bonus_item)

    # ─── Update ──────────────────────────────────────────────────────────────────

    def _update(self, dt: float):
        self._time    += dt
        self._shake_t  = max(0.0, self._shake_t - dt)

        if self.state == STATE_MENU:
            self._update_sparks(dt)
            return
        if self.state != STATE_PLAYING:
            return

        # ── Floor transition ─────────────────────────────────────────────────
        if self._transition_timer > 0:
            prev_t = self._transition_timer
            self._transition_timer -= dt
            self._player_hurt_t = max(0.0, self._player_hurt_t - dt)  # VFX still ticks
            # Load level at midpoint (screen fully black)
            if prev_t > 0.26 >= self._transition_timer and self._transition_level:
                self._load_level(self._transition_level, self.player)
                self._transition_level = None
            return   # freeze world during transition

        # Particles always animate (they're pure VFX, not game-logic)
        self._update_particles(dt)

        # Update all overlay UIs regardless of which is open
        self.inventory.update(dt)
        self.shop.update(dt)
        self.charscreen.update(dt)

        if self.inv_open or self.shop_open or self.char_open:
            return

        # ── Hit-stop: freeze world motion for a beat after a landed hit ──────
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
            self._shake_t        = 0.22
            self._shake_int      = 6.0
            self._player_hurt_t  = 0.28
            hit_dmg = int(prev_hp - self.player.hp)
            if hit_dmg > 0:
                self._dmg_nums.append({
                    'x': self.player.x,
                    'y': self.player.y - 30,
                    'vx': random.uniform(-20, 20),
                    'text': f"-{hit_dmg}",
                    'timer': 0.80, 'max_timer': 0.80,
                    'color': (220, 60, 60), 'big': False,
                })

        for item in self.items:
            if not item.collected:
                item.update(dt)
                if self.player.rect.colliderect(item.rect):
                    item.collect(self.player)
                    self._spawn_pickup_sparkle(item.x, item.y)
        self.items = [i for i in self.items if not i.collected]

        # ── Treasure chests ──────────────────────────────────────────────────
        for chest in self.chests:
            chest.update(dt)
            if not chest.opened and self.player.rect.colliderect(chest.rect):
                chest.open(self.player, self.items, self.dungeon_level)
                self._shake_t   = 0.18
                self._shake_int = 5.0

        # ── Projectiles (fireballs) ──────────────────────────────────────────
        self._update_projectiles(dt)

        # ── Spike traps ──────────────────────────────────────────────────────
        self._update_traps(dt)

        for dn in self._dmg_nums:
            dn['y']     -= 32 * dt
            dn['x']     += dn['vx'] * dt
            dn['timer'] -= dt
        self._dmg_nums = [d for d in self._dmg_nums if d['timer'] > 0]

        if not self.player.is_alive():
            self.state = STATE_GAME_OVER

    # ─── Traps ───────────────────────────────────────────────────────────────────

    def _update_traps(self, dt: float):
        """Cycle spike traps through idle → warning → active, deal damage."""
        if not self.dungeon or not self.dungeon.trap_positions:
            return

        self._spike_timer  -= dt
        self._trap_dmg_cd   = max(0.0, self._trap_dmg_cd - dt)

        if self._spike_timer <= 0:
            if self._spike_phase == "idle":
                self._spike_phase = "warning"
                self._spike_timer = 0.50
            elif self._spike_phase == "warning":
                self._spike_phase = "active"
                self._spike_timer = 0.70
            else:   # active → idle
                self._spike_phase = "idle"
                self._spike_timer = 2.5

        # Damage check while active
        if self._spike_phase == "active" and self._trap_dmg_cd <= 0:
            ptx = int(self.player.x // TILE_SIZE)
            pty = int(self.player.y // TILE_SIZE)
            if (ptx, pty) in set(self.dungeon.trap_positions):
                dmg = self.player.take_damage(10)
                if dmg > 0:
                    self._dmg_nums.append({
                        'x': self.player.x, 'y': self.player.y - 28,
                        'vx': 0.0,
                        'text': str(dmg),
                        'timer': 0.9, 'max_timer': 0.9,
                        'color': (220, 30, 30), 'big': False,
                    })
                    self._shake_t   = 0.14
                    self._shake_int = 4.0
                    self._trap_dmg_cd = 0.8   # can't hit again this quickly

    # ─── Particles ───────────────────────────────────────────────────────────────

    def _spawn_death_particles(self, enemy):
        """Per-enemy-type death burst."""
        from src.entities.enemy import Goblin, Skeleton, Orc, Demon

        if isinstance(enemy, Skeleton):
            palette   = [(204, 196, 176), (160, 150, 130), (240, 235, 220), (80, 72, 60)]
            count, sz = 22, (2, 4)
            spd_range = (50, 230)
            life_range= (0.4, 1.1)
        elif isinstance(enemy, Demon):
            palette   = [(148, 0, 216), (100, 0, 180), (252, 188, 0), (220, 60, 255)]
            count, sz = 28, (3, 7)
            spd_range = (80, 280)
            life_range= (0.3, 0.9)
        elif isinstance(enemy, Orc):
            palette   = [(0, 52, 216), (0, 80, 255), (80, 140, 255), (180, 0, 0)]
            count, sz = 20, (3, 5)
            spd_range = (60, 210)
            life_range= (0.35, 0.8)
        else:  # Goblin + fallback
            palette   = [(220, 92, 16), (180, 50, 0), (252, 140, 40), (200, 70, 0)]
            count, sz = 18, (2, 5)
            spd_range = (60, 200)
            life_range= (0.3, 0.75)

        # Elite bonus sparks
        if getattr(enemy, 'is_elite', False):
            palette = [(220, 175, 0), (252, 220, 60)] + palette
            count   = int(count * 1.5)

        for _ in range(count):
            angle = random.uniform(0, math.pi * 2)
            spd   = random.uniform(*spd_range)
            life  = random.uniform(*life_range)
            self._particles.append({
                'x': enemy.x, 'y': enemy.y,
                'vx': math.cos(angle) * spd,
                'vy': math.sin(angle) * spd,
                'life': life, 'max_life': life,
                'color': random.choice(palette),
                'sz': random.randint(*sz),
            })

    def _spawn_pickup_sparkle(self, px: float, py: float):
        """Tiny gold sparkles when the player picks up an item."""
        for _ in range(8):
            angle = random.uniform(0, math.pi * 2)
            spd   = random.uniform(30, 90)
            life  = random.uniform(0.2, 0.5)
            self._particles.append({
                'x': px, 'y': py,
                'vx': math.cos(angle) * spd,
                'vy': math.sin(angle) * spd - 30,
                'life': life, 'max_life': life,
                'color': (255, 215, 0),
                'sz': random.randint(1, 3),
            })

    def _update_particles(self, dt: float):
        for p in self._particles:
            p['x']    += p['vx'] * dt
            p['y']    += p['vy'] * dt
            p['vy']   += 200 * dt           # gravity
            p['vx']   *= max(0.0, 1 - 3 * dt)   # air drag
            p['life'] -= dt
        self._particles = [p for p in self._particles if p['life'] > 0]

    def _draw_particles(self):
        play_h = SCREEN_HEIGHT - HUD_HEIGHT
        for p in self._particles:
            sx = int(p['x'] - self.camera.x)
            sy = int(p['y'] - self.camera.y)
            if not (-10 < sx < SCREEN_WIDTH + 10 and -10 < sy < play_h + 10):
                continue
            fade = p['life'] / p['max_life']
            col  = tuple(int(c * fade) for c in p['color'])
            sz   = max(1, int(p['sz'] * (0.5 + 0.5 * fade)))
            pygame.draw.circle(self.screen, col, (sx, sy), sz)

    # ─── Draw ────────────────────────────────────────────────────────────────────

    def _draw(self):
        self.screen.fill(VOID_COLOR)

        if self.state == STATE_MENU:
            self._draw_menu()
        elif self.state == STATE_PLAYING:
            self._draw_world()
            if self.inv_open:
                self.inventory.draw(self.screen, self.player)
            elif self.shop_open and self._active_merchant:
                self.shop.draw(self.screen, self._active_merchant, self.player)
            elif self.char_open:
                self.charscreen.draw(self.screen, self.player)
            # Floor-transition fade — black curtain peaks at midpoint
            if self._transition_timer > 0:
                raw_a = 1.0 - abs(self._transition_timer / 0.26 - 1.0)
                a_val = int(max(0, min(255, raw_a * 255)))
                if a_val > 0:
                    fade_s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
                    fade_s.fill((0, 0, 0))
                    fade_s.set_alpha(a_val)
                    self.screen.blit(fade_s, (0, 0))
        elif self.state == STATE_GAME_OVER:
            self._draw_world()
            self._draw_overlay("GAME OVER", "Press ENTER to restart", RED)
        elif self.state == STATE_WIN:
            self._draw_world()
            self._draw_overlay("VICTORY!", "Press ENTER for main menu", YELLOW)

        pygame.display.flip()

    def _draw_world(self):
        # Screen shake — temporarily offset camera
        shk_x = shk_y = 0
        if self._shake_t > 0:
            strength = self._shake_int * (self._shake_t / 0.18)
            shk_x = random.randint(-int(strength), int(strength))
            shk_y = random.randint(-int(strength), int(strength))
            self.camera.x += shk_x
            self.camera.y += shk_y

        self.dungeon.draw(self.screen, self.camera)

        # Stairs portal glow
        stx, sty = self.dungeon.stairs_pos
        sgx = stx - self.camera.x
        sgy = sty - self.camera.y
        play_h = SCREEN_HEIGHT - HUD_HEIGHT
        if -60 < sgx < SCREEN_WIDTH + 60 and -60 < sgy < play_h + 60:
            pulse = 0.60 + 0.40 * abs(math.sin(self._time * 2.2))
            gr    = int(52 * pulse)
            if gr > 0:
                # Outer soft halo
                gs = pygame.Surface((gr * 2 + 4, gr * 2 + 4), pygame.SRCALPHA)
                pygame.draw.circle(gs, (200, 175, 70, int(60 * pulse)),
                                   (gr + 2, gr + 2), gr)
                pygame.draw.circle(gs, (240, 220, 110, int(100 * pulse)),
                                   (gr + 2, gr + 2), gr // 2)
                self.screen.blit(gs, (int(sgx) - gr - 2, int(sgy) - gr - 2))
            # Rotating spoke lines (portal effect — baked into a single SRCALPHA surf)
            spoke_r  = int(30 + 6 * pulse)
            spoke_a  = int(130 * pulse)
            spoke_d  = spoke_r * 2 + 4
            ss       = pygame.Surface((spoke_d, spoke_d), pygame.SRCALPHA)
            n_spokes = 6
            for i in range(n_spokes):
                ang  = self._time * 1.1 + i * (math.pi * 2 / n_spokes)
                sx1  = spoke_d // 2 + int(math.cos(ang) * 7)
                sy1  = spoke_d // 2 + int(math.sin(ang) * 7)
                sx2  = spoke_d // 2 + int(math.cos(ang) * spoke_r)
                sy2  = spoke_d // 2 + int(math.sin(ang) * spoke_r)
                pygame.draw.line(ss, (220, 195, 80, spoke_a),
                                 (sx1, sy1), (sx2, sy2), 1)
            self.screen.blit(ss, (int(sgx) - spoke_d // 2,
                                   int(sgy) - spoke_d // 2))

        dist_stairs = math.hypot(self.player.x - stx, self.player.y - sty)
        if dist_stairs < TILE_SIZE * 3:
            dsx = stx - self.camera.x
            dsy = sty - self.camera.y
            if 0 < dsx < SCREEN_WIDTH and 0 < dsy < play_h:
                hint = self._font_sm.render("E  - descend", True, YELLOW)
                self.screen.blit(hint, (int(dsx) - hint.get_width() // 2,
                                        max(4, int(dsy) - 32)))

        self._draw_traps()

        for item in self.items:
            item.draw(self.screen, self.camera)
        for chest in self.chests:
            chest.draw(self.screen, self.camera)
        for enemy in self.enemies:
            enemy.draw(self.screen, self.camera)
        for merchant in self.merchants:
            merchant.draw(self.screen, self.camera)
            # Interaction hint when player is close enough
            if merchant.near_player(self.player):
                mx_s = int(merchant.x - self.camera.x)
                my_s = int(merchant.y - self.camera.y)
                if 0 < mx_s < SCREEN_WIDTH and 4 < my_s < play_h:
                    hint = self._font_sm.render("F  - Shop", True, (180, 110, 255))
                    self.screen.blit(hint, (mx_s - hint.get_width() // 2,
                                            max(4, my_s - 40)))
        self.player.draw(self.screen, self.camera)

        # Player hurt ring — brief expanding red ring on damage taken
        if self._player_hurt_t > 0:
            t  = 1.0 - self._player_hurt_t / 0.28
            r  = int(16 + 28 * t)
            a  = int(200 * (1.0 - t))
            if r > 1 and a > 0:
                hs = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
                pygame.draw.circle(hs, (220, 30, 30, a), (r + 2, r + 2), r, 3)
                px_ = int(self.player.x - self.camera.x)
                py_ = int(self.player.y - self.camera.y)
                self.screen.blit(hs, (px_ - r - 2, py_ - r - 2))

        self._draw_projectiles()
        self._draw_particles()   # drawn before fog so they fade at torch edges

        self._draw_fog()
        self.screen.blit(self._vignette, (0, 0))

        self._draw_item_labels()

        # Damage numbers — two font sizes; fade eases out
        for dn in self._dmg_nums:
            t      = dn['timer'] / dn['max_timer']     # 1→0
            alpha  = int(255 * min(1.0, t * 1.6))      # stays bright, quick fade at end
            if alpha <= 0:
                continue
            font   = self._font_lg if dn['big'] else self._font_md
            dx_    = int(dn['x'] - self.camera.x)
            dy_    = int(dn['y'] - self.camera.y)
            # Shadow
            sh_    = font.render(dn['text'], True, (0, 0, 0))
            sh_.set_alpha(int(alpha * 0.55))
            self.screen.blit(sh_, (dx_ - sh_.get_width() // 2 + 1, dy_ + 1))
            # Main text
            surf_  = font.render(dn['text'], True, dn['color'])
            surf_.set_alpha(alpha)
            self.screen.blit(surf_, (dx_ - surf_.get_width() // 2, dy_))
            # Gold glow behind crit numbers
            if dn['big'] and alpha > 80:
                gw = surf_.get_width() + 12
                gsurf = pygame.Surface((gw, surf_.get_height() + 8), pygame.SRCALPHA)
                gsurf.fill((220, 175, 0, int(alpha * 0.18)))
                self.screen.blit(gsurf, (dx_ - gw // 2, dy_ - 4))

        self.minimap.draw(self.screen, self.player, self.enemies,
                          self.dungeon.stairs_pos,
                          chests=self.chests,
                          merchants=self.merchants,
                          trap_positions=self.dungeon.trap_positions)
        self.hud.draw(self.screen, self.player, self.dungeon_level)

        # Restore camera after shake
        if shk_x or shk_y:
            self.camera.x -= shk_x
            self.camera.y -= shk_y

    def _draw_traps(self):
        """Draw spike-trap overlays on top of floor tiles."""
        if not self.dungeon or not self.dungeon.trap_positions:
            return
        play_h = SCREEN_HEIGHT - HUD_HEIGHT
        phase  = self._spike_phase

        for tx, ty in self.dungeon.trap_positions:
            sx = tx * TILE_SIZE - int(self.camera.x)
            sy = ty * TILE_SIZE - int(self.camera.y)
            if not (-TILE_SIZE < sx < SCREEN_WIDTH + TILE_SIZE and
                    -TILE_SIZE < sy < play_h + TILE_SIZE):
                continue
            cx = sx + TILE_SIZE // 2
            cy = sy + TILE_SIZE // 2

            if phase == "idle":
                # Subtle cross-hatch marks — easy to miss
                for ox, oy in [(-5, 0), (5, 0), (0, -5), (0, 5)]:
                    pygame.draw.circle(self.screen, (80, 20, 20),
                                       (cx + ox, cy + oy), 2)
            elif phase == "warning":
                # Bright red warning glow
                pulse = abs(math.sin(self._time * 14.0))
                a     = int(140 + 115 * pulse)
                ws    = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
                ws.fill((220, 0, 0, min(255, a // 3)))
                self.screen.blit(ws, (sx, sy))
                for ox, oy in [(-7, 0), (7, 0), (0, -7), (0, 7)]:
                    pygame.draw.circle(self.screen, (220, 0, 0),
                                       (cx + ox, cy + oy), 3)
            else:   # active — spikes extended
                # Red floor fill
                as_ = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
                as_.fill((180, 0, 0, 90))
                self.screen.blit(as_, (sx, sy))
                # Four spike tips
                _SC = (220, 50, 50)
                _SD = (120, 10, 10)
                for ox, oy, ex_, ey_ in [
                    (0, -4,  0, -13),
                    (0,  4,  0,  13),
                    (-4, 0, -13,  0),
                    (4,  0,  13,  0),
                ]:
                    pygame.draw.line(self.screen, _SD,
                                     (cx + ox, cy + oy),
                                     (cx + ex_, cy + ey_), 3)
                    pygame.draw.line(self.screen, _SC,
                                     (cx + ox, cy + oy),
                                     (cx + ex_, cy + ey_), 1)

    def _draw_projectiles(self):
        """Draw player fireballs and their explosion glow."""
        play_h = SCREEN_HEIGHT - HUD_HEIGHT
        for fb in self.projectiles:
            sx = int(fb['x'] - self.camera.x)
            sy = int(fb['y'] - self.camera.y)
            if not (-60 < sx < SCREEN_WIDTH + 60 and -60 < sy < play_h + 60):
                continue

            if fb['exploding']:
                # Expanding explosion ring
                t   = 1.0 - fb['exp_timer'] / 0.30
                r   = int(FIREBALL_RADIUS * t * 0.9)
                a   = int(220 * (1.0 - t))
                if r > 0:
                    gs = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
                    pygame.draw.circle(gs, (252, 150, 20, a),
                                       (r + 2, r + 2), r)
                    pygame.draw.circle(gs, (252, 240, 60, min(255, a + 80)),
                                       (r + 2, r + 2), max(1, r // 3))
                    self.screen.blit(gs, (sx - r - 2, sy - r - 2))
            else:
                # Fireball core
                pygame.draw.circle(self.screen, (252, 60, 0), (sx, sy), 7)
                pygame.draw.circle(self.screen, (252, 220, 60), (sx, sy), 4)
                # Trailing glow
                gs = pygame.Surface((28, 28), pygame.SRCALPHA)
                pygame.draw.circle(gs, (252, 120, 20, 90), (14, 14), 14)
                self.screen.blit(gs, (sx - 14, sy - 14))

    def _draw_fog(self):
        # Pure black outside the lit radius, no soft gradient
        self._fog.fill((0, 0, 0, 210))
        px = int(self.player.x - self.camera.x)
        py = int(self.player.y - self.camera.y)

        # Pick a flickering mask via smooth noise
        raw = (math.sin(self._time * 5.3) * 1.4 +
               math.sin(self._time * 3.1) * 0.6 + 2.0) / 4.0
        idx = int(raw * len(self._torch_masks)) % len(self._torch_masks)
        r, mask = self._torch_masks[idx]

        self._fog.blit(mask, (px - r, py - r),
                       special_flags=pygame.BLEND_RGBA_SUB)
        self.screen.blit(self._fog, (0, 0))

        # Subtle warm torch tint at the lit centre
        gw = int(r * 0.30 + math.sin(self._time * 7.1) * 4)
        warm = pygame.Surface((gw * 2, gw * 2), pygame.SRCALPHA)
        pygame.draw.circle(warm, (48, 20, 0, 22), (gw, gw), gw)
        self.screen.blit(warm, (px - gw, py - gw))

    @staticmethod
    def _bake_light(radius: int) -> pygame.Surface:
        """Pre-bake a radial gradient used to cut a lit hole in the fog."""
        d = radius * 2
        surf = pygame.Surface((d, d), pygame.SRCALPHA)
        for r in range(radius, -1, -3):
            a = int(200 * (1.0 - r / radius) ** 0.55)
            pygame.draw.circle(surf, (0, 0, 0, a), (radius, radius), r)
        return surf

    @staticmethod
    def _bake_vignette() -> pygame.Surface:
        """Pre-bake screen-edge darkening applied over the playfield."""
        w, h = SCREEN_WIDTH, SCREEN_HEIGHT - HUD_HEIGHT
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        depth = 200
        for i in range(depth, 0, -3):
            t = 1 - i / depth
            a = int(t ** 2.5 * 90)
            pygame.draw.rect(surf, (0, 0, 0, a),
                             (depth - i, depth - i,
                              w - 2 * (depth - i),
                              h - 2 * (depth - i)), 3)
        return surf

    def _update_sparks(self, dt: float):
        if random.random() < dt * 10:
            self._sparks.append({
                'x':   random.uniform(SCREEN_WIDTH * 0.25, SCREEN_WIDTH * 0.75),
                'y':   random.uniform(SCREEN_HEIGHT * 0.55, SCREEN_HEIGHT * 0.88),
                'vx':  random.uniform(-18, 18),
                'vy':  random.uniform(-55, -18),
                'life': random.uniform(1.8, 4.2),
                'sz':  random.uniform(1.4, 3.2),
                'max': 1.0,
            })
            self._sparks[-1]['max'] = self._sparks[-1]['life']
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
            return f"Health Potion  +{item.heal_amount} HP", (240, 100, 100)
        if isinstance(item, EquipItem):
            return item.display_name, item.quality_color
        return "Item", WHITE

    def _draw_item_labels(self):
        play_h = SCREEN_HEIGHT - HUD_HEIGHT
        for item in self.items:
            dist = math.hypot(item.x - self.player.x, item.y - self.player.y)
            if dist > TILE_SIZE * 2.5:
                continue
            # Fade in as player approaches: full alpha inside 1 tile
            fade  = 1.0 - max(0.0, dist - TILE_SIZE) / (TILE_SIZE * 1.5)
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
            bg = pygame.Surface((w + 10, h + 6), pygame.SRCALPHA)
            bg.fill((6, 3, 1, min(175, int(alpha * 0.82))))
            self.screen.blit(bg,  (sx - (w + 10) // 2, sy - 3))
            txt.set_alpha(alpha)
            self.screen.blit(txt, (sx - w // 2, sy))

    def _draw_menu(self):
        # ── Title screen ─────────────────────────────────────────────────────
        # Black background with stone-block border tiles
        self.screen.fill((0, 0, 0))
        cx  = SCREEN_WIDTH  // 2
        _STONE     = (68, 100, 176)
        _STONE_HI  = (112, 152, 220)
        _MORTAR    = (0,   8,  52)

        # Draw a border of stone blocks around the edge
        for ty in range(0, SCREEN_HEIGHT, TILE_SIZE):
            for tx in range(0, SCREEN_WIDTH, TILE_SIZE):
                on_border = (tx == 0 or ty == 0 or
                             tx >= SCREEN_WIDTH  - TILE_SIZE or
                             ty >= SCREEN_HEIGHT - TILE_SIZE)
                if on_border:
                    pygame.draw.rect(self.screen, _MORTAR,
                                     (tx, ty, TILE_SIZE, TILE_SIZE))
                    pygame.draw.rect(self.screen, _STONE,
                                     (tx + 1, ty + 1, TILE_SIZE - 2, TILE_SIZE - 2))
                    pygame.draw.line(self.screen, _STONE_HI,
                                     (tx + 1, ty + 1), (tx + TILE_SIZE - 2, ty + 1))

        # Flicker particles as "torchlight" on the title
        for s in self._sparks:
            t   = s['life'] / s['max']
            a   = int(min(255, t * 230))
            r   = max(1, int(s['sz'] * t))
            col = (min(255, int(195 + t * 60)), int(105 * t * t), 0)
            gsurf = pygame.Surface((r * 4 + 2, r * 4 + 2), pygame.SRCALPHA)
            pygame.draw.circle(gsurf, (*col, a // 3), (r * 2 + 1, r * 2 + 1), r * 2)
            pygame.draw.circle(gsurf, (*col, a),      (r * 2 + 1, r * 2 + 1), r)
            self.screen.blit(gsurf, (int(s['x']) - r * 2 - 1,
                                     int(s['y']) - r * 2 - 1))

        # ── Title ─────────────────────────────────────────────────────────────
        pulse = 0.88 + 0.12 * math.sin(self._time * 2.2)
        ycol  = tuple(int(c * pulse) for c in YELLOW)
        title = self._font_xl.render("DUNGEON ADVENTURE", True, ycol)
        # Hard black shadow behind title text
        t_sh  = self._font_xl.render("DUNGEON ADVENTURE", True, (0, 0, 0))
        self.screen.blit(t_sh,  t_sh.get_rect(center=(cx + 3, 180 + 3)))
        self.screen.blit(title, title.get_rect(center=(cx, 180)))

        sub = self._font_lg.render("A Classic Dungeon Crawler", True, WHITE)
        self.screen.blit(sub, sub.get_rect(center=(cx, 242)))

        # Blinking "Press ENTER" (flashes at ~1 Hz)
        if int(self._time * 2) % 2 == 0:
            enter = self._font_md.render("- PRESS  ENTER  TO  START -", True, YELLOW)
            self.screen.blit(enter, enter.get_rect(center=(cx, 310)))

        # ── Separator ─────────────────────────────────────────────────────────
        sep_y = 345
        pygame.draw.line(self.screen, _STONE_HI, (cx - 240, sep_y), (cx - 12, sep_y), 1)
        pygame.draw.line(self.screen, _STONE_HI, (cx + 12,  sep_y), (cx + 240, sep_y), 1)
        # Diamond centre
        pygame.draw.polygon(self.screen, YELLOW,
                            [(cx, sep_y - 6), (cx + 6, sep_y),
                             (cx, sep_y + 6), (cx - 6, sep_y)])

        # ── Controls ──────────────────────────────────────────────────────────
        controls = [
            ("WASD / Arrows", "Move"),
            ("SPACE",         "Attack (melee arc)"),
            ("Z",             "Fireball (25 mana → mouse)"),
            ("E",             "Descend Stairs"),
            ("F",             "Open Shop (near merchant)"),
            ("I / TAB",       "Inventory"),
            ("C",             "Character Screen"),
            ("Q",             "Use Potion"),
            ("ESC",           "Menu / Quit"),
        ]
        key_x = cx - 16
        act_x = cx + 16
        y0, lh = 368, 28
        for i, (key, action) in enumerate(controls):
            y   = y0 + i * lh
            ks  = self._font_sm.render(key,    True, YELLOW)
            acs = self._font_sm.render(action,  True, LIGHT_GRAY)
            self.screen.blit(ks,  ks.get_rect(right=key_x,  centery=y))
            # Diamond bullet
            pygame.draw.polygon(self.screen, _STONE_HI,
                                [(cx, y - 3), (cx + 4, y), (cx, y + 3), (cx - 4, y)])
            self.screen.blit(acs, acs.get_rect(left=act_x, centery=y))

    def _draw_overlay(self, title: str, sub: str, color):
        ov = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 172))
        self.screen.blit(ov, (0, 0))
        cy = (SCREEN_HEIGHT - HUD_HEIGHT) // 2
        cx = SCREEN_WIDTH // 2
        pulse = 0.82 + 0.18 * math.sin(self._time * 3.5)
        pc = tuple(int(c * pulse) for c in color)
        sh = self._font_xl.render(title, True, (15, 5, 5))
        self.screen.blit(sh, sh.get_rect(center=(cx + 4, cy - 40)))
        t = self._font_xl.render(title, True, pc)
        s = self._font_lg.render(sub,   True, WHITE)
        self.screen.blit(t, t.get_rect(center=(cx, cy - 44)))
        self.screen.blit(s, s.get_rect(center=(cx, cy + 24)))
