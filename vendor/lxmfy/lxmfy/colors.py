"""Color support module for LXMFy CLI.

Provides cross-platform color support for terminal output.
"""

import os
import sys


class Colors:
    """ANSI color codes for terminal output.

    Automatically handles Windows Virtual Terminal Processing initialization.
    """

    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"

    _colors_enabled: bool | None = None
    _windows_vt_enabled: bool = False

    @classmethod
    def enable_windows_colors(cls) -> bool:
        """Enable ANSI color support on Windows 10/11.

        Returns:
            True if colors are supported, False otherwise.

        """
        if cls._windows_vt_enabled:
            return True

        if sys.platform != "win32":
            cls._colors_enabled = True
            return True

        try:
            import ctypes
            from ctypes import wintypes

            kernel32 = ctypes.windll.kernel32

            STD_OUTPUT_HANDLE = -11
            STD_ERROR_HANDLE = -12
            ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004

            for std_handle in [STD_OUTPUT_HANDLE, STD_ERROR_HANDLE]:
                handle = kernel32.GetStdHandle(std_handle)
                if handle == -1 or handle == 0:
                    continue

                mode = wintypes.DWORD()
                if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                    continue

                mode.value |= ENABLE_VIRTUAL_TERMINAL_PROCESSING
                if not kernel32.SetConsoleMode(handle, mode):
                    continue

            cls._windows_vt_enabled = True
            cls._colors_enabled = True
            return True

        except Exception:
            cls._colors_enabled = False
            return False

    @classmethod
    def is_colors_supported(cls) -> bool:
        """Check if colors are supported in the current environment.

        Returns:
            True if colors are supported, False otherwise.

        """
        if cls._colors_enabled is not None:
            return cls._colors_enabled

        if sys.platform == "win32":
            return cls.enable_windows_colors()

        if not hasattr(sys.stdout, "isatty") or not sys.stdout.isatty():
            cls._colors_enabled = False
            return False

        term = os.environ.get("TERM", "")
        if term == "dumb" or not term:
            cls._colors_enabled = False
            return False

        cls._colors_enabled = True
        return True

    @classmethod
    def colorize(cls, text: str, *color_codes: str) -> str:
        """Apply color codes to text if colors are supported.

        Args:
            text: The text to colorize.
            *color_codes: One or more color codes to apply.

        Returns:
            Colorized text if supported, plain text otherwise.

        """
        if not cls.is_colors_supported():
            return text

        prefix = "".join(color_codes)
        return f"{prefix}{text}{cls.ENDC}"

    @classmethod
    def strip_colors(cls, text: str) -> str:
        """Remove ANSI color codes from text.

        Args:
            text: Text potentially containing ANSI codes.

        Returns:
            Text with ANSI codes removed.

        """
        import re

        ansi_escape = re.compile(r"\033\[[0-9;]*m")
        return ansi_escape.sub("", text)


def init_colors() -> bool:
    """Initialize color support for the current platform.

    Call this at the start of your CLI application.

    Returns:
        True if colors are supported, False otherwise.

    """
    return Colors.is_colors_supported()


def print_header(text: str) -> None:
    """Print a formatted header with custom styling.

    Args:
        text: The header text to display.

    """
    if Colors.is_colors_supported():
        print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 50}{Colors.ENDC}")
        print(f"{Colors.HEADER}{Colors.BOLD}{text.center(50)}{Colors.ENDC}")
        print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 50}{Colors.ENDC}\n")
    else:
        print(f"\n{'=' * 50}")
        print(f"{text.center(50)}")
        print(f"{'=' * 50}\n")


def print_success(text: str) -> None:
    """Print a success message with custom styling.

    Args:
        text: The success message to display.

    """
    if Colors.is_colors_supported():
        print(f"{Colors.GREEN}{Colors.BOLD}✓ {text}{Colors.ENDC}")
    else:
        print(f"[SUCCESS] {text}")


def print_error(text: str) -> None:
    """Print an error message with custom styling.

    Args:
        text: The error message to display.

    """
    if Colors.is_colors_supported():
        print(f"{Colors.RED}{Colors.BOLD}✗ {text}{Colors.ENDC}")
    else:
        print(f"[ERROR] {text}")


def print_info(text: str) -> None:
    """Print an info message with custom styling.

    Args:
        text: The info message to display.

    """
    if Colors.is_colors_supported():
        print(f"{Colors.BLUE}{Colors.BOLD}ℹ {text}{Colors.ENDC}")
    else:
        print(f"[INFO] {text}")


def print_warning(text: str) -> None:
    """Print a warning message with custom styling.

    Args:
        text: The warning message to display.

    """
    if Colors.is_colors_supported():
        print(f"{Colors.YELLOW}{Colors.BOLD}⚠ {text}{Colors.ENDC}")
    else:
        print(f"[WARNING] {text}")


def print_menu() -> None:
    """Print the interactive menu."""
    print_header("LXMFy Bot Framework")
    if Colors.is_colors_supported():
        print(f"{Colors.CYAN}Available Commands:{Colors.ENDC}")
        print(f"{Colors.BOLD}1.{Colors.ENDC} Create a new bot")
        print(f"{Colors.BOLD}2.{Colors.ENDC} Run a template bot")
        print(f"{Colors.BOLD}3.{Colors.ENDC} Exit")
    else:
        print("Available Commands:")
        print("1. Create a new bot")
        print("2. Run a template bot")
        print("3. Exit")
    print()
