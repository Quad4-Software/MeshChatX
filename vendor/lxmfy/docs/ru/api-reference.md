# Основные компоненты

## LXMFBot

Основной класс бота, отвечающий за маршрутизацию сообщений, обработку команд и жизненный цикл бота.

``` python
from lxmfy import LXMFBot

bot = LXMFBot(
    name="MyBot",
    command_prefix="/",
    admins=set(),
    config_path=None,                 # по умолчанию "config" в рабочей директории
    reticulum_config_dir=None,        # или LXMFY_RETICULUM_CONFIG_DIR / "~/.reticulum"
    test_mode=False,                  # пропускает запуск RNS, для тестов
    log_level="INFO",                 # уровень логгера lxmfy, None не трогает логирование
    loglevel=None,                    # уровень логов RNS 0-7, None берёт конфиг reticulum

    # Анонсы
    announce=600,
    announce_immediately=True,
    announce_enabled=True,
    announce_display_name_file=None,  # файл в config_path, переопределяющий
                                      # анонсируемое имя (файл по умолчанию:
                                      # bot_display_name.txt)

    # Защита от спама
    rate_limit=5,
    cooldown=60,
    max_warnings=3,
    warning_timeout=300,

    # Коги
    cogs_dir="cogs",
    cogs_enabled=True,
    dynamic_cogs_enabled=True,
    external_cogs_enabled=True,
    external_cogs_sandbox_enabled=True,
    external_cogs_sandbox_type="auto",  # "auto", "landlock", "bwrap", "firejail", "none"
    external_cogs_timeout=30,
    hot_reloading=False,

    # Хранилище, события, права
    storage_type="json",              # "json", "sqlite", "msgpack" или "memory"
    storage_path="data",
    permissions_enabled=False,
    first_message_enabled=True,
    event_logging_enabled=True,
    max_logged_events=1000,
    event_middleware_enabled=True,

    # Безопасность
    signature_verification_enabled=False,
    require_message_signatures=False,
    require_stamps=False,             # отклоняет сообщения с невалидными stamp
    request_unknown_identities=False, # запрашивает идентичности отправителей у сети
    stamp_cost=None,                  # входящая стоимость stamp, None отключает
    include_tickets=True,             # прикладывает ticket ответа к исходящим
    identity_pinning_enabled=False,
    landlock_enabled=True,

    # Опциональные функции
    nlp_enabled=False,
    nlp_threshold=0.5,
    link_support_enabled=False,
    lxmf_commands_enabled=True,

    # Доставка
    message_persistence_enabled=True,
    message_queue_size=50,
    opportunistic_sending=True,
    direct_delivery_retries=3,
    propagation_fallback_enabled=True,
    propagation_node=None,            # хеш исходящего узла распространения
    autopeer_propagation=False,       # обнаруживает узлы распространения из анонсов
    autopeer_maxdepth=4,              # макс. глубина hops, None = без ограничения
    enable_propagation_node=False,    # запускает этого бота как узел распространения
    message_storage_limit_mb=500,     # лимит хранилища узла, только в режиме узла

    # Отложенные отправки
    pending_sends_enabled=True,       # удерживает отправки к неизвестным адресатам
    pending_sends_max=200,
    pending_sends_ttl=604800,         # 7 дней
    pending_sends_retry=300,          # секунды между проходами повторов

    # RRC
    rrc_enabled=False,
    rrc_hubs=[],
    rrc_rooms=[],
    rrc_nick=None,
    rrc_dest_name="rrc.hub",
    rrc_auto_reconnect=True,
    rrc_persist_sessions=True,
)
```

Все эти опции являются полями `BotConfig`. `LXMFBot(**kwargs)`
пробрасывает каждый именованный аргумент, так что `bot.config` содержит
итоговые значения.

### Ключевые методы

- `run(delay=10)`: Запускает главный цикл бота
- `cleanup()`: Сохраняет очереди, отменяет разговоры и останавливает
  планировщик, роутер и RNS. Вызывается автоматически при выходе из
  `run()`.
- `send(destination, message, title="Reply", lxmf_fields=None, stamp_cost=None, opportunistic=None, method=None, include_ticket=None, defer=None, reply_to=None, quote=None, thread=None)`:
  Отправляет сообщение адресату. `stamp_cost` переопределяет исходящую
  стоимость для этого сообщения, `opportunistic` переопределяет
  `opportunistic_sending`, `include_ticket` переопределяет
  `include_tickets`, а `defer` переопределяет `pending_sends_enabled`.
  `reply_to`, `quote` и `thread` задают поля трединга ответов.
- `send_with_attachment(destination, message, attachment, title="Reply", stamp_cost=None, opportunistic=None)`:
  Отправляет сообщение с вложением
- `command(name, description="No description provided", admin_only=False, permissions=None, usage=None, examples=None, category=None, aliases=None, threaded=False, rate_limit=None)`:
  Декоратор для регистрации команд. `permissions` переопределяет барьер
  `DefaultPerms` (`ALL` при `admin_only`, иначе `USE_COMMANDS`),
  `threaded` выполняет callback в рабочем потоке, `rate_limit`
  ограничивает вызовы на отправителя за окно cooldown, а `usage`,
  `examples`, `category`, `aliases` питают систему помощи. Команды
  поддерживают типизированные аргументы с автоматической конверсией.
- `intent(name, examples)`: Декоратор для регистрации обработчиков
  NLP-интентов.
- `nlp.export_model()`: Экспортирует данные обученной NLP-модели.
- `nlp.import_model(model_data)`: Импортирует ранее экспортированные
  данные NLP-модели.
- `request_link(destination_hash, callback=None, app_name="lxmf", *aspects)`:
  Запрашивает RNS-соединение к адресату. Позволяет свои `app_name` и
  `aspects` (по умолчанию "lxmf" и "delivery").
- `on_link(callback)`: Регистрирует обработчик входящих RNS-соединений.
- `load_extension(name)`: Загружает модуль расширения cog по имени
  (напр. "cogs.utility").
- `reload_extension(name)`: Перезагружает модуль расширения cog.
- `add_cog(cog_instance)`: Добавляет экземпляр класса cog к боту.
- `remove_cog(cog_name)`: Удаляет cog по имени класса.
- `on_first_message()`: Декоратор для обработки первых сообщений от
  пользователей
- `on_message()`: Декоратор для обработки всех сообщений (вызывается
  до обработки команд)
- `received(function)`: Регистрирует callback, вызываемый с контекстом
  сообщения для каждого входящего сообщения, прошедшего pipeline без
  поглощения командой или интентом
