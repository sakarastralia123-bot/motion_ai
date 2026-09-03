import os
import json
import math
import subprocess

import cv2
import numpy as np

from PIL import Image, ImageDraw, ImageFont


# ============================================================
# PROJECT PATHS
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

INPUT_VIDEO = os.path.join(
    BASE_DIR,
    "input",
    "videos",
    "Video.mp4"
)

PLAN_FILE = os.path.join(
    BASE_DIR,
    "output",
    "smart_graphics_plan.json"
)

OUTPUT_DIR = os.path.join(
    BASE_DIR,
    "output"
)

TEMP_VIDEO = os.path.join(
    OUTPUT_DIR,
    "_graphics_video.mp4"
)

FINAL_VIDEO = os.path.join(
    OUTPUT_DIR,
    "enhanced_video.mp4"
)


# ============================================================
# SETTINGS
# ============================================================

MAX_GRAPHICS = 18

SAFE_MARGIN = 50

# Style learned approximately from your 4 reference videos.
ACCENT = (255, 112, 80)
DARK = (51, 25, 68)
WHITE = (255, 255, 255)
GRAY = (110, 110, 110)

FONT_PATHS = [
    r"C:\Windows\Fonts\arialbd.ttf",
    r"C:\Windows\Fonts\segoeuib.ttf",
    r"C:\Windows\Fonts\calibrib.ttf",
]


# ============================================================
# FONT
# ============================================================

def get_font(size):

    for path in FONT_PATHS:

        if os.path.exists(path):

            return ImageFont.truetype(
                path,
                size
            )

    return ImageFont.load_default()


# ============================================================
# JSON
# ============================================================

def load_json(path):

    if not os.path.exists(path):

        raise FileNotFoundError(
            f"File not found:\n{path}"
        )

    with open(
        path,
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)


# ============================================================
# EASING FUNCTIONS
# ============================================================

def ease_out(t):

    t = max(
        0.0,
        min(
            1.0,
            t
        )
    )

    return 1 - pow(
        1 - t,
        3
    )


def ease_in(t):

    t = max(
        0.0,
        min(
            1.0,
            t
        )
    )

    return t * t * t


def smoothstep(t):

    t = max(
        0.0,
        min(
            1.0,
            t
        )
    )

    return (
        t
        * t
        * (3 - 2 * t)
    )


# ============================================================
# ANIMATION PROGRESS
# ============================================================

def animation_progress(
    current_time,
    start,
    end,
    animation_duration=0.35
):

    duration = max(
        0.01,
        end - start
    )

    elapsed = (
        current_time
        - start
    )

    if elapsed < animation_duration:

        p = (
            elapsed
            / animation_duration
        )

        return (
            ease_out(p),
            1.0
        )

    remaining = (
        end
        - current_time
    )

    if remaining < animation_duration:

        p = (
            remaining
            / animation_duration
        )

        return (
            1.0,
            ease_in(p)
        )

    return (
        1.0,
        1.0
    )


# ============================================================
# TEXT SIZE
# ============================================================

def text_size(
    draw,
    text,
    font
):

    box = draw.textbbox(
        (0, 0),
        text,
        font=font
    )

    return (
        box[2] - box[0],
        box[3] - box[1]
    )


# ============================================================
# ROUNDED RECTANGLE
# ============================================================

def rounded_rectangle(
    draw,
    box,
    radius,
    fill,
    outline=None,
    width=1
):

    draw.rounded_rectangle(
        box,
        radius=radius,
        fill=fill,
        outline=outline,
        width=width
    )


# ============================================================
# POSITION
# ============================================================

def get_position(
    position,
    width,
    height,
    box_w,
    box_h
):

    position = str(
        position
    ).lower().strip()

    margin = SAFE_MARGIN

    positions = {

        "upper_left": (
            margin,
            int(height * 0.12)
        ),

        "upper_right": (
            width - box_w - margin,
            int(height * 0.12)
        ),

        "middle_left": (
            margin,
            int(
                (height - box_h)
                / 2
            )
        ),

        "middle_right": (
            width - box_w - margin,
            int(
                (height - box_h)
                / 2
            )
        ),

        "center": (
            int(
                (width - box_w)
                / 2
            ),
            int(
                (height - box_h)
                / 2
            )
        ),

        "bottom_left": (
            margin,
            height - box_h - margin
        ),

        "bottom_right": (
            width - box_w - margin,
            height - box_h - margin
        ),

        "bottom": (
            int(
                (width - box_w)
                / 2
            ),
            height - box_h - margin
        )
    }

    return positions.get(
        position,
        positions["upper_right"]
    )


