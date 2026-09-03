import json
import math
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter


# ============================================================
# PATHS
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

STORYBOARD = ROOT / "output" / "storyboard.json"
OUTPUT_DIR = ROOT / "output"
ASSETS_DIR = ROOT / "assets"

OUTPUT_DIR.mkdir(exist_ok=True)
ASSETS_DIR.mkdir(exist_ok=True)


# ============================================================
# DEFAULT STYLE
# ============================================================

DEFAULT_STYLE = {
    "background": (248, 248, 246),
    "text": (25, 25, 28),
    "secondary": (100, 100, 105),

    "accent_1": (255, 91, 91),
    "accent_2": (80, 150, 255),
    "accent_3": (255, 190, 70),

    "card": (255, 255, 255),

    "radius": 35,

    "margin": 55,

    "shadow": True
}


# ============================================================
# FONTS
# ============================================================

def find_font(size, bold=False):

    candidates = []

    if os.name == "nt":

        if bold:
            candidates += [
                r"C:\Windows\Fonts\arialbd.ttf",
                r"C:\Windows\Fonts\segoeuib.ttf",
                r"C:\Windows\Fonts\calibrib.ttf",
            ]

        candidates += [
            r"C:\Windows\Fonts\arial.ttf",
            r"C:\Windows\Fonts\segoeui.ttf",
        ]

    candidates += [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    ]

    for path in candidates:

        if os.path.exists(path):
            return ImageFont.truetype(path, size)

    return ImageFont.load_default()


# ============================================================
# EASING
# ============================================================

def ease_out(t):

    t = max(0.0, min(1.0, t))

    return 1 - pow(1 - t, 3)


def ease_in_out(t):

    t = max(0.0, min(1.0, t))

    return (
        2 * t * t
        if t < 0.5
        else 1 - pow(-2 * t + 2, 2) / 2
    )


def clamp(value, minimum, maximum):

    return max(
        minimum,
        min(value, maximum)
    )


# ============================================================
# TEXT WRAPPING
# ============================================================

def wrap_text(draw, text, font, max_width):

    words = text.split()

    lines = []
    current = ""

    for word in words:

        test = (
            word
            if not current
            else current + " " + word
        )

        bbox = draw.textbbox(
            (0, 0),
            test,
            font=font
        )

        width = bbox[2] - bbox[0]

        if width <= max_width:

            current = test

        else:

            if current:
                lines.append(current)

            current = word

    if current:
        lines.append(current)

    return lines


# ============================================================
# CENTERED TEXT
# ============================================================

def draw_centered_text(
    draw,
    text,
    font,
    x,
    y,
    max_width,
    fill,
    spacing=10
):

    lines = wrap_text(
        draw,
        text,
        font,
        max_width
    )

    heights = []

    for line in lines:

        bbox = draw.textbbox(
            (0, 0),
            line,
            font=font
        )

        heights.append(
            bbox[3] - bbox[1]
        )

    total_height = (
        sum(heights)
        + spacing * (len(lines) - 1)
    )

    current_y = y - total_height / 2

    for line, height in zip(lines, heights):

        bbox = draw.textbbox(
            (0, 0),
            line,
            font=font
        )

        width = bbox[2] - bbox[0]

        draw.text(
            (
                x - width / 2,
                current_y
            ),
            line,
            font=font,
            fill=fill
        )

        current_y += height + spacing


# ============================================================
# SHADOWED ROUNDED RECTANGLE
# ============================================================

def rounded_card(
    image,
    box,
    radius,
    fill,
    shadow=True
):

    if shadow:

        shadow_layer = Image.new(
            "RGBA",
            image.size,
            (0, 0, 0, 0)
        )

        shadow_draw = ImageDraw.Draw(
            shadow_layer
        )

        x1, y1, x2, y2 = box

        shadow_draw.rounded_rectangle(
            (
                x1 + 0,
                y1 + 12,
                x2 + 0,
                y2 + 12
            ),
            radius=radius,
            fill=(0, 0, 0, 35)
        )

        shadow_layer = shadow_layer.filter(
            ImageFilter.GaussianBlur(12)
        )

        image.alpha_composite(
            shadow_layer
        )

    draw = ImageDraw.Draw(image)

    draw.rounded_rectangle(
        box,
        radius=radius,
        fill=fill
    )


