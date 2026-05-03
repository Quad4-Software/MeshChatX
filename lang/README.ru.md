# Reticulum MeshChatX

[English](../README.md) | [Deutsch](README.de.md) | [Italiano](README.it.md) | [中文](README.zh.md) | [日本語](README.ja.md)

Существенно доработанный и функционально расширенный форк Reticulum MeshChat от Liam Cottle.

Этот проект независим от оригинального Reticulum MeshChat и не связан с ним.

- Сайт: [meshchatx.com](https://meshchatx.com)
- Исходный код: [git.quad4.io/RNS-Things/MeshChatX](https://git.quad4.io/RNS-Things/MeshChatX)
- Официальное зеркало на GitHub: [github.com/Quad4-Software/MeshChatX](https://github.com/Quad4-Software/MeshChatX)
- Релизы: [github.com/Quad4-Software/MeshChatX](https://github.com/Quad4-Software/MeshChatX)
- Журнал изменений: [`CHANGELOG.md`](../CHANGELOG.md)
- Поддержка проекта: [`donate.md`](../donate.md)

<a href="https://apps.obtainium.imranr.dev/redirect.html?r=obtainium://add/https://github.com/Quad4-Software/MeshChatX"><img src="https://raw.githubusercontent.com/ImranR98/Obtainium/main/assets/graphics/badge_obtainium.png" height="60" alt="Get it on Obtainium"></a>

rngit: `git clone rns://926baefe13daf5178c174f158dae1b45/quad4/MeshChatX`
NomadNet Node: `c10d80b1a42fa958c37a6cc30dc04f53:/page/index.mu`

## Важные отличия от Reticulum MeshChat

- Для вызовов используется LXST
- Peewee ORM заменён на прямой SQL
- Axios заменён на нативный `fetch`
- Electron 41.x (встроенная среда Node 24)
- Колёса `.whl` с веб-сервером и встроенным фронтендом для разных сценариев развёртывания
- i18n
- PNPM и Poetry для зависимостей

> [!WARNING]
> MeshChatX не гарантирует совместимость данных со старыми версиями Reticulum MeshChat. Сделайте резервную копию перед миграцией или тестированием.

> [!WARNING]
> Устаревшие системы пока не поддерживаются. Текущий базис: Python `>=3.11` и Node `>=24` (Electron 41 выровнен с Node 24; поле `engines` в `package.json` и CI на той же линии).

## Требования

- Python `>=3.11` (из `pyproject.toml`)
- Node.js `>=24` (из `package.json`, поле `engines`)
- pnpm `10.33.0` (из `package.json`, поле `packageManager`)
- Poetry (используется в `Taskfile.yml` и CI)

**Browser Versions Required:**

Safari 16.4 или новее, Chrome 111 или новее, Firefox 128 или новее (встроенный веб-интерфейс).

```bash
task install
task lint:all
task test:all
task build:all
```

## Способы установки

Выберите способ в соответствии со средой и форматом пакета.

| Метод                 | Включает фронтенд   | Архитектуры                                      | Лучше всего для                       |
| --------------------- | ------------------- | ------------------------------------------------ | ------------------------------------- |
| Docker-образ          | Да                  | `linux/amd64`, `linux/arm64`                     | Быстрый запуск на серверах Linux      |
| Python wheel (`.whl`) | Да                  | Любая архитектура, поддерживаемая Python         | Безголовый/веб-сервер без сборки Node |
| Linux AppImage        | Да                  | `x64`, `arm64`                                   | Портативное использование на ПК       |
| Debian-пакет (`.deb`) | Да                  | `x64`, `arm64`                                   | Установка на Debian/Ubuntu            |
| RPM-пакет (`.rpm`)    | Да                  | Зависит от раннера CI для публикуемого артефакта | Fedora/RHEL/openSUSE                  |
| Из исходников         | Собирается локально | Архитектура хоста                                | Разработка и кастомные сборки         |

Примечания:

- GitHub Actions собирает помеченные тегом релизы (Linux wheel/AppImage/deb/rpm, Windows, macOS, Flatpak, Android APK при теге на dev/master, SLSA, черновик релиза) в одном запуске: `.github/workflows/build-release.yml`; образ контейнера — `.github/workflows/docker.yml`. Android CI для веток и PR — `.github/workflows/android-build.yml`.
- AppImage + DEB для Linux `x64` и `arm64` собираются на GitHub; RPM собирается по возможности и выкладывается, если шаг дал артефакт.

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

Вместо образа GHCR можно указать `quad4io/meshchatx:latest`, если предпочитаете Docker Hub.

Compose-файл по умолчанию:

- `127.0.0.1:8000` на хосте -> порт `8000` контейнера
- Именованный том Docker **`meshchatx-config`** -> **`/config`** для данных (подходит пользователю **meshchat** в образе, UID 1000, без `chown` на хосте для bind mount)

**По желанию: каталог на хосте**

Замените строку тома на `-v "$(pwd)/meshchat-config:/config"` (Compose: измените `volumes` у сервиса). Контейнер работает от **UID 1000**; каталог на хосте должен быть доступен на запись (обычно: `sudo chown -R 1000:1000 ./meshchat-config`). Создайте пустой каталог до первого запуска, чтобы Docker не создал его с неподходящими правами.

**Просмотр или удаление именованного тома**

```bash
docker volume inspect meshchatx-config
docker rm -f reticulum-meshchatx
docker volume rm meshchatx-config
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
pnpm config set verify-store-integrity true
pnpm install --frozen-lockfile
pip install "poetry==2.3.4"
poetry check --lock
poetry install
pnpm run build-frontend
poetry run python -m meshchatx.meshchat --headless --host 127.0.0.1
```

Пояснения к командам установки:

- `pnpm install --frozen-lockfile` запрещает обновление `pnpm-lock.yaml` и завершится с ошибкой, если lock-файл не соответствует `package.json`. Это исключает скрытую установку неожиданной upstream-версии.
- `verify-store-integrity=true` уже задан в `.npmrc` проекта; явный `pnpm config set` дополнительно ужесточает пользовательскую конфигурацию.
- Lifecycle-скрипты (`preinstall`/`postinstall`) по умолчанию заблокированы в pnpm v10+. Скрипты установки могут запускать только пакеты из `pnpm.onlyBuiltDependencies` в `package.json` (сейчас `electron`, `electron-winstaller`, `esbuild`).
- `poetry check --lock` сразу падает, если `poetry.lock` не синхронизирован с `pyproject.toml`; затем `poetry install` ставит зависимости только из lock-файла.
- Для строгой установки Poetry только из lock-файла зафиксируйте версию Poetry через `pip install "poetry==2.3.4"`, как это делает CI.

Если вы намеренно хотите обновить зависимости, выполните `pnpm update` / `poetry update` отдельным коммитом и проверьте diff lock-файлов до пуша.

## Запуск в песочнице (Linux)

Чтобы запускать нативный `meshchatx` (псевдоним: `meshchat`) с дополнительной изоляцией файловой системы, можно использовать **Firejail** или **Bubblewrap** (`bwrap`), сохраняя обычный сетевой доступ для Reticulum и веб-интерфейса. Полные примеры (pip/pipx, Poetry, USB-serial) в:

- [`docs/meshchatx_linux_sandbox.md`](../docs/meshchatx_linux_sandbox.md)

Та же страница отображается в списке **Документация** (документация MeshChatX) в приложении, если файлы отдаются из встроенных или синхронизированных `meshchatx-docs`.

## Linux на ПК: шрифты эмодзи

Выбор эмодзи отображает стандартные Unicode-эмодзи системными шрифтами (Electron/Chromium). Если вместо них пустые квадраты («тофу»), установите пакет цветных эмодзи и перезапустите приложение.

| Семейство (примеры)        | Пакет                                                                |
| -------------------------- | -------------------------------------------------------------------- |
| Arch Linux, Artix, Manjaro | `noto-fonts-emoji` (`sudo pacman -S noto-fonts-emoji`)               |
| Debian, Ubuntu             | `fonts-noto-color-emoji` (`sudo apt install fonts-noto-color-emoji`) |
| Fedora                     | `google-noto-emoji-color-fonts`                                      |

После установки при необходимости выполните `fc-cache -fv`. Опционально: `noto-fonts` для лучшего покрытия символов на минимальных установках.

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

## Сборка в контейнере (wheel, AppImage, deb, rpm)

`Dockerfile.build` выполняет те же шаги, что и CI (Poetry, pnpm, `task`, пакетные зависимости APT). Ориентирован на **linux/amd64** (NodeSource amd64, Task amd64). Цель по умолчанию: всё; её можно переопределить build-arg.

Для `MESHCHATX_BUILD_TARGETS` доступны: `all` (по умолчанию), `wheel` или `electron` (AppImage + deb для x64 и arm64, RPM по возможности, без wheel).

Сборка:

```bash
docker build -f Dockerfile.build -t meshchatx-build:local .
```

Только wheel:

```bash
docker build -f Dockerfile.build --build-arg MESHCHATX_BUILD_TARGETS=wheel -t meshchatx-build:wheel .
```

Скопируйте `/artifacts` из готового образа на хост:

```bash
cid=$(docker create meshchatx-build:local)
docker cp "${cid}:/artifacts" ./meshchatx-artifacts
docker rm "${cid}"
```

## Поддержка архитектур

- Образ Docker: `amd64`, `arm64`
- Linux AppImage: `x64`, `arm64`
- Linux DEB: `x64`, `arm64`
- Windows: `x64`, `arm64` (скрипты сборки есть)
- macOS: скрипты сборки (`arm64`, `universal`) для локальных сред
- Android: только universal APK (см. [`android/README.md`](../android/README.md))

## Android

MeshChatX поддерживает нативные Android APK (не только Termux).

### Сборка APK из исходников

Из корня репозитория:

```bash
# 1) Собрать колёса Chaquopy для android/app/build.gradle
bash scripts/build-android-wheels-local.sh

# 2) Собрать universal APK (один debug + один release за прогон; см. android/README.md)
cd android
./gradlew --no-daemon :app:assembleDebug :app:assembleRelease
```

**Один** вариант Android. Gradle синхронизирует весь каталог `meshchatx/` в `app/src/main/python/meshchatx/`, включая офлайн-колёса репозитория. Документированные и публикуемые сборки используют только **universal**: за один прогон один debug APK и один release APK, каждый со всеми нативными ABI из `android/app/build.gradle`.

- Debug: `android/app/build/outputs/apk/debug/app-debug.apk`
- Release: `android/app/build/outputs/apk/release/app-release-unsigned.apk`

Примечания:

- Релизы по умолчанию не подписаны, пока не настроена подпись (`scripts/sign-android-apks.sh`).
- Нативные ABI внутри universal APK задаются в `android/app/build.gradle` (в т.ч. `armeabi-v7a`, если включён). Сборка колёс для `armeabi-v7a` требует Android SDK в `ANDROID_HOME` (см. `android/README.md`).
- Если в корне репо есть `dist/reticulum_meshchatx-*.whl` (например из `python -m build --wheel -o dist .`), обновление встроенного репозитория предпочитает эту wheel пакету MeshChatX с PyPI. В CI wheel собирается до шага Android Gradle.

Дополнительная документация:

- [`docs/meshchatx_on_android_with_termux.md`](../docs/meshchatx_on_android_with_termux.md)
- [`android/README.md`](../android/README.md)

## Конфигурация

| Аргумент                   | Переменная окружения                     | По умолчанию | Описание                                                                                                                                                                              |
| -------------------------- | ---------------------------------------- | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `--host`                   | `MESHCHAT_HOST`                          | `127.0.0.1`  | Адрес привязки веб-сервера                                                                                                                                                            |
| `--port`                   | `MESHCHAT_PORT`                          | `8000`       | Порт веб-сервера                                                                                                                                                                      |
| `--no-https`               | `MESHCHAT_NO_HTTPS`                      | `false`      | Отключить HTTPS                                                                                                                                                                       |
| `--ssl-cert` / `--ssl-key` | `MESHCHAT_SSL_CERT` / `MESHCHAT_SSL_KEY` | (нет)        | Пути к PEM-сертификату и ключу; задаются вместе. Переопределяют автосгенерированные сертификаты в каталоге `ssl/` у идентичности.                                                     |
| `--rns-log-level`          | `MESHCHAT_RNS_LOG_LEVEL`                 | (нет)        | Уровень лога стека Reticulum (RNS): `none`, `critical`, `error`, `warning`, `notice`, `verbose`, `debug`, `extreme` или число. CLI перекрывает переменную окружения, если заданы оба. |
| `--headless`               | `MESHCHAT_HEADLESS`                      | `false`      | Не открывать браузер автоматически                                                                                                                                                    |
| `--auth`                   | `MESHCHAT_AUTH`                          | `false`      | Базовая аутентификация                                                                                                                                                                |
| `--storage-dir`            | `MESHCHAT_STORAGE_DIR`                   | `./storage`  | Каталог данных                                                                                                                                                                        |
| `--public-dir`             | `MESHCHAT_PUBLIC_DIR`                    | авто/bundled | Каталог фронтенда (для установок без встроенных ресурсов)                                                                                                                             |

## Ветки

| Ветка    | Назначение                                                         |
| -------- | ------------------------------------------------------------------ |
| `master` | Стабильные релизы. Только код для продакшена.                      |
| `dev`    | Активная разработка. Возможны нестабильные или неполные изменения. |

## Разработка

Типичные задачи из `Taskfile.yml`:

```bash
task install
task lint:all
task test:all
task build:all
```

Сокращения `Makefile`:

| Команда        | Описание                                |
| -------------- | --------------------------------------- |
| `make install` | Установить зависимости pnpm и poetry    |
| `make run`     | Запуск MeshChatX через poetry           |
| `make build`   | Сборка фронтенда                        |
| `make lint`    | eslint и ruff                           |
| `make test`    | Тесты фронтенда и бэкенда               |
| `make clean`   | Удалить артефакты сборки и node_modules |

## Версионирование

Текущая версия в репозитории: `4.6.0`.

- Редактируйте для релизного бампа **только** поле `version` в **`package.json`**.
- Команда **`pnpm run version:sync`** (также в начале **`pnpm run build`**) распространяет эту версию в **`pyproject.toml`**, **`meshchatx/src/version.py`**, **`THIRD_PARTY_NOTICES.txt`** (строка продукта), **README** / **lang/README.\*** (строки «текущая версия»), **`docs/meshchatx_on_raspberry_pi.md`** (пример pipx) и вспомогательные поля **`packaging/arch/PKGBUILD`**.
- **`meshchatx.__version__`** читается из **`meshchatx/src/version.py`** без импорта **`meshchatx.src`**, поэтому обычный `import meshchatx` остаётся лёгким.
- Записи **changelog** по-прежнему вносятся вручную при релизе.

## Безопасность

- [`SECURITY.md`](../SECURITY.md)
- [`LEGAL.md`](../LEGAL.md)
- Встроенные проверки целостности и значения по умолчанию HTTPS/WSS в рантайме приложения.
- Сборка CI и релизы на GitHub Actions.

## Добавление языка

Авторский рабочий процесс: ArgosTranslate, затем локальная LLM (Qwen 3 + Gemma 4).

Затем правки и улучшения от сообщества приветствуются через LXMF или любой доступный канал.

Обнаружение локали автоматическое. Добавьте файл в `meshchatx/src/frontend/locales/` (например `xx.json`) с теми же ключами, что в `en.json`, и строку верхнего уровня `_languageName` для подписи в селекторе. Можно скопировать `en.json` и перевести вручную; **машинная генерация (в т. ч. Argos) необязательна** и никогда не требуется.

**По желанию: старт с Argos Translate:** для чернового перевода из `en.json` можно вызвать `scripts/argos_translate.py` (форматирование, цветной вывод, защита плейсхолдеров вроде `{count}`).

```bash
# Установите argostranslate при необходимости
pipx install argostranslate

# Запустите скрипт перевода
python scripts/argos_translate.py --from en --to xx --input meshchatx/src/frontend/locales/en.json --output meshchatx/src/frontend/locales/xx.json --name "Название языка"
```

После любой машинной прогонки пусть LLM или человек проверяет грамматику, контекст и тон (например формальный/неформальный стиль).

`pnpm test -- tests/frontend/i18n.test.js --run`: проверка равенства ключей с `en.json`.

Никаких других изменений в коде не требуется. Приложение, селектор языка и тесты обнаруживают локали из каталога `meshchatx/src/frontend/locales/` во время сборки.

## Поддержка проекта

Пожертвования добровольны. Они помогают оплатить время и усилия на разработку этого приложения.

**Как поддержать:** [`donate.md`](../donate.md) (Monero, Ko-Fi, Buy Me a Coffee).

## Авторы

- [Liam Cottle](https://github.com/liamcottle) - оригинальный Reticulum MeshChat
- [RFnexus](https://github.com/RFnexus) - парсер micron (JavaScript)
- [markqvist](https://github.com/markqvist) - Reticulum, LXMF, LXST

## Лицензия

Собственные части проекта лицензированы по 0BSD.
Оригинальные upstream-части из Reticulum MeshChat остаются под MIT.
Полный текст и уведомления см. в [`../LICENSE`](../LICENSE).
