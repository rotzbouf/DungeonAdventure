"""
Character class definitions — starting stat allocations and DCSS portrait mappings.

All stat totals sum to 32 (= BASE_STR + BASE_DEX + BASE_VIT + BASE_ENE = 10+5+10+5 + 2
bonus points allocated per class flavour).
"""

HERO_CLASSES: dict[str, dict] = {
    "warrior": {
        "label":    "Warrior",
        "label_de": "Krieger",
        "desc":     "Masters of arms and armour.  High Strength and Vitality.",
        "desc_de":  "Kampferprobte Streiter.  Hohe Stärke und Vitalität.",
        "str_pts":  14,
        "dex_pts":   4,
        "vit_pts":  12,
        "ene_pts":   2,
        # DCSS base portraits available for this class (race key → file stem)
        "portraits": {
            "human":    "human",
            "dwarf":    "dwarf",
        },
    },
    "mage": {
        "label":    "Mage",
        "label_de": "Magier",
        "desc":     "Wielders of arcane power.  High Energy and solid Vitality.",
        "desc_de":  "Meister der Arkankünste.  Hohe Energie und gute Vitalität.",
        "str_pts":   3,
        "dex_pts":   4,
        "vit_pts":   8,
        "ene_pts":  17,
        "portraits": {
            "deep_elf": "deep_elf",
            "elf":      "elf",
            "human":    "human",
        },
    },
    "rogue": {
        "label":    "Rogue",
        "label_de": "Schurke",
        "desc":     "Swift and deadly.  High Dexterity for crits and evasion.",
        "desc_de":  "Schnell und tödlich.  Hohe Geschicklichkeit für Kritische.",
        "str_pts":   7,
        "dex_pts":  15,
        "vit_pts":   7,
        "ene_pts":   3,
        "portraits": {
            "halfling": "halfling",
            "human":    "human",
            "gnome":    "gnome",
        },
    },
}

CLASS_ORDER = ["warrior", "mage", "rogue"]
