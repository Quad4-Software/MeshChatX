import json
import os
import sys


def clear_values(d):
    """Recursively replace all string values with empty strings in a dictionary."""
    if isinstance(d, dict):
        return {k: clear_values(v) for k, v in d.items()}
    return ""


def main():
    # Paths are relative to the workspace root where Taskfile is run
    en_path = os.path.join("meshchatx", "src", "frontend", "locales", "en.json")
    out_path = "locales.json"

    if not os.path.exists(en_path):
        print(f"Error: Source file not found at {en_path}")
        sys.exit(1)

    try:
        with open(en_path, encoding="utf-8") as f:
            en_data = json.load(f)

        template = clear_values(en_data)

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(template, f, indent=4, ensure_ascii=False)

        print(
            f"Successfully generated {out_path} with all keys from {en_path} (empty values).",
        )
    except Exception as e:
        print(f"Error generating locale template: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
