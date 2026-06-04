"""
Persistent user preferences: display mode, keybindings, multiplayer config.
Saved to ~/.dungeonadventure/settings.json.

Usage:
    from src.settings_manager import game_settings
    game_settings.key("attack")          # → pygame keycode
    game_settings.fullscreen             # → bool
    game_settings.server_host            # → str
"""
from __future__ import annotations

import json
import pathlib

import pygame

from src.settings import SCREEN_WIDTH, SCREEN_HEIGHT

SETTINGS_PATH = pathlib.Path("~/.dungeonadventure/settings.json").expanduser()

# ── Window size presets (used when fullscreen = False) ────────────────────────
WINDOW_PRESETS: list[tuple[int, int]] = [
    (1280, 720),
    (1600, 900),
    (1920, 1080),
]

# ── Default keybindings (action → pygame keycode) ─────────────────────────────
# NOTE: pygame.K_* constants are plain ints and don't require pygame.init().
_DEFAULTS: dict[str, int] = {
    "move_up":           pygame.K_w,
    "move_down":         pygame.K_s,
    "move_left":         pygame.K_a,
    "move_right":        pygame.K_d,
    "attack":            pygame.K_SPACE,
    "descend":           pygame.K_e,
    "interact":          pygame.K_f,
    "return_town":       pygame.K_t,
    "potion":            pygame.K_q,
    "inventory":         pygame.K_i,
    "character":         pygame.K_c,
    "skills":            pygame.K_k,
    "quests":            pygame.K_j,
    "spell_fireball":    pygame.K_z,
    "spell_ice_nova":    pygame.K_x,
    "spell_chain":       pygame.K_r,
    "spell_blink":       pygame.K_v,
    "spell_battle_cry":  pygame.K_b,
}

# Human-readable label for each action (used in the Controls tab)
ACTION_LABELS: dict[str, str] = {
    "move_up":          "Move Up",
    "move_down":        "Move Down",
    "move_left":        "Move Left",
    "move_right":       "Move Right",
    "attack":           "Attack / Fire",
    "descend":          "Descend Stairs",
    "interact":         "Interact / Shop",
    "return_town":      "Return to Town",
    "potion":           "Use Potion",
    "inventory":        "Inventory",
    "character":        "Character Screen",
    "skills":           "Skill Tree",
    "quests":           "Quest Log",
    "spell_fireball":   "Fireball",
    "spell_ice_nova":   "Ice Nova",
    "spell_chain":      "Chain Lightning",
    "spell_blink":      "Blink",
    "spell_battle_cry": "Battle Cry",
}


class SettingsManager:
    def __init__(self):
        self.fullscreen:     bool  = True
        self.window_preset:  int   = 0          # index into WINDOW_PRESETS
        self.server_host:    str   = "localhost"
        self.server_port:    int   = 5555
        self.player_name:    str   = "Adventurer"
        self.keybindings:    dict  = dict(_DEFAULTS)
        self.load()

    # ── Keybinding helpers ─────────────────────────────────────────────────────

    def key(self, action: str) -> int:
        """Return the pygame keycode for *action*, defaulting to the built-in."""
        return self.keybindings.get(action, _DEFAULTS.get(action, 0))

    def set_key(self, action: str, keycode: int):
        self.keybindings[action] = keycode
        self.save()

    def reset_keybindings(self):
        self.keybindings = dict(_DEFAULTS)
        self.save()

    # ── Persistence ────────────────────────────────────────────────────────────

    def save(self):
        SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "fullscreen":    self.fullscreen,
            "window_preset": self.window_preset,
            "server_host":   self.server_host,
            "server_port":   self.server_port,
            "player_name":   self.player_name,
            "keybindings":   {k: v for k, v in self.keybindings.items()},
        }
        SETTINGS_PATH.write_text(json.dumps(data, indent=2))

    def load(self):
        if not SETTINGS_PATH.exists():
            return
        try:
            data = json.loads(SETTINGS_PATH.read_text())
            self.fullscreen    = bool(data.get("fullscreen",    self.fullscreen))
            self.window_preset = int(data.get("window_preset",  self.window_preset))
            self.server_host   = str(data.get("server_host",    self.server_host))
            self.server_port   = int(data.get("server_port",    self.server_port))
            self.player_name   = str(data.get("player_name",    self.player_name))[:24]
            for action, code in data.get("keybindings", {}).items():
                if action in _DEFAULTS:
                    self.keybindings[action] = int(code)
        except Exception:
            pass   # corrupt file — keep defaults

    # ── Display application ────────────────────────────────────────────────────

    def apply_display(self) -> pygame.Surface:
        """
        Apply the current fullscreen / windowed setting.
        Returns the new display Surface (caller must update game.screen).
        """
        if self.fullscreen:
            surf = pygame.display.set_mode(
                (SCREEN_WIDTH, SCREEN_HEIGHT),
                pygame.FULLSCREEN | pygame.HWSURFACE | pygame.DOUBLEBUF,
            )
        else:
            ww, wh = WINDOW_PRESETS[
                max(0, min(self.window_preset, len(WINDOW_PRESETS) - 1))
            ]
            # pygame.SCALED keeps the internal 1920×1080 surface; the OS window
            # is resized but all coordinates remain correct.
            surf = pygame.display.set_mode(
                (ww, wh),
                pygame.SCALED | pygame.HWSURFACE | pygame.DOUBLEBUF,
            )
        self.save()
        return surf

    @property
    def window_size_label(self) -> str:
        ww, wh = WINDOW_PRESETS[
            max(0, min(self.window_preset, len(WINDOW_PRESETS) - 1))
        ]
        return f"{ww} × {wh}"


# ── Module-level singleton ─────────────────────────────────────────────────────
game_settings = SettingsManager()
