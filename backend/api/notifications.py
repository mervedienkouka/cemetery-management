from django.conf import settings
from django.core.mail import EmailMessage, send_mail


def _admin_emails(User):
    """Renvoie les emails de tous les administrateurs actifs, pour les
    alertes admin (cahier des charges 6)."""
    return list(
        User.objects.filter(role=User.Roles.ADMIN, is_active=True).values_list(
            "email", flat=True
        )
    )


def notify_admins_new_reservation(User, reservation):
    recipients = _admin_emails(User)
    if not recipients:
        return

    send_mail(
        subject="Nouvelle réservation en attente de validation",
        message=(
            f"Une nouvelle réservation (#{reservation.id}) a été soumise par "
            f"{reservation.client.username} pour la tombe "
            f"{reservation.grave.block.code}-{reservation.grave.grave_number}.\n"
            "Merci de la valider ou de la rejeter depuis le back-office."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=recipients,
        fail_silently=True,
    )


def notify_client_reservation_validated(reservation, pdf_bytes: bytes):
    """Envoie la confirmation + la facture PDF en pièce jointe au client
    (cahier des charges 2.4 / 6)."""
    email = EmailMessage(
        subject="Votre réservation a été validée",
        body=(
            f"Bonjour {reservation.client.username},\n\n"
            f"Votre réservation #{reservation.id} a été validée. "
            "Vous trouverez votre facture en pièce jointe."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[reservation.client.email],
    )
    email.attach(f"facture_reservation_{reservation.id}.pdf", pdf_bytes, "application/pdf")
    email.send(fail_silently=True)


def notify_admins_payment_overdue(User, concession, amount_remaining):
    recipients = _admin_emails(User)
    if not recipients:
        return

    send_mail(
        subject="Retard de paiement détecté",
        message=(
            f"La concession {concession.concession_number} (propriétaire "
            f"{concession.owner.username}) a un solde restant de "
            f"{amount_remaining} à régler."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=recipients,
        fail_silently=True,
    )


def notify_admins_critical_occupancy(User, block, occupancy_rate):
    recipients = _admin_emails(User)
    if not recipients:
        return

    send_mail(
        subject=f"Seuil critique de saturation atteint - Bloc {block.code}",
        message=(
            f"Le bloc {block.code} ({block.cemetery.name}) a atteint un taux "
            f"d'occupation de {occupancy_rate:.0f}%."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=recipients,
        fail_silently=True,
    )
