import flet as ft

import api_client as api


def build_mfa_view(page: ft.Page, state, go_dashboard, go_login):
    code_field = ft.TextField(
        label="Code reçu par email",
        width=340,
        max_length=6,
        autofocus=True,
        prefix_icon=ft.Icons.PIN_OUTLINED,
        border_radius=8,
        text_align=ft.TextAlign.CENTER,
    )
    error_text = ft.Text("", color=ft.Colors.RED)
    loading = ft.ProgressRing(visible=False, width=18, height=18, stroke_width=2)

    def do_verify(e):
        error_text.value = ""
        loading.visible = True
        page.update()

        try:
            tokens = api.verify_otp(state.temp_token, code_field.value.strip())
        except api.ApiError as err:
            loading.visible = False
            error_text.value = err.detail
            page.update()
            return
        except Exception:
            loading.visible = False
            error_text.value = "Impossible de contacter le serveur. Vérifie que le backend est démarré."
            page.update()
            return

        state.access_token = tokens["access_token"]
        state.refresh_token = tokens["refresh_token"]

        try:
            state.user = api.me(state.access_token)
        except api.ApiError as err:
            loading.visible = False
            error_text.value = f"Connecté mais impossible de charger le profil : {err.detail}"
            page.update()
            return

        loading.visible = False
        go_dashboard()

    def cancel(e):
        state.temp_token = None
        go_login()

    verify_button = ft.ElevatedButton(
        content=ft.Row(
            [ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, size=18), ft.Text("Valider", weight=ft.FontWeight.W_600)],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=8,
        ),
        on_click=do_verify,
        width=340,
        height=46,
        bgcolor=ft.Colors.INDIGO_600,
        color=ft.Colors.WHITE,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
    )

    card = ft.Container(
        content=ft.Column(
            [
                ft.Container(
                    content=ft.Icon(ft.Icons.MARK_EMAIL_READ_OUTLINED, size=40, color=ft.Colors.INDIGO_600),
                    bgcolor=ft.Colors.INDIGO_50,
                    width=76,
                    height=76,
                    border_radius=38,
                    alignment=ft.Alignment.CENTER,
                ),
                ft.Container(height=16),
                ft.Text("Vérification en deux étapes", size=22, weight=ft.FontWeight.W_700),
                ft.Text("Un code à 6 chiffres a été envoyé par email.", size=13, color=ft.Colors.ON_SURFACE_VARIANT),
                ft.Container(height=24),
                code_field,
                ft.Container(height=20),
                ft.Row([verify_button, loading], alignment=ft.MainAxisAlignment.CENTER),
                ft.TextButton("Retour", icon=ft.Icons.ARROW_BACK, on_click=cancel),
                error_text,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            tight=True,
        ),
        bgcolor=ft.Colors.WHITE,
        padding=40,
        border_radius=16,
        shadow=ft.BoxShadow(
            spread_radius=1,
            blur_radius=24,
            color=ft.Colors.with_opacity(0.12, ft.Colors.BLACK),
            offset=ft.Offset(0, 8),
        ),
    )

    return ft.Container(
        content=card,
        alignment=ft.Alignment.CENTER,
        expand=True,
        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
    )
