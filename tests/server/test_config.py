import os
from collections.abc import Generator
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from supernote.server.config import ServerConfig


@pytest.fixture(autouse=True)
def patch_server_config() -> Generator[None, None, None]:
    """Override the autouse fixture from conftest.py to do nothing.

    This ensures that ServerConfig.load() runs the real logic instead of returning a mock.
    """
    yield


def test_server_config_defaults(tmp_path: Path) -> None:
    """Test loading configuration with defaults."""
    config_dir = tmp_path / "config"
    config = ServerConfig.load(config_dir)

    assert config.host == "0.0.0.0"
    assert config.port == 8000
    assert config.storage_dir == "storage"
    assert config.auth.secret_key != ""  # Should be generated in-memory


def test_server_config_load_from_file(tmp_path: Path) -> None:
    """Test loading configuration from a file including users."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_file = config_dir / "config.yaml"

    data = {
        "host": "127.0.0.1",
        "port": 9090,
        "auth": {
            "secret_key": "my-secret-key",
            "enable_registration": True,
        },
    }
    with open(config_file, "w") as f:
        yaml.safe_dump(data, f)

    config = ServerConfig.load(config_dir)

    assert config.host == "127.0.0.1"
    assert config.port == 9090
    assert config.auth.secret_key == "my-secret-key"
    assert config.auth.enable_registration is True


def test_server_config_env_var_override(tmp_path: Path) -> None:
    """Test that environment variables override config file."""
    config_dir = tmp_path / "config"
    with patch.dict(
        os.environ,
        {
            "SUPERNOTE_JWT_SECRET": "env-secret",
            "SUPERNOTE_HOST": "1.2.3.4",
            "SUPERNOTE_PORT": "5555",
        },
    ):
        config = ServerConfig.load(config_dir)
        assert config.auth.secret_key == "env-secret"
        assert config.host == "1.2.3.4"
        assert config.port == 5555


def test_example_config_is_valid() -> None:
    """Ensure config-example.yaml can be loaded by ServerConfig."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    config_path = os.path.join(base_dir, "config-example.yaml")

    config = ServerConfig.load(config_file=config_path)

    assert config.host == "0.0.0.0"
    assert config.port == 8000
    assert config.storage_dir == "storage"
    assert config.auth.secret_key == "CHANGE_ME_TO_A_SECURE_RANDOM_STRING"
    assert config.auth.enable_registration is False


def test_server_config_proxy_env_vars(tmp_path: Path) -> None:
    """Test that proxy configuration can be set via environment variables."""
    config_dir = tmp_path / "config"
    with patch.dict(
        os.environ,
        {
            "SUPERNOTE_PROXY_MODE": "strict",
            "SUPERNOTE_TRUSTED_PROXIES": "10.0.0.1,10.0.0.2",
        },
    ):
        config = ServerConfig.load(config_dir)
        assert config.proxy_mode == "strict"
        # The list should be parsed from the comma-separated string
        assert config.trusted_proxies == ["10.0.0.1", "10.0.0.2"]


def test_server_config_temp_cleanup_env_vars(tmp_path: Path) -> None:
    """Test that temp cleanup configuration can be set via environment variables."""
    config_dir = tmp_path / "config"
    with patch.dict(
        os.environ,
        {
            "SUPERNOTE_TEMP_CLEANUP_INTERVAL": "1800",
            "SUPERNOTE_TEMP_TTL": "3600",
        },
    ):
        config = ServerConfig.load(config_dir)
        assert config.temp_cleanup_interval_seconds == 1800
        assert config.temp_ttl_seconds == 3600


def test_server_config_default_quota_env_var(tmp_path: Path) -> None:
    """Test that default quota can be set via environment variable."""
    config_dir = tmp_path / "config"
    with patch.dict(os.environ, {"SUPERNOTE_DEFAULT_QUOTA_BYTES": "5368709120"}):
        config = ServerConfig.load(config_dir)
        assert config.default_quota_bytes == 5368709120  # 5 GB


def test_server_config_quota_env_var_invalid_value(tmp_path: Path) -> None:
    """Invalid (non-integer) quota env var should fall back to the default."""
    config_dir = tmp_path / "config"
    with patch.dict(os.environ, {"SUPERNOTE_DEFAULT_QUOTA_BYTES": "not-a-number"}):
        config = ServerConfig.load(config_dir)
        assert config.default_quota_bytes == 10737418240  # default 10 GB


