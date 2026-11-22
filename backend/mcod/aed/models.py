from typing import Optional

from django.core.exceptions import ValidationError
from django.db import models


class AggregatedAEDInfo(models.Model):
    """Wskaźnik na aktualny zbiorczy wykaz AED (odpowiednik AggregatedDGAInfo)."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resource = models.ForeignKey("resources.Resource", on_delete=models.SET_NULL, null=True)

    def save(self, *args, **kwargs):
        if not self.id and AggregatedAEDInfo.objects.exists():
            raise ValidationError("There can be only one AggregatedAEDInfo instance")
        return super().save(*args, **kwargs)

    @property
    def main_aed_resource(self) -> Optional["Resource"]:  # noqa: F821
        if self.resource and self.resource.is_published and not self.resource.is_removed:
            return self.resource
        return None

    @property
    def main_aed_dataset(self) -> Optional["Dataset"]:  # noqa: F821
        if self.resource and self.resource.dataset.is_published and not self.resource.dataset.is_removed:
            return self.resource.dataset
        return None

    class Meta:
        verbose_name = "Zbiorczy wykaz AED"
        verbose_name_plural = "Zbiorczy wykaz AED"
