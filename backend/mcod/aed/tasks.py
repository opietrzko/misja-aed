import logging

from mcod.core.tasks import extended_shared_task

logger = logging.getLogger("mcod")


@extended_shared_task(atomic=False, bind=True, name="mcod.aed.tasks.create_main_aed_resource_task")
def create_main_aed_resource_task(self) -> None:
    """Scala wykazy AED wszystkich dostawców w jeden zbiorczy zasób CSV.

    1. Zbiera opublikowane i zwalidowane zasoby z flagą ``contains_aed_list``.
    2. Odrzuca niepoprawne wiersze, scala i deduplikuje punkty.
    3. Tworzy zasób zbiorczy w zbiorze danych właściciela i podmienia wskaźnik.
    """
    from mcod.aed.utils import create_main_aed_file, create_or_update_main_aed_resource

    path = create_main_aed_file()
    resource = create_or_update_main_aed_resource(path)
    logger.info("Main AED resource created: %s", resource.pk)
