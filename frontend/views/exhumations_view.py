import os
import tempfile

import flet as ft

import api_client as api

STATUS_LABELS = {
    "PENDING": "En attente de validation",
    "VALIDATED": "Validée",
    "REJECTED": "Rejetée",
}


def build_exhumations_view(page: ft.Page, state):
    error_text = ft.Text("", color=ft.Colors.RED)
    can_manage = state.role in ("ADMIN", "AGENT_TERRAIN")
    can_delete = state.role == "ADMIN"

    grave_dd = ft.Dropdown(label="Tombe", width=180, options=[])
    agent_dd = ft.Dropdown(label="Agent responsable (optionnel)", width=220, options=[])
    date_field = ft.TextField(label="Date (AAAA-MM-JJ)", width=160)
    reason_field = ft.TextField(label="Motif", width=260)

    list_column = ft.Column(spacing=8)

    def refresh_dropdowns():
        try:
            graves = api.list_graves(state.access_token)
        except api.ApiError:
            graves = []
        grave_dd.options = [ft.dropdown.Option(key=str(g["id"]), text=f"Tombe {g['grave_number']}") for g in graves]

        try:
            agents = api.list_users(state.access_token, role="AGENT_TERRAIN")
        except api.ApiError:
            agents = []
        agent_dd.options = [ft.dropdown.Option(key=str(a["id"]), text=a["username"]) for a in agents]
        page.update()

    def download_pv(exhumation_id):
        try:
            pdf_bytes = api.download_exhumation_pv(state.access_token, exhumation_id)
        except api.ApiError as err:
            error_text.value = f"Erreur : {err.detail}"
            page.update()
            return

        path = os.path.join(tempfile.gettempdir(), f"pv_exhumation_{exhumation_id}.pdf")
        with open(path, "wb") as f:
            f.write(pdf_bytes)

        try:
            os.startfile(path)  # Windows
        except AttributeError:
            import webbrowser
            webbrowser.open(f"file://{path}")

    def refresh_list():
        list_column.controls.clear()
        try:
            exhumations = api.list_exhumations(state.access_token)
        except api.ApiError as err:
            list_column.controls.append(ft.Text(f"Erreur : {err.detail}", color=ft.Colors.RED))
            page.update()
            return

        if not exhumations:
            list_column.controls.append(ft.Text("Aucune exhumation.", color=ft.Colors.ON_SURFACE_VARIANT))

        for x in exhumations:
            row_controls = [
                ft.Text(f"#{x['id']}", width=40),
                ft.Text(f"Tombe {x['grave_id']}", width=90),
                ft.Text(x["exhumation_date"], width=100),
                ft.Text(STATUS_LABELS.get(x["status"], x["status"]), width=160),
            ]

            if can_manage and x["status"] == "PENDING":
                def validate(e, xid=x["id"]):
                    try:
                        api.validate_exhumation(state.access_token, xid)
                    except api.ApiError as err:
                        error_text.value = f"Erreur : {err.detail}"
                        page.update()
                        return
                    refresh_list()

                def reject(e, xid=x["id"]):
                    try:
                        api.reject_exhumation(state.access_token, xid)
                    except api.ApiError as err:
                        error_text.value = f"Erreur : {err.detail}"
                        page.update()
                        return
                    refresh_list()

                row_controls.append(ft.ElevatedButton("Valider", height=32, on_click=validate))
                row_controls.append(ft.OutlinedButton("Rejeter", height=32, on_click=reject))

            if x["status"] == "VALIDATED":
                row_controls.append(
                    ft.TextButton("Télécharger le PV", icon=ft.Icons.PICTURE_AS_PDF_OUTLINED, on_click=lambda e, xid=x["id"]: download_pv(xid))
                )

            if can_delete:
                def delete_exhumation(e, xid=x["id"]):
                    try:
                        api.delete_exhumation(state.access_token, xid)
                    except api.ApiError as err:
                        error_text.value = f"Erreur : {err.detail}"
                        page.update()
                        return
                    refresh_list()

                row_controls.append(ft.IconButton(icon=ft.Icons.DELETE_OUTLINE, icon_color=ft.Colors.RED, on_click=delete_exhumation))

            list_column.controls.append(ft.Row(row_controls, wrap=True))

        page.update()

    def create_exhumation(e):
        error_text.value = ""
        if not grave_dd.value or not date_field.value or not reason_field.value:
            error_text.value = "Tombe, date et motif sont obligatoires."
            page.update()
            return

        payload = {
            "grave_id": int(grave_dd.value),
            "responsible_agent_id": int(agent_dd.value) if agent_dd.value else None,
            "exhumation_date": date_field.value,
            "reason": reason_field.value,
        }
        try:
            api.create_exhumation(state.access_token, payload)
        except api.ApiError as err:
            error_text.value = f"Erreur : {err.detail}"
            page.update()
            return

        date_field.value = ""
        reason_field.value = ""
        refresh_list()

    form = ft.Column(
        [
            ft.Text("Nouvelle exhumation", size=16, weight=ft.FontWeight.W_600),
            ft.Row([grave_dd, agent_dd, date_field], wrap=True),
            reason_field,
            ft.ElevatedButton("Créer la demande", icon=ft.Icons.ADD, on_click=create_exhumation),
        ],
        spacing=10,
        visible=can_manage,
    )

    refresh_dropdowns()
    refresh_list()

    return ft.Column(
        [
            ft.Text("Exhumations", size=18, weight=ft.FontWeight.W_600),
            error_text,
            form,
            ft.Divider(),
            ft.Text("Exhumations existantes", size=16, weight=ft.FontWeight.W_600),
            list_column,
        ],
        spacing=10,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )
