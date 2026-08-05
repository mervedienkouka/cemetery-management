import flet as ft

from views.home_view import build_home_view
from views.graves_map_view import build_graves_map_view
from views.reservations_view import build_reservations_view
from views.reports_view import build_reports_view
from views.infrastructure_view import build_infrastructure_view
from views.concessions_view import build_concessions_view
from views.payments_view import build_payments_view
from views.exhumations_view import build_exhumations_view
from views.users_view import build_users_view

ROLE_LABELS = {
    "ADMIN": "Administrateur",
    "SECRETARIAT": "Secrétariat",
    "AGENT_TERRAIN": "Agent de terrain",
    "CLIENT": "Client",
}


def build_dashboard_view(page: ft.Page, state, go_login):
    body = ft.Container(expand=True, padding=20, bgcolor=ft.Colors.SURFACE_CONTAINER_LOWEST)

    def show_home(e=None):
        body.content = build_home_view(page, state)
        page.update()

    def show_graves(e=None):
        body.content = build_graves_map_view(page, state, on_reservation_created=lambda: None)
        page.update()

    def show_reservations(e=None):
        body.content = build_reservations_view(page, state)
        page.update()

    def show_reports(e=None):
        body.content = build_reports_view(page, state)
        page.update()

    def show_infrastructure(e=None):
        body.content = build_infrastructure_view(page, state)
        page.update()

    def show_concessions(e=None):
        body.content = build_concessions_view(page, state)
        page.update()

    def show_payments(e=None):
        body.content = build_payments_view(page, state)
        page.update()

    def show_exhumations(e=None):
        body.content = build_exhumations_view(page, state)
        page.update()

    def show_users(e=None):
        body.content = build_users_view(page, state)
        page.update()

    def do_logout(e=None):
        state.reset()
        go_login()

    nav_items = [
        ft.NavigationRailDestination(icon=ft.Icons.HOME_OUTLINED, selected_icon=ft.Icons.HOME, label="Accueil"),
        ft.NavigationRailDestination(icon=ft.Icons.MAP_OUTLINED, selected_icon=ft.Icons.MAP, label="Carte des tombes"),
        ft.NavigationRailDestination(icon=ft.Icons.EVENT_NOTE_OUTLINED, selected_icon=ft.Icons.EVENT_NOTE, label="Réservations"),
    ]
    handlers = [show_home, show_graves, show_reservations]

    if state.role in ("ADMIN", "SECRETARIAT", "CLIENT"):
        nav_items.append(
            ft.NavigationRailDestination(icon=ft.Icons.ASSIGNMENT_OUTLINED, selected_icon=ft.Icons.ASSIGNMENT, label="Concessions")
        )
        handlers.append(show_concessions)

    if state.role in ("ADMIN", "SECRETARIAT", "CLIENT"):
        nav_items.append(
            ft.NavigationRailDestination(icon=ft.Icons.PAYMENTS_OUTLINED, selected_icon=ft.Icons.PAYMENTS, label="Paiements")
        )
        handlers.append(show_payments)

    if state.role in ("ADMIN", "AGENT_TERRAIN"):
        nav_items.append(
            ft.NavigationRailDestination(icon=ft.Icons.LOCATION_CITY_OUTLINED, selected_icon=ft.Icons.LOCATION_CITY, label="Terrain")
        )
        handlers.append(show_infrastructure)
        nav_items.append(
            ft.NavigationRailDestination(icon=ft.Icons.HEALING_OUTLINED, selected_icon=ft.Icons.HEALING, label="Exhumations")
        )
        handlers.append(show_exhumations)

    if state.role in ("ADMIN", "SECRETARIAT"):
        nav_items.append(
            ft.NavigationRailDestination(icon=ft.Icons.BAR_CHART_OUTLINED, selected_icon=ft.Icons.BAR_CHART, label="Rapports")
        )
        handlers.append(show_reports)

    if state.role == "ADMIN":
        nav_items.append(
            ft.NavigationRailDestination(icon=ft.Icons.MANAGE_ACCOUNTS_OUTLINED, selected_icon=ft.Icons.MANAGE_ACCOUNTS, label="Utilisateurs")
        )
        handlers.append(show_users)

    def on_nav_change(e):
        handlers[e.control.selected_index]()

    rail = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        destinations=nav_items,
        on_change=on_nav_change,
        min_width=100,
        bgcolor=ft.Colors.WHITE,
        indicator_color=ft.Colors.INDIGO_100,
        selected_label_text_style=ft.TextStyle(color=ft.Colors.INDIGO_700, weight=ft.FontWeight.W_600, size=12),
        unselected_label_text_style=ft.TextStyle(color=ft.Colors.ON_SURFACE_VARIANT, size=12),
    )

    header = ft.Container(
        content=ft.Row(
            [
                ft.Icon(ft.Icons.CHURCH, color=ft.Colors.WHITE, size=22),
                ft.Text("Gestion de cimetière", size=18, weight=ft.FontWeight.W_600, color=ft.Colors.WHITE),
                ft.Container(expand=True),
                ft.Icon(ft.Icons.ACCOUNT_CIRCLE, color=ft.Colors.WHITE, size=20),
                ft.Text(f"{state.user['username']} — {ROLE_LABELS.get(state.role, state.role)}", size=13, color=ft.Colors.WHITE),
                ft.IconButton(icon=ft.Icons.LOGOUT, icon_color=ft.Colors.WHITE, tooltip="Se déconnecter", on_click=do_logout),
            ],
            spacing=10,
        ),
        gradient=ft.LinearGradient(
            begin=ft.Alignment.CENTER_LEFT,
            end=ft.Alignment.CENTER_RIGHT,
            colors=[ft.Colors.INDIGO_700, ft.Colors.INDIGO_500],
        ),
        padding=ft.Padding.symmetric(horizontal=20, vertical=14),
    )

    show_home()

    return ft.Column(
        [
            header,
            ft.Divider(height=1),
            ft.Row([rail, ft.VerticalDivider(width=1), body], expand=True),
        ],
        expand=True,
    )
