from django.db import models


class Cemetery(models.Model):
    name = models.CharField(max_length=255)

    address = models.TextField()

    city = models.CharField(max_length=100)

    country = models.CharField(max_length=100)

    total_area = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    description = models.TextField(
        blank=True,
        null=True
    )

    # Standardisation de la taille des tombeaux (cahier des charges 2.2)
    standard_grave_length = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=2.50,
        help_text="Longueur standard d'un tombeau (m) pour ce cimetière"
    )

    standard_grave_width = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=1.00,
        help_text="Largeur standard d'un tombeau (m) pour ce cimetière"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return self.name