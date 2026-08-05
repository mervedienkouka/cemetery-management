import csv
import hashlib
import io
import jwt
import secrets
from datetime import datetime, timedelta, timezone

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.core.mail import send_mail
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from ninja import NinjaAPI, Schema
from ninja.errors import HttpError
from ninja.security import HttpBearer

from typing import Optional

from apps.cemeteries.models import Cemetery
from apps.blocks.models import Block
from apps.graves.models import Grave
from apps.reservations.models import Reservation
from apps.concessions.models import Concession
from apps.concessions.alerts import run_alerts
from apps.payments.models import Payment
from apps.exhumations.models import Exhumation
from apps.users.models import User

from apps.audit.models import AuditLog

from api.documents import generate_invoice_pdf, generate_exhumation_pv_pdf
from api.notifications import (
    notify_admins_new_reservation,
    notify_client_reservation_validated,
    notify_admins_critical_occupancy,
)

User = get_user_model()

# ==========================================================
# CONSTANTES (un seul jeu de constantes, plus de doublons)
# ==========================================================

JWT_ALGORITHM = "HS256"
JWT_SECRET = settings.SECRET_KEY  # à remplacer par une clé JWT dédiée si tu en as une

ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7
MFA_TOKEN_EXPIRE_MINUTES = 5  # durée de vie du temp_token (étape 1 -> étape 2)
MFA_CODE_EXPIRE_MINUTES = getattr(settings, "MFA_CODE_EXPIRE_MINUTES", 10)  # durée de vie du code reçu par email

# Rôles RBAC : valeurs alignées sur apps.users.models.User.Roles
# (ADMIN, SECRETARIAT, AGENT_TERRAIN, CLIENT — il n'y a pas de rôle "comptable").
# Répartition retenue :
#   - AGENT_TERRAIN : opérations physiques (cimetières/blocs/tombes, exhumations)
#   - SECRETARIAT   : front office administratif (réservations, concessions, paiements)
#   - ADMIN         : accès complet, y compris les suppressions sensibles
#   - CLIENT        : ses propres données uniquement
ROLE_ADMIN = User.Roles.ADMIN
ROLE_SECRETARIAT = User.Roles.SECRETARIAT
ROLE_AGENT_TERRAIN = User.Roles.AGENT_TERRAIN
ROLE_CLIENT = User.Roles.CLIENT

ALL_ROLES = (ROLE_ADMIN, ROLE_SECRETARIAT, ROLE_AGENT_TERRAIN, ROLE_CLIENT)

api = NinjaAPI()


# ==========================================================
# JWT - HELPERS
# ==========================================================

