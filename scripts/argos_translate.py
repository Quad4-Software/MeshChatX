#!/usr/bin/env python3
"""Argos Translate JSON localization script.

This script provides an automated workflow to translate JSON localization files
(such as `en.json`) to target languages using Argos Translate. It ensures that
interpolated variables (e.g., `{count}`, `{status}`) are preserved and not
altered during the translation process.

Requirements:
    - argostranslate (pip install argostranslate)

Usage:
    python scripts/argos_translate.py --from en --to zh --input locales/en.json --output locales/zh.json

    You can also use environment variables instead of CLI flags:
    ARGOS_FROM_LANG="en"
    ARGOS_TO_LANG="zh"
    ARGOS_INPUT_FILE="locales/en.json"
    ARGOS_OUTPUT_FILE="locales/zh.json"
"""

import argparse
import json
import os
import re
import sys
import time


# ANSI color codes for terminal output
class Colors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


def print_info(msg):
    print(f"{Colors.OKCYAN}[INFO]{Colors.ENDC} {msg}")


def print_success(msg):
    print(f"{Colors.OKGREEN}[SUCCESS]{Colors.ENDC} {msg}")


def print_warning(msg):
    print(f"{Colors.WARNING}[WARNING]{Colors.ENDC} {msg}")


def print_error(msg):
    print(f"{Colors.FAIL}[ERROR]{Colors.ENDC} {msg}")


try:
    import argostranslate.package
    import argostranslate.translate
except ImportError:
    print_error("The 'argostranslate' module is not installed.")
    print_info("Please install it using: pip install argostranslate")
    sys.exit(1)


def ensure_package_installed(from_code, to_code):
    """Ensure the translation package from `from_code` to `to_code` is installed.

    If not installed, attempts to download and install it automatically.
    """
    installed = argostranslate.translate.get_installed_languages()
    installed_dict = {lang.code: lang for lang in installed}

    from_lang = installed_dict.get(from_code)
    to_lang = installed_dict.get(to_code)

    if not from_lang or not to_lang or to_lang not in from_lang.translations_from:
        print_warning(
            f"Translation package {from_code} -> {to_code} not found. Attempting to install..."
        )
        try:
            argostranslate.package.update_package_index()
            available_packages = argostranslate.package.get_available_packages()

            pkg_to_install = None
            for pkg in available_packages:
                if pkg.from_code == from_code and pkg.to_code == to_code:
                    pkg_to_install = pkg
                    break

            if pkg_to_install:
                print_info(f"Downloading package: {pkg_to_install}")
                argostranslate.package.install_from_path(pkg_to_install.download())
                print_success(
                    f"Successfully installed package: {from_code} -> {to_code}"
                )

                # Refresh installed languages
                installed = argostranslate.translate.get_installed_languages()
                installed_dict = {lang.code: lang for lang in installed}
            else:
                print_error(
                    f"Could not find a translation package for {from_code} -> {to_code}"
                )
                sys.exit(1)
        except Exception as e:
            print_error(f"Failed to install language package: {e}")
            sys.exit(1)

    return installed_dict.get(from_code), installed_dict.get(to_code)


def get_translation_func(from_code, to_code):
    """Returns a translation function for the specified language pair."""
    from_lang, to_lang = ensure_package_installed(from_code, to_code)
    translator = from_lang.get_translation(to_lang)
    if not translator:
        print_error(f"No translation available from {from_code} to {to_code}")
        sys.exit(1)
    return translator.translate


def replace_vars_with_tokens(text):
    """Replaces `{variable}` patterns with a standard token like `XVAR0X`.

    So the translation engine doesn't attempt to translate variable names.
    Returns the modified text and the list of found variables.
    """
    vars_found = []

    def replacer(match):
        vars_found.append(match.group(0))
        return f" XVAR{len(vars_found) - 1}X "

    replaced_text = re.sub(r"\{+.*?\}+", replacer, text)
    return replaced_text, vars_found


