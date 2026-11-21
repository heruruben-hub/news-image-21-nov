#!/usr/bin/env python3
"""The Daily Signal - Saturday 21 November 2026.

A single-file, standard-library-only Python program that draws a
black-and-white newspaper front page summing up the world news of
Saturday 21 November 2026, and writes it as a 1024x1024 PNG.

No network, no clock, no randomness: the output bytes are identical
on every run.

Run:  python3 main.py                       (writes /output/entry.png)
      MAKEFUN_OUTPUT_DIR=. python3 main.py  (writes ./entry.png)
"""

import os
import struct
import zlib

W = H = 1024

# ------------------------------------------------------------------ font --
# Hand-set 5x7 pixel letters, stored as seven row bitmasks per glyph.
# In each mask the five low bits are the five columns, bit 4 leftmost.
# Text is stamped as scaled blocks, so any integer scale stays crisp
# and chunky enough to read when the page is shrunk down.
GLYPHS = {
    "A": (0x0E, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11),
    "B": (0x1E, 0x11, 0x11, 0x1E, 0x11, 0x11, 0x1E),
    "C": (0x0E, 0x11, 0x10, 0x10, 0x10, 0x11, 0x0E),
    "D": (0x1E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x1E),
    "E": (0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x1F),
    "F": (0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x10),
    "G": (0x0E, 0x11, 0x10, 0x17, 0x11, 0x11, 0x0F),
    "H": (0x11, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11),
    "I": (0x0E, 0x04, 0x04, 0x04, 0x04, 0x04, 0x0E),
    "J": (0x07, 0x02, 0x02, 0x02, 0x02, 0x12, 0x0C),
    "K": (0x11, 0x12, 0x14, 0x18, 0x14, 0x12, 0x11),
    "L": (0x10, 0x10, 0x10, 0x10, 0x10, 0x10, 0x1F),
    "M": (0x11, 0x1B, 0x15, 0x15, 0x11, 0x11, 0x11),
    "N": (0x11, 0x19, 0x15, 0x13, 0x11, 0x11, 0x11),
    "O": (0x0E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E),
    "P": (0x1E, 0x11, 0x11, 0x1E, 0x10, 0x10, 0x10),
    "Q": (0x0E, 0x11, 0x11, 0x11, 0x15, 0x12, 0x0D),
    "R": (0x1E, 0x11, 0x11, 0x1E, 0x14, 0x12, 0x11),
    "S": (0x0F, 0x10, 0x10, 0x0E, 0x01, 0x01, 0x1E),
    "T": (0x1F, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04),
    "U": (0x11, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E),
    "V": (0x11, 0x11, 0x11, 0x11, 0x11, 0x0A, 0x04),
    "W": (0x11, 0x11, 0x11, 0x15, 0x15, 0x1B, 0x11),
    "X": (0x11, 0x11, 0x0A, 0x04, 0x0A, 0x11, 0x11),
    "Y": (0x11, 0x11, 0x0A, 0x04, 0x04, 0x04, 0x04),
    "Z": (0x1F, 0x01, 0x02, 0x04, 0x08, 0x10, 0x1F),
    "0": (0x0E, 0x11, 0x13, 0x15, 0x19, 0x11, 0x0E),
    "1": (0x04, 0x0C, 0x04, 0x04, 0x04, 0x04, 0x0E),
    "2": (0x0E, 0x11, 0x01, 0x02, 0x04, 0x08, 0x1F),
    "3": (0x1E, 0x01, 0x01, 0x0E, 0x01, 0x01, 0x1E),
    "4": (0x02, 0x06, 0x0A, 0x12, 0x1F, 0x02, 0x02),
    "5": (0x1F, 0x10, 0x1E, 0x01, 0x01, 0x11, 0x0E),
    "6": (0x0E, 0x10, 0x10, 0x1E, 0x11, 0x11, 0x0E),
    "7": (0x1F, 0x01, 0x02, 0x02, 0x04, 0x04, 0x04),
    "8": (0x0E, 0x11, 0x11, 0x0E, 0x11, 0x11, 0x0E),
    "9": (0x0E, 0x11, 0x11, 0x0F, 0x01, 0x01, 0x0E),
    " ": (0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00),
    ".": (0x00, 0x00, 0x00, 0x00, 0x00, 0x0C, 0x0C),
    ",": (0x00, 0x00, 0x00, 0x00, 0x0C, 0x0C, 0x08),
    "'": (0x04, 0x04, 0x08, 0x00, 0x00, 0x00, 0x00),
    '"': (0x0A, 0x0A, 0x00, 0x00, 0x00, 0x00, 0x00),
    ":": (0x00, 0x0C, 0x0C, 0x00, 0x0C, 0x0C, 0x00),
    ";": (0x00, 0x0C, 0x0C, 0x00, 0x0C, 0x0C, 0x08),
    "-": (0x00, 0x00, 0x00, 0x1F, 0x00, 0x00, 0x00),
    "%": (0x19, 0x1A, 0x02, 0x04, 0x08, 0x0B, 0x13),
    "$": (0x04, 0x0F, 0x15, 0x0E, 0x05, 0x1E, 0x04),
    "/": (0x01, 0x02, 0x02, 0x04, 0x08, 0x08, 0x10),
    "(": (0x03, 0x04, 0x08, 0x08, 0x08, 0x04, 0x03),
    ")": (0x18, 0x04, 0x02, 0x02, 0x02, 0x04, 0x18),
    "!": (0x04, 0x04, 0x04, 0x04, 0x04, 0x00, 0x04),
    "?": (0x0E, 0x11, 0x01, 0x04, 0x04, 0x00, 0x04),
    "&": (0x0C, 0x12, 0x14, 0x08, 0x15, 0x12, 0x0D),
    "+": (0x00, 0x04, 0x04, 0x0E, 0x04, 0x04, 0x00),
}