def create_access_token(user):
    payload = {
        "user_id": user.id,
        "username": user.username,
        "role": user.role,
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_refresh_token(user):
    payload = {
        "user_id": user.id,
        "type": "refresh",
        "exp": datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_mfa_pending_token(user):
    """Jeton temporaire à courte durée de vie, émis après un mot de passe
    correct mais avant la vérification du code MFA."""
    payload = {
        "user_id": user.id,
        "type": "mfa_pending",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=MFA_TOKEN_EXPIRE_MINUTES),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _hash_mfa_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def generate_and_send_mfa_code(user):
    """Génère un code à 6 chiffres, le stocke hashé avec une expiration,
    puis l'envoie par email (cahier des charges 2.1 : MFA par email
    obligatoire)."""
    code = f"{secrets.randbelow(1_000_000):06d}"

    user.mfa_code_hash = _hash_mfa_code(code)
    user.mfa_code_expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=MFA_CODE_EXPIRE_MINUTES
    )
    user.save(update_fields=["mfa_code_hash", "mfa_code_expires_at"])

    try:
        send_mail(
            subject="Votre code de vérification",
            message=(
                f"Votre code de connexion est : {code}\n"
                f"Il expire dans {MFA_CODE_EXPIRE_MINUTES} minutes."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
    except Exception as e:
        raise HttpError(
            502,
            "Impossible d'envoyer l'email de vérification. Vérifie la configuration "
            f"SMTP dans .env (EMAIL_HOST_USER/EMAIL_HOST_PASSWORD). Détail technique : {e}",
        )


def verify_mfa_code(user, submitted_code: str) -> bool:
    """Vérifie le code MFA soumis contre le hash stocké, en respectant
    l'expiration. Le code est invalidé après vérification (usage unique),
    qu'elle réussisse ou échoue."""
    stored_hash = user.mfa_code_hash
    expires_at = user.mfa_code_expires_at

    user.mfa_code_hash = None
    user.mfa_code_expires_at = None
    user.save(update_fields=["mfa_code_hash", "mfa_code_expires_at"])

    if not stored_hash or not expires_at:
        return False
    if datetime.now(timezone.utc) > expires_at:
        return False

    return secrets.compare_digest(stored_hash, _hash_mfa_code(submitted_code))


def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            return None
        return payload
    except Exception:
        return None


class BearerAuth(HttpBearer):
    def authenticate(self, request, token: str):
        payload = decode_access_token(token)
        if not payload:
            return None
        try:
            user = User.objects.get(id=payload["user_id"])
            if not user.is_active:
                return None
            return user
        except User.DoesNotExist:
            return None


# ==========================================================
# RBAC - HELPER
# ==========================================================

def require_roles(request, *roles):
    """Vérifie que l'utilisateur authentifié possède l'un des rôles fournis.
    À appeler en première ligne de toute route protégée par rôle."""
    user_role = getattr(request.auth, "role", None)
    if user_role not in roles:
        raise HttpError(403, "Accès refusé : rôle insuffisant pour cette action.")


def scope_to_owner_if_client(request, queryset, owner_field):
    """Si l'utilisateur est un client, restreint le queryset à ses propres
    enregistrements. Les autres rôles voient tout (selon leurs droits)."""
    if getattr(request.auth, "role", None) == ROLE_CLIENT:
        return queryset.filter(**{owner_field: request.auth})
    return queryset


# ==========================================================
# AUDIT - HELPER (journal immuable : uniquement des créations de lignes)
# ==========================================================

def log_action(request, action: str, resource: str, resource_id, details: str = "", user=None):
    """Écrit une ligne dans le journal d'audit. Ne doit jamais faire échouer
    l'action métier : en cas d'erreur d'écriture, on avale l'exception mais
    ça doit être supervisé (Sentry/logging) en prod.

    `user` peut être passé explicitement quand request.auth n'est pas encore
    défini (ex: pendant le login lui-même, avant que BearerAuth ne s'exécute).
    """
    try:
        AuditLog.objects.create(
            user=user if user is not None else getattr(request, "auth", None),
            action=action,
            resource=resource,
            resource_id=resource_id,
            details=details,
        )
    except Exception:
        pass


# ==========================================================
# SCHEMAS - AUTH
# ==========================================================

class LoginSchema(Schema):
    email: str
    password: str


class TokenSchema(Schema):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"


class MFARequiredSchema(Schema):
    mfa_required: bool = True
    temp_token: str


class VerifyMFASchema(Schema):
    temp_token: str
    otp_code: str


class RefreshSchema(Schema):
    refresh_token: str


class AccessTokenSchema(Schema):
    access_token: str
    token_type: str = "Bearer"


class UserMeOut(Schema):
    id: int
    email: str
    username: str
    role: str
    phone: Optional[str] = None
    is_active: bool = True


class RegisterSchema(Schema):
    username: str
    email: str
    password: str
    phone: str = ""


class UpdateRoleSchema(Schema):
    role: str


class ToggleActiveSchema(Schema):
    is_active: bool


# ==========================================================
# HOME
# ==========================================================

@api.get("/")
def home(request):
    return {
        "message": "Cemetery Management API"
    }


# ==========================================================
# SCHEMAS - CEMETERY
# ==========================================================

class CemeteryIn(Schema):
    name: str
    address: str
    city: str
    country: str
    total_area: float
    description: str = ""
    standard_grave_length: float = 2.50
    standard_grave_width: float = 1.00


class CemeteryOut(Schema):
    id: int
    name: str
    address: str
    city: str
    country: str
    total_area: float
    description: str | None
    standard_grave_length: float
    standard_grave_width: float


# ==========================================================
# SCHEMAS - BLOCK
# ==========================================================

class BlockIn(Schema):
    cemetery_id: int
    name: str
    code: str
    area: float
    description: str = ""
    non_exploitable_area: float = 0


class BlockOut(Schema):
    id: int
    cemetery_id: int
    name: str
    code: str
    area: float
    description: str | None
    non_exploitable_area: float
    estimated_capacity: int


# ==========================================================
# SCHEMAS - GRAVE
# ==========================================================

class GraveIn(Schema):
    block_id: int
    grave_number: str
    length: float
    width: float
    capacity: int
    status: str
    latitude: float | None = None
    longitude: float | None = None
    notes: str = ""


class GraveOut(Schema):
    id: int
    block_id: int
    grave_number: str
    length: float
    width: float
    capacity: int
    status: str
    latitude: float | None
    longitude: float | None
    notes: str | None


# ==========================================================
# SCHEMAS - RESERVATION
# ==========================================================

class ReservationIn(Schema):
    grave_id: int
    client_id: int
    reservation_date: str
    expiration_date: str
    status: str
    notes: str = ""


class ReservationOut(Schema):
    id: int
    grave_id: int
    client_id: int
    reservation_date: str
    expiration_date: str
    status: str
    notes: str | None
    validated_by_id: int | None = None
    validated_at: str | None = None


# ==========================================================
# SCHEMAS - CONCESSION
# ==========================================================

class ConcessionIn(Schema):
    grave_id: int
    owner_id: int
    concession_number: str
    duration_type: str
    start_date: str
    end_date: str | None = None
    status: str
    notes: str = ""


class ConcessionOut(Schema):
    id: int
    grave_id: int
    owner_id: int
    concession_number: str
    duration_type: str
    start_date: str
    end_date: str | None
    status: str
    notes: str | None


# ==========================================================
# SCHEMAS - PAYMENT
# ==========================================================

class PaymentIn(Schema):
    concession_id: int
    amount: float
    amount_due: float | None = None
    payment_date: str
    payment_method: str
    reference: str
    status: str
    notes: str = ""


class PaymentOut(Schema):
    id: int
    concession_id: int
    amount: float
    amount_due: float | None
    payment_date: str
    payment_method: str
    reference: str
    status: str
    notes: str | None


# ==========================================================
# SCHEMAS - EXHUMATION
# ==========================================================

class ExhumationIn(Schema):
    grave_id: int
    responsible_agent_id: int | None = None
    exhumation_date: str
    reason: str
    observations: str = ""


class ExhumationOut(Schema):
    id: int
    grave_id: int
    responsible_agent_id: int | None
    exhumation_date: str
    reason: str
    observations: str | None
    status: str
    validated_by_id: int | None = None
    validated_at: str | None = None


# ==========================================================
# CRUD - CEMETERIES
# Lecture : tous rôles authentifiés | Écriture : ADMIN, AGENT_TERRAIN | Suppression : ADMIN
# ==========================================================

@api.get("/cemeteries", response=list[CemeteryOut], auth=BearerAuth())
def list_cemeteries(request):
    return Cemetery.objects.all()


@api.get("/cemeteries/{cemetery_id}", response=CemeteryOut, auth=BearerAuth())
def get_cemetery(request, cemetery_id: int):
    return get_object_or_404(Cemetery, id=cemetery_id)


@api.post("/cemeteries", auth=BearerAuth())
def create_cemetery(request, payload: CemeteryIn):
    require_roles(request, ROLE_ADMIN, ROLE_AGENT_TERRAIN)

    cemetery = Cemetery.objects.create(
        name=payload.name,
        address=payload.address,
        city=payload.city,
        country=payload.country,
        total_area=payload.total_area,
        description=payload.description,
        standard_grave_length=payload.standard_grave_length,
        standard_grave_width=payload.standard_grave_width,
    )
    log_action(request, "CREATE", "Cemetery", cemetery.id)

    return {
        "id": cemetery.id,
        "message": "Cemetery created successfully"
    }


@api.put("/cemeteries/{cemetery_id}", auth=BearerAuth())
def update_cemetery(request, cemetery_id: int, payload: CemeteryIn):
    require_roles(request, ROLE_ADMIN, ROLE_AGENT_TERRAIN)

    cemetery = get_object_or_404(Cemetery, id=cemetery_id)

    cemetery.name = payload.name
    cemetery.address = payload.address
    cemetery.city = payload.city
    cemetery.country = payload.country
    cemetery.total_area = payload.total_area
    cemetery.description = payload.description
    cemetery.standard_grave_length = payload.standard_grave_length
    cemetery.standard_grave_width = payload.standard_grave_width
    cemetery.save()

    log_action(request, "UPDATE", "Cemetery", cemetery.id)

    return {
        "message": "Cemetery updated successfully"
    }


@api.delete("/cemeteries/{cemetery_id}", auth=BearerAuth())
def delete_cemetery(request, cemetery_id: int):
    require_roles(request, ROLE_ADMIN)

    cemetery = get_object_or_404(Cemetery, id=cemetery_id)
    cemetery.delete()

    log_action(request, "DELETE", "Cemetery", cemetery_id)

    return {
        "message": "Cemetery deleted successfully"
    }


# ==========================================================
# CRUD - BLOCKS
# Lecture : tous rôles authentifiés | Écriture : ADMIN, AGENT_TERRAIN | Suppression : ADMIN
# ==========================================================

@api.get("/blocks", response=list[BlockOut], auth=BearerAuth())
def list_blocks(request):
    return [
        {
            "id": block.id,
            "cemetery_id": block.cemetery.id,
            "name": block.name,
            "code": block.code,
            "area": block.area,
            "description": block.description,
            "non_exploitable_area": block.non_exploitable_area,
            "estimated_capacity": block.estimated_capacity(),
        }
        for block in Block.objects.all()
    ]


@api.get("/blocks/{block_id}", response=BlockOut, auth=BearerAuth())
def get_block(request, block_id: int):
    block = get_object_or_404(Block, id=block_id)

    return {
        "id": block.id,
        "cemetery_id": block.cemetery.id,
        "name": block.name,
        "code": block.code,
        "area": block.area,
        "description": block.description,
        "non_exploitable_area": block.non_exploitable_area,
        "estimated_capacity": block.estimated_capacity(),
    }


@api.post("/blocks", auth=BearerAuth())
def create_block(request, payload: BlockIn):
    require_roles(request, ROLE_ADMIN, ROLE_AGENT_TERRAIN)

    try:
        cemetery = get_object_or_404(Cemetery, id=payload.cemetery_id)

        block = Block.objects.create(
            cemetery=cemetery,
            name=payload.name,
            code=payload.code,
            area=payload.area,
            description=payload.description,
            non_exploitable_area=payload.non_exploitable_area,
        )
        log_action(request, "CREATE", "Block", block.id)

        return {
            "id": block.id,
            "message": "Block created successfully"
        }

    except Exception as e:
        raise HttpError(400, str(e))


@api.put("/blocks/{block_id}", auth=BearerAuth())
def update_block(request, block_id: int, payload: BlockIn):
    require_roles(request, ROLE_ADMIN, ROLE_AGENT_TERRAIN)

    block = get_object_or_404(Block, id=block_id)

    block.cemetery = get_object_or_404(Cemetery, id=payload.cemetery_id)
    block.name = payload.name
    block.code = payload.code
    block.area = payload.area
    block.description = payload.description
    block.non_exploitable_area = payload.non_exploitable_area
    block.save()

    log_action(request, "UPDATE", "Block", block.id)

    return {
        "message": "Block updated successfully"
    }


@api.delete("/blocks/{block_id}", auth=BearerAuth())
def delete_block(request, block_id: int):
    require_roles(request, ROLE_ADMIN)

    block = get_object_or_404(Block, id=block_id)
    block.delete()

    log_action(request, "DELETE", "Block", block_id)

    return {
        "message": "Block deleted successfully"
    }


# ==========================================================
# CRUD - GRAVES
# Lecture : tous rôles authentifiés | Écriture : ADMIN, AGENT_TERRAIN | Suppression : ADMIN
# ==========================================================

@api.get("/graves", response=list[GraveOut], auth=BearerAuth())
def list_graves(request):
    return [
        {
            "id": grave.id,
            "block_id": grave.block.id,
            "grave_number": grave.grave_number,
            "length": grave.length,
            "width": grave.width,
            "capacity": grave.capacity,
            "status": grave.status,
            "latitude": grave.latitude,
            "longitude": grave.longitude,
            "notes": grave.notes,
        }
        for grave in Grave.objects.all()
    ]


@api.get("/graves/{grave_id}", response=GraveOut, auth=BearerAuth())
def get_grave(request, grave_id: int):
    grave = get_object_or_404(Grave, id=grave_id)

    return {
        "id": grave.id,
        "block_id": grave.block.id,
        "grave_number": grave.grave_number,
        "length": grave.length,
        "width": grave.width,
        "capacity": grave.capacity,
        "status": grave.status,
        "latitude": grave.latitude,
        "longitude": grave.longitude,
        "notes": grave.notes,
    }


@api.post("/graves", auth=BearerAuth())
def create_grave(request, payload: GraveIn):
    require_roles(request, ROLE_ADMIN, ROLE_AGENT_TERRAIN)

    try:
        block = get_object_or_404(Block, id=payload.block_id)

        grave = Grave.objects.create(
            block=block,
            grave_number=payload.grave_number,
            length=payload.length,
            width=payload.width,
            capacity=payload.capacity,
            status=payload.status,
            latitude=payload.latitude,
            longitude=payload.longitude,
            notes=payload.notes,
        )
        log_action(request, "CREATE", "Grave", grave.id)

        return {
            "id": grave.id,
            "message": "Grave created successfully"
        }

    except Exception as e:
        raise HttpError(400, str(e))


@api.put("/graves/{grave_id}", auth=BearerAuth())
def update_grave(request, grave_id: int, payload: GraveIn):
    require_roles(request, ROLE_ADMIN, ROLE_AGENT_TERRAIN)

    grave = get_object_or_404(Grave, id=grave_id)

    grave.block = get_object_or_404(Block, id=payload.block_id)
    grave.grave_number = payload.grave_number
    grave.length = payload.length
    grave.width = payload.width
    grave.capacity = payload.capacity
    grave.status = payload.status
    grave.latitude = payload.latitude
    grave.longitude = payload.longitude
    grave.notes = payload.notes
    grave.save()

    log_action(request, "UPDATE", "Grave", grave.id)

    return {
        "message": "Grave updated successfully"
    }


@api.delete("/graves/{grave_id}", auth=BearerAuth())
def delete_grave(request, grave_id: int):
    require_roles(request, ROLE_ADMIN)

    grave = get_object_or_404(Grave, id=grave_id)
    grave.delete()

    log_action(request, "DELETE", "Grave", grave_id)

    return {
        "message": "Grave deleted successfully"
    }


# ==========================================================
# CRUD - RESERVATIONS
# Lecture : ADMIN/SECRETARIAT (tout) + CLIENT (les siennes uniquement)
# Écriture : ADMIN, SECRETARIAT, CLIENT (création) | Modification/suppression : ADMIN, SECRETARIAT
# ==========================================================

@api.get("/reservations", response=list[ReservationOut], auth=BearerAuth())
def list_reservations(request):
    require_roles(request, ROLE_ADMIN, ROLE_SECRETARIAT, ROLE_CLIENT)

    queryset = scope_to_owner_if_client(request, Reservation.objects.all(), "client")

    return [
        {
            "id": reservation.id,
            "grave_id": reservation.grave.id,
            "client_id": reservation.client.id,
            "reservation_date": str(reservation.reservation_date),
            "expiration_date": str(reservation.expiration_date),
            "status": reservation.status,
            "notes": reservation.notes,
            "validated_by_id": reservation.validated_by_id,
            "validated_at": str(reservation.validated_at) if reservation.validated_at else None,
        }
        for reservation in queryset
    ]


@api.get("/reservations/{reservation_id}", response=ReservationOut, auth=BearerAuth())
def get_reservation(request, reservation_id: int):
    require_roles(request, ROLE_ADMIN, ROLE_SECRETARIAT, ROLE_CLIENT)

    reservation = get_object_or_404(Reservation, id=reservation_id)

    if request.auth.role == ROLE_CLIENT and reservation.client_id != request.auth.id:
        raise HttpError(403, "Accès refusé : cette réservation ne t'appartient pas.")

    return {
        "id": reservation.id,
        "grave_id": reservation.grave.id,
        "client_id": reservation.client.id,
        "reservation_date": str(reservation.reservation_date),
        "expiration_date": str(reservation.expiration_date),
        "status": reservation.status,
        "notes": reservation.notes,
        "validated_by_id": reservation.validated_by_id,
        "validated_at": str(reservation.validated_at) if reservation.validated_at else None,
    }


@api.post("/reservations", auth=BearerAuth())
def create_reservation(request, payload: ReservationIn):
    require_roles(request, ROLE_ADMIN, ROLE_SECRETARIAT, ROLE_CLIENT)

    # Un client ne peut réserver que pour lui-même.
    if request.auth.role == ROLE_CLIENT and payload.client_id != request.auth.id:
        raise HttpError(403, "Un client ne peut réserver que pour son propre compte.")

    try:
        grave = get_object_or_404(Grave, id=payload.grave_id)
        client = get_object_or_404(User, id=payload.client_id)

        reservation = Reservation.objects.create(
            grave=grave,
            client=client,
            reservation_date=payload.reservation_date,
            expiration_date=payload.expiration_date,
            status=payload.status,
            notes=payload.notes,
        )

        # Carte SIG : la tombe passe en "Réservé" (orange) tant que la
        # réservation n'est pas validée par un administrateur.
        grave.status = Grave.Status.RESERVED
        grave.save(update_fields=["status"])

        log_action(request, "CREATE", "Reservation", reservation.id)
        notify_admins_new_reservation(User, reservation)

        return {
            "id": reservation.id,
            "message": "Reservation created successfully"
        }

    except Exception as e:
        raise HttpError(400, str(e))


@api.put("/reservations/{reservation_id}", auth=BearerAuth())
def update_reservation(request, reservation_id: int, payload: ReservationIn):
    require_roles(request, ROLE_ADMIN, ROLE_SECRETARIAT)

    reservation = get_object_or_404(Reservation, id=reservation_id)

    reservation.grave = get_object_or_404(Grave, id=payload.grave_id)
    reservation.client = get_object_or_404(User, id=payload.client_id)
    reservation.reservation_date = payload.reservation_date
    reservation.expiration_date = payload.expiration_date
    reservation.status = payload.status
    reservation.notes = payload.notes
    reservation.save()

    log_action(request, "UPDATE", "Reservation", reservation.id)

    return {
        "message": "Reservation updated successfully"
    }


@api.post("/reservations/{reservation_id}/validate", auth=BearerAuth())
def validate_reservation(request, reservation_id: int):
    """Validation admin d'une réservation (cahier des charges 2.4) :
    - la tombe passe de Réservé (orange) à Occupé/Validé (rouge)
    - une facture PDF est générée et envoyée par email au client
    """
    require_roles(request, ROLE_ADMIN, ROLE_SECRETARIAT)

    reservation = get_object_or_404(Reservation, id=reservation_id)

    if reservation.status == Reservation.Status.CONFIRMED:
        raise HttpError(400, "Cette réservation est déjà validée.")

    reservation.status = Reservation.Status.CONFIRMED
    reservation.validated_by = request.auth
    reservation.validated_at = datetime.now(timezone.utc)
    reservation.save()

    grave = reservation.grave
    grave.status = Grave.Status.OCCUPIED
    grave.save(update_fields=["status"])

    pdf_bytes = generate_invoice_pdf(reservation, grave, reservation.client)
    notify_client_reservation_validated(reservation, pdf_bytes)

    log_action(request, "UPDATE", "Reservation", reservation.id, "Validation + facture envoyée")

    # Alerte de saturation si le bloc atteint un seuil critique (>90%)
    block = grave.block
    capacity = block.estimated_capacity()
    if capacity > 0:
        occupied = block.graves.filter(status=Grave.Status.OCCUPIED).count()
        occupancy_rate = (occupied / capacity) * 100
        if occupancy_rate >= 90:
            notify_admins_critical_occupancy(User, block, occupancy_rate)

    return {
        "message": "Reservation validated, invoice generated and sent"
    }


@api.post("/reservations/{reservation_id}/reject", auth=BearerAuth())
def reject_reservation(request, reservation_id: int):
    require_roles(request, ROLE_ADMIN, ROLE_SECRETARIAT)

    reservation = get_object_or_404(Reservation, id=reservation_id)
    reservation.status = Reservation.Status.CANCELLED
    reservation.validated_by = request.auth
    reservation.validated_at = datetime.now(timezone.utc)
    reservation.save()

    # La tombe redevient disponible (vert)
    grave = reservation.grave
    grave.status = Grave.Status.AVAILABLE
    grave.save(update_fields=["status"])

    log_action(request, "UPDATE", "Reservation", reservation.id, "Rejetée")

    return {
        "message": "Reservation rejected"
    }


@api.delete("/reservations/{reservation_id}", auth=BearerAuth())
def delete_reservation(request, reservation_id: int):
    require_roles(request, ROLE_ADMIN, ROLE_SECRETARIAT)

    reservation = get_object_or_404(Reservation, id=reservation_id)
    reservation.delete()

    log_action(request, "DELETE", "Reservation", reservation_id)

    return {
        "message": "Reservation deleted successfully"
    }


# ==========================================================
# CRUD - CONCESSIONS
# Lecture : ADMIN/SECRETARIAT (tout) + CLIENT (les siennes)
# Écriture : ADMIN, SECRETARIAT | Suppression : ADMIN
# ==========================================================

@api.get("/concessions", response=list[ConcessionOut], auth=BearerAuth())
def list_concessions(request):
    require_roles(request, ROLE_ADMIN, ROLE_SECRETARIAT, ROLE_CLIENT)

    queryset = scope_to_owner_if_client(request, Concession.objects.all(), "owner")

    return [
        {
            "id": concession.id,
            "grave_id": concession.grave.id,
            "owner_id": concession.owner.id,
            "concession_number": concession.concession_number,
            "duration_type": concession.duration_type,
            "start_date": str(concession.start_date),
            "end_date": str(concession.end_date) if concession.end_date else None,
            "status": concession.status,
            "notes": concession.notes,
        }
        for concession in queryset
    ]


@api.get("/concessions/{concession_id}", response=ConcessionOut, auth=BearerAuth())
def get_concession(request, concession_id: int):
    require_roles(request, ROLE_ADMIN, ROLE_SECRETARIAT, ROLE_CLIENT)

    concession = get_object_or_404(Concession, id=concession_id)

    if request.auth.role == ROLE_CLIENT and concession.owner_id != request.auth.id:
        raise HttpError(403, "Accès refusé : cette concession ne t'appartient pas.")

    return {
        "id": concession.id,
        "grave_id": concession.grave.id,
        "owner_id": concession.owner.id,
        "concession_number": concession.concession_number,
        "duration_type": concession.duration_type,
        "start_date": str(concession.start_date),
        "end_date": str(concession.end_date) if concession.end_date else None,
        "status": concession.status,
        "notes": concession.notes,
    }


@api.post("/concessions", auth=BearerAuth())
def create_concession(request, payload: ConcessionIn):
    require_roles(request, ROLE_ADMIN, ROLE_SECRETARIAT)

    try:
        grave = get_object_or_404(Grave, id=payload.grave_id)
        owner = get_object_or_404(User, id=payload.owner_id)

        concession = Concession.objects.create(
            grave=grave,
            owner=owner,
            concession_number=payload.concession_number,
            duration_type=payload.duration_type,
            start_date=payload.start_date,
            end_date=payload.end_date,
            status=payload.status,
            notes=payload.notes,
        )
        log_action(request, "CREATE", "Concession", concession.id)

        return {
            "id": concession.id,
            "message": "Concession created successfully"
        }

    except Exception as e:
        raise HttpError(400, str(e))


@api.put("/concessions/{concession_id}", auth=BearerAuth())
def update_concession(request, concession_id: int, payload: ConcessionIn):
    require_roles(request, ROLE_ADMIN, ROLE_SECRETARIAT)

    concession = get_object_or_404(Concession, id=concession_id)

    concession.grave = get_object_or_404(Grave, id=payload.grave_id)
    concession.owner = get_object_or_404(User, id=payload.owner_id)
    concession.concession_number = payload.concession_number
    concession.duration_type = payload.duration_type
    concession.start_date = payload.start_date
    concession.end_date = payload.end_date
    concession.status = payload.status
    concession.notes = payload.notes
    concession.save()

    log_action(request, "UPDATE", "Concession", concession.id)

    return {
        "message": "Concession updated successfully"
    }


@api.delete("/concessions/{concession_id}", auth=BearerAuth())
def delete_concession(request, concession_id: int):
    require_roles(request, ROLE_ADMIN)

    concession = get_object_or_404(Concession, id=concession_id)
    concession.delete()

    log_action(request, "DELETE", "Concession", concession_id)

    return {
        "message": "Concession deleted successfully"
    }


# ==========================================================
# CRUD - PAYMENTS
# Lecture : ADMIN/SECRETARIAT (tout) + CLIENT (les siens)
# Création : ADMIN, SECRETARIAT, CLIENT (paiement de sa propre concession)
# Modification : ADMIN, SECRETARIAT | Suppression : ADMIN
# ==========================================================

@api.get("/payments", response=list[PaymentOut], auth=BearerAuth())
def list_payments(request):
    require_roles(request, ROLE_ADMIN, ROLE_SECRETARIAT, ROLE_CLIENT)

    queryset = Payment.objects.all()
    if request.auth.role == ROLE_CLIENT:
        queryset = queryset.filter(concession__owner=request.auth)

    return [
        {
            "id": payment.id,
            "concession_id": payment.concession.id,
            "amount": float(payment.amount),
            "amount_due": float(payment.amount_due) if payment.amount_due is not None else None,
            "payment_date": str(payment.payment_date),
            "payment_method": payment.payment_method,
            "reference": payment.reference,
            "status": payment.status,
            "notes": payment.notes,
        }
        for payment in queryset
    ]


@api.get("/payments/{payment_id}", response=PaymentOut, auth=BearerAuth())
def get_payment(request, payment_id: int):
    require_roles(request, ROLE_ADMIN, ROLE_SECRETARIAT, ROLE_CLIENT)

    payment = get_object_or_404(Payment, id=payment_id)

    if request.auth.role == ROLE_CLIENT and payment.concession.owner_id != request.auth.id:
        raise HttpError(403, "Accès refusé : ce paiement ne t'appartient pas.")

    return {
        "id": payment.id,
        "concession_id": payment.concession.id,
        "amount": float(payment.amount),
        "amount_due": float(payment.amount_due) if payment.amount_due is not None else None,
        "payment_date": str(payment.payment_date),
        "payment_method": payment.payment_method,
        "reference": payment.reference,
        "status": payment.status,
        "notes": payment.notes,
    }


@api.post("/payments", auth=BearerAuth())
def create_payment(request, payload: PaymentIn):
    require_roles(request, ROLE_ADMIN, ROLE_SECRETARIAT, ROLE_CLIENT)

    try:
        concession = get_object_or_404(Concession, id=payload.concession_id)

        # Un client ne peut payer que pour sa propre concession.
        if request.auth.role == ROLE_CLIENT and concession.owner_id != request.auth.id:
            raise HttpError(403, "Un client ne peut payer que pour sa propre concession.")

        payment = Payment.objects.create(
            concession=concession,
            amount=payload.amount,
            amount_due=payload.amount_due,
            payment_date=payload.payment_date,
            payment_method=payload.payment_method,
            reference=payload.reference,
            status=payload.status,
            notes=payload.notes,
        )
        log_action(request, "CREATE", "Payment", payment.id)

        return {
            "id": payment.id,
            "message": "Payment created successfully"
        }

    except HttpError:
        raise
    except Exception as e:
        raise HttpError(400, str(e))


@api.put("/payments/{payment_id}", auth=BearerAuth())
def update_payment(request, payment_id: int, payload: PaymentIn):
    require_roles(request, ROLE_ADMIN, ROLE_SECRETARIAT)

    payment = get_object_or_404(Payment, id=payment_id)

    payment.concession = get_object_or_404(Concession, id=payload.concession_id)
    payment.amount = payload.amount
    payment.amount_due = payload.amount_due
    payment.payment_date = payload.payment_date
    payment.payment_method = payload.payment_method
    payment.reference = payload.reference
    payment.status = payload.status
    payment.notes = payload.notes
    payment.save()

    log_action(request, "UPDATE", "Payment", payment.id)

    return {
        "message": "Payment updated successfully"
    }


@api.get("/concessions/{concession_id}/balance", auth=BearerAuth())
def get_concession_balance(request, concession_id: int):
    """Solde restant dû sur une concession (cahier des charges 2.6 :
    suivi des paiements partiels)."""
    require_roles(request, ROLE_ADMIN, ROLE_SECRETARIAT, ROLE_CLIENT)

    concession = get_object_or_404(Concession, id=concession_id)

    if request.auth.role == ROLE_CLIENT and concession.owner_id != request.auth.id:
        raise HttpError(403, "Accès refusé : cette concession ne t'appartient pas.")

    payments = concession.payments.filter(status=Payment.Status.COMPLETED)
    total_paid = sum((p.amount for p in payments), start=0)
    latest_due = payments.exclude(amount_due=None).order_by("-payment_date").first()
    amount_due = latest_due.amount_due if latest_due else None

    return {
        "concession_id": concession.id,
        "total_paid": float(total_paid),
        "amount_due": float(amount_due) if amount_due is not None else None,
        "balance_remaining": float(amount_due - total_paid) if amount_due is not None else None,
    }


@api.delete("/payments/{payment_id}", auth=BearerAuth())
def delete_payment(request, payment_id: int):
    require_roles(request, ROLE_ADMIN)

    payment = get_object_or_404(Payment, id=payment_id)
    payment.delete()

    log_action(request, "DELETE", "Payment", payment_id)

    return {
        "message": "Payment deleted successfully"
    }


# ==========================================================
# CRUD - EXHUMATIONS
# Opération sensible : réservée à ADMIN et AGENT_TERRAIN (lecture ET écriture)
# ==========================================================

@api.get("/exhumations", response=list[ExhumationOut], auth=BearerAuth())
def list_exhumations(request):
    require_roles(request, ROLE_ADMIN, ROLE_AGENT_TERRAIN)

    return [
        {
            "id": exhumation.id,
            "grave_id": exhumation.grave.id,
            "responsible_agent_id": exhumation.responsible_agent.id if exhumation.responsible_agent else None,
            "exhumation_date": str(exhumation.exhumation_date),
            "reason": exhumation.reason,
            "observations": exhumation.observations,
            "status": exhumation.status,
            "validated_by_id": exhumation.validated_by_id,
            "validated_at": str(exhumation.validated_at) if exhumation.validated_at else None,
        }
        for exhumation in Exhumation.objects.all()
    ]


@api.get("/exhumations/{exhumation_id}", response=ExhumationOut, auth=BearerAuth())
def get_exhumation(request, exhumation_id: int):
    require_roles(request, ROLE_ADMIN, ROLE_AGENT_TERRAIN)

    exhumation = get_object_or_404(Exhumation, id=exhumation_id)

    return {
        "id": exhumation.id,
        "grave_id": exhumation.grave.id,
        "responsible_agent_id": exhumation.responsible_agent.id if exhumation.responsible_agent else None,
        "exhumation_date": str(exhumation.exhumation_date),
        "reason": exhumation.reason,
        "observations": exhumation.observations,
        "status": exhumation.status,
        "validated_by_id": exhumation.validated_by_id,
        "validated_at": str(exhumation.validated_at) if exhumation.validated_at else None,
    }


@api.post("/exhumations", auth=BearerAuth())
def create_exhumation(request, payload: ExhumationIn):
    require_roles(request, ROLE_ADMIN, ROLE_AGENT_TERRAIN)

    grave = get_object_or_404(Grave, id=payload.grave_id)

    agent = None
    if payload.responsible_agent_id:
        agent = get_object_or_404(User, id=payload.responsible_agent_id)

    exhumation = Exhumation.objects.create(
        grave=grave,
        responsible_agent=agent,
        exhumation_date=payload.exhumation_date,
        reason=payload.reason,
        observations=payload.observations,
    )
    log_action(request, "CREATE", "Exhumation", exhumation.id)

    return {
        "id": exhumation.id,
        "message": "Exhumation created successfully"
    }


@api.put("/exhumations/{exhumation_id}", auth=BearerAuth())
def update_exhumation(request, exhumation_id: int, payload: ExhumationIn):
    require_roles(request, ROLE_ADMIN, ROLE_AGENT_TERRAIN)

    exhumation = get_object_or_404(Exhumation, id=exhumation_id)

    exhumation.grave = get_object_or_404(Grave, id=payload.grave_id)

    if payload.responsible_agent_id:
        exhumation.responsible_agent = get_object_or_404(User, id=payload.responsible_agent_id)
    else:
        exhumation.responsible_agent = None

    exhumation.exhumation_date = payload.exhumation_date
    exhumation.reason = payload.reason
    exhumation.observations = payload.observations
    exhumation.save()

    log_action(request, "UPDATE", "Exhumation", exhumation.id)

    return {
        "message": "Exhumation updated successfully"
    }


@api.post("/exhumations/{exhumation_id}/validate", auth=BearerAuth())
def validate_exhumation(request, exhumation_id: int):
    """Validation administrative + génération du PV (cahier des charges 2.5)."""
    require_roles(request, ROLE_ADMIN, ROLE_AGENT_TERRAIN)

    exhumation = get_object_or_404(Exhumation, id=exhumation_id)

    if exhumation.status == Exhumation.Status.VALIDATED:
        raise HttpError(400, "Cette exhumation est déjà validée.")

    exhumation.status = Exhumation.Status.VALIDATED
    exhumation.validated_by = request.auth
    exhumation.validated_at = datetime.now(timezone.utc)
    exhumation.save()

    log_action(request, "UPDATE", "Exhumation", exhumation.id, "Validée, PV généré")

    return {
        "message": "Exhumation validated, PV available at /exhumations/{id}/pv"
    }


@api.post("/exhumations/{exhumation_id}/reject", auth=BearerAuth())
def reject_exhumation(request, exhumation_id: int):
    require_roles(request, ROLE_ADMIN, ROLE_AGENT_TERRAIN)

    exhumation = get_object_or_404(Exhumation, id=exhumation_id)
    exhumation.status = Exhumation.Status.REJECTED
    exhumation.validated_by = request.auth
    exhumation.validated_at = datetime.now(timezone.utc)
    exhumation.save()

    log_action(request, "UPDATE", "Exhumation", exhumation.id, "Rejetée")

    return {
        "message": "Exhumation rejected"
    }


@api.get("/exhumations/{exhumation_id}/pv", auth=BearerAuth())
def download_exhumation_pv(request, exhumation_id: int):
    """Téléchargement du procès-verbal d'exhumation (document légal,
    cahier des charges 2.5)."""
    require_roles(request, ROLE_ADMIN, ROLE_AGENT_TERRAIN)

    exhumation = get_object_or_404(Exhumation, id=exhumation_id)

    if exhumation.status != Exhumation.Status.VALIDATED:
        raise HttpError(400, "Le PV n'est disponible qu'après validation de l'exhumation.")

    pdf_bytes = generate_exhumation_pv_pdf(exhumation)

    return HttpResponse(
        pdf_bytes,
        content_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="pv_exhumation_{exhumation.id}.pdf"'},
    )


@api.delete("/exhumations/{exhumation_id}", auth=BearerAuth())
def delete_exhumation(request, exhumation_id: int):
    require_roles(request, ROLE_ADMIN)

    exhumation = get_object_or_404(Exhumation, id=exhumation_id)
    exhumation.delete()

    log_action(request, "DELETE", "Exhumation", exhumation_id)

    return {
        "message": "Exhumation deleted successfully"
    }


# ==========================================================
# ==========================================================
# REPORTING ET STATISTIQUES (cahier des charges §7)
# Réservé à ADMIN et SECRETARIAT (accès aux statistiques financières)
# ==========================================================

@api.get("/reports/occupancy", auth=BearerAuth())
def report_occupancy(request):
    """Taux d'occupation par bloc et jauge de saturation globale."""
    require_roles(request, ROLE_ADMIN, ROLE_SECRETARIAT)

    blocks_data = []
    total_capacity = 0
    total_occupied = 0

    for block in Block.objects.select_related("cemetery").all():
        capacity = block.estimated_capacity()
        occupied = block.graves.filter(status=Grave.Status.OCCUPIED).count()
        rate = (occupied / capacity * 100) if capacity > 0 else 0

        total_capacity += capacity
        total_occupied += occupied

        blocks_data.append({
            "block_id": block.id,
            "block_code": block.code,
            "cemetery": block.cemetery.name,
            "estimated_capacity": capacity,
            "occupied": occupied,
            "occupancy_rate": round(rate, 1),
        })

    global_rate = (total_occupied / total_capacity * 100) if total_capacity > 0 else 0

    return {
        "blocks": blocks_data,
        "global_occupancy_rate": round(global_rate, 1),
    }


@api.get("/reports/revenue", auth=BearerAuth())
def report_revenue(request):
    """Revenus totaux et par méthode de paiement (paiements complétés uniquement)."""
    require_roles(request, ROLE_ADMIN, ROLE_SECRETARIAT)

    completed = Payment.objects.filter(status=Payment.Status.COMPLETED)

    total = completed.aggregate(total=Sum("amount"))["total"] or 0

    by_method = []
    for method_value, method_label in Payment.PaymentMethod.choices:
        subtotal = completed.filter(payment_method=method_value).aggregate(
            total=Sum("amount")
        )["total"] or 0
        by_method.append({
            "method": method_value,
            "label": method_label,
            "total": float(subtotal),
        })

    return {
        "total_revenue": float(total),
        "by_method": by_method,
    }


@api.post("/alerts/check", auth=BearerAuth())
def check_alerts(request):
    """Déclenche manuellement la vérification des échéances de concession
    et des retards de paiement (au lieu d'attendre le cron quotidien) —
    réservé à l'administrateur."""
    require_roles(request, ROLE_ADMIN)

    result = run_alerts()

    return {
        "expiring_concessions_count": len(result["expiring_concessions"]),
        "overdue_payments_count": len(result["overdue_payments"]),
        "expiring_concessions": [
            {"concession_number": c.concession_number, "end_date": c.end_date.isoformat()}
            for c in result["expiring_concessions"]
        ],
    }


@api.get("/reports/export/graves", auth=BearerAuth())
def export_graves_csv(request):
    """Export CSV du registre des tombes (cahier des charges §7)."""
    require_roles(request, ROLE_ADMIN, ROLE_SECRETARIAT)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "id", "cimetiere", "bloc", "numero_tombe", "statut",
        "longueur", "largeur", "capacite", "latitude", "longitude",
    ])

    for grave in Grave.objects.select_related("block__cemetery").all():
        writer.writerow([
            grave.id,
            grave.block.cemetery.name,
            grave.block.code,
            grave.grave_number,
            grave.status,
            grave.length,
            grave.width,
            grave.capacity,
            grave.latitude,
            grave.longitude,
        ])

    log_action(request, "EXPORT", "Grave", None, "Export CSV du registre des tombes")

    response = HttpResponse(buffer.getvalue(), content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="registre_tombes.csv"'
    return response


@api.get("/reports/export/payments", auth=BearerAuth())
def export_payments_csv(request):
    """Export CSV du registre des paiements (cahier des charges §7)."""
    require_roles(request, ROLE_ADMIN, ROLE_SECRETARIAT)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "id", "concession", "montant", "date", "methode", "reference", "statut",
    ])

    for payment in Payment.objects.select_related("concession").all():
        writer.writerow([
            payment.id,
            payment.concession.concession_number,
            payment.amount,
            payment.payment_date,
            payment.payment_method,
            payment.reference,
            payment.status,
        ])

    log_action(request, "EXPORT", "Payment", None, "Export CSV du registre des paiements")

    response = HttpResponse(buffer.getvalue(), content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="registre_paiements.csv"'
    return response


# ==========================================================
# AUTHENTIFICATION JWT + MFA
# ==========================================================

@api.post("/login", response=MFARequiredSchema)
def login(request, payload: LoginSchema):
    """Étape 1 : email + mot de passe.
    Le MFA par email est obligatoire pour tous les utilisateurs (cahier des
    charges 2.1) : un mot de passe correct ne renvoie jamais directement les
    tokens, il déclenche l'envoi du code et renvoie un temp_token à soumettre
    à /login/verify-otp.
    """
    user = authenticate(email=payload.email, password=payload.password)

    if user is None:
        raise HttpError(401, "Email ou mot de passe incorrect.")

    generate_and_send_mfa_code(user)
    temp_token = create_mfa_pending_token(user)

    return {
        "mfa_required": True,
        "temp_token": temp_token,
    }


@api.post("/login/verify-otp", response=TokenSchema)
def verify_otp(request, payload: VerifyMFASchema):
    """Étape 2 : vérifie le code reçu par email et délivre les tokens."""
    try:
        decoded = jwt.decode(payload.temp_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HttpError(401, "Session MFA expirée, reconnecte-toi.")
    except jwt.InvalidTokenError:
        raise HttpError(401, "Token MFA invalide.")

    if decoded.get("type") != "mfa_pending":
        raise HttpError(401, "Token invalide.")

    user = get_object_or_404(User, id=decoded["user_id"])

    if not verify_mfa_code(user, payload.otp_code):
        raise HttpError(401, "Code incorrect ou expiré.")

    access_token = create_access_token(user)
    refresh_token = create_refresh_token(user)
    log_action(request, "LOGIN", "User", user.id, "Connexion avec MFA email", user=user)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
    }


@api.post("/refresh", response=AccessTokenSchema)
def refresh_token_view(request, payload: RefreshSchema):
    try:
        decoded = jwt.decode(payload.refresh_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

        if decoded.get("type") != "refresh":
            raise HttpError(401, "Token invalide.")

        user = get_object_or_404(User, id=decoded["user_id"])
        new_access_token = create_access_token(user)

        return {
            "access_token": new_access_token,
            "token_type": "Bearer",
        }

    except jwt.ExpiredSignatureError:
        raise HttpError(401, "Refresh token expiré.")
    except jwt.InvalidTokenError:
        raise HttpError(401, "Refresh token invalide.")


@api.get("/me", response=UserMeOut, auth=BearerAuth())
def me(request):
    user = request.auth
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "role": user.role,
        "phone": user.phone,
    }


@api.get("/users", response=list[UserMeOut], auth=BearerAuth())
def list_users(request, role: str = None, include_inactive: bool = False):
    """Liste des utilisateurs, filtrable par rôle (ex: ?role=CLIENT). Réservé
    au personnel : sert à choisir un client dans les formulaires de
    réservation/concession/paiement. include_inactive (ADMIN uniquement)
    permet de voir aussi les comptes désactivés, pour pouvoir les réactiver."""
    require_roles(request, ROLE_ADMIN, ROLE_SECRETARIAT, ROLE_AGENT_TERRAIN)

    queryset = User.objects.all()
    if not (include_inactive and request.auth.role == ROLE_ADMIN):
        queryset = queryset.filter(is_active=True)
    if role:
        queryset = queryset.filter(role=role)

    return [
        {
            "id": u.id,
            "email": u.email,
            "username": u.username,
            "role": u.role,
            "phone": u.phone,
            "is_active": u.is_active,
        }
        for u in queryset
    ]


@api.post("/register")
def register(request, payload: RegisterSchema):
    """Inscription publique (sans authentification). Cahier des charges :
    permettre aux citoyens de créer un compte pour réserver/consulter.
    Toujours créé avec le rôle CLIENT — les rôles internes (admin,
    secrétariat, agent de terrain) restent réservés à la gestion par un
    administrateur via /users/{id}/role."""
    if User.objects.filter(email=payload.email).exists():
        raise HttpError(400, "Un compte existe déjà avec cet email.")
    if User.objects.filter(username=payload.username).exists():
        raise HttpError(400, "Ce nom d'utilisateur est déjà pris.")

    user = User.objects.create_user(
        username=payload.username,
        email=payload.email,
        password=payload.password,
        phone=payload.phone,
        role=ROLE_CLIENT,
    )
    log_action(request, "CREATE", "User", user.id, "Auto-inscription", user=user)

    return {
        "id": user.id,
        "message": "Compte créé avec succès. Vous pouvez maintenant vous connecter."
    }


@api.put("/users/{user_id}/role", auth=BearerAuth())
def update_user_role(request, user_id: int, payload: UpdateRoleSchema):
    """Changement de rôle d'un utilisateur — réservé à l'administrateur
    (gestion des droits, cahier des charges 2.1)."""
    require_roles(request, ROLE_ADMIN)

    if payload.role not in (ROLE_ADMIN, ROLE_SECRETARIAT, ROLE_AGENT_TERRAIN, ROLE_CLIENT):
        raise HttpError(400, "Rôle invalide.")

    user = get_object_or_404(User, id=user_id)
    old_role = user.role
    user.role = payload.role
    user.save(update_fields=["role"])

    log_action(request, "UPDATE", "User", user.id, f"Rôle changé de {old_role} à {payload.role}")

    return {
        "message": "Rôle mis à jour avec succès."
    }


@api.put("/users/{user_id}/active", auth=BearerAuth())
def toggle_user_active(request, user_id: int, payload: ToggleActiveSchema):
    """Active/désactive un compte utilisateur — réservé à l'administrateur."""
    require_roles(request, ROLE_ADMIN)

    user = get_object_or_404(User, id=user_id)
    user.is_active = payload.is_active
    user.save(update_fields=["is_active"])

    log_action(request, "UPDATE", "User", user.id, f"Compte {'activé' if payload.is_active else 'désactivé'}")

    return {
        "message": "Statut du compte mis à jour."
    }