# ============================================================
# BACKGROUND
# ============================================================

def create_background(
    width,
    height
):

    image = Image.new(
        "RGBA",
        (width, height),
        DEFAULT_STYLE["background"] + (255,)
    )

    return image


# ============================================================
# DECORATIVE SHAPES
# ============================================================

def draw_background_shapes(
    image,
    scene_index
):

    draw = ImageDraw.Draw(image)

    width, height = image.size

    accent_colors = [
        DEFAULT_STYLE["accent_1"],
        DEFAULT_STYLE["accent_2"],
        DEFAULT_STYLE["accent_3"]
    ]

    color_a = accent_colors[
        scene_index % len(accent_colors)
    ]

    color_b = accent_colors[
        (scene_index + 1)
        % len(accent_colors)
    ]

    # Small floating circle
    draw.ellipse(
        (
            width - 150,
            90,
            width - 75,
            165
        ),
        fill=color_a + (55,)
    )

    # Large subtle circle
    draw.ellipse(
        (
            -140,
            height - 310,
            130,
            height - 40
        ),
        fill=color_b + (30,)
    )


# ============================================================
# KINETIC TYPOGRAPHY
# ============================================================

def render_kinetic_typography(
    image,
    sentence,
    progress
):

    draw = ImageDraw.Draw(image)

    width, height = image.size

    font_size = int(width * 0.105)

    font = find_font(
        font_size,
        bold=True
    )

    progress = ease_out(progress)

    # Slide upward.
    y = (
        height * 0.50
        + (1 - progress) * 90
    )

    opacity = int(
        clamp(progress, 0, 1) * 255
    )

    text_layer = Image.new(
        "RGBA",
        image.size,
        (0, 0, 0, 0)
    )

    text_draw = ImageDraw.Draw(
        text_layer
    )

    lines = wrap_text(
        text_draw,
        sentence,
        font,
        width - 100
    )

    line_heights = []

    for line in lines:

        bbox = text_draw.textbbox(
            (0, 0),
            line,
            font=font
        )

        line_heights.append(
            bbox[3] - bbox[1]
        )

    total_height = sum(
        line_heights
    ) + (len(lines) - 1) * 12

    current_y = y - total_height / 2

    for line, line_height in zip(
        lines,
        line_heights
    ):

        bbox = text_draw.textbbox(
            (0, 0),
            line,
            font=font
        )

        line_width = (
            bbox[2] - bbox[0]
        )

        text_draw.text(
            (
                (width - line_width) / 2,
                current_y
            ),
            line,
            font=font,
            fill=DEFAULT_STYLE["text"]
            + (opacity,)
        )

        current_y += line_height + 12

    image.alpha_composite(
        text_layer
    )


# ============================================================
# NORMAL TEXT CARD
# ============================================================

def render_text_card(
    image,
    sentence,
    progress
):

    width, height = image.size

    progress = ease_out(progress)

    card_width = width - 90
    card_height = int(height * 0.48)

    x1 = 45
    x2 = x1 + card_width

    target_y = (
        height * 0.50
        - card_height / 2
    )

    y = target_y + (
        90 * (1 - progress)
    )

    rounded_card(
        image,
        (
            x1,
            int(y),
            x2,
            int(y + card_height)
        ),
        DEFAULT_STYLE["radius"],
        DEFAULT_STYLE["card"] + (255,),
        DEFAULT_STYLE["shadow"]
    )

    draw = ImageDraw.Draw(image)

    font = find_font(
        int(width * 0.065),
        bold=True
    )

    draw_centered_text(
        draw,
        sentence,
        font,
        width / 2,
        y + card_height / 2,
        card_width - 80,
        DEFAULT_STYLE["text"]
    )


# ============================================================
# STATISTIC
# ============================================================

