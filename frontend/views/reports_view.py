import flet as ft

import api_client as api


def build_reports_view(page: ft.Page, state):
    content = ft.Column(spacing=16)

    def refresh():
        content.controls.clear()

        try:
            occupancy = api.report_occupancy(state.access_token)
            revenue = api.report_revenue(state.access_token)
        except api.ApiError as err:
            content.controls.append(ft.Text(f"Erreur : {err.detail}", color=ft.Colors.RED))
            page.update()
            return

        content.controls.append(ft.Text("Taux d'occupation", size=18, weight=ft.FontWeight.W_500))
        content.controls.append(
            ft.Text(f"Global : {occupancy['global_occupancy_rate']}%", size=14, color=ft.Colors.ON_SURFACE_VARIANT)
        )

        for block in occupancy["blocks"]:
            content.controls.append(
                ft.Row([
                    ft.Text(f"{block['cemetery']} - {block['block_code']}", width=220),
                    ft.ProgressBar(value=min(block["occupancy_rate"] / 100, 1), width=200),
                    ft.Text(f"{block['occupancy_rate']}% ({block['occupied']}/{block['estimated_capacity']})"),
                ])
            )

        content.controls.append(ft.Divider())
        content.controls.append(ft.Text("Revenus", size=18, weight=ft.FontWeight.W_500))
        content.controls.append(ft.Text(f"Total : {revenue['total_revenue']}", size=16, weight=ft.FontWeight.W_500))

        for m in revenue["by_method"]:
            content.controls.append(ft.Text(f"{m['label']} : {m['total']}"))

        page.update()

    refresh()
    return content
