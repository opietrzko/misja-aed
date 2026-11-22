from django.core.management.base import BaseCommand

from mcod.aed.template import build_template


class Command(BaseCommand):
    help = "Generuje plik xlsx ze wzorcowym zakresem danych o AED (wymóg konkursowy)."

    def add_arguments(self, parser):
        parser.add_argument("output", type=str, help="Ścieżka pliku wynikowego .xlsx")

    def handle(self, *args, **options):
        path = build_template(options["output"])
        self.stdout.write(self.style.SUCCESS(f"Zapisano {path}"))
