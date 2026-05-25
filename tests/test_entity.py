"""Tests for Entity base class (status effects, knockback)."""
import pytest
from src.entities.entity import Entity
from src.settings import STATUS_POISON, STATUS_BURN, STATUS_SLOW, STATUS_FREEZE


def make_entity():
    return Entity(100.0, 100.0, 20, (255, 0, 0))


# ── apply_status ──────────────────────────────────────────────────────────────

class TestApplyStatus:
    def test_apply_adds_status(self):
        e = make_entity()
        e.apply_status(STATUS_POISON, 3.0, 2.0)
        assert e.has_status(STATUS_POISON)

    def test_apply_refreshes_timer_if_longer(self):
        e = make_entity()
        e.apply_status(STATUS_POISON, 2.0, 1.0)
        e.apply_status(STATUS_POISON, 5.0, 1.0)
        assert e._status[STATUS_POISON]['timer'] == 5.0

    def test_apply_does_not_shorten_timer(self):
        e = make_entity()
        e.apply_status(STATUS_BURN, 5.0, 3.0)
        e.apply_status(STATUS_BURN, 1.0, 3.0)
        assert e._status[STATUS_BURN]['timer'] == 5.0

    def test_apply_uses_higher_magnitude(self):
        e = make_entity()
        e.apply_status(STATUS_BURN, 3.0, 2.0)
        e.apply_status(STATUS_BURN, 3.0, 5.0)
        assert e._status[STATUS_BURN]['magnitude'] == 5.0

    def test_multiple_statuses(self):
        e = make_entity()
        e.apply_status(STATUS_POISON, 2.0, 1.0)
        e.apply_status(STATUS_SLOW,   2.0, 1.0)
        assert e.has_status(STATUS_POISON)
        assert e.has_status(STATUS_SLOW)


# ── tick_statuses ─────────────────────────────────────────────────────────────

class TestTickStatuses:
    def test_expired_status_removed(self):
        e = make_entity()
        e.apply_status(STATUS_POISON, 0.5, 3.0)
        e.tick_statuses(1.0)   # dt > duration → expires
        assert not e.has_status(STATUS_POISON)

    def test_dot_returns_damage_on_tick(self):
        e = make_entity()
        e.apply_status(STATUS_BURN, 5.0, 4.0)
        # Force tick immediately: set tick_timer to 0 so next tick fires
        e._status[STATUS_BURN]['tick_timer'] = 0.0
        dmg = e.tick_statuses(0.01)
        assert dmg == 4

    def test_slow_does_no_damage(self):
        e = make_entity()
        e.apply_status(STATUS_SLOW, 3.0, 1.0)
        e._status[STATUS_SLOW]['tick_timer'] = 0.0
        dmg = e.tick_statuses(0.01)
        assert dmg == 0


# ── status_tint ───────────────────────────────────────────────────────────────

class TestStatusTint:
    def test_poison_tint(self):
        e = make_entity()
        e.apply_status(STATUS_POISON, 2.0)
        assert e.status_tint() == (30, 200, 30)

    def test_burn_tint(self):
        e = make_entity()
        e.apply_status(STATUS_BURN, 2.0)
        assert e.status_tint() == (230, 80, 10)

    def test_slow_tint(self):
        e = make_entity()
        e.apply_status(STATUS_SLOW, 2.0)
        assert e.status_tint() == (60, 100, 220)

    def test_freeze_tint(self):
        """
        BUG: freeze status has no tint in status_tint().
        The player visually looks untinted when frozen (ice blue is missing).
        """
        e = make_entity()
        e.apply_status(STATUS_FREEZE, 2.0)
        tint = e.status_tint()
        assert tint is not None, \
            "freeze status should return an ice-blue tint, but got None"
        # ice blue: R low, G medium-high, B high
        assert tint[2] > tint[0], "freeze tint should be blue-dominant"

    def test_no_status_no_tint(self):
        e = make_entity()
        assert e.status_tint() is None


# ── knockback ─────────────────────────────────────────────────────────────────

class TestKnockback:
    def test_apply_knockback_sets_velocity(self):
        e = make_entity()
        e.apply_knockback(1.0, 0.0, 200.0)
        assert e.kbx == 200.0
        assert e.kby == 0.0

    def test_apply_knockback_accumulates(self):
        e = make_entity()
        e.apply_knockback(1.0, 0.0, 100.0)
        e.apply_knockback(0.0, 1.0, 50.0)
        assert e.kbx == 100.0
        assert e.kby == 50.0
