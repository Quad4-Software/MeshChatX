# Reticulum MeshChatX

[English](../README.md) | [Deutsch](README.de.md) | [Русский](README.ru.md) | [中文](README.zh.md) | [日本語](README.ja.md)

Un fork ampiamente modificato e ricco di funzionalita di Reticulum MeshChat di Liam Cottle.

Questo progetto e indipendente dal progetto originale Reticulum MeshChat e non e affiliato ad esso.

- Sito web: [meshchatx.com](https://meshchatx.com)
- Codice sorgente: [git.quad4.io/RNS-Things/MeshChatX](https://git.quad4.io/RNS-Things/MeshChatX)
- Mirror ufficiale: [github.com/Sudo-Ivan/MeshChatX](https://github.com/Sudo-Ivan/MeshChatX) — usato anche per le build Windows e macOS al momento.
- Release: [git.quad4.io/RNS-Things/MeshChatX/releases](https://git.quad4.io/RNS-Things/MeshChatX/releases)
- Changelog: [`CHANGELOG.md`](../CHANGELOG.md)
- TODO: [Boards](https://git.quad4.io/RNS-Things/MeshChatX/projects)

## Modifiche importanti rispetto a Reticulum MeshChat

- Usa LXST
- Peewee ORM sostituito con SQL diretto
- Axios sostituito con `fetch` nativo
- Electron aggiornato
- Wheel `.whl` con web server e asset frontend integrati per piu opzioni di deploy
- i18n
- PNPM e Poetry per le dipendenze

> [!WARNING]
> MeshChatX non garantisce la compatibilita dei dati con le versioni precedenti di Reticulum MeshChat. Eseguire un backup prima della migrazione o dei test.

> [!WARNING]
> I sistemi legacy non sono ancora completamente supportati. Requisiti minimi attuali: Python `>=3.11` e Node `>=24`.

## Requisiti

- Python `>=3.11` (da `pyproject.toml`)
- Node.js `>=24` (da `package.json`)
- pnpm `10.32.1` (da `package.json`)
- Poetry (utilizzato in `Taskfile.yml` e nei workflow CI)

```bash
task install
task lint:all
task test:all
task build:all
```

## Metodi di installazione

Scegli il metodo in base all'ambiente e al formato del pacchetto.

| Metodo                    | Include frontend     | Architetture                                | Ideale per                                         |
| ------------------------- | -------------------- | ------------------------------------------- | -------------------------------------------------- |
| Immagine Docker           | Si                   | `linux/amd64`, `linux/arm64`                | Avvio rapido su server Linux                       |
| Python wheel (`.whl`)     | Si                   | Qualsiasi architettura supportata da Python | Installazione headless/web-server senza build Node |
| Linux AppImage            | Si                   | `x64`, `arm64`                              | Uso desktop portatile                              |
| Pacchetto Debian (`.deb`) | Si                   | `x64`, `arm64`                              | Installazione Debian/Ubuntu                        |
| Pacchetto RPM (`.rpm`)    | Si                   | Dipende dal CI                              | Fedora/RHEL/openSUSE                               |
| Da sorgente               | Compilato localmente | Architettura host                           | Sviluppo e build personalizzati                    |

Note:

- Il workflow di release compila esplicitamente Linux `x64` e `arm64` AppImage + DEB.
- RPM viene anche tentato e caricato quando prodotto con successo.

## Avvio rapido: Docker

```bash
docker compose up -d
```

Il file compose predefinito mappa:

- `127.0.0.1:8000` sull'host -> porta `8000` del container
- `./meshchat-config` -> `/config` per la persistenza

In caso di errori di permessi:

```bash
sudo chown -R 1000:1000 ./meshchat-config
```

## Installazione da artefatti di release

### 1) Linux AppImage (x64/arm64)

1. Scaricare `ReticulumMeshChatX-v<versione>-linux-<arch>.AppImage` dalle release.
2. Rendere eseguibile e avviare:

```bash
chmod +x ./ReticulumMeshChatX-v*-linux-*.AppImage
./ReticulumMeshChatX-v*-linux-*.AppImage
```

### 2) Debian/Ubuntu `.deb` (x64/arm64)

1. Scaricare `ReticulumMeshChatX-v<versione>-linux-<arch>.deb`.
2. Installare:

```bash
sudo apt install ./ReticulumMeshChatX-v*-linux-*.deb
```

### 3) Sistemi RPM

1. Scaricare `ReticulumMeshChatX-v<versione>-linux-<arch>.rpm` se presente nella release.
2. Installare:

```bash
sudo rpm -Uvh ./ReticulumMeshChatX-v*-linux-*.rpm
```

### 4) Python wheel (`.whl`)

I wheel delle release includono gli asset web compilati.

```bash
pip install ./reticulum_meshchatx-*-py3-none-any.whl
meshchatx --headless
```

`pipx` e supportato:

```bash
pipx install ./reticulum_meshchatx-*-py3-none-any.whl
```

## Esecuzione da sorgente (modalita web server)

Per sviluppo o build locali personalizzate.

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

## Esecuzione in sandbox (Linux)

Per eseguire il binario nativo `meshchatx` (alias: `meshchat`) con isolamento aggiuntivo del filesystem, puoi usare **Firejail** o **Bubblewrap** (`bwrap`) mantenendo l'accesso di rete normale per Reticulum e l'interfaccia web. Esempi completi (pip/pipx, Poetry, note sulla seriale USB) sono in:

- [`docs/meshchatx_linux_sandbox.md`](../docs/meshchatx_linux_sandbox.md)

La stessa pagina compare nell'elenco **Documentazione** in-app (documentazione MeshChatX) quando viene servita dai file `meshchatx-docs` inclusi o sincronizzati.

## Desktop Linux: font emoji

Il selettore emoji mostra gli emoji Unicode standard usando i font di sistema (Electron/Chromium). Se compaiono quadrati vuoti ("tofu"), installate un pacchetto emoji a colori e riavviate l'app.

| Famiglia (esempi)          | Pacchetto                                                                 |
| -------------------------- | ------------------------------------------------------------------------- |
| Arch Linux, Artix, Manjaro | `noto-fonts-emoji` (`sudo pacman -S noto-fonts-emoji`)                    |
| Debian, Ubuntu             | `fonts-noto-color-emoji` (`sudo apt install fonts-noto-color-emoji`)      |
| Fedora                     | `google-noto-emoji-color-fonts`                                         |

Dopo l'installazione, eseguite `fc-cache -fv` se i glifi non compaiono fino al prossimo accesso. Opzionale: `noto-fonts` per una copertura simboli più ampia su installazioni minime.

## Compilazione pacchetti desktop da sorgente

Gli script sono definiti in `package.json` e `Taskfile.yml`.

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

Oppure tramite Task:

```bash
task dist:fe:rpm
```

## Supporto architetture

- Immagine Docker: `amd64`, `arm64`
- Linux AppImage: `x64`, `arm64`
- Linux DEB: `x64`, `arm64`
- Windows: `x64`, `arm64` (script di build disponibili)
- macOS: script di build disponibili (`arm64`, `universal`) per ambienti di build locali
- Android: APK nativi — `arm64-v8a`, `x86_64`, universale

## Android

MeshChatX supporta build APK Android native (non solo Termux).

### Build APK da sorgente

Dalla root del repository:

```bash
# 1) Build delle wheel Chaquopy usate da android/app/build.gradle
bash scripts/build-android-wheels-local.sh

# 2) Build di entrambe le varianti APK
cd android
./gradlew --no-daemon :app:assembleDebug :app:assembleRelease
```

Output APK (split degli ABI e APK universale; vedere `splits { abi { ... } }` in `android/app/build.gradle`):

Debug (`android/app/build/outputs/apk/debug/`):

- `app-arm64-v8a-debug.apk` (dispositivi ARM64)
- `app-x86_64-debug.apk` (emulatori x86_64)
- `app-universal-debug.apk` (tutti gli ABI inclusi in un unico pacchetto)

Release (`android/app/build/outputs/apk/release/`):

- `app-arm64-v8a-release-unsigned.apk`
- `app-x86_64-release-unsigned.apk`
- `app-universal-release-unsigned.apk`

Note:

- Gli output release sono non firmati di default se non configurate le firme.
- Se serve una sola variante: `:app:assembleDebug` o `:app:assembleRelease`.
- Android punta agli ABI `arm64-v8a` e `x86_64` come in `android/app/build.gradle`.

Documentazione aggiuntiva:

- [`docs/meshchatx_on_android_with_termux.md`](../docs/meshchatx_on_android_with_termux.md)
- [`android/README.md`](../android/README.md)

## Configurazione

| Argomento                  | Variabile d'ambiente                     | Predefinito | Descrizione                                                                                                                                                                                           |
| -------------------------- | ---------------------------------------- | ----------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `--host`                   | `MESHCHAT_HOST`                          | `127.0.0.1` | Indirizzo di bind del web server                                                                                                                                                                      |
| `--port`                   | `MESHCHAT_PORT`                          | `8000`      | Porta del web server                                                                                                                                                                                  |
| `--no-https`               | `MESHCHAT_NO_HTTPS`                      | `false`     | Disattiva HTTPS                                                                                                                                                                                       |
| `--ssl-cert` / `--ssl-key` | `MESHCHAT_SSL_CERT` / `MESHCHAT_SSL_KEY` | (nessuno)   | Percorsi PEM certificato e chiave; impostare entrambi. Sostituisce i certificati auto-generati sotto l'identita nella directory `ssl/`.                                                               |
| `--rns-log-level`          | `MESHCHAT_RNS_LOG_LEVEL`                 | (nessuno)   | Livello di log Reticulum (RNS): `none`, `critical`, `error`, `warning`, `notice`, `verbose`, `debug`, `extreme` o numerico. La CLI ha priorita sulla variabile d'ambiente se entrambe sono impostate. |
| `--headless`               | `MESHCHAT_HEADLESS`                      | `false`     | Non aprire il browser automaticamente                                                                                                                                                                 |
| `--auth`                   | `MESHCHAT_AUTH`                          | `false`     | Attiva autenticazione base                                                                                                                                                                            |
| `--storage-dir`            | `MESHCHAT_STORAGE_DIR`                   | `./storage` | Directory dei dati                                                                                                                                                                                    |
| `--public-dir`             | `MESHCHAT_PUBLIC_DIR`                    | auto/bundle | Directory dei file frontend (per installazioni senza asset inclusi)                                                                                                                                   |

## Branch

| Branch   | Scopo                                                                 |
| -------- | --------------------------------------------------------------------- |
| `master` | Release stabili. Solo codice pronto per la produzione.                |
| `dev`    | Sviluppo attivo. Potrebbe contenere modifiche instabili o incomplete. |

## Sviluppo

Attivita comuni da `Taskfile.yml`:

```bash
task install
task lint:all
task test:all
task build:all
```

Scorciatoie `Makefile`:

| Comando        | Descrizione                               |
| -------------- | ----------------------------------------- |
| `make install` | Installa dipendenze pnpm e poetry         |
| `make run`     | Esegue MeshChatX tramite poetry           |
| `make build`   | Compila il frontend                       |
| `make lint`    | Esegue eslint e ruff                      |
| `make test`    | Test frontend e backend                   |
| `make clean`   | Rimuove artefatti di build e node_modules |

## Versioning

Versione attuale nel repository: `4.5.0`.

- La fonte della versione JavaScript/Electron e `package.json`.
- `meshchatx/src/version.py` e sincronizzato da `package.json` con:

```bash
pnpm run version:sync
```

Per release coerenti, allineare i campi di versione dove richiesto (`package.json`, `pyproject.toml`, `meshchatx/__init__.py`).

## Sicurezza

- [`SECURITY.md`](../SECURITY.md)
- Controlli di integrita integrati e HTTPS/WSS predefiniti nell'app
- Workflow di scansione CI in `.gitea/workflows/`

## Aggiungere una lingua

Il rilevamento delle lingue e automatico. Per aggiungere una nuova lingua basta un singolo file JSON:

1. Generare un modello vuoto da `en.json`:

```bash
python scripts/generate_locale_template.py
```

Scrive `locales.json` con ogni chiave impostata a stringa vuota.

2. Rinominare e spostare nella cartella delle lingue:

```bash
mv locales.json meshchatx/src/frontend/locales/xx.json
```

3. Impostare `_languageName` all'inizio del file con il nome nativo della lingua (es. `"Espanol"`, `"Francais"`). Viene mostrato nel selettore lingua.

4. Tradurre tutti i valori rimanenti.

5. Verificare la corrispondenza delle chiavi: `pnpm test -- tests/frontend/i18n.test.js --run`

Nessun altra modifica al codice e necessaria. App, selettore lingua e test scoprono le lingue in `meshchatx/src/frontend/locales/` al momento della build.

## Crediti

- [Liam Cottle](https://github.com/liamcottle) - Reticulum MeshChat originale
- [RFnexus](https://github.com/RFnexus) - Parser Micron (JavaScript)
- [markqvist](https://github.com/markqvist) - Reticulum, LXMF, LXST
