# Reticulum MeshChatX

[English README](../README.md) | [Русский](README.ru.md) | [Italiano](README.it.md) | [中文](README.zh.md) | [日本語](README.ja.md)

Ein umfassend modifizierter und funktionsreicher Fork von Reticulum MeshChat von Liam Cottle.

Dieses Projekt ist unabhaengig vom originalen Reticulum MeshChat und steht in keiner Verbindung dazu.

- Website: [meshchatx.com](https://meshchatx.com)
- Quellcode: [git.quad4.io/RNS-Things/MeshChatX](https://git.quad4.io/RNS-Things/MeshChatX)
- Offizieller Spiegel: [github.com/Sudo-Ivan/MeshChatX](https://github.com/Sudo-Ivan/MeshChatX) – derzeit auch fuer Windows- und macOS-Builds genutzt.
- Releases: [git.quad4.io/RNS-Things/MeshChatX/releases](https://git.quad4.io/RNS-Things/MeshChatX/releases)
- Aenderungsprotokoll: [`CHANGELOG.md`](../CHANGELOG.md)
- TODO: [Boards](https://git.quad4.io/RNS-Things/MeshChatX/projects)

## Wichtige Aenderungen gegenueber Reticulum MeshChat

- Verwendet LXST
- Peewee-ORM durch direktes SQL ersetzt
- Axios durch natives `fetch` ersetzt
- Aktuelles Electron
- `.whl`-Pakete mit Webserver und eingebauten Frontend-Assets fuer mehr Deploy-Optionen
- i18n
- PNPM und Poetry fuer Abhaengigkeiten

> [!WARNING]
> MeshChatX garantiert keine Datenkompatibilitaet mit aelteren Reticulum-MeshChat-Versionen. Erstellen Sie vor Migration oder Tests eine Datensicherung.

> [!WARNING]
> Aeltere Systeme werden noch nicht vollstaendig unterstuetzt. Aktuelle Mindestanforderungen: Python `>=3.11` und Node `>=24`.

## Voraussetzungen

- Python `>=3.11` (aus `pyproject.toml`)
- Node.js `>=24` (aus `package.json`)
- pnpm `10.32.1` (aus `package.json`)
- Poetry (verwendet in `Taskfile.yml` und CI-Workflows)

```bash
task install
task lint:all
task test:all
task build:all
```

## Installationsmethoden

Waehlen Sie die Methode passend zu Umgebung und Paketierung.

| Methode               | Frontend enthalten | Architekturen                         | Geeignet fuer                       |
| --------------------- | ------------------ | ------------------------------------- | ----------------------------------- |
| Docker-Image          | Ja                 | `linux/amd64`, `linux/arm64`          | Schnellster Start auf Linux-Servern |
| Python Wheel (`.whl`) | Ja                 | Jede Python-unterstuetzte Architektur | Headless/Webserver ohne Node-Build  |
| Linux AppImage        | Ja                 | `x64`, `arm64`                        | Portabler Desktop-Einsatz           |
| Debian-Paket (`.deb`) | Ja                 | `x64`, `arm64`                        | Debian/Ubuntu-Installation          |
| RPM-Paket (`.rpm`)    | Ja                 | CI-abhaengig                          | Fedora/RHEL/openSUSE                |
| Aus Quellcode         | Lokal gebaut       | Host-Architektur                      | Entwicklung und individuelle Builds |

Hinweise:

- Der Release-Workflow baut explizit Linux `x64` und `arm64` AppImage + DEB.
- RPM wird ebenfalls versucht und bei Erfolg hochgeladen.

## Schnellstart: Docker

```bash
docker compose up -d
```

Standard-Compose-Datei:

- `127.0.0.1:8000` auf dem Host -> Container-Port `8000`
- `./meshchat-config` -> `/config` fuer Persistenz

Bei Berechtigungsproblemen:

```bash
sudo chown -R 1000:1000 ./meshchat-config
```

## Installation aus Release-Artefakten

### 1) Linux AppImage (x64/arm64)

1. `ReticulumMeshChatX-v<version>-linux-<arch>.AppImage` von den Releases herunterladen.
2. Ausfuehrbar machen und starten:

```bash
chmod +x ./ReticulumMeshChatX-v*-linux-*.AppImage
./ReticulumMeshChatX-v*-linux-*.AppImage
```

### 2) Debian/Ubuntu `.deb` (x64/arm64)

1. `ReticulumMeshChatX-v<version>-linux-<arch>.deb` herunterladen.
2. Installieren:

```bash
sudo apt install ./ReticulumMeshChatX-v*-linux-*.deb
```

### 3) RPM-basierte Systeme

1. `ReticulumMeshChatX-v<version>-linux-<arch>.rpm` herunterladen, falls im Release vorhanden.
2. Installieren:

```bash
sudo rpm -Uvh ./ReticulumMeshChatX-v*-linux-*.rpm
```

### 4) Python Wheel (`.whl`)

Release-Wheels enthalten die gebauten Web-Assets.

```bash
pip install ./reticulum_meshchatx-*-py3-none-any.whl
meshchatx --headless
```

`pipx` wird ebenfalls unterstuetzt:

```bash
pipx install ./reticulum_meshchatx-*-py3-none-any.whl
```

## Aus Quellcode ausfuehren (Webserver-Modus)

Fuer Entwicklung oder lokale Custom-Builds.

```bash
git clone https://git.quad4.io/RNS-Things/MeshChatX.git
cd MeshChatX
corepack enable
pnpm install
pip install poetry
poetry install
pnpm run build-frontend
poetry run python -m meshchatx.meshchat --headless --host 127.0.0.1
```

## Sandboxing (Linux)

Um das native `meshchatx`-Programm (Alias: `meshchat`) mit zusaetzlicher Dateisystem-Isolation auszufuehren, koennen Sie **Firejail** oder **Bubblewrap** (`bwrap`) nutzen, bei weiterhin normalem Netzwerkzugriff fuer Reticulum und die Web-Oberflaeche. Vollstaendige Beispiele (pip/pipx, Poetry, Hinweise zu USB-Seriell) finden Sie in:

- [`docs/meshchatx_linux_sandbox.md`](../docs/meshchatx_linux_sandbox.md)

Dieselbe Seite erscheint in der in-app-**Dokumentation** (MeshChatX-Docs), wenn sie aus den gebuendelten oder synchronisierten `meshchatx-docs`-Dateien ausgeliefert wird.

## Desktop-Pakete aus Quellcode bauen

Diese Skripte sind in `package.json` und `Taskfile.yml` definiert.

### Linux x64 AppImage + DEB

```bash
pnpm run dist:linux-x64
```

### Linux arm64 AppImage + DEB

```bash
pnpm run dist:linux-arm64
```

### RPM

```bash
pnpm run dist:rpm
```

Oder ueber Task:

```bash
task dist:fe:rpm
```

## Architekturunterstuetzung

- Docker: `amd64`, `arm64`
- Linux AppImage: `x64`, `arm64`
- Linux DEB: `x64`, `arm64`
- Windows: `x64`, `arm64` (Build-Skripte vorhanden)
- macOS: Build-Skripte vorhanden (`arm64`, `universal`) fuer lokale Build-Umgebungen
- Android: Projekt und CI-Workflow im Repository enthalten

## Android

- [`docs/meshchatx_on_android_with_termux.md`](../docs/meshchatx_on_android_with_termux.md)
- [`android/README.md`](../android/README.md)

## Konfiguration

| Argument                   | Umgebungsvariable                        | Standard     | Beschreibung                                                                                                                                                                                 |
| -------------------------- | ---------------------------------------- | ------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `--host`                   | `MESHCHAT_HOST`                          | `127.0.0.1`  | Webserver-Bind-Adresse                                                                                                                                                                       |
| `--port`                   | `MESHCHAT_PORT`                          | `8000`       | Webserver-Port                                                                                                                                                                               |
| `--no-https`               | `MESHCHAT_NO_HTTPS`                      | `false`      | HTTPS deaktivieren                                                                                                                                                                           |
| `--ssl-cert` / `--ssl-key` | `MESHCHAT_SSL_CERT` / `MESHCHAT_SSL_KEY` | (keine)      | PEM-Zertifikat und Schluessel; beide setzen. Ueberschreibt automatisch erzeugte Zertifikate unter der Identitaet im Verzeichnis `ssl/`.                                                      |
| `--rns-log-level`          | `MESHCHAT_RNS_LOG_LEVEL`                 | (keine)      | Reticulum (RNS) Log-Level: `none`, `critical`, `error`, `warning`, `notice`, `verbose`, `debug`, `extreme` oder numerisch. CLI ueberschreibt die Umgebungsvariable, wenn beide gesetzt sind. |
| `--headless`               | `MESHCHAT_HEADLESS`                      | `false`      | Browser nicht automatisch oeffnen                                                                                                                                                            |
| `--auth`                   | `MESHCHAT_AUTH`                          | `false`      | Basis-Authentifizierung aktivieren                                                                                                                                                           |
| `--storage-dir`            | `MESHCHAT_STORAGE_DIR`                   | `./storage`  | Datenverzeichnis                                                                                                                                                                             |
| `--public-dir`             | `MESHCHAT_PUBLIC_DIR`                    | auto/bundled | Frontend-Verzeichnis (fuer Installationen ohne gebundelte Assets)                                                                                                                            |

## Branches

| Branch   | Zweck                                                                          |
| -------- | ------------------------------------------------------------------------------ |
| `master` | Stabile Releases. Nur produktionsreifer Code.                                  |
| `dev`    | Aktive Entwicklung. Kann instabile oder unvollstaendige Aenderungen enthalten. |

## Entwicklung

Gaengige Aufgaben aus `Taskfile.yml`:

```bash
task install
task lint:all
task test:all
task build:all
```

`Makefile`-Kurzformen:

| Befehl         | Beschreibung                                  |
| -------------- | --------------------------------------------- |
| `make install` | pnpm- und Poetry-Abhaengigkeiten installieren |
| `make run`     | MeshChatX ueber Poetry starten                |
| `make build`   | Frontend bauen                                |
| `make lint`    | eslint und ruff ausfuehren                    |
| `make test`    | Frontend- und Backend-Tests                   |
| `make clean`   | Build-Artefakte und node_modules entfernen    |

## Versionierung

Aktuelle Version in diesem Repository: `4.4.0`.

- `package.json` ist die Quelle fuer die JavaScript/Electron-Version.
- `meshchatx/src/version.py` wird aus `package.json` synchronisiert mit:

```bash
pnpm run version:sync
```

Fuer konsistente Releases die Versionsfelder dort abgleichen, wo noetig (`package.json`, `pyproject.toml`, `meshchatx/__init__.py`).

## Sicherheit

- [`SECURITY.md`](../SECURITY.md)
- Integrierte Integritaetspruefungen und HTTPS/WSS-Standardeinstellungen in der App
- CI-Scanning-Workflows in `.gitea/workflows/`

## Sprache hinzufuegen

Die Spracherkennung erfolgt automatisch. Um eine neue Sprache hinzuzufuegen, genuegt eine einzige JSON-Datei:

1. Leere Vorlage aus `en.json` erzeugen:

```bash
python scripts/generate_locale_template.py
```

Damit wird `locales.json` mit leeren Strings fuer alle Schluessel geschrieben.

2. Umbenennen und in das Locale-Verzeichnis verschieben:

```bash
mv locales.json meshchatx/src/frontend/locales/xx.json
```

3. `_languageName` am Anfang der Datei auf den nativen Sprachnamen setzen (z.B. `"Espanol"`, `"Francais"`). Wird im Sprachwahlmenue angezeigt.

4. Alle uebrigen Werte uebersetzen.

5. Schluesselparitaet pruefen: `pnpm test -- tests/frontend/i18n.test.js --run`

Keine weiteren Code-Aenderungen noetig. App, Sprachwahl und Tests lesen Locales zur Build-Zeit aus `meshchatx/src/frontend/locales/`.

## Mitwirkende

- [Liam Cottle](https://github.com/liamcottle) - Originales Reticulum MeshChat
- [RFnexus](https://github.com/RFnexus) - Micron-Parser (JavaScript)
- [markqvist](https://github.com/markqvist) - Reticulum, LXMF, LXST
