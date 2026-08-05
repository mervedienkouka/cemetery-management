import flet as ft

import api_client as api

ROLE_OPTIONS = [
    ("ADMIN", "Administrateur"),
    ("SECRETARIAT", "Secrétariat"),
    ("AGENT_TERRAIN", "Agent de terrain"),
    ("CLIENT", "Client"),
]
ROLE_LABELS = dict(ROLE_OPTIONS)


def build_users_view(page: ft.Page, state):
    content = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)
    error_text = ft.Text("", color=ft.Colors.RED)

    def change_role(user_id, new_role):
        try:
            api.update_user_role(state.access_token, user_id, new_role)
        except api.ApiError as err:
            error_text.value = f"Erreur : {err.detail}"
            page.update()
            return
        refresh()

    def toggle_active(user_id, active):
        try:
            api.toggle_user_active(state.access_token, user_id, active)
        except api.ApiError as err:
            error_text.value = f"Erreur : {err.detail}"
            page.update()
            return
        refresh()

    def refresh():
        content.controls.clear()
        error_text.value = ""
        content.controls.append(ft.Text("Utilisateurs et rôles", size=18, weight=ft.FontWeight.W_600))
        content.controls.append(error_text)

        try:
            users = api.list_users(state.access_token, include_inactive=True)
        except api.ApiError as err:
            content.controls.append(ft.Text(f"Erreur : {err.detail}", color=ft.Colors.RED))
            page.update()
            return

        if not users:
            content.controls.append(ft.Text("Aucun utilisateur.", color=ft.Colors.ON_SURFACE_VARIANT))
            page.update()
            return

        for u in users:
            is_active = u.get("is_active", True)

            role_dd = ft.Dropdown(
                width=180,
                value=u["role"],
                options=[ft.dropdown.Option(key=k, text=v) for k, v in ROLE_OPTIONS],
                on_select=lambda e, uid=u["id"]: change_role(uid, e.control.value),
                disabled=(u["id"] == state.user["id"]),
            )

            row = ft.Row(
                [
                    ft.Container(
                        content=ft.Icon(ft.Icons.PERSON, size=18),
                        width=32, height=32, bgcolor=ft.Colors.INDIGO_50, border_radius=16,
                        alignment=ft.Alignment.CENTER,
                    ),
                    ft.Column(
                        [
                            ft.Text(f"{u['username']} ({u['email']})", weight=ft.FontWeight.W_500),
                            ft.Text(
                                (u.get("phone") or "—") + ("" if is_active else " — désactivé"),
                                size=11,
                                color=ft.Colors.RED if not is_active else ft.Colors.ON_SURFACE_VARIANT,
                            ),
                        ],
                        spacing=0,
                        width=280,
                    ),
                    role_dd,
                    ft.IconButton(
                        icon=ft.Icons.PERSON_OFF_OUTLINED if is_active else ft.Icons.PERSON_OUTLINE,
                        tooltip="Désactiver ce compte" if is_active else "Réactiver ce compte",
                        on_click=lambda e, uid=u["id"], active=is_active: toggle_active(uid, not active),
                        disabled=(u["id"] == state.user["id"]),
                    ),
                ],
                spacing=14,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )

            content.controls.append(
                ft.Container(content=row, padding=10, bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST, border_radius=8)
            )

        page.update()

    refresh()
    return content