# ---------------------------------------------------------------- colours --
PAPER = (246, 243, 235)   # warm newsprint white
INK = (20, 20, 22)        # near-black
GRAY = (96, 96, 94)       # captions, sources
RULE = (150, 146, 134)    # hairlines
WASH = (228, 224, 212)    # chart fill / panel tint
ACCENT = (150, 30, 30)    # one restrained red: kickers, the falling line

# ------------------------------------------------------------ framebuffer --
fb = bytearray(W * H * 3)


def set_px(x, y, color):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        fb[i] = color[0]
        fb[i + 1] = color[1]
        fb[i + 2] = color[2]


def rect(x, y, w, h, color):
    """Filled rectangle, clipped to the canvas."""
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(W, x + w), min(H, y + h)
    if x1 <= x0 or y1 <= y0:
        return
    row = bytes(color) * (x1 - x0)
    for yy in range(y0, y1):
        i = (yy * W + x0) * 3
        fb[i:i + len(row)] = row


def frame(x, y, w, h, color, t=1):
    """Rectangle outline of thickness t."""
    rect(x, y, w, t, color)
    rect(x, y + h - t, w, t, color)
    rect(x, y, t, h, color)
    rect(x + w - t, y, t, h, color)


def disc(cx, cy, r, color):
    for dy in range(-r, r + 1):
        dx = int((r * r - dy * dy) ** 0.5)
        rect(cx - dx, cy + dy, 2 * dx + 1, 1, color)


def seg(x0, y0, x1, y1, color, t=1):
    """Thick straight segment (Bresenham)."""
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    while True:
        rect(x0, y0, t, t, color)
        if x0 == x1 and y0 == y1:
            return
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def tri(x0, y0, x1, y1, x2, y2, color):
    """Filled triangle via scanline interpolation."""
    (ax, ay), (bx, by), (cx, cy) = sorted(
        ((x0, y0), (x1, y1), (x2, y2)), key=lambda p: p[1])
    if ay == cy:
        return
    for y in range(ay, cy + 1):
        if y < by:
            xa = ax + (bx - ax) * (y - ay) / max(1, by - ay)
            xb = ax + (cx - ax) * (y - ay) / max(1, cy - ay)
        else:
            xa = bx + (cx - bx) * (y - by) / max(1, cy - by)
            xb = ax + (cx - ax) * (y - ay) / max(1, cy - ay)
        lo, hi = int(min(xa, xb)), int(max(xa, xb))
        rect(lo, y, hi - lo + 1, 1, color)


# ------------------------------------------------------------------- text --
def measure(text, scale):
    """Pixel width of a string at the given scale."""
    return len(text) * 6 * scale - scale if text else 0


def put_text(x, y, text, scale, color):
    cx = x
    for ch in text:
        glyph = GLYPHS.get(ch.upper(), GLYPHS[" "])
        for row in range(7):
            bits = glyph[row]
            for col in range(5):
                if bits & (0x10 >> col):
                    rect(cx + col * scale, y + row * scale, scale, scale, color)
        cx += 6 * scale
    return cx