# ============================================================
# HEADLINE
# ============================================================

def draw_headline(
    image,
    graphic,
    progress,
    opacity
):

    draw = ImageDraw.Draw(
        image
    )

    width, height = image.size

    text = str(
        graphic.get(
            "text",
            ""
        )
    ).strip()

    if not text:

        return

    text = text.upper()

    font_size = max(
        42,
        min(
            86,
            int(
                width * 0.045
            )
        )
    )

    font = get_font(
        font_size
    )

    tw, th = text_size(
        draw,
        text,
        font
    )

    padding_x = 34
    padding_y = 22

    box_w = (
        tw
        + padding_x * 2
    )

    box_h = (
        th
        + padding_y * 2
    )

    x, y = get_position(
        graphic.get(
            "position",
            "upper_right"
        ),
        width,
        height,
        box_w,
        box_h
    )

    # Slide in.
    offset_y = int(
        40
        * (1 - progress)
    )

    x += int(
        10
        * (1 - progress)
    )

    y += offset_y

    layer = Image.new(
        "RGBA",
        image.size,
        (0, 0, 0, 0)
    )

    ld = ImageDraw.Draw(
        layer
    )

    # Shadow.
    rounded_rectangle(
        ld,
        (
            x + 8,
            y + 10,
            x + box_w + 8,
            y + box_h + 10
        ),
        24,
        (
            0,
            0,
            0,
            int(
                55 * opacity
            )
        )
    )

    # Card.
    rounded_rectangle(
        ld,
        (
            x,
            y,
            x + box_w,
            y + box_h
        ),
        24,
        (
            *WHITE,
            int(
                235 * opacity
            )
        )
    )

    # Accent bar.
    ld.rounded_rectangle(
        (
            x,
            y,
            x + 10,
            y + box_h
        ),
        radius=5,
        fill=(
            *ACCENT,
            int(
                255 * opacity
            )
        )
    )

    # Text.
    ld.text(
        (
            x
            + padding_x
            + 4,
            y
            + padding_y
        ),
        text,
        font=font,
        fill=(
            *DARK,
            int(
                255 * opacity
            )
        )
    )

    image.alpha_composite(
        layer
    )


# ============================================================
# KEYWORD
# ============================================================

def draw_keyword(
    image,
    graphic,
    progress,
    opacity
):

    draw = ImageDraw.Draw(
        image
    )

    width, height = image.size

    text = str(
        graphic.get(
            "text",
            ""
        )
    ).strip()

    if not text:

        return

    text = text.upper()

    font = get_font(
        max(
            48,
            min(
                100,
                int(
                    width * 0.055
                )
            )
        )
    )

    tw, th = text_size(
        draw,
        text,
        font
    )

    padding_x = 40
    padding_y = 24

    box_w = (
        tw
        + padding_x * 2
    )

    box_h = (
        th
        + padding_y * 2
    )

    x, y = get_position(
        graphic.get(
            "position",
            "middle_right"
        ),
        width,
        height,
        box_w,
        box_h
    )

    scale = (
        0.75
        + 0.25 * progress
    )

    center_x = (
        x
        + box_w / 2
    )

    center_y = (
        y
        + box_h / 2
    )

    scaled_w = int(
        box_w * scale
    )

    scaled_h = int(
        box_h * scale
    )

    x = int(
        center_x
        - scaled_w / 2
    )

    y = int(
        center_y
        - scaled_h / 2
    )

    layer = Image.new(
        "RGBA",
        image.size,
        (0, 0, 0, 0)
    )

    ld = ImageDraw.Draw(
        layer
    )

    rounded_rectangle(
        ld,
        (
            x,
            y,
            x + scaled_w,
            y + scaled_h
        ),
        30,
        (
            *ACCENT,
            int(
                235 * opacity
            )
        )
    )

    tw2, th2 = text_size(
        ld,
        text,
        font
    )

    ld.text(
        (
            x
            + (scaled_w - tw2) / 2,
            y
            + (scaled_h - th2) / 2
            - 4
        ),
        text,
        font=font,
        fill=(
            *WHITE,
            int(
                255 * opacity
            )
        )
    )

    image.alpha_composite(
        layer
    )


