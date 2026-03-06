# Reticulum MeshChatX

Ein umfassend modifizierter und funktionsreicher Fork von Reticulum MeshChat von Liam Cottle.

Dieses Projekt ist unabhaengig vom originalen Reticulum MeshChat und steht in keiner Verbindung dazu.

- Quellcode: [git.quad4.io/RNS-Things/MeshChatX](https://git.quad4.io/RNS-Things/MeshChatX)
- Releases: [git.quad4.io/RNS-Things/MeshChatX/releases](https://git.quad4.io/RNS-Things/MeshChatX/releases)
- Aenderungsprotokoll: [`CHANGELOG.md`](../CHANGELOG.md)
- [English README](../README.md) | [Русский](README.ru.md) | [Italiano](README.it.md) | [中文](README.zh.md) | [日本語](README.ja.md)

## Wichtige Hinweise

- Volle LXMF-Unterstuetzung ist ein zentrales Projektziel.
- Datenspeicherung und Migrationen werden schrittweise auf reines SQL umgestellt (Ersatz alter Peewee-ORM-Pfade).

> [!WARNING]
> MeshChatX garantiert keine Datenkompatibilitaet mit aelteren Reticulum-MeshChat-Versionen. Erstellen Sie vor Migration oder Tests eine Datensicherung.

> [!WARNING]
> Aeltere Systeme werden noch nicht vollstaendig unterstuetzt. Aktuelle Mindestanforderungen: Python `>=3.11` und Node `>=24`.

## Demo und Screenshots

<video src="https://strg.0rbitzer0.net/raw/62926a2a-0a9a-4f44-a5f6-000dd60deac1.mp4" controls="controls" style="max-width: 100%;"></video>

### Oberflaeche

![Telefon](../screenshots/phone.png)
![Netzwerkvisualisierung](../screenshots/network-visualiser.png)
![Archive](../screenshots/archives.png)
![Identitaeten](../screenshots/identities.png)

## Voraussetzungen

- Python `>=3.11` (aus `pyproject.toml`)
- Node.js `>=24` (aus `package.json`)
- pnpm `10.30.0` (aus `package.json`)
- Poetry (verwendet in `Taskfile.yml` und CI-Workflows)

## Nix (flake.nix)

Das Repository enthaelt einen Nix-Flake unter `flake.nix`.

### Dev-Shell starten

```bash
nix develop
```

### Standard-Nix-Paket bauen

```bash
nix build .#default
```

### Typischer Workflow in `nix develop`

```bash
task install
task lint:all
task test:all
task build:all
```

## Installationsmethoden

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
meshchat --headless
```

`pipx` wird ebenfalls unterstuetzt:

```bash
pipx install ./reticulum_meshchatx-*-py3-none-any.whl
```

## Aus Quellcode ausfuehren (Webserver-Modus)

```bash
git clone https://git.quad4.io/RNS-Things/MeshChatX.git
cd MeshChatX
corepack enable
pnpm install
pip install poetry
poetry install
pnpm run build-frontend
poetry run meshchat --headless --host 127.0.0.1
```

## Desktop-Pakete aus Quellcode bauen

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

## Architekturunterstuetzung

- Docker: `amd64`, `arm64`
- Linux AppImage: `x64`, `arm64`
- Linux DEB: `x64`, `arm64`
- Windows: `x64`, `arm64` (Build-Skripte vorhanden)
- macOS: Build-Skripte vorhanden (`arm64`, `universal`)
- Android: Projekt und CI-Workflow im Repository enthalten

## Android

- [`docs/meshchatx_on_android_with_termux.md`](../docs/meshchatx_on_android_with_termux.md)
- [`android/README.md`](../android/README.md)

## Konfiguration

| Argument        | Umgebungsvariable      | Standard    | Beschreibung                       |
| --------------- | ---------------------- | ----------- | ---------------------------------- |
| `--host`        | `MESHCHAT_HOST`        | `127.0.0.1` | Webserver-Adresse                  |
| `--port`        | `MESHCHAT_PORT`        | `8000`      | Webserver-Port                     |
| `--no-https`    | `MESHCHAT_NO_HTTPS`    | `false`     | HTTPS deaktivieren                 |
| `--headless`    | `MESHCHAT_HEADLESS`    | `false`     | Browser nicht automatisch oeffnen  |
| `--auth`        | `MESHCHAT_AUTH`        | `false`     | Basis-Authentifizierung aktivieren |
| `--storage-dir` | `MESHCHAT_STORAGE_DIR` | `./storage` | Datenverzeichnis                   |
| `--public-dir`  | `MESHCHAT_PUBLIC_DIR`  | auto        | Frontend-Verzeichnis               |

## Entwicklung

```bash
task install
task lint:all
task test:all
task build:all
```

## Sicherheit

- [`SECURITY.md`](../SECURITY.md)
- Integrierte Integritaetspruefungen und HTTPS/WSS-Standardeinstellungen
- CI-Scanning-Workflows in `.gitea/workflows/`

## Mitwirkende

- [Liam Cottle](https://github.com/liamcottle) - Originales Reticulum MeshChat
- [RFnexus](https://github.com/RFnexus) - JavaScript-Micron-Parser
- [markqvist](https://github.com/markqvist) - Reticulum, LXMF, LXST
