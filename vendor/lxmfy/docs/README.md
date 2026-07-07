# LXMFy Docs

Documentation for the LXMFy bot framework. Built with Sphinx and the Furo theme.

**Published docs:** https://lxmfy.quad4.io

**Languages:** English (source) and Russian (`locales/ru/`).

## Building

```bash
poetry install --with dev

# English (default)
make html
make epub
make latexpdf
make text

# Russian
make html-ru
make epub-ru
make latexpdf-ru
make text-ru

# Any language in locales/ (replace XX with language code)
make html-XX epub-XX latexpdf-XX text-XX
```

CI builds all formats for English and every language under `locales/`.

## Running locally

```bash
make serve
```

Serves English HTML at http://localhost:8000. For Russian, open `build/html/ru/index.html` after `make html-ru`.

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

Source files live in `source/` (reStructuredText). Translations are gettext `.po` files in `locales/<lang>/LC_MESSAGES/`.

### Update existing translations

1. Edit English sources in `source/`.
2. Extract strings:

   ```bash
   make pot
   ```

3. Merge into existing `.po` files:

   ```bash
   msgmerge --update locales/ru/LC_MESSAGES/creating-bots.po build/gettext/creating-bots.pot
   msgmerge --update locales/ru/LC_MESSAGES/api-reference.po build/gettext/api-reference.pot
   msgmerge --update locales/ru/LC_MESSAGES/quick-start.po build/gettext/quick-start.pot
   msgmerge --update locales/ru/LC_MESSAGES/index.po build/gettext/index.pot
   ```

4. Translate new or changed `msgstr` entries in the `.po` files.
5. Validate:

   ```bash
   msgfmt --check locales/ru/LC_MESSAGES/*.po
   ```

6. Build and review:

   ```bash
   make html-ru
   ```

### Add a new language

1. Run `make pot`.
2. Create `locales/<lang>/LC_MESSAGES/`.
3. Copy each `build/gettext/*.pot` to `locales/<lang>/LC_MESSAGES/*.po`.
4. Set `Language: <lang>` in each `.po` header and translate all `msgstr` fields.
5. Add the language to `source/index.rst` under **Languages**.
6. Build with `make html-<lang>`.

Adding a language only requires translation files and an index link; CI picks up new `locales/` entries automatically.
