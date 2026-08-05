from django.db import models
from apps.concessions.models import Concession


class Payment(models.Model):

    class PaymentMethod(models.TextChoices):
        CASH = "CASH", "Espèces"
        MOBILE_MONEY = "MOBILE_MONEY", "Mobile Money"
        AIRTEL_MONEY = "AIRTEL_MONEY", "Airtel Money"
        BANK_TRANSFER = "BANK_TRANSFER", "Virement bancaire"

    class Status(models.TextChoices):
        PENDING = "PENDING", "En attente"
        COMPLETED = "COMPLETED", "Payé"
        FAILED = "FAILED", "Échoué"

    concession = models.ForeignKey(
        Concession,
        on_delete=models.CASCADE,
        related_name="payments"
    )

    amount_due = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Montant total dû pour cette concession, permet de calculer le solde restant"
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    payment_date = models.DateField()

    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices
    )

    reference = models.CharField(
        max_length=100,
        unique=True
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    notes = models.TextField(
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.reference