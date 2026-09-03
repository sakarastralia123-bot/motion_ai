import json
import re
import shutil
from pathlib import Path
from difflib import SequenceMatcher

import ollama


# ============================================================
# CONFIG
# ============================================================

MODEL = "llama3.2:3b"

BASE_DIR = Path(__file__).resolve().parent.parent

TRANSCRIPT_FILE = BASE_DIR / "output" / "transcript.json"
VIDEO_ANALYSIS_FILE = BASE_DIR / "output" / "input_video_analysis.json"
STYLE_FILE = BASE_DIR / "output" / "style_memory.json"

OUTPUT_FILE = BASE_DIR / "output" / "smart_graphics_plan.json"
REMOTION_FILE = BASE_DIR / "remotion" / "src" / "graphicsPlan.json"

MIN_GRAPHIC_DURATION = 1.2
MAX_GRAPHIC_DURATION = 3.8

MIN_GRAPHIC_GAP = 1.0

MIN_GRAPHICS = 8
MAX_GRAPHICS = 16

WINDOW_SIZE = 28
WINDOW_STEP = 18


# ============================================================
# JSON
# ============================================================

def load_json(path):
    if not path.exists():
        print()
        print("ERROR: Missing file:")
        print(path)
        print()
        raise SystemExit(1)

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def clean_json(text):
    if not text:
        return None

    text = text.strip()

    text = re.sub(
        r"```json",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"```",
        "",
        text,
    )

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1:
        return None

    candidate = text[start:end + 1]

    try:
        return json.loads(candidate)
    except Exception:
        return None


# ============================================================
# TEXT
# ============================================================

def normalize(word):
    word = str(word).lower()

    word = re.sub(
        r"[^a-z0-9]",
        "",
        word,
    )

    return word


def tokenize(text):
    return [
        normalize(x)
        for x in str(text).split()
        if normalize(x)
    ]


def similarity(a, b):
    a = normalize(a)
    b = normalize(b)

    if not a or not b:
        return 0

    if a == b:
        return 1.0

    if a in b or b in a:
        return 0.88

    return SequenceMatcher(
        None,
        a,
        b,
    ).ratio()


# ============================================================
# TRANSCRIPT
# ============================================================

def extract_words(transcript):

    words = []

    if isinstance(transcript, dict):

        source = transcript.get(
            "words",
            [],
        )

        if not source:

            segments = transcript.get(
                "segments",
                [],
            )

            for segment in segments:

                for word in segment.get(
                    "words",
                    [],
                ):

                    source.append(word)

    elif isinstance(transcript, list):

        source = transcript

    else:

        source = []

    for item in source:

        if not isinstance(item, dict):
            continue

        text = (
            item.get("word")
            or item.get("text")
            or ""
        )

        start = item.get("start")
        end = item.get("end")

        if (
            text
            and isinstance(start, (int, float))
            and isinstance(end, (int, float))
        ):

            words.append(
                {
                    "word": str(text).strip(),
                    "start": float(start),
                    "end": float(end),
                }
            )

    return words


# ============================================================
# WINDOWS
# ============================================================

def create_windows(words):

    windows = []

    if not words:
        return windows

    index = 0

    while index < len(words):

        section = words[
            index:index + WINDOW_SIZE
        ]

        if not section:
            break

        windows.append(
            {
                "index": len(windows),

                "start": section[0]["start"],

                "end": section[-1]["end"],

                "words": section,

                "text": " ".join(
                    x["word"]
                    for x in section
                ),
            }
        )

        index += WINDOW_STEP

    return windows


# ============================================================
# IMPORTANT WORD DETECTION
# ============================================================

IMPORTANT_WORDS = {
    "writing",
    "academic",
    "research",
    "planning",
    "plan",
    "process",
    "organization",
    "organize",
    "evidence",
    "audience",
    "brainstorming",
    "brainstorm",
    "proposal",
    "outline",
    "argument",
    "arguments",
    "counterargument",
    "sources",
    "source",
    "bibliography",
    "learning",
    "progress",
    "improve",
    "improved",
    "improvement",
    "steps",
    "step",
    "direction",
    "ideas",
    "idea",
    "question",
    "questions",
    "paragraphs",
    "paragraph",
    "paper",
    "draft",
    "revision",
    "revision",
    "course",
}


