import base64

from django import template
from django.templatetags.static import static

register = template.Library()


@register.filter
def img_src(value, default="Images/default-avatar.png"):
    """Turn whatever is stored as a picture into a usable <img src>."""
    if not value:
        return static(default)
    if isinstance(value, (bytes, bytearray, memoryview)):
        data = base64.b64encode(bytes(value)).decode("ascii")
        return "data:image/jpeg;base64," + data
    text = str(value).strip()
    if not text or text in ("None", "null"):
        return static(default)
    if text.startswith(("http://", "https://", "/", "data:")):
        return text
    if len(text) > 200:  # long text = base64 picture data
        return "data:image/jpeg;base64," + text
    return static("Images/" + text)
