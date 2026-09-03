import json
import re
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

TRANSCRIPT_FILE = BASE_DIR / "output" / "transcript.json"
VIDEO_ANALYSIS_FILE = BASE_DIR / "output" / "input_video_analysis.json"
STYLE_FILE = BASE_DIR / "style_memory.json"

OUTPUT_FILE = BASE_DIR / "output" / "semantic_graphics_plan.json"


# ============================================================
# LOAD DATA
# ============================================================

def load_json(path):
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


transcript = load_json(TRANSCRIPT_FILE)
video_analysis = load_json(VIDEO_ANALYSIS_FILE)

if STYLE_FILE.exists():
    style = load_json(STYLE_FILE)
else:
    style = {}


segments = transcript.get("segments", [])


# ============================================================
# SEMANTIC CATEGORIES
# ============================================================

NUMBER_PATTERN = re.compile(
    r"\b\d+(?:\.\d+)?(?:%|cm|m|km|million|billion)?\b",
    re.IGNORECASE
)

CONCEPT_WORDS = {
    "writing",
    "research",
    "planning",
    "organization",
    "evidence",
    "audience",
    "argument",
    "counterargument",
    "brainstorming",
    "sources",
    "bibliography",
    "proposal",
    "outline",
    "revision",
    "process",
    "progress",
    "learning",
    "improve",
    "ideas"
}

ACTION_WORDS = {
    "develop",
    "improve",
    "organize",
    "choose",
    "understand",
    "build",
    "create",
    "research",
    "plan",
    "write",
    "revise",
    "learn",
    "focus"
}


# ============================================================
# TEXT HELPERS
# ============================================================

def words(text):
    return re.findall(r"[A-Za-z]+", text.lower())


def important_words(text):
    result = []

    for word in words(text):
        if len(word) < 4:
            continue

        if word in CONCEPT_WORDS:
            result.append(word)

    return list(dict.fromkeys(result))


def find_numbers(text):
    return NUMBER_PATTERN.findall(text)


def contains_question(text):
    return "?" in text


def contains_action(text):
    lower = text.lower()

    return any(
        action in lower
        for action in ACTION_WORDS
    )


# ============================================================
# UNDERSTAND MEANING
# ============================================================

def understand_segment(text):

    lower = text.lower()

    concepts = important_words(text)
    numbers = find_numbers(text)

    # --------------------------------------------------------
    # STATISTIC
    # --------------------------------------------------------

    if numbers:
        return {
            "semantic_type": "statistic",
            "reason": "The speaker mentions a measurable number.",
            "visual": "large_number",
            "content": numbers[0]
        }

    # --------------------------------------------------------
    # QUESTION
    # --------------------------------------------------------

    if contains_question(text):
        return {
            "semantic_type": "question",
            "reason": "The speaker asks a question.",
            "visual": "question_headline",
            "content": text.strip()
        }

    # --------------------------------------------------------
    # PROCESS / ACTION
    # --------------------------------------------------------

    if contains_action(text) and concepts:

        return {
            "semantic_type": "process",
            "reason": "The speaker describes an action or process.",
            "visual": "process_diagram",
            "content": concepts[:4]
        }

    # --------------------------------------------------------
    # MULTIPLE CONCEPTS
    # --------------------------------------------------------

    if len(concepts) >= 2:

        return {
            "semantic_type": "concept_group",
            "reason": "Several related concepts are mentioned.",
            "visual": "concept_cluster",
            "content": concepts[:5]
        }

    # --------------------------------------------------------
    # SINGLE CONCEPT
    # --------------------------------------------------------

    if len(concepts) == 1:

        return {
            "semantic_type": "key_concept",
            "reason": "A meaningful concept is emphasized.",
            "visual": "keyword_card",
            "content": concepts[0]
        }

    # --------------------------------------------------------
    # GENERAL IDEA
    # --------------------------------------------------------

    meaningful = [
        w for w in words(text)
        if len(w) >= 5
    ]

    if meaningful:

        return {
            "semantic_type": "idea",
            "reason": "The sentence contains a general idea worth emphasizing.",
            "visual": "minimal_text",
            "content": " ".join(meaningful[:4])
        }

    return None


