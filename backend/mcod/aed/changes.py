"""Wykrywanie zmian między kolejnymi scaleniami: nowe, usunięte i zmienione rekordy.

Porównujemy poprzedni plik zbiorczy z nowym po kluczu (dysponent, identyfikator). Dostawca widzi w raporcie, że jego
poprawka doszła, a my widzimy, co zniknęło z wykazu zbiorczym (usunięte przez dysponenta, odrzucone albo połączone).
"""

from typing import Any, Dict, List, Optional

import pandas as pd

from mcod.aed.constants import (
    COL_ACCESS,
    COL_AVAILABILITY,
    COL_ID,
    COL_LAT,
    COL_LON,
    COL_PROVIDER,
    COL_SOURCE_RESOURCE,
    COL_STATUS,
    COL_VERIFIED,
    REPORT_CHANGED,
    REPORT_COLUMNS,
    REPORT_NEW,
    REPORT_REMOVED,
)

# Pola, których zmiana jest dla dysponenta i użytkownika istotna. „Aktualność” celowo pominięta: zmienia się z upływem czasu.
TRACKED_COLUMNS = [COL_STATUS, COL_AVAILABILITY, COL_ACCESS, COL_VERIFIED, COL_LAT, COL_LON]
MAX_ROWS_PER_KIND = 500
_COORD_TOLERANCE = 1e-6


def _key(provider: Any, ident: Any) -> str:
    return f"{provider}||{ident}"


def _text(value: Any) -> str:
    if value is None or (not isinstance(value, (list, dict)) and pd.isna(value)):
        return ""
    return value.isoformat() if hasattr(value, "isoformat") else str(value).strip()


def _differs(column: str, before: Any, after: Any) -> bool:
    if column in (COL_LAT, COL_LON):
        try:
            return abs(float(before) - float(after)) > _COORD_TOLERANCE
        except (TypeError, ValueError):
            return _text(before) != _text(after)
    return _text(before) != _text(after)


def _row(provider: Any, resource: Any, ident: Any, result: str, reason: str) -> Dict[str, Any]:
    resource_id = None if _text(resource) == "" else int(float(resource))
    return dict(zip(REPORT_COLUMNS, [provider, resource_id, None, ident, result, reason]))


def diff_main(previous: Optional[pd.DataFrame], current: pd.DataFrame) -> List[Dict[str, Any]]:
    """Wiersze raportu opisujące różnice między poprzednim a nowym wykazem zbiorczym.

    Przy pierwszym scaleniu (brak poprzedniego) nie ma czego porównywać i zwracamy pustą listę.
    """
    if previous is None or previous.empty and previous.columns.empty:
        return []
    prev = {
        _key(r[COL_PROVIDER], r[COL_ID]): r for _, r in previous.iterrows() if COL_PROVIDER in previous and COL_ID in previous
    }
    cur = {_key(r[COL_PROVIDER], r[COL_ID]): r for _, r in current.iterrows()}
    rows: List[Dict[str, Any]] = []

    new_keys = [k for k in cur if k not in prev]
    for k in new_keys[:MAX_ROWS_PER_KIND]:
        r = cur[k]
        rows.append(
            _row(r[COL_PROVIDER], r.get(COL_SOURCE_RESOURCE), r[COL_ID], REPORT_NEW, "rekord pojawił się w wykazie zbiorczym")
        )

    removed_keys = [k for k in prev if k not in cur]
    for k in removed_keys[:MAX_ROWS_PER_KIND]:
        r = prev[k]
        reason = (
            "rekordu nie ma już w wykazie zbiorczym: usunięty przez dysponenta, "
            "odrzucony przy walidacji albo połączony z innym rekordem"
        )
        rows.append(_row(r[COL_PROVIDER], r.get(COL_SOURCE_RESOURCE), r[COL_ID], REPORT_REMOVED, reason))

    changed = 0
    for k in cur:
        if k not in prev:
            continue
        diffs = [
            f"{c}: {_text(prev[k].get(c))} → {_text(cur[k].get(c))}"
            for c in TRACKED_COLUMNS
            if c in prev[k] and _differs(c, prev[k].get(c), cur[k].get(c))
        ]
        if diffs and changed < MAX_ROWS_PER_KIND:
            r = cur[k]
            rows.append(_row(r[COL_PROVIDER], r.get(COL_SOURCE_RESOURCE), r[COL_ID], REPORT_CHANGED, "; ".join(diffs)))
            changed += 1
    return rows
