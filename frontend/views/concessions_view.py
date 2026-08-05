import flet as ft

import api_client as api

DURATION_OPTIONS = [
    ("TEMPORARY", "Temporaire"),
    ("PERPETUAL", "Perpétuelle"),
]

STATUS_OPTIONS = [
    ("ACTIVE", "Active"),
    ("EXPIRED", "Expirée"),
    ("CANCELLED", "Annulée"),
]


def build_concessions_view(page: ft.Page, state):
    error_text = ft.Text("", color=ft.Colors.RED)
    can_manage = state.role in ("ADMIN", "SECRETARIAT")
    can_delete = state.role == "ADMIN"

    grave_dd = ft.Dropdown(label="Tombe", width=200, options=[])
    owner_dd = ft.Dropdown(label="Client (propriétaire)", width=220, options=[])
    number_field = ft.TextField(label="N° de concession", width=180)
    duration_dd = ft.Dropdown(
        label="Durée", width=160,
        options=[ft.dropdown.Option(key=k, text=v) for k, v in DURATION_OPTIONS],
        value="TEMPORARY",
    )
    start_date = ft.TextField(label="Date de début (AAAA-MM-JJ)", width=200)
    end_date = ft.TextField(label="Date de fin (AAAA-MM-JJ, optionnel)", width=220)
    status_dd = ft.Dropdown(
        label="Statut", width=140,
        options=[ft.dropdown.Option(key=k, text=v) for k, v in STATUS_OPTIONS],
        value="ACTIVE",
    )

    list_column = ft.Column(spacing=6)

    def refresh_dropdowns():
        try:
            graves = api.list_graves(state.access_token)
        except api.ApiError:
            graves = []
        grave_dd.options = [ft.dropdown.Option(key=str(g["id"]), text=f"Tombe {g['grave_number']}") for g in graves]

        try:
            clients = api.list_users(state.access_token, role="CLIENT")
        except api.ApiError:
            clients = []
        owner_dd.options = [ft.dropdown.Option(key=str(c["id"]), text=f"{c['username']} ({c['email']})") for c in clients]
        page.update()

    def refresh_list():
        list_column.controls.clear()
        try:
            concessions = api.list_concessions(state.access_token)
        except api.ApiError as err:
            list_column.controls.append(ft.Text(f"Erreur : {err.detail}", color=ft.Colors.RED))
            page.update()
            return

        if not concessions:
            list_column.controls.append(ft.Text("Aucune concession.", color=ft.Colors.ON_SURFACE_VARIANT))

        for c in concessions:
            balance_text = ft.Text("", size=12, color=ft.Colors.ON_SURFACE_VARIANT)

            def load_balance(e, cid=c["id"], txt=balance_text):
                try:
                    bal = api.get_concession_balance(state.access_token, cid)
                except api.ApiError as err:
                    txt.value = f"Erreur : {err.detail}"
                    page.update()
                    return
                if bal["amount_due"] is None:
                    txt.value = "Aucun montant dû renseigné."
                else:
                    txt.value = f"Payé : {bal['total_paid']} / Dû : {bal['amount_due']} — Reste : {bal['balance_remaining']}"
                page.update()

            row_controls = [
                ft.Text(f"#{c['id']} {c['concession_number']}", width=140),
                ft.Text(f"Tombe {c['grave_id']}", width=90),
                ft.Text(f"Client #{c['owner_id']}", width=100),
                ft.Text(c['status'], width=90),
                ft.TextButton("Voir solde", on_click=load_balance),
            ]

            if can_delete:
                def delete_concession(e, cid=c["id"]):
                    try:
                        api.delete_concession(state.access_token, cid)
                    except api.ApiError as err:
                        error_text.value = f"Erreur : {err.detail}"
                        page.update()
                        return
                    refresh_list()

                row_controls.append(ft.IconButton(icon=ft.Icons.DELETE_OUTLINE, icon_color=ft.Colors.RED, on_click=delete_concession))

            list_column.controls.append(ft.Column([ft.Row(row_controls), balance_text], spacing=2))

        page.update()

    def create_concession(e):
        error_text.value = ""
        if not grave_dd.value or not owner_dd.value or not number_field.value or not start_date.value:
            error_text.value = "Tombe, client, numéro et date de début sont obligatoires."
            page.update()
            return

        payload = {
            "grave_id": int(grave_dd.value),
            "owner_id": int(owner_dd.value),
            "concession_number": number_field.value,
            "duration_type": duration_dd.value,
            "start_date": start_date.value,
            "end_date": end_date.value or None,
            "status": status_dd.value,
        }
        try:
            api.create_concession(state.access_token, payload)
        except api.ApiError as err:
            error_text.value = f"Erreur : {err.detail}"
            page.update()
            return

        number_field.value = ""
        start_date.value = ""
        end_date.value = ""
        refresh_list()

    form = ft.Column(
        [
            ft.Text("Nouvelle concession", size=16, weight=ft.FontWeight.W_600),
            ft.Row([grave_dd, owner_dd, number_field], wrap=True),
            ft.Row([duration_dd, start_date, end_date, status_dd], wrap=True),
            ft.ElevatedButton("Créer la concession", icon=ft.Icons.ADD, on_click=create_concession),
        ],
        spacing=10,
        visible=can_manage,
    )

    refresh_dropdowns()
    refresh_list()

    return ft.Column(
        [
            ft.Text("Concessions", size=18, weight=ft.FontWeight.W_600),
            error_text,
            form,
            ft.Divider(),
            ft.Text("Concessions existantes", size=16, weight=ft.FontWeight.W_600),
            list_column,
        ],
        spacing=10,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )
