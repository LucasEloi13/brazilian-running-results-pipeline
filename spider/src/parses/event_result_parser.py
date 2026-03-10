import re
import unicodedata
from typing import Any

from bs4 import BeautifulSoup


def _norm(text: str | None) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _norm_key(label: str | None) -> str:
    value = unicodedata.normalize("NFKD", _norm(label)).encode("ascii", "ignore").decode("ascii")
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_")


def _extract_headers(soup: BeautifulSoup) -> list[str]:
    headers = [_norm(th.get_text(" ")) for th in soup.select("#tableResultados thead th")]
    return headers


def _map_row_values(headers: list[str], values: list[str]) -> dict[str, str]:
    row: dict[str, str] = {}

    for idx, value in enumerate(values):
        if idx >= len(headers):
            break

        raw_key = headers[idx]
        normalized_key = _norm_key(raw_key)
        if not normalized_key:
            normalized_key = f"col_{idx + 1}"

        row[normalized_key] = value

    return row


def parse_result_rows(html: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    headers = _extract_headers(soup)

    rows: list[dict[str, Any]] = []
    for tr in soup.select("#tableResultados tbody tr"):
        cells = tr.select("td")
        if not cells:
            continue

        values = [_norm(td.get_text(" ")) for td in cells]
        if not any(values):
            continue

        row = _map_row_values(headers, values)
        row["raw_row_id"] = (tr.get("id") or "").strip()

        # Stable aliases expected by downstream processing.
        if "geral" in row:
            row["overall"] = row["geral"]
        if "cat" in row:
            row["category"] = row["cat"]
        if "numero" in row:
            row["bib"] = row["numero"]
        if "nome" in row:
            row["athlete_name"] = row["nome"]
        if "equipe" in row:
            row["team"] = row["equipe"]
        if "tempo" in row:
            row["finish_time"] = row["tempo"]

        rows.append(row)

    return rows
