import json
import re
from pathlib import Path
from typing import List, Dict, Any


ROOT = Path(__file__).resolve().parents[1]

STYLE_MEMORY_FILE = ROOT / "style_memory" / "style_memory.json"
OUTPUT_DIR = ROOT / "output"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# STYLE MEMORY
# ============================================================

def load_style_memory() -> Dict[str, Any]:
    if not STYLE_MEMORY_FILE.exists():
        raise FileNotFoundError(
            f"Style memory not found:\n{STYLE_MEMORY_FILE}\n"
            "Run analyzer/analyze_style.py first."
        )

    with open(STYLE_MEMORY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


# ============================================================
# TEXT PROCESSING
# ============================================================

def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text.strip())
    return text


def split_sentences(script: str) -> List[str]:
    script = clean_text(script)

    sentences = re.split(
        r"(?<=[.!?])\s+",
        script
    )

    sentences = [
        s.strip()
        for s in sentences
        if s.strip()
    ]

    return sentences


# ============================================================
# SENTENCE CLASSIFICATION
# ============================================================

def classify_sentence(sentence: str) -> str:

    s = sentence.lower()

    question_words = [
        "why",
        "how",
        "what",
        "when",
        "where",
        "who",
        "is it",
        "can",
        "could",
        "does",
        "did"
    ]

    number_words = [
        "percent",
        "%",
        "million",
        "billion",
        "thousand",
        "cm",
        "centimeter",
        "meters",
        "km",
        "years",
        "times"
    ]

    cause_words = [
        "because",
        "therefore",
        "causes",
        "caused",
        "leads to",
        "results in",
        "due to"
    ]

    contrast_words = [
        "but",
        "however",
        "although",
        "instead",
        "while",
        "yet"
    ]

    if "?" in sentence:
        return "question"

    if any(word in s for word in number_words):
        return "statistic"

    if any(word in s for word in cause_words):
        return "explanation"

    if any(word in s for word in contrast_words):
        return "contrast"

    if any(word in s for word in question_words):
        return "question"

    return "statement"


# ============================================================
# VISUAL SELECTION
# ============================================================

def choose_visual_type(sentence: str, sentence_type: str) -> str:

    s = sentence.lower()

    # Statistics are usually stronger with designed graphics.
    if sentence_type == "statistic":
        return "data_graphic"

    # Questions work well with large typography.
    if sentence_type == "question":
        return "kinetic_typography"

    # Explanations can use diagrams.
    if sentence_type == "explanation":
        return "diagram"

    # Contrasts can use two-sided cards.
    if sentence_type == "contrast":
        return "comparison_cards"

    # Detect subjects that benefit from real footage/images.
    image_keywords = [
        "moon",
        "earth",
        "space",
        "planet",
        "person",
        "people",
        "human",
        "city",
        "mountain",
        "ocean",
        "animal",
        "car",
        "building",
        "computer",
        "phone",
        "hospital",
        "clinic",
        "doctor",
        "school",
        "student"
    ]

    for keyword in image_keywords:
        if keyword in s:
            return "image_plus_graphics"

    # Default to motion graphics.
    return "motion_graphic"


# ============================================================
# STYLE RULES
# ============================================================

def build_style_constraints(memory: Dict[str, Any]) -> Dict[str, Any]:

    style = memory.get("learned_style", {})

    canvas = style.get("canvas", {})
    pacing = style.get("pacing", {})
    density = style.get("visual_density", {})
    palette = style.get("color_palette", [])

    width = canvas.get("preferred_width", 576)
    height = canvas.get("preferred_height", 1024)

    fps = canvas.get("fps_mean", 30)

    duration = pacing.get(
        "duration_mean_seconds",
        20
    )

    motion = pacing.get(
        "motion_mean",
        10
    )

    saturation = density.get(
        "saturation_mean",
        80
    )

    return {
        "canvas": {
            "width": width,
            "height": height,
            "fps": fps,
            "aspect_ratio": canvas.get(
                "aspect_ratio_mean",
                0.5625
            )
        },

        "pacing": {
            "target_duration": duration,
            "motion_strength": motion
        },

        "visual_density": {
            "saturation": saturation,
            "edge_density": density.get(
                "edge_density_mean",
                0.1
            )
        },

        "palette": palette,

        # Conservative design rules based on the
        # observed motion-graphics style.
        "design_rules": {
            "vertical": True,
            "large_typography": True,
            "controlled_color": True,
            "negative_space": True,
            "rounded_cards": True,
            "smooth_motion": True,
            "mixed_media": True,
            "avoid_full_screen_noise": True,
            "avoid_random_camera_motion": True,
            "avoid_generative_video": True
        }
    }