# ============================================================
# GRAPHIC DESIGN DECISION
# ============================================================

def choose_position(index, semantic_type):

    if semantic_type == "statistic":
        return "center"

    positions = [
        "bottom",
        "right",
        "left",
        "top"
    ]

    return positions[index % len(positions)]


def choose_animation(semantic_type):

    if semantic_type == "statistic":
        return "scale_in"

    if semantic_type == "process":
        return "slide_up"

    if semantic_type == "concept_group":
        return "stagger_in"

    if semantic_type == "key_concept":
        return "fade_up"

    return "fade_in"


# ============================================================
# CREATE PLAN
# ============================================================

graphics = []

graphic_id = 1

for segment in segments:

    text = segment.get("text", "").strip()

    if not text:
        continue

    start = float(segment.get("start", 0))
    end = float(segment.get("end", start))

    understanding = understand_segment(text)

    if understanding is None:
        continue

    semantic_type = understanding["semantic_type"]

    # Don't cover the entire screen with graphics.
    # Give the graphic a slightly shorter life than the speech.
    graphic_start = start + 0.10
    graphic_end = max(
        graphic_start + 0.5,
        end - 0.10
    )

    graphic = {
        "id": graphic_id,

        "timing": {
            "start": round(graphic_start, 2),
            "end": round(graphic_end, 2)
        },

        "speech": text,

        "understanding": {
            "type": semantic_type,
            "reason": understanding["reason"]
        },

        "graphic": {
            "visual_type": understanding["visual"],
            "content": understanding["content"]
        },

        "placement": {
            "region": choose_position(
                graphic_id,
                semantic_type
            ),
            "avoid_face": True,
            "safe_margin": 0.08
        },

        "animation": {
            "in": choose_animation(semantic_type),
            "out": "fade_out",
            "duration": 0.35
        },

        "style": {
            "reference_style": True,
            "minimal": True,
            "large_typography": True,
            "rounded_shapes": True,
            "controlled_colors": True,
            "smooth_motion": True
        }
    }

    graphics.append(graphic)

    graphic_id += 1


# ============================================================
# FINAL PLAN
# ============================================================

final_plan = {

    "version": "2.0",

    "purpose": "AI semantic motion graphics overlay",

    "video": {
        "preserve_original_video": True,
        "preserve_original_audio": True,
        "overlay_only": True
    },

    "source": {
        "transcript": str(TRANSCRIPT_FILE),
        "video_analysis": str(VIDEO_ANALYSIS_FILE),
        "style_memory": str(STYLE_FILE)
    },

    "video_properties": video_analysis,

    "style": style,

    "graphics": graphics,

    "rules": {
        "never_replace_original_video": True,
        "never_replace_original_audio": True,
        "avoid_face": True,
        "avoid_center_if_face_detected": True,
        "maintain_negative_space": True,
        "use_reference_style": True,
        "avoid_graphic_overload": True
    }
}


# ============================================================
# SAVE
# ============================================================

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
        final_plan,
        f,
        indent=2,
        ensure_ascii=False
    )


# ============================================================
# DISPLAY
# ============================================================

print()
print("=" * 70)
print("SEMANTIC MOTION GRAPHICS PLANNER")
print("=" * 70)

print()
print(f"Speech segments : {len(segments)}")
print(f"Graphics planned: {len(graphics)}")
print()

for item in graphics:

    print(
        f'{item["timing"]["start"]:.2f}s → '
        f'{item["timing"]["end"]:.2f}s | '
        f'{item["understanding"]["type"]:<15} | '
        f'{item["graphic"]["visual_type"]:<20} | '
        f'{item["graphic"]["content"]}'
    )

print()
print("Plan saved to:")
print(OUTPUT_FILE)
print()