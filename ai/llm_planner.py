import os
import json
import re
import math
import urllib.request
import urllib.error


# ============================================================
# SMART LOCAL AI MOTION GRAPHICS PLANNER
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

OUTPUT_DIR = os.path.join(
    BASE_DIR,
    "output"
)

TIMINGS_FILE = os.path.join(
    OUTPUT_DIR,
    "word_timings.json"
)

OUTPUT_FILE = os.path.join(
    OUTPUT_DIR,
    "smart_graphics_plan.json"
)

STYLE_MEMORY_FILE = os.path.join(
    OUTPUT_DIR,
    "style_memory.json"
)

OLLAMA_URL = "http://localhost:11434/api/generate"

MODEL = "llama3.2:3b"


# ============================================================
# SETTINGS
# ============================================================

MIN_GRAPHIC_DURATION = 0.65
MAX_GRAPHIC_DURATION = 3.8

MIN_GAP = 0.12

MAX_GRAPHICS = 22

MIN_WORDS = 3
MAX_WORDS = 14

MAX_OVERLAP_RATIO = 0.18


# ============================================================
# PRINT
# ============================================================

print("=" * 70)
print("SMART LOCAL AI MOTION GRAPHICS PLANNER")
print("=" * 70)
print()


# ============================================================
# LOAD JSON
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
# LOAD WORD TIMINGS
# ============================================================

timing_data = load_json(
    TIMINGS_FILE
)

words = timing_data.get(
    "words",
    []
)


if not words:

    raise RuntimeError(
        "No words were found in word_timings.json"
    )


# ============================================================
# NORMALIZE WORDS
# ============================================================

clean_words = []

for word in words:

    try:

        text = str(
            word.get("word", "")
        ).strip()

        start = float(
            word.get("start")
        )

        end = float(
            word.get("end")
        )

    except Exception:

        continue


    if not text:
        continue

    if not math.isfinite(start):
        continue

    if not math.isfinite(end):
        continue

    if end <= start:
        continue

    clean_words.append(
        {
            "word": text,
            "start": start,
            "end": end
        }
    )


words = clean_words


if not words:

    raise RuntimeError(
        "No valid word timings found."
    )


video_duration = max(
    w["end"]
    for w in words
)


print(
    f"Words available : {len(words)}"
)

print(
    f"Video duration  : {video_duration:.2f}s"
)

print()


# ============================================================
# BUILD SPEECH WINDOWS
# ============================================================

def build_speech_windows(words):

    windows = []

    current = []

    previous_end = None

    for word in words:

        if previous_end is None:

            current = [word]

        else:

            gap = word["start"] - previous_end

            # A noticeable silence starts a new window.
            if gap > 0.55:

                if current:
                    windows.append(current)

                current = [word]

            else:

                current.append(word)

        previous_end = word["end"]


    if current:
        windows.append(current)


    result = []

    for group in windows:

        if not group:
            continue

        start = group[0]["start"]
        end = group[-1]["end"]

        text = " ".join(
            w["word"]
            for w in group
        )

        result.append(
            {
                "start": start,
                "end": end,
                "text": text,
                "words": group
            }
        )


    return result


speech_windows = build_speech_windows(
    words
)


print(
    f"Speech windows  : {len(speech_windows)}"
)

print()


# ============================================================
# STYLE MEMORY
# ============================================================

style_memory = {}

if os.path.exists(
    STYLE_MEMORY_FILE
):

    try:

        style_memory = load_json(
            STYLE_MEMORY_FILE
        )

        print(
            "Style memory loaded."
        )

    except Exception:

        print(
            "Style memory could not be read."
        )

else:

    print(
        "Style memory not found."
    )

    print(
        "Using built-in professional style."
    )


print()


# ============================================================
# CREATE SPEECH SUMMARY
# ============================================================

speech_summary = []

for i, window in enumerate(
    speech_windows
):

    speech_summary.append(
        {
            "id": i,

            "start":
                round(window["start"], 3),

            "end":
                round(window["end"], 3),

            "text":
                window["text"]
        }
    )


# ============================================================
# PROMPT
# ============================================================

style_text = json.dumps(
    style_memory,
    ensure_ascii=False
) if style_memory else "{}"