FILLER_WORDS = {
    "hello",
    "hi",
    "sir",
    "my",
    "name",
    "is",
    "i",
    "am",
    "im",
    "this",
    "that",
    "the",
    "a",
    "an",
    "and",
    "or",
    "to",
    "of",
    "in",
    "on",
    "for",
    "with",
    "it",
    "was",
    "were",
    "be",
    "been",
    "very",
    "really",
    "also",
    "now",
    "when",
    "looking",
    "back",
    "over",
    "these",
    "weeks",
}


def important_words(window):

    result = []

    for item in window["words"]:

        word = normalize(
            item["word"]
        )

        if not word:
            continue

        if word in FILLER_WORDS:
            continue

        if word in IMPORTANT_WORDS:

            result.append(item)

    return result


# ============================================================
# FALLBACK ANCHOR
# ============================================================

def fallback_anchor(window):

    important = important_words(
        window
    )

    if not important:
        return None

    # Prefer the first important word,
    # but avoid extremely short words.
    for item in important:

        word = normalize(
            item["word"]
        )

        if len(word) >= 5:
            return (
                item["start"],
                item["end"],
            )

    item = important[0]

    return (
        item["start"],
        item["end"],
    )


# ============================================================
# FUZZY ANCHOR MATCHING
# ============================================================

def find_anchor(
    anchor_words,
    window,
):

    if not anchor_words:
        return fallback_anchor(
            window
        )

    anchors = [
        normalize(x)
        for x in anchor_words
        if normalize(x)
    ]

    if not anchors:
        return fallback_anchor(
            window
        )

    words = window["words"]

    # --------------------------------------------------------
    # 1. Try consecutive sequence
    # --------------------------------------------------------

    best_score = 0
    best_range = None

    for i in range(len(words)):

        score_total = 0
        matched = 0

        for j, anchor in enumerate(
            anchors
        ):

            position = i + j

            if position >= len(words):
                break

            score = similarity(
                anchor,
                words[position]["word"],
            )

            score_total += score
            matched += 1

        if matched == 0:
            continue

        score = (
            score_total / matched
        )

        if score > best_score:

            best_score = score

            end_index = min(
                i + matched - 1,
                len(words) - 1,
            )

            best_range = (
                words[i]["start"],
                words[end_index]["end"],
            )

    if best_range is not None and best_score >= 0.48:

        return best_range

    # --------------------------------------------------------
    # 2. Try individual important anchor
    # --------------------------------------------------------

    for anchor in anchors:

        best_word = None
        best_score = 0

        for word in words:

            score = similarity(
                anchor,
                word["word"],
            )

            if score > best_score:

                best_score = score
                best_word = word

        if (
            best_word is not None
            and best_score >= 0.55
        ):

            return (
                best_word["start"],
                best_word["end"],
            )

    # --------------------------------------------------------
    # 3. Fallback
    # --------------------------------------------------------

    return fallback_anchor(
        window
    )


# ============================================================
# PROMPT
# ============================================================

def build_prompt(
    window,
    existing,
    style,
):

    previous = []

    for graphic in existing[-10:]:

        previous.append(
            {
                "concept":
                    graphic.get(
                        "concept",
                        "",
                    ),

                "text":
                    graphic.get(
                        "text",
                        "",
                    ),

                "type":
                    graphic.get(
                        "graphic_type",
                        "",
                    ),
            }
        )

    prompt = f"""
You are an expert motion graphics director.

Create ONE strong motion graphic for this exact speech section.

The original video remains unchanged.

==================================================
SPEECH
==================================================

{window["text"]}

==================================================
STYLE
==================================================

Clean modern minimal educational motion graphics.

Use:

- premium typography
- floating cards
- diagrams
- circles
- lines
- arrows
- documents
- visual relationships
- kinetic text
- smooth movement
- negative space

Avoid generic boring captions.

==================================================
PREVIOUS GRAPHICS
==================================================

{json.dumps(previous, indent=2)}

Never repeat a previous concept.

Never repeat previous display text.

==================================================
CHOOSE ONE TYPE
==================================================

headline
large_number
process
brainstorm
document
argument
audience
evidence
comparison
timeline
emphasis
question

==================================================
GOOD CONCEPTS
==================================================

academic writing
research
planning
organization
evidence
audience
brainstorming
proposal
outline
argument
counterargument
sources
bibliography
writing process
learning
progress
improvement
steps
ideas
questions

==================================================
BAD GRAPHICS
==================================================

Do not create graphics just for:

hello
my name is
I am
this course
this week
looking back
I can see
basically
really
also

==================================================
ANCHOR
==================================================

Return 1-4 words that actually occur
in the speech section.

The Python program will synchronize
the graphic to the speech.

==================================================
OUTPUT
==================================================

Return ONLY JSON.

{{
  "concept": "unique visual concept",
  "reason": "why this deserves visualization",
  "graphic_type": "headline",
  "text": "short display text",
  "position": "upper_right",
  "animation_in": "fade_up",
  "animation_out": "fade",
  "anchor_words": ["important", "words"],
  "importance": 8
}}

Allowed positions:

upper_left
upper_right
middle_left
middle_right
bottom_left
bottom_right
"""

    return prompt


