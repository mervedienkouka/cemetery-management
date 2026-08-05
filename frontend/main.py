import os

import flet as ft

from state import AppState
from views.login_view import build_login_view
from views.mfa_view import build_mfa_view
from views.dashboard_view import build_dashboard_view
from views.register_view import build_register_view


def main(page: ft.Page):
    page.title = "Gestion de cimetière"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0

    state = AppState()

    def show_login():
        page.controls.clear()
        page.add(ft.Container(content=build_login_view(page, state, show_mfa, show_dashboard, show_register), expand=True))
        page.update()

    def show_register():
        page.controls.clear()
        page.add(ft.Container(content=build_register_view(page, show_login), expand=True))
        page.update()

    def show_mfa():
        page.controls.clear()
        page.add(ft.Container(content=build_mfa_view(page, state, show_dashboard, show_login), expand=True))
        page.update()

    def show_dashboard():
        page.controls.clear()
        page.add(build_dashboard_view(page, state, show_login))
        page.update()

    show_login()


if __name__ == "__main__":
    # Render (et la plupart des hébergeurs) imposent le port via la
    # variable d'environnement PORT — en local, on garde 8550 par défaut.
    port = int(os.environ.get("PORT", 8550))
    ft.run(main, view=ft.AppView.WEB_BROWSER, port=port, host="192.168.56.1")