- `on_reaction()`: Декоратор для обработки входящих реакций.
  Обработчики получают `(sender, reaction)`, где reaction несёт ключи
  `reaction_to`, `reaction_emoji` и `reaction_sender`
- `react(destination, message_hash, reaction)`: Отправляет реакцию на
  сообщение через поле LXMF `FIELD_REACTION`
- `validate()`: Выполняет проверки конфигурации бота
- `get_landlock_status()`: Возвращает доступность и состояние
  активации песочницы Landlock LSM для процесса бота
- `diagnose_destination(destination, request_path=False, wait=0.0)`:
  Исследует состояние идентичности и пути для хеша адресата
- `diagnose_connectivity(destination=None, request_path=False, wait=0.0)`:
  Выполняет полный doctor-отчёт и возвращает его dict-ом
- `get_debugger()`: Возвращает `Debugger`, привязанный к этому боту
- `set_propagation_node(node_hash)`: Фиксирует исходящий узел
  распространения
- `get_propagation_node_status()`: Состояние настроенных, обнаруженных
  и текущего исходящего узлов распространения
- `set_message_storage_limit(megabytes)`: Лимит хранилища при работе
  как узел распространения
- `get_propagation_storage_stats()`: Использование хранилища узла или
  dict с причиной недоступности
- `connect_rrc(hub_hash, rooms=None, nick=None, dest_name=None, auto_reconnect=None)`:
  Подключается к RRC-хабу как клиент
- `disconnect_rrc(hub_hash=None)`: Отключает одну или все сессии
  RRC-хабов
- `on_rrc(callback=None)`: Декоратор или регистрация обработчика для
  событий RRC (`handler(event, client, payload)`)
- `on_delivery_event(callback=None)`: Подписывается на поток событий
  исходящей доставки, как декоратор или прямой вызов

### Атрибуты

- `config`: Итоговая `BotConfig`
- `commands`, `cogs`: Реестры команд и когов
- `storage`: Активный backend хранилища
- `scheduler`: `TaskScheduler` для cron-подобных задач
- `events`: `EventManager` для обработчиков событий и dispatch
- `middleware`: `MiddlewareManager` для middleware команд
- `permissions`: `PermissionManager` для ролей и флагов
- `spam_protection`: `SpamProtection` для ограничений частоты,
  предупреждений и банов
- `signature_manager`: Слой политики подписей
- `nlp`: Классификатор интентов (матчит только при `nlp_enabled`)
- `delivery`: `DeliveryTracker`, поток исходящих событий
- `conversations`: `ConversationManager` для вопросов `msg.ask`
- `rrc`: `RRCManager` для сессий с несколькими хабами, `None` пока RRC
  не включён или `connect_rrc()` не выполнен
- `local`: `RNS.Destination` бота (его LXMF-адрес это `bot.local.hash`)

## Анонсируемое имя

Имя, которое видят пиры, берётся из `name`, но для анонсов существуют
два переопределения. Если задан `announce_display_name_file` и такой
файл существует в `config_path`, его содержимое побеждает. Иначе
читается `bot_display_name.txt` в `config_path`, если он есть. В обоих
случаях присвоение `bot.name = "Новое имя"` ресинхронизирует
анонсируемое имя во время выполнения.

Это позволяет операторам переименовывать бота без изменения кода, а
анонсируемое имя может отличаться от внутреннего имени в
конфигурации.

## Структурированные команды через поля LXMF

Боты могут принимать команды, отправленные через `FIELD_COMMANDS` (`0x09`) LXMF, и автоматически отвечать с `FIELD_RESULTS` (`0x0A`). Это даёт структурированные запросы и ответы наряду с обычными текстовыми командами.

Входящие `FIELD_COMMANDS` разбираются и направляются через тот же реестр команд, что и текстовые, с общими проверками прав, разбором аргументов по аннотациям, потоками и middleware.

``` python
from lxmfy import LXMFBot, FIELD_COMMANDS, FIELD_RESULTS, pack_result, unpack_commands

bot = LXMFBot(name="FieldBot")

@bot.command(name="status", description="Return bot status")
def status_cmd(ctx):
    # ctx.fields содержит исходный словарь полей LXMF
    # ctx.request_id устанавливается автоматически, если команда его включала
    ctx.reply("Bot is online")

# Отправка структурированной команды из другого клиента LXMF:
# lxm.fields[FIELD_COMMANDS] = {"command": "status", "args": [], "request_id": "abc123"}
# router.handle_outbound(lxm)

# Ответ бота автоматически включает FIELD_RESULTS с ответом и request_id.
```

Чтобы отключить обработку полевых команд, установите `lxmf_commands_enabled=False` в `BotConfig`.

## Реакции

Реакции передаются полем `FIELD_REACTION` (`0x40`) LXMF поверх пустого сообщения. `pack_reaction` и `unpack_reaction` собирают и разбирают это поле.

``` python
from lxmfy import pack_reaction, unpack_reaction

# Отправка реакции на сообщение
bot.react(destination_hash, message_hash_hex, "\U0001F44D")

# Приём реакций
@bot.on_reaction()
def on_reaction(sender, reaction):
    # reaction["reaction_to"]  — hex-хэш целевого сообщения
    # reaction["reaction_emoji"] — текст реакции (до 16 символов)
    # reaction["reaction_sender"] — отправитель
    print(f"{sender} reacted {reaction['reaction_emoji']} to {reaction['reaction_to']}")
    return True
```

Текст реакции обрезается до 16 печатаемых символов. Исходное поле остаётся доступным в `ctx.fields` и `msg.fields` для совместимости.

## Трединг ответов

Ответы могут нести поля LXMF `FIELD_REPLY_TO` (`0x30`),
`FIELD_REPLY_QUOTE` (`0x31`) и `FIELD_THREAD` (`0x08`). Клиенты,
рендерящие треды, как MeshChatX и Sideband, показывают их как
настоящие цитированные ответы вместо плоских сообщений.

`msg.reply()` тредит автоматически: устанавливает `FIELD_REPLY_TO` в
хеш входящего сообщения и `FIELD_THREAD` в корень разговора.

``` python
@bot.command("status")
def status(msg):
    msg.reply("all systems nominal")          # тредованный ответ
    msg.reply("flat", reply_to=None)          # отказаться от трединга
    msg.reply("noted", quote=True)            # цитирует входящий текст
```

Для отправок, не являющихся ответами, передавайте поля явно:

