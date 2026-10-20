#!/usr/bin/env python3
"""Generate Neon Calculator 2 launcher icons, adaptive icon layers and splash screens.

Pure PIL, no external assets. Run from the project root:
    python3 tools/make_assets.py
"""
import os
from PIL import Image, ImageDraw, ImageFilter, ImageFont

RES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "android", "app", "src", "main", "res")
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

BG_TOP = (26, 36, 65)
BG_BOT = (9, 11, 23)
CYAN = (82, 245, 238)
CYAN_DIM = (60, 190, 190)
PURPLE = (193, 140, 255)
SS = 4  # supersampling factor


def radial_glow(size, center, radius, color, strength=255):
    """Soft radial glow layer (RGBA)."""
    w, h = size
    layer = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(layer)
    steps = 60
    for i in range(steps, 0, -1):
        r = radius * i / steps
        a = int(strength * (1 - i / steps) ** 1.6)
        cx, cy = center
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=a)
    layer = layer.filter(ImageFilter.GaussianBlur(radius / 6))
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    solid = Image.new("RGBA", (w, h), color + (255,))
    out.paste(solid, (0, 0), layer)
    return out


def rounded_mask(size, radius):
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, size[0] - 1, size[1] - 1], radius=radius, fill=255)
    return m


def circle_mask(size):
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).ellipse([0, 0, size[0] - 1, size[1] - 1], fill=255)
    return m


def background(size):
    """Dark navy panel with a cyan aurora at the top and a purple hint at the bottom."""
    w, h = size
    img = Image.new("RGB", (1, h))
    px = img.load()
    for y in range(h):
        t = y / max(1, h - 1)
        px[0, y] = tuple(int(BG_TOP[i] + (BG_BOT[i] - BG_TOP[i]) * t) for i in range(3))
    img = img.resize(size)
    out = img.convert("RGBA")
    out = Image.alpha_composite(out, radial_glow(size, (w * 0.5, -h * 0.12), h * 0.95, CYAN, 60))
    out = Image.alpha_composite(out, radial_glow(size, (w * 0.88, h * 1.05), h * 0.8, PURPLE, 34))
    return out


