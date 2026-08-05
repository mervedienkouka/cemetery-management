import flet as ft

import api_client as api
from status_colors import status_color, status_label


def _stat_card(icon, label, value, color, subtitle=None):
    return ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Container(
                            content=ft.Icon(icon, color=ft.Colors.WHITE, size=20),
                            width=42, height=42,
                            bgcolor=ft.Colors.with_opacity(0.35, ft.Colors.WHITE),
                            border_radius=12,
                            alignment=ft.Alignment.CENTER,
                        ),
                        ft.Container(expand=True),
                    ],
                ),
                ft.Container(height=10),
                ft.Text(str(value), size=28, weight=ft.FontWeight.W_700, color=ft.Colors.WHITE),
                ft.Text(label, size=13, color=ft.Colors.WHITE, weight=ft.FontWeight.W_500),
                ft.Text(subtitle or "", size=11, color=ft.Colors.with_opacity(0.85, ft.Colors.WHITE)),
            ],
            spacing=2,
        ),
        gradient=ft.LinearGradient(
            begin=ft.Alignment.TOP_LEFT,
            end=ft.Alignment.BOTTOM_RIGHT,
            colors=color,
        ),
        border_radius=16,
        padding=18,
        width=220,
        height=150,
        shadow=ft.BoxShadow(blur_radius=16, color=ft.Colors.with_opacity(0.18, ft.Colors.BLACK), offset=ft.Offset(0, 6)),
    )


def _progress_row(label, rate, color):
    return ft.Column(
        [
            ft.Row(
                [ft.Text(label, size=13, weight=ft.FontWeight.W_500), ft.Container(expand=True), ft.Text(f"{rate:.0f}%", size=13, weight=ft.FontWeight.W_600, color=color)],
            ),
            ft.ProgressBar(value=rate / 100, color=color, bgcolor=ft.Colors.with_opacity(0.15, color), height=8, border_radius=4),
        ],
        spacing=4,
    )


GREEN_GRAD = [ft.Colors.GREEN_400, ft.Colors.GREEN_700]
ORANGE_GRAD = [ft.Colors.ORANGE_400, ft.Colors.DEEP_ORANGE_600]
RED_GRAD = [ft.Colors.RED_400, ft.Colors.RED_700]
INDIGO_GRAD = [ft.Colors.INDIGO_400, ft.Colors.INDIGO_700]
TEAL_GRAD = [ft.Colors.TEAL_400, ft.Colors.TEAL_700]
PURPLE_GRAD = [ft.Colors.PURPLE_400, ft.Colors.PURPLE_700]
AMBER_GRAD = [ft.Colors.AMBER_400, ft.Colors.ORANGE_800]


def _build_alerts_card(page: ft.Page, state):
    result_text = ft.Text("", size=13)

    def check_now(e):
        result_text.value = "Vérification en cours..."
        page.update()
        try:
            result = api.check_alerts(state.access_token)
        except api.ApiError as err:
            result_text.value = f"Erreur : {err.detail}"
            page.update()
            return

        parts = [
            f"{result['expiring_concessions_count']} concession(s) proche(s) d'échéance",
            f"{result['overdue_payments_count']} paiement(s) en retard",
        ]
        result_text.value = " · ".join(parts)
        if result["expiring_concessions"]:
            result_text.value += "\n" + ", ".join(
                f"{c['concession_number']} (expire le {c['end_date']})" for c in result["expiring_concessions"]
            )
        page.update()

    return ft.Container(
        content=ft.Row(
            [
                ft.Icon(ft.Icons.NOTIFICATIONS_ACTIVE_OUTLINED, color=ft.Colors.AMBER_700),
                ft.Column(
                    [
                        ft.Text("Alertes concessions / paiements", size=14, weight=ft.FontWeight.W_600),
                        result_text,
                    ],
                    spacing=2,
                    expand=True,
                ),
                ft.ElevatedButton("Vérifier maintenant", icon=ft.Icons.REFRESH, on_click=check_now),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=14,
        ),
        bgcolor=ft.Colors.AMBER_50,
        border_radius=16,
        padding=16,
    )


def _alerts_section(page: ft.Page, state):
    result_text = ft.Text("", size=13)
    loading = ft.ProgressRing(visible=False, width=16, height=16, stroke_width=2)

    def do_check(e):
        loading.visible = True
        result_text.value = ""
        page.update()
        try:
            result = api.check_alerts(state.access_token)
        except api.ApiError as err:
            loading.visible = False
            result_text.value = f"Erreur : {err.detail}"
            result_text.color = ft.Colors.RED
            page.update()
            return

        loading.visible = False
        expiring = result["expiring_concessions_count"]
        overdue = result["overdue_payments_count"]
        if expiring == 0 and overdue == 0:
            result_text.value = "Aucune alerte : rien à signaler."
            result_text.color = ft.Colors.GREEN_700
        else:
            details = ", ".join(f"{c['concession_number']} ({c['end_date']})" for c in result["expiring_concessions"])
            result_text.value = f"{expiring} concession(s) proche(s) d'échéance" + (f" : {details}" if details else "") + f" · {overdue} paiement(s) en retard."
            result_text.color = ft.Colors.ORANGE_800
        page.update()

    return ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Icon(ft.Icons.NOTIFICATIONS_ACTIVE_OUTLINED, color=ft.Colors.AMBER_800),
                        ft.Text("Alertes automatiques", size=16, weight=ft.FontWeight.W_600),
                        ft.Container(expand=True),
                        ft.ElevatedButton(
                            "Vérifier maintenant",
                            icon=ft.Icons.REFRESH,
                            on_click=do_check,
                            bgcolor=ft.Colors.AMBER_700,
                            color=ft.Colors.WHITE,
                        ),
                        loading,
                    ],
                ),
                ft.Text("Échéances de concession à moins de 30 jours et paiements en retard.", size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                result_text,
            ],
            spacing=8,
        ),
        bgcolor=ft.Colors.WHITE,
        border_radius=16,
        padding=20,
        shadow=ft.BoxShadow(blur_radius=12, color=ft.Colors.with_opacity(0.08, ft.Colors.BLACK)),
    )


