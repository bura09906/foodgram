import io

from django.conf import settings
from django.http import FileResponse
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


class ShoppingCartPdfGenerator:
    WIDTH, HEIGHT = A4
    LINE_HEIGHT = 15
    MARGIN_TOP = 50
    MARGIN_BOTTOM = 50
    FILE_HEADER = 'Список покупок'
    KEY_AMOUNT = 'amount'
    KEY_MEAS_UNIT = 'meas_unit'

    def __init__(self, page_objects):
        self.page_objects = page_objects

    def gen_new_page(self, pdf):
        pdfmetrics.registerFont(TTFont('DejaVuSans', settings.PDF_FONT_PATH))
        pdf.setFont('DejaVuSans', 15)
        header_width = pdf.stringWidth(self.FILE_HEADER, 'DejaVuSans', 15)
        x_position = (self.WIDTH - header_width) / 2
        y_position = self.HEIGHT - self.MARGIN_TOP
        pdf.drawString(x_position, y_position, self.FILE_HEADER)
        y_position -= self.LINE_HEIGHT * 2
        return y_position

    def return_pdf(self):
        buffer = io.BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=A4)
        y_position = self.gen_new_page(pdf)
        count = 0
        for name, details in self.page_objects.items():
            name_with_capital_letter = name.capitalize()
            count += 1
            if y_position <= self.MARGIN_BOTTOM:
                pdf.showPage()
                y_position = self.gen_new_page(pdf)
            pdf.drawString(
                40,
                y_position,
                f"{count}. {name_with_capital_letter} -"
                f" {details[self.KEY_AMOUNT]}"
                f" {details[self.KEY_MEAS_UNIT]}"
            )
            y_position -= self.LINE_HEIGHT
        pdf.save()
        buffer.seek(0)
        response = FileResponse(
            buffer,
            as_attachment=True,
            filename='Shopping_cart.pdf',
            content_type='application/pdf'
        )
        return response
