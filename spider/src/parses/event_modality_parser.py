import re
import unicodedata
from typing import Any
from urllib.parse import parse_qs, urljoin, urlparse

from bs4 import BeautifulSoup


def _norm(text: str | None) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _ascii(text: str | None) -> str:
    return unicodedata.normalize("NFKD", _norm(text)).encode("ascii", "ignore").decode("ascii")


def _parse_distance_km(raw_category_name: str) -> float | None:
    match = re.search(r"(\d+(?:[\.,]\d+)?)", _ascii(raw_category_name))
    if not match:
        return None

    numeric = match.group(1).replace(",", ".")
    try:
        return float(numeric)
    except ValueError:
        return None


def parse_modality_targets(html: str, base_url: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")

    unique: dict[tuple[str, str], dict[str, Any]] = {}

    from urllib.parse import quote

    for anchor in soup.select('a[href*="/evento/"][href*="modalidade="][href*="genero="]'):
        href = (anchor.get("href") or "").strip()
        if not href:
            continue

        full_url = urljoin(base_url, href)
        full_url = quote(full_url, safe=":/?&=%")

        parsed = urlparse(full_url)
        query = parse_qs(parsed.query)
        raw_category_name = _norm((query.get("modalidade") or [""])[0])
        gender = _norm((query.get("genero") or [""])[0]).upper()
        distance_km = _parse_distance_km(raw_category_name)
        is_pcd = bool(re.search(r"\bpcd\b", _ascii(raw_category_name).lower()))

        if not raw_category_name or gender not in {"F", "M"} or distance_km is None:
            continue

        key = (raw_category_name, gender)
        if key not in unique:
            unique[key] = {
                "source_url": full_url,
                "raw_category_name": raw_category_name,
                "distance_km": distance_km,
                "is_pcd": is_pcd,
                "gender": gender,
            }

    return list(unique.values())
