from django.db import models
from apps.graves.models import Grave
from django.conf import settings


class Exhumation(models.Model):

    class Status(models.TextChoices):
        PENDING = "PENDING", "En attente de validation"
        VALIDATED = "VALIDATED", "Validée"
        REJECTED = "REJECTED", "Rejetée"

    grave = models.ForeignKey(
        Grave,
        on_delete=models.CASCADE,
        related_name="exhumations"
    )

    responsible_agent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_exhumations"
    )

    exhumation_date = models.DateField()

    reason = models.TextField()

    observations = models.TextField(
        blank=True,
        null=True
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    validated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="validated_exhumations"
    )

    validated_at = models.DateTimeField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"Exhumation #{self.id}"