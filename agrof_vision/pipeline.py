"""Leaf health screening pipeline.

decode → normalise → capture quality → leaf segmentation → tissue
classification → lesion detection → annotated previews.

Everything here is classical computer vision with explainable thresholds.
It measures visible discolouration; it does not identify crops, diseases
or treatments.
"""

from __future__ import annotations

import base64
import os
import time
import uuid
from dataclasses import dataclass

# Refuse decompression bombs before OpenCV allocates memory for them.
os.environ.setdefault("OPENCV_IO_MAX_IMAGE_PIXELS", str(40_000_000))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

MAX_BYTES = 10 * 1024 * 1024
MIN_SIDE = 128
WORKING_SIDE = 1024
FOCUS_SIDE = 512

JPEG = b"\xff\xd8\xff"
PNG = b"\x89PNG\r\n\x1a\n"

DISCLAIMER = (
    "Visual indicators only — not a diagnosis. Yellowing and brown spots can come from disease, pests, "
    "nutrient deficiency, water stress, sun scorch or natural ageing. Confirm with an agronomist or "
    "extension officer before treating a crop."
)

# BGR colours for previews.
LEAF_EDGE = (91, 232, 196)
LESION_EDGE = (109, 77, 255)
TISSUE_COLOURS = {
    1: (106, 168, 47),  # healthy green
    2: (48, 194, 242),  # yellowing
    3: (30, 74, 156),  # browning
    4: (160, 165, 154),  # other (glare, pale)
}


class ImageError(ValueError):
    """The upload is not a usable image."""


@dataclass(frozen=True)
class Check:
    id: str
    label: str
    value: float
    unit: str
    status: str  # pass | warn | fail
    message: str

    def as_dict(self) -> dict:
        return self.__dict__ | {"value": round(self.value, 3)}


def is_supported(raw: bytes) -> bool:
    return raw.startswith(JPEG) or raw.startswith(PNG) or (raw[:4] == b"RIFF" and raw[8:12] == b"WEBP")


def decode(raw: bytes) -> np.ndarray:
    if not raw:
        raise ImageError("The file is empty.")
    if len(raw) > MAX_BYTES:
        raise ImageError("Images must be 10 MB or smaller.")
    if not is_supported(raw):
        raise ImageError("Upload a JPEG, PNG or WebP photo.")
    try:
        image = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)  # applies EXIF orientation
    except cv2.error:
        image = None
    if image is None:
        raise ImageError("The image could not be read. It may be damaged or too large.")
    h, w = image.shape[:2]
    if min(h, w) < MIN_SIDE:
        raise ImageError(f"The image is too small. Use a photo at least {MIN_SIDE} pixels on each side.")
    return image


def resize_max(image: np.ndarray, side: int) -> np.ndarray:
    h, w = image.shape[:2]
    scale = side / max(h, w)
    if scale >= 1:
        return image
    return cv2.resize(image, (round(w * scale), round(h * scale)), interpolation=cv2.INTER_AREA)


def _kernel(size: int) -> np.ndarray:
    size = max(3, size | 1)
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (size, size))


def _fill_holes(mask: np.ndarray) -> np.ndarray:
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    filled = np.zeros_like(mask)
    cv2.drawContours(filled, contours, -1, 255, cv2.FILLED)
    return filled