def test_server_config_temp_cleanup_env_vars_invalid(tmp_path: Path) -> None:
    """Invalid (non-integer) temp cleanup env vars should fall back to defaults."""
    config_dir = tmp_path / "config"
    with patch.dict(
        os.environ,
        {
            "SUPERNOTE_TEMP_CLEANUP_INTERVAL": "not-a-number",
            "SUPERNOTE_TEMP_TTL": "not-a-number",
        },
    ):
        config = ServerConfig.load(config_dir)
        assert config.temp_cleanup_interval_seconds == 3600  # default
        assert config.temp_ttl_seconds == 86400  # default


def test_server_config_mcp_port_env_var(tmp_path: Path) -> None:
    """SUPERNOTE_MCP_PORT env var overrides mcp_port."""
    config_dir = tmp_path / "config"
    with patch.dict(os.environ, {"SUPERNOTE_MCP_PORT": "9001"}):
        config = ServerConfig.load(config_dir)
        assert config.mcp_port == 9001


def test_server_config_mcp_port_env_var_invalid(tmp_path: Path) -> None:
    """Invalid SUPERNOTE_MCP_PORT falls back to default."""
    config_dir = tmp_path / "config"
    with patch.dict(os.environ, {"SUPERNOTE_MCP_PORT": "not-a-port"}):
        config = ServerConfig.load(config_dir)
        assert config.mcp_port == 8001  # default


def test_server_config_invalid_port_env_var(tmp_path: Path) -> None:
    """Invalid SUPERNOTE_PORT falls back to default."""
    config_dir = tmp_path / "config"
    with patch.dict(os.environ, {"SUPERNOTE_PORT": "not-a-port"}):
        config = ServerConfig.load(config_dir)
        assert config.port == 8000  # default


def test_server_config_base_url_env_var(tmp_path: Path) -> None:
    """SUPERNOTE_BASE_URL and SUPERNOTE_MCP_BASE_URL are applied."""
    config_dir = tmp_path / "config"
    with patch.dict(
        os.environ,
        {
            "SUPERNOTE_BASE_URL": "https://notes.example.com",
            "SUPERNOTE_MCP_BASE_URL": "https://mcp.example.com",
        },
    ):
        config = ServerConfig.load(config_dir)
        assert config.base_url == "https://notes.example.com"
        assert config.mcp_base_url == "https://mcp.example.com"


def test_server_config_legacy_auth_url_base(tmp_path: Path) -> None:
    """SUPERNOTE_AUTH_URL_BASE is used as base_url when base_url is not set."""
    config_dir = tmp_path / "config"
    with patch.dict(
        os.environ, {"SUPERNOTE_AUTH_URL_BASE": "https://legacy.example.com"}
    ):
        config = ServerConfig.load(config_dir)
        assert config.base_url == "https://legacy.example.com"


def test_server_config_enable_registration_env_var(tmp_path: Path) -> None:
    """SUPERNOTE_ENABLE_REGISTRATION env var overrides auth config."""
    config_dir = tmp_path / "config"
    with patch.dict(os.environ, {"SUPERNOTE_ENABLE_REGISTRATION": "true"}):
        config = ServerConfig.load(config_dir)
        assert config.auth.enable_registration is True


def test_server_config_enable_remote_password_reset_env_var(tmp_path: Path) -> None:
    """SUPERNOTE_ENABLE_REMOTE_PASSWORD_RESET env var overrides auth config."""
    config_dir = tmp_path / "config"
    with patch.dict(os.environ, {"SUPERNOTE_ENABLE_REMOTE_PASSWORD_RESET": "true"}):
        config = ServerConfig.load(config_dir)
        assert config.auth.enable_remote_password_reset is True


def test_server_config_gemini_env_vars(tmp_path: Path) -> None:
    """Gemini API key and model env vars are applied."""
    config_dir = tmp_path / "config"
    with patch.dict(
        os.environ,
        {
            "SUPERNOTE_GEMINI_API_KEY": "test-gemini-key",
            "SUPERNOTE_GEMINI_OCR_MODEL": "gemini-ocr-test",
            "SUPERNOTE_GEMINI_EMBEDDING_MODEL": "gemini-embed-test",
            "SUPERNOTE_GEMINI_CHAT_MODEL": "gemini-chat-test",
        },
    ):
        config = ServerConfig.load(config_dir)
        assert config.gemini_api_key == "test-gemini-key"
        assert config.gemini_ocr_model == "gemini-ocr-test"
        assert config.gemini_embedding_model == "gemini-embed-test"
        assert config.gemini_chat_model == "gemini-chat-test"


def test_server_config_gemini_concurrency_env_var(tmp_path: Path) -> None:
    """SUPERNOTE_GEMINI_MAX_CONCURRENCY env var sets concurrency."""
    config_dir = tmp_path / "config"
    with patch.dict(os.environ, {"SUPERNOTE_GEMINI_MAX_CONCURRENCY": "10"}):
        config = ServerConfig.load(config_dir)
        assert config.gemini_max_concurrency == 10


