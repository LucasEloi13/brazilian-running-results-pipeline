from pathlib import Path
import sys

# ensure project root
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.parses.event_modality_parser import parse_modality_targets


SAMPLE_HTML = """<html><body>
<a href="/evento/foo/?modalidade=3 KM&genero=F">link1</a>
<a href="/evento/foo/?modalidade=3 KM&genero=F">link2</a>
<a href="/evento/foo/?modalidade=3 KM&genero=M">link3</a>
<!-- card-level link without gender should be ignored -->
<a href="/evento/foo/?modalidade=3 KM">card</a>
</body></html>"""


def test_parse_modality_targets_unique_urls():
    targets = parse_modality_targets(SAMPLE_HTML, "https://openresults.run")
    # Should only return two targets (3 KM F and 3 KM M)
    assert len(targets) == 2
    raw_names = {t['raw_category_name'] for t in targets}
    genders = {t['gender'] for t in targets}
    assert raw_names == {'3 KM'}
    assert genders == {'F', 'M'}
    # both results should have a non-empty URL
    assert all(t['source_url'].startswith('https://openresults.run/evento/foo/') for t in targets)


def test_parse_modality_targets_distance_and_pcd():
    html = '<a href="/evento/foo/?modalidade=5 KM PCD&genero=M"></a>'
    targets = parse_modality_targets(html, "https://base/")
    assert len(targets) == 1
    t = targets[0]
    assert t['distance_km'] == 5.0
    assert t['is_pcd'] is True
    assert t['gender'] == 'M'


def test_parse_modality_targets_encodes_spaces():
    html = '<a href="/evento/foo/?modalidade=3 KM&genero=F"></a>'
    targets = parse_modality_targets(html, "https://base/")
    assert len(targets) == 1
    t = targets[0]
    # original link had space; parser must percent-encode it
    assert "%20" in t['source_url']
    assert "3%20KM" in t['source_url']
