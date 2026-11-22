import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from mcod.aed.constants import COL_ACCESS, COL_AVAILABILITY, COL_STATUS, COL_VERIFIED
from mcod.aed.converter import convert_dataframe, load_profile, read_any
from mcod.aed.utils import main_df_to_csv_bytes


class Command(BaseCommand):
    help = (
        "Konwertuje dowolny plik z listą AED (csv/xlsx/json/geojson, także Overpass OSM) do wzorcowego układu wykazu AED. "
        "Zapisuje plik wynikowy i raport konwersji. Reguły, bez AI."
    )

    def add_arguments(self, parser):
        parser.add_argument("input", help="Plik wejściowy")
        parser.add_argument("-o", "--output", required=True, help="Plik wynikowy CSV")
        parser.add_argument("--report", help="Raport konwersji CSV (domyślnie obok pliku wynikowego)")
        parser.add_argument("--profile", help="Profil źródła: nazwa (np. osm) albo ścieżka do JSON")
        parser.add_argument("--data-zrodla", help="Data weryfikacji/stanu danych RRRR-MM-DD, gdy źródło jej nie podaje")
        parser.add_argument("--dostepnosc", help="Wartość domyślna dla Dostępności, gdy źródło jej nie podaje")
        parser.add_argument("--dostep", help="Wartość domyślna dla Sposobu dostępu")
        parser.add_argument("--status", help="Wartość domyślna dla Statusu urządzenia")
        parser.add_argument(
            "--osie-pl1992-pn",
            action="store_true",
            help="Współrzędne PL-1992: pierwsza kolumna to północ, druga wschód (domyślnie odwrotnie)",
        )
        parser.add_argument("--prefiks-id", default="AED", help="Prefiks nadawanych identyfikatorów")

    def handle(self, *args, **opts):
        import pandas as pd

        df = read_any(opts["input"])
        profile = load_profile(opts["profile"]) if opts["profile"] else None
        defaults = {}
        for key, col in (("data_zrodla", COL_VERIFIED), ("dostepnosc", COL_AVAILABILITY), ("dostep", COL_ACCESS), ("status", COL_STATUS)):
            if opts.get(key):
                defaults[col] = opts[key]

        out, report, mapping = convert_dataframe(df, profile, defaults, opts["prefiks_id"], opts["osie_pl1992_pn"])

        self.stdout.write("Mapowanie kolumn:")
        self.stdout.write(json.dumps(mapping.as_dict(), ensure_ascii=False, indent=2))
        missing = mapping.missing_required({**((profile or {}).get("defaults") or {}), **defaults})
        if missing:
            self.stdout.write(self.style.WARNING("Brak źródła i wartości domyślnej dla: " + ", ".join(missing)))

        out_path = Path(opts["output"])
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(main_df_to_csv_bytes(out))
        report_path = Path(opts["report"]) if opts.get("report") else out_path.with_name(out_path.stem + "-raport.csv")
        pd.DataFrame(report).to_csv(report_path, index=False)

        stats = pd.Series([r["wynik"] for r in report]).value_counts().to_dict()
        self.stdout.write(self.style.SUCCESS(f"Gotowe: {len(out)} z {len(df)} wierszy. {stats}. Plik: {out_path}, raport: {report_path}"))
        if len(out) == 0:
            raise CommandError("Żaden wiersz nie przeszedł walidacji, sprawdź raport i wartości domyślne.")