``` python
bot.send(dest, "see above", reply_to=msg_hash_hex, quote="earlier text")
```

Входящие ответы парсятся в контекст сообщения:

``` python
@bot.command("ctx")
def ctx_cmd(msg):
    msg.reply_to      # hex-хеш, на который отвечает это сообщение, или None
    msg.reply_quote   # цитируемый текст ответа, или None
    msg.thread        # hex-хеш корня треда, или None
```

`pack_reply(message_hash, quote=..., thread=...)` и
`unpack_reply(fields)` экспортируются для ручной обработки полей.

## Разговоры

Команды могут задавать отправителю вопрос и трактовать его следующее
сообщение как ответ, вместо диспетчеризации как команды:

``` python
@bot.command("report")
def report(msg):
    title = msg.ask("Report title?", timeout=300)
    if title is None:
        msg.reply("Timed out.")
        return
    body = msg.ask("Describe the issue.", timeout=600)
    if body is None:
        msg.reply("Timed out.")
        return
    msg.reply(f"Filed: {title.content}")
```

`msg.ask(prompt, timeout=..., validator=...)` блокирует обработчик,
пока не придёт ответ, не сработает timeout или разговор не будет
отменён. Возвращает `Answer` с `content`, `fields`, `hash`, `sender`
и шорткатом `reply(text)`.

Валидатор отклоняет плохие ответы и переспрашивает:

``` python
num = msg.ask(
    "Pick a number",
    validator=lambda a: None if a.content.isdigit() else "Digits only",
)
```

В асинхронных обработчиках команд используйте `await
msg.ask_async(...)`. Для долгих ожиданий или когда может быть много
открытых разговоров, используйте стиль колбеков, чтобы ни один поток
не оставался припаркованным:

``` python
msg.ask(
    "Send the log file",
    on_answer=lambda ans: ans.reply("received"),
    on_timeout=lambda sender: bot.send(sender, "Too slow."),
    timeout=3600,
)
```

Заметки:

- Отправка зарегистрированной команды во время ожидания вопроса
  отменяет вопрос и выполняет команду. У пользователей всегда есть
  выход.
- `bot.conversations.pending_count()` и
  `bot.conversations.cancel(sender)` открывают реестр для диагностики
  и административных инструментов.
- Реестр ограничен 1024 ожидающими вопросами. `ask` возвращает `None`,
  когда он заполнен.
- Блокирующий `ask` паркует поток доставки, обрабатывающий это
  сообщение. Это безопасно для прямых доставок, но боты,
  синхронизирующие большие пачки с узла распространения, должны
  предпочитать колбеки `on_answer`.

## Хранилище

Фреймворк предоставляет три бэкенда хранилища:

### JSONStorage

``` python
from lxmfy import JSONStorage

storage = JSONStorage("data")
```

### SQLiteStorage

``` python
from lxmfy import SQLiteStorage

storage = SQLiteStorage("data/bot.db")
```

### MsgPackStorage

``` python
from lxmfy.storage import MsgPackStorage

storage = MsgPackStorage("data") # {key}.msgpack files
```

### MemoryStorage

``` python
from lxmfy.storage import MemoryStorage

storage = MemoryStorage() # Полностью в памяти
```

## Команды

Регистрация и обработка команд:

``` python
@bot.command(name="hello", description="Says hello")
def hello(ctx):
    ctx.reply(f"Hello {ctx.sender}!")
```

Метаданные помощи и контроль доступа приходят из дополнительных
kwarg-ов декоратора:

``` python
from lxmfy import DefaultPerms

@bot.command(
    name="purge",
    description="Clear stored data",
    permissions=DefaultPerms.MANAGE_MESSAGES,
    usage="/purge <key>",
    examples=["/purge cache"],
    category="Admin",
    aliases=["clear"],
)
def purge(ctx, key: str):
    bot.storage.delete(key)
    ctx.reply(f"Deleted {key}")
```

`permissions` переопределяет барьер по умолчанию: `USE_COMMANDS` для
обычных команд, `ALL` для `admin_only`. `category` группирует команду
в выводе `/help`. `aliases` являются только метаданными помощи: алиасы
показываются пользователям, но не регистрируются для dispatch, так что
`/clear` не выполнит `purge`, если только вы не зарегистрируете его
как вторую команду.

### Аргументы с аннотациями типов

Команды автоматически разбирают и преобразуют аргументы на основе аннотаций типов в функции-обработчике.

``` python
@bot.command(name="add", description="Adds two numbers")
def add(ctx, a: int, b: int):
    result = a + b
    ctx.reply(f"The result is {result}")
```

### Ограничения частоты для отдельной команды

Ограничивает, как часто один отправитель может вызывать команду в
рамках глобального окна `cooldown`. При достижении отклоняется только
вызов, никаких предупреждений или банов.

``` python
@bot.command(name="report", rate_limit=3)
def report(ctx):
    # каждый отправитель может вызвать это 3 раза за период cooldown
    ...
```

Требует `permissions_enabled=True`, как и глобальное ограничение.
Пользователи с ролью admin или `BYPASS_SPAM` пропускают проверку.

## Защита от спама

`bot.spam_protection` обеспечивает глобальное ограничение: отправитель
может послать `rate_limit` сообщений в рамках каждого окна `cooldown`.
Превышение добавляет предупреждение и отклоняет сообщение. На
`max_warnings` отправителя банят. Предупреждения истекают через
`warning_timeout` секунд без нарушений.

Проверки спама выполняются внутри события `message_received` и
требуют `permissions_enabled=True`.

``` python
bot = LXMFBot(
    name="GuardedBot",
    permissions_enabled=True,
    rate_limit=5,        # сообщений за окно cooldown
    cooldown=60,         # длительность окна в секундах
    max_warnings=3,      # предупреждений до бана
    warning_timeout=300, # секунд до сброса предупреждений
)

# Снять бан вручную
bot.spam_protection.unban(sender_hash)
```

Предупреждения, баны и счётчики персистятся в настроенном backend
хранилища, так что баны переживают рестарты. Отправители с
`BYPASS_SPAM` никогда не ограничиваются и не банятся. Покомандное
`rate_limit` в `@bot.command` мягче: оно только отклоняет вызов и
никогда не предупреждает и не банит.

## Система помощи

Фреймворк включает интерактивный генератор помощи с категоризированными меню на основе метаданных когов и команд.

``` python
# Команда help регистрируется автоматически.
# Пользователи могут использовать '/help' или '/help <command>'
```

## Потоковые команды

