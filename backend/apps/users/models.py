from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):

    class Roles(models.TextChoices):
        ADMIN = "ADMIN", "Administrateur"
        SECRETARIAT = "SECRETARIAT", "Secrétariat"
        AGENT_TERRAIN = "AGENT_TERRAIN", "Agent Terrain"
        CLIENT = "CLIENT", "Client"

    email = models.EmailField(unique=True)

    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )

    role = models.CharField(
        max_length=20,
        choices=Roles.choices,
        default=Roles.CLIENT
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    # MFA par email (cahier des charges 2.1 : authentification à double
    # facteur par email obligatoire). Le code n'est jamais stocké en clair.
    mfa_code_hash = models.CharField(
        max_length=64,
        null=True,
        blank=True,
    )

    mfa_code_expires_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return self.email