# ============================================================
# PROCESS FLOW
# ============================================================

def draw_process_flow(
    image,
    graphic,
    progress,
    opacity
):

    width, height = image.size

    concept = str(
        graphic.get(
            "text",
            ""
        )
    ).strip()

    if not concept:

        concept = "PROCESS"

    concept = concept.upper()

    center_y = int(
        height * 0.52
    )

    start_x = int(
        width * 0.58
    )

    gap = int(
        width * 0.10
    )

    radius = int(
        min(
            width,
            height
        )
        * 0.035
    )

    layer = Image.new(
        "RGBA",
        image.size,
        (0, 0, 0, 0)
    )

    ld = ImageDraw.Draw(
        layer
    )

    # Connection line.
    line_start = start_x

    line_end = (
        start_x
        + gap * 2
    )

    animated_end = (
        line_start
        + int(
            (
                line_end
                - line_start
            )
            * progress
        )
    )

    ld.line(
        (
            line_start,
            center_y,
            animated_end,
            center_y
        ),
        fill=(
            *ACCENT,
            int(
                230 * opacity
            )
        ),
        width=max(
            5,
            int(
                width * 0.006
            )
        )
    )

    # Three nodes.
    for i in range(3):

        cx = (
            start_x
            + gap * i
        )

        local_progress = max(
            0,
            min(
                1,
                progress * 3
                - i
            )
        )

        local_progress = ease_out(
            local_progress
        )

        r = int(
            radius
            * (
                0.4
                + 0.6
                * local_progress
            )
        )

        ld.ellipse(
            (
                cx - r,
                center_y - r,
                cx + r,
                center_y + r
            ),
            fill=(
                *ACCENT,
                int(
                    240 * opacity
                )
            )
        )

        number = str(
            i + 1
        )

        f = get_font(
            max(
                24,
                int(
                    radius * 0.9
                )
            )
        )

        tw, th = text_size(
            ld,
            number,
            f
        )

        ld.text(
            (
                cx - tw / 2,
                center_y
                - th / 2
                - 3
            ),
            number,
            font=f,
            fill=(
                *WHITE,
                int(
                    255 * opacity
                )
            )
        )

    # Label.
    label_font = get_font(
        max(
            30,
            int(
                width * 0.026
            )
        )
    )

    tw, th = text_size(
        ld,
        concept,
        label_font
    )

    label_x = (
        start_x
        + gap
        - tw / 2
    )

    label_y = (
        center_y
        + radius
        + 28
    )

    ld.text(
        (
            label_x,
            label_y
        ),
        concept,
        font=label_font,
        fill=(
            *WHITE,
            int(
                255 * opacity
            )
        ),
        stroke_width=2,
        stroke_fill=(
            *DARK,
            int(
                180 * opacity
            )
        )
    )

    image.alpha_composite(
        layer
    )


# ============================================================
# CONCEPT CLUSTER
# ============================================================

