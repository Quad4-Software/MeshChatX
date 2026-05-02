"""Tests for LXMFy CLI functionality."""

import os
from unittest.mock import MagicMock, patch

import pytest

from lxmfy.cli import (
    create_bot_file,
    create_example_cog,
    create_from_template,
    get_bot_name,
    get_template_choice,
    get_user_choice,
    interactive_create,
    interactive_run,
    is_safe_path,
    main,
    sanitize_filename,
    validate_bot_name,
)
from lxmfy.colors import (
    Colors,
    print_error,
    print_header,
    print_info,
    print_menu,
    print_success,
    print_warning,
)


class TestColors:
    """Test Colors class."""

    def test_colors_defined(self):
        """Test that all color constants are defined."""
        assert Colors.HEADER == "\033[95m"
        assert Colors.BLUE == "\033[94m"
        assert Colors.CYAN == "\033[96m"
        assert Colors.GREEN == "\033[92m"
        assert Colors.YELLOW == "\033[93m"
        assert Colors.RED == "\033[91m"
        assert Colors.ENDC == "\033[0m"
        assert Colors.BOLD == "\033[1m"
        assert Colors.UNDERLINE == "\033[4m"


class TestPrintFunctions:
    """Test print utility functions."""

    @patch("lxmfy.colors.Colors.is_colors_supported", return_value=True)
    @patch("builtins.print")
    def test_print_header(self, mock_print, mock_colors):
        """Test print_header function."""
        print_header("Test Header")
        mock_print.assert_called()

    @patch("lxmfy.colors.Colors.is_colors_supported", return_value=True)
    @patch("builtins.print")
    def test_print_success(self, mock_print, mock_colors):
        """Test print_success function."""
        print_success("Test message")
        mock_print.assert_called_with(
            f"{Colors.GREEN}{Colors.BOLD}✓ Test message{Colors.ENDC}",
        )

    @patch("lxmfy.colors.Colors.is_colors_supported", return_value=True)
    @patch("builtins.print")
    def test_print_error(self, mock_print, mock_colors):
        """Test print_error function."""
        print_error("Test error")
        mock_print.assert_called_with(
            f"{Colors.RED}{Colors.BOLD}✗ Test error{Colors.ENDC}",
        )

    @patch("lxmfy.colors.Colors.is_colors_supported", return_value=True)
    @patch("builtins.print")
    def test_print_info(self, mock_print, mock_colors):
        """Test print_info function."""
        print_info("Test info")
        mock_print.assert_called_with(
            f"{Colors.BLUE}{Colors.BOLD}ℹ Test info{Colors.ENDC}",
        )

    @patch("lxmfy.colors.Colors.is_colors_supported", return_value=True)
    @patch("builtins.print")
    def test_print_warning(self, mock_print, mock_colors):
        """Test print_warning function."""
        print_warning("Test warning")
        mock_print.assert_called_with(
            f"{Colors.YELLOW}{Colors.BOLD}⚠ Test warning{Colors.ENDC}",
        )

    @patch("lxmfy.colors.Colors.is_colors_supported", return_value=True)
    @patch("builtins.print")
    def test_print_menu(self, mock_print, mock_colors):
        """Test print_menu function."""
        print_menu()
        assert mock_print.call_count > 5


class TestInputFunctions:
    """Test input handling functions."""

    @patch("builtins.input")
    def test_get_user_choice_valid(self, mock_input):
        """Test get_user_choice with valid input."""
        mock_input.return_value = "1"
        result = get_user_choice()
        assert result == "1"

    @patch("builtins.input")
    @patch("lxmfy.cli.print_error")
    def test_get_user_choice_invalid_then_valid(self, mock_print_error, mock_input):
        """Test get_user_choice with invalid then valid input."""
        mock_input.side_effect = ["4", "2"]
        result = get_user_choice()
        assert result == "2"
        mock_print_error.assert_called_once()

    @patch("builtins.input")
    @patch("lxmfy.cli.validate_bot_name")
    def test_get_bot_name_valid(self, mock_validate, mock_input):
        """Test get_bot_name with valid input."""
        mock_input.return_value = "testbot"
        mock_validate.return_value = "testbot"
        result = get_bot_name()
        assert result == "testbot"

    @patch("builtins.input")
    @patch("lxmfy.cli.print_error")
    @patch("lxmfy.cli.validate_bot_name")
    def test_get_bot_name_invalid_then_valid(
        self,
        mock_validate,
        mock_print_error,
        mock_input,
    ):
        """Test get_bot_name with invalid then valid input."""
        mock_validate.side_effect = [ValueError("Invalid"), "validbot"]
        mock_input.side_effect = ["invalid", "validbot"]
        result = get_bot_name()
        assert result == "validbot"
        mock_print_error.assert_called_once()

    @patch("builtins.input")
    def test_get_template_choice_valid(self, mock_input):
        """Test get_template_choice with valid input."""
        mock_input.side_effect = ["1"]  # Choose basic template
        result = get_template_choice()
        assert result == "basic"

    @patch("builtins.input")
    @patch("lxmfy.cli.print_error")
    def test_get_template_choice_invalid_then_valid(self, mock_print_error, mock_input):
        """Test get_template_choice with invalid then valid input."""
        mock_input.side_effect = ["6", "3"]  # Invalid then reminder
        result = get_template_choice()
        assert result == "reminder"
        mock_print_error.assert_called_once()


