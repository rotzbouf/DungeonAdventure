"""
Quest system for Dungeon Adventure.

QuestLog tracks active and completed quests.  Game events call notify() to
advance progress.  Completed quests return their reward payload for the game
to distribute (XP, gold) rather than touching the player directly.
"""
from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass
class Quest:
    id:          str
    name:        str
    desc:        str
    type:        str    # "kill" | "collect" | "reach"
    target:      str    # enemy class name, "gold", "floor_N" …
    required:    int
    current:     int = 0
    reward_xp:   int = 0
    reward_gold: int = 0
    completed:   bool = False

    def progress_text(self) -> str:
        return f"{self.current}/{self.required}"

    def to_dict(self) -> dict:
        return {
            "id": self.id, "name": self.name, "desc": self.desc,
            "type": self.type, "target": self.target,
            "required": self.required, "current": self.current,
            "reward_xp": self.reward_xp, "reward_gold": self.reward_gold,
            "completed": self.completed,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Quest":
        return cls(**d)


class QuestLog:
    def __init__(self):
        self.active:    list[Quest] = []
        self.completed: list[Quest] = []
        self._all_ids:  set[str]   = set()
        self._pending:  list[str]  = []    # notification strings for the HUD

    # ── Adding quests ─────────────────────────────────────────────────────────

    def add_quest(self, quest: Quest):
        if quest.id not in self._all_ids:
            self._all_ids.add(quest.id)
            self.active.append(quest)

    def add_floor_quests(self, floor: int, ng_plus: int = 0):
        """Offer 2–3 quests suited to this floor depth."""
        pool: list[Quest] = []
        cycle = floor + ng_plus * 5

        # Kill quests — scale by depth
        enemy_quests = [
            ("Goblin",   "Goblin Hunter",  "Kill 5 Goblins.",       5, 1),
            ("Skeleton", "Bone Crusher",   "Kill 4 Skeletons.",     4, 2),
            ("Orc",      "Orc Slayer",     "Kill 3 Orcs.",          3, 3),
            ("Demon",    "Demon Hunter",   "Kill 2 Demons.",        2, 4),
            ("Elite",    "Elite Destroyer","Kill 2 Elite enemies.", 2, 3),
        ]
        for target, name, desc, req, min_floor in enemy_quests:
            if floor >= min_floor:
                xp   = req * 80 * floor
                gold = req * 20 * floor
                pool.append(Quest(
                    id=f"{target.lower()}_f{cycle}",
                    name=name, desc=desc,
                    type="kill", target=target,
                    required=req,
                    reward_xp=xp, reward_gold=gold,
                ))

        # Gold quest
        need = 50 * max(1, floor)
        pool.append(Quest(
            id=f"gold_f{cycle}",
            name="Gold Rush",
            desc=f"Collect {need} gold on this run.",
            type="collect", target="gold",
            required=need,
            reward_xp=100 * floor, reward_gold=0,
        ))

        # Descent quest
        pool.append(Quest(
            id=f"reach_f{cycle + 1}",
            name="Deeper Down",
            desc=f"Descend to floor {floor + 1}.",
            type="reach", target=f"floor_{floor + 1}",
            required=1,
            reward_xp=200 * floor, reward_gold=50 * floor,
        ))

        available = [q for q in pool if q.id not in self._all_ids]

        # The descent quest is always offered — pull it out first so the random
        # shuffle of kill/collect quests can't accidentally drop it.
        reach_id   = f"reach_f{cycle + 1}"
        guaranteed = [q for q in available if q.id == reach_id]
        random_pool = [q for q in available if q.id != reach_id]
        random.shuffle(random_pool)

        for q in guaranteed + random_pool[:2]:
            self.add_quest(q)

    # ── Notifying ─────────────────────────────────────────────────────────────

    def notify(self, event: str, tag: str, amount: int = 1) -> list[Quest]:
        """
        Advance matching quests.  Returns a list of newly completed Quest
        objects so the caller can distribute their rewards.
        """
        done: list[Quest] = []
        for q in list(self.active):
            if q.type == event and q.target == tag and not q.completed:
                q.current = min(q.required, q.current + amount)
                if q.current >= q.required:
                    q.completed = True
                    self.active.remove(q)
                    self.completed.append(q)
                    done.append(q)
                    self._pending.append(f"Quest Complete: {q.name}!")
        return done

    def pop_notifications(self) -> list[str]:
        msgs = self._pending[:]
        self._pending.clear()
        return msgs

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "active":    [q.to_dict() for q in self.active],
            "completed": [q.to_dict() for q in self.completed],
            "all_ids":   list(self._all_ids),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "QuestLog":
        ql = cls()
        for qd in data.get("active", []):
            ql.active.append(Quest.from_dict(qd))
        for qd in data.get("completed", []):
            ql.completed.append(Quest.from_dict(qd))
        ql._all_ids = set(data.get("all_ids", []))
        return ql
