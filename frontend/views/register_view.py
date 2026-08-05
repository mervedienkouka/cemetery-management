import flet as ft

import api_client as api


def build_register_view(page: ft.Page, go_login):
    username_field = ft.TextField(label="Nom d'utilisateur", width=340, prefix_icon=ft.Icons.PERSON_OUTLINE, border_radius=8)
    email_field = ft.TextField(label="Email", width=340, prefix_icon=ft.Icons.EMAIL_OUTLINED, border_radius=8)
    phone_field = ft.TextField(label="Téléphone (optionnel)", width=340, prefix_icon=ft.Icons.PHONE_OUTLINED, border_radius=8)
    password_field = ft.TextField(label="Mot de passe", password=True, can_reveal_password=True, width=340, prefix_icon=ft.Icons.LOCK_OUTLINE, border_radius=8)
    confirm_field = ft.TextField(label="Confirmer le mot de passe", password=True, can_reveal_password=True, width=340, prefix_icon=ft.Icons.LOCK_OUTLINE, border_radius=8)
    error_text = ft.Text("", color=ft.Colors.RED)
    success_text = ft.Text("", color=ft.Colors.GREEN)
    loading = ft.ProgressRing(visible=False, width=18, height=18, stroke_width=2)

    def do_register(e):
        error_text.value = ""
        success_text.value = ""

        if not username_field.value or not email_field.value or not password_field.value:
            error_text.value = "Nom d'utilisateur, email et mot de passe sont obligatoires."
            page.update()
            return

        if password_field.value != confirm_field.value:
            error_text.value = "Les mots de passe ne correspondent pas."
            page.update()
            return

        if len(password_field.value) < 8:
            error_text.value = "Le mot de passe doit contenir au moins 8 caractères."
            page.update()
            return

        loading.visible = True
        page.update()

        try:
            api.register(
                username_field.value.strip(),
                email_field.value.strip(),
                password_field.value,
                phone_field.value.strip(),
            )
        except api.ApiError as err:
            loading.visible = False
            error_text.value = err.detail
            page.update()
            return
        except Exception:
            loading.visible = False
            error_text.value = "Impossible de contacter le serveur."
            page.update()
            return

        loading.visible = False
        success_text.value = "Compte créé avec succès ! Tu peux maintenant te connecter."
        username_field.value = email_field.value = phone_field.value = ""
        password_field.value = confirm_field.value = ""
        page.update()

    register_button = ft.ElevatedButton(
        content=ft.Row(
            [ft.Icon(ft.Icons.PERSON_ADD_ALT_1, size=18), ft.Text("Créer mon compte", weight=ft.FontWeight.W_600)],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=8,
        ),
        on_click=do_register,
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
                    content=ft.Icon(ft.Icons.PERSON_ADD_ALT_1, size=40, color=ft.Colors.INDIGO_600),
                    bgcolor=ft.Colors.INDIGO_50,
                    width=76,
                    height=76,
                    border_radius=38,
                    alignment=ft.Alignment.CENTER,
                ),
                ft.Container(height=16),
                ft.Text("Créer un compte", size=24, weight=ft.FontWeight.W_700),
                ft.Text("Réserve et suis tes démarches en ligne", size=13, color=ft.Colors.ON_SURFACE_VARIANT),
                ft.Container(height=24),
                username_field,
                ft.Container(height=10),
                email_field,
                ft.Container(height=10),
                phone_field,
                ft.Container(height=10),
                password_field,
                ft.Container(height=10),
                confirm_field,
                ft.Container(height=20),
                ft.Row([register_button, loading], alignment=ft.MainAxisAlignment.CENTER),
                success_text,
                error_text,
                ft.TextButton("J'ai déjà un compte — Se connecter", icon=ft.Icons.ARROW_BACK, on_click=lambda e: go_login()),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            tight=True,
            scroll=ft.ScrollMode.AUTO,
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
        padding=20,
    )