def render_statistic(
    image,
    sentence,
    progress
):

    width, height = image.size

    draw = ImageDraw.Draw(image)

    progress = ease_out(progress)

    # Find first number.
    import re

    match = re.search(
        r"\d+(?:\.\d+)?%?",
        sentence
    )

    number = (
        match.group(0)
        if match
        else "?"
    )

    number_font = find_font(
        int(width * 0.19),
        bold=True
    )

    text_font = find_font(
        int(width * 0.055),
        bold=True
    )

    scale = 0.75 + (
        0.25 * progress
    )

    number_y = (
        height * 0.38
    )

    bbox = draw.textbbox(
        (0, 0),
        number,
        font=number_font
    )

    number_width = (
        bbox[2] - bbox[0]
    )

    draw.text(
        (
            width / 2 - number_width / 2,
            number_y
        ),
        number,
        font=number_font,
        fill=DEFAULT_STYLE["accent_2"]
    )

    remaining = sentence.replace(
        number,
        ""
    ).strip()

    draw_centered_text(
        draw,
        remaining,
        text_font,
        width / 2,
        height * 0.57,
        width - 100,
        DEFAULT_STYLE["text"]
    )


# ============================================================
# COMPARISON CARDS
# ============================================================

def render_comparison(
    image,
    sentence,
    progress
):

    width, height = image.size

    progress = ease_out(progress)

    draw = ImageDraw.Draw(image)

    gap = 22

    card_width = (
        width - 90 - gap
    ) / 2

    card_height = 300

    y = (
        height * 0.5
        - card_height / 2
    )

    left_x = (
        45
        - 100 * (1 - progress)
    )

    right_x = (
        width / 2
        + gap / 2
        + 100 * (1 - progress)
    )

    rounded_card(
        image,
        (
            int(left_x),
            int(y),
            int(left_x + card_width),
            int(y + card_height)
        ),
        30,
        DEFAULT_STYLE["card"] + (255,)
    )

    rounded_card(
        image,
        (
            int(right_x),
            int(y),
            int(right_x + card_width),
            int(y + card_height)
        ),
        30,
        DEFAULT_STYLE["card"] + (255,)
    )

    font = find_font(
        int(width * 0.048),
        bold=True
    )

    draw_centered_text(
        draw,
        "BEFORE",
        font,
        left_x + card_width / 2,
        y + card_height / 2,
        card_width - 30,
        DEFAULT_STYLE["accent_1"]
    )

    draw_centered_text(
        draw,
        "AFTER",
        font,
        right_x + card_width / 2,
        y + card_height / 2,
        card_width - 30,
        DEFAULT_STYLE["accent_2"]
    )


# ============================================================
# DIAGRAM
# ============================================================

def render_diagram(
    image,
    sentence,
    progress
):

    width, height = image.size

    draw = ImageDraw.Draw(image)

    progress = ease_in_out(progress)

    center_x = width / 2

    center_y = height / 2

    node_radius = 48

    positions = [
        (
            center_x,
            center_y - 180
        ),
        (
            center_x - 130,
            center_y + 100
        ),
        (
            center_x + 130,
            center_y + 100
        )
    ]

    colors = [
        DEFAULT_STYLE["accent_1"],
        DEFAULT_STYLE["accent_2"],
        DEFAULT_STYLE["accent_3"]
    ]

    # Connections
    for i in [1, 2]:

        x1, y1 = positions[0]
        x2, y2 = positions[i]

        draw.line(
            (
                x1,
                y1,
                x2,
                y2
            ),
            fill=DEFAULT_STYLE["secondary"],
            width=8
        )

    # Nodes
    for i, (x, y) in enumerate(
        positions
    ):

        current_radius = (
            node_radius
            * (
                0.5
                + 0.5 * progress
            )
        )

        draw.ellipse(
            (
                x - current_radius,
                y - current_radius,
                x + current_radius,
                y + current_radius
            ),
            fill=colors[i] + (255,)
        )

    font = find_font(
        int(width * 0.047),
        bold=True
    )

    draw_centered_text(
        draw,
        sentence,
        font,
        center_x,
        height * 0.78,
        width - 100,
        DEFAULT_STYLE["text"]
    )


# ============================================================
# MOTION GRAPHIC
# ============================================================