def colour_masks(image: np.ndarray) -> dict[str, np.ndarray]:
    """Per-pixel colour classes used by segmentation and tissue analysis."""
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    hue, sat, val = cv2.split(hsv)
    bgr = image.astype(np.float32)
    total = bgr.sum(axis=2) + 1e-6
    b, g, r = (bgr[..., i] / total for i in range(3))
    exg = 2 * g - r - b  # excess-green vegetation index

    # Otsu picks the vegetation/background split for this photo; the floor
    # stops it from splitting a frame that is entirely leaf.
    exg_u8 = np.clip((exg + 1) * 127.5, 0, 255).astype(np.uint8)
    otsu, _ = cv2.threshold(exg_u8, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    exg_cut = min(max(otsu / 127.5 - 1, 0.06), 0.25)

    bright_enough = (total > 60) & (val >= 30)
    green = (exg > exg_cut) & (hue >= 33) & (hue <= 90) & (sat >= 40) & bright_enough
    yellow = (hue >= 17) & (hue < 33) & (sat >= 70) & (val >= 110)
    brown = (((hue < 17) | (hue >= 165)) & (sat >= 40) & (val < 205)) | ((val < 70) & bright_enough)
    glare = (val >= 245) & (sat < 35)
    return {
        "green": green,
        "yellow": yellow & ~green,
        "brown": brown & ~green & ~yellow,
        "glare": glare,
        "exg_threshold": np.float32(exg_cut),
    }


def segment_leaf(image: np.ndarray, masks: dict[str, np.ndarray]) -> np.ndarray:
    """Leaf mask: green tissue, plus yellow tissue connected to it, closed and hole-filled."""
    h, w = image.shape[:2]
    green = masks["green"].astype(np.uint8) * 255
    green = cv2.morphologyEx(green, cv2.MORPH_OPEN, _kernel(3))
    plant = green | (masks["yellow"].astype(np.uint8) * 255)
    plant = cv2.morphologyEx(plant, cv2.MORPH_OPEN, _kernel(5))

    count, labels, stats, _ = cv2.connectedComponentsWithStats(plant, connectivity=8)
    if count <= 1:
        return np.zeros((h, w), np.uint8)
    green_per_label = np.bincount(labels.ravel(), weights=(green > 0).ravel(), minlength=count)
    areas = stats[:, cv2.CC_STAT_AREA]
    keep = np.zeros(count, bool)
    keep[1:] = (areas[1:] >= 0.01 * h * w) & (green_per_label[1:] >= 0.1 * areas[1:])
    leaf = np.where(keep[labels], 255, 0).astype(np.uint8)

    # Bridge lesions on the leaf and fill enclosed spots so they count as leaf.
    leaf = cv2.morphologyEx(leaf, cv2.MORPH_CLOSE, _kernel(round(max(h, w) * 0.02)))
    return _fill_holes(leaf)


def classify_tissue(leaf: np.ndarray, masks: dict[str, np.ndarray]) -> np.ndarray:
    """0 background, 1 healthy, 2 yellowing, 3 browning, 4 other."""
    inside = leaf > 0
    tissue = np.zeros(leaf.shape, np.uint8)
    tissue[inside] = 4
    tissue[inside & masks["brown"]] = 3
    tissue[inside & masks["yellow"]] = 2
    tissue[inside & masks["green"]] = 1
    return tissue


def find_lesions(tissue: np.ndarray, leaf_area: int) -> list[dict]:
    """Spot-like discoloured patches. Broad yellowing (e.g. a whole leaf tip)
    is reported through tissue shares instead, so it is not counted here."""
    lesion = np.where((tissue == 2) | (tissue == 3), 255, 0).astype(np.uint8)
    lesion = cv2.morphologyEx(lesion, cv2.MORPH_OPEN, _kernel(3))
    lesion = cv2.morphologyEx(lesion, cv2.MORPH_CLOSE, _kernel(5))  # rejoin patches split by veins
    count, _, stats, _ = cv2.connectedComponentsWithStats(lesion, connectivity=8)
    min_area = max(12, int(leaf_area * 0.0002))
    max_area = int(leaf_area * 0.03)
    found = [
        {
            "x": int(x),
            "y": int(y),
            "width": int(bw),
            "height": int(bh),
            "area_fraction": round(float(area) / leaf_area, 4),
        }
        for x, y, bw, bh, area in stats[1:count]
        if min_area <= area <= max_area
    ]
    return sorted(found, key=lambda item: item["area_fraction"], reverse=True)


def _status(value: float, good: tuple[float, float], ok: tuple[float, float]) -> str:
    if good[0] <= value <= good[1]:
        return "pass"
    if ok[0] <= value <= ok[1]:
        return "warn"
    return "fail"


def quality_checks(original: np.ndarray, image: np.ndarray, leaf: np.ndarray, masks: dict) -> list[Check]:
    h, w = image.shape[:2]
    lightness = float(cv2.cvtColor(image, cv2.COLOR_BGR2LAB)[..., 0].mean()) / 255
    has_leaf = bool(leaf.any())
    region = leaf > 0 if has_leaf else np.ones((h, w), bool)
    glare = float(masks["glare"][region].mean())
    coverage = float((leaf > 0).mean())

    # Focus is measured on the leaf's bounding box at a fixed scale, so photo
    # size and busy backgrounds do not skew it.
    if has_leaf:
        ys, xs = np.nonzero(leaf)
        crop = image[ys.min() : ys.max() + 1, xs.min() : xs.max() + 1]
    else:
        crop = image
    gray = cv2.cvtColor(resize_max(crop, FOCUS_SIDE), cv2.COLOR_BGR2GRAY)
    focus = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    short_side = min(original.shape[:2])

    exposure = _status(lightness, (0.25, 0.82), (0.16, 0.9))
    checks = [
        Check(
            "exposure",
            "Lighting",
            lightness * 100,
            "%",
            exposure,
            {
                "pass": "Lighting is even and bright enough.",
                "warn": "Lighting is borderline. Shade the leaf from harsh sun or move to brighter light.",
                "fail": "The photo is too dark or overexposed. Retake in even daylight.",
            }[exposure],
        ),
        Check(
            "focus",
            "Sharpness",
            focus,
            "",
            _status(focus, (90, float("inf")), (35, float("inf"))),
            "The leaf is in focus."
            if focus >= 90
            else "The leaf looks soft. Hold the phone steady and tap the leaf to focus."
            if focus >= 35
            else "The photo is blurry. Retake with the phone steady and the leaf in focus.",
        ),
        Check(
            "glare",
            "Glare",
            glare * 100,
            "%",
            _status(glare, (0, 0.02), (0, 0.08)),
            "No significant glare."
            if glare <= 0.02
            else "Some reflections on the leaf. Avoid direct sunlight on shiny leaves."
            if glare <= 0.08
            else "Strong glare hides the leaf surface. Shade the leaf and retake.",
        ),
        Check(
            "framing",
            "Leaf in frame",
            coverage * 100,
            "%",
            "fail" if not has_leaf else _status(coverage, (0.15, 0.9), (0.05, 1.0)),
            "No leaf was found. Photograph a single leaf against a contrasting background."
            if not has_leaf
            else "The leaf fills the frame well."
            if 0.15 <= coverage <= 0.9
            else "The leaf is small in the frame. Move closer."
            if coverage < 0.15
            else "The leaf fills the whole frame; its edges may be cut off.",
        ),
        Check(
            "resolution",
            "Resolution",
            short_side,
            "px",
            _status(short_side, (480, float("inf")), (240, float("inf"))),
            "Resolution is good."
            if short_side >= 480
            else "Low resolution. Use the phone's main camera at full size.",
        ),
    ]
    return checks


def _data_url(image: np.ndarray) -> str:
    ok, buffer = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 84])
    if not ok:
        raise ImageError("Could not create a preview image.")
    return "data:image/jpeg;base64," + base64.b64encode(buffer.tobytes()).decode()


