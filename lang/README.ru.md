# Reticulum MeshChatX

Существенно доработанный и функционально расширенный форк Reticulum MeshChat от Liam Cottle.

Этот проект независим от оригинального Reticulum MeshChat и не связан с ним.

- Исходный код: [git.quad4.io/RNS-Things/MeshChatX](https://git.quad4.io/RNS-Things/MeshChatX)
- Релизы: [git.quad4.io/RNS-Things/MeshChatX/releases](https://git.quad4.io/RNS-Things/MeshChatX/releases)
- Журнал изменений: [`CHANGELOG.md`](../CHANGELOG.md)
- TODO: [`TODO.md`](../TODO.md)
- [English README](../README.md) | [Deutsch](README.de.md) | [Italiano](README.it.md) | [中文](README.zh.md) | [日本語](README.ja.md)

## Важные замечания

- Полная поддержка LXMF является ключевым направлением проекта.
- Хранение данных и миграции постепенно переводятся на прямой SQL (замена устаревших путей Peewee ORM).

> [!WARNING]
> MeshChatX не гарантирует совместимость данных со старыми версиями Reticulum MeshChat. Сделайте резервную копию перед миграцией или тестированием.

> [!WARNING]
> Устаревшие системы пока не полностью поддерживаются. Текущие требования: Python `>=3.11` и Node `>=24`.

## Демо и скриншоты

<video src="https://strg.0rbitzer0.net/raw/62926a2a-0a9a-4f44-a5f6-000dd60deac1.mp4" controls="controls" style="max-width: 100%;"></video>

### Интерфейс

![Телефон](../screenshots/phone.png)
![Визуализатор сети](../screenshots/network-visualiser.png)
![Архивы](../screenshots/archives.png)
![Идентичности](../screenshots/identities.png)

## Требования

- Python `>=3.11` (из `pyproject.toml`)
- Node.js `>=24` (из `package.json`)
- pnpm `10.32.1` (из `package.json`)
- Poetry (используется в `Taskfile.yml` и CI)

## Nix (flake.nix)

В репозитории есть Nix-флейк `flake.nix`.

### Войти в dev-оболочку

```bash
nix develop
```

### Собрать пакет по умолчанию

```bash
nix build .#default
```

### Типичный рабочий процесс внутри `nix develop`

```bash
task install
task lint:all
task test:all
task build:all
```

## Способы установки

| Метод                 | Включает фронтенд   | Архитектуры                              | Лучше всего подходит для              |
| --------------------- | ------------------- | ---------------------------------------- | ------------------------------------- |
| Docker-образ          | Да                  | `linux/amd64`, `linux/arm64`             | Быстрый запуск на серверах Linux      |
| Python wheel (`.whl`) | Да                  | Любая архитектура, поддерживаемая Python | Безголовый/веб-сервер без сборки Node |
| Linux AppImage        | Да                  | `x64`, `arm64`                           | Портативное использование на ПК       |
| Debian-пакет (`.deb`) | Да                  | `x64`, `arm64`                           | Установка на Debian/Ubuntu            |
| RPM-пакет (`.rpm`)    | Да                  | Зависит от CI                            | Fedora/RHEL/openSUSE                  |
| Из исходников         | Собирается локально | Архитектура хоста                        | Разработка и кастомные сборки         |

Примечания:

- CI явно собирает Linux `x64` и `arm64` AppImage + DEB.
- RPM также создается при сборке релиза и загружается, если успешно.

## Быстрый старт: Docker

```bash
docker compose up -d
```

Compose-файл по умолчанию:

- `127.0.0.1:8000` на хосте -> порт `8000` контейнера
- `./meshchat-config` -> `/config` для хранения данных

Если возникают ошибки прав доступа:

```bash
sudo chown -R 1000:1000 ./meshchat-config
```

## Установка из релизных артефактов

### 1) Linux AppImage (x64/arm64)

1. Скачайте `ReticulumMeshChatX-v<версия>-linux-<арх>.AppImage` из релизов.
2. Сделайте исполняемым и запустите:

```bash
chmod +x ./ReticulumMeshChatX-v*-linux-*.AppImage
./ReticulumMeshChatX-v*-linux-*.AppImage
```

### 2) Debian/Ubuntu `.deb` (x64/arm64)

1. Скачайте `ReticulumMeshChatX-v<версия>-linux-<арх>.deb`.
2. Установите:

```bash
sudo apt install ./ReticulumMeshChatX-v*-linux-*.deb
```

### 3) RPM-системы

1. Скачайте `ReticulumMeshChatX-v<версия>-linux-<арх>.rpm`, если есть в релизе.
2. Установите:

```bash
sudo rpm -Uvh ./ReticulumMeshChatX-v*-linux-*.rpm
```

### 4) Python wheel (`.whl`)

Wheel-пакеты из релизов включают собранный фронтенд.

```bash
pip install ./reticulum_meshchatx-*-py3-none-any.whl
meshchat --headless
```

`pipx` также поддерживается:

```bash
pipx install ./reticulum_meshchatx-*-py3-none-any.whl
```

## Запуск из исходников (режим веб-сервера)

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

## Запуск в песочнице (Linux)

Чтобы запускать нативный бинарник `meshchat` с дополнительной изоляцией файловой системы, можно использовать **Firejail** или **Bubblewrap** (`bwrap`), сохраняя обычный сетевой доступ для Reticulum и веб-интерфейса. Полные примеры (pip/pipx, Poetry, заметки про USB-serial) в:

- [`docs/meshchatx_linux_sandbox.md`](../docs/meshchatx_linux_sandbox.md)

Та же страница отображается во встроенном разделе **Документация** (документация MeshChatX), когда она отдаётся из входящих в сборку или синхронизируемых файлов `meshchatx-docs`.

## Сборка пакетов из исходников

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

## Поддержка архитектур

- Docker: `amd64`, `arm64`
- Linux AppImage: `x64`, `arm64`
- Linux DEB: `x64`, `arm64`
- Windows: `x64`, `arm64` (скрипты сборки доступны)
- macOS: скрипты сборки доступны (`arm64`, `universal`)
- Android: проект и CI-воркфлоу присутствуют в репозитории

## Android

- [`docs/meshchatx_on_android_with_termux.md`](../docs/meshchatx_on_android_with_termux.md)
- [`android/README.md`](../android/README.md)

## Конфигурация

| Аргумент        | Переменная окружения   | По умолчанию | Описание                           |
| --------------- | ---------------------- | ------------ | ---------------------------------- |
| `--host`        | `MESHCHAT_HOST`        | `127.0.0.1`  | Адрес привязки веб-сервера         |
| `--port`        | `MESHCHAT_PORT`        | `8000`       | Порт веб-сервера                   |
| `--no-https`    | `MESHCHAT_NO_HTTPS`    | `false`      | Отключить HTTPS                    |
| `--headless`    | `MESHCHAT_HEADLESS`    | `false`      | Не открывать браузер автоматически |
| `--auth`        | `MESHCHAT_AUTH`        | `false`      | Включить базовую аутентификацию    |
| `--storage-dir` | `MESHCHAT_STORAGE_DIR` | `./storage`  | Директория данных                  |
| `--public-dir`  | `MESHCHAT_PUBLIC_DIR`  | авто         | Директория фронтенд-файлов         |

## Ветки

| Ветка    | Назначение                                                                |
| -------- | ------------------------------------------------------------------------- |
| `master` | Стабильные релизы. Только готовый к продакшену код.                       |
| `dev`    | Активная разработка. Может содержать нестабильные или неполные изменения. |

## Разработка

```bash
task install
task lint:all
task test:all
task build:all
```

## Безопасность

- [`SECURITY.md`](../SECURITY.md)
- Встроенные проверки целостности и HTTPS/WSS по умолчанию
- CI-сканирование в `.gitea/workflows/`

## Добавление языка

Обнаружение локалей происходит автоматически. Для добавления нового языка достаточно одного JSON-файла:

1. Сгенерировать шаблон из `en.json`:

```bash
python scripts/generate_locale_template.py
```

2. Переименовать и переместить в каталог локалей:

```bash
mv locales.json meshchatx/src/frontend/locales/xx.json
```

3. Установить `_languageName` в начале файла на название языка на этом языке (например `"Espanol"`, `"Francais"`).

4. Перевести все остальные значения.

5. Проверить соответствие ключей: `pnpm test -- tests/frontend/i18n.test.js --run`

Никаких других изменений кода не требуется.

## Авторы

- [Liam Cottle](https://github.com/liamcottle) - Оригинальный Reticulum MeshChat
- [RFnexus](https://github.com/RFnexus) - JavaScript-реализация Micron-парсера
- [markqvist](https://github.com/markqvist) - Reticulum, LXMF, LXST
