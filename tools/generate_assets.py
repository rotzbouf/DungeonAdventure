"""
Asset generator for DungeonAdventure.
Run once to produce all PNG files under assets/.

    python tools/generate_assets.py

Requires Pillow (pip install Pillow).
Falls back gracefully to procedural drawing when assets are absent.
"""
from __future__ import annotations
import math
import os
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance

ROOT   = Path(__file__).parent.parent
ASSETS = ROOT / "assets"

TILE_SZ  = 40   # must match settings.TILE_SIZE
SPRITE_W = 40   # player sprite canvas
SPRITE_H = 40


# ── Noise helpers ─────────────────────────────────────────────────────────────

def _hash(x: int, y: int, seed: int = 0) -> float:
    n = x + y * 57 + seed * 131
    n = (n << 13) ^ n
    return (1.0 - ((n * (n * n * 15731 + 789221) + 1376312589) & 0x7FFF_FFFF)
            / 1_073_741_824.0)


def _lerp(a: float, b: float, t: float) -> float:
    t = t * t * (3 - 2 * t)   # smoothstep
    return a + (b - a) * t


def _smooth(x: float, y: float, seed: int = 0) -> float:
    ix, iy = int(x), int(y)
    fx, fy = x - ix, y - iy
    v00 = _hash(ix,   iy,   seed)
    v10 = _hash(ix+1, iy,   seed)
    v01 = _hash(ix,   iy+1, seed)
    v11 = _hash(ix+1, iy+1, seed)
    return _lerp(_lerp(v00, v10, fx), _lerp(v01, v11, fx), fy)


def fractal(x: float, y: float, octaves: int = 5, seed: int = 0) -> float:
    v, amp, freq = 0.0, 0.5, 1.0
    for _ in range(octaves):
        v   += _smooth(x * freq, y * freq, seed) * amp
        amp  *= 0.5
        freq *= 2.1
    return max(0.0, min(1.0, v + 0.5))   # remap to [0,1]


def marble(x: float, y: float, seed: int = 0) -> float:
    n = fractal(x, y, 5, seed)
    return (math.sin((x * 0.4 + n * 4.0) * math.pi) + 1.0) / 2.0


# ── Colour helpers ────────────────────────────────────────────────────────────

def blend(c1: tuple, c2: tuple, t: float) -> tuple:
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(len(c1)))


def darken(c: tuple, amount: int) -> tuple:
    return tuple(max(0, v - amount) for v in c[:3]) + c[3:]


def lighten(c: tuple, amount: int) -> tuple:
    return tuple(min(255, v + amount) for v in c[:3]) + c[3:]


def with_alpha(c: tuple, a: int) -> tuple:
    return c[:3] + (a,)


# ── Tile themes ───────────────────────────────────────────────────────────────

THEMES = {
    "dungeon": {
        "floor_base":  (28,  22,  38),   "floor_hi":  (52,  44,  70),
        "floor_lo":    (18,  12,  26),   "floor_crack":(14, 8, 20),
        "wall_base":   (62,  88, 160),   "wall_hi":   (108,148,218),
        "wall_sh":     (32,  50, 112),   "mortar":    (8,   14,  66),
    },
    "crypt": {
        "floor_base":  (22,  18,  22),   "floor_hi":  (42,  38,  44),
        "floor_lo":    (12,   9,  12),   "floor_crack":(8, 6, 8),
        "wall_base":   (78,  72,  82),   "wall_hi":   (138,130,142),
        "wall_sh":     (40,  35,  44),   "mortar":    (18,  14,  20),
    },
    "forge": {
        "floor_base":  (32,   8,   0),   "floor_hi":  (58,  18,   4),
        "floor_lo":    (18,   4,   0),   "floor_crack":(12, 2, 0),
        "wall_base":   (96,  44,  18),   "wall_hi":   (158, 84,  36),
        "wall_sh":     (50,  18,   4),   "mortar":    (24,   6,   0),
    },
    "inferno": {
        "floor_base":  (42,   4,   0),   "floor_hi":  (78,  14,   4),
        "floor_lo":    (26,   2,   0),   "floor_crack":(18, 0, 0),
        "wall_base":   (178, 44,   8),   "wall_hi":   (232, 94,  18),
        "wall_sh":     (92,  14,   0),   "mortar":    (48,   6,   0),
    },
    "abyss": {
        "floor_base":  ( 6,  10,  18),   "floor_hi":  (14,  22,  44),
        "floor_lo":    ( 2,   4,   8),   "floor_crack":(0, 2, 6),
        "wall_base":   (16,  66,  92),   "wall_hi":   (32, 124,154),
        "wall_sh":     ( 6,  32,  52),   "mortar":    ( 2,   8,  16),
    },
}


# ── Tile generators ───────────────────────────────────────────────────────────

def make_floor_tile(theme: dict, variant: int = 0, size: int = TILE_SZ) -> Image.Image:
    """Organic flagstone slab with fractal noise grain."""
    img  = Image.new("RGBA", (size, size))
    draw = ImageDraw.Draw(img)
    seed = variant * 37

    M = 2   # mortar border
    # Fill mortar background
    img.paste(theme["mortar"][:3] + (255,), (0, 0, size, size))

    # Draw slab face pixel by pixel with noise
    for py in range(M, size - M):
        for px in range(M, size - M):
            # Base noise
            nx = px / size * 3.0 + seed * 0.1
            ny = py / size * 3.0 + seed * 0.17
            n  = fractal(nx, ny, 4, seed)
            # Vertical gradient (lighter at top)
            grad = 1.0 - (py - M) / (size - 2 * M - 1) * 0.25
            t    = n * 0.55 + 0.45
            col  = blend(theme["floor_lo"], theme["floor_hi"], t * grad)
            img.putpixel((px, py), col + (255,))

    # Bevel edges of slab
    hi  = lighten(theme["floor_hi"], 28)
    sh  = darken(theme["mortar"],    4)
    for i in range(2):
        a = 200 - i * 80
        # Top + left highlight
        for x in range(M, size - M):
            img.putpixel((x, M + i), with_alpha(hi, a))
        for y in range(M, size - M):
            img.putpixel((M + i, y), with_alpha(hi, a))
        # Bottom + right shadow
        for x in range(M, size - M):
            img.putpixel((x, size - M - 1 - i), with_alpha(sh, a))
        for y in range(M, size - M):
            img.putpixel((size - M - 1 - i, y), with_alpha(sh, a))

    # Occasional crack
    rng = random.Random(seed * 3 + 7)
    if rng.random() < 0.35:
        cx_ = rng.randint(M + 4, size - M - 10)
        cy_ = rng.randint(M + 4, size - M - 8)
        crack = theme["floor_crack"] + (180,)
        draw.line([(cx_, cy_), (cx_ + rng.randint(4, 10), cy_ + rng.randint(2, 6))],
                  fill=crack, width=1)

    # Slight blur for organic feel
    return img.filter(ImageFilter.GaussianBlur(0.4))


