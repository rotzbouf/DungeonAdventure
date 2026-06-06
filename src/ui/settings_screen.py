"""
Settings overlay — three tabs: Display, Controls, Multiplayer.

Usage:
    screen = SettingsScreen()
    screen.open(apply_display_fn=game._apply_display)
    screen.handle_event(event)
    screen.draw(surface)
"""
from __future__ import annotations

import pygame

from src.settings import SCREEN_WIDTH, SCREEN_HEIGHT, HUD_HEIGHT
from src.settings_manager import (
    game_settings, ACTION_LABELS, WINDOW_PRESETS, _DEFAULTS,
)

# ── Palette ───────────────────────────────────────────────────────────────────
_BG        = (8,   6,  14)
_PANEL     = (14, 12,  24)
_BORDER    = (100, 70, 180)
_BORDER_LO = (50,  35,  90)
_HDR       = (180, 140, 255)
_SEL       = (40,  25,  70)
_SEL_HI    = (70,  45, 120)
_DIM       = (90,  80, 120)
_GREEN     = (60,  200,  80)
_RED       = (200,  50,  50)
_GOLD      = (220, 175,   0)
_WHITE     = (220, 220, 220)
_WARN      = (240, 140,  20)
_TAB_ACT   = (70,  45, 120)
_TAB_IN    = (25,  18,  44)

_TABS = ["DISPLAY", "CONTROLS", "MULTIPLAYER"]

# Ordered action list for the Controls tab
_CONTROL_ACTIONS = list(ACTION_LABELS.keys())


