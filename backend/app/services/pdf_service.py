import os
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
import logging

logger = logging.getLogger(__name__)

# The path to the templates directory, relative to this file's location
# __file__ -> /code/app/services/pdf_service.py
# os.path.dirname(__file__) -> /code/app/services
# os.path.dirname(os.path.dirname(__file__)) -> /code/app
TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')

def generate_pdf_from_template(template_name: str, context: dict) -> bytes:
    """
    Renders an HTML template with the given context and converts it to a PDF.

    :param template_name: The filename of the HTML template in the 'templates' directory.
    :param context: A dictionary of data to pass to the template.
    :return: The generated PDF as bytes.
    """
    try:
        env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
        template = env.get_template(template_name)
        html_out = template.render(context)
        return HTML(string=html_out).write_pdf()
    except Exception as e:
        logger.error(f"Failed to generate PDF for template '{template_name}': {e}", exc_info=True)
        raise