# Reticulum MeshChatX

[English README](../README.md) | [Deutsch](README.de.md) | [Italiano](README.it.md) | [中文](README.zh.md) | [日本語](README.ja.md)

Существенно доработанный и функционально расширенный форк Reticulum MeshChat от Liam Cottle.

Этот проект независим от оригинального Reticulum MeshChat и не связан с ним.

- Сайт: [meshchatx.com](https://meshchatx.com)
- Исходный код: [git.quad4.io/RNS-Things/MeshChatX](https://git.quad4.io/RNS-Things/MeshChatX)
- Официальное зеркало: [github.com/Sudo-Ivan/MeshChatX](https://github.com/Sudo-Ivan/MeshChatX) — пока также используется для сборок Windows и macOS.
- Релизы: [git.quad4.io/RNS-Things/MeshChatX/releases](https://git.quad4.io/RNS-Things/MeshChatX/releases)
- Журнал изменений: [`CHANGELOG.md`](../CHANGELOG.md)
- TODO: [Boards](https://git.quad4.io/RNS-Things/MeshChatX/projects)

## Важные отличия от Reticulum MeshChat

- Используется LXST
- Peewee ORM заменён на прямой SQL
- Axios заменён на нативный `fetch`
- Актуальный Electron
- Колёса `.whl` с веб-сервером и встроенным фронтендом для разных сценариев развёртывания
- i18n
- PNPM и Poetry для зависимостей

> [!WARNING]
> MeshChatX не гарантирует совместимость данных со старыми версиями Reticulum MeshChat. Сделайте резервную копию перед миграцией или тестированием.

> [!WARNING]
> Устаревшие системы пока не полностью поддерживаются. Текущие требования: Python `>=3.11` и Node `>=24`.

## Требования

- Python `>=3.11` (из `pyproject.toml`)
- Node.js `>=24` (из `package.json`)
- pnpm `10.32.1` (из `package.json`)
- Poetry (используется в `Taskfile.yml` и CI)

```bash
task install
task lint:all
task test:all
task build:all
```

## Способы установки

Выберите способ в соответствии со средой и форматом пакета.

| Метод                 | Включает фронтенд   | Архитектуры                              | Лучше всего для                       |
| --------------------- | ------------------- | ---------------------------------------- | ------------------------------------- |
| Docker-образ          | Да                  | `linux/amd64`, `linux/arm64`             | Быстрый запуск на серверах Linux      |
| Python wheel (`.whl`) | Да                  | Любая архитектура, поддерживаемая Python | Безголовый/веб-сервер без сборки Node |
| Linux AppImage        | Да                  | `x64`, `arm64`                           | Портативное использование на ПК       |
| Debian-пакет (`.deb`) | Да                  | `x64`, `arm64`                           | Установка на Debian/Ubuntu            |
| RPM-пакет (`.rpm`)    | Да                  | Зависит от CI                            | Fedora/RHEL/openSUSE                  |
| Из исходников         | Собирается локально | Архитектура хоста                        | Разработка и кастомные сборки         |

Примечания:

- Релизный workflow явно собирает Linux `x64` и `arm64` AppImage + DEB.
- RPM также собирается при попытке и загружается при успехе.

## Быстрый старт: Docker

```bash
docker compose up -d
```

Compose-файл по умолчанию:

- `127.0.0.1:8000` на хосте -> порт `8000` контейнера
- `./meshchat-config` -> `/config` для данных

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

В релизных wheel включены собранные веб-ресурсы.

```bash
pip install ./reticulum_meshchatx-*-py3-none-any.whl
meshchatx --headless
```

`pipx` также поддерживается:

```bash
pipx install ./reticulum_meshchatx-*-py3-none-any.whl
```

## Запуск из исходников (режим веб-сервера)

Для разработки или локальной сборки.

```bash
git clone https://git.quad4.io/RNS-Things/MeshChatX.git
cd MeshChatX
corepack enable
pnpm install
pip install poetry
poetry install
pnpm run build-frontend
poetry run meshchatx --headless --host 127.0.0.1
```

## Запуск в песочнице (Linux)

Чтобы запускать нативный `meshchatx` (псевдоним: `meshchat`) с дополнительной изоляцией файловой системы, можно использовать **Firejail** или **Bubblewrap** (`bwrap`), сохраняя обычный сетевой доступ для Reticulum и веб-интерфейса. Полные примеры (pip/pipx, Poetry, USB-serial) в:

- [`docs/meshchatx_linux_sandbox.md`](../docs/meshchatx_linux_sandbox.md)

Та же страница отображается во встроенной **Документации** (документация MeshChatX), когда она отдаётся из `meshchatx-docs`.

## Сборка настольных пакетов из исходников

Скрипты заданы в `package.json` и `Taskfile.yml`.

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

Через Task:

```bash
task dist:fe:rpm
```

## Поддержка архитектур

- Docker: `amd64`, `arm64`
- Linux AppImage: `x64`, `arm64`
- Linux DEB: `x64`, `arm64`
- Windows: `x64`, `arm64` (скрипты сборки есть)
- macOS: скрипты сборки (`arm64`, `universal`) для локальных сред
- Android: проект и CI в репозитории

## Android

- [`docs/meshchatx_on_android_with_termux.md`](../docs/meshchatx_on_android_with_termux.md)
- [`android/README.md`](../android/README.md)

## Конфигурация

| Аргумент                   | Переменная окружения                     | По умолчанию | Описание                                                                                                                                      |
| -------------------------- | ---------------------------------------- | ------------ | --------------------------------------------------------------------------------------------------------------------------------------------- |
| `--host`                   | `MESHCHAT_HOST`                          | `127.0.0.1`  | Адрес привязки веб-сервера                                                                                                                    |
| `--port`                   | `MESHCHAT_PORT`                          | `8000`       | Порт веб-сервера                                                                                                                              |
| `--no-https`               | `MESHCHAT_NO_HTTPS`                      | `false`      | Отключить HTTPS                                                                                                                               |
| `--ssl-cert` / `--ssl-key` | `MESHCHAT_SSL_CERT` / `MESHCHAT_SSL_KEY` | (нет)        | Пути к PEM-сертификату и ключу; задаются вместе. Переопределяют автосгенерированные сертификаты в каталоге `ssl/` у идентичности.               |
| `--headless`               | `MESHCHAT_HEADLESS`                      | `false`      | Не открывать браузер автоматически                                                                                                            |
| `--auth`                   | `MESHCHAT_AUTH`                          | `false`      | Базовая аутентификация                                                                                                                        |
| `--storage-dir`            | `MESHCHAT_STORAGE_DIR`                   | `./storage`  | Каталог данных                                                                                                                                |
| `--public-dir`             | `MESHCHAT_PUBLIC_DIR`                    | авто/bundled | Каталог фронтенда (для установок без встроенных ресурсов)                                                                                     |

## Ветки

| Ветка    | Назначение                                                                |
| -------- | ------------------------------------------------------------------------- |
| `master` | Стабильные релизы. Только код для продакшена.                             |
| `dev`    | Активная разработка. Возможны нестабильные или неполные изменения.        |

## Разработка

Типичные задачи из `Taskfile.yml`:

```bash
task install
task lint:all
task test:all
task build:all
```

Сокращения `Makefile`:

| Команда        | Описание                                   |
| -------------- | ------------------------------------------ |
| `make install` | Установить зависимости pnpm и poetry       |
| `make run`     | Запуск MeshChatX через poetry              |
| `make build`   | Сборка фронтенда                           |
| `make lint`    | eslint и ruff                              |
| `make test`    | Тесты фронтенда и бэкенда                  |
| `make clean`   | Удалить артефакты сборки и node_modules    |

## Версионирование

Текущая версия в репозитории: `4.4.0`.

- Источник версии JS/Electron — `package.json`.
- `meshchatx/src/version.py` синхронизируется из `package.json`:

```bash
pnpm run version:sync
```

Для согласованных релизов выравнивайте поля версий где нужно (`package.json`, `pyproject.toml`, `meshchatx/__init__.py`).

## Безопасность

- [`SECURITY.md`](../SECURITY.md)
- Встроенные проверки целостности и HTTPS/WSS по умолчанию в приложении
- CI-сканирование в `.gitea/workflows/`

## Добавление языка

Локали обнаруживаются автоматически. Достаточно одного JSON-файла:

1. Сгенерировать пустой шаблон из `en.json`:

```bash
python scripts/generate_locale_template.py
```

Создаётся `locales.json` со всеми ключами и пустыми строками.

2. Переименовать и переместить:

```bash
mv locales.json meshchatx/src/frontend/locales/xx.json
```

3. В начале файла задать `_languageName` — нативное имя языка (например `"Espanol"`, `"Francais"`). Отображается в выборе языка.

4. Перевести остальные значения.

5. Проверить ключи: `pnpm test -- tests/frontend/i18n.test.js --run`

Других изменений кода не требуется. Приложение, селектор языка и тесты используют `meshchatx/src/frontend/locales/` на этапе сборки.

## Авторы

- [Liam Cottle](https://github.com/liamcottle) — оригинальный Reticulum MeshChat
- [RFnexus](https://github.com/RFnexus) — парсер Micron (JavaScript)
- [markqvist](https://github.com/markqvist) — Reticulum, LXMF, LXST
