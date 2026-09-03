import cv2
import json
import os


# ============================================================
# SETTINGS
# ============================================================

VIDEO_PATH = r"C:\Users\acer\Desktop\motion_ai\input\videos\Video.mp4"

OUTPUT_PATH = r"C:\Users\acer\Desktop\motion_ai\output\face_safe_zones.json"

SAMPLE_EVERY_SECONDS = 0.5

FACE_PADDING = 0.35


# ============================================================
# HELPERS
# ============================================================

def clamp(value, minimum=0.0, maximum=1.0):
    return max(minimum, min(maximum, value))


def expand_box(x, y, w, h, frame_width, frame_height):

    pad_x = w * FACE_PADDING
    pad_y = h * FACE_PADDING

    x1 = max(0, x - pad_x)
    y1 = max(0, y - pad_y)

    x2 = min(frame_width, x + w + pad_x)
    y2 = min(frame_height, y + h + pad_y)

    return {
        "x": round(x1 / frame_width, 4),
        "y": round(y1 / frame_height, 4),
        "width": round((x2 - x1) / frame_width, 4),
        "height": round((y2 - y1) / frame_height, 4),
    }


def intersects(a, b):

    ax1 = a["x"]
    ay1 = a["y"]
    ax2 = ax1 + a["width"]
    ay2 = ay1 + a["height"]

    bx1 = b["x"]
    by1 = b["y"]
    bx2 = bx1 + b["width"]
    by2 = by1 + b["height"]

    return not (
        ax2 <= bx1
        or ax1 >= bx2
        or ay2 <= by1
        or ay1 >= by2
    )


# ============================================================
# CHECK OPENCV
# ============================================================

print("=" * 70)
print("FACE DETECTION / SAFE GRAPHICS ANALYZER")
print("=" * 70)

print()

print("OpenCV version:", cv2.__version__)

if not hasattr(cv2, "FaceDetectorYN_create"):

    raise RuntimeError(
        "This OpenCV installation does not contain "
        "FaceDetectorYN_create()."
    )

print("FaceDetectorYN API: available")

print()


# ============================================================
# DOWNLOAD / LOCATE FACE MODEL
# ============================================================

MODEL_DIR = os.path.join(
    os.path.dirname(__file__),
    "models"
)

os.makedirs(MODEL_DIR, exist_ok=True)

MODEL_PATH = os.path.join(
    MODEL_DIR,
    "face_detection_yunet_2023mar.onnx"
)


# YuNet model URL
MODEL_URL = (
    "https://github.com/opencv/opencv_zoo/"
    "raw/main/models/face_detection_yunet/"
    "face_detection_yunet_2023mar.onnx"
)


if not os.path.exists(MODEL_PATH):

    print("Face model not found.")
    print()
    print("Downloading YuNet face detector...")
    print()

    import urllib.request

    try:

        urllib.request.urlretrieve(
            MODEL_URL,
            MODEL_PATH
        )

    except Exception as e:

        raise RuntimeError(
            "Could not download the YuNet face detector.\n"
            "Internet connection is required the first time.\n\n"
            f"Error: {e}"
        )

    print("Face model downloaded.")


# ============================================================
# OPEN VIDEO
# ============================================================

if not os.path.exists(VIDEO_PATH):

    raise FileNotFoundError(
        f"Video not found:\n{VIDEO_PATH}"
    )


cap = cv2.VideoCapture(VIDEO_PATH)

if not cap.isOpened():

    raise RuntimeError(
        "Could not open video."
    )


fps = cap.get(
    cv2.CAP_PROP_FPS
)

frame_count = int(
    cap.get(cv2.CAP_PROP_FRAME_COUNT)
)

width = int(
    cap.get(cv2.CAP_PROP_FRAME_WIDTH)
)

height = int(
    cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
)

duration = (
    frame_count / fps
    if fps > 0
    else 0
)


print("Video:")
print(VIDEO_PATH)
print()

print(f"Resolution : {width} x {height}")
print(f"FPS        : {fps:.2f}")
print(f"Frames     : {frame_count}")
print(f"Duration   : {duration:.2f} seconds")
print()


# ============================================================
# CREATE YUNET DETECTOR
# ============================================================

detector = cv2.FaceDetectorYN_create(
    MODEL_PATH,
    "",
    (width, height),
    0.6,
    0.3,
    5000
)


# ============================================================
# ANALYZE VIDEO
# ============================================================

sample_every_frames = max(
    1,
    int(fps * SAMPLE_EVERY_SECONDS)
)


face_timeline = []

frame_number = 0

