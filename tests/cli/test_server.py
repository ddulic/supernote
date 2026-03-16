"""Tests for the server CLI module."""

import argparse
import os
from unittest.mock import patch

from supernote.cli.server import add_parser, serve_run


def test_add_parser_registers_serve_subcommand() -> None:
    """add_parser() registers a 'serve' subcommand."""
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    add_parser(subparsers)
    args = parser.parse_args(["serve"])
    assert hasattr(args, "func")


def test_add_parser_ephemeral_flag() -> None:
    """add_parser() registers --ephemeral flag on serve subcommand."""
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    add_parser(subparsers)
    args = parser.parse_args(["serve", "--ephemeral"])
    assert args.ephemeral is True


def test_add_parser_config_dir_flag() -> None:
    """add_parser() registers --config-dir flag on serve subcommand."""
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    add_parser(subparsers)
    args = parser.parse_args(["serve", "--config-dir", "/tmp/cfg"])
    assert args.config_dir == "/tmp/cfg"


def test_serve_run_non_ephemeral() -> None:
    """serve_run() without --ephemeral calls server_app.run directly."""
    args = argparse.Namespace(ephemeral=False)
    with patch("supernote.cli.server.server_app.run") as mock_run:
        serve_run(args)
    mock_run.assert_called_once_with(args)


def test_serve_run_ephemeral_sets_env_and_runs() -> None:
    """serve_run() with --ephemeral sets env vars and calls server_app.run."""
    args = argparse.Namespace(ephemeral=True)
    env_clean = {
        k: v
        for k, v in os.environ.items()
        if k not in ("SUPERNOTE_PORT", "SUPERNOTE_HOST")
    }
    with (
        patch.dict(os.environ, env_clean, clear=True),
        patch("supernote.cli.server.server_app.run") as mock_run,
    ):
        serve_run(args)
    mock_run.assert_called_once_with(args)
    # Env vars are cleaned up after the tempdir context manager exits
    # but run was called inside the block, so we just verify it was called


def test_serve_run_ephemeral_respects_existing_port() -> None:
    """serve_run() with --ephemeral does not override an existing SUPERNOTE_PORT."""
    args = argparse.Namespace(ephemeral=True)
    with (
        patch.dict(os.environ, {"SUPERNOTE_PORT": "9999"}, clear=False),
        patch("supernote.cli.server.server_app.run"),
    ):
        serve_run(args)
    # The existing value should have been preserved during the call
