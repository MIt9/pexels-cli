"""Tests for Pexels CLI."""

from typer.testing import CliRunner
from pexels_cli.cli import app
from pexels_cli.config import load_config

runner = CliRunner()


def test_config_commands():
    result = runner.invoke(app, ["config", "show"])
    assert result.exit_code == 0
    assert "Pexels CLI Configuration" in result.output

    set_res = runner.invoke(app, ["config", "set-pexels-key", "KEY_ABC_123"])
    assert set_res.exit_code == 0
    assert "successfully saved" in set_res.output

    cfg = load_config()
    assert cfg.pexels_api_key == "KEY_ABC_123"


def test_help_command():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Pexels CLI" in result.output
    assert "smart-photo" in result.output
    assert "smart-video" in result.output