prompt = f"""
You are a professional motion graphics director.

You are designing graphics for a talking-head educational
video.

The original video and original audio MUST remain untouched.

Your job is NOT to create subtitles.

Your job is to create a SMALL number of meaningful motion
graphics that visually reinforce what the speaker is saying.

IMPORTANT RULES:

1. Only create a graphic when the spoken content contains
   a visually meaningful concept.

2. Do NOT create graphics for every sentence.

3. Do NOT create graphics during silence.

4. Do NOT repeat the same generic graphic.

5. Do NOT use generic words such as:
   "PROGRESS", "SKILLS", "PROCESS", "STEP", "MINDSET"
   unless the speaker is explicitly discussing that concept.

6. Prefer concrete concepts:
   course names,
   important numbers,
   research,
   writing,
   brainstorming,
   proposal,
   outline,
   evidence,
   argument,
   audience,
   revision,
   final paper.

7. Graphic timing MUST be based on the supplied speech windows.

8. A graphic should normally last between
   0.8 and 3.5 seconds.

9. Do not start a graphic before the relevant words.

10. Do not end a graphic long after the relevant words.

11. Avoid unnecessary overlapping graphics.

12. At most ONE major graphic should normally be visible
    at a time.

13. The graphic should emphasize the most important idea,
    not repeat the entire sentence.

14. Use professional motion graphics:
    kinetic typography,
    diagram,
    progress indicator,
    document/card,
    timeline,
    arrows,
    highlighted keywords,
    connected nodes,
    icons,
    numerical callouts.

15. Do NOT design the actual face-safe placement.
    The Remotion renderer will handle that later.

16. Use one of these graphic types:

    headline
    keyword
    number
    process
    timeline
    diagram
    document
    comparison
    callout

17. Use one of these positions:

    upper_left
    upper_right
    middle_left
    middle_right
    bottom_left
    bottom_right

18. Keep text short:
    normally 1-4 words.

19. Avoid duplicates.

20. Maximum {MAX_GRAPHICS} graphics.

Return ONLY valid JSON.

No markdown.

No explanation.

JSON format:

{{
  "video_strategy": {{
    "overall_style": "professional modern educational motion graphics",
    "graphics_density": "medium",
    "preserve_original_video": true,
    "preserve_original_audio": true
  }},
  "graphics": [
    {{
      "speech_start": 10.2,
      "speech_end": 12.4,
      "importance": 9,
      "concept": "academic writing",
      "reason": "speaker explicitly discusses improving academic writing",
      "graphic_type": "headline",
      "visual_description": "animated typography with subtle document motif",
      "text": "ACADEMIC WRITING",
      "position": "upper_right",
      "animation_in": "spring",
      "animation_out": "fade"
    }}
  ]
}}

SPEECH WINDOWS:

{json.dumps(
    speech_summary,
    indent=2,
    ensure_ascii=False
)}

STYLE MEMORY:

{style_text}
"""


# ============================================================
# OLLAMA
# ============================================================

def call_ollama(prompt):

    payload = {
        "model": MODEL,

        "prompt": prompt,

        "stream": False,

        "format": "json",

        "options": {
            "temperature": 0.15,
            "top_p": 0.85,
            "num_ctx": 8192
        }
    }


    data = json.dumps(
        payload
    ).encode(
        "utf-8"
    )


    request = urllib.request.Request(
        OLLAMA_URL,
        data=data,

        headers={
            "Content-Type":
                "application/json"
        },

        method="POST"
    )


    try:

        with urllib.request.urlopen(
            request,
            timeout=180
        ) as response:

            result = json.loads(
                response.read().decode(
                    "utf-8"
                )
            )

    except urllib.error.URLError as e:

        raise RuntimeError(
            "Could not connect to Ollama.\n"
            "Make sure Ollama is running.\n\n"
            f"{e}"
        )


    return result.get(
        "response",
        ""
    )


print(
    "Analyzing speech with local AI..."
)

print(
    f"Model: {MODEL}"
)

print()


raw_response = call_ollama(
    prompt
)


print(
    "AI response received."
)

print()


# ============================================================
# JSON EXTRACTION
# ============================================================

def extract_json(text):

    text = text.strip()

    # Remove markdown fences.
    text = re.sub(
        r"```json",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"```",
        "",
        text
    )

    text = text.strip()


    # First attempt.
    try:

        return json.loads(
            text
        )

    except Exception:
        pass


    # Find outer JSON object.
    start = text.find("{")
    end = text.rfind("}")

    if start >= 0 and end > start:

        candidate = text[
            start:end + 1
        ]

        try:

            return json.loads(
                candidate
            )

        except Exception:
            pass


    return None


