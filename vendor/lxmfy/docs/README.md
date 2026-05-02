# LXMFy Docs

Docs for the LXMFy bot framework. Built using Sphinx and Furo theme.

## Building

```bash
poetry install --with dev

# Build English documentation (HTML, EPUB, PDF, Text)
make html
make epub
make latexpdf
make text

# Build Russian documentation
make html-ru
make epub-ru
make latexpdf-ru
make text-ru

# Build documentation for any language (replace XX with language code)
make html-XX epub-XX latexpdf-XX text-XX

# Build all formats for all languages (English + all in locales/)
# The Gitea Actions CI does this automatically
```

## Running

```bash
make serve
```

## Docker

### Local/Development (BusyBox)

```bash
docker build -t lxmfy-docs .
docker run -p 8080:8080 lxmfy-docs
```

### Production (Nginx)

```bash
docker build -f Dockerfile.prod -t lxmfy-docs:prod .
docker run -p 8080:8080 lxmfy-docs:prod
```

If using Podman, replace `docker` with `podman`.

## Translations

### How to Add or Update Translations

1.  **Generate translation templates:**
    ```bash
    make pot
    ```

2.  **For a new language (e.g., `fr` for French):**
    ```bash
    # Create directory structure
    mkdir -p locales/fr/LC_MESSAGES

    # Copy and rename template files
    cp build/gettext/*.pot locales/fr/LC_MESSAGES/
    rename 's/\.pot$/.po/' locales/fr/LC_MESSAGES/*.pot

    # Translate the msgstr fields in the .po files
    ```

3.  **For existing languages (update translations):**
    ```bash
    # Edit locales/*/LC_MESSAGES/*.po files to update translations
    ```

4.  **Build the translated documentation:**
    ```bash
    # Build all formats for your language (replace XX with language code)
    make html-XX epub-XX latexpdf-XX text-XX

    # Gitea Actions automatically builds all languages and formats
    ```

**Note:** The system automatically detects all languages in `locales/` and builds all formats for them. Adding a new language requires only creating the translation files - no workflow changes needed!