# ============================================================
# OLLAMA
# ============================================================

def ask_ai(prompt):

    try:

        response = ollama.chat(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content":
                        "Return only valid JSON.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            options={
                "temperature": 0.45,
                "num_predict": 300,
            },
        )

        return clean_json(
            response["message"]["content"]
        )

    except Exception as error:

        print(
            f"   Ollama error: {error}"
        )

        return None


# ============================================================
# VALIDATION
# ============================================================

ALLOWED_TYPES = {
    "headline",
    "large_number",
    "process",
    "brainstorm",
    "document",
    "argument",
    "audience",
    "evidence",
    "comparison",
    "timeline",
    "emphasis",
    "question",
}

ALLOWED_POSITIONS = {
    "upper_left",
    "upper_right",
    "middle_left",
    "middle_right",
    "bottom_left",
    "bottom_right",
}


def validate_graphic(data):

    if not isinstance(data, dict):
        return None

    concept = str(
        data.get(
            "concept",
            "",
        )
    ).strip()

    text = str(
        data.get(
            "text",
            "",
        )
    ).strip()

    graphic_type = str(
        data.get(
            "graphic_type",
            "headline",
        )
    ).strip().lower()

    position = str(
        data.get(
            "position",
            "upper_right",
        )
    ).strip().lower()

    anchors = data.get(
        "anchor_words",
        [],
    )

    if not concept:
        return None

    if not text:
        return None

    if graphic_type not in ALLOWED_TYPES:

        graphic_type = "headline"

    if position not in ALLOWED_POSITIONS:

        position = "upper_right"

    if not isinstance(
        anchors,
        list,
    ):

        anchors = []

    anchors = [
        str(x).strip()
        for x in anchors
        if str(x).strip()
    ]

    return {
        "concept": concept,
        "reason": str(
            data.get(
                "reason",
                "",
            )
        ),

        "graphic_type":
            graphic_type,

        "text":
            text[:60],

        "position":
            position,

        "animation_in":
            str(
                data.get(
                    "animation_in",
                    "fade_up",
                )
            ),

        "animation_out":
            str(
                data.get(
                    "animation_out",
                    "fade",
                )
            ),

        "anchor_words":
            anchors[:4],

        "importance":
            int(
                data.get(
                    "importance",
                    7,
                )
            )
            if str(
                data.get(
                    "importance",
                    7,
                )
            ).isdigit()
            else 7,
    }


# ============================================================
# TIMING
# ============================================================

def add_timing(
    graphic,
    window,
):

    anchor = find_anchor(
        graphic.get(
            "anchor_words",
            [],
        ),
        window,
    )

    if anchor is None:
        return None

    start, end = anchor

    # Slightly before the spoken word
    start -= 0.12

    # Remain visible after the word
    end += 0.55

    start = max(
        0,
        start,
    )

    duration = end - start

    if duration < MIN_GRAPHIC_DURATION:

        end = (
            start
            + MIN_GRAPHIC_DURATION
        )

    if end - start > MAX_GRAPHIC_DURATION:

        end = (
            start
            + MAX_GRAPHIC_DURATION
        )

    graphic["speech_start"] = round(
        start,
        3,
    )

    graphic["speech_end"] = round(
        end,
        3,
    )

    return graphic


# ============================================================
# DUPLICATE DETECTION
# ============================================================

