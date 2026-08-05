from django.db import models
from apps.cemeteries.models import Cemetery


class Block(models.Model):
    cemetery = models.ForeignKey(
        Cemetery,
        on_delete=models.CASCADE,
        related_name='blocks'
    )

    name = models.CharField(max_length=100)

    code = models.CharField(
        max_length=20,
        unique=True
    )

    area = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    description = models.TextField(
        blank=True,
        null=True
    )

    # Zones non exploitables (allées, chemins...) à déduire du calcul de
    # capacité (cahier des charges 2.2)
    non_exploitable_area = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Surface non exploitable dans ce bloc (allées, chemins...), en m²"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def estimated_capacity(self):
        """Nombre de places estimées, déduction faite des zones non
        exploitables, sur la base de la taille standard de tombeau du
        cimetière parent (cahier des charges 2.2)."""
        usable_area = self.area - self.non_exploitable_area
        if usable_area <= 0:
            return 0

        grave_surface = (
            self.cemetery.standard_grave_length * self.cemetery.standard_grave_width
        )
        if grave_surface <= 0:
            return 0

        return int(usable_area // grave_surface)

    def __str__(self):
        return f"{self.cemetery.name} - {self.name}"