class _TextField:
    """Simple single-line text input widget."""
    W = 300;  H = 28

    def __init__(self, value: str = "", max_len: int = 64, digits_only: bool = False):
        self.value      = value
        self.max_len    = max_len
        self.digits_only = digits_only
        self.focused    = False
        self._rect      = pygame.Rect(0, 0, self.W, self.H)
        self._font      = pygame.font.SysFont("monospace", 24)
        self._cursor_t  = 0.0

    def set_rect(self, x: int, y: int):
        self._rect.topleft = (x, y)

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.focused:
            return False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                self.value = self.value[:-1]
                return True
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_ESCAPE):
                self.focused = False
                return True
            ch = event.unicode
            if ch and len(self.value) < self.max_len:
                if self.digits_only and not ch.isdigit():
                    return True
                self.value += ch
                return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if not self._rect.collidepoint(event.pos):
                self.focused = False
        return False

    def update(self, dt: float):
        self._cursor_t += dt

    def draw(self, surface: pygame.Surface):
        col_border = _BORDER if self.focused else _BORDER_LO
        pygame.draw.rect(surface, _PANEL,    self._rect)
        pygame.draw.rect(surface, col_border, self._rect, 1)
        display = self.value
        if self.focused and int(self._cursor_t * 2) % 2 == 0:
            display += "|"
        txt = self._font.render(display, True, _WHITE)
        surface.blit(txt, (self._rect.left + 6, self._rect.centery - txt.get_height() // 2))


class SettingsScreen:
    W = 980
    H = 680

    def __init__(self):
        self._fl = pygame.font.SysFont("monospace", 28, bold=True)
        self._fm = pygame.font.SysFont("monospace", 25, bold=True)
        self._fs = pygame.font.SysFont("monospace", 25)

        self._tab          = 0        # 0=Display, 1=Controls, 2=Multiplayer
        self._listening    = ""       # action name being rebound, or ""
        self._apply_fn     = None     # callable: apply display settings
        self._connect_fn   = None     # callable(host, port, name) → NetworkClient
        self._msg          = ""
        self._msg_t        = 0.0
        self._msg_ok       = True

        # Multiplayer text fields
        self._tf_name = _TextField(game_settings.player_name, max_len=24)
        self._tf_host = _TextField(game_settings.server_host, max_len=64)
        self._tf_port = _TextField(str(game_settings.server_port), max_len=5, digits_only=True)

        # Multiplayer connect state
        self._net_client_ref = None   # pending NetworkClient while connecting
        self._connect_status = ""     # "" | "connecting" | "connected" | "failed: ..."

    # ── Public API ────────────────────────────────────────────────────────────

    def open(self, apply_display_fn=None, connect_fn=None):
        self._tab          = 0
        self._listening    = ""
        self._msg          = ""
        self._msg_t        = 0.0
        self._apply_fn     = apply_display_fn
        self._connect_fn   = connect_fn
        self._net_client_ref = None
        self._connect_status = ""
        # Re-sync text fields in case settings changed externally
        self._tf_name.value = game_settings.player_name
        self._tf_host.value = game_settings.server_host
        self._tf_port.value = str(game_settings.server_port)

    @property
    def is_listening(self) -> bool:
        return bool(self._listening)

    def update(self, dt: float):
        if self._msg_t > 0:
            self._msg_t = max(0.0, self._msg_t - dt)
        self._tf_name.update(dt)
        self._tf_host.update(dt)
        self._tf_port.update(dt)
        # Poll pending connection
        if self._net_client_ref is not None:
            nc = self._net_client_ref
            if nc.connected:
                self._connect_status = "connected"
                self._net_client_ref = None
            elif nc.error:
                self._connect_status = f"failed: {nc.error}"
                self._net_client_ref = None

    def handle_event(self, event: pygame.event.Event) -> bool:
        ox = SCREEN_WIDTH  // 2 - self.W // 2
        oy = (SCREEN_HEIGHT - HUD_HEIGHT) // 2 - self.H // 2

        # ── Keybinding listen mode ────────────────────────────────────────────
        if self._listening and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._listening = ""
            else:
                game_settings.set_key(self._listening, event.key)
                self._notify(f"Bound {ACTION_LABELS.get(self._listening, self._listening)}"
                             f" → {pygame.key.name(event.key).upper()}", ok=True)
                self._listening = ""
            return True

        # ── Text fields (multiplayer tab) ─────────────────────────────────────
        if self._tab == 2:
            for tf in (self._tf_name, self._tf_host, self._tf_port):
                if tf.focused and tf.handle_event(event):
                    self._save_multiplayer()
                    return True

        # ── Mouse clicks ──────────────────────────────────────────────────────
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            lx = event.pos[0] - ox
            ly = event.pos[1] - oy

            # Tab bar
            if 0 <= ly < 88:
                tw = self.W // len(_TABS)
                t  = lx // tw
                if 0 <= t < len(_TABS):
                    self._tab = t
                    self._listening = ""
                return True

            if self._tab == 0:
                self._handle_display_click(lx, ly)
            elif self._tab == 1:
                self._handle_controls_click(lx, ly)
            elif self._tab == 2:
                # Connect button (panel-local coords)
                conn_r = self._connect_btn_rect()
                if conn_r.collidepoint(lx, ly) and self._net_client_ref is None:
                    self._do_connect()
                    return True
                # Route to text fields (absolute coords)
                lpos = (event.pos[0], event.pos[1])
                for tf in (self._tf_name, self._tf_host, self._tf_port):
                    if tf._rect.collidepoint(lpos):
                        tf.focused = True
                    else:
                        tf.focused = False
            return True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Unfocus text fields if clicking outside
            for tf in (self._tf_name, self._tf_host, self._tf_port):
                if not tf._rect.collidepoint(event.pos):
                    tf.focused = False

        return False

    def _handle_display_click(self, lx: int, ly: int):
        # Fullscreen toggle at ~150
        if 110 <= ly <= 150:
            game_settings.fullscreen = not game_settings.fullscreen
            if self._apply_fn:
                self._apply_fn()
            self._notify("Fullscreen " + ("ON" if game_settings.fullscreen else "OFF"), ok=True)

        # Window preset buttons at ~240
        if not game_settings.fullscreen and 220 <= ly <= 260:
            pad = 20
            btn_w = (self.W - pad * 2 - 180) // len(WINDOW_PRESETS)
            for i in range(len(WINDOW_PRESETS)):
                bx = pad + 180 + i * btn_w
                if bx <= lx <= bx + btn_w - 10:
                    game_settings.window_preset = i
                    if self._apply_fn:
                        self._apply_fn()
                    self._notify(f"Window: {game_settings.window_size_label}", ok=True)
                    return

    def _handle_controls_click(self, lx: int, ly: int):
        pad = 20
        y0  = 110
        row_h = 32
        half = (self.W - pad * 2) // 2

        # Reset button
        reset_r = self._reset_btn_rect()
        if reset_r.collidepoint(lx + (SCREEN_WIDTH // 2 - self.W // 2),
                                 ly + (SCREEN_HEIGHT // 2 - self.H // 2)):
            game_settings.reset_keybindings()
            self._notify("Keybindings reset to defaults.", ok=True)
            return

        # Two-column action rows
        n = len(_CONTROL_ACTIONS)
        col_count = (n + 1) // 2
        for idx, action in enumerate(_CONTROL_ACTIONS):
            col  = idx // col_count
            row  = idx %  col_count
            row_x = pad + col * half
            row_y = y0 + row * row_h
            if (row_x <= lx <= row_x + half - 8
                    and row_y <= ly <= row_y + row_h - 2):
                self._listening = action
                return

    def _reset_btn_rect(self) -> pygame.Rect:
        bw, bh = 240, 30
        ox = SCREEN_WIDTH  // 2 - self.W // 2
        oy = (SCREEN_HEIGHT - HUD_HEIGHT) // 2 - self.H // 2
        return pygame.Rect(
            ox + self.W // 2 - bw // 2,
            oy + self.H - 52,
            bw, bh
        )

    def _connect_btn_rect(self) -> pygame.Rect:
        bw, bh = 220, 38
        return pygame.Rect(self.W // 2 - bw // 2, 276, bw, bh)

    def _do_connect(self):
        self._save_multiplayer()
        if self._connect_fn is None:
            self._notify("Connect callback not configured.", ok=False)
            return
        self._net_client_ref = self._connect_fn(
            game_settings.server_host,
            game_settings.server_port,
            game_settings.player_name,
        )
        self._connect_status = "connecting"

    def _save_multiplayer(self):
        game_settings.player_name = self._tf_name.value or "Adventurer"
        game_settings.server_host = self._tf_host.value or "localhost"
        try:
            game_settings.server_port = max(1, min(65535, int(self._tf_port.value or "5555")))
        except ValueError:
            pass
        game_settings.save()

    def _notify(self, msg: str, ok: bool = True):
        self._msg   = msg
        self._msg_ok = ok
        self._msg_t  = 3.0

    # ── Draw ──────────────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface):
        ox = SCREEN_WIDTH  // 2 - self.W // 2
        oy = (SCREEN_HEIGHT - HUD_HEIGHT) // 2 - self.H // 2

        # Dim backdrop
        ov = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT - HUD_HEIGHT), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 200))
        surface.blit(ov, (0, 0))

        panel = pygame.Surface((self.W, self.H))
        panel.fill(_BG)
        pygame.draw.rect(panel, _BORDER, (0, 0, self.W, self.H), 2)

        self._draw_tabs(panel)

        if self._tab == 0:
            self._draw_display(panel)
        elif self._tab == 1:
            self._draw_controls(panel)
        elif self._tab == 2:
            self._draw_multiplayer(panel, ox, oy)

        self._draw_footer(panel)
        surface.blit(panel, (ox, oy))

        # Text fields are drawn on the main surface (absolute coords)
        if self._tab == 2:
            self._tf_name.draw(surface)
            self._tf_host.draw(surface)
            self._tf_port.draw(surface)

    def _draw_tabs(self, surf: pygame.Surface):
        pygame.draw.rect(surf, _PANEL, (0, 0, self.W, 88))
        pygame.draw.line(surf, _BORDER, (0, 88), (self.W, 88), 1)
        title = self._fl.render("SETTINGS", True, _HDR)
        surf.blit(title, title.get_rect(centerx=self.W // 2, centery=22))
        tw = self.W // len(_TABS)
        for i, label in enumerate(_TABS):
            tx   = i * tw
            rect = pygame.Rect(tx, 48, tw - 2, 32)
            col  = _TAB_ACT if self._tab == i else _TAB_IN
            pygame.draw.rect(surf, col, rect)
            pygame.draw.rect(surf, _BORDER_LO, rect, 1)
            ts = self._fm.render(label, True, _HDR if self._tab == i else _DIM)
            surf.blit(ts, ts.get_rect(center=rect.center))

    # ── Display tab ───────────────────────────────────────────────────────────

    def _draw_display(self, surf: pygame.Surface):
        pad = 20
        y   = 108

        # ── Fullscreen row ────────────────────────────────────────────────────
        lbl = self._fm.render("Fullscreen", True, _WHITE)
        surf.blit(lbl, (pad, y + 4))
        on_off = game_settings.fullscreen
        toggle_col = _GREEN if on_off else _RED
        btn_txt = "  ON  " if on_off else "  OFF "
        btn_surf = self._fm.render(btn_txt, True, (0, 0, 0))
        btn_r = pygame.Rect(pad + 200, y, 80, 30)
        pygame.draw.rect(surf, toggle_col, btn_r, border_radius=4)
        surf.blit(btn_surf, btn_surf.get_rect(center=btn_r.center))
        pygame.draw.rect(surf, _WHITE, btn_r, 1, border_radius=4)
        hint = self._fs.render("click to toggle", True, _DIM)
        surf.blit(hint, (pad + 290, y + 8))
        y += 50

        # ── Window size row ───────────────────────────────────────────────────
        lbl2 = self._fm.render("Window size", True, _WHITE if not on_off else _DIM)
        surf.blit(lbl2, (pad, y + 4))
        btn_w = 130
        for i, (ww, wh) in enumerate(WINDOW_PRESETS):
            bx  = pad + 200 + i * (btn_w + 8)
            sel = (i == game_settings.window_preset) and not on_off
            bc  = _SEL_HI if sel else _SEL
            tc  = _HDR if sel else (_DIM if on_off else _WHITE)
            br  = pygame.Rect(bx, y, btn_w, 30)
            pygame.draw.rect(surf, bc, br, border_radius=4)
            pygame.draw.rect(surf, _BORDER_LO if not sel else _BORDER, br, 1, border_radius=4)
            ts = self._fs.render(f"{ww}×{wh}", True, tc)
            surf.blit(ts, ts.get_rect(center=br.center))
        if on_off:
            note = self._fs.render("(switch to windowed first)", True, _DIM)
            surf.blit(note, (pad + 200, y + 32))
        y += 60

        # ── Info box ──────────────────────────────────────────────────────────
        pygame.draw.line(surf, _BORDER_LO, (pad, y), (self.W - pad, y), 1)
        y += 14
        for line in [
            "The game renders at 1920×1080 internally.",
            "Windowed mode scales the render to the chosen size; mouse coords are remapped.",
            "Changes apply immediately.",
        ]:
            s = self._fs.render(line, True, _DIM)
            surf.blit(s, (pad, y))
            y += 18

    # ── Controls tab ─────────────────────────────────────────────────────────

    def _draw_controls(self, surf: pygame.Surface):
        pad   = 20
        y0    = 108
        row_h = 32
        n     = len(_CONTROL_ACTIONS)
        col_count = (n + 1) // 2
        half  = (self.W - pad * 2) // 2

        if self._listening:
            # Listening banner
            ban_r = pygame.Rect(pad, y0 - 30, self.W - pad * 2, 24)
            pygame.draw.rect(surf, _WARN, ban_r, border_radius=3)
            lbl = ACTION_LABELS.get(self._listening, self._listening)
            msg = f'  PRESS ANY KEY to bind  "{lbl}"  —  ESC to cancel'
            ms  = self._fs.render(msg, True, (0, 0, 0))
            surf.blit(ms, ms.get_rect(center=ban_r.center))

        for idx, action in enumerate(_CONTROL_ACTIONS):
            col  = idx // col_count
            row  = idx %  col_count
            rx   = pad + col * half
            ry   = y0 + row * row_h
            if ry + row_h > self.H - 60:
                break

            listening_this = (self._listening == action)
            bg = _SEL_HI if listening_this else (_SEL if idx % 2 == 0 else _PANEL)
            pygame.draw.rect(surf, bg, (rx, ry, half - 8, row_h - 2))

            lbl = ACTION_LABELS.get(action, action)
            ls  = self._fs.render(lbl, True, _WARN if listening_this else _WHITE)
            surf.blit(ls, (rx + 6, ry + 8))

            if listening_this:
                ks = self._fs.render("PRESS A KEY...", True, _GOLD)
            else:
                code    = game_settings.key(action)
                key_str = pygame.key.name(code).upper()
                is_def  = (code == _DEFAULTS.get(action, code))
                ks      = self._fs.render(key_str, True, _DIM if is_def else _GREEN)
            surf.blit(ks, ks.get_rect(right=rx + half - 14, centery=ry + row_h // 2))

        # Reset defaults button
        bw, bh = 240, 30
        reset_r = pygame.Rect(self.W // 2 - bw // 2, self.H - 52, bw, bh)
        pygame.draw.rect(surf, _SEL, reset_r, border_radius=4)
        pygame.draw.rect(surf, _BORDER_LO, reset_r, 1, border_radius=4)
        rs = self._fm.render("RESET TO DEFAULTS", True, _DIM)
        surf.blit(rs, rs.get_rect(center=reset_r.center))

    # ── Multiplayer tab ───────────────────────────────────────────────────────

    def _draw_multiplayer(self, surf: pygame.Surface,
                           ox: int, oy: int):
        pad = 20
        y   = 108

        rows = [
            ("Player Name",  self._tf_name),
            ("Server Host",  self._tf_host),
            ("Server Port",  self._tf_port),
        ]
        lbl_w = 180
        for label, tf in rows:
            lbl_s = self._fm.render(label, True, _WHITE)
            surf.blit(lbl_s, (pad, y + 6))
            # Position the text field on the main surface (absolute coords)
            tf.set_rect(ox + pad + lbl_w, oy + y)
            y += 46

        # Divider
        pygame.draw.line(surf, _BORDER_LO, (pad, y + 10), (self.W - pad, y + 10), 1)
        y += 26

        # CONNECT button
        conn_r = self._connect_btn_rect()
        connecting = (self._connect_status == "connecting")
        connected  = (self._connect_status == "connected")
        failed     = self._connect_status.startswith("failed")
        if connecting:
            btn_col, txt_col = _WARN, (0, 0, 0)
            btn_label = "CONNECTING..."
        elif connected:
            btn_col, txt_col = _GREEN, (0, 0, 0)
            btn_label = "CONNECTED"
        else:
            btn_col  = _SEL_HI if not failed else _SEL
            txt_col  = _HDR if not failed else _DIM
            btn_label = "CONNECT TO SERVER"
        pygame.draw.rect(surf, btn_col, conn_r, border_radius=5)
        pygame.draw.rect(surf, _BORDER, conn_r, 1, border_radius=5)
        bs = self._fm.render(btn_label, True, txt_col)
        surf.blit(bs, bs.get_rect(center=conn_r.center))
        y = conn_r.bottom + 8

        # Status text
        if self._connect_status:
            if connected:
                st_col, st_txt = _GREEN, "Connected!"
            elif connecting:
                st_col, st_txt = _WARN, "Connecting to server..."
            else:
                st_col = _RED
                st_txt = self._connect_status[len("failed: "):][:80]
            ss = self._fs.render(st_txt, True, st_col)
            surf.blit(ss, ss.get_rect(centerx=self.W // 2, y=y))
            y += ss.get_height() + 10

        # Divider before hint
        y += 6
        pygame.draw.line(surf, _BORDER_LO, (pad, y), (self.W - pad, y), 1)
        y += 14

        # Command-line hint
        for line in [
            "To start a server:",
            "  python server.py --port 5555",
            "",
            "CLI connect (alternative):",
            f'  python main.py --connect {game_settings.server_host}:{game_settings.server_port}',
            f'    --name "{game_settings.player_name}"',
        ]:
            col = _DIM if not line.startswith("  python") else _GREEN
            s = self._fs.render(line, True, col if line else _DIM)
            surf.blit(s, (pad, y))
            y += 18

    # ── Footer ────────────────────────────────────────────────────────────────

    def _draw_footer(self, surf: pygame.Surface):
        fy = self.H - 26
        pygame.draw.line(surf, _BORDER_LO, (0, fy), (self.W, fy), 1)

        if self._msg and self._msg_t > 0:
            fade = min(1.0, self._msg_t / 0.4)
            col  = tuple(int(c * fade) for c in (_GREEN if self._msg_ok else _RED))
            ms   = self._fs.render(self._msg, True, col)
            surf.blit(ms, ms.get_rect(centerx=self.W // 2, centery=fy + 12))
        else:
            hint = self._fs.render(
                "Click tab to switch  ·  ESC to close", True, _DIM)
            surf.blit(hint, hint.get_rect(centerx=self.W // 2, centery=fy + 12))
