import pandas as pd

from mcod.aed.changes import MAX_ROWS_PER_KIND, diff_main
from mcod.aed.constants import (
    COL_ID,
    COL_LAT,
    COL_LON,
    COL_PROVIDER,
    COL_SOURCE_RESOURCE,
    COL_STATUS,
    COL_VERIFIED,
)


def frame(*rows):
    cols = [COL_PROVIDER, COL_ID, COL_SOURCE_RESOURCE, COL_STATUS, COL_VERIFIED, COL_LAT, COL_LON]
    return pd.DataFrame(list(rows), columns=cols)


def test_first_run_has_nothing_to_compare():
    assert diff_main(None, frame(("P", "A", 1, "czynny", "2026-11-01", 50.0, 19.0))) == []


def test_new_removed_and_changed_records():
    prev = frame(("P", "A", 1, "czynny", "2026-10-01", 50.0, 19.0), ("P", "B", 1, "czynny", "2026-10-01", 51.0, 20.0))
    cur = frame(("P", "A", 1, "nieczynny", "2026-11-01", 50.0, 19.0), ("P", "C", 1, "czynny", "2026-11-01", 52.0, 21.0))
    by_result = {r["Wynik"]: r for r in diff_main(prev, cur)}
    assert by_result["nowy rekord"]["Identyfikator AED"] == "C"
    assert by_result["usunięto z wykazu zbiorczego"]["Identyfikator AED"] == "B"
    changed = by_result["zmieniony rekord"]
    assert changed["Identyfikator AED"] == "A"
    assert (
        "Status urządzenia: czynny -> nieczynny" in changed["Powód"]
        and "Data ostatniej weryfikacji: 2026-10-01 -> 2026-11-01" in changed["Powód"]
    )


def test_same_data_gives_no_changes_and_float_noise_is_ignored():
    prev = frame(("P", "A", 1, "czynny", "2026-11-01", 50.0614300, 19.93658))
    cur = frame(("P", "A", 1, "czynny", "2026-11-01", 50.06143000001, 19.93658))
    assert diff_main(prev, cur) == []


def test_same_id_of_different_providers_is_not_confused():
    prev = frame(("P1", "A", 1, "czynny", "2026-11-01", 50.0, 19.0))
    cur = frame(("P2", "A", 2, "czynny", "2026-11-01", 50.0, 19.0))
    results = sorted(r["Wynik"] for r in diff_main(prev, cur))
    assert results == ["nowy rekord", "usunięto z wykazu zbiorczego"]


def test_output_is_capped_per_kind():
    cur = frame(*[("P", str(n), 1, "czynny", "2026-11-01", 50.0, 19.0) for n in range(MAX_ROWS_PER_KIND + 50)])
    prev = frame(("Q", "X", 1, "czynny", "2026-11-01", 50.0, 19.0))
    assert sum(1 for r in diff_main(prev, cur) if r["Wynik"] == "nowy rekord") == MAX_ROWS_PER_KIND
