import re
from dataclasses import asdict, dataclass
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from typing import Optional


@dataclass
class EventName:
    url: str
    slug: str
    name: Optional[str]
    year: Optional[int]
    day: Optional[int]
    month: Optional[int]
    month_abbr: Optional[str]
    date: Optional[str] 
    city: Optional[str]
    state: Optional[str]
    total_finishers: Optional[int]
    distances: Optional[list]


MONTH_MAP = {
    "jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
    "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12,
}


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def _format_date(year: Optional[int], month: Optional[int], day: Optional[int]) -> Optional[str]:
    if year is None or month is None or day is None:
        return None
    return f"{year:04d}-{month:02d}-{day:02d}"


def _parse_int(s: Optional[str]) -> Optional[int]:
    """Pull an integer from text or a regex match.

    The original callers sometimes passed the result of
    ``re.search``. Accept either a string or a ``re.Match`` so that
    callers don't need to unwrap groups manually.  Returns ``None`` if
    the input is falsy or no number can be extracted.
    """
    if not s:
        return None
    if isinstance(s, re.Match):
        # use first group if available
        try:
            s = s.group(1)
        except Exception:
            return None
    m = re.search(r"([\d.]+)", s)
    if not m:
        return None
    try:
        return int(m.group(1).replace(".", ""))
    except ValueError:
        return None


def _has_events(html: str) -> bool:
    return bool(re.search(r'href="/evento/', html))


# helpers used by ``_parse_page``

def _parse_slug(href: str) -> str:
    return href.strip("/").split("/")[-1]


def _parse_name(a) -> Optional[str]:
    h2 = a.select_one("h2.h5, h2.h6")
    return _norm(h2.get_text(" ")) if h2 else None


def _parse_year(a) -> Optional[int]:
    span = a.select_one(".card-header span")
    if not span:
        return None
    try:
        return int(_norm(span.get_text()))
    except ValueError:
        return None


def _parse_day_month(a) -> tuple[Optional[int], Optional[str], Optional[int]]:
    day = None
    month_abbr = None
    month = None

    span_day = a.select_one(".card-body span.fw-bold.fs-5")
    if span_day:
        try:
            day = int(_norm(span_day.get_text()))
        except ValueError:
            pass

    span_month = a.select_one(".card-body span.fw-bold.fs-6")
    if span_month:
        month_abbr = _norm(span_month.get_text()).lower()
        month = MONTH_MAP.get(month_abbr)

    return day, month_abbr, month


def _parse_location_and_finishers(a) -> tuple[Optional[str], Optional[str], Optional[int]]:
    city = None
    state = None
    total_finishers = None
    pinfo = a.select_one("p.h6.mb-1.small")
    if pinfo:
        txt = _norm(pinfo.get_text(" "))
        txt = txt.replace("&nbsp", " ")
        loc = re.search(r"(.+?)\s*-\s*([A-Z]{2})", txt)
        if loc:
            city = _norm(loc.group(1))
            state = loc.group(2)
        match = re.search(r"\|\s*([\d.]+)\s*concluintes", txt)
        if match:
            total_finishers = _parse_int(match.group(1))
    return city, state, total_finishers


def _parse_distances(a) -> Optional[list[dict]]:
    distances: list[dict] = []
    for d in a.select("div.kms"):
        dtxt = _norm(d.get_text(" "))
        km_match = re.search(r"\b(\d+)\s*k\b", dtxt.lower())
        if not km_match:
            continue
        dist_finishers = None
        match = re.search(r"\|\s*([\d.]+)\s*concluintes", dtxt)
        if match:
            dist_finishers = _parse_int(match.group(1))
        distances.append({"km": km_match.group(1), "finishers": dist_finishers})
    return distances or None



def _parse_page(html: str, base_url: str) -> list[EventName]:
    soup = BeautifulSoup(html, "html.parser")
    events: list[EventName] = []
    seen: set[str] = set()

    for a in soup.select('a[href^="/evento/"]'):
        href = a.get("href", "")
        full_url = urljoin(base_url, href)
        if full_url in seen:
            continue
        seen.add(full_url)

        slug = _parse_slug(href)
        name = _parse_name(a)
        year = _parse_year(a)
        day, month_abbr, month = _parse_day_month(a)
        city, state, total_finishers = _parse_location_and_finishers(a)
        distances = _parse_distances(a)

        events.append(EventName(
            url=full_url,
            slug=slug,
            name=name,
            year=year,
            day=day,
            month=month,
            month_abbr=month_abbr,
            date=_format_date(year, month, day),
            city=city,
            state=state,
            total_finishers=total_finishers,
            distances=distances,
        ))

    return events