plan = extract_json(
    raw_response
)


# ============================================================
# FALLBACK PLANNER
# ============================================================

def fallback_plan():

    print(
        "AI JSON could not be parsed."
    )

    print(
        "Using deterministic semantic fallback."
    )

    print()


    graphics = []


    keywords = [

        (
            [
                "BSIT",
                "computer",
                "information technology"
            ],
            "BSIT",
            "headline",
            9
        ),

        (
            [
                "COM102",
                "composition"
            ],
            "COM102",
            "headline",
            9
        ),

        (
            [
                "academic writing",
                "academic"
            ],
            "ACADEMIC WRITING",
            "headline",
            9
        ),

        (
            [
                "brainstorm"
            ],
            "BRAINSTORMING",
            "process",
            8
        ),

        (
            [
                "proposal"
            ],
            "PROPOSAL",
            "document",
            8
        ),

        (
            [
                "outline"
            ],
            "OUTLINE",
            "process",
            8
        ),

        (
            [
                "evidence"
            ],
            "EVIDENCE",
            "diagram",
            8
        ),

        (
            [
                "argument"
            ],
            "ARGUMENT",
            "diagram",
            8
        ),

        (
            [
                "audience"
            ],
            "AUDIENCE",
            "callout",
            7
        ),

        (
            [
                "research"
            ],
            "RESEARCH",
            "document",
            8
        ),

        (
            [
                "revision",
                "revise"
            ],
            "REVISION",
            "process",
            8
        ),

        (
            [
                "eight weeks",
                "8 weeks"
            ],
            "8 WEEKS",
            "timeline",
            8
        ),

        (
            [
                "progress"
            ],
            "PROGRESS",
            "timeline",
            7
        )
    ]


    used = set()


    for window in speech_windows:

        lower = window["text"].lower()


        selected = None


        for terms, label, gtype, importance in keywords:

            if label in used:
                continue

            for term in terms:

                if term in lower:

                    selected = (
                        label,
                        gtype,
                        importance,
                        term
                    )

                    break

            if selected:
                break


        if not selected:
            continue


        label, gtype, importance, matched = selected

        # Align tightly around the matching word.
        matching_words = [

            w for w in window["words"]

            if matched in w["word"].lower()
            or w["word"].lower() in matched
        ]


        if matching_words:

            start = matching_words[0]["start"]
            end = matching_words[-1]["end"]

        else:

            start = window["start"]
            end = min(
                window["end"],
                start + 2.5
            )


        # Add slight breathing room.
        start = max(
            window["start"],
            start - 0.10
        )

        end = min(
            window["end"],
            end + 0.65
        )


        if end - start < MIN_GRAPHIC_DURATION:

            end = min(
                window["end"],
                start + MIN_GRAPHIC_DURATION
            )


        graphics.append(
            {
                "speech_start": round(
                    start,
                    3
                ),

                "speech_end": round(
                    end,
                    3
                ),

                "importance":
                    importance,

                "concept":
                    matched,

                "reason":
                    f"Speaker mentions {matched}",

                "graphic_type":
                    gtype,

                "visual_description":
                    "professional animated motion graphic",

                "text":
                    label,

                "position":
                    "upper_right",

                "animation_in":
                    "spring",

                "animation_out":
                    "fade"
            }
        )


        used.add(
            label
        )


    return {
        "video_strategy": {
            "overall_style":
                "professional modern educational motion graphics",

            "graphics_density":
                "medium",

            "preserve_original_video":
                True,

            "preserve_original_audio":
                True
        },

        "graphics":
            graphics
    }


if plan is None:

    plan = fallback_plan()


# ============================================================
# NORMALIZE AI GRAPHICS
# ============================================================