def make_wall_tile(theme: dict, variant: int = 0, size: int = TILE_SZ) -> Image.Image:
    """Stone-block wall with layered fractal texture."""
    img  = Image.new("RGBA", (size, size))
    seed = variant * 53 + 100

    BLOCK_W, BLOCK_H = 18, 10

    # Stone base noise
    for py in range(size):
        for px in range(size):
            nx = px / size * 4.0
            ny = py / size * 4.0
            n  = fractal(nx, ny, 5, seed)
            t  = n * 0.6 + 0.4
            col = blend(theme["wall_sh"], theme["wall_hi"], t)
            img.putpixel((px, py), col + (255,))

    draw = ImageDraw.Draw(img)

    # Mortar grid
    for row in range(4):
        ry  = row * BLOCK_H
        off = (BLOCK_W // 2) if (row + variant) % 2 == 0 else 0
        # Horizontal mortar line
        draw.line([(0, ry), (size, ry)], fill=theme["mortar"] + (255,), width=1)
        for col in range(-1, 4):
            bx = col * BLOCK_W + off
            x1, x2 = max(0, bx), min(size, bx + BLOCK_W - 1)
            y1, y2  = ry + 1, min(size, ry + BLOCK_H - 1)
            if x2 <= x1 or y2 <= y1:
                continue
            # Vertical mortar
            draw.line([(x1, y1), (x1, y2)], fill=theme["mortar"] + (255,), width=1)
            # Bevel highlight top
            hl = lighten(theme["wall_hi"], 18)
            draw.line([(x1 + 1, y1 + 1), (x2 - 1, y1 + 1)], fill=hl + (180,), width=1)
            draw.line([(x1 + 1, y1 + 1), (x1 + 1, y2 - 1)], fill=hl + (140,), width=1)
            # Bevel shadow bottom-right
            sh = theme["wall_sh"] + (200,)
            draw.line([(x1 + 1, y2 - 1), (x2 - 1, y2 - 1)], fill=sh, width=1)
            draw.line([(x2 - 1, y1 + 1), (x2 - 1, y2 - 1)], fill=sh, width=1)

    # Top-face depth cap (lighter top 3 px — reads as wall top surface)
    cap  = lighten(theme["wall_hi"], 55)
    cap2 = lighten(theme["wall_hi"], 28)
    draw.line([(0, 0), (size, 0)], fill=cap  + (255,), width=1)
    draw.line([(0, 1), (size, 1)], fill=cap2 + (255,), width=1)
    draw.line([(0, 2), (size, 2)], fill=theme["wall_hi"] + (200,), width=1)

    return img.filter(ImageFilter.GaussianBlur(0.3))


# ── Player sprites ────────────────────────────────────────────────────────────

_SKIN  = (232, 174, 96, 255)
_SKIN_D= (180, 122, 60, 255)
_BLACK = (0, 0, 0, 255)

def _armor_colors(quality: str = "plate") -> dict:
    if quality == "plate":
        return dict(
            base =(68, 96, 160, 255), hi=(130, 162, 224, 255),
            sh   =(32, 52, 100, 255), trim=(200, 174, 50, 255),
            cape =(24, 36,  88, 255), cape_hi=(60, 88, 160, 255),
        )
    return dict(
        base=(56, 100, 56, 255), hi=(100, 164, 100, 255),
        sh  =(28,  60, 28, 255), trim=(160, 130, 30, 255),
        cape=(28,  52, 28, 255), cape_hi=(64, 120, 64, 255),
    )


def _draw_player_facing(direction: str) -> Image.Image:
    """
    40×40 armored knight sprite.
    direction: 'south' | 'north' | 'east' | 'west'
    """
    sz  = 40
    img = Image.new("RGBA", (sz, sz), (0, 0, 0, 0))
    d   = ImageDraw.Draw(img)
    col = _armor_colors("plate")

    cx, cy = sz // 2, sz // 2

    def pix(x, y, c):
        if 0 <= x < sz and 0 <= y < sz:
            img.putpixel((x, y), c)

    def rect(x, y, w, h, c):
        x2, y2 = min(sz-1, x+w-1), min(sz-1, y+h-1)
        if x2 >= x and y2 >= y:
            d.rectangle([x, y, x2, y2], fill=c)

    def ellipse(x, y, w, h, c):
        d.ellipse([x, y, x+w-1, y+h-1], fill=c)

    # ── Facing SOUTH (default, front view) ───────────────────────────────────
    if direction == "south":
        # Shadow
        d.ellipse([cx-12, cy+13, cx+12, cy+18], fill=(0,0,0,60))

        # Cape
        d.polygon([(cx-9, cy-4), (cx+9, cy-4),
                   (cx+12, cy+12), (cx-12, cy+12)], fill=col["cape"])
        d.polygon([(cx-8, cy-3), (cx+8, cy-3),
                   (cx+10, cy+10), (cx-10, cy+10)], fill=col["cape_hi"])

        # Boots
        for sx_, sy_ in [(cx-5, cy+10), (cx+1, cy+10)]:
            rect(sx_, sy_, 5, 7, (32, 20, 8, 255))
            rect(sx_+1, sy_, 3, 5, (56, 36, 14, 255))

        # Legs / hose
        rect(cx-7, cy+4, 6, 8, col["sh"])
        rect(cx+1, cy+4, 6, 8, col["sh"])
        rect(cx-6, cy+4, 4, 6, col["base"])
        rect(cx+2, cy+4, 4, 6, col["base"])

        # Body / chest plate
        rect(cx-8, cy-6, 16, 12, col["sh"])
        rect(cx-7, cy-5, 14, 10, col["base"])
        rect(cx-6, cy-5, 12,  8, col["hi"])
        # Plate groove
        d.line([(cx, cy-5), (cx, cy+4)], fill=col["sh"], width=1)
        d.line([(cx-6, cy+1), (cx+6, cy+1)], fill=col["sh"], width=1)

        # Pauldrons
        for side in (-1, 1):
            px_ = cx + side * 8
            ellipse(px_-4, cy-7, 9, 9, col["sh"])
            ellipse(px_-3, cy-6, 7, 7, col["base"])
            ellipse(px_-2, cy-5, 5, 5, col["hi"])

        # Belt
        rect(cx-7, cy+2, 14, 3, (44, 30, 10, 255))
        rect(cx-2, cy+2,  4, 3, (160, 130, 20, 255))  # buckle

        # Arms
        rect(cx-11, cy-3, 5, 8, col["sh"])
        rect(cx+ 6, cy-3, 5, 8, col["sh"])
        rect(cx-10, cy-2, 3, 6, col["base"])
        rect(cx+ 7, cy-2, 3, 6, col["base"])

        # Sword (right side)
        d.line([(cx+10, cy+4), (cx+18, cy-8)], fill=(0,0,0,255), width=3)
        d.line([(cx+10, cy+3), (cx+18, cy-9)], fill=(190, 190, 220, 255), width=2)
        d.line([(cx+9, cy+2), (cx+10, cy+4)],  fill=(160, 130, 30, 255), width=2)
        d.line([(cx+7, cy+1), (cx+12, cy+1)],  fill=(160, 130, 30, 255), width=2)

        # Shield (left side)
        shx, shy = cx-16, cy-4
        d.polygon([(shx+3,shy), (shx+8,shy), (shx+10,shy+8), (shx+5,shy+13), (shx,shy+8)],
                  fill=col["sh"])
        d.polygon([(shx+4,shy+1),(shx+7,shy+1),(shx+9,shy+8),(shx+5,shy+12),(shx+1,shy+8)],
                  fill=col["base"])
        d.line([(shx+5,shy+1),(shx+5,shy+11)], fill=col["trim"], width=1)
        d.line([(shx+2,shy+6),(shx+8,shy+6)],  fill=col["trim"], width=1)

        # Helmet
        hx, hy = cx, cy-12
        ellipse(hx-7, hy-5, 15, 14, (0,0,0,255))
        ellipse(hx-6, hy-4, 13, 12, (70,80,100,255))
        ellipse(hx-5, hy-3, 11, 10, (100,112,140,255))
        # Face opening
        rect(hx-4, hy+1, 8, 5, _SKIN_D)
        rect(hx-3, hy+2, 6, 3, _SKIN)
        # Helmet crest line
        d.line([(hx,hy-3),(hx,hy+2)], fill=(160,130,30,255), width=1)
        # Visor slit
        for i in range(3):
            rect(hx-3, hy+2+i, 6, 1, (20,18,24,200) if i == 1 else (70,64,80,180))
        # Eyes
        pix(hx-2, hy+3, (200, 180, 80, 255))
        pix(hx+2, hy+3, (200, 180, 80, 255))

    # ── Facing NORTH (back view) ──────────────────────────────────────────────
    elif direction == "north":
        d.ellipse([cx-12, cy+13, cx+12, cy+18], fill=(0,0,0,60))
        # Cape (prominent from back)
        d.polygon([(cx-9, cy-2), (cx+9, cy-2),
                   (cx+13, cy+14), (cx-13, cy+14)], fill=col["cape"])
        d.line([(cx-8,cy-2),(cx-12,cy+13)], fill=col["cape_hi"], width=2)
        d.line([(cx+8,cy-2),(cx+12,cy+13)], fill=col["cape_hi"], width=2)
        # Boots
        for sx_, sy_ in [(cx-5, cy+10), (cx+1, cy+10)]:
            rect(sx_, sy_, 5, 7, (32,20,8,255))
            rect(sx_+1,sy_,3,5,(56,36,14,255))
        # Legs
        rect(cx-7, cy+4, 6, 8, col["sh"])
        rect(cx+1, cy+4, 6, 8, col["sh"])
        rect(cx-6, cy+4, 4, 6, col["base"])
        rect(cx+2, cy+4, 4, 6, col["base"])
        # Back plate
        rect(cx-8, cy-6, 16, 12, col["sh"])
        rect(cx-7, cy-5, 14, 10, col["base"])
        rect(cx-5, cy-4,  4,  3, col["hi"])
        rect(cx+1, cy-4,  4,  3, col["hi"])
        # Pauldrons
        for side in (-1, 1):
            px_ = cx + side * 8
            ellipse(px_-4, cy-7, 9, 9, col["sh"])
            ellipse(px_-3, cy-6, 7, 7, col["base"])
        # Arms
        rect(cx-11, cy-3, 5, 8, col["sh"])
        rect(cx+ 6, cy-3, 5, 8, col["sh"])
        # Helmet back
        hx, hy = cx, cy-12
        ellipse(hx-7, hy-5, 15, 14, (0,0,0,255))
        ellipse(hx-6, hy-4, 13, 12, (70,80,100,255))
        ellipse(hx-5, hy-3, 11, 10, (100,112,140,255))
        # Helmet crest
        d.line([(hx,hy-4),(hx,hy+3)], fill=(160,130,30,255), width=2)

    # ── Facing EAST ───────────────────────────────────────────────────────────
    elif direction in ("east", "west"):
        flip = direction == "west"
        # Shadow
        d.ellipse([cx-10, cy+13, cx+10, cy+18], fill=(0,0,0,60))
        # Cape sweeping back
        back = 1 if not flip else -1
        cape_tip_x = cx - back * 12
        d.polygon([(cx + back*5, cy-4), (cx + back*6, cy+4),
                   (cape_tip_x, cy+10), (cape_tip_x-back*2, cy-2)],
                  fill=col["cape"])
        # Boot
        bx_ = cx + back * 4
        rect(bx_-2, cy+10, 8, 7, (32,20,8,255))
        rect(bx_-1, cy+10, 6, 5, (56,36,14,255))
        rect(bx_+1, cy+16, 7, 2, (24,14,4,255))  # sole
        # Leg
        rect(cx-3, cy+4, 6, 8, col["sh"])
        rect(cx-2, cy+4, 4, 6, col["base"])
        # Body
        rect(cx-5, cy-6, 10, 12, col["sh"])
        rect(cx-4, cy-5,  8, 10, col["base"])
        rect(cx-3, cy-4,  6,  8, col["hi"])
        # Profile pauldron (leading side)
        px_ = cx + back * 6
        ellipse(px_-4, cy-7, 9, 9, col["sh"])
        ellipse(px_-3, cy-6, 7, 7, col["base"])
        ellipse(px_-2, cy-5, 5, 5, col["hi"])
        # Arm (forward arm carries sword)
        arm_x = cx + back * 5
        rect(arm_x-2, cy-2, 4, 9, col["sh"])
        rect(arm_x-1, cy-1, 2, 7, col["base"])
        # Sword
        sx0, sy0 = arm_x + back * 1, cy + 5
        sx1, sy1 = sx0 + back * 14, sy0 - 14
        d.line([(sx0, sy0), (sx1, sy1)], fill=(0,0,0,255), width=3)
        d.line([(sx0, sy0-1), (sx1, sy1-1)], fill=(190,190,220,255), width=2)
        d.line([(sx0-back*2, sy0-3), (sx0+back*2, sy0-3)],
               fill=(160,130,30,255), width=2)
        # Shield on back arm (profile)
        shx = cx - back * 8
        d.ellipse([shx-5, cy-5, shx+4, cy+7], fill=col["sh"])
        d.ellipse([shx-4, cy-4, shx+3, cy+6], fill=col["base"])
        d.line([(shx-1, cy-3), (shx-1, cy+5)], fill=col["trim"], width=1)
        # Helmet (side profile)
        hx, hy = cx, cy-11
        d.ellipse([hx-5, hy-5, hx+5, hy+7],  fill=(0,0,0,255))
        d.ellipse([hx-4, hy-4, hx+4, hy+6],  fill=(70,80,100,255))
        d.ellipse([hx-3, hy-3, hx+3, hy+5],  fill=(100,112,140,255))
        # Face opening (narrow side slit)
        fax = hx + back * 3
        rect(fax-1, hy,    3, 5, _SKIN_D)
        rect(fax,   hy+1,  2, 3, _SKIN)
        pix(fax, hy+2, (200,180,80,255))
        # Nose guard
        rect(fax+back, hy+1, 2, 4, (80,88,108,255))
        # Crest
        d.line([(hx-back*2,hy-5),(hx+back*2,hy-5)], fill=(160,130,30,255), width=2)
        if flip:
            img = img.transpose(Image.FLIP_LEFT_RIGHT)

    # Apply slight sharpening for crisp look
    img = img.filter(ImageFilter.SHARPEN)
    return img


def save_player_sprites():
    out = ASSETS / "sprites"
    out.mkdir(exist_ok=True)
    for direction in ("south", "north", "east", "west"):
        spr = _draw_player_facing(direction)
        spr.save(out / f"player_{direction}.png")
        print(f"  player_{direction}.png")


# ── Enemy sprites ─────────────────────────────────────────────────────────────

def make_goblin(size: int = 28) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0,0,0,0))
    d   = ImageDraw.Draw(img)
    cx, cy = size//2, size//2

    _B = (0,0,0,255)
    _G = (80, 140, 50, 255);  _GD = (50, 90, 28, 255);  _GH = (120, 190, 80, 255)
    _S = (220, 60, 60, 255)   # eyes
    _CLUB_C = (110, 80, 40, 255);  _CLUB_H = (160, 120, 60, 255)
    _CLOTH = (80, 55, 20, 255)

    # Shadow
    d.ellipse([cx-9, cy+9, cx+9, cy+13], fill=(0,0,0,50))

    # Ears (big, pointed, swept outward)
    for side in (-1, 1):
        ear = [(cx+side*4, cy-6),
               (cx+side*13, cy-14),
               (cx+side*8,  cy-2)]
        d.polygon([(x+1,y+1) for x,y in ear], fill=_B)
        d.polygon(ear, fill=_G)
        # Inner ear
        inner = [(cx+side*5, cy-6),
                 (cx+side*11, cy-12),
                 (cx+side*8,  cy-3)]
        d.polygon(inner, fill=_GD)

    # Body — hunched (shifted down)
    d.ellipse([cx-7, cy-1, cx+7, cy+11], fill=_B)
    d.ellipse([cx-6, cy,   cx+6, cy+10], fill=_GD)
    d.ellipse([cx-5, cy+1, cx+5, cy+9],  fill=_G)
    # Belly
    d.ellipse([cx-3, cy+4, cx+3, cy+9],  fill=_GH)
    # Cloth loincloth
    d.rectangle([cx-4, cy+7, cx+4, cy+11], fill=_CLOTH)

    # Head — large for the body
    d.ellipse([cx-7, cy-11, cx+7, cy+1],   fill=_B)
    d.ellipse([cx-6, cy-10, cx+6, cy],     fill=_GD)
    d.ellipse([cx-5, cy-9,  cx+5, cy-1],   fill=_G)

    # Eyes — deep-set red
    for side in (-1, 1):
        ex = cx + side * 3
        d.rectangle([ex-2, cy-7, ex+1, cy-4], fill=_B)
        d.rectangle([ex-1, cy-6, ex,   cy-5], fill=_S)

    # Nostrils
    for side in (-1, 1):
        img.putpixel((cx + side*1, cy-3), (40,20,10,220))

    # Fangs
    for side, off in ((-1, -2), (1, 1)):
        d.line([(cx+off, cy-2), (cx+off, cy+1)], fill=(220,200,160,255), width=1)

    # Claw lines (lower corners of body)
    for side in (-1, 1):
        bx = cx + side * 6
        for i in range(3):
            d.line([(bx, cy+8), (bx + side*(2+i), cy+12+i)],
                   fill=_B, width=1)

    # Bone club
    d.line([(cx+8, cy+2), (cx+18, cy-10)], fill=_B,     width=4)
    d.line([(cx+8, cy+2), (cx+18, cy-10)], fill=_CLUB_C, width=3)
    d.line([(cx+7, cy+1), (cx+17, cy-11)], fill=_CLUB_H, width=1)
    d.ellipse([cx+14, cy-14, cx+22, cy-7], fill=_B)
    d.ellipse([cx+15, cy-13, cx+21, cy-8], fill=_CLUB_C)
    d.ellipse([cx+16, cy-12, cx+20, cy-9], fill=_CLUB_H)

    return img


