import json
import os
import re
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

TRANSCRIPT_FILE = BASE_DIR / "output" / "transcript.json"
VIDEO_ANALYSIS_FILE = BASE_DIR / "output" / "input_video_analysis.json"
STYLE_FILE = BASE_DIR / "style_memory.json"

OUTPUT_FILE = BASE_DIR / "output" / "graphics_plan.json"


# ---------------------------------------------------------
# LOAD FILES
# ---------------------------------------------------------

def load_json(path):
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


transcript_data = load_json(TRANSCRIPT_FILE)
video_data = load_json(VIDEO_ANALYSIS_FILE)

if STYLE_FILE.exists():
    style_data = load_json(STYLE_FILE)
else:
    style_data = {
        "canvas": {
            "orientation": "vertical",
            "preferred_width": 1080,
            "preferred_height": 1920
        },
        "visual_style": {
            "brightness": "light",
            "layout": "minimal",
            "typography": "large",
            "motion": "smooth",
            "density": "low"
        },
        "graphics": {
            "preferred_types": [
                "keyword",
                "headline",
                "stat",
                "arrow",
                "card",
                "icon"
            ]
        }
    }


# ---------------------------------------------------------
# GET TRANSCRIPT SEGMENTS
# ---------------------------------------------------------

segments = transcript_data.get("segments", [])

if not segments:
    raise ValueError("No transcript segments found.")


# ---------------------------------------------------------
# KEYWORD DETECTION
# ---------------------------------------------------------

STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "if", "then",
    "this", "that", "these", "those", "is", "are", "was",
    "were", "be", "been", "being", "to", "of", "in", "on",
    "for", "with", "at", "by", "from", "as", "it", "its",
    "i", "me", "my", "we", "our", "you", "your", "they",
    "their", "he", "she", "his", "her", "them", "and",
    "so", "very", "just", "can", "could", "would", "should",
    "will", "have", "has", "had", "do", "did", "does",
    "about", "into", "over", "after", "before", "than",
    "also", "now", "not", "only", "more", "most"
}


def clean_words(text):
    words = re.findall(r"[A-Za-z0-9]+", text.lower())

    return [
        w for w in words
        if w not in STOPWORDS and len(w) >= 4
    ]


# ---------------------------------------------------------
# DETECT IMPORTANT CONTENT
# ---------------------------------------------------------

def detect_graphic_type(text):
    lower = text.lower()

    # Numbers / statistics
    if re.search(r"\b\d+(\.\d+)?\b", text):
        return "stat"

    # Strong explanatory phrases
    if any(x in lower for x in [
        "because",
        "important",
        "problem",
        "reason",
        "result",
        "helped",
        "improve",
        "increase",
        "decrease"
    ]):
        return "keyword"

    # Questions
    if "?" in text:
        return "headline"

    # Default
    return "keyword"


def importance_score(text):
    words = clean_words(text)

    score = 0

    # Longer meaningful segments
    if len(words) >= 5:
        score += 1

    if len(words) >= 9:
        score += 1

    # Numbers are visually useful
    if re.search(r"\b\d+(\.\d+)?\b", text):
        score += 3

    # Strong semantic words
    important_words = [
        "important",
        "problem",
        "research",
        "writing",
        "evidence",
        "audience",
        "planning",
        "organization",
        "argument",
        "counterargument",
        "proposal",
        "outline",
        "sources",
        "bibliography",
        "revision",
        "progress",
        "improve",
        "process"
    ]

    for word in important_words:
        if word in text.lower():
            score += 1

    return score


# ---------------------------------------------------------
# POSITION SELECTION
# ---------------------------------------------------------

def choose_position(index):
    positions = [
        "bottom",
        "left",
        "right",
        "top"
    ]

    return positions[index % len(positions)]


# ---------------------------------------------------------
# ANIMATION STYLE
# ---------------------------------------------------------

