"""Crée le compte administrateur au déploiement si les variables
d'environnement ADMIN_EMAIL / ADMIN_USERNAME / ADMIN_PASSWORD sont
définies et qu'aucun compte avec cet email n'existe déjà (idempotent —
sans danger si exécuté à chaque déploiement)."""
import os

from django.core.management.base import BaseCommand

from apps.users.models import User


class Command(BaseCommand):
    help = "Crée le compte admin depuis les variables d'environnement (si absent)."

    def handle(self, *args, **options):
        email = os.getenv("ADMIN_EMAIL")
        username = os.getenv("ADMIN_USERNAME")
        password = os.getenv("ADMIN_PASSWORD")

        if not (email and username and password):
            self.stdout.write("ADMIN_EMAIL/ADMIN_USERNAME/ADMIN_PASSWORD non définis — rien à faire.")
            return

        if User.objects.filter(email=email).exists():
            self.stdout.write(self.style.SUCCESS(f"Le compte admin {email} existe déjà — rien à faire."))
            return

        User.objects.create_user(
            username=username,
            email=email,
            password=password,
            role=User.Roles.ADMIN,
        )
        self.stdout.write(self.style.SUCCESS(f"Compte admin {email} créé."))