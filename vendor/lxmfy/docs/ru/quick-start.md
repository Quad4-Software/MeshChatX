# Быстрый старт

## Требования

- Python 3.11+
- Reticulum Network Stack (`pip install rns`, версия 1.5.4+)
- LXMF (`pip install lxmf`, версия 1.1.1+; устанавливается автоматически вместе с LXMFy)
- CBOR (`cborx`, устанавливается автоматически, нужен для RRC)

=== "PyPI"

    ``` bash
    pip install lxmfy
    ```

=== "Из исходников"

    ``` bash
    git clone https://github.com/Quad4-Software/LXMFy
    cd LXMFy
    poetry install
    ```

## Создание первого бота (через CLI)

Используйте CLI LXMFy для создания каркаса проекта. Два
способа:

- `lxmfy init` задаёт несколько вопросов (имя, шаблон, хранилище,
  префикс, админы) и записывает готовую к запуску директорию проекта.
- `lxmfy create` записывает один файл бота со значениями по
  умолчанию, без вопросов.

Это руководство использует `lxmfy create`.

1.  **Откройте терминал** в каталоге, где хотите создать проект бота.

2.  **Выполните команду создания:**

    ``` bash
    lxmfy create my_first_bot
    ```

    Эта команда создаст следующие файлы:

    - `my_first_bot.py`: основной файл бота с разумными настройками по умолчанию.
    - `cogs/`: каталог для расширений бота (когов).
    - `cogs/__init__.py`: делает каталог `cogs` пакетом Python.
    - `cogs/basic.py`: пример кога с простыми командами "hello" и "about".
    - `data/`: каталог, где бот хранит данные (по умолчанию JSON).
    - `config/`: каталог, где бот хранит идентификатор и статус анонсов.

3.  **Просмотрите файл `my_first_bot.py`:**

    ``` python
    from lxmfy import LXMFBot

    bot = LXMFBot(
        name="my_first_bot",  # Имя бота, используется в анонсах и идентификаторе
        announce=600,         # Интервал анонсов в секундах (10 минут)
        announce_immediately=True, # Анонсировать при первом запуске?
        admins=set(),         # Множество хэшей LXMF-адресов администраторов
        hot_reloading=False,  # Включить/выключить горячую перезагрузку когов
        rate_limit=5,         # Максимум сообщений в минуту от пользователя
        cooldown=60,          # Период охлаждения в секундах для rate limit
        max_warnings=3,       # Предупреждений до бана за спам
        warning_timeout=300,  # Время (секунды) до сброса предупреждений
        command_prefix="/",   # Префикс команд (например, /hello)
        cogs_dir="cogs",      # Каталог для загрузки когов
        cogs_enabled=True,    # Включить/выключить загрузку когов
        permissions_enabled=False, # Включить/выключить ролевую систему прав
        storage_type="json",  # Бэкенд хранилища ("json", "sqlite", "msgpack" или "memory")
        storage_path="data",  # Путь к файлам хранилища/базе данных
        first_message_enabled=True, # Специальная обработка первых сообщений
        event_logging_enabled=True, # Записывать события в хранилище?
        max_logged_events=1000,   # Максимум событий в журнале
        event_middleware_enabled=True, # Включить middleware событий?
        announce_enabled=True,   # Включить/выключить сетевые анонсы
        signature_verification_enabled=False, # Включить/выключить проверку подписей
        require_message_signatures=False     # Требовать подписи у всех сообщений
    )

    # Чтобы добавить администратора, найдите свой хэш LXMF-адреса и добавьте его сюда:
    # bot.config.admins.add("ваш_lxmf_хэш")
    # bot.admins = bot.config.admins # Чтобы запущенный экземпляр узнал об этом

    # Пример подготовки поля иконки LXMF (необязательно)
    # from lxmfy import IconAppearance, pack_icon_appearance_field
    # try:
    #     icon_data = IconAppearance(icon_name="emoji_objects", fg_color=b'\xFF\xA5\x00', bg_color=b'\x8B\x45\x13') # Оранжевый на коричневом
    #     bot.icon_field = pack_icon_appearance_field(icon_data) # Сохранить для send/reply
    # except Exception as e:
    #     print(f"Не удалось подготовить поле иконки: {e}")
    #     bot.icon_field = None

    if __name__ == "__main__":
        print(f"Запуск бота: {bot.config.name}")
        print(f"LXMF-адрес бота: {bot.local.hash}") # Выводит адрес бота
        bot.run()
    ```

4.  **(Необязательно) Добавьте свой хэш администратора:**

    - Найдите свой хэш LXMF-адреса (например, в клиенте Reticulum, таком как Sideband или NomadNet).
    - Раскомментируйте и отредактируйте строку `bot.config.admins.add(...)` в `my_first_bot.py`, заменив `"your_lxmf_hash_here"` на свой настоящий хэш.

5.  **Запустите бота:**

    ``` bash
    python my_first_bot.py
    ```

    Бот запустится, выведет свой LXMF-адрес, может отправить анонс в сеть Reticulum и начнёт принимать сообщения.

## Взаимодействие с ботом

1.  **Отправьте сообщение** на LXMF-адрес бота из своего клиента.
2.  **Попробуйте пример команды:** отправьте боту `/hello`. Он должен ответить "Hello `<ваш_хэш>`!". Если вы раскомментировали пример с иконкой выше, ответ может также содержать иконку.
3.  **Попробуйте команду помощи:** отправьте `/help`.

Если ничего не приходит, запустите `lxmfy debug` из директории
проекта. Он проверяет конфигурацию Reticulum, интерфейсы, идентичность
и pipeline отправки и сохраняет редактированный отчёт, которым можно
поделиться, прося помощи.

## Что настроить дальше

**Обработчики сообщений**

- `@bot.on_first_message()` для первого сообщения от каждого отправителя
- `@bot.on_message()` для всех сообщений до обработки команд

**Доставка**

- `direct_delivery_retries` в `LXMFBot(...)` повторяет прямую доставку перед откатом на propagation
- `propagation_node` (или `bot.set_propagation_node(...)`) выбирает конкретный узел распространения LXMF
- Персистентность исходящей очереди включена по умолчанию (`message_persistence_enabled=True`) с ограниченной очередью (`message_queue_size`)

**Reticulum Relay Chat (RRC)**

- Подключайтесь к хабам с `rrc_enabled=True` или шаблоном `rrc`
- Используйте ту же конфигурацию Reticulum, что у MeshChatX или вашего хаба (`reticulum_config_dir` или `LXMFY_RETICULUM_CONFIG_DIR`, обычно `~/.reticulum`)
- См. [Создание ботов](creating-bots.md#reticulum-relay-chat-rrc) про комнатных ботов и обнаружение хабов

**Безопасность**

- `signature_verification_enabled=True` проверяет результаты валидации подписей LXMF
- `require_message_signatures=True` отклоняет неподписанные или невалидные сообщения
- В Linux `landlock_enabled=True` (по умолчанию) применяет файловую песочницу Landlock LSM. Переопределяется через `LXMFY_LANDLOCK=0` или `LXMFY_LANDLOCK=1`
- Внешние скриптовые коги могут использовать Landlock, bubblewrap или firejail через `external_cogs_sandbox_type`
- LXMF подписывает исходящие сообщения. LXMFy обеспечивает политику проверки и опциональную изоляцию

**Разработка**

- `make typecheck` запускает `pyright lxmfy`
- `make ci` запускает линт, проверку типов, проверку безопасности, тесты и сборку

См. [Создание ботов](creating-bots.md) и [Справочник API](api-reference.md) про регистрацию команд, коги и детали API.
