from django.core.management.base import BaseCommand

from mcod.aed.utils import create_main_aed_file, create_main_aed_resource


class Command(BaseCommand):
    help = "Scala wykazy AED wszystkich dostawców w zbiorczy zasób (to samo co zadanie Celery)."

    def add_arguments(self, parser):
        parser.add_argument("--file-only", action="store_true", help="Tylko wygeneruj plik CSV, bez zasobu w portalu.")

    def handle(self, *args, **options):
        path = create_main_aed_file()
        self.stdout.write(f"Wygenerowano plik: {path}")
        if options["file_only"]:
            return
        resource = create_main_aed_resource(path)
        self.stdout.write(self.style.SUCCESS(f"Utworzono zasób zbiorczy: {resource.pk} ({resource.title})"))
