from django.db import models
from apps.graves.models import Grave
from django.conf import settings


class Concession(models.Model):

    class DurationType(models.TextChoices):
        FIFTEEN_YEARS = "15_YEARS", "15 ans"
        THIRTY_YEARS = "30_YEARS", "30 ans"
        PERPETUAL = "PERPETUAL", "Perpétuelle"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        EXPIRED = "EXPIRED", "Expirée"
        CANCELLED = "CANCELLED", "Annulée"

    grave = models.ForeignKey(
        Grave,
        on_delete=models.CASCADE,
        related_name="concessions"
    )

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="concessions"
    )

    concession_number = models.CharField(
        max_length=50,
        unique=True
    )

    duration_type = models.CharField(
        max_length=20,
        choices=DurationType.choices
    )

    start_date = models.DateField()

    end_date = models.DateField(
        null=True,
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE
    )

    notes = models.TextField(
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return self.concession_number