def render_motion_graphic(
    image,
    sentence,
    progress,
    scene_index
):

    width, height = image.size

    draw = ImageDraw.Draw(image)

    progress = ease_in_out(progress)

    colors = [
        DEFAULT_STYLE["accent_1"],
        DEFAULT_STYLE["accent_2"],
        DEFAULT_STYLE["accent_3"]
    ]

    c1 = colors[
        scene_index % 3
    ]

    c2 = colors[
        (scene_index + 1) % 3
    ]

    center_x = width / 2
    center_y = height / 2

    radius = (
        100
        + 70 * math.sin(
            progress * math.pi
        )
    )

    draw.ellipse(
        (
            center_x - radius,
            center_y - radius,
            center_x + radius,
            center_y + radius
        ),
        fill=c1 + (220,)
    )

    second_x = (
        center_x
        + math.sin(
            progress * math.pi * 2
        ) * 100
    )

    second_y = (
        center_y
        + math.cos(
            progress * math.pi * 2
        ) * 100
    )

    draw.rounded_rectangle(
        (
            second_x - 60,
            second_y - 60,
            second_x + 60,
            second_y + 60
        ),
        radius=25,
        fill=c2 + (230,)
    )

    font = find_font(
        int(width * 0.055),
        bold=True
    )

    draw_centered_text(
        draw,
        sentence,
        font,
        width / 2,
        height * 0.78,
        width - 90,
        DEFAULT_STYLE["text"]
    )


# ============================================================
# IMAGE + GRAPHICS
# ============================================================

def find_asset(search_terms):

    if not search_terms:
        return None

    files = []

    for extension in [
        "*.png",
        "*.jpg",
        "*.jpeg",
        "*.webp"
    ]:

        files.extend(
            ASSETS_DIR.glob(extension)
        )

    if not files:
        return None

    # Basic filename matching.
    for term in search_terms:

        term = term.lower()

        for file in files:

            if term in file.stem.lower():
                return file

    return files[0]


def render_image_scene(
    image,
    sentence,
    scene,
    progress
):

    width, height = image.size

    progress = ease_out(progress)

    asset = find_asset(
        scene["visual"].get(
            "asset_search_terms",
            []
        )
    )

    if asset:

        try:

            photo = Image.open(
                asset
            ).convert("RGBA")

            target_width = int(
                width * 0.82
            )

            ratio = (
                target_width
                / photo.width
            )

            target_height = int(
                photo.height * ratio
            )

            photo = photo.resize(
                (
                    target_width,
                    target_height
                ),
                Image.Resampling.LANCZOS
            )

            x = int(
                (width - target_width) / 2
            )

            target_y = int(
                height * 0.30
            )

            y = int(
                target_y
                + 80 * (1 - progress)
            )

            image.alpha_composite(
                photo,
                (
                    x,
                    y
                )
            )

        except Exception:
            pass

    # Always keep text as part of the designed composition.
    draw = ImageDraw.Draw(image)

    font = find_font(
        int(width * 0.052),
        bold=True
    )

    draw_centered_text(
        draw,
        sentence,
        font,
        width / 2,
        height * 0.80,
        width - 90,
        DEFAULT_STYLE["text"]
    )


# ============================================================
# SCENE RENDER
# ============================================================

def render_scene(
    scene,
    scene_index,
    local_progress,
    width,
    height
):

    image = create_background(
        width,
        height
    )

    draw_background_shapes(
        image,
        scene_index
    )

    sentence = scene.get(
        "narration",
        ""
    )

    visual_type = (
        scene
        .get("visual", {})
        .get("type", "motion_graphic")
    )

    if visual_type == "kinetic_typography":

        render_kinetic_typography(
            image,
            sentence,
            local_progress
        )

    elif visual_type == "data_graphic":

        render_statistic(
            image,
            sentence,
            local_progress
        )

    elif visual_type == "comparison_cards":

        render_comparison(
            image,
            sentence,
            local_progress
        )

    elif visual_type == "diagram":

        render_diagram(
            image,
            sentence,
            local_progress
        )

    elif visual_type == "image_plus_graphics":

        render_image_scene(
            image,
            sentence,
            scene,
            local_progress
        )

    else:

        render_motion_graphic(
            image,
            sentence,
            local_progress,
            scene_index
        )

    return image.convert("RGB")


