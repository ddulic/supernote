from unittest.mock import MagicMock

from supernote.server.utils.auth_utils import get_token_from_request


def test_get_token_from_header() -> None:
    request = MagicMock()
    request.headers.get.return_value = "header-token"
    assert get_token_from_request(request) == "header-token"


def test_get_token_from_query_param() -> None:
    request = MagicMock()
    request.headers.get.return_value = None
    request.query.get.return_value = "query-token"
    assert get_token_from_request(request) == "query-token"


def test_get_token_missing() -> None:
    request = MagicMock()
    request.headers.get.return_value = None
    request.query.get.return_value = None
    assert get_token_from_request(request) is None


def test_header_takes_precedence_over_query() -> None:
    request = MagicMock()
    request.headers.get.return_value = "header-token"
    request.query.get.return_value = "query-token"
    assert get_token_from_request(request) == "header-token"