def build_home_view(page: ft.Page, state):
    content = ft.Column(spacing=20, scroll=ft.ScrollMode.AUTO, expand=True)

    def refresh():
        content.controls.clear()
        content.controls.append(
            ft.Text(f"Bonjour, {state.user['username']} 👋", size=22, weight=ft.FontWeight.W_700)
        )

        try:
            graves = api.list_graves(state.access_token)
        except api.ApiError:
            graves = []

        counts = {"AVAILABLE": 0, "RESERVED": 0, "OCCUPIED": 0, "UNUSABLE": 0}
        for g in graves:
            counts[g["status"]] = counts.get(g["status"], 0) + 1

        cards = ft.Row(
            [
                _stat_card(ft.Icons.CHECK_CIRCLE_OUTLINE, "Disponibles", counts["AVAILABLE"], GREEN_GRAD),
                _stat_card(ft.Icons.SCHEDULE, "Réservées", counts["RESERVED"], ORANGE_GRAD),
                _stat_card(ft.Icons.LOCK_OUTLINE, "Occupées", counts["OCCUPIED"], RED_GRAD),
            ],
            spacing=16,
            wrap=True,
        )

        if state.role == "CLIENT":
            try:
                my_reservations = [r for r in api.list_reservations(state.access_token) if r["client_id"] == state.user["id"]]
            except api.ApiError:
                my_reservations = []
            pending = len([r for r in my_reservations if r["status"] == "PENDING"])

            cards.controls.append(
                _stat_card(ft.Icons.PENDING_ACTIONS, "Mes réservations en attente", pending, AMBER_GRAD)
            )
            content.controls.append(cards)
            page.update()
            return

        if state.role == "AGENT_TERRAIN":
            content.controls.append(cards)
            page.update()
            return

        # ADMIN / SECRETARIAT : vision complète avec occupation + revenus
        try:
            pending_reservations = len([r for r in api.list_reservations(state.access_token) if r["status"] == "PENDING"])
        except api.ApiError:
            pending_reservations = 0

        cards.controls.append(
            _stat_card(ft.Icons.PENDING_ACTIONS, "Réservations en attente", pending_reservations, AMBER_GRAD)
        )

        try:
            occupancy = api.report_occupancy(state.access_token)
        except api.ApiError:
            occupancy = {"blocks": [], "global_occupancy_rate": 0}

        try:
            revenue = api.report_revenue(state.access_token)
        except api.ApiError:
            revenue = {"total_revenue": 0, "by_method": []}

        cards.controls.append(
            _stat_card(ft.Icons.DONUT_LARGE, "Taux d'occupation global", f"{occupancy['global_occupancy_rate']:.0f}%", INDIGO_GRAD)
        )
        cards.controls.append(
            _stat_card(ft.Icons.PAYMENTS, "Revenus totaux", f"{revenue['total_revenue']:.0f}", TEAL_GRAD, subtitle="toutes méthodes confondues")
        )

        content.controls.append(cards)

        if state.role == "ADMIN":
            content.controls.append(_alerts_section(page, state))

        if state.role == "ADMIN":
            content.controls.append(_build_alerts_card(page, state))
        if occupancy["blocks"]:
            block_rows = ft.Column(
                [
                    _progress_row(f"{b['cemetery']} — Bloc {b['block_code']}", b["occupancy_rate"], ft.Colors.INDIGO_600)
                    for b in occupancy["blocks"]
                ],
                spacing=14,
            )
            content.controls.append(
                ft.Container(
                    content=ft.Column(
                        [ft.Text("Occupation par bloc", size=16, weight=ft.FontWeight.W_600), ft.Container(height=8), block_rows],
                    ),
                    bgcolor=ft.Colors.WHITE,
                    border_radius=16,
                    padding=20,
                    shadow=ft.BoxShadow(blur_radius=12, color=ft.Colors.with_opacity(0.08, ft.Colors.BLACK)),
                )
            )

        # Revenus par méthode de paiement
        if revenue["by_method"]:
            method_colors = [ft.Colors.TEAL_600, ft.Colors.PURPLE_600, ft.Colors.INDIGO_600, ft.Colors.ORANGE_700]
            method_rows = ft.Column(
                [
                    ft.Row(
                        [
                            ft.Container(width=10, height=10, bgcolor=method_colors[i % len(method_colors)], border_radius=5),
                            ft.Text(m["label"], size=13),
                            ft.Container(expand=True),
                            ft.Text(f"{m['total']:.0f}", size=13, weight=ft.FontWeight.W_600),
                        ]
                    )
                    for i, m in enumerate(revenue["by_method"])
                ],
                spacing=10,
            )
            content.controls.append(
                ft.Container(
                    content=ft.Column(
                        [ft.Text("Revenus par méthode de paiement", size=16, weight=ft.FontWeight.W_600), ft.Container(height=8), method_rows],
                    ),
                    bgcolor=ft.Colors.WHITE,
                    border_radius=16,
                    padding=20,
                    shadow=ft.BoxShadow(blur_radius=12, color=ft.Colors.with_opacity(0.08, ft.Colors.BLACK)),
                )
            )

        page.update()

    refresh()
    return ft.Container(content=content, padding=4, bgcolor=ft.Colors.SURFACE_CONTAINER_LOWEST, expand=True)
