from fpdf import FPDF


def _base_pdf(title: str) -> FPDF:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, title, ln=True, align="C")
    pdf.ln(5)
    pdf.set_font("Helvetica", "", 11)
    return pdf


def generate_invoice_pdf(reservation, grave, client, concession=None) -> bytes:
    """Facture PDF générée à la validation d'une réservation
    (cahier des charges 2.4)."""
    pdf = _base_pdf("Facture de réservation")

    pdf.cell(0, 8, f"Facture N° RES-{reservation.id:06d}", ln=True)
    pdf.cell(0, 8, f"Client : {client.username} ({client.email})", ln=True)
    pdf.cell(0, 8, f"Emplacement : Bloc {grave.block.code} - Tombe {grave.grave_number}", ln=True)
    pdf.cell(0, 8, f"Date de réservation : {reservation.reservation_date}", ln=True)
    pdf.cell(0, 8, f"Date d'expiration : {reservation.expiration_date}", ln=True)
    pdf.cell(0, 8, f"Statut : {reservation.get_status_display()}", ln=True)

    if concession is not None:
        pdf.ln(4)
        pdf.cell(0, 8, f"Concession N° {concession.concession_number}", ln=True)
        pdf.cell(0, 8, f"Type de durée : {concession.get_duration_type_display()}", ln=True)

    pdf.ln(10)
    pdf.set_font("Helvetica", "I", 9)
    pdf.cell(0, 6, "Document généré automatiquement - Gestion de Cimetière GI2 2026", ln=True)

    return bytes(pdf.output())


def generate_exhumation_pv_pdf(exhumation) -> bytes:
    """Procès-verbal d'exhumation, généré à la validation administrative
    (cahier des charges 2.5)."""
    pdf = _base_pdf("Procès-verbal d'exhumation")

    pdf.cell(0, 8, f"PV N° EXH-{exhumation.id:06d}", ln=True)
    pdf.cell(0, 8, f"Tombe : Bloc {exhumation.grave.block.code} - {exhumation.grave.grave_number}", ln=True)
    pdf.cell(0, 8, f"Date d'exhumation : {exhumation.exhumation_date}", ln=True)
    pdf.cell(0, 8, f"Motif : {exhumation.reason}", ln=True)

    if exhumation.responsible_agent:
        pdf.cell(0, 8, f"Agent responsable : {exhumation.responsible_agent.username}", ln=True)

    if exhumation.validated_by:
        pdf.cell(0, 8, f"Validé par : {exhumation.validated_by.username}", ln=True)
        pdf.cell(0, 8, f"Date de validation : {exhumation.validated_at}", ln=True)

    if exhumation.observations:
        pdf.ln(4)
        pdf.multi_cell(0, 8, f"Observations : {exhumation.observations}")

    pdf.ln(10)
    pdf.set_font("Helvetica", "I", 9)
    pdf.cell(0, 6, "Document généré automatiquement - Gestion de Cimetière GI2 2026", ln=True)

    return bytes(pdf.output())
