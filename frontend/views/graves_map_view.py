import flet as ft
import flet_map as fm

import api_client as api
from status_colors import status_color, status_label

MAP_HEIGHT = 480
MARKER_SIZE = 26
DEFAULT_ZOOM = 15
EMPTY_ZOOM = 12
# Pointe-Noire, République du Congo — centre par défaut tant qu'aucune
# tombe n'est géolocalisée.
POINTE_NOIRE = fm.MapLatitudeLongitude(-4.7761, 11.8636)


def build_graves_map_view(page: ft.Page, state, on_reservation_created):
    content = ft.Column(spacing=12, expand=True)
    status_text = ft.Text("", color=ft.Colors.RED)

    def open_grave_dialog(grave):
        info = ft.Column(
            [
                ft.Text(f"Tombe n° {grave['grave_number']}", size=18, weight=ft.FontWeight.W_500),
                ft.Row([
                    ft.Container(width=14, height=14, bgcolor=status_color(grave["status"]), border_radius=7),
                    ft.Text(status_label(grave["status"])),
                ]),
                ft.Text(f"Capacité : {grave['capacity']} place(s)"),
                ft.Text(f"Dimensions : {grave['length']} x {grave['width']} m"),
            ],
            tight=True,
            spacing=6,
        )

        actions = [ft.TextButton("Fermer", on_click=lambda e: close_dialog())]

        if state.role == "CLIENT" and grave["status"] == "AVAILABLE":
            actions.insert(0, ft.ElevatedButton("Réserver", on_click=lambda e: reserve(grave)))

        dialog = ft.AlertDialog(
            title=ft.Text("Détail de la tombe"),
            content=info,
            actions=actions,
        )

        def close_dialog():
            page.pop_dialog()

        page.show_dialog(dialog)

    def reserve(grave):
        from datetime import date, timedelta

        payload = {
            "grave_id": grave["id"],
            "client_id": state.user["id"],
            "reservation_date": date.today().isoformat(),
            "expiration_date": (date.today() + timedelta(days=30)).isoformat(),
            "status": "PENDING",
        }
        try:
            api.create_reservation(state.access_token, payload)
        except api.ApiError as err:
            status_text.value = f"Erreur : {err.detail}"
            page.pop_dialog()
            page.update()
            return

        page.pop_dialog()
        status_text.value = "Réservation envoyée, en attente de validation."
        page.update()
        on_reservation_created()
        refresh()

    def refresh():
        content.controls.clear()
        status_text.value = ""

        try:
            graves = api.list_graves(state.access_token)
        except api.ApiError as err:
            content.controls.append(ft.Text(f"Erreur : {err.detail}", color=ft.Colors.RED))
            page.update()
            return

        located = [g for g in graves if g.get("latitude") is not None and g.get("longitude") is not None]

        legend = ft.Row(
            [
                ft.Row([ft.Container(width=12, height=12, bgcolor=color, border_radius=6), ft.Text(status_label(key), size=12)])
                for key, color in [("AVAILABLE", ft.Colors.GREEN), ("RESERVED", ft.Colors.ORANGE), ("OCCUPIED", ft.Colors.RED), ("UNUSABLE", ft.Colors.GREY)]
            ],
            spacing=16,
        )

        if not located:
            empty_map = fm.Map(
                expand=True,
                height=MAP_HEIGHT,
                initial_center=POINTE_NOIRE,
                initial_zoom=EMPTY_ZOOM,
                layers=[
                    fm.TileLayer(url_template="https://tile.openstreetmap.org/{z}/{x}/{y}.png"),
                    fm.RichAttribution(
                        attributions=[fm.TextSourceAttribution(text="OpenStreetMap contributors", on_click=lambda e: None)]
                    ),
                ],
            )
            content.controls.append(ft.Text("Aucune tombe géolocalisée pour le moment — carte centrée sur Pointe-Noire.", size=12, color=ft.Colors.ON_SURFACE_VARIANT))
            content.controls.append(ft.Container(content=empty_map, border_radius=8, clip_behavior=ft.ClipBehavior.ANTI_ALIAS, height=MAP_HEIGHT, expand=True))
            content.controls.append(legend)
            page.update()
            return

        # Le cimetière du cahier des charges est à Pointe-Noire : la carte
        # s'ouvre toujours centrée là-dessus, même si des tombes de test ont
        # des coordonnées ailleurs (ça permet aussi de repérer visuellement
        # une tombe mal géolocalisée).
        center = POINTE_NOIRE

        def make_marker(g):
            marker_content = ft.Container(
                width=MARKER_SIZE,
                height=MARKER_SIZE,
                bgcolor=status_color(g["status"]),
                border_radius=MARKER_SIZE / 2,
                border=ft.Border.all(2, ft.Colors.WHITE),
                on_click=lambda e, grave=g: open_grave_dialog(grave),
                tooltip=f"Tombe {g['grave_number']} - {status_label(g['status'])}",
            )
            return fm.Marker(
                content=marker_content,
                coordinates=fm.MapLatitudeLongitude(float(g["latitude"]), float(g["longitude"])),
                width=MARKER_SIZE,
                height=MARKER_SIZE,
            )

        map_widget = fm.Map(
            expand=True,
            height=MAP_HEIGHT,
            initial_center=center,
            initial_zoom=EMPTY_ZOOM,
            layers=[
                fm.TileLayer(
                    url_template="https://tile.openstreetmap.org/{z}/{x}/{y}.png",
                ),
                fm.RichAttribution(
                    attributions=[
                        fm.TextSourceAttribution(
                            text="OpenStreetMap contributors",
                            on_click=lambda e: None,
                        ),
                    ],
                ),
                fm.MarkerLayer(markers=[make_marker(g) for g in located]),
            ],
        )

        content.controls.append(ft.Text("Carte des tombes", size=18, weight=ft.FontWeight.W_500))
        content.controls.append(ft.Text("Emplacements réels (OpenStreetMap) — clique un point pour le détail.", size=12, color=ft.Colors.ON_SURFACE_VARIANT))
        content.controls.append(ft.Container(content=map_widget, border_radius=8, clip_behavior=ft.ClipBehavior.ANTI_ALIAS, height=MAP_HEIGHT, expand=True))
        content.controls.append(legend)
        content.controls.append(status_text)
        page.update()

    refresh()
    return content