def is_duplicate(
    candidate,
    existing,
):

    candidate_concept = normalize(
        candidate["concept"]
    )

    candidate_text = normalize(
        candidate["text"]
    )

    for old in existing:

        old_concept = normalize(
            old["concept"]
        )

        old_text = normalize(
            old["text"]
        )

        # Exact text
        if (
            candidate_text
            and candidate_text == old_text
        ):
            return True

        # Exact concept
        if (
            candidate_concept
            and candidate_concept
            == old_concept
        ):
            return True

        # Similar concept
        if (
            similarity(
                candidate_concept,
                old_concept,
            )
            > 0.82
        ):
            return True

        # Timing overlap
        overlap_start = max(
            candidate["speech_start"],
            old["speech_start"],
        )

        overlap_end = min(
            candidate["speech_end"],
            old["speech_end"],
        )

        if overlap_end > overlap_start:

            overlap = (
                overlap_end
                - overlap_start
            )

            duration = (
                candidate["speech_end"]
                - candidate["speech_start"]
            )

            if (
                duration > 0
                and overlap / duration
                > 0.35
            ):
                return True

        # Gap
        if (
            candidate["speech_start"]
            >= old["speech_end"]
        ):

            gap = (
                candidate["speech_start"]
                - old["speech_end"]
            )

            if gap < MIN_GRAPHIC_GAP:
                return True

    return False


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)
    print("V3 SMART LOCAL MOTION GRAPHICS PLANNER")
    print("=" * 70)
    print()

    transcript = load_json(
        TRANSCRIPT_FILE
    )

    video_analysis = load_json(
        VIDEO_ANALYSIS_FILE
    )

    style = {}

    if STYLE_FILE.exists():

        try:
            style = load_json(
                STYLE_FILE
            )
        except Exception:
            style = {}

    words = extract_words(
        transcript
    )

    if not words:

        print(
            "ERROR: No word timings found."
        )

        return

    print(
        f"Transcript words : {len(words)}"
    )

    print(
        f"Video duration   : "
        f"{words[-1]['end']:.2f}s"
    )

    windows = create_windows(
        words
    )

    print(
        f"Speech windows   : {len(windows)}"
    )

    print(
        f"Target graphics  : "
        f"{MIN_GRAPHICS}-{MAX_GRAPHICS}"
    )

    print()

    graphics = []

    # ========================================================
    # AI PASS
    # ========================================================

    for number, window in enumerate(
        windows,
        start=1,
    ):

        print(
            f"[{number:02d}/{len(windows):02d}] "
            f"{window['start']:.2f}s → "
            f"{window['end']:.2f}s"
        )

        prompt = build_prompt(
            window,
            graphics,
            style,
        )

        result = ask_ai(
            prompt
        )

        graphic = validate_graphic(
            result
        )

        if graphic is None:

            print(
                "   AI graphic invalid"
            )

            # ------------------------------------------------
            # Automatic fallback graphic
            # ------------------------------------------------

            important = important_words(
                window
            )

            if important:

                item = important[0]

                graphic = {
                    "concept":
                        item["word"],

                    "reason":
                        "Important spoken concept",

                    "graphic_type":
                        "emphasis",

                    "text":
                        item["word"].upper(),

                    "position":
                        (
                            "upper_right"
                            if len(graphics) % 2 == 0
                            else "upper_left"
                        ),

                    "animation_in":
                        "scale_in",

                    "animation_out":
                        "fade",

                    "anchor_words":
                        [item["word"]],

                    "importance":
                        6,
                }

                print(
                    f"   FALLBACK → "
                    f"{graphic['text']}"
                )

            else:

                print(
                    "   No meaningful concept → skipped"
                )

                continue

        graphic = add_timing(
            graphic,
            window,
        )

        if graphic is None:

            print(
                "   Could not determine timing"
            )

            continue

        if is_duplicate(
            graphic,
            graphics,
        ):

            print(
                f"   Duplicate → "
                f"{graphic['concept']}"
            )

            continue

        graphics.append(
            graphic
        )

        print(
            f"   + "
            f"{graphic['graphic_type']} | "
            f"{graphic['text']}"
        )

        print(
            f"     "
            f"{graphic['speech_start']:.2f}s → "
            f"{graphic['speech_end']:.2f}s"
        )

        if len(graphics) >= MAX_GRAPHICS:

            break

    # ========================================================
    # SORT
    # ========================================================

    graphics.sort(
        key=lambda x:
            x["speech_start"]
    )

    # ========================================================
    # SECONDARY FALLBACK
    #
    # If AI still produces fewer than 8,
    # create graphics directly from important
    # concepts that have not already been used.
    # ========================================================

    if len(graphics) < MIN_GRAPHICS:

        print()
        print(
            "AI produced fewer than 8 graphics."
        )

        print(
            "Running deterministic concept pass..."
        )

        used_concepts = {
            normalize(
                g["concept"]
            )
            for g in graphics
        }

        for window in windows:

            important = important_words(
                window
            )

            for item in important:

                concept = normalize(
                    item["word"]
                )

                if not concept:
                    continue

                if concept in used_concepts:
                    continue

                candidate = {
                    "concept":
                        item["word"],

                    "reason":
                        "Important concept detected in speech",

                    "graphic_type":
                        "emphasis",

                    "text":
                        item["word"].upper(),

                    "position":
                        (
                            "upper_left"
                            if len(graphics) % 2 == 0
                            else "upper_right"
                        ),

                    "animation_in":
                        "scale_in",

                    "animation_out":
                        "fade",

                    "anchor_words":
                        [item["word"]],

                    "importance":
                        5,

                    "speech_start":
                        max(
                            0,
                            item["start"] - 0.12,
                        ),

                    "speech_end":
                        min(
                            words[-1]["end"] + 0.1,
                            item["end"] + 1.5,
                        ),
                }

                if is_duplicate(
                    candidate,
                    graphics,
                ):
                    continue

                graphics.append(
                    candidate
                )

                used_concepts.add(
                    concept
                )

                print(
                    f"   + FALLBACK: "
                    f"{candidate['text']}"
                )

                if len(graphics) >= MAX_GRAPHICS:
                    break

            if len(graphics) >= MAX_GRAPHICS:
                break

    # ========================================================
    # FINAL SORT
    # ========================================================

    graphics.sort(
        key=lambda x:
            x["speech_start"]
    )

    graphics = graphics[
        :MAX_GRAPHICS
    ]

    # ========================================================
    # PLAN
    # ========================================================

    plan = {

        "video_strategy": {

            "overall_style":
                "clean modern minimal educational motion graphics",

            "graphics_density":
                "controlled medium-high",

            "primary_position":
                "upper_right",

            "secondary_position":
                "upper_left",

            "preserve_original_video":
                True,

            "preserve_original_audio":
                True,

            "avoid_repetition":
                True,

            "minimum_graphic_gap":
                MIN_GRAPHIC_GAP,

            "maximum_graphics":
                MAX_GRAPHICS,

            "semantic_planning":
                True,

            "word_synchronized":
                True,

            "face_aware":
                True,

            "local_anchor_matching":
                True,

            "fallback_concept_detection":
                True,
        },

        "graphics":
            graphics,
    }

    # ========================================================
    # SAVE
    # ========================================================

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            plan,
            f,
            indent=2,
            ensure_ascii=False,
        )

    # ========================================================
    # COPY TO REMOTION
    # ========================================================

    REMOTION_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(
        OUTPUT_FILE,
        REMOTION_FILE,
    )

    # ========================================================
    # FINAL REPORT
    # ========================================================

    print()
    print("=" * 70)
    print("V3 PLANNING COMPLETE")
    print("=" * 70)
    print()

    print(
        f"Graphics generated : "
        f"{len(graphics)}"
    )

    print()

    for index, graphic in enumerate(
        graphics,
        start=1,
    ):

        print(
            f"{index:02d}. "
            f"{graphic['speech_start']:.2f}s → "
            f"{graphic['speech_end']:.2f}s | "
            f"{graphic['graphic_type']:12} | "
            f"{graphic['position']:12} | "
            f"{graphic['text']}"
        )

    print()

    print(
        "Plan saved:"
    )

    print(
        OUTPUT_FILE
    )

    print()

    print(
        "Remotion plan:"
    )

    print(
        REMOTION_FILE
    )

    print()

    if len(graphics) >= MIN_GRAPHICS:

        print(
            "SUCCESS: Enough graphics generated."
        )

    else:

        print(
            "WARNING: Still fewer than 8 graphics."
        )

    print()

    print("=" * 70)


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()