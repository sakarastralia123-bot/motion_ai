import cv2
import json
import os
import numpy as np
from pathlib import Path


# ============================================================
# CONFIG
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

INPUT_DIR = PROJECT_ROOT / "input" / "videos"
OUTPUT_DIR = PROJECT_ROOT / "output"

ANALYSIS_FILE = OUTPUT_DIR / "input_video_analysis.json"

SAMPLE_FPS = 2.0


# ============================================================
# HELPERS
# ============================================================

def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def safe_mean(values):
    return float(np.mean(values)) if values else 0.0


def percentile(values, p):
    return float(np.percentile(values, p)) if values else 0.0


def calculate_edge_density(gray):
    edges = cv2.Canny(gray, 100, 200)
    return float(np.mean(edges > 0))


def calculate_motion(previous_gray, current_gray):
    if previous_gray is None:
        return 0.0

    diff = cv2.absdiff(previous_gray, current_gray)

    return float(np.mean(diff))


def analyze_regions(gray):
    """
    Analyze different parts of the frame.

    This helps us later decide where motion graphics
    can safely be placed.
    """

    h, w = gray.shape

    regions = {
        "top": gray[:int(h * 0.30), :],
        "middle": gray[int(h * 0.30):int(h * 0.70), :],
        "bottom": gray[int(h * 0.70):, :],

        "left": gray[:, :int(w * 0.35)],
        "center": gray[:, int(w * 0.35):int(w * 0.65)],
        "right": gray[:, int(w * 0.65):],
    }

    result = {}

    for name, region in regions.items():
        result[name] = {
            "brightness": float(np.mean(region)),
            "edge_density": calculate_edge_density(region)
        }

    return result


def calculate_scene_change(previous_gray, current_gray):
    if previous_gray is None:
        return 0.0

    diff = cv2.absdiff(previous_gray, current_gray)

    return float(np.mean(diff))


# ============================================================
# VIDEO ANALYSIS
# ============================================================

