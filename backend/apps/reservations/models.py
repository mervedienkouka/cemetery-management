from django.db import models
from apps.graves.models import Grave
from django.conf import settings


class Reservation(models.Model):

    class Status(models.TextChoices):
        PENDING = "PENDING", "En attente"
        CONFIRMED = "CONFIRMED", "Confirmée"
        CANCELLED = "CANCELLED", "Annulée"

    grave = models.ForeignKey(
        Grave,
        on_delete=models.CASCADE,
        related_name="reservations"
    )

    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reservations"
    )

    reservation_date = models.DateField()

    expiration_date = models.DateField()

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    notes = models.TextField(
        blank=True,
        null=True
    )

    validated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="validated_reservations"
    )

    validated_at = models.DateTimeField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return f"Reservation #{self.id}"