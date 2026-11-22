import pytest

from mcod.aed.hours import normalize_hours


@pytest.mark.parametrize(
    "text,expected",
    [
        ("pn\u2013pt 7:30\u201316:00", "Mo-Fr 07:30-16:00"),  # polska półpauza
        ("pn\u2014pt 8-16", "Mo-Fr 08:00-16:00"),  # pauza
        ("pn-pt 7:30-16:00", "Mo-Fr 07:30-16:00"),
        ("pn-pt 7-17", "Mo-Fr 07:00-17:00"),
        ("Mo-Fr 08:00-18:00", "Mo-Fr 08:00-18:00"),
        ("godz: 8.00-18.00 w dni robocze", "Mo-Fr 08:00-18:00"),
        ("8.00-18.00 w dni robocze", "Mo-Fr 08:00-18:00"),
        ("od 8 do 16 codziennie", "Mo-Su 08:00-16:00"),
        ("codziennie 9:00\u201321:00", "Mo-Su 09:00-21:00"),
        ("Mo-Su 07:00-22:00", "Mo-Su 07:00-22:00"),
        ("pn-pt 7-17, sob 9-13", "Mo-Fr 07:00-17:00; Sa 09:00-13:00"),
        ("Mo-Fr 08:00-12:00,14:00-18:00", "Mo-Fr 08:00-12:00,14:00-18:00"),
        ("pon.-pt. 8-16", "Mo-Fr 08:00-16:00"),
        ("pn, śr, pt 8-12", "Mo,We,Fr 08:00-12:00"),
        ("pn-sob 10-20", "Mo-Sa 10:00-20:00"),
        ("sob-pn 10-20", "Mo,Sa,Su 10:00-20:00"),
        ("weekend 10-14", "Sa,Su 10:00-14:00"),
        ("8-12 pn, śr, pt", "Mo,We,Fr 08:00-12:00"),
        ("8-16 pn-pt, 9-13 sob", "Mo-Fr 08:00-16:00; Sa 09:00-13:00"),
    ],
)
def test_parses_polish_and_osm_notations(text, expected):
    assert normalize_hours(text) == expected


@pytest.mark.parametrize(
    "text", ["całodobowo", "24/7", "całą dobę", "24h", "nonstop", "00:00-24:00 codziennie", "caołobowo"[:0] or "całodobowe"]
)
def test_round_the_clock(text):
    assert normalize_hours(text) == "24/7"


def test_blank_text_uses_availability():
    assert normalize_hours("", "całodobowo") == "24/7"
    assert normalize_hours(None, "w godzinach") is None
    assert normalize_hours(float("nan")) is None


@pytest.mark.parametrize(
    "text",
    [
        "8-16",  # brak dni: nie zakładamy, że codziennie
        "po uzgodnieniu",
        "pn-pt 25-30",  # niepoprawne godziny
        "pn-pt 8-12, 10-14",  # nakładające się przedziały
        "pn-pt 8-8",
        "zimą krócej",
    ],
)
def test_does_not_guess(text):
    assert normalize_hours(text) is None


def test_overnight_range_is_kept():
    assert normalize_hours("pn-pt 22:00-06:00") == "Mo-Fr 22:00-06:00"