def calculator_glyph(size, scale=1.0, glow=True):
    """Neon calculator: rounded body, glowing display bar and keypad dots."""
    s = size
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    g = int(s * 0.62 * scale)              # body size
    x0 = (s - g) // 2
    y0 = (s - g) // 2
    x1, y1 = x0 + g, y0 + g
    pad = int(g * 0.11)
    lw = max(2, int(g * 0.055))

    if glow:
        halo = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        hd = ImageDraw.Draw(halo)
        hd.rounded_rectangle([x0, y0, x1, y1], radius=int(g * 0.22), outline=CYAN + (170,), width=lw * 2)
        halo = halo.filter(ImageFilter.GaussianBlur(g * 0.07))
        img = Image.alpha_composite(img, halo)

    d = ImageDraw.Draw(img)
    # body
    d.rounded_rectangle([x0, y0, x1, y1], radius=int(g * 0.22), fill=(18, 22, 41, 255), outline=CYAN + (235,), width=lw)
    # display
    dx0, dy0 = x0 + pad, y0 + pad
    dx1, dy1 = x1 - pad, y0 + pad + int(g * 0.20)
    d.rounded_rectangle([dx0, dy0, dx1, dy1], radius=int(g * 0.05), fill=(9, 13, 27, 255), outline=CYAN + (150,), width=max(1, lw // 2))
    # display readout (cyan bar) + small accent
    bar_h = max(2, int((dy1 - dy0) * 0.20))
    by = (dy0 + dy1) // 2 - bar_h // 2
    d.rounded_rectangle([dx0 + int(g * 0.05), by, dx1 - int(g * 0.30), by + bar_h], radius=bar_h // 2, fill=CYAN + (255,))
    # keypad 3x3
    cols, rows = 3, 3
    kx0, ky0 = x0 + pad, dy1 + int(g * 0.07)
    kx1, ky1 = x1 - pad, y1 - pad
    cw = (kx1 - kx0) / cols
    ch = (ky1 - ky0) / rows
    kr = int(min(cw, ch) * 0.30)
    for r in range(rows):
        for c in range(cols):
            cx = kx0 + cw * (c + 0.5)
            cy = ky0 + ch * (r + 0.5)
            color = PURPLE if (r == rows - 1 and c == cols - 1) else CYAN_DIM
            d.ellipse([cx - kr, cy - kr, cx + kr, cy + kr], fill=color + (255,))
    return img


def icon_master(size):
    """Full-bleed app icon (square, rounded corners baked in for legacy launchers)."""
    s = size
    base = background((s, s))
    base = Image.alpha_composite(base, calculator_glyph(s))
    base.putalpha(rounded_mask((s, s), int(s * 0.22)))
    return base


def icon_round_master(size):
    s = size
    base = background((s, s))
    base = Image.alpha_composite(base, calculator_glyph(s, scale=0.86))
    base.putalpha(circle_mask((s, s)))
    return base


def foreground_master(size):
    """Adaptive-icon foreground: transparent, content inside the 66/108 safe zone."""
    s = size
    return calculator_glyph(s, scale=0.80)


def splash_image(w, h):
    """Splash: background + centered logo + wordmark, sized for the given canvas."""
    base = background((w, h))
    short = min(w, h)
    # faint neon grid
    grid = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grid)
    step = max(24, short // 18)
    for x in range(0, w, step):
        gd.line([(x, 0), (x, h)], fill=CYAN + (10,), width=1)
    for y in range(0, h, step):
        gd.line([(0, y), (w, y)], fill=CYAN + (10,), width=1)
    base = Image.alpha_composite(base, grid)

    logo = calculator_glyph(int(short * 0.52), scale=0.94)
    lw = logo.size[0]
    cx, cy = w // 2, int(h * 0.42)
    base.alpha_composite(logo, (cx - lw // 2, cy - lw // 2))

    d = ImageDraw.Draw(base)
    title = "NEON CALCULATOR 2"
    fs = max(12, int(short * 0.058))
    try:
        f = ImageFont.truetype(FONT_BOLD, fs)
        fs2 = max(9, int(short * 0.026))
        f2 = ImageFont.truetype(FONT_REG, fs2)
    except OSError:
        f = ImageFont.load_default()
        f2 = f
    tw = d.textlength(title, font=f)
    ty = cy + lw // 2 + int(short * 0.05)
    d.text((cx - tw / 2, ty), title, font=f, fill=(244, 247, 255, 255))
    sub = "SMART CALCULATOR"
    sw = d.textlength(sub, font=f2)
    d.text((cx - sw / 2, ty + fs * 1.5), sub, font=f2, fill=CYAN + (200,))
    return base.convert("RGB")


def save(img, relpath):
    path = os.path.join(RES, relpath)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path, optimize=True)
    print("wrote", relpath, img.size)


def main():
    # ---- launcher icons (legacy, per density) ----
    icon_densities = {"mdpi": 48, "hdpi": 72, "xhdpi": 96, "xxhdpi": 144, "xxxhdpi": 192}
    fg_densities = {"mdpi": 108, "hdpi": 162, "xhdpi": 216, "xxhdpi": 324, "xxxhdpi": 432}
    master = icon_master(1024)
    round_master = icon_round_master(1024)
    fg_master = foreground_master(1024)
    for d, px in icon_densities.items():
        save(master.resize((px, px), Image.LANCZOS), f"mipmap-{d}/ic_launcher.png")
        save(round_master.resize((px, px), Image.LANCZOS), f"mipmap-{d}/ic_launcher_round.png")
    for d, px in fg_densities.items():
        save(fg_master.resize((px, px), Image.LANCZOS), f"mipmap-{d}/ic_launcher_foreground.png")
    # full-bleed master kept for stores / README
    os.makedirs(os.path.join(RES, "..", "..", "..", "..", "..", "store"), exist_ok=True)
    store = os.path.normpath(os.path.join(RES, "..", "..", "..", "..", "..", "store"))
    master.resize((512, 512), Image.LANCZOS).convert("RGB").save(os.path.join(store, "play_icon_512.png"))

    # ---- splash screens ----
    splash = {
        "drawable/splash.png": (480, 320),
        "drawable-port-mdpi/splash.png": (320, 480),
        "drawable-port-hdpi/splash.png": (480, 800),
        "drawable-port-xhdpi/splash.png": (720, 1280),
        "drawable-port-xxhdpi/splash.png": (960, 1600),
        "drawable-port-xxxhdpi/splash.png": (1280, 1920),
        "drawable-land-mdpi/splash.png": (480, 320),
        "drawable-land-hdpi/splash.png": (800, 480),
        "drawable-land-xhdpi/splash.png": (1280, 720),
        "drawable-land-xxhdpi/splash.png": (1600, 960),
        "drawable-land-xxxhdpi/splash.png": (1920, 1280),
    }
    for rel, (w, h) in splash.items():
        save(splash_image(w, h), rel)

    # ---- adaptive icon background: keep the neon gradient ----
    bg = background((512, 512)).convert("RGB")
    bg.save(os.path.join(os.path.dirname(__file__), "icon_background_512.png"))
    print("wrote tools/icon_background_512.png")


if __name__ == "__main__":
    main()