def make_skeleton(size: int = 28) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0,0,0,0))
    d   = ImageDraw.Draw(img)
    cx, cy = size//2, size//2

    _B   = (0,0,0,255)
    _BN  = (192, 184, 162, 255)
    _BND = (130, 122, 104, 255)
    _BNH = (220, 215, 196, 255)
    _EYE = (80, 200, 255, 255)
    _SW  = (190, 188, 175, 255)
    _SWH = (220, 225, 215, 255)
    _GLD = (160, 130, 30, 255)

    d.ellipse([cx-8, cy+9, cx+8, cy+13], fill=(0,0,0,50))

    # ── Arm bones (behind body) ───────────────────────────────────────────────
    # Left arm — sword arm
    d.line([(cx+5, cy-1), (cx+11, cy+6)], fill=_B,   width=3)
    d.line([(cx+5, cy-1), (cx+11, cy+6)], fill=_BND, width=2)
    d.ellipse([cx+4, cy-3, cx+8, cy+1], fill=_B)
    d.ellipse([cx+5, cy-2, cx+7, cy],   fill=_BN)
    d.ellipse([cx+9, cy+4, cx+13, cy+8], fill=_B)
    d.ellipse([cx+10, cy+5, cx+12, cy+7], fill=_BN)
    # Right arm — tucked
    d.line([(cx-5, cy-1), (cx-10, cy+5)], fill=_B,   width=3)
    d.line([(cx-5, cy-1), (cx-10, cy+5)], fill=_BND, width=2)

    # ── Ribcage / spine ───────────────────────────────────────────────────────
    # Spine
    d.line([(cx, cy-2), (cx, cy+9)], fill=_B,   width=3)
    d.line([(cx, cy-2), (cx, cy+9)], fill=_BND, width=2)
    # Ribs — 3 pairs (drawn as small arcs curving outward)
    for i in range(3):
        ry = cy + i * 3
        for side in (-1, 1):
            rx0 = cx + 1
            rx1 = cx + side * 7
            x0, x1 = min(rx0, rx1), max(rx0, rx1)
            if x1 <= x0:
                continue
            sa = 0 if side > 0 else 180
            ea = 180 if side > 0 else 360
            d.arc([x0, ry-1, x1, ry+4], sa, ea, fill=_B,   width=2)
            d.arc([x0, ry-1, x1, ry+4], sa, ea, fill=_BNH, width=1)

    # ── Pelvis ────────────────────────────────────────────────────────────────
    d.ellipse([cx-5, cy+8, cx+5, cy+12], fill=_B)
    d.ellipse([cx-4, cy+9, cx+4, cy+11], fill=_BN)

    # ── Leg bones ─────────────────────────────────────────────────────────────
    for side in (-1, 1):
        lx = cx + side * 3
        d.line([(lx, cy+10), (lx, cy+18)], fill=_B,   width=3)
        d.line([(lx, cy+10), (lx, cy+18)], fill=_BND, width=2)
        d.ellipse([lx-2, cy+17, lx+2, cy+21], fill=_B)
        d.ellipse([lx-1, cy+18, lx+1, cy+20], fill=_BN)

    # ── Skull ─────────────────────────────────────────────────────────────────
    hx, hy = cx, cy-8
    d.ellipse([hx-7, hy-6, hx+7, hy+6],   fill=_B)
    d.ellipse([hx-6, hy-5, hx+6, hy+5],   fill=_BND)
    d.ellipse([hx-5, hy-4, hx+5, hy+4],   fill=_BN)
    # Cranium dome highlight
    d.arc([hx-4, hy-4, hx+4, hy],   200, 340, fill=_BNH, width=1)
    # Eye sockets
    for side in (-1, 1):
        ex = hx + side * 3
        d.ellipse([ex-2, hy-2, ex+2, hy+2], fill=_B)
        # Glowing eyes
        d.ellipse([ex-1, hy-1, ex+1, hy+1], fill=_EYE)
    # Nasal void
    d.rectangle([hx-1, hy+1, hx+1, hy+3], fill=_B)
    # Teeth
    for tx in range(hx-4, hx+5, 2):
        d.rectangle([tx, hy+3, tx+1, hy+5], fill=_BN)
        d.line([(tx, hy+3), (tx, hy+5)], fill=_B, width=1)

    # ── Sword (right side of figure) ─────────────────────────────────────────
    sw0x, sw0y = cx+11, cy+5
    sw1x, sw1y = cx+21, cy-10
    d.line([(sw0x,sw0y), (sw1x,sw1y)], fill=_B,   width=3)
    d.line([(sw0x,sw0y), (sw1x,sw1y)], fill=_SW,  width=2)
    d.line([(sw0x,sw0y-1),(sw1x,sw1y-1)], fill=_SWH, width=1)
    # Guard
    d.line([(sw0x-3, sw0y-3), (sw0x+3, sw0y+3)], fill=_GLD, width=2)

    return img


