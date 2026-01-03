# Reticulum MeshChatX

A [Reticulum MeshChat](https://github.com/liamcottle/reticulum-meshchat) fork from the future.

<video src="https://strg.0rbitzer0.net/raw/62926a2a-0a9a-4f44-a5f6-000dd60deac1.mp4" controls="controls" style="max-width: 100%;"></video>

This project is separate from the original Reticulum MeshChat project, and is not affiliated with the original project.

> [!WARNING]  
> Backup your reticulum-meshchat folder before using! MeshChatX will attempt to auto-migrate whatever it can from the old database without breaking things, but it is best to keep backups.

## Goal

To provide everything you need for Reticulum, LXMF, and LXST in one beautiful and feature-rich application.

- Desktop app
- Self-host on your server easily with or without containers
- Mobile app (one can dream)

## Quick Start (Docker - Recommended)

The easiest way to get MeshChatX running is using Docker. Our official image is multi-arch and supports `linux/amd64` and `linux/arm64` (Raspberry Pi, etc.).

```bash
# Pull and run the latest image
docker pull git.quad4.io/rns-things/meshchatx:latest

# Run MeshChatX in a Docker container
docker run -d \
  --name=meshchatx \
  -p 8000:8000 \
  -v $PWD/storage:/app/storage \
  -v $PWD/public:/app/public \
  # --network=host \  # Uncomment for autointerface support
  git.quad4.io/rns-things/meshchatx:latest

# Or use Docker Compose for an even easier setup
docker compose up -d
```

Check [releases](https://git.quad4.io/RNS-Things/MeshChatX/releases) for pre-built binaries (AppImage, DEB, EXE) if you prefer standalone apps.

## Major Features

- **Full LXST Support**: Custom voicemail, phonebook, contact sharing, and ringtone support.
- **Multi-Identity**: Switch between multiple Reticulum identities seamlessly.
- **Modern UI/UX**: A completely redesigned, intuitive interface.
- **Integrated Maps**: OpenLayers with MBTiles support for offline maps.
- **Security**: Built-in authentication, automatic HTTPS, and CORS protection.
- **Offline Docs**: Access Reticulum documentation without an internet connection.
- **Powerful Tools**: Includes RNStatus, RNProbe, RNCP, Micron Editor, Paper Message Generator and a Translator.
- **Page Archiving**: Built-in crawler and browser for archived pages.
- **Blocklist**: Block LXMF users, Telephony, and NomadNet Nodes.
- **i18n**: Support for English, German, and Russian.

## Screenshots

<details>
<summary>Telephony & Calling</summary>

### Phone

![Phone](screenshots/phone.png)

### Active Call

![Calling](screenshots/calling.png)

### Call Ended

![Call Ended](screenshots/calling-end.png)

### Voicemail

![Voicemail](screenshots/voicemail.png)

### Ringtone Settings

![Ringtone](screenshots/ringtone.png)

</details>

<details>
<summary>Networking & Visualization</summary>

### Network Visualiser

![Network Visualiser](screenshots/network-visualiser.png)
![Network Visualiser 2](screenshots/network-visualiser2.png)

</details>

<details>
<summary>Page Archives</summary>

### Archives Browser

![Archives](screenshots/archives.png)

### Viewing Archived Page

![Archive View](screenshots/archive-view.png)

</details>

<details>
<summary>Tools & Identities</summary>

### Tools

![Tools](screenshots/tools.png)

### Identity Management

![Identities](screenshots/identities.png)

</details>

### Pipx / Global Installation

If you prefer to install MeshChatX globally using `pipx, pip or uv`, you can do so directly from the repository. However, you must specify the path to your built frontend files using the `--public-dir` flag or `MESHCHAT_PUBLIC_DIR` environment variable, as the static files are not bundled with the source code. The release .whl packages include the built frontend files and also there is a seperate frontend zip to grab and use.

1. **Install MeshChatX**:

    ```bash
    pipx install git+https://git.quad4.io/RNS-Things/MeshChatX
    ```

2. **Run with Frontend Path**:
    ```bash
    # Replace /path/to/MeshChatX/meshchatx/public with your actual path
    meshchat --public-dir /path/to/MeshChatX/meshchatx/public
    ```

### Manual Installation (From Source)

If you want to run MeshChatX from the source code locally:

1. **Clone the repository**:

    ```bash
    git clone https://git.quad4.io/RNS-Things/MeshChatX
    cd MeshChatX
    ```

2. **Build the Frontend**:
   Requires Node.js and pnpm.

    ```bash
    corepack enable
    pnpm install
    pnpm run build-frontend
    ```

3. **Install & Run Backend**:
   Requires Python 3.10+ and Poetry.
    ```bash
    pip install poetry
    poetry install
    poetry run meshchat --headless --host 127.0.0.1
    ```

## Configuration

MeshChatX can be configured via command-line arguments or environment variables.

| Argument        | Environment Variable   | Default     | Description          |
| :-------------- | :--------------------- | :---------- | :------------------- |
| `--host`        | `MESHCHAT_HOST`        | `127.0.0.1` | Web server address   |
| `--port`        | `MESHCHAT_PORT`        | `8000`      | Web server port      |
| `--no-https`    | `MESHCHAT_NO_HTTPS`    | `false`     | Disable HTTPS        |
| `--headless`    | `MESHCHAT_HEADLESS`    | `false`     | Don't launch browser |
| `--auth`        | `MESHCHAT_AUTH`        | `false`     | Enable basic auth    |
| `--storage-dir` | `MESHCHAT_STORAGE_DIR` | `./storage` | Data directory       |
| `--public-dir`  | `MESHCHAT_PUBLIC_DIR`  | -           | Frontend files path  |

## GPG Verification

To ensure the security and authenticity of this project, all commits and releases are GPG signed. You can verify the signatures of the commits using the following steps:

### 1. Import the Developer's Public Key

Fetch the public key from the Gitea instance and import it into your GPG keyring:

```bash
# Replace YOUR_TOKEN if the instance requires authentication
curl -s "https://git.quad4.io/api/v1/users/Ivan/gpg_keys" | jq -r '.[0].public_key' | gpg --import
```

### 2. Verify Commits

Once the key is imported, you can verify the commits in your local clone:

```bash
# Show signatures for the last 10 commits
git log --show-signature -n 10
```

You should see "Good signature from Ivan <ivan@quad4.io>" with the Key ID `1E0B37EE76428197`.

## Development

We use [Task](https://taskfile.dev/) for automation.

| Task            | Description                         |
| :-------------- | :---------------------------------- |
| `task install`  | Install all dependencies            |
| `task run`      | Run the application                 |
| `task lint`     | Run all linters (Python & Frontend) |
| `task format`   | Format all code (Python & Frontend) |
| `task test`     | Run all tests                       |
| `task test:cov` | Run tests with coverage reports     |
| `task build`    | Build frontend and backend          |

## TODO

- [ ] RNS hot reload fix
- [ ] Offline Reticulum documentation tool
- [ ] Spam filter (based on keywords)
- [ ] TAK tool/integration
- [ ] RNS Tunnel - tunnel regular services over RNS
- [ ] RNS Filesync - P2P file sync

## Credits

- [Liam Cottle](https://github.com/liamcottle) - Original Reticulum MeshChat
- [RFnexus](https://github.com/RFnexus) - [micron-parser-js](https://github.com/RFnexus/micron-parser-js)