def restore_vars_from_tokens(text, vars_found):
    """Restores the original `{variable}` patterns back into the translated text.

    Looks for the `XVAR0X` tokens.
    """
    for i, var in enumerate(vars_found):
        # The translation engine might change case or spacing around the token
        text = re.sub(rf"\s*[xX][vV][aA][rR]{i}[xX]\s*", var, text)
    return text.strip()


def translate_dict(data, translate_func, target_name=None):
    """Recursively iterates over a dictionary and translates all string values.

    Skips the `_languageName` key, which can be explicitly set.
    """
    if isinstance(data, dict):
        new_dict = {}
        for k, v in data.items():
            if k == "_languageName" and target_name:
                new_dict[k] = target_name
                continue
            elif k == "_languageName":
                # Keep original if no target name provided
                new_dict[k] = v
                continue

            new_dict[k] = translate_dict(v, translate_func, target_name)
        return new_dict
    elif isinstance(data, list):
        return [translate_dict(item, translate_func, target_name) for item in data]
    elif isinstance(data, str):
        if not data.strip():
            return data

        temp_text, vars_found = replace_vars_with_tokens(data)
        try:
            translated_temp = translate_func(temp_text)
            return restore_vars_from_tokens(translated_temp, vars_found)
        except Exception as e:
            print_warning(
                f"Failed to translate '{data}': {e}. Falling back to original."
            )
            return data
    else:
        return data


def main():
    parser = argparse.ArgumentParser(
        description="Translate JSON localization files using Argos Translate."
    )
    parser.add_argument(
        "--from", dest="from_lang", help="Source language code (e.g. 'en')"
    )
    parser.add_argument("--to", dest="to_lang", help="Target language code (e.g. 'zh')")
    parser.add_argument("--input", dest="input_file", help="Path to input JSON file")
    parser.add_argument("--output", dest="output_file", help="Path to output JSON file")
    parser.add_argument(
        "--name",
        dest="target_name",
        help="Native name of the target language (e.g. '中文' for Chinese)",
    )

    args = parser.parse_args()

    # Fallback to Environment Variables if arguments aren't provided
    from_lang = args.from_lang or os.environ.get("ARGOS_FROM_LANG")
    to_lang = args.to_lang or os.environ.get("ARGOS_TO_LANG")
    input_file = args.input_file or os.environ.get("ARGOS_INPUT_FILE")
    output_file = args.output_file or os.environ.get("ARGOS_OUTPUT_FILE")
    target_name = args.target_name or os.environ.get("ARGOS_TARGET_NAME")

    if not all([from_lang, to_lang, input_file, output_file]):
        parser.print_help()
        print_error(
            "Missing required arguments. Please provide --from, --to, --input, and --output."
        )
        sys.exit(1)

    if not os.path.exists(input_file):
        print_error(f"Input file not found: {input_file}")
        sys.exit(1)

    print_info(f"Source Language: {Colors.BOLD}{from_lang}{Colors.ENDC}")
    print_info(f"Target Language: {Colors.BOLD}{to_lang}{Colors.ENDC}")
    print_info(f"Input File:      {Colors.BOLD}{input_file}{Colors.ENDC}")
    print_info(f"Output File:     {Colors.BOLD}{output_file}{Colors.ENDC}")

    # Load JSON
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            source_data = json.load(f)
    except json.JSONDecodeError as e:
        print_error(f"Invalid JSON in input file: {e}")
        sys.exit(1)

    start_time = time.time()

    # Get Translator
    translate_func = get_translation_func(from_lang, to_lang)

    print_info(
        "Starting translation. This may take a moment depending on the file size..."
    )
    translated_data = translate_dict(source_data, translate_func, target_name)

    # Ensure output directory exists
    os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)

    # Save translated JSON
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(translated_data, f, ensure_ascii=False, indent=4)
            f.write("\n")
    except IOError as e:
        print_error(f"Could not write to output file: {e}")
        sys.exit(1)

    elapsed_time = time.time() - start_time
    print_success(f"Translation complete in {elapsed_time:.2f} seconds!")
    print_success(f"Output saved to {Colors.BOLD}{output_file}{Colors.ENDC}")


if __name__ == "__main__":
    main()
