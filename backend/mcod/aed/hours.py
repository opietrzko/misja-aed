"""Parser godzin dostępności: wolny tekst -> jednolity zapis (podzbiór składni OpenStreetMap opening_hours).

Rozumie polskie i angielskie zapisy: „pn-pt 7:30-16:00”, „Mo-Fr 08:00-18:00”, „godz: 8.00-18.00 w dni robocze”,
„od 8 do 16 codziennie”, „pn-pt 7-17, sob 9-13”, „całodobowo”. Czego nie jest pewny, nie zgaduje: zwraca None.
Wynik: „24/7” albo segmenty w rodzaju „Mo-Fr 07:30-16:00; Sa 09:00-13:00”.
"""

import re
import unicodedata
from typing import Dict, List, Optional, Set, Tuple

from mcod.aed.text import norm

HOURS_24_7 = "24/7"
DAYS = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]

_OSM_TO_PL = {"Mo": "pn", "Tu": "wt", "We": "sr", "Th": "czw", "Fr": "pt", "Sa": "sob", "Su": "nd"}
_DAY_CODE = {
    "poniedzialek": "Mo",
    "pon": "Mo",
    "pn": "Mo",
    "wtorek": "Tu",
    "wt": "Tu",
    "sroda": "We",
    "sr": "We",
    "czwartek": "Th",
    "czw": "Th",
    "piatek": "Fr",
    "pt": "Fr",
    "sobota": "Sa",
    "sob": "Sa",
    "sb": "Sa",
    "niedziela": "Su",
    "niedz": "Su",
    "ndz": "Su",
    "nd": "Su",
}
_DAY = r"(?:poniedzialek|wtorek|sroda|czwartek|piatek|sobota|niedziela|niedz|ndz|pon|czw|sob|wt|sr|pn|pt|sb|nd)"
_TIME = r"(\d{1,2})(?:[:.](\d{2}))?\s*-\s*(\d{1,2})(?:[:.](\d{2}))?"
_ALL_DAYS = r"(?:codziennie|we wszystkie dni|wszystkie dni|w kazdy dzien|kazdego dnia)"
_WORK_DAYS = r"(?:w dni robocze|dni robocze|dniach roboczych|robocze|roboczych)"
_WEEKEND = r"(?:w weekendy|weekendy|weekend)"
_MASTER = re.compile(
    rf"(?P<all>{_ALL_DAYS})|(?P<work>{_WORK_DAYS})|(?P<wkd>{_WEEKEND})"
    rf"|\b(?P<d1>{_DAY})\b\.?\s*-\s*\b(?P<d2>{_DAY})\b\.?|\b(?P<d>{_DAY})\b\.?|(?P<t>{_TIME})"
)
_ROUND_THE_CLOCK = re.compile(r"calodob|cala dob|24 ?/ ?7|24 ?h\b|non ?stop|zawsze|przez cala dobe")

Range = Tuple[int, int]  # minuty od północy


def _expand(first: str, last: str) -> Set[str]:
    """Zakres dni, także przechodzący przez niedzielę (np. sob-pn)."""
    i, j = DAYS.index(_DAY_CODE[first]), DAYS.index(_DAY_CODE[last])
    order = range(i, j + 1) if i <= j else list(range(i, 7)) + list(range(0, j + 1))
    return {DAYS[k] for k in order}


def _to_minutes(h: str, m: Optional[str]) -> Optional[int]:
    hour, minute = int(h), int(m) if m else 0
    if hour > 24 or minute > 59 or (hour == 24 and minute):
        return None
    return hour * 60 + minute


def _make_range(match: "re.Match") -> Optional[Range]:
    start = _to_minutes(match.group(1), match.group(2))
    end = _to_minutes(match.group(3), match.group(4))
    if start is None or end is None or start == end or start >= 24 * 60:
        return None
    return start, end


def _prepare(text: str) -> str:
    """Zapis OSM (Mo, Tu...) zamieniamy na polski przed zdjęciem wielkości liter, potem „od X do Y” -> „X-Y”."""
    text = re.sub(r"\b(Mo|Tu|We|Th|Fr|Sa|Su)\b", lambda m: _OSM_TO_PL[m.group(1)], text)
    text = unicodedata.normalize("NFKD", text.lower().replace("ł", "l"))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[\u2013\u2014\u2212]", "-", text)  # półpauza, pauza i znak minus jako zwykły łącznik
    return re.sub(r"\bod\s+(\d{1,2}(?:[:.]\d{2})?)\s+do\s+(\d{1,2}(?:[:.]\d{2})?)", r"\1-\2", text)