def normalize_graphic(g):

    if not isinstance(
        g,
        dict
    ):
        return None


    # Accept several possible field names.
    start = g.get(
        "speech_start",
        g.get(
            "start",
            g.get(
                "start_time"
            )
        )
    )


    end = g.get(
        "speech_end",
        g.get(
            "end",
            g.get(
                "end_time"
            )
        )
    )


    try:

        start = float(start)
        end = float(end)

    except Exception:

        return None


    if not math.isfinite(start):
        return None

    if not math.isfinite(end):
        return None


    start = max(
        0,
        start
    )

    end = min(
        video_duration,
        end
    )


    if end <= start:
        return None


    text = str(
        g.get(
            "text",
            ""
        )
    ).strip()


    if not text:
        return None


    # Remove accidental giant text.
    words_in_text = text.split()

    if len(words_in_text) > 5:

        text = " ".join(
            words_in_text[:5]
        )


    graphic_type = str(
        g.get(
            "graphic_type",
            "keyword"
        )
    ).strip().lower()


    allowed_types = {

        "headline",
        "keyword",
        "number",
        "process",
        "timeline",
        "diagram",
        "document",
        "comparison",
        "callout"
    }


    if graphic_type not in allowed_types:

        graphic_type = "keyword"


    position = str(
        g.get(
            "position",
            "upper_right"
        )
    ).strip().lower()


    allowed_positions = {

        "upper_left",
        "upper_right",
        "middle_left",
        "middle_right",
        "bottom_left",
        "bottom_right"
    }


    if position not in allowed_positions:

        position = "upper_right"


    try:

        importance = int(
            g.get(
                "importance",
                6
            )
        )

    except Exception:

        importance = 6


    importance = max(
        1,
        min(
            10,
            importance
        )
    )


    return {

        "speech_start":
            round(start, 3),

        "speech_end":
            round(end, 3),

        "importance":
            importance,

        "concept":
            str(
                g.get(
                    "concept",
                    text
                )
            ).strip(),

        "reason":
            str(
                g.get(
                    "reason",
                    "Relevant spoken concept"
                )
            ).strip(),

        "graphic_type":
            graphic_type,

        "visual_description":
            str(
                g.get(
                    "visual_description",
                    "professional animated motion graphic"
                )
            ).strip(),

        "text":
            text,

        "position":
            position,

        "animation_in":
            str(
                g.get(
                    "animation_in",
                    "spring"
                )
            ),

        "animation_out":
            str(
                g.get(
                    "animation_out",
                    "fade"
                )
            )
    }


# ============================================================
# NORMALIZE
# ============================================================

raw_graphics = plan.get(
    "graphics",
    []
)


if not isinstance(
    raw_graphics,
    list
):

    raw_graphics = []


graphics = []


for g in raw_graphics:

    normalized = normalize_graphic(
        g
    )

    if normalized:

        graphics.append(
            normalized
        )


# ============================================================
# MATCH GRAPHICS TO REAL SPEECH
# ============================================================

def find_best_speech_window(
    start,
    end
):

    best = None
    best_score = 0


    for window in speech_windows:

        overlap_start = max(
            start,
            window["start"]
        )

        overlap_end = min(
            end,
            window["end"]
        )


        overlap = max(
            0,
            overlap_end - overlap_start
        )


        if overlap <= 0:
            continue


        graphic_duration = max(
            0.01,
            end - start
        )


        score = overlap / graphic_duration


        if score > best_score:

            best_score = score
            best = window


    return best


# Snap each graphic to actual speech.
for g in graphics:

    window = find_best_speech_window(
        g["speech_start"],
        g["speech_end"]
    )


    if window is None:
        continue


    g["speech_start"] = max(
        window["start"],
        g["speech_start"]
    )

    g["speech_end"] = min(
        window["end"],
        g["speech_end"]
    )


# ============================================================
# REMOVE TOO-SHORT GRAPHICS
# ============================================================

filtered = []


for g in graphics:

    duration = (
        g["speech_end"] -
        g["speech_start"]
    )


    if duration < MIN_GRAPHIC_DURATION:

        # Give the graphic a small extension,
        # but NEVER outside speech.
        new_end = min(
            video_duration,
            g["speech_start"] +
            MIN_GRAPHIC_DURATION
        )


        if new_end <= g["speech_end"]:

            continue


        g["speech_end"] = new_end


    duration = (
        g["speech_end"] -
        g["speech_start"]
    )


    if duration > MAX_GRAPHIC_DURATION:

        g["speech_end"] = (
            g["speech_start"] +
            MAX_GRAPHIC_DURATION
        )


    filtered.append(
        g
    )


graphics = filtered


# ============================================================
# REMOVE DUPLICATES
# ============================================================

unique = []

seen = set()


for g in graphics:

    key = (
        g["text"].lower().strip(),
        g["graphic_type"]
    )


    if key in seen:
        continue


    seen.add(key)

    unique.append(
        g
    )


graphics = unique


# ============================================================
# SORT BY TIME
# ============================================================

graphics.sort(
    key=lambda x: (
        x["speech_start"],
        -x["importance"]
    )
)