class TestUtilityFunctions:
    """Test utility functions."""

    def test_sanitize_filename_basic(self):
        """Test sanitize_filename with basic filename."""
        result = sanitize_filename("test file!.txt")
        assert result == "testfile.py"  # Removes special chars and forces .py extension

    def test_sanitize_filename_no_extension(self):
        """Test sanitize_filename with no extension."""
        result = sanitize_filename("test file!")
        assert result == "testfile.py"

    def test_sanitize_filename_extension_override(self):
        """Test sanitize_filename forces .py extension."""
        result = sanitize_filename("test.js")
        assert result == "test.py"  # Forces .py extension

    def test_validate_bot_name_valid(self):
        """Test validate_bot_name with valid name."""
        result = validate_bot_name("TestBot123")
        assert result == "TestBot123"

    def test_validate_bot_name_with_spaces(self):
        """Test validate_bot_name with spaces and special chars."""
        result = validate_bot_name("Test Bot!")
        assert result == "Test Bot"  # Removes special chars

    def test_validate_bot_name_empty(self):
        """Test validate_bot_name with empty string."""
        with pytest.raises(ValueError, match="Bot name cannot be empty"):
            validate_bot_name("")

    def test_validate_bot_name_only_special(self):
        """Test validate_bot_name with only special characters."""
        with pytest.raises(ValueError, match="Bot name must contain valid characters"):
            validate_bot_name("!@#$%")

    def test_is_safe_path_no_base(self):
        """Test is_safe_path without base path."""
        assert is_safe_path("/some/path") is True

    def test_is_safe_path_safe(self):
        """Test is_safe_path with safe path."""
        assert is_safe_path("/base/safe/path", "/base") is True

    def test_is_safe_path_unsafe(self):
        """Test is_safe_path with unsafe path."""
        assert is_safe_path("/unsafe/path", "/base") is False

    def test_is_safe_path_invalid(self):
        """Test is_safe_path with invalid path."""
        assert is_safe_path("", "/base") is False


class TestFileCreation:
    """Test file creation functions."""

    def test_create_bot_file_basic(self, tmp_path):
        """Test create_bot_file creates a basic bot file."""
        output_path = tmp_path / "test_bot.py"
        result = create_bot_file("TestBot", str(output_path))

        assert os.path.exists(output_path)
        assert result.endswith("test_bot.py")

        with open(output_path) as f:
            content = f.read()
            assert "from lxmfy import LXMFBot" in content
            assert 'name="TestBot"' in content

    def test_create_bot_file_no_cogs(self, tmp_path):
        """Test create_bot_file with no_cogs=True."""
        output_path = tmp_path / "test_bot.py"
        result = create_bot_file("TestBot", str(output_path), no_cogs=True)

        assert result.endswith("test_bot.py")

        with open(output_path) as f:
            content = f.read()
            assert "cogs_enabled=False" in content

    def test_create_example_cog(self, tmp_path):
        """Test create_example_cog creates cog files."""
        bot_path = tmp_path / "test_bot.py"
        bot_path.write_text("# Test bot file")

        create_example_cog(str(bot_path))

        cogs_dir = tmp_path / "cogs"
        assert cogs_dir.exists()

        init_file = cogs_dir / "__init__.py"
        assert init_file.exists()

        basic_cog = cogs_dir / "basic.py"
        assert basic_cog.exists()

        with open(basic_cog) as f:
            content = f.read()
            assert "from lxmfy import Command" in content
            assert "class BasicCommands:" in content

    def test_create_from_template_basic(self, tmp_path):
        """Test create_from_template with basic template."""
        output_path = tmp_path / "test_bot.py"
        result = create_from_template("basic", str(output_path), "TestBot")

        assert os.path.exists(output_path)
        assert result.endswith("test_bot.py")

    def test_create_from_template_echo(self, tmp_path):
        """Test create_from_template with echo template."""
        output_path = tmp_path / "echo_bot.py"
        result = create_from_template("echo", str(output_path), "EchoBot")

        assert os.path.exists(output_path)
        assert result.endswith("echo_bot.py")

        with open(output_path) as f:
            content = f.read()
            assert "from lxmfy.templates import EchoBot" in content

    def test_create_from_template_invalid(self, tmp_path):
        """Test create_from_template with invalid template."""
        output_path = tmp_path / "invalid_bot.py"
        with pytest.raises(RuntimeError, match="Invalid template"):
            create_from_template("invalid", str(output_path), "InvalidBot")