# ============================================================
# TIMING
# ============================================================

def estimate_scene_duration(
    sentence: str,
    sentence_type: str,
    total_sentences: int,
    target_video_duration: float
) -> float:

    word_count = len(sentence.split())

    # Approximate speaking duration.
    speech_duration = word_count / 2.6

    if sentence_type == "question":
        speech_duration += 0.4

    if sentence_type == "statistic":
        speech_duration += 0.5

    if sentence_type == "explanation":
        speech_duration += 0.3

    # Prevent extreme scene lengths.
    speech_duration = max(
        1.5,
        min(speech_duration, 6.0)
    )

    return round(speech_duration, 2)


# ============================================================
# MOTION DESIGN
# ============================================================

def choose_animation(
    visual_type: str,
    sentence_type: str
) -> Dict[str, Any]:

    if visual_type == "kinetic_typography":
        return {
            "entry": "fade_up",
            "main": "word_reveal",
            "exit": "fade_out",
            "easing": "ease_out"
        }

    if visual_type == "data_graphic":
        return {
            "entry": "scale_up",
            "main": "count_up",
            "exit": "slide_out",
            "easing": "ease_out"
        }

    if visual_type == "diagram":
        return {
            "entry": "draw_in",
            "main": "move_along_path",
            "exit": "fade_out",
            "easing": "ease_in_out"
        }

    if visual_type == "comparison_cards":
        return {
            "entry": "slide_from_sides",
            "main": "subtle_float",
            "exit": "slide_down",
            "easing": "ease_in_out"
        }

    if visual_type == "image_plus_graphics":
        return {
            "entry": "scale_in",
            "main": "parallax",
            "exit": "fade_out",
            "easing": "ease_in_out"
        }

    return {
        "entry": "fade_up",
        "main": "float",
        "exit": "fade_out",
        "easing": "ease_in_out"
    }


# ============================================================
# LAYOUT
# ============================================================

def choose_layout(
    visual_type: str,
    sentence_type: str
) -> str:

    if visual_type == "kinetic_typography":
        return "center_focus"

    if visual_type == "data_graphic":
        return "center_graphic"

    if visual_type == "diagram":
        return "diagram_center"

    if visual_type == "comparison_cards":
        return "split_screen"

    if visual_type == "image_plus_graphics":
        return "image_with_text"

    if sentence_type == "question":
        return "large_text"

    return "minimal_card"


# ============================================================
# SCENE GENERATION
# ============================================================

def generate_scene(
    sentence: str,
    index: int,
    style_constraints: Dict[str, Any],
    total_sentences: int
) -> Dict[str, Any]:

    sentence_type = classify_sentence(sentence)

    visual_type = choose_visual_type(
        sentence,
        sentence_type
    )

    duration = estimate_scene_duration(
        sentence,
        sentence_type,
        total_sentences,
        style_constraints["pacing"]["target_duration"]
    )

    animation = choose_animation(
        visual_type,
        sentence_type
    )

    layout = choose_layout(
        visual_type,
        sentence_type
    )

    scene = {
        "scene_id": index + 1,

        "narration": sentence,

        "type": sentence_type,

        "duration": duration,

        "visual": {
            "type": visual_type,
            "layout": layout,

            "text": {
                "headline": sentence,
                "large": (
                    visual_type == "kinetic_typography"
                    or sentence_type == "question"
                )
            },

            "asset_required": visual_type in [
                "image_plus_graphics"
            ],

            "asset_search_terms": [],

            "graphics": []
        },

        "motion": animation,

        "style": {
            "use_learned_palette": True,
            "negative_space": True,
            "controlled_color": True,
            "rounded_elements": True
        }
    }

    # --------------------------------------------------------
    # Asset search terms
    # --------------------------------------------------------

    if visual_type == "image_plus_graphics":

        words = re.findall(
            r"\b[a-zA-Z]{4,}\b",
            sentence
        )

        stopwords = {
            "this",
            "that",
            "with",
            "from",
            "about",
            "there",
            "their",
            "which",
            "every",
            "what",
            "when",
            "where",
            "because",
            "could",
            "would",
            "should"
        }

        keywords = [
            word.lower()
            for word in words
            if word.lower() not in stopwords
        ]

        scene["visual"]["asset_search_terms"] = keywords[:5]

    # --------------------------------------------------------
    # Graphics
    # --------------------------------------------------------

    if visual_type == "data_graphic":

        numbers = re.findall(
            r"\d+(?:\.\d+)?%?",
            sentence
        )

        scene["visual"]["graphics"].append({
            "kind": "number",
            "value": numbers[0] if numbers else "",
            "animation": "count_up"
        })

    elif visual_type == "diagram":

        scene["visual"]["graphics"].append({
            "kind": "flow",
            "nodes": 3,
            "animation": "draw_in"
        })

    elif visual_type == "comparison_cards":

        scene["visual"]["graphics"].append({
            "kind": "two_cards",
            "animation": "slide_from_sides"
        })

    elif visual_type == "motion_graphic":

        scene["visual"]["graphics"].append({
            "kind": "geometric_shapes",
            "count": 2,
            "animation": "subtle_float"
        })

    return scene


