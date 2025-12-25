import qrcode
import io
import base64
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from .models import QRCode, Claim


def generate_qr_code(claim):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(claim.qr_code.code)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    img_io = io.BytesIO()
    img.save(img_io, format='PNG')
    img_io.seek(0)

    base64_img = base64.b64encode(img_io.getvalue()).decode()

    return base64_img


def get_qr_code_url(claim):
    try:
        qr_code = QRCode.objects.get(claim=claim)
        if qr_code.qr_image_url:
            return qr_code.qr_image_url
    except QRCode.DoesNotExist:
        pass
    return None


def validate_qr_code(code):
    try:
        qr = QRCode.objects.get(code=code)
        return qr
    except QRCode.DoesNotExist:
        return None
