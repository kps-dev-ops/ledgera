"""Génération PDF via WeasyPrint à partir de templates HTML + print.css."""
from pathlib import Path

from django.conf import settings
from django.template.loader import render_to_string
from weasyprint import CSS, HTML

PRINT_CSS_PATH = Path(settings.BASE_DIR) / "static" / "css" / "print.css"


def render_pdf(template_name: str, context: dict) -> bytes:
    """Rend un template Django en PDF avec print.css commun."""
    html = render_to_string(template_name, context)
    css = CSS(filename=str(PRINT_CSS_PATH)) if PRINT_CSS_PATH.exists() else None
    return HTML(string=html, base_url=str(settings.BASE_DIR)).write_pdf(
        stylesheets=[css] if css else []
    )
