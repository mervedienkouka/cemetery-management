"""Alertes automatiques : échéances de concession proches et retards de
paiement (cahier des charges 2.5 "alertes automatiques" et §6 "alertes
admin"). À planifier via une tâche cron/systemd-timer, ex :

    0 7 * * * cd /path/to/backend && python manage.py send_alerts

(exécution quotidienne à 7h). Peut aussi être déclenché manuellement
depuis le tableau de bord admin via l'endpoint POST /alerts/check.
"""
from django.core.management.base import BaseCommand

from apps.concessions.alerts import run_alerts


class Command(BaseCommand):
    help = "Envoie les alertes d'échéance de concession et de retard de paiement."

    def handle(self, *args, **options):
        result = run_alerts()
        for c in result["expiring_concessions"]:
            self.stdout.write(f"[ALERTE] Concession {c.concession_number} expire le {c.end_date}")
        for p in result["overdue_payments"]:
            self.stdout.write(f"[ALERTE] Paiement en retard : {p.reference} (concession {p.concession.concession_number})")
        self.stdout.write(self.style.SUCCESS(
            f"{len(result['expiring_concessions'])} concession(s) proche(s) d'échéance, "
            f"{len(result['overdue_payments'])} paiement(s) en retard."
        ))
