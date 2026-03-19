import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.parses.event_modality_parser import _parse_distance_km


@pytest.mark.parametrize(
    ("raw_category_name", "expected"),
    [
        ("5K", 5.0),
        ("10k", 10.0),
        ("21 KM", 21.0),
        ("KIDS 600M", 0.6),
        ("DUPLA 100+", 0.1),
        ("TRAIL 42,2KM", 42.2),
        ("VETERANA 60", None),
        ("GERAL IDOSO 60", None),
        ("SEM DISTANCIA", None),
    ],
)
def test_parse_distance_km(raw_category_name: str, expected: float | None) -> None:
    parsed = _parse_distance_km(raw_category_name)

    if expected is None:
        assert parsed is None
        return

    assert parsed is not None
    assert parsed == pytest.approx(expected)
