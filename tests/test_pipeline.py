import cv2
import numpy as np
import pytest

from agrof_vision.pipeline import ImageError, analyze, colour_masks, resize_max, segment_leaf
from agrof_vision.synthetic import LeafSpec, encode, leaf_photo


def iou(spec: LeafSpec) -> float:
    photo = leaf_photo(spec)
    image = resize_max(photo.image, 1024)
    found = segment_leaf(image, colour_masks(image)) > 0
    truth = cv2.resize(photo.leaf_mask, found.shape[::-1], interpolation=cv2.INTER_NEAREST) > 0
    return (found & truth).sum() / (found | truth).sum()


@pytest.mark.parametrize("background", ["soil", "paper"])
def test_segments_the_leaf_and_not_the_soil(background):
    assert iou(LeafSpec(background=background)) > 0.95


def test_healthy_leaf(healthy_jpeg):
    result = analyze(healthy_jpeg)
    assert result["opencv_version"].startswith("5.")
    assert result["leaf"]["detected"]
    assert result["tissue"]["healthy"] > 0.97
    assert result["lesions"]["count"] == 0
    assert result["condition"] == "Mostly green"
    assert result["quality"]["grade"] == "good"
    assert result["images"]["overlay"].startswith("data:image/jpeg;base64,")
    assert result["images"]["tissue"].startswith("data:image/jpeg;base64,")


def test_counts_spots(spotted):
    result = analyze(encode(spotted.image))
    assert result["lesions"]["count"] == spotted.lesion_count
    assert result["tissue"]["browning"] > 0.01
    assert result["condition"] == "Some discolouration"


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_spot_count_is_exact_across_layouts(seed):
    photo = leaf_photo(LeafSpec(spots=10, seed=seed))
    assert analyze(encode(photo.image))["lesions"]["count"] == 10


def test_measures_yellowing_without_calling_it_spots():
    result = analyze(encode(leaf_photo(LeafSpec(yellowing=0.3)).image))
    assert 0.2 < result["tissue"]["yellowing"] < 0.4
    assert result["lesions"]["count"] == 0
    assert result["condition"] == "Extensive discolouration"


def test_flags_blur_and_darkness():
    blurry = analyze(encode(leaf_photo(LeafSpec(blur=21)).image))
    checks = {c["id"]: c["status"] for c in blurry["quality"]["checks"]}
    assert checks["focus"] == "fail" and blurry["quality"]["grade"] == "poor"
    dark = analyze(encode(leaf_photo(LeafSpec(brightness=0.25)).image))
    assert {c["id"]: c["status"] for c in dark["quality"]["checks"]}["exposure"] == "fail"


def test_no_leaf_in_a_photo_of_sky():
    sky = np.full((600, 800, 3), (230, 180, 120), np.uint8)
    result = analyze(encode(sky))
    assert not result["leaf"]["detected"]
    assert result["condition"] == "No leaf detected"


def test_png_and_webp_are_accepted(healthy_jpeg):
    image = leaf_photo(LeafSpec(width=640, height=480)).image
    assert analyze(encode(image, ".png"))["leaf"]["detected"]
    assert analyze(encode(image, ".webp"))["leaf"]["detected"]


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        (b"", "empty"),
        (b"GIF89a....", "JPEG, PNG or WebP"),
        (b"\xff\xd8\xff" + b"0" * 100, "could not be read"),
    ],
)
def test_rejects_bad_files(raw, message):
    with pytest.raises(ImageError, match=message):
        analyze(raw)


def test_rejects_tiny_images():
    with pytest.raises(ImageError, match="too small"):
        analyze(encode(np.zeros((60, 60, 3), np.uint8)))