def _days_from_match(match: "re.Match") -> Optional[Set[str]]:
    if match.group("all"):
        return set(DAYS)
    if match.group("work"):
        return set(DAYS[:5])
    if match.group("wkd"):
        return {"Sa", "Su"}
    if match.group("d1"):
        return _expand(match.group("d1"), match.group("d2"))
    if match.group("d"):
        return {_DAY_CODE[match.group("d")]}
    return None


class _Assigner:
    """Stan skanowania tekstu: do jakich dni przypisujemy kolejne przedziały godzin."""

    def __init__(self, times_first: bool):
        self.times_first = times_first  # styl „8-16 pn-pt, 9-13 sob”: godziny przed dniami
        self.per_day: Dict[str, List[Range]] = {d: [] for d in DAYS}
        self.current: Optional[Set[str]] = None
        self.pending: List[Range] = []  # godziny podane przed dniami („8-18 w dni robocze”)
        self.leading: List[Range] = []  # takie godziny już przypisane pierwszemu dniowi z listy („8-12 pn, śr, pt”)
        self.after_days = False  # poprzedni token to dni: kolejne dni bez godzin pomiędzy nimi się sumują

    def _assign(self, days: Set[str], ranges: List[Range]) -> None:
        for day in days:
            self.per_day[day].extend(ranges)

    def add_days(self, days: Set[str]) -> None:
        self.current = (self.current | days) if (self.after_days and self.current) else days
        if not self.after_days:
            self.leading = self.pending
        self._assign(days, self.leading if self.after_days else self.pending)
        self.after_days = True
        self.pending = []

    def add_range(self, rng: Range) -> None:
        self.after_days = False
        self.leading = []
        if self.current is None or self.times_first:
            self.pending.append(rng)
        else:
            self._assign(self.current, [rng])


def _scan(text: str) -> Optional[Dict[str, List[Range]]]:
    """Przypisuje przedziały godzin do dni. None, gdy tekst jest niejednoznaczny lub niepoprawny."""
    matches = list(_MASTER.finditer(text))
    assigner = _Assigner(times_first=bool(matches) and matches[0].group("t") is not None)
    for match in matches:
        days = _days_from_match(match)
        if days is not None:
            assigner.add_days(days)
            continue
        rng = _make_range(re.match(_TIME, match.group("t")))
        if rng is None:
            return None
        assigner.add_range(rng)
    return None if assigner.pending else assigner.per_day  # godziny bez dni: nie zakładamy, że obowiązują codziennie


def _overlaps(ranges: List[Range]) -> bool:
    ordered = sorted(ranges)
    return any(ordered[i][1] > ordered[i + 1][0] for i in range(len(ordered) - 1))


def _fmt(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _run_label(run: List[int]) -> str:
    if len(run) == 1:
        return DAYS[run[0]]
    if len(run) == 2:
        return f"{DAYS[run[0]]},{DAYS[run[1]]}"
    return f"{DAYS[run[0]]}-{DAYS[run[-1]]}"


def _compress_days(days: List[str]) -> str:
    idx = sorted(DAYS.index(d) for d in days)
    runs, start = [], 0
    for k in range(1, len(idx) + 1):
        if k == len(idx) or idx[k] != idx[k - 1] + 1:
            runs.append(idx[start:k])
            start = k
    return ",".join(_run_label(r) for r in runs)


def _format(per_day: Dict[str, List[Range]]) -> Optional[str]:
    groups: Dict[Tuple[Range, ...], List[str]] = {}
    for day in DAYS:
        ranges = per_day[day]
        if not ranges:
            continue
        if _overlaps(ranges):
            return None
        groups.setdefault(tuple(sorted(set(ranges))), []).append(day)
    if not groups:
        return None
    if len(groups) == 1:
        ranges, days = next(iter(groups.items()))
        if len(days) == 7 and ranges == ((0, 24 * 60),):
            return HOURS_24_7
    segments = sorted(groups.items(), key=lambda kv: DAYS.index(kv[1][0]))
    return "; ".join(
        f"{_compress_days(days)} " + ",".join(f"{_fmt(s)}-{_fmt(e)}" for s, e in ranges) for ranges, days in segments
    )


def normalize_hours(text: Optional[str], availability: Optional[str] = None) -> Optional[str]:
    """Jednolity zapis godzin albo None (nie rozpoznano lub niejednoznaczne). „całodobowo” -> „24/7”."""
    blank = text is None or (isinstance(text, float) and text != text) or str(text).strip() == ""
    if blank:
        return HOURS_24_7 if availability == "całodobowo" else None
    prepared = _prepare(str(text))
    if _ROUND_THE_CLOCK.search(norm(prepared)) or _ROUND_THE_CLOCK.search(prepared):
        return HOURS_24_7
    per_day = _scan(prepared)
    return _format(per_day) if per_day is not None else None
