# LXMFy Docs

Documentation for the LXMFy bot framework. Built with Zensical.

Published at https://lxmfy.quad4.io

## Building

```bash
pip install zensical mkdocstrings-python
zensical build   # output in site/
zensical serve   # local preview on http://localhost:8000
```

Translated pages live in `de/`, `es/`, `fr/`, `pt/`, `uk/`, `ru/`, and
`zh/` and are plain page-level translations of the English sources.

Release artifacts (PDF, EPUB, text) for every language are built by
`docs/build-release-docs.sh` and attached to GitHub releases.

The site uses the Quad4 "void" palette (`docs/stylesheets/void.css`) with
a dark scheme as default and a light "paper" scheme behind the palette
toggle.