def choose_animation(index):
    animations = [
        "fade_up",
        "slide_up",
        "scale_in",
        "fade_in"
    ]

    return animations[index % len(animations)]


# ---------------------------------------------------------
# CREATE GRAPHICS PLAN
# ---------------------------------------------------------

graphics = []

graphic_id = 1

for segment in segments:

    text = segment.get("text", "").strip()

    if not text:
        continue

    start = float(segment.get("start", 0))
    end = float(segment.get("end", start + 1))

    score = importance_score(text)

    # Ignore very unimportant speech
    if score < 1:
        continue

    words = clean_words(text)

    if not words:
        continue

    graphic_type = detect_graphic_type(text)

    # Select a short phrase rather than dumping the entire sentence
    if graphic_type == "stat":
        numbers = re.findall(
            r"\b\d+(?:\.\d+)?(?:%|cm|m|km|million|billion)?\b",
            text,
            flags=re.IGNORECASE
        )

        if numbers:
            graphic_text = numbers[0]
        else:
            graphic_text = words[0].upper()

    else:
        selected = words[:3]
        graphic_text = " ".join(selected).upper()

    graphic = {
        "id": graphic_id,

        "timing": {
            "start": round(start, 2),
            "end": round(end, 2)
        },

        "source_text": text,

        "importance": score,

        "type": graphic_type,

        "content": {
            "text": graphic_text
        },

        "placement": {
            "region": choose_position(graphic_id),
            "avoid_face": True,
            "safe_margin": 0.08
        },

        "animation": {
            "in": choose_animation(graphic_id),
            "out": "fade_out",
            "duration": 0.35
        },

        "style": {
            "use_reference_style": True,
            "minimal": True,
            "large_typography": True,
            "rounded_shapes": True,
            "controlled_accent_color": True
        }
    }

    graphics.append(graphic)

    graphic_id += 1


# ---------------------------------------------------------
# LIMIT GRAPHICS DENSITY
# ---------------------------------------------------------

# We don't want graphics appearing every second.
# Keep the strongest graphics if there are too many.

MAX_GRAPHICS = 15

if len(graphics) > MAX_GRAPHICS:

    graphics.sort(
        key=lambda x: x["importance"],
        reverse=True
    )

    graphics = graphics[:MAX_GRAPHICS]

    graphics.sort(
        key=lambda x: x["timing"]["start"]
    )


# ---------------------------------------------------------
# FINAL PLAN
# ---------------------------------------------------------

plan = {
    "version": "1.0",

    "project": {
        "type": "motion_graphics_overlay",
        "preserve_original_video": True,
        "preserve_original_audio": True
    },

    "input": {
        "transcript": str(TRANSCRIPT_FILE),
        "video_analysis": str(VIDEO_ANALYSIS_FILE),
        "style_memory": str(STYLE_FILE)
    },

    "style": style_data,

    "graphics": graphics,

    "rendering_rules": {
        "overlay_only": True,
        "do_not_replace_original_video": True,
        "do_not_replace_original_audio": True,
        "respect_safe_area": True,
        "avoid_face": True,
        "avoid_excessive_graphics": True,
        "smooth_animation": True
    }
}


# ---------------------------------------------------------
# SAVE
# ---------------------------------------------------------

OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True
)

with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8"
) as f:
    json.dump(
        plan,
        f,
        indent=2,
        ensure_ascii=False
    )


# ---------------------------------------------------------
# REPORT
# ---------------------------------------------------------

print()
print("=" * 70)
print("AI VIDEO UNDERSTANDING")
print("=" * 70)

print()
print(f"Transcript segments : {len(segments)}")
print(f"Graphics planned    : {len(graphics)}")

print()

for g in graphics:
    print(
        f'{g["timing"]["start"]:.2f}s → '
        f'{g["timing"]["end"]:.2f}s | '
        f'{g["type"]:<10} | '
        f'{g["content"]["text"]}'
    )

print()
print("Graphics plan saved to:")
print(OUTPUT_FILE)
print()