from django.core.management.base import BaseCommand

from mcod.aed.utils import build_main_aed, create_or_update_main_aed_resource, publish_auxiliary_resources


class Command(BaseCommand):
    help = "Scala wykazy AED wszystkich dostawców w zbiorczy zasób (to samo co zadanie Celery)."

    def add_arguments(self, parser):
        parser.add_argument("--file-only", action="store_true", help="Tylko wygeneruj plik CSV, bez zasobu w portalu.")

    def handle(self, *args, **options):
        build = build_main_aed()
        self.stdout.write(f"Wygenerowano plik: {build.csv_path} ({len(build.main_df)} rekordów, uwag w raporcie: {len(build.report)})")
        if options["file_only"]:
            return
        resource = create_or_update_main_aed_resource(build.csv_path)
        aux = publish_auxiliary_resources(resource.dataset, build)
        self.stdout.write(
            self.style.SUCCESS(
                f"Zasób zbiorczy gotowy: {resource.pk} ({resource.title}); raport: {aux['report'].pk}; GeoJSON: {aux['geojson'].pk}"
            )
        )
