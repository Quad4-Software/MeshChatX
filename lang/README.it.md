# Reticulum MeshChatX

[English](../README.md) | [Deutsch](README.de.md) | [Русский](README.ru.md) | [中文](README.zh.md) | [日本語](README.ja.md)

Un fork ampiamente modificato e ricco di funzionalita di Reticulum MeshChat di Liam Cottle.

Questo progetto e indipendente dal progetto originale Reticulum MeshChat e non e affiliato ad esso.

- Sito web: [meshchatx.com](https://meshchatx.com)
- Codice sorgente: [git.quad4.io/RNS-Things/MeshChatX](https://git.quad4.io/RNS-Things/MeshChatX)
- Mirror ufficiale su GitHub: [github.com/Quad4-Software/MeshChatX](https://github.com/Quad4-Software/MeshChatX)
- Release: [github.com/Quad4-Software/MeshChatX](https://github.com/Quad4-Software/MeshChatX)
- Changelog: [`CHANGELOG.md`](../CHANGELOG.md)
- Donazioni: [`donate.md`](../donate.md)

<a href="https://apps.obtainium.imranr.dev/redirect.html?r=obtainium://add/https://github.com/Quad4-Software/MeshChatX"><img src="https://raw.githubusercontent.com/ImranR98/Obtainium/main/assets/graphics/badge_obtainium.png" height="60" alt="Get it on Obtainium"></a>

rngit: `git clone rns://926baefe13daf5178c174f158dae1b45/quad4/MeshChatX`
NomadNet Node: `c10d80b1a42fa958c37a6cc30dc04f53:/page/index.mu`

## Modifiche importanti rispetto a Reticulum MeshChat

- Usa LXST per le chiamate
- Peewee ORM sostituito con SQL diretto
- Axios sostituito con `fetch` nativo
- Electron 41.x (runtime Node 24 incluso)
- Wheel `.whl` con web server e asset frontend integrati per piu opzioni di deploy
- i18n
- PNPM e Poetry per le dipendenze

> [!WARNING]
> MeshChatX non garantisce la compatibilita dei dati con le versioni precedenti di Reticulum MeshChat. Eseguire un backup prima della migrazione o dei test.

> [!WARNING]
> I sistemi legacy non sono ancora supportati. Base attuale: Python `>=3.11` e Node `>=24` (Electron 41 allineato a Node 24; `engines` in `package.json` e la CI seguono la stessa linea).

## Requisiti

- Python `>=3.11` (da `pyproject.toml`)
- Node.js `>=24` (da `package.json`, campo `engines`)
- pnpm `10.33.0` (da `package.json`, campo `packageManager`)
- Poetry (utilizzato in `Taskfile.yml` e nei workflow CI)

**Browser Versions Required:**

Safari 16.4 o successivo, Chrome 111 o successivo, Firefox 128 o successivo (interfaccia web integrata).

```bash
task install
task lint:all
task test:all
task build:all
```

## Metodi di installazione

Scegli il metodo in base all'ambiente e al formato del pacchetto.

| Metodo                    | Include frontend     | Architetture                                     | Ideale per                                         |
| ------------------------- | -------------------- | ------------------------------------------------ | -------------------------------------------------- |
| Immagine Docker           | Si                   | `linux/amd64`, `linux/arm64`                     | Avvio rapido su server Linux                       |
| Python wheel (`.whl`)     | Si                   | Qualsiasi architettura supportata da Python      | Installazione headless/web-server senza build Node |
| Linux AppImage            | Si                   | `x64`, `arm64`                                   | Uso desktop portatile                              |
| Pacchetto Debian (`.deb`) | Si                   | `x64`, `arm64`                                   | Installazione Debian/Ubuntu                        |
| Pacchetto RPM (`.rpm`)    | Si                   | Dipende dal runner CI per l'artefatto pubblicato | Fedora/RHEL/openSUSE                               |
| Da sorgente               | Compilato localmente | Architettura host                                | Sviluppo e build personalizzati                    |

Note:

- GitHub Actions compila le release con tag (Linux wheel/AppImage/deb/rpm, Windows, macOS, Flatpak, APK Android se il tag è su dev/master, SLSA, bozza di release) in un'unica esecuzione tramite `.github/workflows/build-release.yml`; l'immagine container tramite `.github/workflows/docker.yml`. CI Android per branch e PR: `.github/workflows/android-build.yml`.
- Per Linux, `x64` e `arm64` AppImage + DEB sono compilate su GitHub; il RPM e tentato e viene caricato quando l'artefatto e prodotto.

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
  -v meshchatx-config:/config \
  ghcr.io/quad4-software/meshchatx:latest
```

Al posto dell'immagine GHCR puoi usare `quad4io/meshchatx:latest` se preferisci Docker Hub.

Il file compose predefinito mappa:

- `127.0.0.1:8000` sull'host -> porta `8000` del container
- Volume Docker nominato **`meshchatx-config`** -> **`/config`** per la persistenza (adatto all'utente **meshchat** dell'immagine, UID 1000, senza `chown` sull'host per i bind mount)

**Opzionale: montare una directory dell'host**

Sostituisci la riga del volume con `-v "$(pwd)/meshchat-config:/config"` (Compose: modifica la voce `volumes` del servizio). Il container gira come **UID 1000**; la directory sull'host deve essere scrivibile (tipico: `sudo chown -R 1000:1000 ./meshchat-config`). Prima del primo avvio crea una directory vuota; altrimenti Docker potrebbe crearla con permessi errati.

**Ispezionare o eliminare il volume nominato**

```bash
docker volume inspect meshchatx-config
docker rm -f reticulum-meshchatx
docker volume rm meshchatx-config
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
pnpm config set verify-store-integrity true
pnpm install --frozen-lockfile
pip install "poetry==2.3.4"
poetry check --lock
poetry install
pnpm run build-frontend
poetry run python -m meshchatx.meshchat --headless --host 127.0.0.1
```

Note sui comandi di installazione:

- `pnpm install --frozen-lockfile` rifiuta di aggiornare `pnpm-lock.yaml` e fallisce se il lockfile non corrisponde a `package.json`. Cosi' si evita che una versione upstream inattesa venga installata silenziosamente.
- `verify-store-integrity=true` e' impostato anche nel `.npmrc` del progetto; la riga esplicita `pnpm config set` rafforza inoltre la configurazione utente.
- Gli script di lifecycle (`preinstall`/`postinstall`) sono bloccati di default in pnpm v10+. Solo i pacchetti elencati in `pnpm.onlyBuiltDependencies` di `package.json` possono eseguire script di installazione (attualmente `electron`, `electron-winstaller`, `esbuild`).
- `poetry check --lock` fallisce subito se `poetry.lock` non e' allineato con `pyproject.toml`; `poetry install` risolve poi solo dal lockfile.
- Per un'installazione Poetry strettamente basata sul lockfile (senza refresh implicito), fissa Poetry con `pip install "poetry==2.3.4"`, in linea con la CI.

Se vuoi aggiornare intenzionalmente le dipendenze, esegui `pnpm update` / `poetry update` in un commit dedicato e rivedi il diff del lockfile prima del push.

## Esecuzione in sandbox (Linux)

Per eseguire il binario nativo `meshchatx` (alias: `meshchat`) con isolamento aggiuntivo del filesystem, puoi usare **Firejail** o **Bubblewrap** (`bwrap`) mantenendo l'accesso di rete normale per Reticulum e l'interfaccia web. Esempi completi (pip/pipx, Poetry, note sulla seriale USB) sono in:

- [`docs/meshchatx_linux_sandbox.md`](../docs/meshchatx_linux_sandbox.md)

La stessa pagina compare nell'elenco **Documentazione** (documentazione MeshChatX) in-app quando viene servita dai file `meshchatx-docs` in bundle o sincronizzati.

## Desktop Linux: font emoji

Il selettore emoji mostra gli emoji Unicode standard usando i font di sistema (Electron/Chromium). Se compaiono quadrati vuoti ("tofu"), installate un pacchetto emoji a colori e riavviate l'app.

| Famiglia (esempi)          | Pacchetto                                                            |
| -------------------------- | -------------------------------------------------------------------- |
| Arch Linux, Artix, Manjaro | `noto-fonts-emoji` (`sudo pacman -S noto-fonts-emoji`)               |
| Debian, Ubuntu             | `fonts-noto-color-emoji` (`sudo apt install fonts-noto-color-emoji`) |
| Fedora                     | `google-noto-emoji-color-fonts`                                      |

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

## Build container (wheel, AppImage, deb, rpm)

`Dockerfile.build` esegue le stesse fasi usate in CI (Poetry, pnpm, `task`, dipendenze APT). Orientato a **linux/amd64** (tarball NodeSource amd64, Task amd64). Il target predefinito e completo; si puo sovrascrivere con un build-arg.

Valori per `MESHCHATX_BUILD_TARGETS`: `all` (default), `wheel` o `electron` (AppImage + deb per x64 e arm64, RPM se possibile, senza wheel).

Build:

```bash
docker build -f Dockerfile.build -t meshchatx-build:local .
```

Solo wheel:

```bash
docker build -f Dockerfile.build --build-arg MESHCHATX_BUILD_TARGETS=wheel -t meshchatx-build:wheel .
```

Copiare `/artifacts` dall'immagine finita all'host:

```bash
cid=$(docker create meshchatx-build:local)
docker cp "${cid}:/artifacts" ./meshchatx-artifacts
docker rm "${cid}"
```

## Supporto architetture

- Immagine Docker: `amd64`, `arm64`
- Linux AppImage: `x64`, `arm64`
- Linux DEB: `x64`, `arm64`
- Windows: `x64`, `arm64` (script di build disponibili)
- macOS: script di build disponibili (`arm64`, `universal`) per ambienti di build locali
- Android: solo APK universale (vedi [`android/README.md`](../android/README.md))

## Android

MeshChatX supporta build APK Android native (non solo Termux).

### Build APK da sorgente

Dalla root del repository:

```bash
# 1) Build delle wheel Chaquopy usate da android/app/build.gradle
bash scripts/build-android-wheels-local.sh

# 2) Build APK universal (un debug + una release per esecuzione; vedi android/README.md)
cd android
./gradlew --no-daemon :app:assembleDebug :app:assembleRelease
```

**Una** sola variante Android. Gradle sincronizza l'intera directory `meshchatx/` in `app/src/main/python/meshchatx/`, incluse le wheel offline del repository. Build documentate e pubblicate usano solo packaging **universal**: un APK debug e uno release per esecuzione, ciascuno con tutti gli ABI nativi configurati in `android/app/build.gradle`.

- Debug: `android/app/build/outputs/apk/debug/app-debug.apk`
- Release: `android/app/build/outputs/apk/release/app-release-unsigned.apk`

Note:

- Gli output di release non sono firmati finche non configuri la firma (`scripts/sign-android-apks.sh`).
- Gli ABI nativi nel APK universale seguono `android/app/build.gradle` (incluso `armeabi-v7a` se abilitato). Le wheel per `armeabi-v7a` richiedono Android SDK su `ANDROID_HOME` (vedi `android/README.md`).
- Se esiste in root `dist/reticulum_meshchatx-*.whl` (es. da `python -m build --wheel -o dist .`), l'aggiornamento del repository in bundle preferisce quella wheel rispetto a PyPI. In CI la wheel viene costruita prima del passo Gradle Android.

Documentazione aggiuntiva:

- [`docs/meshchatx_on_android_with_termux.md`](../docs/meshchatx_on_android_with_termux.md)
- [`android/README.md`](../android/README.md)

## Configurazione

| Argomento                  | Variabile d'ambiente                     | Predefinito  | Descrizione                                                                                                                                                                                           |
| -------------------------- | ---------------------------------------- | ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `--host`                   | `MESHCHAT_HOST`                          | `127.0.0.1`  | Indirizzo di bind del web server                                                                                                                                                                      |
| `--port`                   | `MESHCHAT_PORT`                          | `8000`       | Porta del web server                                                                                                                                                                                  |
| `--no-https`               | `MESHCHAT_NO_HTTPS`                      | `false`      | Disattiva HTTPS                                                                                                                                                                                       |
| `--ssl-cert` / `--ssl-key` | `MESHCHAT_SSL_CERT` / `MESHCHAT_SSL_KEY` | (nessuno)    | Percorsi PEM certificato e chiave; impostare entrambi. Sostituisce i certificati auto-generati sotto l'identita nella directory `ssl/`.                                                               |
| `--rns-log-level`          | `MESHCHAT_RNS_LOG_LEVEL`                 | (nessuno)    | Livello di log Reticulum (RNS): `none`, `critical`, `error`, `warning`, `notice`, `verbose`, `debug`, `extreme` o numerico. La CLI ha priorita sulla variabile d'ambiente se entrambe sono impostate. |
| `--headless`               | `MESHCHAT_HEADLESS`                      | `false`      | Non aprire il browser automaticamente                                                                                                                                                                 |
| `--auth`                   | `MESHCHAT_AUTH`                          | `false`      | Attiva autenticazione base                                                                                                                                                                            |
| `--storage-dir`            | `MESHCHAT_STORAGE_DIR`                   | `./storage`  | Directory dei dati                                                                                                                                                                                    |
| `--public-dir`             | `MESHCHAT_PUBLIC_DIR`                    | auto/bundled | Directory dei file frontend (necessaria per installazioni da sorgente senza asset in bundle)                                                                                                          |

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

## Versionamento

Versione attuale nel repository: `4.6.0`.

- L'unico valore che modifichi per un bump di release e **`version` in `package.json`**.
- Esegui **`pnpm run version:sync`** (all'inizio anche di **`pnpm run build`**) per propagare in **`pyproject.toml`**, **`meshchatx/src/version.py`**, **`THIRD_PARTY_NOTICES.txt`** (riga prodotto), **README** / **lang/README.\*** (righe "versione attuale"), **esempio pipx in `docs/meshchatx_on_raspberry_pi.md`**, e aiuti in **`packaging/arch/PKGBUILD`**.
- **`meshchatx.__version__`** si legge da **`meshchatx/src/version.py`** senza importare **`meshchatx.src`**, cosi un semplice `import meshchatx` resta leggero.
- Le voci del **changelog** restano manuali quando tagghi una release.

## Sicurezza

- [`SECURITY.md`](../SECURITY.md)
- [`LEGAL.md`](../LEGAL.md)
- Controlli di integrita integrati e valori predefiniti HTTPS/WSS nel runtime dell'app.
- Build CI e release su GitHub Actions.

## Aggiungere una lingua

Flusso dell'autore: ArgosTranslate, poi LLM locale (Qwen 3 + Gemma 4).

Poi si accettano volentieri fix dalla community (LXMF o come mi contattate).

Il rilevamento locale e automatico. Aggiungi un file in `meshchatx/src/frontend/locales/` (es. `xx.json`) con le stesse chiavi di `en.json` e un `_languageName` in cima per l'etichetta nel selettore. Puoi copiare `en.json` e tradurre tutto a mano; **la generazione assistita da machine e opzionale** e non e mai obbligatoria.

**Opzionale: avvio con Argos Translate** -- per una bozza partendo da `en.json` puoi usare `scripts/argos_translate.py` (formattazione, output a colori, variabili di interpolazione come `{count}`).

```bash
# Installa argostranslate se non l'hai gia
pipx install argostranslate

# Esegui lo script di traduzione
python scripts/argos_translate.py --from en --to xx --input meshchatx/src/frontend/locales/en.json --output meshchatx/src/frontend/locales/xx.json --name "Nome della tua lingua"
```

Dopo qualsiasi passaggio automatico, un LLM o un revisore umano controlli grammatica, contesto e tono (es. formale vs informale).

Esegui `pnpm test -- tests/frontend/i18n.test.js --run` per verificare la parita delle chiavi con `en.json`.

Non sono necessarie altre modifiche al codice. L'app, il selettore della lingua e i test scoprono le lingue dalla cartella `meshchatx/src/frontend/locales/` durante la compilazione.

## Donazioni

Le donazioni sono facoltative. Servono a finanziare tempo e impegno per sviluppare questa app.

**Come donare:** [`donate.md`](../donate.md) (Monero, Ko-Fi, Buy Me a Coffee).

## Crediti

- [Liam Cottle](https://github.com/liamcottle) - Reticulum MeshChat originale
- [RFnexus](https://github.com/RFnexus) - parser micron (JavaScript)
- [markqvist](https://github.com/markqvist) - Reticulum, LXMF, LXST

## Licenza

Le parti di proprieta del progetto sono rilasciate sotto 0BSD.
Le parti originali upstream da Reticulum MeshChat restano sotto MIT.
Per testo completo e note, vedi [`../LICENSE`](../LICENSE).