def analyze_video(video_path):

    print()
    print("=" * 70)
    print("INPUT VIDEO ANALYZER")
    print("=" * 70)
    print()
    print(f"Video: {video_path}")
    print()

    cap = cv2.VideoCapture(str(video_path))

    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)

    if fps <= 0:
        fps = 30.0

    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    duration = frame_count / fps if fps else 0

    print(f"Resolution : {width} x {height}")
    print(f"FPS        : {fps:.2f}")
    print(f"Frames     : {frame_count}")
    print(f"Duration   : {duration:.2f} seconds")

    orientation = "vertical" if height > width else "horizontal"

    aspect_ratio = width / height if height else 0

    # --------------------------------------------------------
    # Sampling
    # --------------------------------------------------------

    sample_interval = max(1, int(fps / SAMPLE_FPS))

    brightness_values = []
    saturation_values = []
    motion_values = []
    edge_values = []
    scene_change_values = []

    region_samples = []

    timestamps = []

    previous_gray = None

    frame_number = 0

    print()
    print("Analyzing frames...")

    while True:

        ret, frame = cap.read()

        if not ret:
            break

        if frame_number % sample_interval != 0:
            frame_number += 1
            continue

        timestamp = frame_number / fps

        # ----------------------------------------------------
        # Resize for analysis
        # ----------------------------------------------------

        small = cv2.resize(frame, (320, 568))

        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)

        hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)

        # ----------------------------------------------------
        # Basic visual properties
        # ----------------------------------------------------

        brightness = float(np.mean(gray))

        saturation = float(np.mean(hsv[:, :, 1]))

        edge_density = calculate_edge_density(gray)

        motion = calculate_motion(previous_gray, gray)

        scene_change = calculate_scene_change(
            previous_gray,
            gray
        )

        # ----------------------------------------------------
        # Store
        # ----------------------------------------------------

        brightness_values.append(brightness)
        saturation_values.append(saturation)
        edge_values.append(edge_density)
        motion_values.append(motion)
        scene_change_values.append(scene_change)

        timestamps.append(timestamp)

        region_samples.append(
            analyze_regions(gray)
        )

        previous_gray = gray.copy()

        frame_number += 1

    cap.release()

    # ========================================================
    # SCENE CHANGE DETECTION
    # ========================================================

    scene_threshold = max(
        25.0,
        percentile(scene_change_values, 90)
    )

    scene_changes = []

    for i, value in enumerate(scene_change_values):

        if value >= scene_threshold:

            if i < len(timestamps):

                scene_changes.append({
                    "timestamp": round(timestamps[i], 3),
                    "strength": round(value, 3)
                })

    # Avoid multiple detections very close together

    filtered_scene_changes = []

    for scene in scene_changes:

        if not filtered_scene_changes:

            filtered_scene_changes.append(scene)
            continue

        previous = filtered_scene_changes[-1]

        if scene["timestamp"] - previous["timestamp"] >= 0.75:

            filtered_scene_changes.append(scene)

    # ========================================================
    # REGION ANALYSIS
    # ========================================================

    region_summary = {}

    if region_samples:

        region_names = region_samples[0].keys()

        for name in region_names:

            brightness = [
                sample[name]["brightness"]
                for sample in region_samples
            ]

            edges = [
                sample[name]["edge_density"]
                for sample in region_samples
            ]

            region_summary[name] = {
                "brightness": round(
                    safe_mean(brightness), 3
                ),
                "edge_density": round(
                    safe_mean(edges), 5
                )
            }

    # ========================================================
    # GRAPHICS-SAFE AREA ESTIMATION
    # ========================================================

    # Lower edge density usually means there is less visual
    # information in that region.
    #
    # This is NOT yet object detection.
    # It is simply a first approximation.

    candidate_regions = []

    for name, data in region_summary.items():

        score = (
            (255 - data["brightness"]) * 0.20
            +
            (1 - data["edge_density"]) * 100
        )

        candidate_regions.append({
            "region": name,
            "score": round(float(score), 3)
        })

    candidate_regions.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    # ========================================================
    # MOTION LEVEL
    # ========================================================

    mean_motion = safe_mean(motion_values)

    p50_motion = percentile(
        motion_values,
        50
    )

    p90_motion = percentile(
        motion_values,
        90
    )

    if mean_motion < 5:
        motion_level = "very_low"

    elif mean_motion < 15:
        motion_level = "low"

    elif mean_motion < 30:
        motion_level = "medium"

    elif mean_motion < 60:
        motion_level = "high"

    else:
        motion_level = "very_high"

    # ========================================================
    # VISUAL DENSITY
    # ========================================================

    mean_edges = safe_mean(edge_values)

    if mean_edges < 0.025:
        visual_density = "very_low"

    elif mean_edges < 0.045:
        visual_density = "low"

    elif mean_edges < 0.070:
        visual_density = "medium"

    elif mean_edges < 0.100:
        visual_density = "high"

    else:
        visual_density = "very_high"

    # ========================================================
    # COMPLETE RESULT
    # ========================================================

    result = {

        "video": {
            "filename": video_path.name,
            "path": str(video_path),
            "width": width,
            "height": height,
            "fps": round(float(fps), 3),
            "frame_count": frame_count,
            "duration": round(float(duration), 3),
            "orientation": orientation,
            "aspect_ratio": round(float(aspect_ratio), 5)
        },

        "visual_analysis": {

            "brightness": {
                "mean": round(
                    safe_mean(brightness_values),
                    3
                ),
                "p10": round(
                    percentile(brightness_values, 10),
                    3
                ),
                "p90": round(
                    percentile(brightness_values, 90),
                    3
                )
            },

            "saturation": {
                "mean": round(
                    safe_mean(saturation_values),
                    3
                )
            },

            "edge_density": round(
                mean_edges,
                5
            ),

            "visual_density": visual_density,

            "motion": {
                "mean": round(
                    mean_motion,
                    3
                ),
                "p50": round(
                    p50_motion,
                    3
                ),
                "p90": round(
                    p90_motion,
                    3
                ),
                "level": motion_level
            }
        },

        "regions": region_summary,

        "graphics_placement": {
            "best_candidate_regions": candidate_regions[:6]
        },

        "scene_changes": {
            "count": len(filtered_scene_changes),
            "timestamps": filtered_scene_changes
        },

        "sampling": {
            "sample_fps": SAMPLE_FPS,
            "samples": len(timestamps)
        }
    }

    return result


# ============================================================
# MAIN
# ============================================================

def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    INPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    videos = []

    for extension in [
        "*.mp4",
        "*.mov",
        "*.mkv",
        "*.avi"
    ]:

        videos.extend(
            INPUT_DIR.glob(extension)
        )

    if not videos:

        print()
        print("ERROR: No input video found.")
        print()
        print("Put your video inside:")
        print(INPUT_DIR)
        print()

        return

    # For now, analyze the first video.
    video_path = videos[0]

    result = analyze_video(video_path)

    with open(
        ANALYSIS_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            result,
            f,
            indent=4
        )

    print()
    print("=" * 70)
    print("ANALYSIS COMPLETE")
    print("=" * 70)

    print()
    print(f"Motion level   : {result['visual_analysis']['motion']['level']}")
    print(
        f"Visual density : "
        f"{result['visual_analysis']['visual_density']}"
    )

    print(
        f"Scene changes  : "
        f"{result['scene_changes']['count']}"
    )

    print()
    print("Best graphics placement areas:")

    for region in result["graphics_placement"]["best_candidate_regions"][:4]:

        print(
            f"  {region['region']:10s} "
            f"score={region['score']}"
        )

    print()
    print(f"Analysis saved to:")
    print(ANALYSIS_FILE)
    print()


if __name__ == "__main__":
    main()