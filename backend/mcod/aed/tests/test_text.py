import pytest

from mcod.aed.text import norm, normalize_address, text_similarity


def test_norm_strips_diacritics_and_punctuation():
    assert norm("Szerokość geogr.") == "szerokosc geogr"


@pytest.mark.parametrize(
    "street,city,expected",
    [
        ("ul. Paradna 36, 93-345 Łódź", None, ("ul. Paradna 36", "Łódź", "93-345")),
        ("ulica Paradna 36", "Łódź", ("ul. Paradna 36", "Łódź", None)),
        ("Aleja Piłsudskiego 12, 90-001 Łódź", None, ("al. Piłsudskiego 12", "Łódź", "90-001")),
        ("pl. Wolności 1, Poznań", None, ("pl. Wolności 1", "Poznań", None)),
        ("ul. Bydgoska 17/21 Łódź", "Łódź", ("ul. Bydgoska 17/21", "Łódź", None)),
        ("ul.Szewska 4", "Kraków", ("ul. Szewska 4", "Kraków", None)),
        ("os. Słoneczne 5", None, ("os. Słoneczne 5", None, None)),
        # miejscowość podana osobno ma pierwszeństwo przed tą z adresu
        ("ul. Paradna 36, 93-345 Łódź", "Zgierz", ("ul. Paradna 36", "Zgierz", "93-345")),
        (None, None, (None, None, None)),
        ("", "Kraków", (None, "Kraków", None)),
    ],
)
def test_normalize_address(street, city, expected):
    assert tuple(normalize_address(street, city)) == expected


def test_five_digits_without_dash_is_not_a_postal_code():
    # „ul. Długa 12345” to numer budynku, a nie kod pocztowy
    assert normalize_address("ul. Długa 12345", "Kraków").postal is None


def test_similarity_same_and_different_text():
    assert text_similarity("ul. Floriańska 1", "ulica Floriańska 1") == 1.0
    assert text_similarity("hol główny przy recepcji", "hol główny, przy recepcji") == 1.0
    assert text_similarity("ul. Floriańska 1", "ul. Dietla 50") < 0.5


def test_similarity_different_building_numbers_are_capped():
    # prawie identyczny ciąg, ale to dwa różne budynki
    assert text_similarity("ul. Floriańska 1", "ul. Floriańska 10") <= 0.3


def test_similarity_none_when_a_side_is_empty():
    assert text_similarity("", "ul. X 1") is None
    assert text_similarity(None, None) is None