def draw_concept_cluster(
    image,
    graphic,
    progress,
    opacity
):

    width, height = image.size

    layer = Image.new(
        "RGBA",
        image.size,
        (0, 0, 0, 0)
    )

    ld = ImageDraw.Draw(
        layer
    )

    center_x = int(
        width * 0.72
    )

    center_y = int(
        height * 0.50
    )

    center_radius = int(
        min(
            width,
            height
        )
        * 0.055
    )

    r = int(
        center_radius
        * (
            0.75
            + 0.25 * progress
        )
    )

    ld.ellipse(
        (
            center_x - r,
            center_y - r,
            center_x + r,
            center_y + r
        ),
        fill=(
            *ACCENT,
            int(
                235 * opacity
            )
        )
    )

    font = get_font(
        max(
            26,
            int(
                width * 0.022
            )
        )
    )

    center_text = str(
        graphic.get(
            "text",
            "IDEA"
        )
    ).upper()

    tw, th = text_size(
        ld,
        center_text,
        font
    )

    ld.text(
        (
            center_x
            - tw / 2,
            center_y
            - th / 2
        ),
        center_text,
        font=font,
        fill=(
            *WHITE,
            int(
                255 * opacity
            )
        )
    )

    labels = [
        "IDEA",
        "PLAN",
        "EVIDENCE",
        "RESULT"
    ]

    distance = int(
        min(
            width,
            height
        )
        * 0.15
    )

    for i, label in enumerate(
        labels
    ):

        angle = (
            i
            * math.pi
            / 2
        ) - math.pi / 4

        local_progress = max(
            0,
            min(
                1,
                progress * 2
                - i * 0.18
            )
        )

        local_progress = ease_out(
            local_progress
        )

        cx = int(
            center_x
            + math.cos(angle)
            * distance
            * local_progress
        )

        cy = int(
            center_y
            + math.sin(angle)
            * distance
            * local_progress
        )

        rr = int(
            center_radius * 0.58
        )

        # Connection first.
        ld.line(
            (
                center_x,
                center_y,
                cx,
                cy
            ),
            fill=(
                *ACCENT,
                int(
                    180 * opacity
                )
            ),
            width=4
        )

        ld.ellipse(
            (
                cx - rr,
                cy - rr,
                cx + rr,
                cy + rr
            ),
            fill=(
                *DARK,
                int(
                    220 * opacity
                )
            )
        )

        f = get_font(
            max(
                18,
                int(
                    width * 0.014
                )
            )
        )

        tw, th = text_size(
            ld,
            label,
            f
        )

        ld.text(
            (
                cx - tw / 2,
                cy - th / 2
            ),
            label,
            font=f,
            fill=(
                *WHITE,
                int(
                    255 * opacity
                )
            )
        )

    image.alpha_composite(
        layer
    )


# ============================================================
# MINIMAL TEXT
# ============================================================

def draw_minimal_text(
    image,
    graphic,
    progress,
    opacity
):

    draw = ImageDraw.Draw(
        image
    )

    width, height = image.size

    text = str(
        graphic.get(
            "text",
            ""
        )
    ).strip()

    if not text:

        return

    text = text.upper()

    font = get_font(
        max(
            40,
            min(
                82,
                int(
                    width * 0.043
                )
            )
        )
    )

    x = int(
        width * 0.08
    )

    y = int(
        height * 0.82
    )

    y += int(
        35
        * (1 - progress)
    )

    draw.text(
        (
            x,
            y
        ),
        text,
        font=font,
        fill=(
            *WHITE,
            int(
                255 * opacity
            )
        ),
        stroke_width=3,
        stroke_fill=(
            *DARK,
            int(
                210 * opacity
            )
        )
    )


# ============================================================
# RENDER ONE GRAPHIC
# ============================================================

def render_graphic(
    frame,
    graphic,
    current_time
):

    start = float(
        graphic.get(
            "speech_start",
            0
        )
    )

    end = float(
        graphic.get(
            "speech_end",
            start + 1
        )
    )

    if current_time < start:

        return frame

    if current_time > end:

        return frame

    animation_duration = float(
        graphic.get(
            "animation_duration",
            0.35
        )
    )

    progress, opacity = (
        animation_progress(
            current_time,
            start,
            end,
            animation_duration
        )
    )

    # --------------------------------------------------------
    # OpenCV BGR -> PIL RGB
    # --------------------------------------------------------

    rgb = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2RGB
    )

    image = Image.fromarray(
        rgb
    ).convert(
        "RGBA"
    )

    graphic_type = str(
        graphic.get(
            "graphic_type",
            "headline"
        )
    ).lower().strip()

    # --------------------------------------------------------
    # GRAPHIC TYPES
    # --------------------------------------------------------

    if graphic_type in [
        "headline",
        "title"
    ]:

        draw_headline(
            image,
            graphic,
            progress,
            opacity
        )

    elif graphic_type in [
        "keyword",
        "highlight"
    ]:

        draw_keyword(
            image,
            graphic,
            progress,
            opacity
        )

    elif graphic_type in [
        "process",
        "process flow",
        "process_flow",
        "diagram"
    ]:

        draw_process_flow(
            image,
            graphic,
            progress,
            opacity
        )

    elif graphic_type in [
        "concept cluster",
        "concept_cluster"
    ]:

        draw_concept_cluster(
            image,
            graphic,
            progress,
            opacity
        )

    else:

        draw_minimal_text(
            image,
            graphic,
            progress,
            opacity
        )

    # --------------------------------------------------------
    # PIL RGB -> NUMPY -> OpenCV BGR
    # --------------------------------------------------------

    rgb_result = np.array(
        image.convert(
            "RGB"
        )
    )

    result = cv2.cvtColor(
        rgb_result,
        cv2.COLOR_RGB2BGR
    )

    return result


