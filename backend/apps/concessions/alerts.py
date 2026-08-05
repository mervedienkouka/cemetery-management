"""Logique partagée des alertes automatiques (échéances de concession et
retards de paiement) — utilisée à la fois par la commande de gestion
`send_alerts` (pour un cron/planificateur de tâches) et par l'endpoint API
`/alerts/check` (déclenchement manuel depuis le tableau de bord admin,
cahier des charges 2.5)."""
from datetime import date, timedelta

from apps.concessions.models import Concession
from apps.payments.models import Payment
from apps.users.models import User
from api.notifications import notify_admins_payment_overdue


def run_alerts():
    """Exécute les deux vérifications et renvoie un résumé chiffré."""
    expiring = _alert_expiring_concessions()
    overdue = _alert_overdue_payments()
    return {"expiring_concessions": expiring, "overdue_payments": overdue}


def _alert_expiring_concessions():
    threshold = date.today() + timedelta(days=30)

    expiring = Concession.objects.filter(
        status=Concession.Status.ACTIVE,
        end_date__isnull=False,
        end_date__lte=threshold,
        end_date__gte=date.today(),
    )
    return list(expiring)


def _alert_overdue_payments():
    overdue = Payment.objects.filter(
        status=Payment.Status.PENDING,
        payment_date__lt=date.today(),
    )

    alerted = []
    for payment in overdue:
        remaining = payment.amount_due - payment.amount if payment.amount_due else payment.amount
        notify_admins_payment_overdue(User, payment.concession, remaining)
        alerted.append(payment)

    return alerted
