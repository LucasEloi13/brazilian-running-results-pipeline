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


def _parse_int(s: str) -> Optional[int]:
    if not s:
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

        slug = href.strip("/").split("/")[-1]

        # Name - can be h2.h5 or h2.h6
        h2 = a.select_one("h2.h5, h2.h6")
        name = _norm(h2.get_text(" ")) if h2 else None

        # Year
        year_span = a.select_one(".card-header span")
        year: Optional[int] = None
        if year_span:
            try:
                year = int(_norm(year_span.get_text()))
            except ValueError:
                pass

        # Day / month - updated selectors
        day: Optional[int] = None
        month_abbr: Optional[str] = None
        month: Optional[int] = None
        
        # Day is in span with classes fw-bold fs-5
        day_span = a.select_one(".card-body span.fw-bold.fs-5")
        if day_span:
            try:
                day = int(_norm(day_span.get_text()))
            except ValueError:
                pass
        
        # Month is in span with classes fw-bold fs-6
        month_span = a.select_one(".card-body span.fw-bold.fs-6")
        if month_span:
            month_abbr = _norm(month_span.get_text()).lower()
            month = MONTH_MAP.get(month_abbr)

        # City / state / finishers
        city: Optional[str] = None
        state: Optional[str] = None
        total_finishers: Optional[int] = None
        pinfo = a.select_one("p.h6.mb-1.small")
        if pinfo:
            txt = _norm(pinfo.get_text(" "))
            # Replace malformed &nbsp (without semicolon) with space
            txt = txt.replace("&nbsp", " ")
            # Match city and state (format: "Cidade - UF")
            loc = re.search(r"(.+?)\s*-\s*([A-Z]{2})", txt)
            if loc:
                city = _norm(loc.group(1))
                state = loc.group(2)
            # Match total finishers after pipe
            finishers_match = re.search(r"\|\s*([\d.]+)\s*concluintes", txt)
            if finishers_match:
                total_finishers = _parse_int(finishers_match.group(1))

        # Distances
        distances: list[dict] = []
        for d in a.select("div.kms"):
            dtxt = _norm(d.get_text(" "))
            km_m = re.search(r"\b(\d+)\s*k\b", dtxt.lower())
            if not km_m:
                continue
            # Extract finishers for this distance
            dist_finishers = None
            finishers_match = re.search(r"\|\s*([\d.]+)\s*concluintes", dtxt)
            if finishers_match:
                dist_finishers = _parse_int(finishers_match.group(1))
            
            distances.append({
                "km": km_m.group(1),
                "finishers": dist_finishers,
            })

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
            distances=distances or None,
        ))

    return events