def make_orc(size: int = 36) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0,0,0,0))
    d   = ImageDraw.Draw(img)
    cx, cy = size//2, size//2

    _B  = (0,0,0,255)
    _AR = (28, 60, 190, 255)   # blue plate
    _ARH= (80, 140, 240, 255)
    _ARD= (12, 28, 110, 255)
    _CAPE=(8, 24, 90, 255);  _CAPEH=(30, 70, 150, 255)
    _EYE=(220, 30, 30, 255)
    _HELM=(60, 70, 90, 255);  _HELMH=(120,130,150,255)
    _GOLD=(180, 150, 30, 255)

    # Shadow
    d.ellipse([cx-12, cy+13, cx+12, cy+18], fill=(0,0,0,55))

    # Cape / tabard (behind body)
    d.polygon([(cx-8, cy-4), (cx+8, cy-4),
               (cx+12, cy+14), (cx-12, cy+14)], fill=_B)
    d.polygon([(cx-7, cy-3), (cx+7, cy-3),
               (cx+11, cy+13), (cx-11, cy+13)], fill=_CAPE)
    d.line([(cx-6, cy-2), (cx-10, cy+12)], fill=_CAPEH, width=2)
    d.line([(cx+6, cy-2), (cx+10, cy+12)], fill=_CAPEH, width=2)

    # Boots
    for side in (-1, 1):
        bx = cx + side * 4
        d.rectangle([bx-4, cy+10, bx+3, cy+17], fill=_B)
        d.rectangle([bx-3, cy+11, bx+2, cy+16], fill=(36,24,10,255))
        d.rectangle([bx-3, cy+16, bx+4, cy+18], fill=(20,12,4,255))

    # Legs
    for side in (-1, 1):
        lx = cx + side * 4
        d.rectangle([lx-4, cy+4, lx+3, cy+11], fill=_ARD)
        d.rectangle([lx-3, cy+5, lx+2, cy+10], fill=_AR)

    # Body / chest plate
    d.rectangle([cx-9, cy-8, cx+9, cy+6], fill=_B)
    d.rectangle([cx-8, cy-7, cx+8, cy+5], fill=_ARD)
    d.rectangle([cx-7, cy-6, cx+7, cy+4], fill=_AR)
    d.rectangle([cx-6, cy-5, cx+6, cy+2], fill=_ARH)
    # Chest lines
    d.line([(cx, cy-6), (cx, cy+2)],     fill=_ARD, width=1)
    d.line([(cx-6,cy-1),(cx+6,cy-1)],    fill=_ARD, width=1)
    # Tabard stripe
    d.rectangle([cx-2, cy-4, cx+2, cy+4], fill=(10,30,110,255))
    d.line([(cx, cy-3), (cx, cy+3)],       fill=_GOLD, width=1)

    # Pauldrons with spikes
    for side in (-1, 1):
        px_ = cx + side * 9
        d.ellipse([px_-5, cy-9, px_+4, cy+1], fill=_B)
        d.ellipse([px_-4, cy-8, px_+3, cy],   fill=_ARD)
        d.ellipse([px_-3, cy-7, px_+2, cy-1], fill=_AR)
        d.ellipse([px_-2, cy-6, px_+1, cy-2], fill=_ARH)
        # Spike
        d.polygon([(px_-1, cy-9), (px_+1, cy-9), (px_, cy-14)], fill=_B)
        d.polygon([(px_-1,cy-8),  (px_+1,cy-8),  (px_, cy-13)], fill=_ARH)

    # Arms
    for side in (-1, 1):
        ax = cx + side * 10
        d.rectangle([ax-3, cy-5, ax+2, cy+5], fill=_B)
        d.rectangle([ax-2, cy-4, ax+1, cy+4], fill=_AR)

    # Axe (right side)
    d.line([(cx+12, cy+4), (cx+12, cy-12)], fill=_B, width=3)
    d.line([(cx+12, cy+4), (cx+12, cy-12)], fill=(130,100,40,255), width=2)
    d.polygon([(cx+12, cy-12), (cx+19, cy-8), (cx+20, cy-14),
               (cx+14, cy-16)], fill=_B)
    d.polygon([(cx+12, cy-11), (cx+18, cy-8), (cx+19, cy-13),
               (cx+13, cy-15)], fill=(160,155,165,255))
    d.line([(cx+12, cy-11),(cx+18, cy-8)], fill=(210,210,220,255), width=1)

    # Helmet with nose guard
    hx, hy = cx, cy-12
    d.ellipse([hx-8, hy-7, hx+8, hy+7],   fill=_B)
    d.ellipse([hx-7, hy-6, hx+7, hy+6],   fill=_HELM)
    d.ellipse([hx-6, hy-5, hx+6, hy+5],   fill=_HELMH)
    # Brow ridge
    d.line([(hx-6,hy-2),(hx+6,hy-2)], fill=_B, width=2)
    d.line([(hx-5,hy-2),(hx+5,hy-2)], fill=(90,100,120,255), width=1)
    # Eye slits
    d.rectangle([hx-6, hy, hx-2, hy+2], fill=_B)
    d.rectangle([hx+2, hy, hx+6, hy+2], fill=_B)
    d.rectangle([hx-5, hy, hx-3, hy+1], fill=_EYE)
    d.rectangle([hx+3, hy, hx+5, hy+1], fill=_EYE)
    # Nose guard
    d.rectangle([hx-1, hy, hx+1, hy+6],   fill=_B)
    d.rectangle([hx-1, hy, hx,   hy+5],   fill=(90,100,120,255))
    # Horns
    for side in (-1, 1):
        horn = [(hx+side*5, hy-5), (hx+side*11, hy-14), (hx+side*4, hy-2)]
        d.polygon([(x+1,y+1) for x,y in horn], fill=_B)
        d.polygon(horn, fill=(80,60,20,255))
        d.line([horn[0], horn[1]], fill=(130,100,40,255), width=1)

    return img


