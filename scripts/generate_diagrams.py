"""Generate submission-ready PNG diagrams directly (no SVG intermediate)."""

from __future__ import annotations

from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError as exc:  # pragma: no cover - helper-only dependency
    raise SystemExit("Pillow is required: python -m pip install pillow") from exc

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
WIDTH, HEIGHT = 1600, 900
BG = "#07111f"
PANEL = "#10233a"
PANEL_2 = "#15304c"
INK = "#eef7ff"
MUTED = "#9cb3c9"
ACCENT = "#56d6c9"
ORANGE = "#ffb36b"
RED = "#ff7f87"


def font(size: int, *, bold: bool = False) -> ImageFont.ImageFont:
    candidates = [
        Path("C:/Windows/Fonts/seguisb.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf"),
        Path(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            if bold
            else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        ),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def rounded(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    fill: str,
    outline: str = ACCENT,
) -> None:
    draw.rounded_rectangle(box, radius=24, fill=fill, outline=outline, width=3)


def centered(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    text: str,
    *,
    size: int,
    color: str = INK,
    bold: bool = False,
) -> None:
    face = font(size, bold=bold)
    left, top, right, bottom = draw.multiline_textbbox(
        (0, 0), text, font=face, spacing=8, align="center"
    )
    width, height = right - left, bottom - top
    x = box[0] + (box[2] - box[0] - width) / 2
    y = box[1] + (box[3] - box[1] - height) / 2
    draw.multiline_text((x, y), text, font=face, fill=color, spacing=8, align="center")


def arrow(
    draw: ImageDraw.ImageDraw,
    start: tuple[int, int],
    end: tuple[int, int],
    color: str = ACCENT,
) -> None:
    draw.line((start, end), fill=color, width=6)
    x, y = end
    draw.polygon(((x, y), (x - 18, y - 12), (x - 18, y + 12)), fill=color)


def architecture() -> None:
    image = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(image)
    draw.text((70, 45), "Acheon context compilation", font=font(48, bold=True), fill=INK)
    draw.text(
        (72, 108),
        "A deterministic, inspectable layer around the model",
        font=font(25),
        fill=MUTED,
    )
    boxes = [
        (70, 260, 310, 520),
        (390, 260, 630, 520),
        (710, 260, 950, 520),
        (1030, 260, 1270, 520),
        (1350, 260, 1560, 520),
    ]
    labels = [
        "Typed records\n\nscope · source\nlifecycle · links",
        "Versioned store\n\nSQLite revisions\nhash audit chain",
        "Selection\n\ngates · rank fusion\nlinks · diversity",
        "Context packet\n\nestimated budget\nreasons · digest",
        "Runtime\n\noffline preview\nor GPT-5.6",
    ]
    colors = [PANEL, PANEL, PANEL_2, PANEL_2, PANEL]
    for box, label, color in zip(boxes, labels, colors, strict=True):
        rounded(draw, box, color)
        centered(draw, box, label, size=26, bold=True)
    for left, right in zip(boxes, boxes[1:], strict=False):
        arrow(draw, (left[2] + 10, 390), (right[0] - 16, 390))
    footer = (150, 650, 1450, 800)
    rounded(draw, footer, "#0d1d30", outline=ORANGE)
    centered(
        draw,
        footer,
        (
            "Boundary: application-level context use — no weight changes,\n"
            "no expanded provider window, no hidden claim of permanent model memory"
        ),
        size=27,
        color=ORANGE,
        bold=True,
    )
    image.save(DOCS / "architecture.png", optimize=True)


def evaluation_loop() -> None:
    image = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(image)
    draw.text((70, 45), "Evidence before adjectives", font=font(48, bold=True), fill=INK)
    draw.text(
        (72, 108),
        "Equal budget · fixed seeds · absolute metrics · every failure",
        font=font(25),
        fill=MUTED,
    )
    rows = [
        ((100, 230, 460, 390), "Frozen cases\nGold relevant + forbidden", ACCENT),
        ((620, 230, 980, 390), "Four strategies\n3 baselines + Acheon", ACCENT),
        ((1140, 230, 1500, 390), "Paired metrics\nRecall · precision · safety", ACCENT),
        ((1140, 570, 1500, 730), "Evidence label\nverified · observed · open", ORANGE),
        ((620, 570, 980, 730), "Ablations + failures\nMachine-readable artifact", ORANGE),
        ((100, 570, 460, 730), "Reproduce\nTests · benchmark · verify", ORANGE),
    ]
    for box, label, outline in rows:
        rounded(draw, box, PANEL if outline == ACCENT else PANEL_2, outline=outline)
        centered(draw, box, label, size=27, bold=True)
    arrow(draw, (470, 310), (604, 310))
    arrow(draw, (990, 310), (1124, 310))
    draw.line((1320, 400, 1320, 550), fill=ORANGE, width=6)
    draw.polygon(((1320, 560), (1308, 540), (1332, 540)), fill=ORANGE)
    arrow(draw, (1130, 650), (996, 650), color=ORANGE)
    arrow(draw, (610, 650), (476, 650), color=ORANGE)
    draw.text(
        (430, 810),
        "Synthetic selection evidence is not a model-intelligence claim.",
        font=font(29, bold=True),
        fill=RED,
    )
    image.save(DOCS / "evaluation-loop.png", optimize=True)


def main() -> None:
    DOCS.mkdir(parents=True, exist_ok=True)
    architecture()
    evaluation_loop()
    print("generated docs/architecture.png and docs/evaluation-loop.png")


if __name__ == "__main__":
    main()