Для долгих или блокирующих операций, которые не взаимодействуют напрямую с Reticulum Network Stack, команды можно запускать в отдельном потоке, чтобы бот оставался отзывчивым.

``` python
import time

@bot.command(name="long_task", description="Performs a long-running task in a separate thread", threaded=True)
def long_task_command(ctx):
    ctx.reply("Starting a long task... please wait.")
    time.sleep(10) # Выполняется в отдельном потоке
    ctx.reply("Long task completed!")
```

!!! warning "Потокобезопасность"

    Функции с `threaded=True` **не должны** напрямую взаимодействовать с
    Reticulum Network Stack (RNS) или компонентами, зависящими от
    `lxmfy.transport.py`, так как они в общем случае не потокобезопасны.
    Используйте `ctx.reply()` для отправки сообщений пользователю из
    потоковой команды.

## События

Система событий для обработки различных событий бота:

``` python
@bot.events.on("message_received", EventPriority.HIGHEST)
def handle_message(event):
    # event.data несёт полезную нагрузку, напр. sender и message
    event.cancel()  # останавливает последующих обработчиков и дальнейшую обработку
```

Обработчики выполняются в порядке `EventPriority`: `HIGHEST`, `HIGH`,
`NORMAL`, `LOW`. Сама проверка спама является обработчиком
`message_received` с `HIGHEST`, так что отмена этого события является
механизмом, которым ограничитель отбрасывает сообщения.

Диспетчеризируйте свои события:

``` python
from lxmfy import Event

bot.events.dispatch(Event("order_placed", data={"user": ctx.sender}))
```

`event_logging_enabled`, `max_logged_events` и
`event_middleware_enabled` существуют в `BotConfig`, но не подключены:
события не пишутся в хранилище, а `bot.events.use()` является stub.
Считайте их зарезервированными.

## Тестирование

`lxmfy.testing.TestBot` является `LXMFBot`, предварительно настроенный
для тестов. Никакой экземпляр Reticulum не запускается. Входящие
сообщения проходят настоящий pipeline получения (middleware, проверки
спама, права, dispatch), а исходящие отправки захватываются для
утверждений.

``` python
from lxmfy import TestBot

def test_ping():
    with TestBot() as bot:
        @bot.command("ping")
        def ping(msg):
            msg.reply("pong")

        sent = bot.receive("/ping", sender="alice")
        assert sent[0].content == "pong"
        assert sent[0].destination == bot.sender_hex("alice")
```

- `bot.receive(content, sender=..., fields=..., message_hash=...)`
  вводит сообщение и возвращает созданные объекты `SentMessage`.
  Отправители именованные: `"alice"` мапится на стабильный фейковый
  хеш, или передайте hex-хеш адресата напрямую.
- `bot.drain()` вытягивает исходящие сообщения из очереди. `bot.outbox`
  накапливает всё отправленное. `bot.last_sent(sender=...)` достаёт
  последнее.
- `bot.wait_sent(n, timeout=...)` ждёт потоковые команды.
- `bot.receive_later(content, sender=..., delay=...)` отвечает на
  блокирующие вызовы `msg.ask` из daemon-потока.
- `fake_message(content, source_hash=..., ...)` строит входящее
  сообщение для прямого вызова `bot._message_received`.

`SentMessage` оборачивает каждое захваченное исходящее сообщение:
`destination` (hex), `content`, `title`, `fields`, `method`,
`include_ticket`, `stamp_cost` и `raw` для базового объекта.

Тестовый набор репозитория также включает сценарии надёжности и
стресса. Запускайте их тестовым раннером репозитория.

### Расширенный набор проверок надёжности

Фреймворк включает обширный набор автоматизированных тестов для суровых условий:

- **Manifold Testing**: проверка математической топологии векторного пространства намерений NLP.
- **Chaos Engineering**: симуляция битовой гнили, отказа SD-карты и порчи хранилища.
- **Temporal Drift**: проверка устойчивости к скачкам системных часов (±1 год).
- **Leak Detection**: долгосрочное отслеживание памяти, файловых дескрипторов и потоков.

## Права доступа

Система прав для контроля доступа к возможностям бота:

``` python
from lxmfy import DefaultPerms

@bot.command(name="admin", description="Admin command", admin_only=True)
def admin_command(ctx):
    if ctx.is_admin:
        ctx.reply("Admin command executed")
```

Включите через `permissions_enabled=True`. Флаги
`DefaultPerms`:

- `USE_BOT`, `SEND_MESSAGES`, `USE_COMMANDS`: базовый доступ
- `MANAGE_MESSAGES`, `MANAGE_COMMANDS`, `MANAGE_USERS`: повышенный
- `BYPASS_RATELIMIT`, `BYPASS_SPAM`, `VIEW_ADMIN_COMMANDS`: специальные
- `VIEW_EVENTS`, `MANAGE_EVENTS`, `BYPASS_EVENT_CHECKS`: система событий
- `NONE`, `ALL`: шорткаты

`bot.permissions` управляет ролями и назначениями:

``` python
bot.permissions.create_role("moderator", DefaultPerms.MANAGE_MESSAGES | DefaultPerms.BYPASS_SPAM)
bot.permissions.assign_role(user_hash, "moderator")
bot.permissions.remove_role(user_hash, "moderator")
bot.permissions.has_permission(user_hash, DefaultPerms.USE_COMMANDS)
```

Роли и назначения персистятся в настроенном backend хранилища.
Существуют две встроенные роли, которые нельзя удалить: `user`
(по умолчанию) и `admin`, автоматически выдаваемая каждому хешу в
`admins`.

## Middleware

Система middleware для обработки сообщений и событий:

``` python
from lxmfy import MiddlewareType

@bot.middleware.register(MiddlewareType.PRE_COMMAND)
def pre_command_middleware(ctx):
    # ctx оборачивает контекст сообщения, ctx.cancelled отбрасывает его
    if "spamword" in ctx.data.content:
        ctx.cancel()
```

Три точки pipeline выполняют middleware:

- `PRE_COMMAND`: до dispatch команд, после проверок спама. Если
  цепочка возвращает `None`, сообщение полностью отменяется.
- `POST_COMMAND`: после callback команды (включая потоковые команды,
  срабатывающие в рабочем потоке).
- `PRE_EVENT`: до dispatch события `message_received`.

`POST_EVENT`, `REQUEST` и `RESPONSE` существуют в `MiddlewareType`, но
ничто в pipeline их пока не выполняет.

## Вложения

Поддержка отправки файлов, изображений и аудио:

``` python
from lxmfy import Attachment, AttachmentType

attachment = Attachment(
    type=AttachmentType.IMAGE,
    name="image.jpg",
    data=image_data,
    format="jpg"
)
bot.send_with_attachment(destination, "Here's an image", attachment)
```

## Внешний вид иконки (поле LXMF)

Боту можно назначить пользовательскую иконку, которую отображают совместимые клиенты LXMF. Используется `LXMF.FIELD_ICON_APPEARANCE`.

``` python
from lxmfy import IconAppearance, pack_icon_appearance_field
import LXMF # Требуется для LXMF.FIELD_ICON_APPEARANCE

# Определяем внешний вид иконки
icon_data = IconAppearance(
    icon_name="smart_toy",  # Имя из Material Symbols
    fg_color=b'\xFF\xFF\xFF',  # Белый передний план (3 байта)
    bg_color=b'\x4A\x90\xE2'   # Синий фон (3 байта)
)

# Упаковываем в формат поля LXMF
icon_lxmf_field = pack_icon_appearance_field(icon_data)

# Отправляем сообщение с этой иконкой
bot.send(
    destination_hash_str,
    "Hello from your friendly bot!",
    title="Bot Message",
    lxmf_fields=icon_lxmf_field
)

# Можно комбинировать с другими полями, например с вложениями:
# attachment_field = pack_attachment(some_attachment)
# combined_fields = {**icon_lxmf_field, **attachment_field}
# bot.send(destination, "Message with icon and attachment", lxmf_fields=combined_fields)
```

## Планировщик

Система планирования задач:

``` python
@bot.scheduler.schedule(name="daily_task", cron_expr="0 0 * * *")
def daily_task():
    # Выполняется ежедневно в полночь
    pass
```

## Подписи

LXMFy предоставляет настройки для встроенной криптографической подписи и проверки сообщений LXMF:

``` python
from lxmfy import LXMFBot

bot = LXMFBot(
    name="SecureBot",
    signature_verification_enabled=True,  # Включить проверку подписей
    require_message_signatures=False      # True — отклонять неподписанные сообщения
)
```

!!! note "Обработка подписей"

    LXMF автоматически выполняет все криптографические операции подписи и
    проверки с идентификаторами RNS. `SignatureManager` в LXMFy - это
    слой конфигурации, который:

    - Управляет тем, применять ли проверку подписей
    - Определяет политику для неподписанных сообщений (принимать или
      отклонять)
    - Интегрируется с системой прав (например, обход проверки для
      доверенных пользователей)

Сами криптографические операции выполняет LXMF/RNS, а не LXMFy.

### Песочница Landlock LSM

На ядрах Linux с поддержкой Landlock (5.13+) LXMFy может ограничивать доступ к файловой системе для процесса бота и для внешних скриптовых когов.

**Песочница процесса бота**

Когда `landlock_enabled=True` (по умолчанию) и бот не запущен в `test_mode`, бот вызывает `apply_landlock_sandbox()` при инициализации. Системные каталоги доступны только для чтения; хранилище бота, конфигурация, коги, конфигурация Reticulum и временные пути остаются записываемыми.

``` python
bot = LXMFBot(
    name="SecureBot",
    landlock_enabled=True,
)

status = bot.get_landlock_status()
# ключи status: landlock_kernel_supported, landlock_requested,
# landlock_auto_enabled, landlock_disabled_by_env, landlock_active
```

**Переопределение через окружение**

- `LXMFY_LANDLOCK=0`: отключить Landlock даже на поддерживаемых ядрах
- `LXMFY_LANDLOCK=1`: попытаться применить Landlock в Linux независимо от автоопределения
- не задано: следовать `landlock_enabled` и автоопределению ядра

**Песочница внешних когов**

Скриптовые коги используют `external_cogs_sandbox_type`. В режиме `auto` предпочитается Landlock, так как ему не нужны внешние инструменты. Полный список вариантов песочницы — в руководстве [Создание ботов](creating-bots.md).

### Закрепление идентификатора

LXMFy поддерживает опциональное закрепление идентификатора (pinning) для защиты от подмены при ротации или компрометации идентификатора. Когда включено, бот «закрепляет» LXMF-адрес за первым увиденным открытым ключом.

``` python
bot = LXMFBot(
    identity_pinning_enabled=True
)
```

### Методы SignatureManager

`SignatureManager` доступен как `bot.signature_manager`, когда `signature_verification_enabled=True`:

- `should_verify_message(sender)`: определить, нужно ли проверять сообщение от данного отправителя
- `handle_unsigned_message(sender, message_hash)`: обработать сообщения без валидной подписи согласно политике

### Как работают подписи LXMF

LXMF автоматически подписывает все исходящие сообщения идентификатором RNS отправителя во время операции `pack()`. При получении сообщений LXMF проверяет подписи и предоставляет:

- `message.signature_validated`: булево значение валидности подписи
- `message.unverified_reason`: код причины при неудачной проверке (например, `SIGNATURE_INVALID`, `SOURCE_UNKNOWN`)

LXMFy использует эти встроенные свойства LXMF для применения политики подписей бота.

## Доставка сообщений

LXMFy предоставляет расширенные возможности доставки, включая узлы распространения и автоматические повторы:

### Узлы распространения

Отправка сообщений через конкретные узлы распространения для повышения надёжности в сети Reticulum:

``` python
# Настройте узел распространения один раз на уровне конфигурации/времени выполнения
bot.set_propagation_node("<propagation_node_hash>")

# Отправка с настроенным поведением доставки
bot.send(
    destination_hash,
    "Message content"
)

# Хэш узла распространения должен быть валидным узлом распространения LXMF
# в сети Reticulum
```

Узел также можно задать при создании через
`propagation_node="<hash>"`, или бот может находить узлы сам:

``` python
bot = LXMFBot(
    name="AutoBot",
    autopeer_propagation=True, # учит узлы из анонсов
    autopeer_maxdepth=4,       # игнорирует узлы глубже 4 hops
)
```

`bot.get_propagation_node_status()` сообщает о ручном узле,
обнаруженных узлах и исходящем узле, используемом в данный момент.

### Автоматические повторы

Настройка автоматических повторных попыток для неудачных прямых доставок:

``` python
bot = LXMFBot(
    name="ReliableBot",
    direct_delivery_retries=5,  # Повторять прямую доставку до 5 раз
    propagation_fallback_enabled=True
)

bot.send(destination_hash, "Important message")

# direct_delivery_retries по умолчанию равно 3
# Логика повторов автоматически обрабатывает обратные вызовы доставки
```