def make_demon(size: int = 28) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0,0,0,0))
    d   = ImageDraw.Draw(img)
    cx, cy = size//2, size//2

    _B    = (0,0,0,255)
    _ROBE = (130, 0, 200, 255);  _ROBED = (60, 0, 110, 255)
    _ROBEH= (180, 80, 255, 255)
    _GOLD = (240, 180, 0, 255)
    _CLAW = (80, 20, 100, 255)

    # Shadow
    d.ellipse([cx-8, cy+9, cx+8, cy+13], fill=(0,0,0,50))

    # ── Wavy cloak hem (bottom) ────────────────────────────────────────────
    # Simulate wave with 5 points
    hem_pts = []
    for j in range(7):
        hx_ = cx - 12 + j * 4
        hy_ = cy + 13 + int(math.sin(j * 1.1) * 4)
        hem_pts.append((hx_, hy_))
    robe_poly = hem_pts + [(cx+12, cy-2), (cx+6, cy-10),
                            (cx, cy-13), (cx-6, cy-10), (cx-12, cy-2)]
    d.polygon([(x+1,y+1) for x,y in robe_poly], fill=_B)
    d.polygon(robe_poly, fill=_ROBED)

    inner_poly = hem_pts[1:-1] + [(cx+10, cy-2), (cx+5, cy-9),
                                    (cx, cy-11), (cx-5, cy-9), (cx-10, cy-2)]
    d.polygon(inner_poly, fill=_ROBE)

    # Robe highlight fold
    d.line([(cx, cy-10), (cx, cy+6)], fill=_ROBEH, width=1)

    # ── Clawed hands ──────────────────────────────────────────────────────
    for side in (-1, 1):
        hx_ = cx + side * 11
        hy_ = cy + 2
        d.ellipse([hx_-3, hy_-3, hx_+3, hy_+3], fill=_ROBED)
        for ci in range(3):
            cx2 = hx_ + side * (ci * 2)
            d.line([(cx2, hy_-3), (cx2 + side*3, hy_-8)], fill=_B, width=1)
            d.line([(cx2, hy_-3), (cx2 + side*3, hy_-8)], fill=_CLAW, width=1)

    # ── Hood ──────────────────────────────────────────────────────────────
    hx, hy = cx, cy-9
    d.ellipse([hx-9, hy-6, hx+9, hy+8],  fill=_B)
    d.ellipse([hx-8, hy-5, hx+8, hy+7],  fill=_ROBED)
    d.ellipse([hx-6, hy-3, hx+6, hy+5],  fill=_ROBE)
    # Hood rim arc
    d.arc([hx-8, hy-5, hx+8, hy+4], 180, 360, fill=_ROBEH, width=1)

    # Face in hood shadow
    d.ellipse([hx-4, hy-1, hx+4, hy+6], fill=(20, 10, 30, 220))

    # Glowing gold eyes
    ey = hy + 2
    d.rectangle([hx-4, ey, hx-1, ey+2], fill=_B)
    d.rectangle([hx+1, ey, hx+4, ey+2], fill=_B)
    d.rectangle([hx-3, ey, hx-2, ey+1], fill=_GOLD)
    d.rectangle([hx+2, ey, hx+3, ey+1], fill=_GOLD)
    img.putpixel((hx-2, ey),   (255, 230, 100, 255))
    img.putpixel((hx+3, ey),   (255, 230, 100, 255))

    return img


