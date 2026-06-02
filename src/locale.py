"""
Localisation module — English (en) and German (de).

Usage
-----
    from src.locale import t, set_lang, lang

    t("inv.title")                    → "INVENTORY" / "INVENTAR"
    t("hud.level_up", n=5)           → "LEVEL UP!  NOW LEVEL 5"
    set_lang("de")                    → switch all future t() calls to German
    lang()                            → "en" or "de"
"""
from __future__ import annotations

_LANG: str = "en"


def lang() -> str:
    """Return the active language code."""
    return _LANG


def set_lang(code: str) -> None:
    """Switch the active language ("en" or "de")."""
    global _LANG
    if code in ("en", "de"):
        _LANG = code


def t(key: str, **kwargs) -> str:
    """
    Return the translation for *key* in the active language.
    Falls back to English, then to the bare key.
    Optional keyword arguments are substituted via str.format().
    """
    entry = _T.get(key)
    if entry is None:
        return key
    text = entry.get(_LANG) or entry.get("en") or key
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, ValueError, IndexError):
            pass
    return text


# ── Quest helpers ─────────────────────────────────────────────────────────────

_QUEST_PREFIXES = [
    ("goblin",   "quest.goblin_hunter"),
    ("skeleton", "quest.bone_crusher"),
    ("orc",      "quest.orc_slayer"),
    ("demon",    "quest.demon_hunter"),
    ("elite",    "quest.elite_destroyer"),
    ("gold",     "quest.gold_rush"),
    ("reach",    "quest.deeper_down"),
]


def t_quest_name(quest_id: str, fallback: str = "") -> str:
    """Return the localised display name for a quest given its ID.
    Falls back to *fallback* (or the raw ID) when no prefix matches."""
    for prefix, base_key in _QUEST_PREFIXES:
        if quest_id.startswith(prefix):
            return t(f"{base_key}.name")
    return fallback if fallback else quest_id


def t_quest_desc(quest_id: str, required: int, target: str = "") -> str:
    """Return the localised description for a quest."""
    if quest_id.startswith("goblin"):   return t("quest.goblin_hunter.desc")
    if quest_id.startswith("skeleton"): return t("quest.bone_crusher.desc")
    if quest_id.startswith("orc"):      return t("quest.orc_slayer.desc")
    if quest_id.startswith("demon"):    return t("quest.demon_hunter.desc")
    if quest_id.startswith("elite"):    return t("quest.elite_destroyer.desc")
    if quest_id.startswith("gold"):
        return t("quest.gold_rush.desc", n=required)
    if quest_id.startswith("reach"):
        # target is e.g. "floor_4"; required is 1
        try:
            floor_n = int(target.split("_")[1])
        except (IndexError, ValueError):
            floor_n = required
        return t("quest.deeper_down.desc", n=floor_n)
    return ""


# ── Slot label helper ─────────────────────────────────────────────────────────

_SLOT_LABEL_KEYS: dict[str, str] = {
    "weapon": "slot.weapon",
    "shield": "slot.shield",
    "helm":   "slot.helm",
    "chest":  "slot.chest",
    "gloves": "slot.gloves",
    "boots":  "slot.boots",
    "belt":   "slot.belt",
    "ring":   "slot.ring",
    "ring2":  "slot.ring2",
    "amulet": "slot.amulet",
}


def get_slot_label(key: str) -> str:
    """Return the localised slot label (upper-cased)."""
    return t(_SLOT_LABEL_KEYS.get(key, f"slot.{key}"))


# ── String table ──────────────────────────────────────────────────────────────