Система повторов отслеживает попытки доставки по каждому получателю и автоматически повторяет неудачные доставки. Успешные доставки сбрасывают счётчик повторов для этого получателя.

### Отложенные отправки

Отправка адресату, чью идентичность узел ещё не слышал, обычно сразу
проваливается. С `pending_sends_enabled` (по умолчанию) сообщение
вместо этого удерживается в хранилище, а затем автоматически
выталкивается, когда адресат анонсируется или при периодическом
проходе.

``` python
bot = LXMFBot(
    pending_sends_enabled=True,
    pending_sends_max=200,     # самые старые удержанные сообщения выпадают сверх этого
    pending_sends_ttl=604800,  # удержанные сообщения истекают через 7 дней
    pending_sends_retry=300,   # секунды между проходами в run()
)

# Переопределение для отдельной отправки
bot.send(dest, "hold this", defer=True)
bot.send(dest, "send or drop", defer=False)
```

Удержанные отправки появляются как `held (unknown peers)` в
административной команде `/queue` и создают события `deferred` в
трекере доставки.

### Персистентность сообщений

Исходящие сообщения можно сохранять на диск, чтобы они доставлялись даже после перезапуска бота. Персистентность включена по умолчанию. Очередь исходящих в памяти ограничена (`message_queue_size`, по умолчанию 50) и при переполнении отбрасывает самое старое сообщение. Невалидные хэши получателей не восстанавливаются.

``` python
bot = LXMFBot(
    message_persistence_enabled=True,
    message_queue_size=50,
)
```

### Stamp-ы и ticket-ы

Стоимость stamp заставляет отправителей выполнять proof-of-work до
того, как их сообщение будет принято, что сдерживает нежелательный
трафик. LXMFy открывает обе стороны механизма.

``` python
bot = LXMFBot(
    stamp_cost=16,          # требует эту входящую стоимость stamp
    require_stamps=True,    # отклоняет сообщения с невалидными stamp
    include_tickets=True,   # позволяет пирам отвечать без генерации stamp
)
```

- `stamp_cost` является входящим требованием. Исходящая стоимость отправки
  по-прежнему берётся из анонса пира, если только вы не передадите
  `stamp_cost=` в `bot.send()`.
- `include_tickets` (по умолчанию True) прикладывает ticket ответа к
  исходящим сообщениям, так что пир с требованием stamp может
  ответить без оплаты. Переопределяйте для отдельной отправки через
  `include_ticket=`.
- `request_unknown_identities=True` запрашивает у сети идентичность
  отправителя, когда сообщение приходит из неизвестного источника,
  что помогает проверкам stamp и подписей разрешиться вместо слепого
  провала.

Контроль во время выполнения лежит в разделе «Управление роутером»: `set_inbound_stamp_cost`,
`enforce_stamps`, `ignore_stamps`, `generate_ticket` и методы
инспекции ticket-ов.

### Работа как узел распространения

Бот может одновременно быть узлом распространения LXMF, храня
сообщения для пиров, которые офлайн:

``` python
bot = LXMFBot(
    enable_propagation_node=True,
    message_storage_limit_mb=500,
)

bot.set_message_storage_limit(750)
stats = bot.get_propagation_storage_stats()
```

`get_propagation_node_status()` работает для обеих ролей: сообщает об
исходящем узле, который этот бот использует, и о том, является ли он
сам узлом. Связанные контроли: `announce_propagation_node()`
рекламирует узел, `set_retain_on_node()` сохраняет доставленные
сообщения на нём, а `allow_control_identity()` /
`disallow_control_identity()` управляют тем, какие идентичности могут
использовать контрольный канал узла.

### События доставки

`bot.delivery` записывает ограниченный поток событий исходящего
жизненного цикла, чтобы наблюдать поток сообщений без чтения логов.
Стадии: `queued`, `deferred`, `dispatched`, `delivered`, `failed`,
`cancelled`, `dropped`. Недавний хвост персистится в хранилище и
восстанавливается при запуске.

``` python
@bot.on_delivery_event()
def watch(event):
    print(event["stage"], event.get("destination"), event.get("reason"))

# Или прямая инспекция
recent = bot.delivery.recent(20)
failures = bot.delivery.recent(stage="failed")
to_peer = bot.delivery.recent(destination="aa11bb...")
```

Каждое событие является dict-ом с `ts`, `stage` и опционально `destination`,
`message_id`, `hash`, `method`, `attempts`, `reason`, `title`.

Админы получают команду `/delivery [limit]`, рендерящую ту же
хронологию в чате, а `lxmfy debug` показывает сводку хронологии
доставки в проверках pipeline отправки.

### Встроенные административные команды

Эти команды регистрируются автоматически и требуют, чтобы отправитель
был в `admins`, когда права включены:

| Команда | Действие |
| --- | --- |
| `/queue` | Показывает исходящую очередь роутера, внутреннюю очередь и удержанные отправки |
| `/cancel <id|all>` | Отменяет ожидающие исходящие сообщения |
| `/inbox [cancel <hash|all>]` | Перечисляет или отменяет активные входящие передачи |
| `/delivery [n]` | Показывает последние n событий доставки (по умолчанию 15, макс. 50) |
| `/loadext <name>` | Загружает расширение cog |
| `/reloadext <name>` | Перезагружает загруженное расширение cog |

### Управление роутером

Тонкие обёртки над базовым `LXMRouter` для управления отправителями,
ticket-ами, управления исходящей очередью и синхронизации узла
распространения. Все принимают хеши адресатов как hex-строки и
возвращают `False`, когда роутер не работает (например в
`test_mode`).

**Управление отправителями (входящее)**

- `ignore_destination(destination)` / `unignore_destination(destination)` / `is_ignored(destination)`:
  Отбрасывает входящие сообщения от отправителя
- `allow_destination(destination)` / `disallow_destination(destination)`:
  Управление whitelist, когда роутер работает в режиме allow-list
- `prioritise_destination(destination)` / `unprioritise_destination(destination)`:
  Список приоритетных отправителей
- `set_inbound_stamp_cost(stamp_cost)`: Требует стоимость stamp на
  входящих сообщениях (`None` очищает)
- `enforce_stamps()` / `ignore_stamps()`: Переключатели требования
  входящих stamp-ов

**Ticket-ы**

- `generate_ticket(destination, expiry=None)`: Выдаёт входящий
  stamp-ticket для отправителя
- `get_inbound_tickets(destination)`: Ticket-ы, удерживаемые для
  отправителя
