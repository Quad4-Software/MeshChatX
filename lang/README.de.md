# Reticulum MeshChatX

[English](../README.md) | [Русский](README.ru.md) | [Italiano](README.it.md) | [中文](README.zh.md) | [日本語](README.ja.md)

Ein umfassend modifizierter und funktionsreicher Fork von Reticulum MeshChat von Liam Cottle.

Dieses Projekt ist unabhaengig vom originalen Reticulum MeshChat und steht in keiner Verbindung dazu.

- Website: [meshchatx.com](https://meshchatx.com)
- Quellcode: [git.quad4.io/RNS-Things/MeshChatX](https://git.quad4.io/RNS-Things/MeshChatX)
- Offizielles GitHub-Mirror: [github.com/Quad4-Software/MeshChatX](https://github.com/Quad4-Software/MeshChatX)
- Releases: [github.com/Quad4-Software/MeshChatX](https://github.com/Quad4-Software/MeshChatX)
- Aenderungsprotokoll: [`CHANGELOG.md`](../CHANGELOG.md)

rngit: `git clone rns://926baefe13daf5178c174f158dae1b45/quad4/MeshChatX`
NomadNet Node: `c10d80b1a42fa958c37a6cc30dc04f53:/page/index.mu`

## Wichtige Aenderungen gegenueber Reticulum MeshChat

- Verwendet LXST fuer Anrufe
- Peewee-ORM durch direktes SQL ersetzt
- Axios durch natives `fetch` ersetzt
- Electron 41.x (mit Node-24-Laufzeit)
- `.whl`-Pakete mit Webserver und eingebauten Frontend-Assets fuer mehr Deploy-Optionen
- i18n
- PNPM und Poetry fuer Abhaengigkeiten

> [!WARNING]
> MeshChatX garantiert keine Datenkompatibilitaet mit aelteren Reticulum-MeshChat-Versionen. Erstellen Sie vor Migration oder Tests eine Datensicherung.

> [!WARNING]
> Aeltere Systeme werden noch nicht unterstuetzt. Aktuelle Basis: Python `>=3.11` und Node `>=24` (Electron 41 entspricht Node 24; `engines` in `package.json` und CI folgen derselben Linie).

## Voraussetzungen

- Python `>=3.11` (aus `pyproject.toml`)
- Node.js `>=24` (aus `package.json`, Feld `engines`)
- pnpm `10.33.0` (aus `package.json`, Feld `packageManager`)
- Poetry (verwendet in `Taskfile.yml` und CI-Workflows)

```bash
task install
task lint:all
task test:all
task build:all
```

## Installationsmethoden

Waehlen Sie die Methode passend zu Umgebung und Paketierung.

| Methode               | Frontend enthalten | Architekturen                               | Geeignet fuer                       |
| --------------------- | ------------------ | ------------------------------------------- | ----------------------------------- |
| Docker-Image          | Ja                 | `linux/amd64`, `linux/arm64`                | Schnellster Start auf Linux-Servern |
| Python Wheel (`.whl`) | Ja                 | Jede Python-unterstuetzte Architektur       | Headless/Webserver ohne Node-Build  |
| Linux AppImage        | Ja                 | `x64`, `arm64`                              | Portabler Desktop-Einsatz           |
| Debian-Paket (`.deb`) | Ja                 | `x64`, `arm64`                              | Debian/Ubuntu-Installation          |
| RPM-Paket (`.rpm`)    | Ja                 | Vom CI-Runner abhaengig (Veroeffentlichung) | Fedora/RHEL/openSUSE                |
| Aus Quellcode         | Lokal gebaut       | Host-Architektur                            | Entwicklung und individuelle Builds |

Hinweise:

- GitHub Actions baut getaggte Releases: Windows und macOS in `.github/workflows/build-release.yml`, Linux Wheel/AppImage/deb/rpm in `.github/workflows/build-linux-release.yml` und das Container-Image in `.github/workflows/docker.yml`.
- Linux `x64` und `arm64` AppImage + DEB werden auf GitHub gebaut; RPM wird versucht und hochgeladen, wenn es erzeugt wird.

## Docker

- **Docker Hub:** `quad4io/meshchatx`
- **GHCR:** `ghcr.io/quad4-software/meshchatx`

```bash
docker compose up -d
```

```bash
docker run -d --name reticulum-meshchatx \
  --restart unless-stopped \
  --security-opt no-new-privileges:true \
  -p 127.0.0.1:8000:8000 \
  -v "$(pwd)/meshchat-config:/config" \
  ghcr.io/quad4-software/meshchatx:latest
```

Sie koennen `quad4io/meshchatx:latest` statt des GHCR-Images verwenden, wenn Sie Docker Hub bevorzugen.

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
pnpm config set verify-store-integrity true
pnpm install --frozen-lockfile
pip install "poetry==2.3.4"
poetry check --lock
poetry install
pnpm run build-frontend
poetry run python -m meshchatx.meshchat --headless --host 127.0.0.1
```

Hinweise zu den Installationsbefehlen:

- `pnpm install --frozen-lockfile` verweigert Aenderungen an `pnpm-lock.yaml` und schlaegt fehl, wenn die Lockdatei nicht zu `package.json` passt. Damit wird verhindert, dass eine unerwartete Upstream-Version still eingespielt wird.
- `verify-store-integrity=true` ist auch in der projektweiten `.npmrc` gesetzt; die explizite `pnpm config set`-Zeile haertet zusaetzlich die Benutzerkonfiguration.
- Lifecycle-Skripte (`preinstall`/`postinstall`) sind in pnpm v10+ standardmaessig blockiert. Nur die unter `pnpm.onlyBuiltDependencies` in `package.json` aufgefuehrten Pakete duerfen Installationsskripte ausfuehren (aktuell `electron`, `electron-winstaller`, `esbuild`).
- `poetry check --lock` schlaegt frueh fehl, wenn `poetry.lock` nicht mit `pyproject.toml` synchron ist; `poetry install` aufloest danach nur aus der Lockdatei.
- Fuer eine strikte Lockfile-Installation (ohne implizite Lock-Aktualisierung) Poetry mit `pip install "poetry==2.3.4"` pinnen, passend zur CI-Version.

Wenn Sie absichtlich Abhaengigkeiten aktualisieren wollen, fuehren Sie `pnpm update` / `poetry update` in einem dedizierten Commit aus und pruefen Sie das resultierende Lockdatei-Diff vor dem Push.

## Sandboxing (Linux)

Um das native `meshchatx`-Programm (Alias: `meshchat`) mit zusaetzlicher Dateisystem-Isolation auszufuehren, koennen Sie **Firejail** oder **Bubblewrap** (`bwrap`) nutzen, bei weiterhin normalem Netzwerkzugriff fuer Reticulum und die Web-Oberflaeche. Vollstaendige Beispiele (pip/pipx, Poetry, Hinweise zu USB-Seriell) finden Sie in:

- [`docs/meshchatx_linux_sandbox.md`](../docs/meshchatx_linux_sandbox.md)

Dieselbe Seite erscheint in der in-app-Liste **Dokumentation** (MeshChatX-Dokumentation), wenn sie aus den gebuendelten oder synchronisierten `meshchatx-docs`-Dateien ausgeliefert wird.

## Linux-Desktop: Emoji-Schriften

Die Emoji-Auswahl rendert Standard-Unicode-Emoji mit den Systemschriften (Electron/Chromium). Wenn Emoji als leere Kaestchen („Tofu“) erscheinen, installieren Sie ein Farb-Emoji-Paket und starten Sie die App neu.

| Distribution (Beispiele)   | Paket                                                                |
| -------------------------- | -------------------------------------------------------------------- |
| Arch Linux, Artix, Manjaro | `noto-fonts-emoji` (`sudo pacman -S noto-fonts-emoji`)               |
| Debian, Ubuntu             | `fonts-noto-color-emoji` (`sudo apt install fonts-noto-color-emoji`) |
| Fedora                     | `google-noto-emoji-color-fonts`                                      |

Nach der Installation bei Bedarf `fc-cache -fv` ausfuehren. Optional: `noto-fonts` fuer breitere Symbolabdeckung bei minimalen Installationen.

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

## Container-Build (Wheel, AppImage, deb, rpm)

`Dockerfile.build` fuehrt die gleichen Schritte wie die CI aus (Poetry, pnpm, `task`, APT-Paketabhaengigkeiten). Ausgelegt auf **linux/amd64** (NodeSource amd64, Task amd64). Standardziel ist alles; per Build-Arg ueberschreibbar.

Werte fuer `MESHCHATX_BUILD_TARGETS`: `all` (Standard), `wheel` oder `electron` (AppImage + deb fuer x64 und arm64, RPM best-effort, kein wheel).

Build:

```bash
docker build -f Dockerfile.build -t meshchatx-build:local .
```

Nur Wheel:

```bash
docker build -f Dockerfile.build --build-arg MESHCHATX_BUILD_TARGETS=wheel -t meshchatx-build:wheel .
```

`/artifacts` aus dem fertigen Image auf den Host kopieren:

```bash
cid=$(docker create meshchatx-build:local)
docker cp "${cid}:/artifacts" ./meshchatx-artifacts
docker rm "${cid}"
```

## Architekturunterstuetzung

- Docker-Image: `amd64`, `arm64`
- Linux AppImage: `x64`, `arm64`
- Linux DEB: `x64`, `arm64`
- Windows: `x64`, `arm64` (Build-Skripte vorhanden)
- macOS: Build-Skripte vorhanden (`arm64`, `universal`) fuer lokale Build-Umgebungen
- Android: native APKs — ABIs `arm64-v8a`, `x86_64`, `armeabi-v7a` (32-bit ARM), plus universal

## Android

MeshChatX unterstuetzt native Android-APK-Builds (nicht nur Termux).

### APKs aus Quellcode bauen

Vom Repository-Root:

```bash
# 1) Chaquopy-Wheels gemaess android/app/build.gradle bauen
bash scripts/build-android-wheels-local.sh

# 2) Universal-APK bauen (ein Debug + ein Release pro Lauf; siehe android/README.md)
cd android
./gradlew --no-daemon :app:assembleDebug :app:assembleRelease
```

**Eine** Android-Variante. Gradle synchronisiert den gesamten `meshchatx/`-Ordner nach `app/src/main/python/meshchatx/`, inklusive Offline-Repository-Raeder. **ABI-Verpackung:** `universal` (Standard) oder `split` (siehe `android/app/build.gradle`).

Bei **`-PmeshchatxAbiPackaging=universal`** (Standard) liefert jeder Buildtyp ein APK mit allen gewaehlten ABIs:

- Debug: `android/app/build/outputs/apk/debug/app-debug.apk`
- Release: `android/app/build/outputs/apk/release/app-release-unsigned.apk`

Bei **`-PmeshchatxAbiPackaging=split`** und mehr als einem ABI in `-PmeshchatxAbis` koennen pro-ABI-APKs entstehen, wie in [`android/README.md`](../android/README.md) beschrieben.

Hinweise:

- Release-Builds sind standardmaessig unsigniert, bis die Signatur konfiguriert ist (`scripts/sign-android-apks.sh`).
- Android richtet sich nach den in `android/app/build.gradle` gelisteten ABIs (einschliesslich `armeabi-v7a`, falls aktiviert). Das Bauen von Radern fuer `armeabi-v7a` erfordert ein Android-SDK in `ANDROID_HOME` (siehe `android/README.md`).
- ABI-Liste: `-PmeshchatxAbis` oder `MESHCHATX_ABIS`. Verpackung: `-PmeshchatxAbiPackaging=universal|split` oder `MESHCHATX_ABI_PACKAGING`.
- Existiert im Repo-Root `dist/reticulum_meshchatx-*.whl` (z. B. nach `python -m build --wheel -o dist .`), bevorzugt die Aktualisierung des Offline-Repositorys dieses Wheel gegueber PyPI. In der CI wird das Wheel vor dem Android-Gradle-Schritt gebaut.

Weitere Dokumentation:

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
| `--public-dir`             | `MESHCHAT_PUBLIC_DIR`                    | auto/bundled | Frontend-Verzeichnis (fuer Quell-Installationen ohne gebundelte Assets)                                                                                                                      |

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

Aktuelle Version in diesem Repository: `4.6.0`.

- Fuer Release-Bumps bearbeiten Sie **nur** `version` in **`package.json`**.
- **`pnpm run version:sync`** (wird auch zu Beginn von **`pnpm run build`** ausgefuehrt) verbreitet diese Version in **`pyproject.toml`**, **`meshchatx/src/version.py`**, **`THIRD_PARTY_NOTICES.txt`** (Produktzeile), **README** / **lang/README.\*** (Zeilen mit aktueller Version), **`docs/meshchatx_on_raspberry_pi.md`** (pipx-Beispiel) und Hilfsfelder in **`packaging/arch/PKGBUILD`**.
- **`meshchatx.__version__`** wird aus **`meshchatx/src/version.py`** gelesen, ohne `meshchatx.src` zu importieren, damit ein normales `import meshchatx` leicht bleibt.
- **Changelog**-Eintrage bleiben beim Release manuell.

## Sicherheit

- [`SECURITY.md`](../SECURITY.md)
- [`LEGAL.md`](../LEGAL.md)
- Eingebaute Integritaetspruefungen und HTTPS/WSS-Standardwerte in der App-Laufzeit.
- CI- und Release-Builds in GitHub Actions.

## Sprache hinzufuegen

Arbeitsablauf des Autors: ArgosTranslate, dann lokales LLM (Qwen 3 + Gemma 4).

Korrekturen von der Community sind willkommen — per LXMF oder wo Sie erreichbar sind.

Die Locale-Erkennung erfolgt automatisch. Fuegen Sie Dateien unter `meshchatx/src/frontend/locales/` hinzu (z. B. `xx.json`) mit denselben Schluesseln wie `en.json` und oberstes `_languageName` fuer die Sprachauswahl. Sie koennen `en.json` kopieren und alles manuell uebersetzen; **maschinenunterstuetzte Erzeugung (optional)** ist niemals erforderlich.

**Optional: Argos-Translate-Start** — fuer einen Entwurf aus `en.json` koennen Sie `scripts/argos_translate.py` nutzen; es behandelt Formatierung, farbige Ausgabe und schuetzt z. B. `{count}`.

```bash
# argostranslate ggf. installieren
pipx install argostranslate

# Uebersetzungsskript ausfuehren
python scripts/argos_translate.py --from en --to xx --input meshchatx/src/frontend/locales/en.json --output meshchatx/src/frontend/locales/xx.json --name "Ihr Sprachname"
```

Nach jeder maschinellen Runde Grammatik, Kontext und Ton (formell vs. informell) mit LLM oder Mensch pruefen.

`pnpm test -- tests/frontend/i18n.test.js --run` prueft die Schluesselparitaet mit `en.json`.

Keine weiteren Code-Aenderungen noetig. App, Sprachwahl und Tests lesen Locales zur Build-Zeit aus `meshchatx/src/frontend/locales/`.

## Mitwirkende

- [Liam Cottle](https://github.com/liamcottle) - Originales Reticulum MeshChat
- [RFnexus](https://github.com/RFnexus) - micron-Parser (JavaScript)
- [markqvist](https://github.com/markqvist) - Reticulum, LXMF, LXST

## Lizenz

Die projekt-eigenen Anteile stehen unter 0BSD.
Urspruengliche Upstream-Anteile von Reticulum MeshChat bleiben unter MIT.
Vollstaendiger Text und Hinweise in [`../LICENSE`](../LICENSE).