_T: dict[str, dict[str, str]] = {

    # ── Main Menu ─────────────────────────────────────────────────────────────
    "menu.subtitle":       {"en": "A Classic Dungeon Crawler",
                            "de": "Ein klassisches Dungeon-Abenteuer"},
    "menu.press_enter":    {"en": "- PRESS  ENTER  TO  START -",
                            "de": "- ENTER  DRÜCKEN  ZUM  START -"},
    "menu.press_c":        {"en": "- PRESS  C  TO  CONTINUE -",
                            "de": "- C  DRÜCKEN  ZUM  FORTFAHREN -"},
    "menu.skill_note":     {"en": "* requires skill tree unlock",
                            "de": "* benötigt Fähigkeitsbaum-Freischaltung"},
    "menu.lang_label":     {"en": "LANGUAGE", "de": "SPRACHE"},

    # Controls list
    "ctrl.move":           {"en": "Move",
                            "de": "Bewegen"},
    "ctrl.attack":         {"en": "Attack   SHIFT+SPC  Whirlwind*",
                            "de": "Angriff   SHIFT+LZT  Wirbelwind*"},
    "ctrl.fireball":       {"en": "Fireball (25 mana → mouse)",
                            "de": "Feuerball (25 Mana → Maus)"},
    "ctrl.ice_nova":       {"en": "Ice Nova* (20 mana, AoE slow)",
                            "de": "Eisnova* (20 Mana, Flächenverlang.)"},
    "ctrl.chain_light":    {"en": "Chain Lightning* (35 mana)",
                            "de": "Kettenblitz* (35 Mana)"},
    "ctrl.blink":          {"en": "Blink* (15 mana → cursor)",
                            "de": "Blinzeln* (15 Mana → Zeiger)"},
    "ctrl.battle_cry":     {"en": "Battle Cry* (20 mana, +dmg)",
                            "de": "Schlachtruf* (20 Mana, +Schaden)"},
    "ctrl.descend":        {"en": "Descend Stairs  /  Enter Dungeon (town)",
                            "de": "Treppe hinab / Dungeon betreten (Stadt)"},
    "ctrl.return_town":    {"en": "Return to Town  (saves game)",
                            "de": "Zur Stadt  (speichert Spiel)"},
    "ctrl.shop":           {"en": "Open Shop",       "de": "Laden öffnen"},
    "ctrl.inventory":      {"en": "Inventory",       "de": "Inventar"},
    "ctrl.char":           {"en": "Character Screen","de": "Charakterschirm"},
    "ctrl.skills":         {"en": "Skill Tree",      "de": "Fähigkeitsbaum"},
    "ctrl.quests":         {"en": "Quest Journal",   "de": "Questbuch"},
    "ctrl.potion":         {"en": "Use Potion",      "de": "Trank benutzen"},
    "ctrl.minimap":        {"en": "Toggle Minimap",  "de": "Minikarte"},

    # ── HUD ───────────────────────────────────────────────────────────────────
    "hud.mp":              {"en": "MP",     "de": "MP"},
    "hud.ready":           {"en": "READY",  "de": "BEREIT"},
    "hud.atk_lbl":         {"en": "ATK",    "de": "ANG"},
    "hud.floor_prefix":    {"en": "B",      "de": "E"},
    "hud.level_up":        {"en": "LEVEL UP!  NOW LEVEL {n}",
                            "de": "AUFGESTIEGEN!  JETZT LEVEL {n}"},
    "hud.stat_pts":        {"en": "★ {n} STAT POINT{s}  [C]",
                            "de": "★ {n} STATPUNKT{e}  [C]"},
    "hud.skill_pts":       {"en": "✦ {n} SKILL POINT{s}  [K]",
                            "de": "✦ {n} FÄHIGKEITSPUNKT{e}  [K]"},
    "hud.battle_cry":      {"en": "⚔ BATTLE CRY!",  "de": "⚔ SCHLACHTRUF!"},
    "hud.status.poison":   {"en": "PSN",  "de": "GIF"},
    "hud.status.burn":     {"en": "BRN",  "de": "BRN"},
    "hud.status.slow":     {"en": "SLW",  "de": "LGS"},
    "hud.status.freeze":   {"en": "FRZ",  "de": "GFR"},
    # Spell names shown in HUD spell bar
    "spell.fireball":      {"en": "Fireball",  "de": "Feuerball"},
    "spell.ice_nova":      {"en": "Ice Nova",  "de": "Eisnova"},
    "spell.chain_ltng":    {"en": "ChainLtng", "de": "KettenBl."},
    "spell.blink":         {"en": "Blink",     "de": "Blinzeln"},
    "spell.battle_cry":    {"en": "BattleCry", "de": "Schlachtruf"},

    # ── Inventory ─────────────────────────────────────────────────────────────
    "inv.title":           {"en": "INVENTORY",
                            "de": "INVENTAR"},
    "inv.hint":            {"en": "I/TAB close   click to equip/unequip   Q use potion",
                            "de": "I/TAB schließen   klicken zum An-/Ablegen   Q Trank"},
    "inv.backpack":        {"en": "BACKPACK",     "de": "RUCKSACK"},
    "inv.empty_slot":      {"en": "--- empty ---","de": "--- leer ---"},
    "inv.potions":         {"en": "Potions: {n}  (Q to use)",
                            "de": "Tränke: {n}  (Q benutzen)"},
    "inv.full_hp":         {"en": "Already at full HP",
                            "de": "LP bereits voll"},
    "inv.unequipped":      {"en": "Unequipped: {name}",
                            "de": "Abgelegt: {name}"},
    "inv.equipped":        {"en": "Equipped: {name}",
                            "de": "Angelegt: {name}"},
    "inv.used_potion":     {"en": "Used potion  +{n} HP",
                            "de": "Trank benutzt  +{n} LP"},
    "inv.vs_equipped":     {"en": "vs. equipped:",
                            "de": "vs. ausgerüstet:"},

    # Slot labels
    "slot.weapon":  {"en": "WEAPON",  "de": "WAFFE"},
    "slot.shield":  {"en": "SHIELD",  "de": "SCHILD"},
    "slot.helm":    {"en": "HELM",    "de": "HELM"},
    "slot.chest":   {"en": "CHEST",   "de": "PANZER"},
    "slot.gloves":  {"en": "GLOVES",  "de": "HANDSCH."},
    "slot.boots":   {"en": "BOOTS",   "de": "STIEFEL"},
    "slot.belt":    {"en": "BELT",    "de": "GÜRTEL"},
    "slot.ring":    {"en": "RING 1",  "de": "RING 1"},
    "slot.ring2":   {"en": "RING 2",  "de": "RING 2"},
    "slot.amulet":  {"en": "AMULET",  "de": "AMULETT"},

    # ── Shop ──────────────────────────────────────────────────────────────────
    "shop.for_sale":    {"en": "FOR SALE",   "de": "ZU KAUFEN"},
    "shop.sell_items":  {"en": "SELL ITEMS", "de": "VERKAUFEN"},
    "shop.hint":        {"en": "Left-click: Buy   Right-click: Sell   F / ESC: Close",
                         "de": "Links: Kaufen   Rechts: Verkaufen   F / ESC: Schließen"},
    "shop.gold":        {"en": "Gold: {n}",  "de": "Gold: {n}"},
    "shop.bought":      {"en": "Bought: {name}",      "de": "Gekauft: {name}"},
    "shop.need_gold":   {"en": "Need {n} more gold!", "de": "Benötige {n} mehr Gold!"},
    "shop.sold":        {"en": "Sold {name}  +{n} g", "de": "Verkauft: {name}  +{n} G"},
    "shop.health_pot":  {"en": "Health Potion  +{n} HP",
                         "de": "Heiltrank  +{n} LP"},

    # ── Character Screen ──────────────────────────────────────────────────────
    "char.title":       {"en": "CHARACTER",     "de": "CHARAKTER"},
    "char.hero":        {"en": "Level {n}  Hero","de": "Level {n}  Held"},
    "char.max":         {"en": "Level {n}  (MAX)","de": "Level {n}  (MAX)"},
    "char.xp":          {"en": "XP  {cur} / {nxt}","de": "EP  {cur} / {nxt}"},
    "char.xp_max":      {"en": "XP  MAX LEVEL",  "de": "EP  MAXIMALSTUFE"},
    "char.stat_pts":    {"en": "  ★  {n} Stat Points Available  ★  ",
                         "de": "  ★  {n} Statpunkte verfügbar  ★  "},
    "char.hint":        {"en": "Click  +  to spend stat point    C / ESC  to close",
                         "de": "Klicke  +  für Statpunkt    C / ESC  schließen"},
    "char.no_pts":      {"en": "No stat points available!",
                         "de": "Keine Statpunkte verfügbar!"},
    # Stat names
    "stat.str.short":   {"en": "STR",          "de": "STÄ"},
    "stat.str.long":    {"en": "Strength",      "de": "Stärke"},
    "stat.str.desc":    {"en": "Each point: +2 Attack",
                         "de": "Pro Punkt: +2 Angriff"},
    "stat.dex.short":   {"en": "DEX",           "de": "GES"},
    "stat.dex.long":    {"en": "Dexterity",     "de": "Geschickl."},
    "stat.dex.desc":    {"en": "Each point: +1 Defense  +0.5% Crit",
                         "de": "Pro Punkt: +1 Abwehr  +0,5% Krit"},
    "stat.vit.short":   {"en": "VIT",           "de": "VIT"},
    "stat.vit.long":    {"en": "Vitality",      "de": "Vitalität"},
    "stat.vit.desc":    {"en": "Each point: +10 Max Life",
                         "de": "Pro Punkt: +10 max. LP"},
    "stat.ene.short":   {"en": "ENE",           "de": "ENE"},
    "stat.ene.long":    {"en": "Energy",        "de": "Energie"},
    "stat.ene.desc":    {"en": "Each point: +5 Max Mana",
                         "de": "Pro Punkt: +5 max. Mana"},
    # Derived stat labels
    "derived.attack":   {"en": "Attack",      "de": "Angriff"},
    "derived.defense":  {"en": "Defense",     "de": "Abwehr"},
    "derived.max_life": {"en": "Max Life",    "de": "Max. LP"},
    "derived.max_mana": {"en": "Max Mana",    "de": "Max. Mana"},
    "derived.crit":     {"en": "Crit Chance", "de": "Krit.-Chance"},
    "derived.lifesteal":{"en": "Life Steal",  "de": "Lebensentzug"},
    "derived.move_spd": {"en": "Move Speed",  "de": "Bewegung"},
    "derived.gold_find":{"en": "Gold Find",   "de": "Goldsuche"},

    # ── Skill Screen ──────────────────────────────────────────────────────────
    "skill.title_pts":   {"en": "SKILL TREE  [ K ]   —   {n} SKILL POINT{s} AVAILABLE",
                          "de": "FÄHIGKEITSBAUM  [ K ]   —   {n} FÄHIGKEITSPUNKT{e} VERFÜGBAR"},
    "skill.tree.combat": {"en": "── COMBAT ──",  "de": "── KAMPF ──"},
    "skill.tree.magic":  {"en": "── MAGIC ──",   "de": "── MAGIE ──"},
    "skill.tree.rogue":  {"en": "── ROGUE ──",   "de": "── SCHURKE ──"},
    "skill.click_learn": {"en": "Click to learn","de": "Klicken zum Lernen"},
    "skill.mastered":    {"en": "MASTERED",      "de": "GEMEISTERT"},
    "skill.req":         {"en": "Req: {name}",   "de": "Ben.: {name}"},
    "skill.hint":        {"en": "Click a skill to spend a point    K / ESC  to close",
                          "de": "Fähigkeit klicken    K / ESC  schließen"},
    # Skill names & descriptions (keyed by skill id)
    "skill.power_strike.name":     {"en": "Power Strike",     "de": "Mächtiger Schlag"},
    "skill.power_strike.desc":     {"en": "+8% melee damage per level",
                                    "de": "+8% Nahkampfschaden pro Stufe"},
    "skill.toughness.name":        {"en": "Toughness",        "de": "Zähigkeit"},
    "skill.toughness.desc":        {"en": "+6% max HP per level",
                                    "de": "+6% max. LP pro Stufe"},
    "skill.battle_cry.name":       {"en": "Battle Cry",       "de": "Schlachtruf"},
    "skill.battle_cry.desc":       {"en": "B — +25% dmg for 5 s (20 mana)",
                                    "de": "B — +25% Schaden 5 Sek. (20 Mana)"},
    "skill.whirlwind.name":        {"en": "Whirlwind",        "de": "Wirbelwind"},
    "skill.whirlwind.desc":        {"en": "SHIFT+SPC — hits all nearby (25 mana)",
                                    "de": "SHIFT+LZT — trifft alle (25 Mana)"},
    "skill.fireball_mastery.name": {"en": "Fireball Mastery", "de": "Feuerball-Meisterschaft"},
    "skill.fireball_mastery.desc": {"en": "+15% fireball dmg, -2 mana per level",
                                    "de": "+15% FB-Schaden, -2 Mana/Stufe"},
    "skill.arcane_mind.name":      {"en": "Arcane Mind",      "de": "Arkangeist"},
    "skill.arcane_mind.desc":      {"en": "+10% max mana per level",
                                    "de": "+10% max. Mana pro Stufe"},
    "skill.ice_nova.name":         {"en": "Ice Nova",         "de": "Eisnova"},
    "skill.ice_nova.desc":         {"en": "Unlocks Ice Nova spell (X)",
                                    "de": "Schaltet Eisnova frei (X)"},
    "skill.chain_lightning.name":  {"en": "Chain Lightning",  "de": "Kettenblitz"},
    "skill.chain_lightning.desc":  {"en": "Unlocks Chain Lightning (R)",
                                    "de": "Schaltet Kettenblitz frei (R)"},
    "skill.crit_mastery.name":     {"en": "Critical Mastery", "de": "Krit.-Meisterschaft"},
    "skill.crit_mastery.desc":     {"en": "+5% crit chance per level",
                                    "de": "+5% Krit.-Chance pro Stufe"},
    "skill.evasion.name":          {"en": "Evasion",          "de": "Ausweichen"},
    "skill.evasion.desc":          {"en": "+4% dodge chance per level",
                                    "de": "+4% Ausweichwahrsch. pro Stufe"},
    "skill.poison_blade.name":     {"en": "Poison Blade",     "de": "Giftklinge"},
    "skill.poison_blade.desc":     {"en": "Melee hits apply Poison (25/50/75%)",
                                    "de": "Nahkampf Gift (25/50/75%)"},
    "skill.shadow_step.name":      {"en": "Shadow Step",      "de": "Schattensprung"},
    "skill.shadow_step.desc":      {"en": "Unlocks Blink (V), -5 mana/level",
                                    "de": "Schaltet Blinzeln frei (V), -5 Mana/Stufe"},

    # ── Quest Log ─────────────────────────────────────────────────────────────
    "quest.title":       {"en": "QUEST JOURNAL  [ J ]",    "de": "QUESTBUCH  [ J ]"},
    "quest.active":      {"en": "─── ACTIVE QUESTS ───",   "de": "─── AKTIVE QUESTS ───"},
    "quest.no_active":   {"en": "No active quests.",        "de": "Keine aktiven Quests."},
    "quest.completed":   {"en": "─── COMPLETED ({n}) ───",
                          "de": "─── ABGESCHLOSSEN ({n}) ───"},
    "quest.hint":        {"en": "J / ESC  to close",        "de": "J / ESC  schließen"},
    "quest.reward_xp":   {"en": "Reward: {xp} XP",          "de": "Belohnung: {xp} EP"},
    "quest.reward_gold": {"en": "  +{gold} Gold",           "de": "  +{gold} Gold"},
    "quest.complete":    {"en": "Quest Complete",            "de": "Quest abgeschlossen"},
    # Quest names & descriptions
    "quest.goblin_hunter.name":   {"en": "Goblin Hunter",      "de": "Goblin-Jäger"},
    "quest.goblin_hunter.desc":   {"en": "Kill 5 Goblins.",    "de": "Töte 5 Goblins."},
    "quest.bone_crusher.name":    {"en": "Bone Crusher",       "de": "Knochenbrecherer"},
    "quest.bone_crusher.desc":    {"en": "Kill 4 Skeletons.",  "de": "Töte 4 Skelette."},
    "quest.orc_slayer.name":      {"en": "Orc Slayer",         "de": "Ork-Töter"},
    "quest.orc_slayer.desc":      {"en": "Kill 3 Orcs.",       "de": "Töte 3 Orks."},
    "quest.demon_hunter.name":    {"en": "Demon Hunter",       "de": "Dämonenjäger"},
    "quest.demon_hunter.desc":    {"en": "Kill 2 Demons.",     "de": "Töte 2 Dämonen."},
    "quest.elite_destroyer.name": {"en": "Elite Destroyer",    "de": "Elitevernichter"},
    "quest.elite_destroyer.desc": {"en": "Kill 2 Elite enemies.",
                                   "de": "Töte 2 Elite-Gegner."},
    "quest.gold_rush.name":       {"en": "Gold Rush",          "de": "Goldrausch"},
    "quest.gold_rush.desc":       {"en": "Collect {n} gold on this run.",
                                   "de": "Sammle {n} Gold in diesem Durchlauf."},
    "quest.deeper_down.name":     {"en": "Deeper Down",        "de": "Tiefer hinab"},
    "quest.deeper_down.desc":     {"en": "Descend to floor {n}.",
                                   "de": "Steige auf Etage {n} ab."},

    # ── Town ──────────────────────────────────────────────────────────────────
    "town.dungeon_sign":  {"en": "DUNGEON",           "de": "DUNGEON"},
    "town.enter_dungeon": {"en": "E  —  Enter Dungeon","de": "E  —  Dungeon betreten"},
    "town.your_home":     {"en": "YOUR HOME",          "de": "DEIN ZUHAUSE"},
    "town.enter_house":   {"en": "F  —  Enter Your Home", "de": "F  —  Dein Haus betreten"},
    "town.shop_hint":     {"en": "F — Shop",           "de": "F — Laden"},
    "town.rested":        {"en": "Rested at the inn — HP and MP fully restored",
                           "de": "Gerastet — LP und Mana vollständig aufgefüllt"},
    "town.footer":        {"en": "F: Shop   I: Inventory   C: Character   K: Skills"
                                 "   E: Enter Dungeon (floor {n})   ESC: Menu",
                           "de": "F: Laden   I: Inventar   C: Charakter   K: Fähigkeiten"
                                 "   E: Dungeon betreten (Etage {n})   ESC: Menü"},
    # Merchant display names (town specialists)
    "merchant.blacksmith": {"en": "Blacksmith",       "de": "Schmied"},
    "merchant.armourer":   {"en": "Armourer",         "de": "Rüstungsschmied"},
    "merchant.jeweler":    {"en": "Jeweler",           "de": "Juwelier"},
    "merchant.alchemist":  {"en": "Alchemist",         "de": "Alchemist"},
    # Dungeon merchant
    "merchant.travelling": {"en": "TRAVELLING MERCHANT","de": "REISENDER HÄNDLER"},
    "merchant.default":    {"en": "MERCHANT",           "de": "HÄNDLER"},

    # ── Dungeon / in-game ──────────────────────────────────────────────────────
    "game.descend":        {"en": "E — descend",         "de": "E — hinabsteigen"},
    "game.descend_ng":     {"en": "E — descend (NG+!)",  "de": "E — hinabsteigen (NG+!)"},
    "game.merchant_found": {"en": "A merchant is trading on this floor  (F)",
                            "de": "Ein Händler ist auf dieser Etage  (F)"},
    "game.game_over":      {"en": "GAME OVER",            "de": "SPIEL VORBEI"},
    "game.press_enter":    {"en": "Press ENTER to return to menu",
                            "de": "ENTER drücken zum Menü"},
    "game.quest_reward":   {"en": "Quest: {name}  +{xp} XP",
                            "de": "Quest: {name}  +{xp} EP"},
    "game.used_potion":    {"en": "Used potion  (Remaining: {n})",
                            "de": "Trank benutzt  (Verbleibend: {n})"},
    "game.boss_incoming":  {"en": "⚠  BOSS INCOMING  ⚠",
                            "de": "⚠  BOSS NAHT  ⚠"},
    "game.boss_defeated":  {"en": "{name} defeated!",
                            "de": "{name} besiegt!"},

    # ── Item modifier descriptions ─────────────────────────────────────────────
    "mod.atk":             {"en": "+{v} to Attack",         "de": "+{v} auf Angriff"},
    "mod.atk_pct":         {"en": "+{v}% Enhanced Damage",  "de": "+{v}% Verstärkter Schaden"},
    "mod.def":             {"en": "+{v} to Defense",        "de": "+{v} auf Abwehr"},
    "mod.max_hp":          {"en": "+{v} to Life",           "de": "+{v} auf Leben"},
    "mod.hp_regen":        {"en": "+{v} Life Regen / sec",  "de": "+{v} LP-Regen / Sek."},
    "mod.life_steal":      {"en": "{v}% Life Stolen per Hit","de": "{v}% Leben gestohlen/Treffer"},
    "mod.crit":            {"en": "+{v}% Critical Strike",  "de": "+{v}% Kritischer Treffer"},
    "mod.thorns":          {"en": "Attacker Takes {v} Dmg", "de": "Angreifer erleidet {v} Schaden"},
    "mod.speed":           {"en": "+{v}% Faster Run/Walk",  "de": "+{v}% Schnelleres Laufen"},
    "mod.gold_find":       {"en": "+{v}% Better Chance Gold","de": "+{v}% Bessere Goldchance"},
    "mod.max_mana":        {"en": "+{v} to Mana",           "de": "+{v} auf Mana"},
    "mod.atk_spd":         {"en": "+{v}% Increased Atk Spd","de": "+{v}% Mehr Angriffsgeschw."},
}
