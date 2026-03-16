"""Tests for supernote.notebook.decoder module."""

from supernote.notebook import color
from supernote.notebook.decoder import RattaRleDecoder


def test_create_color_bytearray_rgb() -> None:
    """RGB mode extracts r,g,b components and replicates for length."""
    decoder = RattaRleDecoder()
    # 0xFF0000 = red
    colormap = {0x61: 0xFF0000}
    result = decoder._create_color_bytearray(color.MODE_RGB, colormap, 0x61, 2)
    assert result == bytearray([0xFF, 0x00, 0x00, 0xFF, 0x00, 0x00])


def test_create_color_bytearray_grayscale() -> None:
    """Non-RGB mode uses the colormap value as a raw byte and replicates."""
    decoder = RattaRleDecoder()
    colormap = {0x61: 128}
    result = decoder._create_color_bytearray(color.MODE_GRAYSCALE, colormap, 0x61, 3)
    assert result == bytearray([128, 128, 128])
