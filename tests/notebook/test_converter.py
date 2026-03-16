"""Tests for supernote.notebook.converter module."""

from unittest.mock import MagicMock

from supernote.notebook.converter import ImageConverter


def test_get_mark_layer_visibility_marks_matching_layers() -> None:
    """_get_mark_layer_visibility maps layer names to True if type is MARK."""
    converter = ImageConverter(MagicMock())
    page = MagicMock()

    mark_layer = MagicMock()
    mark_layer.get_name.return_value = "MAINLAYER"
    mark_layer.get_type.return_value = "MARK"

    other_layer = MagicMock()
    other_layer.get_name.return_value = "LAYER1"
    other_layer.get_type.return_value = "OTHER"

    page.get_layers.return_value = [mark_layer, other_layer]

    result = converter._get_mark_layer_visibility(page)
    assert result == {"MAINLAYER": True, "LAYER1": False}
