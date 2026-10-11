"""Writes the synthetic demo photos used by the web app's "Try a sample" buttons."""

from pathlib import Path

from agrof_vision.synthetic import LeafSpec, encode, leaf_photo

OUT = Path(__file__).resolve().parent.parent / "web" / "public" / "samples"
SAMPLES = {
    "healthy": LeafSpec(seed=21),
    "spotted": LeafSpec(spots=9, seed=5),
    "yellowing": LeafSpec(yellowing=0.32, spots=3, seed=8, background="paper"),
}

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for name, spec in SAMPLES.items():
        (OUT / f"{name}.jpg").write_bytes(encode(leaf_photo(spec).image, quality=86))
        print("wrote", OUT / f"{name}.jpg")
