from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    """Journal d'audit immuable.

    Cahier des charges : chaque action métier (création/modification/
    suppression/connexion) doit laisser une trace immuable. Une fois créée,
    une ligne ne peut plus être modifiée ni supprimée (voir save()/delete()
    ci-dessous, et AuditLogAdmin qui bloque aussi ça côté admin Django).
    """

    class Action(models.TextChoices):
        CREATE = "CREATE", "Création"
        UPDATE = "UPDATE", "Modification"
        DELETE = "DELETE", "Suppression"
        LOGIN = "LOGIN", "Connexion"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )

    action = models.CharField(
        max_length=20,
        choices=Action.choices,
    )

    resource = models.CharField(max_length=100)

    resource_id = models.CharField(
        max_length=50,
        null=True,
        blank=True,
    )

    details = models.TextField(
        blank=True,
        default="",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.created_at}] {self.action} {self.resource}#{self.resource_id}"

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ValueError(
                "Le journal d'audit est immuable : une ligne existante ne peut pas être modifiée."
            )
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError(
            "Le journal d'audit est immuable : une ligne ne peut pas être supprimée."
        )
