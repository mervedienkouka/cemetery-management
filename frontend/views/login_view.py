import flet as ft

import api_client as api


def build_login_view(page: ft.Page, state, go_mfa, go_dashboard, go_register=None):
    email_field = ft.TextField(
        label="Email",
        autofocus=True,
        width=340,
        prefix_icon=ft.Icons.EMAIL_OUTLINED,
        border_radius=8,
    )
    password_field = ft.TextField(
        label="Mot de passe",
        password=True,
        can_reveal_password=True,
        width=340,
        prefix_icon=ft.Icons.LOCK_OUTLINE,
        border_radius=8,
    )
    error_text = ft.Text("", color=ft.Colors.RED)
    loading = ft.ProgressRing(visible=False, width=18, height=18, stroke_width=2)

    def do_login(e):
        error_text.value = ""
        loading.visible = True
        page.update()

        try:
            result = api.login(email_field.value.strip(), password_field.value)
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

        loading.visible = False

        if result.get("mfa_required"):
            state.temp_token = result["temp_token"]
            go_mfa()
        else:
            page.update()

    login_button = ft.ElevatedButton(
        content=ft.Row(
            [ft.Icon(ft.Icons.LOGIN, size=18), ft.Text("Se connecter", weight=ft.FontWeight.W_600)],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=8,
        ),
        on_click=do_login,
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
                    content=ft.Icon(ft.Icons.CHURCH, size=40, color=ft.Colors.INDIGO_600),
                    bgcolor=ft.Colors.INDIGO_50,
                    width=76,
                    height=76,
                    border_radius=38,
                    alignment=ft.Alignment.CENTER,
                ),
                ft.Container(height=16),
                ft.Text("Gestion de cimetière", size=24, weight=ft.FontWeight.W_700),
                ft.Text("Connectez-vous à votre espace", size=13, color=ft.Colors.ON_SURFACE_VARIANT),
                ft.Container(height=24),
                email_field,
                ft.Container(height=12),
                password_field,
                ft.Container(height=20),
                ft.Row([login_button, loading], alignment=ft.MainAxisAlignment.CENTER),
                error_text,
            ] + ([ft.TextButton("Pas de compte ? Créer un compte", icon=ft.Icons.PERSON_ADD_ALT_1, on_click=lambda e: go_register())] if go_register else []),
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
