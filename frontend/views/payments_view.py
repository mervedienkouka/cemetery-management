import flet as ft

import api_client as api

METHOD_OPTIONS = [
    ("CASH", "Espèces"),
    ("MOBILE_MONEY", "Mobile Money"),
    ("AIRTEL_MONEY", "Airtel Money"),
    ("BANK_TRANSFER", "Virement bancaire"),
]

STATUS_OPTIONS = [
    ("PENDING", "En attente"),
    ("COMPLETED", "Complété"),
    ("FAILED", "Échoué"),
]


def build_payments_view(page: ft.Page, state):
    error_text = ft.Text("", color=ft.Colors.RED)
    can_delete = state.role == "ADMIN"

    concession_dd = ft.Dropdown(label="Concession", width=200, options=[])
    amount_field = ft.TextField(label="Montant payé", width=140)
    amount_due_field = ft.TextField(label="Montant total dû (optionnel)", width=200)
    date_field = ft.TextField(label="Date (AAAA-MM-JJ)", width=160)
    method_dd = ft.Dropdown(
        label="Moyen de paiement", width=180,
        options=[ft.dropdown.Option(key=k, text=v) for k, v in METHOD_OPTIONS],
        value="CASH",
    )
    reference_field = ft.TextField(label="Référence", width=160)
    status_dd = ft.Dropdown(
        label="Statut", width=140,
        options=[ft.dropdown.Option(key=k, text=v) for k, v in STATUS_OPTIONS],
        value="COMPLETED",
    )

    list_column = ft.Column(spacing=6)

    def refresh_dropdowns():
        try:
            concessions = api.list_concessions(state.access_token)
        except api.ApiError:
            concessions = []
        concession_dd.options = [
            ft.dropdown.Option(key=str(c["id"]), text=f"{c['concession_number']} (#{c['id']})") for c in concessions
        ]
        page.update()

    def refresh_list():
        list_column.controls.clear()
        try:
            payments = api.list_payments(state.access_token)
        except api.ApiError as err:
            list_column.controls.append(ft.Text(f"Erreur : {err.detail}", color=ft.Colors.RED))
            page.update()
            return

        if not payments:
            list_column.controls.append(ft.Text("Aucun paiement.", color=ft.Colors.ON_SURFACE_VARIANT))

        for p in payments:
            method_label = dict(METHOD_OPTIONS).get(p["payment_method"], p["payment_method"])
            row_controls = [
                ft.Text(f"#{p['id']}", width=40),
                ft.Text(f"Concession {p['concession_id']}", width=110),
                ft.Text(f"{p['amount']}", width=90),
                ft.Text(method_label, width=130),
                ft.Text(p["status"], width=90),
                ft.Text(p["payment_date"], width=100),
            ]

            if can_delete:
                def delete_payment(e, pid=p["id"]):
                    try:
                        api.delete_payment(state.access_token, pid)
                    except api.ApiError as err:
                        error_text.value = f"Erreur : {err.detail}"
                        page.update()
                        return
                    refresh_list()

                row_controls.append(ft.IconButton(icon=ft.Icons.DELETE_OUTLINE, icon_color=ft.Colors.RED, on_click=delete_payment))

            list_column.controls.append(ft.Row(row_controls))

        page.update()

    def create_payment(e):
        error_text.value = ""
        if not concession_dd.value or not amount_field.value or not date_field.value or not reference_field.value:
            error_text.value = "Concession, montant, date et référence sont obligatoires."
            page.update()
            return
        try:
            amount_value = float(amount_field.value)
            amount_due_value = float(amount_due_field.value) if amount_due_field.value else None
        except ValueError:
            error_text.value = "Le montant doit être un nombre."
            page.update()
            return

        payload = {
            "concession_id": int(concession_dd.value),
            "amount": amount_value,
            "amount_due": amount_due_value,
            "payment_date": date_field.value,
            "payment_method": method_dd.value,
            "reference": reference_field.value,
            "status": status_dd.value,
        }
        try:
            api.create_payment(state.access_token, payload)
        except api.ApiError as err:
            error_text.value = f"Erreur : {err.detail}"
            page.update()
            return

        amount_field.value = ""
        amount_due_field.value = ""
        date_field.value = ""
        reference_field.value = ""
        refresh_list()

    form = ft.Column(
        [
            ft.Text("Nouveau paiement", size=16, weight=ft.FontWeight.W_600),
            ft.Row([concession_dd, amount_field, amount_due_field], wrap=True),
            ft.Row([date_field, method_dd, reference_field, status_dd], wrap=True),
            ft.ElevatedButton("Enregistrer le paiement", icon=ft.Icons.ADD, on_click=create_payment),
        ],
        spacing=10,
    )

    refresh_dropdowns()
    refresh_list()

    return ft.Column(
        [
            ft.Text("Paiements", size=18, weight=ft.FontWeight.W_600),
            error_text,
            form,
            ft.Divider(),
            ft.Text("Paiements existants", size=16, weight=ft.FontWeight.W_600),
            list_column,
        ],
        spacing=10,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )
