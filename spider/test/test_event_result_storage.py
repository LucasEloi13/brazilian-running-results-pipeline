import pytest

from pathlib import Path
from typing import Any

# ensure project root on path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
import sys
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.storage.event_result_storage import EventResultStorage, execute_values


class DummyCursor:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def fetchall(self):
        # value may be injected by the fake execute_values
        return []


class DummyDB:
    def __init__(self, cursor_obj: DummyCursor):
        self._cursor = cursor_obj

    def cursor(self):
        return self._cursor


def test_bulk_upsert_tasks_dedup(monkeypatch):
    captured: dict[str, Any] = {}

    def fake_execute_values(cur, query, rows, page_size=None):
        # record rows passed for inspection
        captured['rows'] = list(rows)

    monkeypatch.setattr('src.storage.event_result_storage.execute_values', fake_execute_values)

    storage = EventResultStorage(db=DummyDB(DummyCursor()), config={})
    modality_map = {'A': 1, 'B': 2}
    targets = [
        {'raw_category_name': 'A', 'gender': 'M', 'source_url': 'u1'},
        {'raw_category_name': 'A', 'gender': 'M', 'source_url': 'u2'},  # duplicate
        {'raw_category_name': 'A', 'gender': 'F', 'source_url': 'u3'},
        {'raw_category_name': 'B', 'gender': 'M', 'source_url': 'u4'},
    ]

    count = storage._bulk_upsert_tasks(10, modality_map, targets)
    assert count == 3
    # ensure the duplicate (A,M) was collapsed and last URL wins
    assert set(captured['rows']) == {
        (10, 1, 'M', 'u2'),
        (10, 1, 'F', 'u3'),
        (10, 2, 'M', 'u4'),
    }


def test_bulk_upsert_modalities_dedup(monkeypatch):
    captured: dict[str, Any] = {}

    def fake_execute_values(cur, query, rows, page_size=None):
        captured['rows'] = list(rows)
        # simulate returning ids for two inserted/updated rows
        def fetchall():
            return [(123, 'A')]

        cur.fetchall = fetchall

    monkeypatch.setattr('src.storage.event_result_storage.execute_values', fake_execute_values)

    storage = EventResultStorage(db=DummyDB(DummyCursor()), config={})
    # two targets with same raw_category_name should collapse into one
    targets = [
        {'raw_category_name': 'A', 'distance_km': 5, 'is_pcd': False},
        {'raw_category_name': 'A', 'distance_km': 10, 'is_pcd': True},
    ]

    result = storage._bulk_upsert_modalities(7, targets)
    assert result == {'A': 123}
    assert captured['rows'] == [(7, 10.0, True, 'A')]