def render_overlay(image: np.ndarray, leaf: np.ndarray, lesions: list[dict]) -> np.ndarray:
    overlay = image.copy()
    dim = cv2.addWeighted(image, 0.55, np.zeros_like(image), 0.45, 0)
    overlay[leaf == 0] = dim[leaf == 0]
    thickness = max(2, round(max(image.shape[:2]) / 400))
    contours, _ = cv2.findContours(leaf, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(overlay, contours, -1, LEAF_EDGE, thickness, cv2.LINE_AA)
    for lesion in lesions[:60]:
        pad = thickness + 2
        cv2.rectangle(
            overlay,
            (lesion["x"] - pad, lesion["y"] - pad),
            (lesion["x"] + lesion["width"] + pad, lesion["y"] + lesion["height"] + pad),
            LESION_EDGE,
            thickness,
            cv2.LINE_AA,
        )
    return overlay


def render_tissue(image: np.ndarray, tissue: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255
    out = (cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)[..., None].repeat(3, axis=2) * 0.35).astype(np.float32)
    shade = (0.55 + 0.45 * gray)[..., None]
    for label, colour in TISSUE_COLOURS.items():
        region = tissue == label
        out[region] = (np.array(colour, np.float32) * shade)[region]
    return np.clip(out, 0, 255).astype(np.uint8)


def _condition(index: float, has_leaf: bool, lesions: int) -> str:
    if not has_leaf:
        return "No leaf detected"
    if index < 0.05 and lesions < 3:
        return "Mostly green"
    if index < 0.2:
        return "Some discolouration"
    return "Extensive discolouration"


def analyze(raw: bytes) -> dict:
    started = time.perf_counter()
    original = decode(raw)
    image = resize_max(original, WORKING_SIDE)
    masks = colour_masks(image)
    leaf = segment_leaf(image, masks)
    leaf_area = int(np.count_nonzero(leaf))
    has_leaf = leaf_area > 0

    tissue = classify_tissue(leaf, masks)
    shares = {
        name: (float(np.count_nonzero(tissue == label)) / leaf_area if has_leaf else 0.0)
        for name, label in (("healthy", 1), ("yellowing", 2), ("browning", 3), ("other", 4))
    }
    lesions = find_lesions(tissue, leaf_area) if has_leaf else []
    discolouration = shares["yellowing"] + shares["browning"]

    checks = quality_checks(original, image, leaf, masks)
    points = {"pass": 100, "warn": 60, "fail": 15}
    score = round(sum(points[c.status] for c in checks) / len(checks))
    if any(c.status == "fail" for c in checks) or score < 60:
        grade = "poor"
    else:
        grade = "good" if score >= 88 else "fair"

    findings = [{"level": "warn", "text": c.message} for c in checks if c.status != "pass"]
    if has_leaf:
        findings.append(
            {
                "level": "warn" if discolouration >= 0.05 else "info",
                "text": (
                    f"{round(shares['yellowing'] * 100)}% of the leaf area looks yellow and "
                    f"{round(shares['browning'] * 100)}% looks brown or dark."
                ),
            }
        )
        if lesions:
            findings.append(
                {
                    "level": "warn",
                    "text": f"{len(lesions)} spot-like discoloured "
                    f"area{'s' if len(lesions) != 1 else ''} detected. "
                    "Check the underside of leaves and nearby plants for similar spots.",
                }
            )
        if grade == "poor":
            findings.append(
                {"level": "warn", "text": "Retake the photo before relying on these measurements."}
            )

    h, w = image.shape[:2]
    return {
        "id": uuid.uuid4().hex,
        "opencv_version": cv2.__version__,
        "processing_ms": round((time.perf_counter() - started) * 1000),
        "image": {
            "width": int(original.shape[1]),
            "height": int(original.shape[0]),
            "analyzed_width": int(w),
            "analyzed_height": int(h),
        },
        "quality": {"score": score, "grade": grade, "checks": [c.as_dict() for c in checks]},
        "leaf": {"detected": has_leaf, "coverage": round(leaf_area / (h * w), 4)},
        "tissue": {k: round(v, 4) for k, v in shares.items()},
        "discolouration_index": round(discolouration, 4),
        "condition": _condition(discolouration, has_leaf, len(lesions)),
        "lesions": {
            "count": len(lesions),
            "area_fraction": round(sum(item["area_fraction"] for item in lesions), 4),
            "largest_fraction": lesions[0]["area_fraction"] if lesions else 0.0,
            "boxes": lesions[:60],
        },
        "findings": findings,
        "images": {
            "overlay": _data_url(render_overlay(image, leaf, lesions)),
            "tissue": _data_url(render_tissue(image, tissue)),
        },
        "thresholds": {"exg": round(float(masks["exg_threshold"]), 3)},
        "disclaimer": DISCLAIMER,
    }