def save_enemy_sprites():
    out = ASSETS / "sprites" / "enemies"
    out.mkdir(parents=True, exist_ok=True)

    sprites = [
        ("goblin.png",   make_goblin(28)),
        ("skeleton.png", make_skeleton(28)),
        ("orc.png",      make_orc(36)),
        ("demon.png",    make_demon(28)),
    ]
    for name, img in sprites:
        img.save(out / name)
        print(f"  enemies/{name}")


# ── Town building facade textures ─────────────────────────────────────────────

_STALL_PALETTES = {
    "weapons":  dict(plaster=(162,124,92),  timber=(50,28,8),  awning=(160,50,10)),
    "armor":    dict(plaster=(110,120,148), timber=(28,36,60),  awning=(30,70,130)),
    "jewelry":  dict(plaster=(100,148,148), timber=(12,60,60),  awning=(20,130,130)),
    "potions":  dict(plaster=(100,148,100), timber=(16,60,16),  awning=(30,120,30)),
    "enchant":  dict(plaster=(128,100,160), timber=(36,10,72),  awning=(80,20,150)),
    "craft":    dict(plaster=(148,124,88),  timber=(50,28,8),   awning=(140,80,20)),
    "guild":    dict(plaster=(124,120,160), timber=(28,28,56),  awning=(60,60,140)),
    "house":    dict(plaster=(170,155,122), timber=(54,34,12),  awning=(110,70,16)),
}


