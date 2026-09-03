import os
import json
import subprocess
import whisper


BASE = r"C:\Users\acer\Desktop\motion_ai"

VIDEO = os.path.join(
    BASE,
    "input",
    "videos",
    "Video.mp4"
)

OUTPUT = os.path.join(
    BASE,
    "output",
    "transcript.json"
)

AUDIO = os.path.join(
    BASE,
    "output",
    "_transcription_audio.wav"
)


print("=" * 70)
print("WORD-SYNCHRONIZED TRANSCRIPTION")
print("=" * 70)

print()
print("Extracting audio...")


# ------------------------------------------------------------
# Extract audio
# ------------------------------------------------------------

cmd = [
    "ffmpeg",
    "-y",
    "-i",
    VIDEO,
    "-vn",
    "-ac",
    "1",
    "-ar",
    "16000",
    "-af",
    "apad=pad_dur=2",
    AUDIO
]

result = subprocess.run(
    cmd,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL
)

if result.returncode != 0:
    print("ERROR: Could not extract audio.")
    raise SystemExit(1)


# ------------------------------------------------------------
# Whisper
# ------------------------------------------------------------

print("Loading Whisper model...")

model = whisper.load_model("base")

print("Transcribing with WORD timestamps...")
print()


result = model.transcribe(
    AUDIO,

    language="en",

    fp16=False,

    word_timestamps=True,

    temperature=0,

    no_speech_threshold=0.35,

    logprob_threshold=-1.0,

    compression_ratio_threshold=2.4
)


# ------------------------------------------------------------
# Build clean word-level transcript
# ------------------------------------------------------------

segments = []

for segment in result.get("segments", []):

    words = []

    for word in segment.get("words", []):

        text = word.get("word", "").strip()

        if not text:
            continue

        start = float(
            word.get(
                "start",
                segment["start"]
            )
        )

        end = float(
            word.get(
                "end",
                segment["end"]
            )
        )

        words.append({
            "word": text,
            "start": start,
            "end": end
        })


    segments.append({
        "start": float(segment["start"]),
        "end": float(segment["end"]),
        "text": segment["text"].strip(),
        "words": words
    })


# ------------------------------------------------------------
# Save
# ------------------------------------------------------------

data = {
    "language": result.get("language", "en"),
    "segments": segments
}


os.makedirs(
    os.path.dirname(OUTPUT),
    exist_ok=True
)


with open(
    OUTPUT,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        data,
        f,
        indent=2,
        ensure_ascii=False
    )


# ------------------------------------------------------------
# Statistics
# ------------------------------------------------------------

word_count = sum(
    len(s["words"])
    for s in segments
)


print("=" * 70)
print("TRANSCRIPTION COMPLETE")
print("=" * 70)

print()
print("Segments :", len(segments))
print("Words    :", word_count)

print()
print("Example word timing:")

shown = 0

for segment in segments:

    for word in segment["words"]:

        print(
            f'{word["start"]:6.2f}s → '
            f'{word["end"]:6.2f}s   '
            f'{word["word"]}'
        )

        shown += 1

        if shown >= 30:
            break

    if shown >= 30:
        break


print()
print("Saved:")
print(OUTPUT)