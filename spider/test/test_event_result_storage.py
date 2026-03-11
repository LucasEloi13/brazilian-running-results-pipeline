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
    def __init__(self):
        self.executed: list[tuple[str, Any]] = []
        self.description = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, query, params=None):
        self.executed.append((query, params))

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


def test_fetch_actionable_tasks_claims_in_progress():
    cursor = DummyCursor()
    cursor.description = [
        ("task_id",),
        ("job_id",),
        ("modality_id",),
        ("gender",),
        ("source_url",),
        ("attempts",),
        ("event_id",),
        ("slug",),
        ("distance_km",),
        ("is_pcd",),
        ("raw_category_name",),
        ("city_name",),
        ("state_abbr",),
    ]

    def fetchall():
        return [(1, 10, 20, 'M', 'https://example.com', 2, 30, 'event-x', 5.0, False, '5km', 'Cuiaba', 'MT')]

    cursor.fetchall = fetchall
    storage = EventResultStorage(db=DummyDB(cursor), config={})

    tasks = storage.fetch_actionable_tasks([10])

    assert tasks == [{
        'task_id': 1,
        'job_id': 10,
        'modality_id': 20,
        'gender': 'M',
        'source_url': 'https://example.com',
        'attempts': 2,
        'event_id': 30,
        'slug': 'event-x',
        'distance_km': 5.0,
        'is_pcd': False,
        'raw_category_name': '5km',
        'city_name': 'Cuiaba',
        'state_abbr': 'MT',
    }]
    assert "status = 'in_progress'" in cursor.executed[0][0]
