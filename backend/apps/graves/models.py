from django.db import models
from apps.blocks.models import Block


class Grave(models.Model):

    class Status(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Disponible"
        RESERVED = "RESERVED", "Réservé"
        OCCUPIED = "OCCUPIED", "Occupé"
        UNUSABLE = "UNUSABLE", "Inexploitable"

    block = models.ForeignKey(
        Block,
        on_delete=models.CASCADE,
        related_name="graves"
    )

    grave_number = models.CharField(
        max_length=50
    )

    length = models.DecimalField(
        max_digits=5,
        decimal_places=2
    )

    width = models.DecimalField(
        max_digits=5,
        decimal_places=2
    )

    capacity = models.PositiveIntegerField(
        default=1
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.AVAILABLE
    )

    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True
    )

    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True
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
        return f"{self.block.code} - {self.grave_number}"
