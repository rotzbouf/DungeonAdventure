"""Tests for the quest system."""
from src.quests import Quest, QuestLog


# ── Quest.progress_text ───────────────────────────────────────────────────────

class TestQuestProgressText:
    def test_initial(self):
        q = Quest("id", "name", "desc", "kill", "Goblin", 5)
        assert q.progress_text() == "0/5"

    def test_partial(self):
        q = Quest("id", "name", "desc", "kill", "Goblin", 5, current=3)
        assert q.progress_text() == "3/5"


# ── QuestLog.add_quest ────────────────────────────────────────────────────────

class TestAddQuest:
    def test_adds_to_active(self):
        ql = QuestLog()
        q  = Quest("q1", "n", "d", "kill", "Goblin", 3)
        ql.add_quest(q)
        assert q in ql.active

    def test_duplicate_id_ignored(self):
        ql = QuestLog()
        q  = Quest("q1", "n", "d", "kill", "Goblin", 3)
        ql.add_quest(q)
        ql.add_quest(q)
        assert len(ql.active) == 1


# ── QuestLog.notify ───────────────────────────────────────────────────────────

class TestNotify:
    def _make_kill_quest(self, target="Goblin", required=3) -> tuple[QuestLog, Quest]:
        ql = QuestLog()
        q  = Quest("q1", "n", "d", "kill", target, required,
                   reward_xp=100, reward_gold=50)
        ql.add_quest(q)
        return ql, q

    def test_wrong_event_does_nothing(self):
        ql, q = self._make_kill_quest()
        done = ql.notify("collect", "Goblin")
        assert not done
        assert q.current == 0

    def test_wrong_target_does_nothing(self):
        ql, q = self._make_kill_quest("Goblin")
        done = ql.notify("kill", "Orc")
        assert not done
        assert q.current == 0

    def test_correct_event_advances(self):
        ql, q = self._make_kill_quest(required=3)
        ql.notify("kill", "Goblin")
        assert q.current == 1

    def test_amount_parameter(self):
        ql, q = self._make_kill_quest(required=10)
        ql.notify("kill", "Goblin", amount=4)
        assert q.current == 4

    def test_current_capped_at_required(self):
        ql, q = self._make_kill_quest(required=3)
        ql.notify("kill", "Goblin", amount=100)
        assert q.current == 3

    def test_completion_moves_to_completed(self):
        ql, q = self._make_kill_quest(required=2)
        ql.notify("kill", "Goblin")
        ql.notify("kill", "Goblin")
        assert q in ql.completed
        assert q not in ql.active

    def test_completion_returns_quest(self):
        ql, q = self._make_kill_quest(required=1)
        done = ql.notify("kill", "Goblin")
        assert done == [q]

    def test_already_completed_not_notified_again(self):
        ql, q = self._make_kill_quest(required=1)
        ql.notify("kill", "Goblin")
        done2 = ql.notify("kill", "Goblin")
        assert done2 == []

    def test_completed_flag(self):
        ql, q = self._make_kill_quest(required=1)
        ql.notify("kill", "Goblin")
        assert q.completed

    def test_collect_event_with_amount(self):
        ql = QuestLog()
        q  = Quest("gold1", "n", "d", "collect", "gold", 100,
                   reward_xp=50, reward_gold=0)
        ql.add_quest(q)
        ql.notify("collect", "gold", 60)
        assert q.current == 60
        done = ql.notify("collect", "gold", 60)
        assert q.completed
        assert done == [q]


# ── QuestLog.pop_notifications ────────────────────────────────────────────────

class TestPopNotifications:
    def test_returns_pending_and_clears(self):
        ql = QuestLog()
        q  = Quest("q1", "Done!", "d", "kill", "Goblin", 1)
        ql.add_quest(q)
        ql.notify("kill", "Goblin")
        msgs = ql.pop_notifications()
        assert len(msgs) == 1
        assert "Done!" in msgs[0]
        assert ql.pop_notifications() == []


# ── add_floor_quests ──────────────────────────────────────────────────────────

class TestFloorQuests:
    def test_adds_at_least_one_quest(self):
        ql = QuestLog()
        ql.add_floor_quests(1)
        assert len(ql.active) >= 1

    def test_adds_at_most_three_quests(self):
        ql = QuestLog()
        ql.add_floor_quests(1)
        assert len(ql.active) <= 3

    def test_duplicate_floor_call_doesnt_readd(self):
        ql = QuestLog()
        ql.add_floor_quests(1)
        count_before = len(ql.active)
        ql.add_floor_quests(1)       # same floor — same IDs — should be no-ops
        assert len(ql.active) == count_before

    def test_floor_5_includes_reach_quest(self):
        ql = QuestLog()
        ql.add_floor_quests(5)
        targets = {q.target for q in ql.active}
        assert "floor_6" in targets


# ── Serialisation ─────────────────────────────────────────────────────────────

class TestSerialisation:
    def test_quest_round_trip(self):
        q  = Quest("q1", "name", "desc", "kill", "Goblin", 5,
                   current=3, reward_xp=100, reward_gold=50, completed=False)
        q2 = Quest.from_dict(q.to_dict())
        assert q2.id          == q.id
        assert q2.current     == q.current
        assert q2.reward_xp   == q.reward_xp
        assert q2.completed   == q.completed

    def test_questlog_round_trip(self):
        ql = QuestLog()
        ql.add_floor_quests(2)
        # Complete one quest
        for q in list(ql.active):
            ql.notify(q.type, q.target, q.required)
            break
        d   = ql.to_dict()
        ql2 = QuestLog.from_dict(d)
        assert len(ql2.active)    == len(ql.active)
        assert len(ql2.completed) == len(ql.completed)
        assert ql2._all_ids       == ql._all_ids
