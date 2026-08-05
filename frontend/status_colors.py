"""Code couleur des statuts de tombe (cahier des charges 2.3) :
Vert = Disponible, Orange = Réservé/en attente, Rouge = Occupé/Validé,
Gris = zone non exploitable."""
import flet as ft

STATUS_COLORS = {
    "AVAILABLE": ft.Colors.GREEN,
    "RESERVED": ft.Colors.ORANGE,
    "OCCUPIED": ft.Colors.RED,
    "UNUSABLE": ft.Colors.GREY,
}

STATUS_LABELS = {
    "AVAILABLE": "Disponible",
    "RESERVED": "Réservé",
    "OCCUPIED": "Occupé",
    "UNUSABLE": "Inexploitable",
}


def status_color(status: str) -> str:
    return STATUS_COLORS.get(status, ft.Colors.GREY)


def status_label(status: str) -> str:
    return STATUS_LABELS.get(status, status)