# ============================================================
# BUILD STORYBOARD
# ============================================================

def build_storyboard(script: str) -> Dict[str, Any]:

    memory = load_style_memory()

    style_constraints = build_style_constraints(
        memory
    )

    sentences = split_sentences(script)

    if not sentences:
        raise ValueError(
            "No usable sentences found in script."
        )

    scenes = []

    for index, sentence in enumerate(sentences):

        scene = generate_scene(
            sentence=sentence,
            index=index,
            style_constraints=style_constraints,
            total_sentences=len(sentences)
        )

        scenes.append(scene)

    # --------------------------------------------------------
    # Normalize timing
    # --------------------------------------------------------

    target_duration = style_constraints[
        "pacing"
    ][
        "target_duration"
    ]

    current_duration = sum(
        scene["duration"]
        for scene in scenes
    )

    if current_duration > 0:

        scale = (
            target_duration /
            current_duration
        )

        # Don't radically change timing.
        scale = max(
            0.75,
            min(scale, 1.25)
        )

        for scene in scenes:

            scene["duration"] = round(
                scene["duration"] * scale,
                2
            )

    # --------------------------------------------------------
    # Assign timeline
    # --------------------------------------------------------

    current_time = 0.0

    for scene in scenes:

        scene["start"] = round(
            current_time,
            2
        )

        current_time += scene["duration"]

        scene["end"] = round(
            current_time,
            2
        )

    storyboard = {

        "project": {
            "name": "motion_ai_project",
            "version": 1
        },

        "style_source": {
            "training_videos": memory.get(
                "training_videos",
                0
            ),

            "style_memory_version": memory.get(
                "version",
                1
            )
        },

        "canvas": style_constraints["canvas"],

        "style": style_constraints,

        "script": script,

        "duration": round(
            current_time,
            2
        ),

        "scene_count": len(scenes),

        "scenes": scenes
    }

    return storyboard


# ============================================================
# SAVE
# ============================================================

def save_storyboard(
    storyboard: Dict[str, Any],
    filename: str = "storyboard.json"
):

    path = OUTPUT_DIR / filename

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            storyboard,
            f,
            indent=2,
            ensure_ascii=False
        )

    return path


# ============================================================
# COMMAND LINE
# ============================================================

def main():

    print()
    print("=" * 70)
    print("MOTION AI — STYLE-AWARE SCENE PLANNER")
    print("=" * 70)
    print()

    print(
        "Enter your video script."
    )
    print(
        "Press ENTER twice when finished."
    )
    print()

    lines = []

    while True:

        try:
            line = input()

        except EOFError:
            break

        if line == "":
            if lines:
                break
            continue

        lines.append(line)

    script = " ".join(lines)

    if not script.strip():

        print(
            "ERROR: No script entered."
        )

        return

    print()
    print("Loading Style Memory...")

    memory = load_style_memory()

    print(
        f"Training videos: "
        f"{memory.get('training_videos', 0)}"
    )

    print()

    storyboard = build_storyboard(
        script
    )

    output = save_storyboard(
        storyboard
    )

    print(
        f"Scenes created: "
        f"{storyboard['scene_count']}"
    )

    print(
        f"Target duration: "
        f"{storyboard['duration']} seconds"
    )

    print()

    for scene in storyboard["scenes"]:

        print(
            f"Scene {scene['scene_id']}: "
            f"{scene['visual']['type']} | "
            f"{scene['duration']} sec"
        )

        print(
            f"  {scene['narration']}"
        )

    print()

    print(
        f"Storyboard saved to:\n{output}"
    )

    print()
    print("=" * 70)


if __name__ == "__main__":
    main()