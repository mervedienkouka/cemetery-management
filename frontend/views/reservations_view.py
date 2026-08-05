import flet as ft

import api_client as api
from status_colors import status_color, status_label

STATUS_LABELS_RESERVATION = {
    "PENDING": "En attente",
    "CONFIRMED": "Validée",
    "CANCELLED": "Annulée",
}


def build_reservations_view(page: ft.Page, state):
    content = ft.Column(spacing=10)
    can_manage = state.role in ("ADMIN", "SECRETARIAT")

    def refresh():
        content.controls.clear()
        content.controls.append(ft.Text("Réservations", size=18, weight=ft.FontWeight.W_500))

        try:
            reservations = api.list_reservations(state.access_token)
        except api.ApiError as err:
            content.controls.append(ft.Text(f"Erreur : {err.detail}", color=ft.Colors.RED))
            page.update()
            return

        if not reservations:
            content.controls.append(ft.Text("Aucune réservation.", color=ft.Colors.ON_SURFACE_VARIANT))
            page.update()
            return

        for r in reservations:
            row_controls = [
                ft.Text(f"#{r['id']}", width=40),
                ft.Text(f"Tombe {r['grave_id']}", width=90),
                ft.Text(r["reservation_date"], width=100),
                ft.Container(
                    content=ft.Text(STATUS_LABELS_RESERVATION.get(r["status"], r["status"]), size=12),
                    bgcolor=ft.Colors.AMBER_100 if r["status"] == "PENDING" else (
                        ft.Colors.GREEN_100 if r["status"] == "CONFIRMED" else ft.Colors.RED_100
                    ),
                    padding=ft.Padding.symmetric(horizontal=8, vertical=4),
                    border_radius=6,
                ),
            ]

            if can_manage and r["status"] == "PENDING":
                row_controls.append(
                    ft.ElevatedButton("Valider", height=32, on_click=lambda e, rid=r["id"]: validate(rid))
                )
                row_controls.append(
                    ft.OutlinedButton("Rejeter", height=32, on_click=lambda e, rid=r["id"]: reject(rid))
                )

            content.controls.append(
                ft.Container(
                    content=ft.Row(row_controls, spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    bgcolor=ft.Colors.WHITE,
                    border_radius=12,
                    padding=ft.Padding.symmetric(horizontal=14, vertical=10),
                    shadow=ft.BoxShadow(blur_radius=8, color=ft.Colors.with_opacity(0.06, ft.Colors.BLACK)),
                )
            )

        page.update()

    def validate(reservation_id):
        try:
            api.validate_reservation(state.access_token, reservation_id)
        except api.ApiError as err:
            content.controls.append(ft.Text(f"Erreur : {err.detail}", color=ft.Colors.RED))
        refresh()

    def reject(reservation_id):
        try:
            api.reject_reservation(state.access_token, reservation_id)
        except api.ApiError as err:
            content.controls.append(ft.Text(f"Erreur : {err.detail}", color=ft.Colors.RED))
        refresh()

    refresh()
    return content
