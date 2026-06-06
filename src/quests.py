"""
Quest system for Dungeon Adventure.

QuestLog tracks active and completed quests.  Game events call notify() to
advance progress.  Completed quests return their reward payload for the game
to distribute (XP, gold) rather than touching the player directly.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from src.locale import t, t_quest_name


@dataclass
class Quest:
    id:          str
    name:        str
    desc:        str
    type:        str    # "kill" | "collect" | "reach" | "fetch" | "clear" | "bounty"
    target:      str    # enemy class, "gold", "floor_N", quest_item_id, bounty_id
    required:    int
    current:     int = 0
    reward_xp:   int = 0
    reward_gold: int = 0
    completed:   bool = False
    giver:       str = ""   # NPC title who assigned this quest
    floor:       int = 0    # target floor (fetch / clear / bounty)

    def progress_text(self) -> str:
        return f"{self.current}/{self.required}"

    def to_dict(self) -> dict:
        return {
            "id": self.id, "name": self.name, "desc": self.desc,
            "type": self.type, "target": self.target,
            "required": self.required, "current": self.current,
            "reward_xp": self.reward_xp, "reward_gold": self.reward_gold,
            "completed": self.completed,
            "giver": self.giver, "floor": self.floor,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Quest":
        known = {f.name for f in cls.__dataclass_fields__.values()}
        return cls(**{k: v for k, v in d.items() if k in known})


class QuestLog:
    def __init__(self):
        self.active:         list[Quest] = []
        self.completed:      list[Quest] = []
        self._all_ids:       set[str]   = set()
        self._pending:       list[str]  = []    # notification strings for the HUD
        self.floors_visited: set[int]   = set() # for "clear" quest tracking

    # ── Adding quests ─────────────────────────────────────────────────────────

    def add_quest(self, quest: Quest):
        if quest.id not in self._all_ids:
            self._all_ids.add(quest.id)
            self.active.append(quest)

    def add_floor_quests(self, floor: int):
        """Offer 2–3 quests suited to this floor depth."""
        pool: list[Quest] = []
        cycle = floor

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

    def add_npc_quests(self, floor: int, giver: str) -> list[Quest]:
        """
        Build 2-3 quests from a quest-giver NPC scaled to *floor*.
        Returns the new Quest objects (NOT yet added — player must accept them).
        """
        offered: list[Quest] = []
        f = max(1, floor)

        # Kill quest — random enemy tier appropriate for the floor
        kill_opts = [
            ("Goblin",   "Goblin Bounty",   5, 1),
            ("Skeleton", "Skeleton Patrol", 4, 2),
            ("Orc",      "Orc Culling",     3, 3),
            ("Demon",    "Demon Contract",  2, 5),
        ]
        eligible = [o for o in kill_opts if f >= o[3]]
        if eligible:
            target, name, req, _ = random.choice(eligible)
            qid = f"npc_kill_{target.lower()}_{giver[:4]}_{f}"
            if qid not in self._all_ids:
                offered.append(Quest(
                    id=qid, name=name, giver=giver, floor=f,
                    desc=f"Kill {req} {target}s for {giver}.",
                    type="kill", target=target, required=req,
                    reward_xp=req * 120 * f, reward_gold=req * 30 * f,
                ))

        # Fetch quest — go to floor+1 or +2, pick up a relic
        fetch_floor = f + random.randint(1, 2)
        relic_names = ["Ancient Relic", "Lost Tome", "Dungeon Sigil",
                       "Cursed Idol", "Forgotten Key"]
        relic = random.choice(relic_names)
        qid = f"npc_fetch_{giver[:4]}_{f}"
        if qid not in self._all_ids:
            offered.append(Quest(
                id=qid, name=f"Retrieve the {relic}", giver=giver,
                floor=fetch_floor,
                desc=f"Find the {relic} on floor {fetch_floor} and return to town.",
                type="fetch", target=qid, required=1,
                reward_xp=250 * f, reward_gold=80 * f,
            ))

        # Clear quest — explore a deeper floor and return to town
        if f >= 2:
            clear_floor = f + random.randint(1, 3)
            qid = f"npc_clear_{giver[:4]}_{f}"
            if qid not in self._all_ids:
                offered.append(Quest(
                    id=qid, name=f"Scout Floor {clear_floor}", giver=giver,
                    floor=clear_floor,
                    desc=f"Reach floor {clear_floor} and return to town.",
                    type="clear", target=f"floor_{clear_floor}", required=1,
                    reward_xp=300 * f, reward_gold=100 * f,
                ))

        # Bounty — on floor f, kill a named elite
        qid = f"npc_bounty_{giver[:4]}_{f}"
        if f >= 3 and qid not in self._all_ids:
            offered.append(Quest(
                id=qid, name=f"Floor {f} Bounty", giver=giver, floor=f,
                desc=f"Slay the marked elite on floor {f}.",
                type="bounty", target=qid, required=1,
                reward_xp=400 * f, reward_gold=150 * f,
            ))

        return offered[:3]  # offer at most 3

    def track_floor(self, floor: int) -> None:
        """Record that the player has visited this floor (clears 'clear' quests)."""
        self.floors_visited.add(floor)

    def on_town_return(self) -> list[Quest]:
        """
        Check clear quests: if the required floor was visited, complete them.
        Returns newly completed quests for reward distribution.
        """
        done: list[Quest] = []
        for q in list(self.active):
            if q.type == "clear" and q.floor in self.floors_visited:
                q.current = q.required
                q.completed = True
                self.active.remove(q)
                self.completed.append(q)
                done.append(q)
                self._pending.append(
                    f"{t('quest.complete')}: {t_quest_name(q.id, q.name)}!")
        return done

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
                    self._pending.append(
                        f"{t('quest.complete')}: {t_quest_name(q.id, q.name)}!")
        return done

    def pop_notifications(self) -> list[str]:
        msgs = self._pending[:]
        self._pending.clear()
        return msgs

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "active":         [q.to_dict() for q in self.active],
            "completed":      [q.to_dict() for q in self.completed],
            "all_ids":        list(self._all_ids),
            "floors_visited": list(self.floors_visited),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "QuestLog":
        ql = cls()
        for qd in data.get("active", []):
            ql.active.append(Quest.from_dict(qd))
        for qd in data.get("completed", []):
            ql.completed.append(Quest.from_dict(qd))
        ql._all_ids       = set(data.get("all_ids", []))
        ql.floors_visited = set(data.get("floors_visited", []))
        return ql
