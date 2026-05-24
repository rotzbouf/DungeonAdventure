import math
import pygame
from src.entities.entity import Entity
from src.settings import (TILE_SIZE, PLAYER_COLOR, PLAYER_SPEED, PLAYER_SIZE,
                           PLAYER_MAX_HP, PLAYER_MAX_MANA, PLAYER_BASE_ATTACK,
                           PLAYER_BASE_DEFENSE, PLAYER_ATTACK_RANGE,
                           PLAYER_ATTACK_COOLDOWN, XP_BASE,
                           MAX_PLAYER_LEVEL, STAT_POINTS_PER_LEVEL,
                           BASE_STR, BASE_DEX, BASE_VIT, BASE_ENE)

_ATTACK_HALF_ARC = math.pi * 0.4   # ±72° — visual and hit detection use the same value


class Player(Entity):
    def __init__(self, x: float, y: float):
        super().__init__(x, y, PLAYER_SIZE, PLAYER_COLOR)

        self.max_hp   = PLAYER_MAX_HP
        self.hp       = float(PLAYER_MAX_HP)
        self.max_mana = PLAYER_MAX_MANA
        self.mana     = float(PLAYER_MAX_MANA)

        self.base_attack  = PLAYER_BASE_ATTACK
        self.base_defense = PLAYER_BASE_DEFENSE
        self.attack_range = PLAYER_ATTACK_RANGE
        self.attack_cooldown = PLAYER_ATTACK_COOLDOWN
        self.speed = PLAYER_SPEED

        self.level      = 1
        self.xp         = 0
        self.xp_to_next = XP_BASE
        self.gold       = 0

        # ── D2-style core attributes ─────────────────────────────────────────
        self.str_pts  = BASE_STR   # Strength  → attack
        self.dex_pts  = BASE_DEX   # Dexterity → defense + crit
        self.vit_pts  = BASE_VIT   # Vitality  → max HP
        self.ene_pts  = BASE_ENE   # Energy    → max mana
        self.stat_points = 0       # unspent points available to allocate

        # ── D2-style equipment slots ─────────────────────────────────────────
        from src.items.item import (SLOT_WEAPON, SLOT_SHIELD, SLOT_HELM,
                                    SLOT_CHEST, SLOT_GLOVES, SLOT_BOOTS,
                                    SLOT_BELT, SLOT_RING, SLOT_AMULET)
        self.equipment: dict = {
            SLOT_WEAPON: None,
            SLOT_SHIELD: None,
            SLOT_HELM:   None,
            SLOT_CHEST:  None,
            SLOT_GLOVES: None,
            SLOT_BOOTS:  None,
            SLOT_BELT:   None,
            SLOT_RING:   None,
            "ring2":     None,
            SLOT_AMULET: None,
        }
        self.backpack: list = []    # unequipped equip items
        self.potions:  list = []    # potions always separate

        self._attack_timer     = 0.0
        self._invincible_timer = 0.0
        self._attack_anim      = 0.0
        self.attack_angle      = 0.0

    # ─── Equipment stat accumulator ──────────────────────────────────────────────

    def _equip_total(self, kind: str) -> float:
        """Sum a modifier kind across all equipped items."""
        total = 0.0
        for item in self.equipment.values():
            if item is not None:
                total += item.get_mod_total(kind)
        return total

    # ─── Derived stats ───────────────────────────────────────────────────────────

    @property
    def attack(self) -> int:
        from src.items.item import MOD_ATK, MOD_ATK_PCT
        # STR above floor gives +2 attack per point
        base = self.base_attack + self.level * 2 + (self.str_pts - BASE_STR) * 2
        flat = self._equip_total(MOD_ATK)
        pct  = self._equip_total(MOD_ATK_PCT)
        return int(base + flat + base * pct / 100)

    @property
    def defense(self) -> int:
        from src.items.item import MOD_DEF
        # DEX above floor gives +1 defense per point
        base = self.base_defense + self.level // 2 + (self.dex_pts - BASE_DEX)
        return int(base + self._equip_total(MOD_DEF))

    @property
    def max_hp_total(self) -> int:
        from src.items.item import MOD_MAX_HP
        # VIT above floor gives +10 max HP per point
        vit_bonus = (self.vit_pts - BASE_VIT) * 10
        return self.max_hp + vit_bonus + int(self._equip_total(MOD_MAX_HP))

    @property
    def max_mana_total(self) -> int:
        from src.items.item import MOD_MAX_MANA
        # ENE above floor gives +5 max mana per point
        ene_bonus = (self.ene_pts - BASE_ENE) * 5
        return self.max_mana + ene_bonus + int(self._equip_total(MOD_MAX_MANA))

    @property
    def crit_chance(self) -> float:
        from src.items.item import MOD_CRIT
        # DEX above floor gives +0.5% crit per point
        return (self.dex_pts - BASE_DEX) * 0.5 + self._equip_total(MOD_CRIT)

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
        if self.has_status('slow'):
            base_spd *= 0.60
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

    # Backward-compat properties used by HUD / old code
    @property
    def equipped_weapon(self):
        from src.items.item import SLOT_WEAPON
        return self.equipment.get(SLOT_WEAPON)

    @property
    def equipped_armor(self):
        from src.items.item import SLOT_CHEST
        return self.equipment.get(SLOT_CHEST)

    # ─── Inventory ───────────────────────────────────────────────────────────────

    def add_item(self, item):
        from src.items.item import EquipItem, HealthPotion
        if isinstance(item, HealthPotion):
            self.potions.append(item)
        elif isinstance(item, EquipItem):
            # Auto-equip if slot is empty; otherwise send to backpack
            slot = item.slot
            key  = slot
            # Ring: fill ring1 first, then ring2
            if slot == "ring":
                if self.equipment.get("ring") is None:
                    key = "ring"
                elif self.equipment.get("ring2") is None:
                    key = "ring2"
                else:
                    key = None  # both rings occupied → backpack
            if key is not None and self.equipment.get(key) is None:
                self.equipment[key] = item
            else:
                self.backpack.append(item)

    def equip(self, item, slot_key: str | None = None) -> object | None:
        """Equip item; returns the previously equipped item (or None)."""
        from src.items.item import EquipItem, SLOT_RING
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
        """Move equipped item in slot_key to backpack."""
        item = self.equipment.get(slot_key)
        if item is not None:
            self.equipment[slot_key] = None
            self.backpack.append(item)

    def use_potion(self) -> bool:
        if self.potions and self.hp < self.max_hp_total:
            potion = self.potions.pop()
            self.heal(potion.heal_amount)
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
            # Small automatic gains per level — main growth comes from stat investment
            self.max_hp  += 5
            self.hp       = min(self.hp + 5, self.max_hp_total)
            self.max_mana += 3
            self.mana     = min(self.mana + 3, self.max_mana_total)
            self.stat_points += STAT_POINTS_PER_LEVEL
            leveled = True
        if self.level >= MAX_PLAYER_LEVEL:
            self.xp = self.xp_to_next   # pin XP bar full at cap
        return leveled

    def spend_stat(self, stat: str) -> bool:
        """Spend 1 stat point. stat ∈ {'str','dex','vit','ene'}.
        Returns True on success."""
        if self.stat_points <= 0:
            return False
        if stat == 'str':
            self.str_pts += 1
        elif stat == 'dex':
            self.dex_pts += 1
        elif stat == 'vit':
            old_max = self.max_hp_total
            self.vit_pts += 1
            # Grant the new HP immediately (D2 behaviour)
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
        """0.0 = just attacked, 1.0 = fully ready."""
        cd = self.effective_cooldown
        if cd == 0:
            return 1.0
        return 1.0 - min(1.0, self._attack_timer / cd)

    def try_attack(self, enemies: list) -> list:
        if self._attack_timer > 0:
            return []
        self._attack_timer = self.effective_cooldown
        self._attack_anim  = 0.22

        # Snap to currently-held direction so attack matches live key state,
        # not the angle cached from the previous frame's update().
        keys = pygame.key.get_pressed()
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
            angle_to = math.atan2(enemy.y - self.y, enemy.x - self.x)
            diff = abs(self.attack_angle - angle_to)
            if diff > math.pi:
                diff = math.pi * 2 - diff
            if diff < _ATTACK_HALF_ARC:
                hit.append(enemy)
        return hit

    # ─── Update ──────────────────────────────────────────────────────────────────

    def update(self, dt: float, dungeon, camera):
        self._attack_timer     = max(0.0, self._attack_timer - dt)
        self._invincible_timer = max(0.0, self._invincible_timer - dt)
        self._attack_anim      = max(0.0, self._attack_anim - dt)

        # Slow mana regeneration
        self.mana = min(self.max_mana_total, self.mana + 3.0 * dt)
        # HP regeneration from gear
        regen = self.hp_regen_rate
        if regen > 0 and self.hp < self.max_hp_total:
            self.hp = min(self.max_hp_total, self.hp + regen * dt)

        # Status effect DoT (poison, burn)
        dot_dmg = self.tick_statuses(dt)
        if dot_dmg > 0 and self._invincible_timer <= 0:
            self.hp = max(0.0, self.hp - dot_dmg)

        keys = pygame.key.get_pressed()
        dx = dy = 0.0
        if keys[pygame.K_w] or keys[pygame.K_UP]:    dy -= 1.0
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:  dy += 1.0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:  dx -= 1.0
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: dx += 1.0

        if dx != 0 and dy != 0:
            dx *= 0.7071
            dy *= 0.7071

        if dx != 0 or dy != 0:
            self.attack_angle = math.atan2(dy, dx)

        half  = self.size // 2
        mg    = 2
        spd   = self.move_speed      # includes gear speed bonuses
        new_x = self.x + dx * spd * dt
        test  = pygame.Rect(new_x - half + mg, self.y - half + mg,
                            self.size - mg * 2, self.size - mg * 2)
        if self._rect_ok(test, dungeon):
            self.x = new_x

        new_y = self.y + dy * spd * dt
        test  = pygame.Rect(self.x - half + mg, new_y - half + mg,
                            self.size - mg * 2, self.size - mg * 2)
        if self._rect_ok(test, dungeon):
            self.y = new_y

        # ── Knockback physics ────────────────────────────────────────────────
        if self.kbx or self.kby:
            new_x = self.x + self.kbx * dt
            test  = pygame.Rect(new_x - half + mg, self.y - half + mg,
                                self.size - mg * 2, self.size - mg * 2)
            if self._rect_ok(test, dungeon):
                self.x = new_x
            else:
                self.kbx = 0.0

            new_y = self.y + self.kby * dt
            test  = pygame.Rect(self.x - half + mg, new_y - half + mg,
                                self.size - mg * 2, self.size - mg * 2)
            if self._rect_ok(test, dungeon):
                self.y = new_y
            else:
                self.kby = 0.0

            friction = max(0.0, 1.0 - 12.0 * dt)
            self.kbx *= friction
            self.kby *= friction
            if abs(self.kbx) < 2.0:
                self.kbx = 0.0
            if abs(self.kby) < 2.0:
                self.kby = 0.0

        self._sync_rect()

    def _rect_ok(self, rect: pygame.Rect, dungeon) -> bool:
        for cx, cy in [(rect.left, rect.top), (rect.right, rect.top),
                       (rect.left, rect.bottom), (rect.right, rect.bottom)]:
            if not dungeon.is_walkable(int(cx // TILE_SIZE), int(cy // TILE_SIZE)):
                return False
        return True

    # ─── Draw ────────────────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface, camera):
        if self._invincible_timer > 0 and int(self._invincible_timer * 14) % 2:
            return

        dr = camera.apply(self.rect)
        cx, cy = dr.centerx, dr.centery
        fa     = self.attack_angle
        perp   = fa + math.pi / 2

        # ── Player colour palette ─────────────────────────────────────────────
        _BLK      = (0,    0,    0)
        _TUNIC    = (0,  160,    0)   # green tunic
        _TUNIC_D  = (0,   88,    0)   # darker tunic shadow
        # Blend status tint into tunic colour
        _tint = self.status_tint()
        if _tint:
            _TUNIC   = tuple(min(255, (c + t) // 2) for c, t in zip(_TUNIC,   _tint))
            _TUNIC_D = tuple(min(255, (c + t) // 2) for c, t in zip(_TUNIC_D, _tint))
        _SKIN     = (252, 188,  100)  # skin tone
        _SKIN_D   = (180, 128,   56)
        _SWORD    = (216, 216,  252)  # silvery sword blade
        _GUARD    = (176, 140,   36)  # gold cross-guard
        _SHIELD   = (0,   52,  216)   # blue shield
        _SHIELD_D = (0,   24,  140)
        _SHIELD_H = (80, 140,  252)   # shield highlight
        _HAT      = (0,  160,    0)   # same green as tunic

        half = self.size // 2

        # ── Body (green tunic) ───────────────────────────────────────────────
        body = pygame.Rect(cx - half + 2, cy - half + 2, self.size - 4, self.size - 4)
        pygame.draw.rect(surface, _BLK, body.inflate(2, 2))
        pygame.draw.rect(surface, _TUNIC, body)
        # Lower-half shadow stripe
        low = pygame.Rect(body.left, body.centery, body.width, body.height // 2)
        pygame.draw.rect(surface, _TUNIC_D, low)

        # ── Shield (on perpendicular-left of facing direction) ───────────────
        s_cx = int(cx - math.cos(fa) * 2 + math.cos(perp) * (half + 5))
        s_cy = int(cy - math.sin(fa) * 2 + math.sin(perp) * (half + 5))
        fw, fh = 5, 7           # shield half-extents along facing/perp
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
        pygame.draw.polygon(surface, _BLK,      sh_pts)
        pygame.draw.polygon(surface, _SHIELD_D, [sh_pts[0], sh_pts[1], sh_pts[2], sh_pts[3]])
        # Inner highlight on top-half of shield
        inner = [
            sh_pts[0],
            sh_pts[1],
            ((sh_pts[1][0]+sh_pts[2][0])//2, (sh_pts[1][1]+sh_pts[2][1])//2),
            ((sh_pts[0][0]+sh_pts[3][0])//2, (sh_pts[0][1]+sh_pts[3][1])//2),
        ]
        pygame.draw.polygon(surface, _SHIELD, inner)
        # Highlight pip
        pygame.draw.circle(surface, _SHIELD_H, (s_cx, s_cy), 2)

        # ── Head / hat (facing-side of body) ─────────────────────────────────
        hx = int(cx + math.cos(fa) * (half - 1))
        hy = int(cy + math.sin(fa) * (half - 1))
        pygame.draw.circle(surface, _BLK,    (hx, hy), 6)
        pygame.draw.circle(surface, _SKIN,   (hx, hy), 5)
        # Hat tip (green triangle extending in facing direction)
        hat_tip = (int(hx + math.cos(fa) * 10), int(hy + math.sin(fa) * 10))
        hat_l   = (int(hx + math.cos(perp) * 4), int(hy + math.sin(perp) * 4))
        hat_r   = (int(hx - math.cos(perp) * 4), int(hy - math.sin(perp) * 4))
        pygame.draw.polygon(surface, _BLK,  [hat_tip, hat_l, hat_r])
        pygame.draw.polygon(surface, _HAT,
                            [(int(hx + math.cos(fa) * 9), int(hy + math.sin(fa) * 9)),
                             (int(hx + math.cos(perp) * 3), int(hy + math.sin(perp) * 3)),
                             (int(hx - math.cos(perp) * 3), int(hy - math.sin(perp) * 3))])
        # Eyes (two 1-px dots offset toward facing, side by side)
        for sign in (1, -1):
            ex = int(hx + math.cos(fa) * 2 + math.cos(perp) * 2 * sign)
            ey = int(hy + math.sin(fa) * 2 + math.sin(perp) * 2 * sign)
            surface.set_at((ex, ey), _BLK)

        # ── Sword (extends from body in facing direction) ─────────────────────
        sw0x = int(cx + math.cos(fa) * (half + 1))
        sw0y = int(cy + math.sin(fa) * (half + 1))
        sw1x = int(cx + math.cos(fa) * (half + 15))
        sw1y = int(cy + math.sin(fa) * (half + 15))
        pygame.draw.line(surface, _BLK,   (sw0x, sw0y), (sw1x, sw1y), 3)
        pygame.draw.line(surface, _SWORD, (sw0x, sw0y), (sw1x, sw1y), 2)
        # Cross-guard
        gx = int(cx + math.cos(fa) * (half + 3))
        gy = int(cy + math.sin(fa) * (half + 3))
        pygame.draw.line(surface, _GUARD,
                         (int(gx + math.cos(perp) * 5), int(gy + math.sin(perp) * 5)),
                         (int(gx - math.cos(perp) * 5), int(gy - math.sin(perp) * 5)), 2)

        # ── Attack-ready indicator (green glow ring below sprite) ────────────
        ring_r = half + 9
        if self._attack_timer > 0:
            t = 1.0 - self._attack_timer / self.attack_cooldown
            col = (int(200 * t), int(200 * t), 0)
            pygame.draw.arc(surface, col,
                            pygame.Rect(cx - ring_r, cy - ring_r, ring_r * 2, ring_r * 2),
                            -math.pi / 2, -math.pi / 2 + math.pi * 2 * t, 2)
        else:
            pygame.draw.circle(surface, (0, 200, 0), (cx, cy), ring_r, 1)

        # ── Sword-swing arc (bright yellow-white flash) ──────────────────────
        if self._attack_anim > 0:
            r    = self.attack_range
            fade = self._attack_anim / 0.22
            arc_surf = pygame.Surface((r * 2 + 10, r * 2 + 10), pygame.SRCALPHA)
            pts2 = [(r + 5, r + 5)]
            for i in range(13):
                ang = fa - _ATTACK_HALF_ARC + (2 * _ATTACK_HALF_ARC * i / 12)
                pts2.append((r + 5 + math.cos(ang) * r, r + 5 + math.sin(ang) * r))
            pygame.draw.polygon(arc_surf, (252, 248, 100, int(50 * fade)), pts2)
            pygame.draw.arc(arc_surf, (252, 252, 200, int(240 * fade)),
                            pygame.Rect(5, 5, r * 2, r * 2),
                            fa - _ATTACK_HALF_ARC, fa + _ATTACK_HALF_ARC, 3)
            surface.blit(arc_surf, (cx - r - 5, cy - r - 5))
