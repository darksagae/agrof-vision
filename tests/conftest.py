import pytest

from agrof_vision.synthetic import LeafSpec, encode, leaf_photo


@pytest.fixture(scope="session")
def healthy_jpeg() -> bytes:
    return encode(leaf_photo(LeafSpec()).image)


@pytest.fixture(scope="session")
def spotted():
    return leaf_photo(LeafSpec(spots=8, seed=11))
