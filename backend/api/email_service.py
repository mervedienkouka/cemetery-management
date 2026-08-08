"""Envoi d'email transactionnel via l'API HTTP de Brevo (ex-Sendinblue).

Pourquoi pas Django send_mail/SMTP en production : les hébergeurs gratuits
(Render, Heroku, etc.) bloquent désormais les ports SMTP sortants (25, 465,
587) pour lutter contre le spam. L'API Brevo passe par HTTPS (port 443,
jamais bloqué), donc ça fonctionne même sur un palier gratuit.

Nécessite les variables d'environnement :
  BREVO_API_KEY     — clé API générée sur brevo.com
  BREVO_SENDER_EMAIL — l'adresse expéditeur, vérifiée dans Brevo
"""
import os

import requests

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


class EmailSendError(Exception):
    pass


def send_transactional_email(to_email: str, subject: str, text_content: str, to_name: str = ""):
    api_key = os.getenv("BREVO_API_KEY")
    sender_email = os.getenv("BREVO_SENDER_EMAIL")

    if not api_key or not sender_email:
        raise EmailSendError(
            "BREVO_API_KEY ou BREVO_SENDER_EMAIL manquant dans les variables d'environnement."
        )

    payload = {
        "sender": {"email": sender_email, "name": "Gestion de cimetière"},
        "to": [{"email": to_email, "name": to_name or to_email}],
        "subject": subject,
        "textContent": text_content,
    }
    headers = {
        "accept": "application/json",
        "api-key": api_key,
        "content-type": "application/json",
    }

    try:
        response = requests.post(BREVO_API_URL, json=payload, headers=headers, timeout=15)
    except requests.RequestException as e:
        raise EmailSendError(f"Impossible de contacter Brevo : {e}")

    if response.status_code >= 300:
        raise EmailSendError(f"Brevo a refusé l'envoi (HTTP {response.status_code}) : {response.text}")