- `get_outbound_ticket(destination)` / `get_outbound_ticket_expiry(destination)` /
  `get_outbound_stamp_cost(destination)`: Состояние исходящего
  ticket-а, узнанное из сети

**Исходящая очередь**

- `outbound_queue()`: Снимок ожидающих исходящих сообщений
- `get_outbound_progress(lxm_hash)`: Прогресс доставки для хеша
  сообщения или `None`
- `cancel_outbound(message_id)`: Удаляет сообщение из очереди до
  доставки
- `delivery_link_available(destination)`: Существует ли активное
  RNS-соединение к адресату

**Входящая очередь**

- `has_message(message_hash)`: Был ли уже доставлен входящий LXM-хеш
- `inbound_count()`: Активные входящие передачи ресурсов в процессе
- `inbound_transfers()`: Снимок каждой передачи с хешем, размером,
  прогрессом и статусом
- `cancel_inbound(resource_hash)`: Прерывает активную входящую
  передачу
- `cancel_all_inbound()`: Прерывает все активные входящие передачи,
  возвращает отменённое количество

**Обнаружение пиров**

Метаданные анонсов для адресатов, которых слышал этот узел:

- `get_peer_app_data(destination)`: Сырые байты анонсированных
  app_data
- `get_peer_lxmf_data(destination)`: Декодированные метаданные
  LXMF-анонса (`display_name`, `stamp_cost`, `capabilities`) или
  `None`, когда пир не анонсировал валидные данные LXMF
- `get_peer_announce(destination)`: Полная запись анонса с hops,
  received_at, interface и app_data
- `list_peer_announces(limit=100)`: Все услышанные анонсы, новейшие
  первыми

**Распространение**

- `sync_propagation_node(max_messages=None)`: Тянет сообщения с
  настроенного узла распространения
- `cancel_propagation_sync()`: Останавливает текущую синхронизацию
- `get_propagation_stats()`: Состояние передачи и лимиты узла или
  `None`
- `set_retain_on_node(retain)`: Сохраняет доставленные сообщения на
  узле
- `announce_propagation_node()`: Анонсирует этот узел как узел
  распространения
- `allow_control_identity(destination)` / `disallow_control_identity(destination)`:
  Whitelist контрольного канала распространения

**Приём**

- `ingest_lxm_uri(uri)`: Импортирует сообщение URI `lxm://` во
  входящую очередь

## Диагностика

Когда сообщения не текут, отладчик проверяет весь путь вместо
угадывания: конфигурацию Reticulum, состояние общего экземпляра,
интерфейсы, идентичность, поведение анонсов, конфигурацию доставки и
pipeline отправки.

``` bash
lxmfy debug                          # полный doctor-отчёт, сохранённый в файл
lxmfy debug probe <hash> --request-path --wait 30
lxmfy debug send <hash>              # отслеживает тестовую отправку
lxmfy debug receive                  # проверяет готовность приёма
lxmfy debug compare <hash_a> <hash_b>
lxmfy debug tips                     # исправления распространённых сбоев
```

Отчёты по умолчанию редактируются ради приватности: домашние пути и
хеши обрезаются. `--json` выдаёт машиночитаемый вывод, `-o ФАЙЛ`
записывает отчёт, `--no-save` пропускает файл, `--no-privacy`
сохраняет полные значения для локального использования, а `--no-color`
или `NO_COLOR` отключает ANSI-вывод.

Те же проверки можно вызывать из кода:

``` python
report = bot.diagnose_connectivity()            # doctor-отчёт как dict
probe = bot.diagnose_destination(               # исследование идентичности и пути
    "<peer_hash>", request_path=True, wait=30,
)

debugger = bot.get_debugger()                   # полный API
checks = debugger.check_send_pipeline()
verdict = debugger.run_doctor(destination)
```

`lxmfy/debugger.py` также экспортирует самостоятельный помощник
`diagnose_destination(hash, ...)` плюс типы отчётов `CheckResult`,
`DestinationProbe`, `DoctorReport` и `MessageDebugger` для собственных
инструментов.

## Обработчики сообщений

LXMFy предоставляет декораторы для обработки разных типов входящих сообщений:

### Обработчик первого сообщения

Обработка первого сообщения от каждого пользователя:

``` python
@bot.on_first_message()
def welcome_user(sender, message):
    content = message.content.decode("utf-8")
    bot.send(sender, f"Welcome! You said: {content}")
    return True  # Верните True, чтобы остановить дальнейшую обработку
```

### Общий обработчик сообщений

Обработка всех входящих сообщений до обработки команд:

``` python
@bot.on_message()
def handle_all_messages(sender, message):
    content = message.content.decode("utf-8").strip()

    # Своя логика здесь
    if content.startswith("echo:"):
        bot.send(sender, content[5:])
        return True  # Остановить дальнейшую обработку

    return False  # Перейти к обработке команд
```

Обработчики сообщений вызываются в таком порядке: 1. обработчик первого сообщения (если это первое сообщение от отправителя) 2. общие обработчики (зарегистрированные через `on_message()`) 3. обработка команд (если сообщение начинается с префикса команды)

### Резервный callback

`bot.received(fn)` регистрирует callback, выполняемый в конце pipeline
для сообщений, которые ничто другое не поглотило: ни обработчик
первого сообщения, ни обработчик `on_message` с возвратом True, ни
подходящая команда или NLP-интент. Callback получает тот же контекст
сообщения, что и команды, с `msg.sender`, `msg.content`,
`msg.reply()` и прочим.

``` python
@bot.received
def fallback(msg):
    msg.reply("Sorry, I did not understand that.")
```

Используйте как универсальный обработчик для свободного текста.

## Reticulum Relay Chat (RRC)

