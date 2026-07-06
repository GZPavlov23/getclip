import io
import urllib.request

from PIL import Image, ImageTk


def load_thumbnail(url: str, max_width: int = 260) -> ImageTk.PhotoImage:
    with urllib.request.urlopen(url, timeout=10) as response:
        raw_bytes = response.read()

    image = Image.open(io.BytesIO(raw_bytes))
    ratio = max_width / image.width
    new_size = (max_width, int(image.height * ratio))
    image = image.resize(new_size)

    return ImageTk.PhotoImage(image)