while True:

    ret, frame = cap.read()

    if not ret:
        break

    if frame_number % sample_every_frames != 0:

        frame_number += 1
        continue

    timestamp = (
        frame_number / fps
    )

    detector.setInputSize(
        (width, height)
    )

    _, faces = detector.detect(
        frame
    )

    detected_faces = []

    if faces is not None:

        for face in faces:

            # YuNet output:
            #
            # face[0] = x
            # face[1] = y
            # face[2] = width
            # face[3] = height
            #
            # face[14] = confidence

            x = float(face[0])
            y = float(face[1])

            w = float(face[2])
            h = float(face[3])

            confidence = float(
                face[-1]
            )

            if confidence < 0.50:
                continue

            safe_box = expand_box(
                x,
                y,
                w,
                h,
                width,
                height
            )

            safe_box["confidence"] = round(
                confidence,
                4
            )

            detected_faces.append(
                safe_box
            )


    # Largest face first
    detected_faces.sort(
        key=lambda box:
        box["width"] *
        box["height"],
        reverse=True
    )


    face_timeline.append(
        {
            "time": round(
                timestamp,
                3
            ),

            "face_count":
                len(detected_faces),

            "faces":
                detected_faces,
        }
    )


    frame_number += 1


cap.release()


# ============================================================
# GRAPHICS POSITIONS
# ============================================================

candidate_boxes = {

    "upper_left": {
        "x": 0.04,
        "y": 0.07,
        "width": 0.35,
        "height": 0.22,
    },

    "upper_right": {
        "x": 0.61,
        "y": 0.07,
        "width": 0.35,
        "height": 0.22,
    },

    "middle_left": {
        "x": 0.04,
        "y": 0.39,
        "width": 0.35,
        "height": 0.22,
    },

    "middle_right": {
        "x": 0.61,
        "y": 0.39,
        "width": 0.35,
        "height": 0.22,
    },

    "bottom_left": {
        "x": 0.04,
        "y": 0.70,
        "width": 0.35,
        "height": 0.22,
    },

    "bottom_right": {
        "x": 0.61,
        "y": 0.70,
        "width": 0.35,
        "height": 0.22,
    },
}


positions = list(
    candidate_boxes.keys()
)


# ============================================================
# DETERMINE SAFE POSITIONS
# ============================================================

safe_position_timeline = []


for sample in face_timeline:

    faces = sample["faces"]

    if not faces:

        safe_position_timeline.append(
            {
                "time": sample["time"],

                "safe_positions":
                    positions,

                "blocked_positions":
                    [],

                "face":
                    None,
            }
        )

        continue


    main_face = faces[0]

    blocked = []


    for position in positions:

        graphic_box = candidate_boxes[
            position
        ]

        if intersects(
            graphic_box,
            main_face
        ):

            blocked.append(
                position
            )


    safe = [
        p
        for p in positions
        if p not in blocked
    ]


    # If all positions are blocked,
    # allow the least dangerous positions.
    if not safe:

        safe = [
            p
            for p in positions
            if p not in blocked[:4]
        ]


    safe_position_timeline.append(
        {
            "time": sample["time"],

            "safe_positions":
                safe,

            "blocked_positions":
                blocked,

            "face":
                main_face,
        }
    )


# ============================================================
# SAVE RESULTS
# ============================================================

output = {

    "version": 2,

    "video": {

        "path":
            VIDEO_PATH,

        "width":
            width,

        "height":
            height,

        "fps":
            fps,

        "duration":
            duration,
    },

    "detector": {

        "method":
            "YuNet",

        "sample_interval_seconds":
            SAMPLE_EVERY_SECONDS,

        "face_padding":
            FACE_PADDING,
    },

    "face_timeline":
        face_timeline,

    "safe_position_timeline":
        safe_position_timeline,

    "graphics_rules": {

        "avoid_face":
            True,

        "prefer_empty_space":
            True,

        "dynamic_positioning":
            True,

        "preserve_original_video":
            True,

        "preserve_original_audio":
            True,
    },
}


os.makedirs(
    os.path.dirname(OUTPUT_PATH),
    exist_ok=True
)


with open(
    OUTPUT_PATH,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        output,
        f,
        indent=2
    )


# ============================================================
# SUMMARY
# ============================================================

total_samples = len(
    face_timeline
)

samples_with_faces = sum(
    1
    for sample in face_timeline
    if sample["face_count"] > 0
)


print()
print("=" * 70)
print("FACE DETECTION COMPLETE")
print("=" * 70)

print()

print(
    f"Samples analyzed : {total_samples}"
)

print(
    f"Samples with face : {samples_with_faces}"
)


if total_samples:

    coverage = (
        samples_with_faces /
        total_samples
    ) * 100

    print(
        f"Face coverage    : {coverage:.1f}%"
    )


print()

print(
    "Output saved to:"
)

print(
    OUTPUT_PATH
)

print()

print(
    "The face-safe placement data is ready "
    "for the Remotion renderer."
)