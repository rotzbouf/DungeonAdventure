import math
import random
import pygame
from src.settings import TILE_SIZE, BOSS_FLOOR_INTERVAL
from src.world.tile import set_theme
from src.world.dungeon import Dungeon
from src.entities.player import Player
from src.entities.enemy import (get_enemy_types, Lich, DemonLord, StoneGolem,
                                  VampireLord, ElderDragon, IronColossus)
from src.entities.merchant import Merchant
from src.items.item import random_item, TreasureChest
from src.quests import QuestLog
from src import save as savesys
from src.locale import t, t_quest_name
from src.world.town import PLAYER_SPAWN as TOWN_PLAYER_SPAWN


class SessionLayer:
    """Level loading, new/continue game, descend, shop open, quest rewards."""

    def _load_level(self, level: int, player: Player | None = None):
        from src.world.tile import set_theme
        set_theme(level)

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
            if random.random() < 0.15:
                enemy.make_elite()
            self.enemies.append(enemy)

        # Boss floor: spawn a named boss every BOSS_FLOOR_INTERVAL floors
        if level > 0 and level % BOSS_FLOOR_INTERVAL == 0 and self.dungeon.rooms:
            _BOSS_ROTATION = [Lich, DemonLord, StoneGolem,
                              VampireLord, ElderDragon, IronColossus]
            bidx  = (level // BOSS_FLOOR_INTERVAL - 1) % len(_BOSS_ROTATION)
            BType = _BOSS_ROTATION[bidx]
            room  = self.dungeon.rooms[-1]
            bx    = room.center[0] * TILE_SIZE + TILE_SIZE // 2
            by    = room.center[1] * TILE_SIZE + TILE_SIZE // 2
            boss  = BType(float(bx), float(by))
            boss.scale_to_level(level)
            self.enemies.append(boss)
            self.hud.notify_quest(t("game.boss_incoming"))

        self.items = [random_item(tx, ty, level, floor=level)
                      for tx, ty in self.dungeon.item_spawns]

        self.merchants = [
            Merchant(tx * TILE_SIZE + TILE_SIZE // 2,
                     ty * TILE_SIZE + TILE_SIZE // 2,
                     level)
            for tx, ty in self.dungeon.merchant_spawns
        ]
        if self.merchants:
            self.hud.notify_quest(t("game.merchant_found"))

        self.chests = [TreasureChest(tx, ty)
                       for tx, ty in self.dungeon.chest_positions]

        self.projectiles    = []
        self._lightning_arcs = []
        self._spike_phase   = "idle"
        self._spike_timer   = 2.5
        self._trap_dmg_cd   = 0.0
        self._dmg_nums      = []
        self._particles     = []
        self.inv_open = self.shop_open = self.char_open = False
        self.quest_open = self.skill_open = self.enchant_open = False
        self._active_merchant = None

        # Floor quests
        self.quest_log.add_floor_quests(level)

    def _new_game(self):
        self.dungeon_level = 1
        self.quest_log  = QuestLog()
        self._battle_cry_timer = 0.0
        self._ice_nova_cd = self._chain_cd = self._blink_cd = 0.0
        # Create fresh player and enter town
        from src.entities.player import Player as _Player
        self.player = _Player(TOWN_PLAYER_SPAWN[0], TOWN_PLAYER_SPAWN[1])
        self._enter_town(rest=False)

    def _continue_game(self):
        """Load a saved game and drop the player into town."""
        data = savesys.load_game()
        if not data:
            self._new_game()
            return
        from src.skills import SkillTree
        from src.entities.player import Player as _Player
        # Migrate old saves that used ng_plus: convert to absolute floor number
        ng_plus            = data.get("ng_plus", 0)
        raw_level          = data.get("dungeon_level", 1)
        self.dungeon_level = raw_level + ng_plus * 5
        self.quest_log     = QuestLog.from_dict(data.get("quests", {}))

        # Build a bare player and restore saved state
        self.player = _Player(TOWN_PLAYER_SPAWN[0], TOWN_PLAYER_SPAWN[1])
        savesys.restore_player(self.player, data)
        self.player.skill_tree = SkillTree.from_dict(data.get("skills", {}))

        self._battle_cry_timer = 0.0
        self._ice_nova_cd = self._chain_cd = self._blink_cd = 0.0
        self._enter_town(rest=False)

    def _try_descend(self):
        sx, sy = self.dungeon.stairs_pos
        if math.hypot(self.player.x - sx, self.player.y - sy) < TILE_SIZE * 1.6:
            if self._transition_timer > 0:
                return
            next_level = self.dungeon_level + 1
            # Notify quest: reach floor
            done = self.quest_log.notify("reach", f"floor_{next_level}")
            self._apply_quest_rewards(done)

            self._transition_level = next_level
            self._transition_timer = 0.52
            # Auto-save on descent
            savesys.save_game(self.player, self.dungeon_level,
                              quest_log=self.quest_log,
                              skill_tree=self.player.skill_tree)

    def _try_open_shop(self):
        for merchant in self.merchants:
            if merchant.near_player(self.player):
                self._active_merchant = merchant
                self.shop_open = True
                return

    def _apply_quest_rewards(self, done_quests: list):
        for q in done_quests:
            if q.reward_xp:
                leveled = self.player.gain_xp(q.reward_xp)
                if leveled:
                    self.hud.notify_level_up()
            if q.reward_gold:
                self.player.gold += q.reward_gold
            self.hud.notify_quest(
                t("game.quest_reward", name=t_quest_name(q.id), xp=q.reward_xp))