class TestInteractiveFunctions:
    """Test interactive functions."""

    @patch("builtins.input")
    @patch("lxmfy.cli.create_from_template")
    @patch("lxmfy.cli.print_success")
    @patch("lxmfy.cli.print_info")
    def test_interactive_create_basic(
        self,
        mock_print_info,
        mock_print_success,
        mock_create,
        mock_input,
    ):
        """Test interactive_create with basic template."""
        mock_input.side_effect = ["TestBot", "1", "test_bot.py"]
        mock_create.return_value = "test_bot.py"

        interactive_create()

        mock_create.assert_called_once_with("basic", "test_bot.py", "TestBot")
        mock_print_success.assert_called()
        mock_print_info.assert_called()

    @patch("builtins.input")
    @patch("lxmfy.cli.create_from_template")
    @patch("lxmfy.cli.print_success")
    @patch("lxmfy.cli.print_info")
    def test_interactive_create_with_cog(
        self,
        mock_print_info,
        mock_print_success,
        mock_create,
        mock_input,
    ):
        """Test interactive_create creates example cog."""
        mock_input.side_effect = ["TestBot", "1", ""]  # Empty output path
        mock_create.return_value = "TestBot.py"

        interactive_create()

        mock_create.assert_called_once_with("basic", "TestBot.py", "TestBot")

    @patch("builtins.input")
    @patch("builtins.print")
    @patch("lxmfy.cli.print_header")
    @patch("lxmfy.cli.get_template_choice")
    def test_interactive_run(
        self,
        mock_get_template,
        mock_print_header,
        mock_print,
        mock_input,
    ):
        """Test interactive_run function."""
        mock_input.side_effect = ["CustomName"]
        mock_get_template.return_value = "echo"

        # Mock the EchoBot template
        with patch("lxmfy.cli.EchoBot") as mock_echo_bot:
            mock_bot_instance = MagicMock()
            mock_echo_bot.return_value = mock_bot_instance

            interactive_run()

            mock_echo_bot.assert_called_once()
            mock_bot_instance.run.assert_called_once()


class TestMainFunction:
    """Test main function."""

    @patch("sys.argv", ["lxmfy"])
    @patch("lxmfy.cli.interactive_mode")
    def test_main_interactive_mode(self, mock_interactive):
        """Test main function calls interactive_mode when no args."""
        main()
        mock_interactive.assert_called_once()

    @patch("sys.argv", ["lxmfy", "create", "testbot"])
    @patch("lxmfy.cli.create_from_template")
    @patch("lxmfy.cli.print_success")
    @patch("lxmfy.cli.print_info")
    def test_main_create_command(
        self,
        mock_print_info,
        mock_print_success,
        mock_create,
    ):
        """Test main function create command."""
        mock_create.return_value = "testbot.py"

        main()

        mock_create.assert_called_once_with("basic", "testbot.py", "testbot")
        mock_print_success.assert_called()
        mock_print_info.assert_called()

    @patch("sys.argv", ["lxmfy", "run", "echo"])
    @patch("lxmfy.cli.EchoBot")
    def test_main_run_command(self, mock_echo_bot):
        """Test main function run command."""
        mock_bot_instance = MagicMock()
        mock_echo_bot.return_value = mock_bot_instance

        main()

        mock_echo_bot.assert_called_once()
        mock_bot_instance.run.assert_called_once()

    @patch("sys.argv", ["lxmfy", "signatures", "test"])
    @patch("builtins.print")
    def test_main_signatures_test(self, mock_print):
        """Test main function signatures test command."""
        main()
        # Should print signature test messages
        assert mock_print.call_count > 5

    @patch("sys.argv", ["lxmfy", "signatures", "enable"])
    @patch("builtins.print")
    def test_main_signatures_enable(self, mock_print):
        """Test main function signatures enable command."""
        main()
        mock_print.assert_called()

    @patch("sys.argv", ["lxmfy", "signatures", "disable"])
    @patch("builtins.print")
    def test_main_signatures_disable(self, mock_print):
        """Test main function signatures disable command."""
        main()
        mock_print.assert_called()

    @patch("sys.argv", ["lxmfy", "signatures", "invalid"])
    @patch("lxmfy.cli.print_error")
    @patch("lxmfy.cli.print_info")
    def test_main_signatures_invalid(self, mock_print_info, mock_print_error):
        """Test main function signatures invalid command."""
        # This should not crash and should print error messages
        try:
            main()
        except SystemExit:
            pass  # Expected when invalid subcommand is provided

        # Should print error about unknown subcommand
        mock_print_error.assert_called_with("Unknown subcommand: invalid")
        mock_print_info.assert_called_with(
            "Available subcommands: test, enable, disable",
        )
