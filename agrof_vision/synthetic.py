"""Synthetic leaf photos for tests and demo samples.

These are procedurally generated so the test suite has known ground truth
(where the leaf is, how much is yellow, how many spots). They are not a
substitute for evaluation on real, labelled field photos.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

SOIL_BGR = (42, 72, 108)
LEAF_BGR = (48, 142, 62)
VEIN_BGR = (110, 196, 150)
YELLOW_BGR = (52, 196, 222)
LESION_BGR = (28, 58, 104)
HALO_BGR = (64, 176, 206)


@dataclass(frozen=True)
class LeafSpec:
    width: int = 1200
    height: int = 900
    spots: int = 0
    yellowing: float = 0.0  # 0..1 share of the leaf turned yellow, from the tip
    blur: int = 0  # Gaussian kernel size; 0 = sharp
    brightness: float = 1.0
    background: str = "soil"  # "soil" or "paper"
    seed: int = 7


@dataclass(frozen=True)
class LeafPhoto:
    image: np.ndarray
    leaf_mask: np.ndarray
    lesion_count: int


def _noise(rng: np.random.Generator, shape: tuple[int, int], scale: int) -> np.ndarray:
    small = rng.normal(0, 1, (max(2, shape[0] // scale), max(2, shape[1] // scale))).astype(np.float32)
    return cv2.resize(small, (shape[1], shape[0]), interpolation=cv2.INTER_CUBIC)


def _leaf_outline(spec: LeafSpec) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Returns the outline polygon, the base point and the tip point."""
    cx, cy = spec.width / 2, spec.height / 2
    length = min(spec.width * 0.72, spec.height * 1.15)
    half_width = length * 0.24
    angle = np.deg2rad(-18)
    axis = np.array([np.cos(angle), np.sin(angle)])
    normal = np.array([-axis[1], axis[0]])
    base = np.array([cx, cy]) - axis * length / 2
    t = np.linspace(0, 1, 120)
    widths = half_width * np.sin(np.pi * t) ** 0.85 * (1 - 0.35 * t)
    centre = base + np.outer(t * length, axis)
    left = centre + np.outer(widths, normal)
    right = centre - np.outer(widths, normal)
    outline = np.vstack([left, right[::-1]]).astype(np.int32)
    return outline, base, base + axis * length


def leaf_photo(spec: LeafSpec | None = None) -> LeafPhoto:
    spec = spec or LeafSpec()
    rng = np.random.default_rng(spec.seed)
    h, w = spec.height, spec.width

    if spec.background == "soil":
        image = np.empty((h, w, 3), np.float32)
        image[:] = SOIL_BGR
        image += _noise(rng, (h, w), 6)[..., None] * 14 + _noise(rng, (h, w), 40)[..., None] * 10
        for _ in range(60):  # pebbles
            centre = (int(rng.integers(0, w)), int(rng.integers(0, h)))
            shade = float(rng.uniform(70, 150))
            cv2.circle(image, centre, int(rng.integers(3, 9)), (shade * 0.9, shade * 0.95, shade), -1)
    else:
        image = np.full((h, w, 3), 226, np.float32)
        image += _noise(rng, (h, w), 30)[..., None] * 4

    outline, base, tip = _leaf_outline(spec)
    mask = np.zeros((h, w), np.uint8)
    cv2.fillPoly(mask, [outline], 255)

    leaf = np.empty((h, w, 3), np.float32)
    leaf[:] = LEAF_BGR
    leaf *= (1 + _noise(rng, (h, w), 10) * 0.06)[..., None]

    # Yellowing spreads from the tip back along the leaf.
    if spec.yellowing > 0:
        ys, xs = np.mgrid[0:h, 0:w]
        axis = (tip - base) / np.linalg.norm(tip - base)
        progress = ((xs - base[0]) * axis[0] + (ys - base[1]) * axis[1]) / np.linalg.norm(tip - base)
        cutoff = np.quantile(progress[mask > 0], 1 - spec.yellowing)
        blend = np.clip((progress - cutoff) / 0.04 + 0.5, 0, 1)[..., None]
        leaf = leaf * (1 - blend) + np.array(YELLOW_BGR, np.float32) * blend

    cv2.line(leaf, tuple(base.astype(int)), tuple(tip.astype(int)), VEIN_BGR, 5)
    axis = tip - base
    normal = np.array([-axis[1], axis[0]]) / np.linalg.norm(axis)
    for t in np.linspace(0.12, 0.85, 8):
        start = base + axis * t
        for side in (1, -1):
            end = start + axis * 0.12 + normal * side * np.linalg.norm(axis) * 0.2 * (1 - t * 0.5)
            cv2.line(leaf, tuple(start.astype(int)), tuple(end.astype(int)), VEIN_BGR, 2)

    lesion_count = 0
    if spec.spots:
        inner = cv2.erode(mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (61, 61)))
        ys, xs = np.nonzero(inner)
        placed: list[tuple[int, int, int]] = []
        attempts = 0
        while lesion_count < spec.spots and attempts < 2000:
            attempts += 1
            i = int(rng.integers(0, len(xs)))
            x, y, r = int(xs[i]), int(ys[i]), int(rng.integers(9, 18))
            if any((x - px) ** 2 + (y - py) ** 2 < (r + pr + 30) ** 2 for px, py, pr in placed):
                continue
            cv2.circle(leaf, (x, y), r + 6, HALO_BGR, -1)
            cv2.circle(leaf, (x, y), r, LESION_BGR, -1)
            placed.append((x, y, r))
            lesion_count += 1

    # Soft shadow under the leaf, then composite.
    shadow = cv2.GaussianBlur(mask, (0, 0), 14).astype(np.float32) / 255
    shadow = np.roll(shadow, (14, 10), axis=(0, 1))
    image *= (1 - 0.35 * shadow)[..., None]
    alpha = cv2.GaussianBlur(mask, (5, 5), 0).astype(np.float32)[..., None] / 255
    image = image * (1 - alpha) + leaf * alpha

    # Gentle light falloff and sensor noise.
    ys, xs = np.mgrid[0:h, 0:w]
    vignette = 1 - 0.18 * (((xs - w / 2) / w) ** 2 + ((ys - h / 2) / h) ** 2) * 2
    image = image * vignette[..., None] * spec.brightness
    image += rng.normal(0, 2.5, image.shape)
    image = np.clip(image, 0, 255).astype(np.uint8)
    if spec.blur:
        k = spec.blur | 1
        image = cv2.GaussianBlur(image, (k, k), 0)
    return LeafPhoto(image=image, leaf_mask=mask, lesion_count=lesion_count)


def encode(image: np.ndarray, ext: str = ".jpg", quality: int = 92) -> bytes:
    params = [cv2.IMWRITE_JPEG_QUALITY, quality] if ext == ".jpg" else []
    ok, buffer = cv2.imencode(ext, image, params)
    if not ok:
        raise ValueError("Could not encode image")
    return buffer.tobytes()