def test_server_config_gemini_concurrency_clamped_to_one(tmp_path: Path) -> None:
    """SUPERNOTE_GEMINI_MAX_CONCURRENCY < 1 is clamped to 1."""
    config_dir = tmp_path / "config"
    with patch.dict(os.environ, {"SUPERNOTE_GEMINI_MAX_CONCURRENCY": "0"}):
        config = ServerConfig.load(config_dir)
        assert config.gemini_max_concurrency == 1


def test_server_config_gemini_concurrency_invalid(tmp_path: Path) -> None:
    """Invalid SUPERNOTE_GEMINI_MAX_CONCURRENCY falls back to default."""
    config_dir = tmp_path / "config"
    with patch.dict(os.environ, {"SUPERNOTE_GEMINI_MAX_CONCURRENCY": "not-a-number"}):
        config = ServerConfig.load(config_dir)
        assert config.gemini_max_concurrency == 5  # default


def test_server_config_mistral_env_vars(tmp_path: Path) -> None:
    """Mistral API key and model env vars are applied."""
    config_dir = tmp_path / "config"
    with patch.dict(
        os.environ,
        {
            "SUPERNOTE_MISTRAL_API_KEY": "test-mistral-key",
            "SUPERNOTE_MISTRAL_OCR_MODEL": "mistral-ocr-test",
            "SUPERNOTE_MISTRAL_EMBEDDING_MODEL": "mistral-embed-test",
            "SUPERNOTE_MISTRAL_CHAT_MODEL": "mistral-chat-test",
        },
    ):
        config = ServerConfig.load(config_dir)
        assert config.mistral_api_key == "test-mistral-key"
        assert config.mistral_ocr_model == "mistral-ocr-test"
        assert config.mistral_embedding_model == "mistral-embed-test"
        assert config.mistral_chat_model == "mistral-chat-test"


def test_server_config_mistral_concurrency_clamped(tmp_path: Path) -> None:
    """SUPERNOTE_MISTRAL_MAX_CONCURRENCY < 1 is clamped to 1."""
    config_dir = tmp_path / "config"
    with patch.dict(os.environ, {"SUPERNOTE_MISTRAL_MAX_CONCURRENCY": "0"}):
        config = ServerConfig.load(config_dir)
        assert config.mistral_max_concurrency == 1


def test_server_config_mistral_concurrency_invalid(tmp_path: Path) -> None:
    """Invalid SUPERNOTE_MISTRAL_MAX_CONCURRENCY falls back to default."""
    config_dir = tmp_path / "config"
    with patch.dict(os.environ, {"SUPERNOTE_MISTRAL_MAX_CONCURRENCY": "bad"}):
        config = ServerConfig.load(config_dir)
        assert config.mistral_max_concurrency == 5  # default


def test_server_config_base_url_property_default() -> None:
    """base_url property derives URL from host/port when _base_url is None."""
    from supernote.server.config import ServerConfig as SC

    cfg = SC(host="0.0.0.0", port=8000)
    assert cfg.base_url == "http://localhost:8000"

    cfg2 = SC(host="192.168.1.1", port=9000)
    assert cfg2.base_url == "http://192.168.1.1:9000"


def test_server_config_mcp_base_url_property_default() -> None:
    """mcp_base_url property derives URL from host/mcp_port when _mcp_base_url is None."""
    from supernote.server.config import ServerConfig as SC

    cfg = SC(host="0.0.0.0", mcp_port=8001)
    assert cfg.mcp_base_url == "http://localhost:8001"


def test_server_config_get_bool_env_false_values(tmp_path: Path) -> None:
    """_get_bool_env returns False for '0', 'false', 'no', 'off'."""
    from supernote.server.config import _get_bool_env

    for val in ("0", "false", "no", "off", "FALSE"):
        with patch.dict(os.environ, {"TEST_BOOL": val}):
            assert _get_bool_env("TEST_BOOL", True) is False


def test_server_config_get_bool_env_true_values() -> None:
    """_get_bool_env returns True for '1', 'true', 'yes', 'on'."""
    from supernote.server.config import _get_bool_env

    for val in ("1", "true", "yes", "on", "TRUE"):
        with patch.dict(os.environ, {"TEST_BOOL": val}):
            assert _get_bool_env("TEST_BOOL", False) is True


def test_server_config_invalid_yaml(tmp_path: Path) -> None:
    """Invalid YAML in config file falls back to defaults."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "config.yaml").write_text("not: valid: yaml: [")
    config = ServerConfig.load(config_dir)
    # Falls back to defaults
    assert config.host == "0.0.0.0"