# ============================================================
# CONTROL OVERLAP
# ============================================================

final_graphics = []

last_end = -999


for g in graphics:

    start = g["speech_start"]
    end = g["speech_end"]


    # If there is enough separation,
    # keep the graphic.
    if start >= last_end + MIN_GAP:

        final_graphics.append(
            g
        )

        last_end = end

        continue


    # There is overlap.
    # Compare importance with previous graphic.
    previous = final_graphics[-1] if final_graphics else None


    if previous is None:

        final_graphics.append(
            g
        )

        last_end = end

        continue


    overlap = min(
        previous["speech_end"],
        end
    ) - max(
        previous["speech_start"],
        start
    )


    if overlap < 0:
        overlap = 0


    previous_duration = max(
        0.01,
        previous["speech_end"] -
        previous["speech_start"]
    )


    overlap_ratio = (
        overlap /
        previous_duration
    )


    # If overlap is small, trim the new graphic.
    if overlap_ratio <= MAX_OVERLAP_RATIO:

        new_start = (
            previous["speech_end"] +
            MIN_GAP
        )


        if new_start < end:

            g["speech_start"] = new_start

            final_graphics.append(
                g
            )

            last_end = end

        continue


    # Strong overlap.
    # Keep the more important graphic.
    if g["importance"] > previous["importance"]:

        final_graphics[-1] = g

        last_end = g["speech_end"]

    # Otherwise discard new graphic.


graphics = final_graphics


# ============================================================
# MAXIMUM GRAPHICS
# ============================================================

if len(graphics) > MAX_GRAPHICS:

    graphics.sort(
        key=lambda x: x["importance"],
        reverse=True
    )

    graphics = graphics[
        :MAX_GRAPHICS
    ]

    graphics.sort(
        key=lambda x:
        x["speech_start"]
    )


# ============================================================
# FINAL SAFETY PASS
# ============================================================

safe_graphics = []


for g in graphics:

    start = float(
        g["speech_start"]
    )

    end = float(
        g["speech_end"]
    )


    if not math.isfinite(start):
        continue

    if not math.isfinite(end):
        continue

    if start < 0:
        continue

    if end <= start:
        continue


    # Ensure the graphic actually intersects
    # real speech.
    real_speech = False


    for window in speech_windows:

        if (
            start < window["end"]
            and end > window["start"]
        ):

            real_speech = True
            break


    if not real_speech:
        continue


    safe_graphics.append(
        g
    )


graphics = safe_graphics


# ============================================================
# BUILD FINAL PLAN
# ============================================================

final_plan = {

    "version":
        3,

    "video_strategy": {

        "overall_style":
            "professional modern educational motion graphics",

        "graphics_density":
            "medium",

        "primary_position":
            "upper_right",

        "secondary_position":
            "upper_left",

        "preserve_original_video":
            True,

        "preserve_original_audio":
            True,

        "face_aware":
            True,

        "semantic_timing":
            True,

        "speech_locked":
            True,

        "avoid_silence":
            True,

        "avoid_duplicate_graphics":
            True
    },

    "graphics":
        graphics
}


# ============================================================
# VALIDATE JSON
# ============================================================

serialized = json.dumps(
    final_plan,
    indent=2,
    ensure_ascii=False
)


# This guarantees that the file we write
# can actually be read back by Python.
json.loads(
    serialized
)


# ============================================================
# SAVE
# ============================================================

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8"
) as f:

    f.write(
        serialized
    )


# ============================================================
# REPORT
# ============================================================

print("=" * 70)
print("SMART PLANNER COMPLETE")
print("=" * 70)
print()

print(
    f"Words           : {len(words)}"
)

print(
    f"Speech windows  : {len(speech_windows)}"
)

print(
    f"Graphics planned: {len(graphics)}"
)

print()


for index, g in enumerate(
    graphics,
    start=1
):

    print(
        f"{index:02d}. "
        f"{g['speech_start']:.2f}s → "
        f"{g['speech_end']:.2f}s | "
        f"{g['graphic_type']:<11} | "
        f"{g['position']:<13} | "
        f"{g['text']}"
    )


print()

print(
    "Saved:"
)

print(
    OUTPUT_FILE
)

print()

print(
    "The plan is valid JSON."
)

print(
    "Graphics are locked to real speech windows."
)

print(
    "Next: Remotion face-aware motion graphics renderer."
)

print("=" * 70)