def make_building_facade(specialty: str, w: int = 200, h: int = 140) -> Image.Image:
    pal = _STALL_PALETTES.get(specialty, _STALL_PALETTES["weapons"])
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d   = ImageDraw.Draw(img)
    pl  = pal["plaster"]
    tm  = pal["timber"]
    aw  = pal["awning"]

    # ── Stone base (lower 40 px) ──────────────────────────────────────────────
    stone_base = (72, 64, 54)
    for py in range(h - 40, h):
        for px in range(w):
            n = fractal(px / 60, py / 40, 3, hash(specialty) % 1000)
            col = blend(stone_base, lighten(stone_base, 28), n)
            img.putpixel((px, py), col + (255,))
    # Mortar lines
    BLOCK_W, BLOCK_H = 28, 14
    for row in range(3):
        ry = h - 40 + row * BLOCK_H
        d.line([(0, ry), (w, ry)], fill=(30,26,20,255), width=1)
        off = (BLOCK_W // 2) if row % 2 == 0 else 0
        for col in range(-1, w // BLOCK_W + 2):
            bx = col * BLOCK_W + off
            d.line([(bx, ry+1), (bx, ry+BLOCK_H-1)], fill=(30,26,20,255), width=1)

    # ── Plaster wall (upper portion) ──────────────────────────────────────────
    for py in range(0, h - 40):
        for px in range(w):
            n = fractal(px / 80, py / 60, 3, hash(specialty+str(1)) % 1000) * 0.3 + 0.7
            col = tuple(int(c * n) for c in pl)
            img.putpixel((px, py), col + (255,))

    # ── Timber frame ─────────────────────────────────────────────────────────
    def timber_rect(x, y, ww, hh):
        d.rectangle([x, y, x+ww, y+hh], fill=tm + (255,))
        d.line([(x+1, y+1), (x+ww-1, y+1)], fill=lighten(tm, 20) + (200,), width=1)
        d.line([(x+1, y+1), (x+1, y+hh-1)], fill=lighten(tm, 15) + (180,), width=1)

    T = 5  # timber width
    panel_w = w // 3
    # Verticals
    for bx in [0, panel_w, 2*panel_w, w - T]:
        timber_rect(bx, 0, T, h - 40)
    # Horizontals
    for by in [0, (h-40)//2, h-40-T]:
        timber_rect(0, by, w, T)
    # Diagonal braces per panel
    for pi in range(3):
        x0 = pi * panel_w + T
        x1 = x0 + panel_w - T
        y0, y1 = T, (h-40)//2 - T
        d.line([(x0, y0), (x1, y1)], fill=tm + (200,), width=2)
        d.line([(x1, y0), (x0, y1)], fill=tm + (200,), width=2)
        y0, y1 = (h-40)//2 + T, h-40-2*T
        d.line([(x0, y0), (x1, y1)], fill=tm + (200,), width=2)
        d.line([(x1, y0), (x0, y1)], fill=tm + (200,), width=2)

    # ── Windows (2 in upper section) ─────────────────────────────────────────
    win_h = max(30, (h-40)//2 - 16)
    win_w = panel_w - 24
    for wi, wx_ in enumerate([panel_w // 2 - win_w // 2,
                               2 * panel_w + panel_w // 2 - win_w // 2]):
        wy = 10
        # Frame
        d.rectangle([wx_-2, wy-2, wx_+win_w+1, wy+win_h+1], fill=tm+(255,))
        # Glass — warm interior glow
        for py_ in range(wy, wy+win_h):
            for px_ in range(wx_, wx_+win_w):
                dist_top = (py_ - wy) / win_h
                n = fractal(px_/30, py_/30, 2, wi*200)
                warm = blend((255, 200, 80), (255, 140, 40), dist_top + n*0.3)
                img.putpixel((px_, py_), warm + (220,))
        # Cross muntins
        mx = wx_ + win_w // 2
        my = wy + win_h // 2
        d.line([(mx, wy), (mx, wy+win_h)], fill=tm+(255,), width=2)
        d.line([(wx_, my), (wx_+win_w, my)], fill=tm+(255,), width=2)
        # Reflection glint
        d.line([(wx_+2, wy+2), (wx_+6, wy+2)], fill=(255,240,200,120), width=1)

    # ── Awning / counter ─────────────────────────────────────────────────────
    aw_y = h - 44
    d.rectangle([0, aw_y, w, aw_y+18], fill=aw+(255,))
    # Stripes
    stripe = lighten(aw, 30)
    for sx_ in range(0, w, 16):
        d.line([(sx_, aw_y), (sx_-8, aw_y+18)], fill=stripe+(180,), width=2)
    d.rectangle([0, aw_y, w, aw_y+18], fill=(0,0,0,0), outline=lighten(aw,40)+(255,))
    # Scalloped edge
    for sx_ in range(0, w-10, 14):
        d.arc([sx_, aw_y+12, sx_+14, aw_y+24], 0, 180, fill=lighten(aw,40)+(255,), width=2)

    img = img.filter(ImageFilter.GaussianBlur(0.35))
    return img


def save_town_facades():
    out = ASSETS / "town"
    out.mkdir(exist_ok=True)
    for specialty in _STALL_PALETTES:
        img = make_building_facade(specialty)
        img.save(out / f"facade_{specialty}.png")
        print(f"  town/facade_{specialty}.png")


# ── Tile texture generation ───────────────────────────────────────────────────

def save_tile_textures():
    out = ASSETS / "tiles"
    out.mkdir(exist_ok=True)
    for theme_name, theme in THEMES.items():
        for variant in range(4):
            floor = make_floor_tile(theme, variant)
            floor.save(out / f"floor_{theme_name}_{variant}.png")
            wall  = make_wall_tile(theme, variant)
            wall.save(out / f"wall_{theme_name}_{variant}.png")
        print(f"  tiles/{theme_name} (8 tiles)")


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Generating assets...")
    print("\n[1/4] Tile textures")
    save_tile_textures()
    print("\n[2/4] Player sprites")
    save_player_sprites()
    print("\n[3/4] Enemy sprites")
    save_enemy_sprites()
    print("\n[4/4] Town facades")
    save_town_facades()
    print(f"\nDone — assets written to {ASSETS}")
