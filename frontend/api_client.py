"""Client HTTP vers l'API Django Ninja du backend.

Toutes les fonctions renvoient soit les données JSON décodées, soit lèvent
une ApiError avec le message renvoyé par le backend (schéma HttpError de
django-ninja : {"detail": "..."}).
"""
import os

import requests

# En local, pointe vers le serveur Django lancé sur la même machine.
# En production (hébergement), définir la variable d'environnement
# API_BASE_URL avec l'URL réelle du backend déployé, ex :
#   API_BASE_URL=https://mon-backend.onrender.com/api
BASE_URL = os.environ.get("API_BASE_URL", "http://127.0.0.1:8000/api")


class ApiError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"[{status_code}] {detail}")


def _handle(response: requests.Response):
    if response.status_code >= 400:
        try:
            detail = response.json().get("detail", response.text)
        except Exception:
            detail = response.text
        raise ApiError(response.status_code, detail)
    if response.status_code == 200 and response.headers.get("content-type", "").startswith("text/csv"):
        return response.content
    if not response.content:
        return None
    return response.json()


def _headers(token: str | None = None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _get(path, token=None, params=None):
    return _handle(requests.get(f"{BASE_URL}{path}", headers=_headers(token), params=params))


def _post(path, token=None, json=None):
    return _handle(requests.post(f"{BASE_URL}{path}", headers=_headers(token), json=json))


def _put(path, token=None, json=None):
    return _handle(requests.put(f"{BASE_URL}{path}", headers=_headers(token), json=json))


def _delete(path, token=None):
    return _handle(requests.delete(f"{BASE_URL}{path}", headers=_headers(token)))


# ---------- Authentification / MFA ----------

def login(email: str, password: str):
    return _post("/login", json={"email": email, "password": password})


def verify_otp(temp_token: str, otp_code: str):
    return _post("/login/verify-otp", json={"temp_token": temp_token, "otp_code": otp_code})


def me(token: str):
    return _get("/me", token=token)


def list_users(token, role: str | None = None, include_inactive: bool = False):
    params = {}
    if role:
        params["role"] = role
    if include_inactive:
        params["include_inactive"] = "true"
    return _get("/users", token=token, params=params or None)


def register(username, email, password, phone=""):
    return _post("/register", json={
        "username": username, "email": email, "password": password, "phone": phone,
    })


def update_user_role(token, user_id, role):
    return _put(f"/users/{user_id}/role", token=token, json={"role": role})


def toggle_user_active(token, user_id, is_active):
    return _put(f"/users/{user_id}/active", token=token, json={"is_active": is_active})


def check_alerts(token):
    return _post("/alerts/check", token=token)


# ---------- Cimetières / blocs / tombes ----------

def list_cemeteries(token):
    return _get("/cemeteries", token=token)


def get_cemetery(token, cemetery_id):
    return _get(f"/cemeteries/{cemetery_id}", token=token)


def create_cemetery(token, payload):
    return _post("/cemeteries", token=token, json=payload)


def update_cemetery(token, cemetery_id, payload):
    return _put(f"/cemeteries/{cemetery_id}", token=token, json=payload)


def delete_cemetery(token, cemetery_id):
    return _delete(f"/cemeteries/{cemetery_id}", token=token)


def list_blocks(token):
    return _get("/blocks", token=token)


def get_block(token, block_id):
    return _get(f"/blocks/{block_id}", token=token)


def create_block(token, payload):
    return _post("/blocks", token=token, json=payload)


def update_block(token, block_id, payload):
    return _put(f"/blocks/{block_id}", token=token, json=payload)


def delete_block(token, block_id):
    return _delete(f"/blocks/{block_id}", token=token)


def list_graves(token):
    return _get("/graves", token=token)


def get_grave(token, grave_id):
    return _get(f"/graves/{grave_id}", token=token)


def create_grave(token, payload):
    return _post("/graves", token=token, json=payload)


def update_grave(token, grave_id, payload):
    return _put(f"/graves/{grave_id}", token=token, json=payload)


def delete_grave(token, grave_id):
    return _delete(f"/graves/{grave_id}", token=token)


# ---------- Réservations ----------

def list_reservations(token):
    return _get("/reservations", token=token)


def get_reservation(token, reservation_id):
    return _get(f"/reservations/{reservation_id}", token=token)


def create_reservation(token, payload):
    return _post("/reservations", token=token, json=payload)


def update_reservation(token, reservation_id, payload):
    return _put(f"/reservations/{reservation_id}", token=token, json=payload)


def delete_reservation(token, reservation_id):
    return _delete(f"/reservations/{reservation_id}", token=token)


def validate_reservation(token, reservation_id):
    return _post(f"/reservations/{reservation_id}/validate", token=token)


def reject_reservation(token, reservation_id):
    return _post(f"/reservations/{reservation_id}/reject", token=token)


# ---------- Concessions / paiements ----------

def list_concessions(token):
    return _get("/concessions", token=token)


def get_concession(token, concession_id):
    return _get(f"/concessions/{concession_id}", token=token)


def create_concession(token, payload):
    return _post("/concessions", token=token, json=payload)


def update_concession(token, concession_id, payload):
    return _put(f"/concessions/{concession_id}", token=token, json=payload)


def delete_concession(token, concession_id):
    return _delete(f"/concessions/{concession_id}", token=token)


def get_concession_balance(token, concession_id):
    return _get(f"/concessions/{concession_id}/balance", token=token)


def list_payments(token):
    return _get("/payments", token=token)


def get_payment(token, payment_id):
    return _get(f"/payments/{payment_id}", token=token)


def create_payment(token, payload):
    return _post("/payments", token=token, json=payload)


def update_payment(token, payment_id, payload):
    return _put(f"/payments/{payment_id}", token=token, json=payload)


def delete_payment(token, payment_id):
    return _delete(f"/payments/{payment_id}", token=token)


# ---------- Exhumations ----------

def list_exhumations(token):
    return _get("/exhumations", token=token)


def get_exhumation(token, exhumation_id):
    return _get(f"/exhumations/{exhumation_id}", token=token)


def create_exhumation(token, payload):
    return _post("/exhumations", token=token, json=payload)


def update_exhumation(token, exhumation_id, payload):
    return _put(f"/exhumations/{exhumation_id}", token=token, json=payload)


def delete_exhumation(token, exhumation_id):
    return _delete(f"/exhumations/{exhumation_id}", token=token)


def validate_exhumation(token, exhumation_id):
    return _post(f"/exhumations/{exhumation_id}/validate", token=token)


def reject_exhumation(token, exhumation_id):
    return _post(f"/exhumations/{exhumation_id}/reject", token=token)


def download_exhumation_pv(token, exhumation_id):
    response = requests.get(
        f"{BASE_URL}/exhumations/{exhumation_id}/pv",
        headers=_headers(token),
    )
    if response.status_code >= 400:
        try:
            detail = response.json().get("detail", response.text)
        except Exception:
            detail = response.text
        raise ApiError(response.status_code, detail)
    return response.content


# ---------- Reporting ----------

def report_occupancy(token):
    return _get("/reports/occupancy", token=token)


def report_revenue(token):
    return _get("/reports/revenue", token=token)


def check_alerts(token):
    return _post("/alerts/check", token=token)


def check_alerts(token):
    return _post("/alerts/check", token=token)
