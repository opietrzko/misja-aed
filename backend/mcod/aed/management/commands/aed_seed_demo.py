import datetime
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand

from mcod.aed.constants import MAIN_AED_COLUMNS  # noqa: F401

DEMO_DIR = Path(__file__).resolve().parents[2] / "demo_data"

OWNER = {"title": "Ministerstwo Cyfryzacji", "abbr": "MC", "type": "state"}

PROVIDERS = [
    {
        "file": "urzad-miasta-demo-krakow.csv",
        "title": "Urząd Miasta Demo-Kraków",
        "abbr": "UMDK",
        "type": "local",
        "scope": "AED w budynkach i na obiektach miejskich Krakowa",
    },
    {
        "file": "fundacja-demo-ratownik.csv",
        "title": "Fundacja Demo-Ratownik",
        "abbr": "FDR",
        "type": "other",
        "scope": "AED w przestrzeni publicznej Krakowa i Warszawy (inicjatywa oddolna)",
    },
    {
        "file": "wcr-demo-gdansk.csv",
        "title": "Wojewódzkie Centrum Ratownictwa Demo-Gdańsk",
        "abbr": "WCRDG",
        "type": "state",
        "scope": "AED w Gdańsku i okolicach",
    },
]


class Command(BaseCommand):
    help = "Tworzy 3 fikcyjnych dysponentów z wykazami AED (dane syntetyczne) do demonstracji."

    def handle(self, *args, **options):
        from mcod.datasets.models import Dataset
        from mcod.organizations.models import Organization
        from mcod.resources.models import Resource, ResourceFile

        for p in [OWNER] + PROVIDERS:
            org, _ = Organization.objects.get_or_create(
                title=p["title"],
                defaults=dict(
                    slug=p["abbr"].lower(),
                    abbreviation=p["abbr"],
                    description=f"{p['title']} - dysponent demonstracyjny Misji AED (dane syntetyczne).",
                    institution_type=getattr(Organization, f"INSTITUTION_TYPE_{p['type'].upper()}"),
                    postal_code="00-001",
                    city="Demo",
                    street_type="ul.",
                    street="Przykładowa",
                    street_number="1",
                    email="demo@example.pl",
                    epuap="/demo/SkrytkaESP",
                    fax="000000000",
                    tel="000000000",
                    regon="000000000",
                    website="https://example.pl",
                ),
            )
            if "file" not in p:  # właściciel zbioru zbiorczego - bez własnego wykazu
                continue
            if Resource.objects.filter(dataset__organization=org, contains_aed_list=True).exists():
                self.stdout.write(f"{p['title']}: wykaz już istnieje, pomijam")
                continue
            dataset, _ = Dataset.objects.get_or_create(
                title=f"Wykaz defibrylatorów AED - {p['title']}",
                organization=org,
                defaults=dict(
                    notes=f"Wykaz AED dysponenta {p['title']}. Zakres: {p['scope']}. Dane syntetyczne (demonstracja).",
                    update_frequency="daily",
                    has_dynamic_data=False,
                    has_high_value_data=False,
                    has_high_value_data_from_ec_list=False,
                    has_research_data=False,
                    status="published",
                ),
            )
            if Resource.objects.filter(dataset=dataset, contains_aed_list=True).exists():
                self.stdout.write(f"{p['title']}: wykaz już istnieje, pomijam")
                continue
            path = DEMO_DIR / p["file"]
            resource = Resource.objects.create(
                title=f"Wykaz AED - {p['scope']}",
                description=f"Zakres referencyjny: {p['scope']}. Dane syntetyczne.",
                dataset=dataset,
                has_dynamic_data=False,
                has_high_value_data=False,
                has_high_value_data_from_ec_list=False,
                has_research_data=False,
                contains_aed_list=True,
                status="published",
                data_date=datetime.date.today(),
            )
            ResourceFile.objects.create(
                resource=resource,
                is_main=True,
                file=SimpleUploadedFile(path.name, path.read_bytes(), content_type="text/csv"),
            )
            self.stdout.write(self.style.SUCCESS(f"{p['title']}: utworzono zasób {resource.pk}"))