# ============================================================
# LOAD STORYBOARD
# ============================================================

def load_storyboard():

    if not STORYBOARD.exists():

        raise FileNotFoundError(
            f"\nStoryboard not found:\n"
            f"{STORYBOARD}\n\n"
            f"Run:\n"
            f"python generator\\scene_planner.py"
        )

    with open(
        STORYBOARD,
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)


# ============================================================
# FIND FFMPEG
# ============================================================

def find_ffmpeg():

    ffmpeg = shutil.which(
        "ffmpeg"
    )

    if ffmpeg:
        return ffmpeg

    windows_path = (
        r"C:\ffmpeg\bin\ffmpeg.exe"
    )

    if os.path.exists(
        windows_path
    ):
        return windows_path

    raise RuntimeError(
        "FFmpeg was not found.\n"
        "Make sure ffmpeg is installed "
        "and available in PATH."
    )


# ============================================================
# RENDER VIDEO
# ============================================================

def render_video():

    storyboard = load_storyboard()

    canvas = storyboard.get(
        "canvas",
        {}
    )

    width = int(
        canvas.get(
            "width",
            576
        )
    )

    height = int(
        canvas.get(
            "height",
            1024
        )
    )

    fps = float(
        canvas.get(
            "fps",
            30
        )
    )

    # Keep FPS reasonable.
    if fps < 20 or fps > 60:
        fps = 30

    scenes = storyboard.get(
        "scenes",
        []
    )

    if not scenes:

        raise ValueError(
            "Storyboard contains no scenes."
        )

    ffmpeg = find_ffmpeg()

    temp_dir = Path(
        tempfile.mkdtemp(
            prefix="motion_ai_"
        )
    )

    print()
    print("=" * 70)
    print("MOTION AI — DETERMINISTIC RENDERER")
    print("=" * 70)
    print()

    print(
        f"Canvas: {width}x{height}"
    )

    print(
        f"FPS: {fps}"
    )

    print(
        f"Scenes: {len(scenes)}"
    )

    print()

    frame_number = 0

    try:

        for scene_index, scene in enumerate(
            scenes
        ):

            duration = float(
                scene.get(
                    "duration",
                    2
                )
            )

            scene_frames = max(
                1,
                int(
                    round(
                        duration * fps
                    )
                )
            )

            print(
                f"Rendering scene "
                f"{scene_index + 1}/"
                f"{len(scenes)}..."
            )

            for local_frame in range(
                scene_frames
            ):

                if scene_frames == 1:

                    progress = 1.0

                else:

                    progress = (
                        local_frame
                        / (scene_frames - 1)
                    )

                frame = render_scene(
                    scene,
                    scene_index,
                    progress,
                    width,
                    height
                )

                frame_path = (
                    temp_dir
                    / f"frame_{frame_number:07d}.png"
                )

                frame.save(
                    frame_path,
                    "PNG"
                )

                frame_number += 1

        output_path = (
            OUTPUT_DIR
            / "final_video.mp4"
        )

        print()
        print(
            f"Encoding {frame_number} frames..."
        )

        command = [
            ffmpeg,

            "-y",

            "-framerate",
            str(fps),

            "-i",
            str(
                temp_dir
                / "frame_%07d.png"
            ),

            "-c:v",
            "libx264",

            "-preset",
            "medium",

            "-crf",
            "18",

            "-pix_fmt",
            "yuv420p",

            "-movflags",
            "+faststart",

            str(output_path)
        ]

        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if result.returncode != 0:

            print(
                result.stderr
            )

            raise RuntimeError(
                "FFmpeg encoding failed."
            )

        print()
        print("=" * 70)
        print("VIDEO CREATED")
        print("=" * 70)
        print()
        print(
            f"Output:\n{output_path}"
        )
        print()
        print(
            f"Frames: {frame_number}"
        )
        print(
            f"FPS: {fps}"
        )
        print(
            f"Resolution: {width}x{height}"
        )
        print()

        return output_path

    finally:

        shutil.rmtree(
            temp_dir,
            ignore_errors=True
        )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    try:

        render_video()

    except Exception as e:

        print()
        print("ERROR:")
        print(e)
        print()