# ============================================================
# CLEAN GRAPHICS PLAN
# ============================================================

def clean_graphics(
    graphics
):

    cleaned = []

    for graphic in graphics:

        if not isinstance(
            graphic,
            dict
        ):

            continue

        try:

            start = float(
                graphic.get(
                    "speech_start"
                )
            )

            end = float(
                graphic.get(
                    "speech_end"
                )
            )

        except (
            TypeError,
            ValueError
        ):

            continue

        if end <= start:

            continue

        # Maximum duration.
        if (
            end - start
            > 4
        ):

            end = (
                start
                + 4
            )

        graphic[
            "speech_start"
        ] = start

        graphic[
            "speech_end"
        ] = end

        if not graphic.get(
            "text"
        ):

            concept = graphic.get(
                "concept",
                ""
            )

            if isinstance(
                concept,
                list
            ):

                concept = " ".join(
                    map(
                        str,
                        concept
                    )
                )

            graphic[
                "text"
            ] = str(
                concept
            )

        cleaned.append(
            graphic
        )

    cleaned.sort(
        key=lambda x:
        x["speech_start"]
    )

    return cleaned[
        :MAX_GRAPHICS
    ]


# ============================================================
# MAIN RENDER
# ============================================================

def render():

    print()
    print("=" * 70)
    print("SMART MOTION GRAPHICS RENDERER")
    print("=" * 70)
    print()

    print(
        "Project:"
    )

    print(
        BASE_DIR
    )

    print()

    print(
        "Input video:"
    )

    print(
        INPUT_VIDEO
    )

    print()

    print(
        "Graphics plan:"
    )

    print(
        PLAN_FILE
    )

    print()

    # --------------------------------------------------------
    # CHECK FILES
    # --------------------------------------------------------

    if not os.path.exists(
        INPUT_VIDEO
    ):

        print(
            "ERROR: Input video not found."
        )

        return

    if not os.path.exists(
        PLAN_FILE
    ):

        print(
            "ERROR: Graphics plan not found."
        )

        return

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True
    )

    # --------------------------------------------------------
    # LOAD GRAPHICS PLAN
    # --------------------------------------------------------

    plan_data = load_json(
        PLAN_FILE
    )

    if isinstance(
        plan_data,
        dict
    ):

        graphics = plan_data.get(
            "graphics",
            []
        )

    elif isinstance(
        plan_data,
        list
    ):

        graphics = plan_data

    else:

        graphics = []

    graphics = clean_graphics(
        graphics
    )

    print(
        f"Graphics loaded: "
        f"{len(graphics)}"
    )

    print()

    for index, graphic in enumerate(
        graphics,
        start=1
    ):

        print(
            f"{index:02d}. "
            f"{graphic['speech_start']:.2f}s "
            f"→ "
            f"{graphic['speech_end']:.2f}s "
            f"| "
            f"{graphic.get('graphic_type', 'headline')} "
            f"| "
            f"{graphic.get('text', '')}"
        )

    print()

    # --------------------------------------------------------
    # OPEN INPUT VIDEO
    # --------------------------------------------------------

    cap = cv2.VideoCapture(
        INPUT_VIDEO
    )

    if not cap.isOpened():

        print(
            "ERROR: Could not open input video."
        )

        return

    width = int(
        cap.get(
            cv2.CAP_PROP_FRAME_WIDTH
        )
    )

    height = int(
        cap.get(
            cv2.CAP_PROP_FRAME_HEIGHT
        )
    )

    fps = cap.get(
        cv2.CAP_PROP_FPS
    )

    total_frames = int(
        cap.get(
            cv2.CAP_PROP_FRAME_COUNT
        )
    )

    if fps <= 0:

        fps = 30.0

    duration = (
        total_frames
        / fps
    )

    print(
        "Video information:"
    )

    print(
        f"Resolution : "
        f"{width} x {height}"
    )

    print(
        f"FPS        : "
        f"{fps:.2f}"
    )

    print(
        f"Frames     : "
        f"{total_frames}"
    )

    print(
        f"Duration   : "
        f"{duration:.2f}s"
    )

    print()

    # --------------------------------------------------------
    # TEMP VIDEO WRITER
    # --------------------------------------------------------

    fourcc = (
        cv2.VideoWriter_fourcc(
            *"mp4v"
        )
    )

    writer = cv2.VideoWriter(
        TEMP_VIDEO,
        fourcc,
        fps,
        (
            width,
            height
        )
    )

    if not writer.isOpened():

        print(
            "ERROR: Could not create temporary video."
        )

        cap.release()

        return

    # --------------------------------------------------------
    # RENDER
    # --------------------------------------------------------

    print(
        "Rendering motion graphics..."
    )

    frame_number = 0

    while True:

        ret, frame = cap.read()

        if not ret:

            break

        current_time = (
            frame_number
            / fps
        )

        output_frame = (
            frame.copy()
        )

        # ----------------------------------------------------
        # APPLY ACTIVE GRAPHICS
        # ----------------------------------------------------

        for graphic in graphics:

            start = graphic[
                "speech_start"
            ]

            end = graphic[
                "speech_end"
            ]

            if (
                start
                <= current_time
                <= end
            ):

                output_frame = (
                    render_graphic(
                        output_frame,
                        graphic,
                        current_time
                    )
                )

        writer.write(
            output_frame
        )

        frame_number += 1

        # Progress.
        if frame_number % 30 == 0:

            percent = (
                frame_number
                / total_frames
                * 100
            )

            print(
                f"\rRendering: "
                f"{percent:6.2f}%",
                end=""
            )

    cap.release()

    writer.release()

    print()
    print()

    print(
        "Graphics rendering finished."
    )

    # --------------------------------------------------------
    # RESTORE ORIGINAL AUDIO
    # --------------------------------------------------------

    print(
        "Restoring original audio..."
    )

    ffmpeg_command = [

        "ffmpeg",

        "-y",

        "-i",
        TEMP_VIDEO,

        "-i",
        INPUT_VIDEO,

        "-map",
        "0:v:0",

        "-map",
        "1:a:0",

        "-c:v",
        "libx264",

        "-preset",
        "medium",

        "-crf",
        "18",

        "-c:a",
        "aac",

        "-b:a",
        "192k",

        "-shortest",

        FINAL_VIDEO
    ]

    try:

        subprocess.run(
            ffmpeg_command,
            check=True
        )

    except FileNotFoundError:

        print()
        print(
            "ERROR: FFmpeg was not found."
        )

        print(
            "Make sure FFmpeg is available "
            "in your PATH."
        )

        return

    except subprocess.CalledProcessError:

        print()
        print(
            "ERROR: FFmpeg failed "
            "while creating the final video."
        )

        return

    # --------------------------------------------------------
    # DELETE TEMPORARY VIDEO
    # --------------------------------------------------------

    try:

        if os.path.exists(
            TEMP_VIDEO
        ):

            os.remove(
                TEMP_VIDEO
            )

    except Exception:

        pass

    # --------------------------------------------------------
    # COMPLETE
    # --------------------------------------------------------

    print()

    print("=" * 70)
    print(
        "SMART RENDER COMPLETE"
    )
    print("=" * 70)

    print()

    print(
        "Final video:"
    )

    print(
        FINAL_VIDEO
    )

    print()

    print(
        "Original video : PRESERVED"
    )

    print(
        "Original audio : PRESERVED"
    )

    print(
        "Motion graphics: ADDED"
    )

    print()


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    render()