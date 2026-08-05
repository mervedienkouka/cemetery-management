import flet as ft

import api_client as api
from status_colors import status_color, status_label

GRAVE_STATUS_OPTIONS = [
    ("AVAILABLE", "Disponible"),
    ("RESERVED", "Réservé"),
    ("OCCUPIED", "Occupé"),
    ("UNUSABLE", "Inexploitable"),
]


def build_infrastructure_view(page: ft.Page, state):
    error_text = ft.Text("", color=ft.Colors.RED)

    # ---------- Onglet Cimetières ----------

    cem_name = ft.TextField(label="Nom", width=260)
    cem_address = ft.TextField(label="Adresse", width=260)
    cem_city = ft.TextField(label="Ville", width=180)
    cem_country = ft.TextField(label="Pays", width=180)
    cem_area = ft.TextField(label="Superficie totale (m²)", width=200)
    cem_list = ft.Column(spacing=6)

    def refresh_cemeteries():
        cem_list.controls.clear()
        try:
            cemeteries = api.list_cemeteries(state.access_token)
        except api.ApiError as err:
            cem_list.controls.append(ft.Text(f"Erreur : {err.detail}", color=ft.Colors.RED))
            page.update()
            return

        if not cemeteries:
            cem_list.controls.append(ft.Text("Aucun cimetière.", color=ft.Colors.ON_SURFACE_VARIANT))
        for c in cemeteries:
            row = [ft.Text(f"#{c['id']} — {c['name']} ({c['city']}, {c['country']}) — {c['total_area']} m²", expand=True)]

            if state.role == "ADMIN":
                def delete_cemetery(e, cid=c["id"]):
                    try:
                        api.delete_cemetery(state.access_token, cid)
                    except api.ApiError as err:
                        error_text.value = f"Erreur : {err.detail}"
                        page.update()
                        return
                    refresh_cemeteries()
                    refresh_cemetery_dropdown()

                row.append(ft.IconButton(icon=ft.Icons.DELETE_OUTLINE, icon_color=ft.Colors.RED, on_click=delete_cemetery))

            cem_list.controls.append(
                ft.Container(
                    content=ft.Row(row),
                    padding=8,
                    bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                    border_radius=6,
                )
            )
        page.update()

    def create_cemetery(e):
        error_text.value = ""
        if not cem_name.value or not cem_area.value:
            error_text.value = "Le nom et la superficie sont obligatoires."
            page.update()
            return
        try:
            area_value = float(cem_area.value)
        except ValueError:
            error_text.value = "La superficie doit être un nombre."
            page.update()
            return

        payload = {
            "name": cem_name.value,
            "address": cem_address.value or "",
            "city": cem_city.value or "",
            "country": cem_country.value or "",
            "total_area": area_value,
        }
        try:
            api.create_cemetery(state.access_token, payload)
        except api.ApiError as err:
            error_text.value = f"Erreur : {err.detail}"
            page.update()
            return

        cem_name.value = cem_address.value = cem_city.value = cem_country.value = cem_area.value = ""
        refresh_cemeteries()
        refresh_cemetery_dropdown()

    cemeteries_tab = ft.Column(
        [
            ft.Text("Nouveau cimetière", size=16, weight=ft.FontWeight.W_600),
            ft.Row([cem_name, cem_city, cem_country], wrap=True),
            ft.Row([cem_address, cem_area], wrap=True),
            ft.ElevatedButton("Créer le cimetière", icon=ft.Icons.ADD, on_click=create_cemetery),
            ft.Divider(),
            ft.Text("Cimetières existants", size=16, weight=ft.FontWeight.W_600),
            cem_list,
        ],
        spacing=10,
        scroll=ft.ScrollMode.AUTO,
    )

    # ---------- Onglet Blocs ----------

    block_cemetery_dd = ft.Dropdown(label="Cimetière", width=260, options=[])
    block_name = ft.TextField(label="Nom", width=200)
    block_code = ft.TextField(label="Code", width=120)
    block_area = ft.TextField(label="Superficie (m²)", width=180)
    block_non_exploit = ft.TextField(label="Zone non exploitable (m²)", width=200, value="0")
    block_list = ft.Column(spacing=6)

    def refresh_cemetery_dropdown():
        try:
            cemeteries = api.list_cemeteries(state.access_token)
        except api.ApiError:
            cemeteries = []
        block_cemetery_dd.options = [ft.dropdown.Option(key=str(c["id"]), text=c["name"]) for c in cemeteries]
        page.update()

    def refresh_blocks():
        block_list.controls.clear()
        try:
            blocks = api.list_blocks(state.access_token)
        except api.ApiError as err:
            block_list.controls.append(ft.Text(f"Erreur : {err.detail}", color=ft.Colors.RED))
            page.update()
            return

        if not blocks:
            block_list.controls.append(ft.Text("Aucun bloc.", color=ft.Colors.ON_SURFACE_VARIANT))
        for b in blocks:
            row = [
                ft.Text(
                    f"#{b['id']} — {b['name']} ({b['code']}) — {b['area']} m², "
                    f"capacité estimée : {b['estimated_capacity']} places",
                    expand=True,
                )
            ]

            if state.role == "ADMIN":
                def delete_block(e, bid=b["id"]):
                    try:
                        api.delete_block(state.access_token, bid)
                    except api.ApiError as err:
                        error_text.value = f"Erreur : {err.detail}"
                        page.update()
                        return
                    refresh_blocks()
                    refresh_block_dropdown()

                row.append(ft.IconButton(icon=ft.Icons.DELETE_OUTLINE, icon_color=ft.Colors.RED, on_click=delete_block))

            block_list.controls.append(
                ft.Container(
                    content=ft.Row(row),
                    padding=8,
                    bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                    border_radius=6,
                )
            )
        page.update()

    def create_block(e):
        error_text.value = ""
        if not block_cemetery_dd.value or not block_name.value or not block_code.value or not block_area.value:
            error_text.value = "Cimetière, nom, code et superficie sont obligatoires."
            page.update()
            return
        try:
            area_value = float(block_area.value)
            non_exploit_value = float(block_non_exploit.value or 0)
        except ValueError:
            error_text.value = "La superficie doit être un nombre."
            page.update()
            return

        payload = {
            "cemetery_id": int(block_cemetery_dd.value),
            "name": block_name.value,
            "code": block_code.value,
            "area": area_value,
            "non_exploitable_area": non_exploit_value,
        }
        try:
            api.create_block(state.access_token, payload)
        except api.ApiError as err:
            error_text.value = f"Erreur : {err.detail}"
            page.update()
            return

        block_name.value = block_code.value = block_area.value = ""
        block_non_exploit.value = "0"
        refresh_blocks()
        refresh_block_dropdown()

    blocks_tab = ft.Column(
        [
            ft.Text("Nouveau bloc", size=16, weight=ft.FontWeight.W_600),
            ft.Row([block_cemetery_dd, block_name, block_code], wrap=True),
            ft.Row([block_area, block_non_exploit], wrap=True),
            ft.ElevatedButton("Créer le bloc", icon=ft.Icons.ADD, on_click=create_block),
            ft.Divider(),
            ft.Text("Blocs existants", size=16, weight=ft.FontWeight.W_600),
            block_list,
        ],
        spacing=10,
        scroll=ft.ScrollMode.AUTO,
    )

    # ---------- Onglet Tombes ----------

    grave_block_dd = ft.Dropdown(label="Bloc", width=220, options=[])
    grave_number = ft.TextField(label="Numéro de tombe", width=160)
    grave_length = ft.TextField(label="Longueur (m)", width=140, value="2.5")
    grave_width = ft.TextField(label="Largeur (m)", width=140, value="1")
    grave_capacity = ft.TextField(label="Capacité", width=100, value="1")
    grave_status_dd = ft.Dropdown(
        label="Statut", width=160,
        options=[ft.dropdown.Option(key=k, text=v) for k, v in GRAVE_STATUS_OPTIONS],
        value="AVAILABLE",
    )
    grave_lat = ft.TextField(label="Latitude", width=140)
    grave_lon = ft.TextField(label="Longitude", width=140)
    grave_list = ft.Column(spacing=6)

    def refresh_block_dropdown():
        try:
            blocks = api.list_blocks(state.access_token)
        except api.ApiError:
            blocks = []
        grave_block_dd.options = [ft.dropdown.Option(key=str(b["id"]), text=f"{b['name']} ({b['code']})") for b in blocks]
        page.update()

    def refresh_graves():
        grave_list.controls.clear()
        try:
            graves = api.list_graves(state.access_token)
        except api.ApiError as err:
            grave_list.controls.append(ft.Text(f"Erreur : {err.detail}", color=ft.Colors.RED))
            page.update()
            return

        if not graves:
            grave_list.controls.append(ft.Text("Aucune tombe.", color=ft.Colors.ON_SURFACE_VARIANT))
        for g in graves:
            row = [
                ft.Container(width=12, height=12, bgcolor=status_color(g["status"]), border_radius=6),
                ft.Text(
                    f"#{g['id']} — Tombe {g['grave_number']} — {status_label(g['status'])} — capacité {g['capacity']}",
                    expand=True,
                ),
            ]

            if state.role == "ADMIN":
                def delete_grave(e, gid=g["id"]):
                    try:
                        api.delete_grave(state.access_token, gid)
                    except api.ApiError as err:
                        error_text.value = f"Erreur : {err.detail}"
                        page.update()
                        return
                    refresh_graves()

                row.append(ft.IconButton(icon=ft.Icons.DELETE_OUTLINE, icon_color=ft.Colors.RED, on_click=delete_grave))

            grave_list.controls.append(ft.Row(row))
        page.update()

    def create_grave(e):
        error_text.value = ""
        if not grave_block_dd.value or not grave_number.value:
            error_text.value = "Le bloc et le numéro de tombe sont obligatoires."
            page.update()
            return
        try:
            length_value = float(grave_length.value)
            width_value = float(grave_width.value)
            capacity_value = int(grave_capacity.value)
            lat_value = float(grave_lat.value) if grave_lat.value else None
            lon_value = float(grave_lon.value) if grave_lon.value else None
        except ValueError:
            error_text.value = "Vérifie les valeurs numériques (longueur, largeur, capacité, latitude, longitude)."
            page.update()
            return

        payload = {
            "block_id": int(grave_block_dd.value),
            "grave_number": grave_number.value,
            "length": length_value,
            "width": width_value,
            "capacity": capacity_value,
            "status": grave_status_dd.value,
            "latitude": lat_value,
            "longitude": lon_value,
        }
        try:
            api.create_grave(state.access_token, payload)
        except api.ApiError as err:
            error_text.value = f"Erreur : {err.detail}"
            page.update()
            return

        grave_number.value = ""
        grave_lat.value = ""
        grave_lon.value = ""
        refresh_graves()

    graves_tab = ft.Column(
        [
            ft.Text("Nouvelle tombe", size=16, weight=ft.FontWeight.W_600),
            ft.Row([grave_block_dd, grave_number, grave_status_dd], wrap=True),
            ft.Row([grave_length, grave_width, grave_capacity], wrap=True),
            ft.Row([grave_lat, grave_lon], wrap=True),
            ft.Text("Latitude/longitude optionnelles — nécessaires pour apparaître sur la carte.", size=11, color=ft.Colors.ON_SURFACE_VARIANT),
            ft.ElevatedButton("Créer la tombe", icon=ft.Icons.ADD, on_click=create_grave),
            ft.Divider(),
            ft.Text("Tombes existantes", size=16, weight=ft.FontWeight.W_600),
            grave_list,
        ],
        spacing=10,
        scroll=ft.ScrollMode.AUTO,
    )

    tabs = ft.Tabs(
        length=3,
        selected_index=0,
        expand=True,
        content=ft.Column(
            expand=True,
            controls=[
                ft.TabBar(
                    tabs=[
                        ft.Tab(label="Cimetières"),
                        ft.Tab(label="Blocs"),
                        ft.Tab(label="Tombes"),
                    ]
                ),
                ft.TabBarView(
                    expand=True,
                    controls=[
                        ft.Container(content=cemeteries_tab, padding=16),
                        ft.Container(content=blocks_tab, padding=16),
                        ft.Container(content=graves_tab, padding=16),
                    ],
                ),
            ],
        ),
    )

    refresh_cemeteries()
    refresh_cemetery_dropdown()
    refresh_blocks()
    refresh_block_dropdown()
    refresh_graves()

    return ft.Column(
        [
            ft.Text("Gestion du terrain", size=18, weight=ft.FontWeight.W_600),
            error_text,
            tabs,
        ],
        expand=True,
    )
