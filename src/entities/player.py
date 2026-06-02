import math
import random
import pygame
from src.entities.entity import Entity
from src.settings import (TILE_SIZE, PLAYER_COLOR, PLAYER_SPEED, PLAYER_SIZE,
                           PLAYER_MAX_HP, PLAYER_MAX_MANA, PLAYER_BASE_ATTACK,
                           PLAYER_BASE_DEFENSE, PLAYER_ATTACK_RANGE,
                           PLAYER_ATTACK_COOLDOWN, XP_BASE,
                           MAX_PLAYER_LEVEL, STAT_POINTS_PER_LEVEL,
                           BASE_STR, BASE_DEX, BASE_VIT, BASE_ENE)
from src.skills import SkillTree

_ATTACK_HALF_ARC = math.pi * 0.4   # ±72° — visual and hit detection


class Player(Entity):
    def __init__(self, x: float, y: float):
        super().__init__(x, y, PLAYER_SIZE, PLAYER_COLOR)

        self.max_hp   = PLAYER_MAX_HP
        self.hp       = float(PLAYER_MAX_HP)
        self.max_mana = PLAYER_MAX_MANA
        self.mana     = float(PLAYER_MAX_MANA)

        self.base_attack      = PLAYER_BASE_ATTACK
        self.base_defense     = PLAYER_BASE_DEFENSE
        self.attack_range     = PLAYER_ATTACK_RANGE
        self.attack_cooldown  = PLAYER_ATTACK_COOLDOWN
        self.speed            = PLAYER_SPEED

        self.level      = 1
        self.xp         = 0
        self.xp_to_next = XP_BASE
        self.gold       = 0
        self.materials: dict[str, int] = {}   # crafting materials inventory

        # ── D2-style core attributes ─────────────────────────────────────────
        self.str_pts    = BASE_STR
        self.dex_pts    = BASE_DEX
        self.vit_pts    = BASE_VIT
        self.ene_pts    = BASE_ENE
        self.stat_points = 0

        # ── Skill tree ───────────────────────────────────────────────────────
        self.skill_tree = SkillTree()

        # ── Equipment slots ──────────────────────────────────────────────────
        from src.items.item import (SLOT_WEAPON, SLOT_SHIELD, SLOT_HELM,
                                    SLOT_CHEST, SLOT_GLOVES, SLOT_BOOTS,
                                    SLOT_BELT, SLOT_RING, SLOT_AMULET)
        self.equipment: dict = {
            SLOT_WEAPON: None, SLOT_SHIELD: None, SLOT_HELM:   None,
            SLOT_CHEST:  None, SLOT_GLOVES: None, SLOT_BOOTS:  None,
            SLOT_BELT:   None, SLOT_RING:   None, "ring2":     None,
            SLOT_AMULET: None,
        }
        self.backpack: list = []
        self.stash:    list = []   # house chest — persistent storage
        self.potions:  list = []

        self._attack_timer     = 0.0
        self._invincible_timer = 0.0
        self._attack_anim      = 0.0
        self.attack_angle      = 0.0

    # ─── Equipment stat accumulator ──────────────────────────────────────────────

    def _equip_total(self, kind: str) -> float:
        total = 0.0
        for item in self.equipment.values():
            if item is not None:
                total += item.get_mod_total(kind)
        return total + self._synergy_bonus(kind)

    def _synergy_bonus(self, kind: str) -> float:
        """Extra stats from cross-item enchantment synergies."""
        # Collect all tags from every equipped item's enchantments
        all_tags: set[str] = set()
        has_any = False
        for item in self.equipment.values():
            if item is not None and getattr(item, 'enchantments', None):
                has_any = True
                from src.items.enchant import ENCHANTMENTS
                for eid in item.enchantments:
                    enc = ENCHANTMENTS.get(eid)
                    if enc:
                        all_tags.update(enc.tags)
        if not has_any:
            return 0.0
        from src.items.enchant import active_synergies
        total = 0.0
        for _name, bonus_mods in active_synergies(all_tags):
            total += sum(v for k, v in bonus_mods if k == kind)
        return total

    def equipped_enchant_tags(self) -> set[str]:
        """All enchantment tags across every equipped item (for display)."""
        tags: set[str] = set()
        from src.items.enchant import ENCHANTMENTS
        for item in self.equipment.values():
            if item is not None:
                for eid in getattr(item, 'enchantments', []):
                    enc = ENCHANTMENTS.get(eid)
                    if enc:
                        tags.update(enc.tags)
        return tags

    # ─── Derived stats ───────────────────────────────────────────────────────────

    @property
    def attack(self) -> int:
        from src.items.item import MOD_ATK, MOD_ATK_PCT
        base = self.base_attack + self.level * 2 + (self.str_pts - BASE_STR) * 2
        flat = self._equip_total(MOD_ATK)
        pct  = self._equip_total(MOD_ATK_PCT)
        raw  = int(base + flat + base * pct / 100)
        # Skill: Power Strike passive bonus
        return int(raw * (1.0 + self.skill_tree.melee_damage_bonus()))

    @property
    def defense(self) -> int:
        from src.items.item import MOD_DEF
        base = self.base_defense + self.level // 2 + (self.dex_pts - BASE_DEX)
        return int(base + self._equip_total(MOD_DEF))

    @property
    def max_hp_total(self) -> int:
        from src.items.item import MOD_MAX_HP
        vit_bonus  = (self.vit_pts - BASE_VIT) * 10
        equip_hp   = int(self._equip_total(MOD_MAX_HP))
        skill_mult = 1.0 + self.skill_tree.max_hp_bonus()
        return int((self.max_hp + vit_bonus + equip_hp) * skill_mult)

    @property
    def max_mana_total(self) -> int:
        from src.items.item import MOD_MAX_MANA
        ene_bonus   = (self.ene_pts - BASE_ENE) * 5
        equip_mana  = int(self._equip_total(MOD_MAX_MANA))
        skill_mult  = 1.0 + self.skill_tree.max_mana_bonus()
        return int((self.max_mana + ene_bonus + equip_mana) * skill_mult)

    @property
    def crit_chance(self) -> float:
        from src.items.item import MOD_CRIT
        dex_crit   = (self.dex_pts - BASE_DEX) * 0.5
        equip_crit = self._equip_total(MOD_CRIT)
        skill_crit = self.skill_tree.crit_bonus()
        return dex_crit + equip_crit + skill_crit

    @property
    def dodge_chance(self) -> float:
        return self.skill_tree.dodge_chance()

    @property
    def life_steal(self) -> float:
        from src.items.item import MOD_LIFE_STEAL
        return self._equip_total(MOD_LIFE_STEAL)

    @property
    def hp_regen_rate(self) -> float:
        from src.items.item import MOD_HP_REGEN
        return self._equip_total(MOD_HP_REGEN)

    @property
    def thorns_damage(self) -> float:
        from src.items.item import MOD_THORNS
        return self._equip_total(MOD_THORNS)

    @property
    def move_speed(self) -> float:
        from src.items.item import MOD_SPEED
        bonus    = self._equip_total(MOD_SPEED)
        base_spd = PLAYER_SPEED * (1.0 + bonus / 100)
        if self.has_status('slow') or self.has_status('freeze'):
            base_spd *= 0.55
        return base_spd

    @property
    def gold_find_bonus(self) -> float:
        from src.items.item import MOD_GOLD_FIND
        return self._equip_total(MOD_GOLD_FIND)

    @property
    def effective_cooldown(self) -> float:
        from src.items.item import MOD_ATK_SPD
        bonus = self._equip_total(MOD_ATK_SPD)
        return max(0.12, PLAYER_ATTACK_COOLDOWN * (1.0 - bonus / 100))

    @property
    def has_bow(self) -> bool:
        from src.items.item import BOW_BASES, SLOT_WEAPON
        w = self.equipment.get(SLOT_WEAPON)
        return w is not None and w.base_name in BOW_BASES

    @property
    def bow_attack(self) -> int:
        from src.items.item import MOD_ATK, SLOT_WEAPON
        from src.settings import ARROW_BASE_DMG
        dex_bonus = (self.dex_pts - BASE_DEX) * 3
        bow = self.equipment.get(SLOT_WEAPON)
        bow_atk = bow.get_mod_total(MOD_ATK) if bow else 0.0
        skill_mult = 1.0 + self.skill_tree.melee_damage_bonus()
        return int((ARROW_BASE_DMG + dex_bonus + bow_atk + self.level) * skill_mult)

    # ─── Inventory ───────────────────────────────────────────────────────────────

    def add_item(self, item):
        from src.items.item import EquipItem, HealthPotion
        if isinstance(item, HealthPotion):
            self.potions.append(item)
        elif isinstance(item, EquipItem):
            slot = item.slot
            key  = slot
            if slot == "ring":
                if self.equipment.get("ring") is None:
                    key = "ring"
                elif self.equipment.get("ring2") is None:
                    key = "ring2"
                else:
                    key = None
            if key is not None and self.equipment.get(key) is None:
                self.equipment[key] = item
            else:
                self.backpack.append(item)

    def equip(self, item, slot_key: str | None = None) -> object | None:
        from src.items.item import EquipItem
        if not isinstance(item, EquipItem):
            return None
        key = slot_key or item.slot
        if key not in self.equipment:
            key = item.slot
        old = self.equipment.get(key)
        self.equipment[key] = item
        if item in self.backpack:
            self.backpack.remove(item)
        return old

    def unequip(self, slot_key: str) -> None:
        item = self.equipment.get(slot_key)
        if item is not None:
            self.equipment[slot_key] = None
            self.backpack.append(item)

    def use_potion(self) -> bool:
        if self.potions and self.hp < self.max_hp_total:
            self.heal(self.potions.pop().heal_amount)
            return True
        return False

    # ─── Combat ──────────────────────────────────────────────────────────────────

    def gain_xp(self, amount: int) -> bool:
        if self.level >= MAX_PLAYER_LEVEL:
            return False
        self.xp += amount
        leveled = False
        while self.xp >= self.xp_to_next and self.level < MAX_PLAYER_LEVEL:
            self.xp -= self.xp_to_next
            self.level += 1
            self.xp_to_next = int(XP_BASE * (self.level ** 1.4))
            self.max_hp   += 5
            self.hp        = min(self.hp + 5, self.max_hp_total)
            self.max_mana += 3
            self.mana      = min(self.mana + 3, self.max_mana_total)
            self.stat_points            += STAT_POINTS_PER_LEVEL
            self.skill_tree.skill_points += 1
            leveled = True
        if self.level >= MAX_PLAYER_LEVEL:
            self.xp = self.xp_to_next
        return leveled

    def spend_stat(self, stat: str) -> bool:
        if self.stat_points <= 0:
            return False
        if stat == 'str':
            self.str_pts += 1
        elif stat == 'dex':
            self.dex_pts += 1
        elif stat == 'vit':
            old_max = self.max_hp_total
            self.vit_pts += 1
            self.hp = min(self.hp + (self.max_hp_total - old_max), self.max_hp_total)
        elif stat == 'ene':
            old_max = self.max_mana_total
            self.ene_pts += 1
            self.mana = min(self.mana + (self.max_mana_total - old_max), self.max_mana_total)
        else:
            return False
        self.stat_points -= 1
        return True

    def take_damage(self, amount: int) -> int:
        if self._invincible_timer > 0:
            return 0
        # Dodge check (Evasion skill)
        if self.dodge_chance > 0 and random.uniform(0, 100) < self.dodge_chance:
            self._invincible_timer = 0.15   # brief iframes after dodge
            return 0
        actual = max(1, amount - self.defense)
        self.hp -= actual
        self._invincible_timer = 0.4
        return actual

    def heal(self, amount: int):
        self.hp = min(self.max_hp_total, self.hp + amount)

    def is_alive(self) -> bool:
        return self.hp > 0

    @property
    def attack_ready(self) -> float:
        cd = self.effective_cooldown
        if cd == 0:
            return 1.0
        return 1.0 - min(1.0, self._attack_timer / cd)

    def try_attack(self, enemies: list, whirlwind: bool = False,
                   net_keys=None) -> list:
        if self._attack_timer > 0:
            return []
        self._attack_timer = self.effective_cooldown
        self._attack_anim  = 0.22

        keys = net_keys if net_keys is not None else pygame.key.get_pressed()
        dx = dy = 0.0
        if keys[pygame.K_w] or keys[pygame.K_UP]:    dy -= 1.0
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:  dy += 1.0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:  dx -= 1.0
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: dx += 1.0
        if dx != 0 or dy != 0:
            self.attack_angle = math.atan2(dy, dx)

        hit = []
        for enemy in enemies:
            dist = math.hypot(enemy.x - self.x, enemy.y - self.y)
            if dist > self.attack_range:
                continue
            if whirlwind:
                hit.append(enemy)   # 360° — no arc check
                continue
            angle_to = math.atan2(enemy.y - self.y, enemy.x - self.x)
            diff = abs(self.attack_angle - angle_to)
            if diff > math.pi:
                diff = math.pi * 2 - diff
            if diff < _ATTACK_HALF_ARC:
                hit.append(enemy)
        return hit

    # ─── Update ──────────────────────────────────────────────────────────────────

    def update(self, dt: float, dungeon, camera, net_keys=None):
        self._attack_timer     = max(0.0, self._attack_timer - dt)
        self._invincible_timer = max(0.0, self._invincible_timer - dt)
        self._attack_anim      = max(0.0, self._attack_anim - dt)

        # Mana regen
        self.mana = min(self.max_mana_total, self.mana + 3.0 * dt)
        # HP regen from gear
        if self.hp_regen_rate > 0 and self.hp < self.max_hp_total:
            self.hp = min(self.max_hp_total, self.hp + self.hp_regen_rate * dt)

        # Status DoT
        dot = self.tick_statuses(dt)
        if dot > 0 and self._invincible_timer <= 0:
            self.hp = max(0.0, self.hp - dot)

        keys = net_keys if net_keys is not None else pygame.key.get_pressed()
        dx = dy = 0.0
        if keys[pygame.K_w] or keys[pygame.K_UP]:    dy -= 1.0
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:  dy += 1.0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:  dx -= 1.0
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: dx += 1.0
        if dx != 0 and dy != 0:
            dx *= 0.7071; dy *= 0.7071
        if dx != 0 or dy != 0:
            self.attack_angle = math.atan2(dy, dx)

        half = self.size // 2
        mg   = 2
        spd  = self.move_speed
        new_x = self.x + dx * spd * dt
        if self._rect_ok(pygame.Rect(new_x - half + mg, self.y - half + mg,
                                     self.size - mg * 2, self.size - mg * 2), dungeon):
            self.x = new_x
        new_y = self.y + dy * spd * dt
        if self._rect_ok(pygame.Rect(self.x - half + mg, new_y - half + mg,
                                     self.size - mg * 2, self.size - mg * 2), dungeon):
            self.y = new_y

        # Knockback physics
        if self.kbx or self.kby:
            new_x = self.x + self.kbx * dt
            tr = pygame.Rect(new_x - half + mg, self.y - half + mg,
                             self.size - mg * 2, self.size - mg * 2)
            if self._rect_ok(tr, dungeon):
                self.x = new_x
            else:
                self.kbx = 0.0
            new_y = self.y + self.kby * dt
            tr = pygame.Rect(self.x - half + mg, new_y - half + mg,
                             self.size - mg * 2, self.size - mg * 2)
            if self._rect_ok(tr, dungeon):
                self.y = new_y
            else:
                self.kby = 0.0
            friction = max(0.0, 1.0 - 12.0 * dt)
            self.kbx *= friction; self.kby *= friction
            if abs(self.kbx) < 2.0: self.kbx = 0.0
            if abs(self.kby) < 2.0: self.kby = 0.0

        self._sync_rect()

    def _rect_ok(self, rect: pygame.Rect, dungeon) -> bool:
        for cx, cy in [(rect.left, rect.top), (rect.right, rect.top),
                       (rect.left, rect.bottom), (rect.right, rect.bottom)]:
            if not dungeon.is_walkable(int(cx // TILE_SIZE), int(cy // TILE_SIZE)):
                return False
        return True

    # ─── Equipment visual helpers ────────────────────────────────────────────────

    def _equip_visuals(self) -> dict:
        """Return draw parameters derived from equipped items."""
        from src.items.item import (SLOT_WEAPON, SLOT_CHEST, SLOT_HELM,
                                    SLOT_SHIELD,
                                    QUALITY_MAGIC, QUALITY_RARE, QUALITY_UNIQUE)
        t = pygame.time.get_ticks() * 0.001

        # ── Chest / tunic colour ──────────────────────────────────────────────
        chest = self.equipment.get(SLOT_CHEST)
        if chest is None:
            tunic = (0, 160, 0)
        elif "Plate" in chest.base_name:
            tunic = (50, 90, 170)      # blue steel plate
        elif "Ring Mail" in chest.base_name:
            tunic = (75, 80, 80)       # grey chainmail
        else:
            tunic = (0, 140, 20)       # leather / starter
        # Quality shimmer
        if chest is not None:
            if chest.quality == QUALITY_UNIQUE:
                r = int(180 + 40 * math.sin(t * 1.8))
                g = int(100 + 30 * math.sin(t * 1.8 + 1.5))
                b = int(20)
                tunic = (min(255, r), min(255, g), b)
            elif chest.quality == QUALITY_RARE:
                tunic = tuple(min(255, int(c * 0.65 + 65)) for c in tunic)  # type: ignore
            elif chest.quality == QUALITY_MAGIC:
                tunic = (tunic[0] // 2, tunic[1] // 2, min(255, tunic[2] + 90))  # type: ignore

        # ── Weapon ───────────────────────────────────────────────────────────
        wp = self.equipment.get(SLOT_WEAPON)
        sword_len = 15
        sword_col = (216, 216, 252)
        guard_col = (176, 140, 36)
        sword_w   = 2      # line width

        if wp is not None:
            bn = wp.base_name
            if "Dagger"     in bn: sword_len, sword_w = 9,  1
            elif "Short"    in bn: sword_len, sword_w = 12, 2
            elif "Broad"    in bn: sword_len, sword_w = 16, 2
            elif "Battle"   in bn: sword_len, sword_w, sword_col = 11, 3, (180, 60, 20)
            elif "War Hammer" in bn: sword_len, sword_w, sword_col = 9, 4, (200, 175, 55)
            elif "Great"    in bn: sword_len, sword_w, sword_col = 21, 2, (160, 210, 255)
            # Quality colour
            if wp.quality == QUALITY_UNIQUE:
                r = int(220 + 35 * math.sin(t * 2.2))
                sword_col = (min(255, r), min(255, int(170 + 30 * math.sin(t))), 20)
            elif wp.quality == QUALITY_RARE:
                sword_col = (220, 185, 20)
            elif wp.quality == QUALITY_MAGIC:
                sword_col = (60, 100, 255)

        # ── Shield ───────────────────────────────────────────────────────────
        sh = self.equipment.get(SLOT_SHIELD)
        show_shield = sh is not None
        if sh is not None:
            if "Tower" in sh.base_name:
                shield_col, shield_hi, shield_d = (30, 40, 70), (60, 80, 140), (12, 18, 50)
            elif "Kite"  in sh.base_name:
                shield_col, shield_hi, shield_d = (0, 44, 180), (55, 110, 220), (0, 20, 100)
            else:  # Buckler
                shield_col, shield_hi, shield_d = (0, 52, 216), (80, 140, 252), (0, 24, 140)
            if sh.quality == QUALITY_UNIQUE:
                shield_col = (175, 135, 20)
                shield_hi  = (220, 195, 55)
                shield_d   = (100, 75, 10)
        else:
            shield_col, shield_hi, shield_d = (0, 52, 216), (80, 140, 252), (0, 24, 140)

        # ── Helm ─────────────────────────────────────────────────────────────
        helm = self.equipment.get(SLOT_HELM)
        helm_type = "none"
        if helm is not None:
            if "Great" in helm.base_name:
                helm_type = "great"
            elif helm.base_name == "Helm":
                helm_type = "helm"
            else:
                helm_type = "cap"

        return {
            "tunic": tunic, "tunic_d": tuple(max(0, c - 70) for c in tunic),  # type: ignore
            "sword_len": sword_len, "sword_col": sword_col,
            "guard_col": guard_col, "sword_w": sword_w,
            "show_shield": show_shield,
            "shield_col": shield_col, "shield_hi": shield_hi, "shield_d": shield_d,
            "helm_type": helm_type,
        }

    # ─── Draw ────────────────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface, camera):
        if self._invincible_timer > 0 and int(self._invincible_timer * 14) % 2:
            return

        dr = camera.apply(self.rect)
        cx, cy = dr.centerx, dr.centery
        fa     = self.attack_angle
        perp   = fa + math.pi / 2

        vis = self._equip_visuals()

        _BLK    = (0, 0, 0)
        _TUNIC  = vis["tunic"]
        _TUNIC_D= vis["tunic_d"]
        # Status tint blended in
        _tint = self.status_tint()
        if _tint:
            _TUNIC   = tuple(min(255, (c + t) // 2) for c, t in zip(_TUNIC, _tint))   # type: ignore
            _TUNIC_D = tuple(min(255, (c + t) // 2) for c, t in zip(_TUNIC_D, _tint)) # type: ignore
        _SKIN   = (252, 188, 100)
        _SKIN_D = (180, 128,  56)
        _SWORD  = vis["sword_col"]
        _GUARD  = vis["guard_col"]
        _HAT    = _TUNIC

        half = self.size // 2

        # ── Body ─────────────────────────────────────────────────────────────
        body = pygame.Rect(cx - half + 2, cy - half + 2, self.size - 4, self.size - 4)
        pygame.draw.rect(surface, _BLK, body.inflate(2, 2))
        pygame.draw.rect(surface, _TUNIC, body)
        pygame.draw.rect(surface, _TUNIC_D,
                         pygame.Rect(body.left, body.centery,
                                     body.width, body.height // 2))

        # ── Shield (conditional on equipment) ────────────────────────────────
        if vis["show_shield"]:
            s_cx = int(cx - math.cos(fa) * 2 + math.cos(perp) * (half + 5))
            s_cy = int(cy - math.sin(fa) * 2 + math.sin(perp) * (half + 5))
            fw, fh = 5, 7
            sh_pts = [
                (int(s_cx + math.cos(fa)*fh - math.cos(perp)*fw),
                 int(s_cy + math.sin(fa)*fh - math.sin(perp)*fw)),
                (int(s_cx + math.cos(fa)*fh + math.cos(perp)*fw),
                 int(s_cy + math.sin(fa)*fh + math.sin(perp)*fw)),
                (int(s_cx - math.cos(fa)*fh + math.cos(perp)*fw),
                 int(s_cy - math.sin(fa)*fh + math.sin(perp)*fw)),
                (int(s_cx - math.cos(fa)*fh - math.cos(perp)*fw),
                 int(s_cy - math.sin(fa)*fh - math.sin(perp)*fw)),
            ]
            pygame.draw.polygon(surface, _BLK,           sh_pts)
            pygame.draw.polygon(surface, vis["shield_d"], sh_pts)
            inner = [
                sh_pts[0], sh_pts[1],
                ((sh_pts[1][0]+sh_pts[2][0])//2, (sh_pts[1][1]+sh_pts[2][1])//2),
                ((sh_pts[0][0]+sh_pts[3][0])//2, (sh_pts[0][1]+sh_pts[3][1])//2),
            ]
            pygame.draw.polygon(surface, vis["shield_col"], inner)
            pygame.draw.circle(surface, vis["shield_hi"], (s_cx, s_cy), 2)

        # ── Head / hat ───────────────────────────────────────────────────────
        hx = int(cx + math.cos(fa) * (half - 1))
        hy = int(cy + math.sin(fa) * (half - 1))
        pygame.draw.circle(surface, _BLK,  (hx, hy), 6)
        pygame.draw.circle(surface, _SKIN, (hx, hy), 5)

        helm_type = vis["helm_type"]
        if helm_type == "great":
            # Great helm: rect covering most of head
            pygame.draw.rect(surface, _BLK, (hx - 5, hy - 7, 10, 10))
            pygame.draw.rect(surface, (100, 100, 120), (hx - 4, hy - 6, 8, 8))
            pygame.draw.rect(surface, (160, 160, 180), (hx - 4, hy - 6, 8, 3))
            # Eye slit
            pygame.draw.line(surface, _BLK, (hx - 3, hy - 2), (hx + 3, hy - 2), 1)
        elif helm_type == "helm":
            # Rounded iron helm
            pygame.draw.circle(surface, _BLK,          (hx, hy - 3), 6)
            pygame.draw.circle(surface, (90, 90, 110),  (hx, hy - 3), 5)
            pygame.draw.circle(surface, (140, 140, 160),(hx, hy - 3), 3)
        else:
            # Default pointed hat
            hat_tip = (int(hx + math.cos(fa) * 10), int(hy + math.sin(fa) * 10))
            hat_l   = (int(hx + math.cos(perp) * 4), int(hy + math.sin(perp) * 4))
            hat_r   = (int(hx - math.cos(perp) * 4), int(hy - math.sin(perp) * 4))
            pygame.draw.polygon(surface, _BLK, [hat_tip, hat_l, hat_r])
            pygame.draw.polygon(surface, _HAT,
                                [(int(hx + math.cos(fa) * 9), int(hy + math.sin(fa) * 9)),
                                 (int(hx + math.cos(perp) * 3), int(hy + math.sin(perp) * 3)),
                                 (int(hx - math.cos(perp) * 3), int(hy - math.sin(perp) * 3))])

        # Eyes
        for sign in (1, -1):
            ex = int(hx + math.cos(fa) * 2 + math.cos(perp) * 2 * sign)
            ey = int(hy + math.sin(fa) * 2 + math.sin(perp) * 2 * sign)
            surface.set_at((ex, ey), _BLK)

        # ── Weapon (sword / axe / hammer / staff) ────────────────────────────
        sw0x = int(cx + math.cos(fa) * (half + 1))
        sw0y = int(cy + math.sin(fa) * (half + 1))
        slen = vis["sword_len"]
        sw1x = int(cx + math.cos(fa) * (half + 1 + slen))
        sw1y = int(cy + math.sin(fa) * (half + 1 + slen))
        pygame.draw.line(surface, _BLK,   (sw0x, sw0y), (sw1x, sw1y), vis["sword_w"] + 1)
        pygame.draw.line(surface, _SWORD, (sw0x, sw0y), (sw1x, sw1y), vis["sword_w"])
        # Guard
        gx = int(cx + math.cos(fa) * (half + 3))
        gy = int(cy + math.sin(fa) * (half + 3))
        pygame.draw.line(surface, _GUARD,
                         (int(gx + math.cos(perp) * 5), int(gy + math.sin(perp) * 5)),
                         (int(gx - math.cos(perp) * 5), int(gy - math.sin(perp) * 5)), 2)

        # ── Attack-ready ring ────────────────────────────────────────────────
        ring_r = half + 9
        if self._attack_timer > 0:
            t = 1.0 - self._attack_timer / self.attack_cooldown
            col = (int(200 * t), int(200 * t), 0)
            pygame.draw.arc(surface, col,
                            pygame.Rect(cx - ring_r, cy - ring_r, ring_r*2, ring_r*2),
                            -math.pi/2, -math.pi/2 + math.pi*2*t, 2)
        else:
            pygame.draw.circle(surface, (0, 200, 0), (cx, cy), ring_r, 1)

        # ── Attack arc flash ─────────────────────────────────────────────────
        if self._attack_anim > 0:
            r    = self.attack_range
            fade = self._attack_anim / 0.22
            arc_surf = pygame.Surface((r*2+10, r*2+10), pygame.SRCALPHA)
            pts2 = [(r+5, r+5)]
            for i in range(13):
                ang = fa - _ATTACK_HALF_ARC + 2 * _ATTACK_HALF_ARC * i / 12
                pts2.append((r+5 + math.cos(ang)*r, r+5 + math.sin(ang)*r))
            pygame.draw.polygon(arc_surf, (252, 248, 100, int(50*fade)), pts2)
            pygame.draw.arc(arc_surf, (252, 252, 200, int(240*fade)),
                            pygame.Rect(5, 5, r*2, r*2),
                            fa - _ATTACK_HALF_ARC, fa + _ATTACK_HALF_ARC, 3)
            surface.blit(arc_surf, (cx - r - 5, cy - r - 5))