def put_center(cx, y, text, scale, color):
    put_text(cx - measure(text, scale) // 2, y, text, scale, color)


def put_right(x1, y, text, scale, color):
    put_text(x1 - measure(text, scale), y, text, scale, color)


def wrap(text, scale, max_width):
    """Greedy word wrap; returns the list of line strings."""
    lines, cur = [], ""
    for word in text.split(" "):
        trial = word if not cur else cur + " " + word
        if measure(trial, scale) <= max_width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def put_block(x, y, text, scale, max_width, leading, color, max_lines=None):
    """Draw wrapped text; returns the y just past the last line."""
    lines = wrap(text, scale, max_width)
    if max_lines is not None:
        lines = lines[:max_lines]
    for i, ln in enumerate(lines):
        put_text(x, y + i * leading, ln, scale, color)
    return y + len(lines) * leading


# ------------------------------------------------------------- the chart ---
def draw_slump_chart(x, y, w, h):
    """A falling market line for the Wall Street story: pale wash,
    dotted gridlines, one jagged red descent with an arrowhead."""
    rect(x, y, w, h, WASH)
    frame(x, y, w, h, RULE, 1)
    for f in (0.33, 0.66):
        gy = y + int(h * f)
        for gx in range(x + 6, x + w - 4, 10):
            rect(gx, gy, 5, 1, RULE)
    put_text(x + 10, y + 8, "S&P 500", 1, GRAY)
    put_right(x + w - 10, y + 6, "-3.7%", 3, ACCENT)
    pts = [(x + 14, y + 20), (x + 74, y + 27), (x + 134, y + 23),
           (x + 194, y + 40), (x + 254, y + 52), (x + 314, y + 46),
           (x + 374, y + 64), (x + w - 16, y + h - 12)]
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        seg(ax, ay, bx, by, ACCENT, 3)
    ex, ey = pts[-1]
    tri(ex - 4, ey - 14, ex + 12, ey - 2, ex - 10, ey + 4, ACCENT)
    disc(pts[0][0], pts[0][1], 3, INK)


# -------------------------------------------------------------- the page ---
LEFT = 28
RIGHT = 996
COLW = 468          # two-column width
COL2 = 528          # second column x


def masthead():
    frame(10, 10, W - 20, H - 20, INK, 3)
    frame(18, 18, W - 32, H - 32, INK, 1)
    put_center(W // 2, 36, "THE DAILY SIGNAL", 10, INK)
    rect(LEFT, 116, RIGHT - LEFT, 3, INK)
    rect(LEFT, 123, RIGHT - LEFT, 1, INK)
    put_text(LEFT, 132, "VOL. I - NO. 47", 1, GRAY)
    put_center(W // 2, 130, "SATURDAY 21 NOVEMBER 2026", 3, INK)
    put_right(RIGHT, 132, "WORLD EDITION", 1, GRAY)
    rect(LEFT, 156, RIGHT - LEFT, 4, INK)


def lead_story():
    put_text(LEFT, 172, "EUROPE AT WAR - POLAND", 2, ACCENT)
    put_text(LEFT, 196, "MISSILES FALL ON POLAND", 5, INK)
    put_text(LEFT, 244, "IN MASSIVE STRIKE ON UKRAINE", 5, INK)
    put_block(LEFT, 292, "Warsaw calls it a deliberate provocation and "
              "seeks NATO support; the alliance condemns a grave "
              "violation of its airspace.", 2, RIGHT - LEFT, 20, GRAY)
    rect(LEFT, 352, RIGHT - LEFT, 1, RULE)
    put_block(LEFT, 364, "Two Russian missiles and a suspected drone "
              "came down on Polish territory during Moscow's massive "
              "overnight strike on Ukraine, one of the largest air "
              "attacks of the war. The strike hit bridges in Kyiv and "
              "killed at least nine people across the country.",
              2, COLW, 20, INK)
    put_block(COL2, 364, "Ukraine answered by striking the Crimean "
              "Bridge. Poland has formally requested NATO support, and "
              "Denmark has deployed Gripen fighter jets. Warsaw says "
              "the intrusion was a deliberate provocation, not an "
              "accident, and allies are consulting urgently tonight.",
              2, COLW, 20, INK)
    rect(LEFT, 536, RIGHT - LEFT, 2, INK)


def middle_band():
    seg(512, 552, 512, 748, RULE, 1)
    # Left: the ICJ verdict on Myanmar.
    put_text(LEFT, 552, "THE HAGUE - WORLD COURT", 1, ACCENT)
    put_block(LEFT, 572, "ICJ: MYANMAR COMMITTED GENOCIDE AGAINST "
              "THE ROHINGYA PEOPLE", 3, COLW, 27, INK)
    put_block(LEFT, 662, "The International Court of Justice ruled "
              "that Myanmar's forces committed genocide against the "
              "Rohingya, a historic verdict. Myanmar and China "
              "objected to the ruling.", 2, COLW, 19, INK)
    # Right: the Shenzhen trilateral summit.
    put_text(COL2, 552, "SHENZHEN - SUMMIT DIPLOMACY", 1, ACCENT)
    put_block(COL2, 572, "TRUMP, XI AND PUTIN HOLD FIRST TRILATERAL "
              "SUMMIT IN SHENZHEN", 3, COLW, 27, INK)
    put_block(COL2, 662, "The US, Chinese and Russian leaders met "
              "face to face for the first time, but left with few "
              "concrete results. Putin called Trump 'a friend of "
              "mine'; it was not the 'New Yalta' he had envisioned.",
              2, COLW, 19, INK)
    rect(LEFT, 758, RIGHT - LEFT, 2, INK)


def bottom_band():
    seg(512, 774, 512, 918, RULE, 1)
    # Left: Wall Street, with the chart.
    put_text(LEFT, 774, "MARKETS - NEW YORK", 1, ACCENT)
    put_text(LEFT, 792, "WALL STREET SLUMPS 3.7%", 3, INK)
    draw_slump_chart(LEFT, 824, COLW, 76)
    put_text(LEFT, 906, "AI AND CHIP SHARES LEAD THE SELL-OFF; "
             "ANTHROPIC SLIDES", 1, GRAY)
    # Right: UK-EU deals in Brussels.
    put_text(COL2, 774, "BRUSSELS - UK / EU", 1, ACCENT)
    put_block(COL2, 792, "UK AND EU SIGN TRADE AND YOUTH DEALS",
              3, COLW, 27, INK)
    put_block(COL2, 850, "The UK and EU signed deals on food trade, "
              "carbon markets and youth mobility. The EU also paid "
              "Ukraine 7.9 billion euros.", 2, COLW, 18, INK)
    rect(LEFT, 926, RIGHT - LEFT, 2, INK)


def world_briefs():
    cols = [(28, 304), (360, 304), (692, 304)]
    for cx, _ in cols[1:]:
        seg(cx - 16, 940, cx - 16, 998, RULE, 1)
    items = [
        ("MISSILES OVER RIYADH",
         "Saudi-led forces downed Houthi missiles over Riyadh and hit "
         "Hodeidah port, risking a vital aid route. Iran's war nears "
         "month nine; Trump is in no rush on Iran."),
        ("CANCER PILL BREAKTHROUGH",
         "Doctors hail a new pill as a breakthrough for pancreatic "
         "cancer, long one of the hardest cancers to treat."),
        ("CLIMATE TALKS STALL",
         "UN climate talks near crunch time with no deal in sight, "
         "as nations urge pulling carbon from the air."),
    ]
    for (x, w), (head, body) in zip(cols, items):
        put_block(x, 940, head, 2, w, 17, INK, max_lines=1)
        put_block(x, 962, body, 1, w, 10, INK)


def draw_page():
    rect(0, 0, W, H, PAPER)
    masthead()
    lead_story()
    middle_band()
    bottom_band()
    world_briefs()


# ------------------------------------------------------------------- PNG ---
def encode_png():
    def chunk(kind, data):
        return (struct.pack(">I", len(data)) + kind + data
                + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    raw = bytearray()
    stride = W * 3
    for yy in range(H):
        raw.append(0)  # filter: none
        raw.extend(fb[yy * stride:(yy + 1) * stride])
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + chunk(b"IEND", b""))


def main():
    out = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    path = out if out.endswith(".png") else os.path.join(out, "entry.png")
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    draw_page()
    data = encode_png()
    with open(path, "wb") as fh:
        fh.write(data)
    print("wrote %s (%d bytes)" % (path, len(data)))


if __name__ == "__main__":
    main()