Боты могут подключаться к хабам [RRC](https://rrc.kc1awv.net/) по RNS Link с конвертами CBOR. Пакет: `lxmfy.rrc`.

### Опции BotConfig

- `rrc_enabled` (bool, по умолчанию `False`): подключать настроенные хабы при запуске
- `rrc_hubs` (список hex-хэшей): хэши получателей хабов
- `rrc_rooms` (список строк): комнаты для авто-join после WELCOME
- `rrc_nick` (строка или None): никнейм в HELLO и сообщениях комнат
- `rrc_dest_name` (строка, по умолчанию `"rrc.hub"`): имя получателя для построения destination хаба
- `rrc_auto_reconnect` (bool, по умолчанию `True`): переподключение после потери link
- `rrc_persist_sessions` (bool, по умолчанию `True`): сохранять хабы и комнаты между перезапусками
- `reticulum_config_dir` (строка или None): каталог конфигурации Reticulum. Также задаётся через `LXMFY_RETICULUM_CONFIG_DIR`. Используйте ту же конфигурацию, что у MeshChatX (часто `~/.reticulum`), чтобы анонсы хаба были видны.

### Пример

``` python
from lxmfy import LXMFBot, RRCMessage

bot = LXMFBot(
    name="RoomBot",
    reticulum_config_dir="~/.reticulum",
    rrc_enabled=True,
    rrc_hubs=["664fc0e8d2e448658e37bb3f34e6c88f"],
    rrc_rooms=["general"],
    rrc_nick="RoomBot",
)

@bot.on_rrc
def on_rrc(event, client, payload):
    if event == "msg" and isinstance(payload, RRCMessage) and payload.mention:
        client.send_message(payload.room, f"Hi {payload.nick}")

# API времени выполнения
# bot.connect_rrc(hub_hash, rooms=["general"])
# bot.rrc.send_message("general", "hello")
# bot.rrc.send_notice("general", "notice")
# bot.rrc.send_action("general", "waves")
# bot.rrc.join("ops")
# bot.rrc.part("ops")
# bot.rrc.status()
# bot.disconnect_rrc()
```

### Экспортируемые типы

- `RRCClient`: сессия с одним хабом
- `RRCManager`: менеджер нескольких хабов (`bot.rrc`)
- `RRCMessage`: данные события комнаты (`kind`, `room`, `text`, `nick`, `src`, `mention`, ...)
- `RRC_VERSION`: константа версии проводного протокола
- `DEFAULT_DEST_NAME`: Имя адресата хаба по умолчанию
  (`"rrc.hub"`)
- `make_envelope`, `encode_envelope`, `decode_envelope`,
  `validate_envelope`, `normalize_room`: Помощники wire-формата для
  инструментов, говорящих с хабами напрямую

Типичные события, передаваемые обработчикам `@bot.on_rrc`: `status`, `welcome`, `joined`, `parted`, `msg`, `notice`, `action`, `motd`, `error` и `rtt`.

# Шаблоны

Фреймворк включает несколько готовых шаблонов ботов:

## EchoBot

Простой echo-бот, повторяющий сообщения:

``` python
from lxmfy.templates import EchoBot

bot = EchoBot()
bot.run()
```

## NoteBot

Бот для заметок с хранилищем JSON:

``` python
from lxmfy.templates import NoteBot

bot = NoteBot()
bot.run()
```

## ReminderBot

Бот-напоминалка с хранилищем SQLite:

``` python
from lxmfy.templates import ReminderBot

bot = ReminderBot()
bot.run()
```

## RRCBot

RRC-бот для комнат: подключается к настроенным хабам и отвечает на `@упоминания`. По умолчанию хаб `664fc0e8d2e448658e37bb3f34e6c88f`, комната `#general` и `~/.reticulum`, если доступен.

``` python
from lxmfy.templates import RRCBot

bot = RRCBot(
    hubs=["664fc0e8d2e448658e37bb3f34e6c88f"],
    rooms=["general"],
    nick="RRCBot",
    reticulum_config_dir="~/.reticulum",
)
bot.run()
```

# Инструменты CLI

Фреймворк предоставляет инструменты командной строки для управления
ботами. Запуск `lxmfy` без аргументов открывает интерактивное меню.

``` bash
# Интерактивный scaffold полного проекта
lxmfy init mybot                 # директория проекта, bot.py, cogs/, README
lxmfy init --here --yes          # текущая директория, принимает все значения по умолчанию

# Создать один файл бота
lxmfy create mybot
lxmfy create --template echo mybot
lxmfy create --template rrc my_rrc_bot
lxmfy create mybot --no-cogs     # пропускает пакет cogs
lxmfy create --output dir/bot.py --name MyBot

# Запустить бота из шаблона
lxmfy run echo
lxmfy run rrc
lxmfy run reminder --name "MyReminder"

# Диагностировать соединение (см. раздел Диагностика)
lxmfy debug
lxmfy debug probe <hash> --request-path --wait 30

# Тестировать проверку подписей с сообщением
lxmfy signatures test

# Включить проверку подписей
lxmfy signatures enable

# Выключить проверку подписей
lxmfy signatures disable
```

`lxmfy init` спрашивает имя проекта, шаблон, backend хранилища,
префикс команд и хеши админов. Каждый вопрос принимает вместо этого
флаг: `--dir`, `--bot-name`, `--template`, `--storage`, `--prefix`,
`--admins`, `--no-cogs`, `--force`, `--yes`. На не-TTY stdin берутся
значения по умолчанию.

Шаблоны для `create` и `run`: `basic`, `echo`, `reminder`, `note`,
`cogtest`, `rrc`.

# Обработка ошибок

Перехватывайте завершение работы и ошибки выполнения вокруг `bot.run()`:

``` python
try:
    bot.run()
except KeyboardInterrupt:
    bot.cleanup()
except Exception as e:
    logger.error(f"Error running bot: {str(e)}")
```

# Справочник модулей

Генерируется из строк документации исходного кода.

::: lxmfy.LXMFBot

::: lxmfy.BotConfig

::: lxmfy.Command

::: lxmfy.Attachment

::: lxmfy.AttachmentType

::: lxmfy.IconAppearance

::: lxmfy.Event

::: lxmfy.EventManager

::: lxmfy.EventPriority

::: lxmfy.MiddlewareContext

::: lxmfy.MiddlewareManager

::: lxmfy.MiddlewareType

::: lxmfy.DefaultPerms

::: lxmfy.PermissionManager

::: lxmfy.Role

::: lxmfy.HelpFormatter

::: lxmfy.HelpSystem

::: lxmfy.TaskScheduler

::: lxmfy.ScheduledTask

::: lxmfy.Storage

::: lxmfy.JSONStorage

::: lxmfy.SQLiteStorage

::: lxmfy.storage.MemoryStorage

::: lxmfy.MsgPackStorage

::: lxmfy.ConversationManager

::: lxmfy.Answer

::: lxmfy.DeliveryTracker

::: lxmfy.TestBot

::: lxmfy.SentMessage

::: lxmfy.Debugger

::: lxmfy.MessageDebugger

::: lxmfy.DoctorReport

::: lxmfy.DestinationProbe

::: lxmfy.CheckResult

::: lxmfy.RRCClient

::: lxmfy.RRCManager

::: lxmfy.RRCMessage
