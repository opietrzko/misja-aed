import pandas as pd
import pytest

from mcod.aed.constants import (
    COL_AVAILABILITY,
    COL_CITY,
    COL_CONTACT,
    COL_DAYS_SINCE,
    COL_HOURS_NORM,
    COL_LAT,
    COL_LOCATION,
    COL_LON,
    COL_OBJECT_TYPE,
    COL_SOURCES_COUNT,
    COL_STATUS,
    COL_STREET,
    COL_TERYT,
)
from mcod.aed.quality import (
    anomalies,
    completeness_points,
    coordinate_decimals,
    corroboration_points,
    freshness_points,
    merge_confidence,
    precision_points,
    trust_score,
)


def full_row(**over):
    row = {
        COL_CITY: "Kraków",
        COL_STREET: "ul. Floriańska 1",
        COL_TERYT: "1261011",
        COL_LOCATION: "hol",
        COL_OBJECT_TYPE: "urząd",
        COL_CONTACT: "bhp@example.pl",
        COL_AVAILABILITY: "całodobowo",
        COL_HOURS_NORM: "24/7",
        COL_STATUS: "czynny",
        COL_DAYS_SINCE: 20,
        COL_SOURCES_COUNT: 1,
        COL_LAT: 50.06143,
        COL_LON: 19.93658,
    }
    row.update(over)
    return pd.Series(row)


@pytest.mark.parametrize("value,digits", [(50.06143, 5), (50.06, 2), (50.0, 0), (50.123, 3), (50.123456789, 7), (None, 0)])
def test_coordinate_decimals(value, digits):
    assert coordinate_decimals(value) == digits


def test_best_record_scores_100_minus_corroboration():
    # komplet pól, świeży, 5 miejsc po przecinku, godziny 24/7, ale jedno źródło
    assert trust_score(full_row()) == 80
    assert trust_score(full_row(**{COL_SOURCES_COUNT: 3})) == 100


def test_corroboration_points():
    assert [corroboration_points(n) for n in (1, 2, 3, 5)] == [0, 15, 20, 20]


def test_freshness_points_and_to_verify_is_half():
    assert [freshness_points(d, "czynny") for d in (10, 200, 500, 900)] == [30, 22, 10, 0]
    assert freshness_points(10, "do weryfikacji") == 15
    assert freshness_points(-5, "czynny") == 5
    assert freshness_points(None, "czynny") == 0


def test_completeness_counts_hours_only_for_hours_availability():
    empty = full_row(
        **{COL_CITY: None, COL_STREET: None, COL_TERYT: None, COL_LOCATION: None, COL_OBJECT_TYPE: None, COL_CONTACT: None}
    )
    assert completeness_points(empty) == 0
    assert completeness_points(full_row()) == 30
    with_hours = full_row(**{COL_AVAILABILITY: "w godzinach", COL_HOURS_NORM: None})
    assert completeness_points(with_hours) == round(30 * 6 / 7)  # godziny wchodzą do opisu i ich brakuje


def test_precision_points():
    assert [
        precision_points(50.06143, 19.93658),
        precision_points(50.0614, 19.9365),
        precision_points(50.061, 19.936),
        precision_points(50.06, 19.93),
    ] == [10, 7, 3, 0]


def test_anomalies_and_penalty():
    low = full_row(**{COL_LAT: 50.06, COL_LON: 19.93})
    notes = anomalies(low, same_point_count=4, hours_unparsed=True)
    assert len(notes) == 3
    assert any("bardzo niska precyzja" in n for n in notes)
    assert any("4 rekordach" in n for n in notes)
    assert trust_score(low, anomaly_count=len(notes)) == trust_score(low) - 30


def test_future_date_is_an_anomaly():
    assert any("z przyszłości" in n for n in anomalies(full_row(**{COL_DAYS_SINCE: -3})))


def test_broken_device_is_capped_and_score_never_negative():
    assert trust_score(full_row(**{COL_STATUS: "nieczynny", COL_SOURCES_COUNT: 3})) == 20
    assert trust_score(full_row(**{COL_DAYS_SINCE: 900, COL_LAT: 50.0, COL_LON: 19.0}), anomaly_count=10) == 0


@pytest.mark.parametrize(
    "distance,similarity,expected",
    [(0, None, 100), (3, 1.0, 100), (10, 1.0, 91), (30, 0.7, 54), (50, 0.6, 24), (60, None, 0)],
)
def test_merge_confidence(distance, similarity, expected):
    assert merge_confidence(distance, similarity, max_m=50) == expected
