# Основні компоненти

## LXMFBot

Головний клас бота, який обробляє маршрутизацію повідомлень, обробку
команд і керування життєвим циклом бота.

``` python
from lxmfy import LXMFBot

bot = LXMFBot(
    name="MyBot",
    command_prefix="/",
    admins=set(),
    config_path=None,                 # типово "config" у робочій теці
    reticulum_config_dir=None,        # або LXMFY_RETICULUM_CONFIG_DIR / "~/.reticulum"
    test_mode=False,                  # пропускає запуск RNS, для тестів
    log_level="INFO",                 # рівень логера lxmfy, None не чіпає логування
    loglevel=None,                    # рівень логів RNS 0-7, None бере конфіг reticulum

    # Announces
    announce=600,
    announce_immediately=True,
    announce_enabled=True,
    announce_display_name_file=None,  # файл у config_path, що перевизначає
                                      # анонсоване ім'я (типовий файл:
                                      # bot_display_name.txt)

    # Захист від спаму
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

    # Сховище, події, права
    storage_type="json",              # "json", "sqlite", "msgpack" або "memory"
    storage_path="data",
    permissions_enabled=False,
    first_message_enabled=True,
    event_logging_enabled=True,
    max_logged_events=1000,
    event_middleware_enabled=True,

    # Безпека
    signature_verification_enabled=False,
    require_message_signatures=False,
    require_stamps=False,             # відхиляє повідомлення з невалідними stamp
    request_unknown_identities=False, # запитує ідентичності відправників у мережі
    stamp_cost=None,                  # вхідна вартість stamp, None вимикає
    include_tickets=True,             # додає ticket відповіді до вихідних
    identity_pinning_enabled=False,
    landlock_enabled=True,

    # Опційні функції
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
    propagation_node=None,            # хеш вихідного вузла поширення
    autopeer_propagation=False,       # знаходить вузли поширення з announces
    autopeer_maxdepth=4,              # макс. глибина hops для автопірингу, None = без межі
    enable_propagation_node=False,    # запускає цього бота як вузол поширення
    message_storage_limit_mb=500,     # ліміт сховища вузла, лише в режимі вузла

    # Відкладені відправлення
    pending_sends_enabled=True,       # тримає відправлення для невідомих адресатів
    pending_sends_max=200,
    pending_sends_ttl=604800,         # 7 днів
    pending_sends_retry=300,          # секунди між проходами повторів

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

Усі ці опції є полями `BotConfig`. `LXMFBot(**kwargs)` передає кожен
іменований аргумент, тож `bot.config` містить результуючі значення.

### Ключові методи

- `run(delay=10)`: Запускає головний цикл бота
- `cleanup()`: Персистить черги, скасовує розмови та зупиняє
  планувальник, роутер і RNS. Викликається автоматично при виході з
  `run()`.
- `send(destination, message, title="Reply", lxmf_fields=None, stamp_cost=None, opportunistic=None, method=None, include_ticket=None, defer=None, reply_to=None, quote=None, thread=None)`:
  Надсилає повідомлення адресату. `stamp_cost` перевизначає вихідну
  вартість для цього повідомлення, `opportunistic` перевизначає
  `opportunistic_sending`, `include_ticket` перевизначає
  `include_tickets`, а `defer` перевизначає `pending_sends_enabled`.
  `reply_to`, `quote` і `thread` встановлюють поля тредування
  відповідей.
- `send_with_attachment(destination, message, attachment, title="Reply", stamp_cost=None, opportunistic=None)`:
  Надсилає повідомлення з вкладенням
- `command(name, description="No description provided", admin_only=False, permissions=None, usage=None, examples=None, category=None, aliases=None, threaded=False, rate_limit=None)`:
  Декоратор для реєстрації команд. `permissions` перевизначає бар'єр
  `DefaultPerms` (`ALL` при `admin_only`, інакше `USE_COMMANDS`),
  `threaded` виконує callback у робочому потоці, `rate_limit` обмежує
  виклики на відправника за вікно cooldown, а `usage`, `examples`,
  `category`, `aliases` живлять систему довідки. Команди підтримують
  типізовані аргументи з автоматичною конверсією.
- `intent(name, examples)`: Декоратор для реєстрації обробників
  NLP-інтентів.
- `nlp.export_model()`: Експортує дані навченої NLP-моделі.
- `nlp.import_model(model_data)`: Імпортує раніше експортовані дані
  NLP-моделі.
- `request_link(destination_hash, callback=None, app_name="lxmf", *aspects)`:
  Запитує RNS-з'єднання до адресата. Дозволяє власні `app_name` і
  `aspects` (типово "lxmf" і "delivery").
- `on_link(callback)`: Реєструє обробник вхідних RNS-з'єднань.
- `load_extension(name)`: Завантажує модуль розширення cog за назвою
  (напр. "cogs.utility").
- `reload_extension(name)`: Перезавантажує модуль розширення cog.
- `add_cog(cog_instance)`: Додає екземпляр класу cog до бота.
- `remove_cog(cog_name)`: Видаляє cog за назвою класу.
- `on_first_message()`: Декоратор для обробки перших повідомлень від
  користувачів
- `on_message()`: Декоратор для обробки всіх повідомлень (викликається
  перед обробкою команд)
- `received(function)`: Реєструє callback, що викликається з контекстом
  повідомлення для кожного вхідного повідомлення, яке пройшло pipeline
  без поглинання командою чи інтентом
- `on_reaction()`: Декоратор для обробки вхідних реакцій. Обробники
  отримують `(sender, reaction)`, де reaction несе ключі
  `reaction_to`, `reaction_emoji` і `reaction_sender`
- `react(destination, message_hash, reaction)`: Надсилає реакцію на
  повідомлення через поле LXMF `FIELD_REACTION`
- `validate()`: Запускає перевірки конфігурації бота
- `get_landlock_status()`: Повертає доступність і стан активації
  пісочниці Landlock LSM для процесу бота
- `diagnose_destination(destination, request_path=False, wait=0.0)`:
  Досліджує стан ідентичності та шляху для хеша адресата
- `diagnose_connectivity(destination=None, request_path=False, wait=0.0)`:
  Виконує повний doctor-звіт і повертає його dict-ом
- `get_debugger()`: Повертає `Debugger`, прив'язаний до цього бота
- `set_propagation_node(node_hash)`: Фіксує вихідний вузол поширення
- `get_propagation_node_status()`: Стан налаштованих, виявлених і
  поточного вихідного вузлів поширення
- `set_message_storage_limit(megabytes)`: Ліміт сховища при роботі як
  вузол поширення
- `get_propagation_storage_stats()`: Використання сховища вузла або
  dict із причиною недоступності
- `connect_rrc(hub_hash, rooms=None, nick=None, dest_name=None, auto_reconnect=None)`:
  Підключається до RRC-хаба як клієнт
- `disconnect_rrc(hub_hash=None)`: Відключає одну чи всі сесії
  RRC-хабів
- `on_rrc(callback=None)`: Декоратор або реєстрація обробника для
  подій RRC (`handler(event, client, payload)`)
- `on_delivery_event(callback=None)`: Підписується на потік подій
  вихідної доставки, як декоратор або прямий виклик

### Атрибути

- `config`: Результуюча `BotConfig`
- `commands`, `cogs`: Реєстри команд і когів
- `storage`: Активний backend сховища
- `scheduler`: `TaskScheduler` для cron-подібних задач
- `events`: `EventManager` для обробників подій і dispatch
- `middleware`: `MiddlewareManager` для middleware команд
- `permissions`: `PermissionManager` для ролей і прапорців
- `spam_protection`: `SpamProtection` для обмежень частоти, попереджень
  і банів
- `signature_manager`: Шар політики підписів
- `nlp`: Класифікатор інтентів (матчить лише при `nlp_enabled`)
- `delivery`: `DeliveryTracker`, потік вихідних подій
- `conversations`: `ConversationManager` для питань `msg.ask`
- `rrc`: `RRCManager` для сесій із кількома хабами, `None` доки RRC не
  ввімкнено або `connect_rrc()` не виконано
- `local`: `RNS.Destination` бота (його LXMF-адреса це
  `bot.local.hash`)

## Анонсоване ім'я

Ім'я, яке бачать піри, походить із `name`, але для announces існують
два перевизначення. Якщо задано `announce_display_name_file` і такий
файл існує в `config_path`, його вміст перемагає. Інакше читається
`bot_display_name.txt` у `config_path`, якщо він є. У будь-якому разі
присвоєння `bot.name = "Нове ім'я"` ресинхронізує анонсоване ім'я
під час виконання.

Це дає операторам змогу перейменувати бота без зміни коду, а
анонсоване ім'я може відрізнятися від внутрішнього імені в
конфігурації.

## Структуровані команди через поля LXMF

Боти можуть отримувати команди, надіслані через `FIELD_COMMANDS`
(`0x09`) LXMF, і автоматично відповідати з `FIELD_RESULTS` (`0x0A`). Це
вмикає структуровані процеси запит/відповідь поруч із звичайними
текстовими командами.

Вхідні `FIELD_COMMANDS` розбираються і спрямовуються через той самий
реєстр команд, що й текстові команди, зі спільними перевірками прав,
розбором типізованих аргументів, потоками та middleware.

``` python
from lxmfy import LXMFBot, FIELD_COMMANDS, FIELD_RESULTS, pack_result, unpack_commands

bot = LXMFBot(name="FieldBot")

@bot.command(name="status", description="Return bot status")
def status_cmd(ctx):
    # ctx.fields містить сирий словник полів LXMF
    # ctx.request_id встановлюється автоматично, якщо команда його містила
    ctx.reply("Bot is online")

# Надсилання структурованої команди з іншого клієнта LXMF:
# lxm.fields[FIELD_COMMANDS] = {"command": "status", "args": [], "request_id": "abc123"}
# router.handle_outbound(lxm)

# Відповідь бота автоматично містить FIELD_RESULTS з відповіддю та request_id.
```

Щоб вимкнути обробку польових команд, задайте
`lxmf_commands_enabled=False` у `BotConfig`.

## Реакції

Реакції передаються як поле LXMF `FIELD_REACTION` (`0x40`) на інакше
порожньому повідомленні. `pack_reaction` і `unpack_reaction` будують і
розбирають це поле.

``` python
from lxmfy import pack_reaction, unpack_reaction

# Надіслати реакцію на повідомлення
bot.react(destination_hash, message_hash_hex, "thumbs up emoji")

# Отримувати реакції
@bot.on_reaction()
def on_reaction(sender, reaction):
    # reaction["reaction_to"]  - hex-хеш цільового повідомлення
    # reaction["reaction_emoji"] - текст реакції (до 16 символів)
    # reaction["reaction_sender"] - відправник
    print(f"{sender} reacted {reaction['reaction_emoji']} to {reaction['reaction_to']}")
    return True
```

Текст реакції обмежений 16 друкованими символами. Сире поле лишається
доступним у `ctx.fields` і `msg.fields` для сумісності.

## Тредування відповідей

Відповіді можуть нести поля LXMF `FIELD_REPLY_TO` (`0x30`),
`FIELD_REPLY_QUOTE` (`0x31`) і `FIELD_THREAD` (`0x08`). Клієнти, що
рендерять треди, як-от MeshChatX і Sideband, показують їх як справжні
цитовані відповіді замість пласких повідомлень.

`msg.reply()` тредить автоматично: встановлює `FIELD_REPLY_TO` на хеш
вхідного повідомлення і `FIELD_THREAD` на корінь розмови.

``` python
@bot.command("status")
def status(msg):
    msg.reply("all systems nominal")          # тредована відповідь
    msg.reply("flat", reply_to=None)          # відмовитись від тредування
    msg.reply("noted", quote=True)            # цитує вхідний текст
```

Для відправлень, які не є відповідями, передайте поля явно:

``` python
bot.send(dest, "see above", reply_to=msg_hash_hex, quote="earlier text")
```

Вхідні відповіді парсяться в контекст повідомлення:

``` python
@bot.command("ctx")
def ctx_cmd(msg):
    msg.reply_to      # hex-хеш, на який відповідає це повідомлення, або None
    msg.reply_quote   # цитований текст відповіді, або None
    msg.thread        # hex-хеш кореня треду, або None
```

`pack_reply(message_hash, quote=..., thread=...)` і
`unpack_reply(fields)` експортуються для ручної обробки полів.

## Розмови

Команди можуть ставити відправнику питання і трактувати його наступне
повідомлення як відповідь, замість диспетчеризації як команди:

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

`msg.ask(prompt, timeout=..., validator=...)` блокує обробник, доки не
надійде відповідь, не спрацює timeout або розмову не буде скасовано.
Повертає `Answer` із `content`, `fields`, `hash`, `sender` і шорткатом
`reply(text)`.

Валідатор відхиляє погані відповіді й перепитує:

``` python
num = msg.ask(
    "Pick a number",
    validator=lambda a: None if a.content.isdigit() else "Digits only",
)
```

В асинхронних обробниках команд використовуйте `await
msg.ask_async(...)`. Для довгих очікувань або коли може бути багато
відкритих розмов, використовуйте стиль колбеків, щоб жоден потік не
залишався припаркованим:

``` python
msg.ask(
    "Send the log file",
    on_answer=lambda ans: ans.reply("received"),
    on_timeout=lambda sender: bot.send(sender, "Too slow."),
    timeout=3600,
)
```

Нотатки:

- Надсилання зареєстрованої команди під час очікування питання скасовує
  питання й виконує команду. Користувачі завжди мають вихід.
- `bot.conversations.pending_count()` і
  `bot.conversations.cancel(sender)` відкривають реєстр для діагностики
  й адміністративних інструментів.
- Реєстр обмежений 1024 очікуючими питаннями. `ask` повертає `None`,
  коли він заповнений.
- Блокуючий `ask` паркує потік доставки, що обробляє це повідомлення.
  Це безпечно для прямих доставок, але боти, що синхронізують великі
  пакети з вузла поширення, мають надавати перевагу колбекам
  `on_answer`.

## Сховище

Фреймворк надає три бекенди сховища:

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

storage = MemoryStorage() # Повністю в пам'яті
```

## Команди

Реєстрація та обробка команд:

``` python
@bot.command(name="hello", description="Says hello")
def hello(ctx):
    ctx.reply(f"Hello {ctx.sender}!")
```

Метадані довідки та контроль доступу надходять із додаткових
kwarg-ів декоратора:

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

`permissions` перевизначає типовий бар'єр: `USE_COMMANDS` для звичайних
команд, `ALL` для `admin_only`. `category` групує команду у виводі
`/help`. `aliases` є лише метаданими довідки: аліаси показуються
користувачам, але не реєструються для dispatch, тож `/clear` не
виконає `purge`, хіба що ви зареєструєте його як другу команду.

### Типізовані аргументи

Команди автоматично розбирають і перетворюють аргументи на основі
анотацій типів у функції зворотного виклику.

``` python
@bot.command(name="add", description="Adds two numbers")
def add(ctx, a: int, b: int):
    result = a + b
    ctx.reply(f"The result is {result}")
```

### Обмеження частоти для окремої команди

Обмежує, як часто один відправник може викликати команду в межах
глобального вікна `cooldown`. При досягненні відхиляється лише виклик,
жодних попереджень чи банів.

``` python
@bot.command(name="report", rate_limit=3)
def report(ctx):
    # кожен відправник може викликати це 3 рази за період cooldown
    ...
```

Потребує `permissions_enabled=True`, як і глобальне обмеження.
Користувачі з роллю admin або `BYPASS_SPAM` пропускають перевірку.

## Захист від спаму

`bot.spam_protection` забезпечує глобальне обмеження: відправник може
надіслати `rate_limit` повідомлень у межах кожного вікна `cooldown`.
Перевищення додає попередження і відхиляє повідомлення. На
`max_warnings` відправника банять. Попередження зникають після
`warning_timeout` секунд без порушень.

Перевірки спаму виконуються всередині події `message_received` і
потребують `permissions_enabled=True`.

``` python
bot = LXMFBot(
    name="GuardedBot",
    permissions_enabled=True,
    rate_limit=5,        # повідомлень за вікно cooldown
    cooldown=60,         # тривалість вікна в секундах
    max_warnings=3,      # попереджень перед баном
    warning_timeout=300, # секунд до скидання попереджень
)

# Зняти бан вручну
bot.spam_protection.unban(sender_hash)
```

Попередження, бани й лічильники персистять у налаштованому backend
сховища, тож бани переживають рестарти. Відправники з `BYPASS_SPAM`
ніколи не обмежуються й не баняться. Покомандне `rate_limit` у
`@bot.command` м'якше: воно лише відхиляє виклик і ніколи не попереджає
чи не банить.

## Система довідки

Фреймворк включає інтерактивний генератор довідки, який створює
категоризовані меню довідки на основі метаданих коґів і команд.

``` python
# Команда help реєструється автоматично.
# Користувачі можуть використовувати '/help' або '/help <command>'
```

## Команди в окремому потоці

Для довготривалих або блокуючих операцій, які не взаємодіють із
Reticulum Network Stack напряму, ви можете виконувати команди в окремому
потоці, щоб бот лишався чутливим.

``` python
import time

@bot.command(name="long_task", description="Performs a long-running task in a separate thread", threaded=True)
def long_task_command(ctx):
    ctx.reply("Starting a long task... please wait.")
    time.sleep(10) # Це виконується в окремому потоці
    ctx.reply("Long task completed!")
```

!!! warning "Безпека потоків"

    Функції, позначені `threaded=True`, **не повинні** напряму
    взаємодіяти з Reticulum Network Stack (RNS) або будь-якими
    компонентами, які покладаються на `lxmfy.transport.py`, оскільки
    вони загалом не є потокобезпечними. Використовуйте `ctx.reply()` для
    надсилання повідомлень користувачу зсередини команди в окремому
    потоці.

## Події

Система подій для обробки різних подій бота:

``` python
@bot.events.on("message_received", EventPriority.HIGHEST)
def handle_message(event):
    # event.data несе навантаження, напр. sender і message
    event.cancel()  # зупиняє наступних обробників і подальшу обробку
```

Обробники виконуються в порядку `EventPriority`: `HIGHEST`, `HIGH`,
`NORMAL`, `LOW`. Сама перевірка спаму є обробником `message_received`
з `HIGHEST`, тож скасування цієї події є механізмом, яким обмежувач
відкидає повідомлення.

Диспетчеризуйте власні події:

``` python
from lxmfy import Event

bot.events.dispatch(Event("order_placed", data={"user": ctx.sender}))
```

`event_logging_enabled`, `max_logged_events` і
`event_middleware_enabled` існують у `BotConfig`, але не підключені:
події не записуються у сховище, а `bot.events.use()` є stub.
Вважайте їх зарезервованими.

## Тестування

`lxmfy.testing.TestBot` є `LXMFBot`, попередньо налаштований для
тестів. Жоден екземпляр Reticulum не запускається. Вхідні повідомлення
проходять справжній pipeline отримання (middleware, перевірки спаму,
права, dispatch), а вихідні відправлення захоплюються для
тверджень.

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
  вводить повідомлення і повертає створені об'єкти `SentMessage`.
  Відправники іменовані: `"alice"` мапиться на стабільний фейковий
  хеш, або передайте hex-хеш адресата напряму.
- `bot.drain()` витягує вихідні повідомлення з черги. `bot.outbox`
  накопичує все надіслане. `bot.last_sent(sender=...)` дістає
  останнє.
- `bot.wait_sent(n, timeout=...)` чекає на потокові команди.
- `bot.receive_later(content, sender=..., delay=...)` відповідає на
  блокуючі виклики `msg.ask` з daemon-потоку.
- `fake_message(content, source_hash=..., ...)` будує вхідне
  повідомлення для прямого виклику `bot._message_received`.

`SentMessage` обгортає кожне захоплене вихідне повідомлення:
`destination` (hex), `content`, `title`, `fields`, `method`,
`include_ticket`, `stamp_cost` і `raw` для базового об'єкта.

Тестовий набір репозиторію також містить сценарії надійності та
стресу. Запускайте їх тестовим раннером репозиторію.

### Розширений набір перевірок надійності

Фреймворк включає великий набір автоматизованих тестів для суворих
умов:

- **Manifold Testing**: перевіряє математичну топологію векторного
  простору NLP-інтентів.
- **Chaos Engineering**: імітує bit-rot, відмову SD-карти та пошкодження
  сховища.
- **Temporal Drift**: перевіряє стійкість до стрибків системного
  годинника (±1 рік).
- **Leak Detection**: довготермінове відстеження пам'яті, файлових
  дескрипторів і потоків.

## Права доступу

Система прав для керування доступом до функцій бота:

``` python
from lxmfy import DefaultPerms

@bot.command(name="admin", description="Admin command", admin_only=True)
def admin_command(ctx):
    if ctx.is_admin:
        ctx.reply("Admin command executed")
```

Увімкніть через `permissions_enabled=True`. Прапорці
`DefaultPerms`:

- `USE_BOT`, `SEND_MESSAGES`, `USE_COMMANDS`: базовий доступ
- `MANAGE_MESSAGES`, `MANAGE_COMMANDS`, `MANAGE_USERS`: підвищений
- `BYPASS_RATELIMIT`, `BYPASS_SPAM`, `VIEW_ADMIN_COMMANDS`: спеціальні
- `VIEW_EVENTS`, `MANAGE_EVENTS`, `BYPASS_EVENT_CHECKS`: система подій
- `NONE`, `ALL`: шорткати

`bot.permissions` керує ролями та призначеннями:

``` python
bot.permissions.create_role("moderator", DefaultPerms.MANAGE_MESSAGES | DefaultPerms.BYPASS_SPAM)
bot.permissions.assign_role(user_hash, "moderator")
bot.permissions.remove_role(user_hash, "moderator")
bot.permissions.has_permission(user_hash, DefaultPerms.USE_COMMANDS)
```

Ролі та призначення персистять у налаштованому backend сховища.
Існують дві вбудовані ролі, які не можна видалити: `user` (типова) і
`admin`, що автоматично надається кожному хешу в `admins`.

## Middleware

Система middleware для обробки повідомлень і подій:

``` python
from lxmfy import MiddlewareType

@bot.middleware.register(MiddlewareType.PRE_COMMAND)
def pre_command_middleware(ctx):
    # ctx обгортає контекст повідомлення, ctx.cancelled відкидає його
    if "spamword" in ctx.data.content:
        ctx.cancel()
```

Три точки pipeline виконують middleware:

- `PRE_COMMAND`: перед dispatch команд, після перевірок спаму. Якщо
  ланцюг повертає `None`, повідомлення повністю скасовується.
- `POST_COMMAND`: після callback команди (включно з потоковими
  командами, які спрацьовують у робочому потоці).
- `PRE_EVENT`: перед dispatch події `message_received`.

`POST_EVENT`, `REQUEST` і `RESPONSE` існують у `MiddlewareType`, але
ніщо в pipeline їх поки не виконує.

## Вкладення

Підтримка надсилання файлів, зображень і аудіо:

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

## Вигляд іконки (поле LXMF)

Ви можете задати власну іконку для бота, яку сумісні клієнти LXMF можуть
відображати. Для цього використовується `LXMF.FIELD_ICON_APPEARANCE`.

``` python
from lxmfy import IconAppearance, pack_icon_appearance_field
import LXMF # Потрібен для LXMF.FIELD_ICON_APPEARANCE

# Визначаємо вигляд іконки
icon_data = IconAppearance(
    icon_name="smart_toy",  # Ім'я з Material Symbols
    fg_color=b'\xFF\xFF\xFF',  # Білий передній план (3 байти)
    bg_color=b'\x4A\x90\xE2'   # Синій фон (3 байти)
)

# Пакуємо у формат поля LXMF
icon_lxmf_field = pack_icon_appearance_field(icon_data)

# Надсилаємо повідомлення з цією іконкою
bot.send(
    destination_hash_str,
    "Hello from your friendly bot!",
    title="Bot Message",
    lxmf_fields=icon_lxmf_field
)

# Можна також комбінувати з іншими полями, наприклад з вкладеннями:
# attachment_field = pack_attachment(some_attachment)
# combined_fields = {**icon_lxmf_field, **attachment_field}
# bot.send(destination, "Message with icon and attachment", lxmf_fields=combined_fields)
```

## Планувальник

Система планування задач:

``` python
@bot.scheduler.schedule(name="daily_task", cron_expr="0 0 * * *")
def daily_task():
    # Виконується щодня опівночі
    pass
```

## Підписи

LXMFy надає параметри конфігурації для вбудованого в LXMF
криптографічного підписування та перевірки повідомлень:

``` python
from lxmfy import LXMFBot

bot = LXMFBot(
    name="SecureBot",
    signature_verification_enabled=True,  # Увімкнути перевірку підписів
    require_message_signatures=False      # Встановіть True, щоб відхиляти непідписані повідомлення
)
```

!!! note "Обробка підписів"

    LXMF автоматично виконує все криптографічне підписування та
    перевірку за допомогою ідентифікаторів RNS. `SignatureManager`
    LXMFy - це шар конфігурації, який:

    - Керує тим, чи застосовувати перевірку підписів
    - Визначає політику для непідписаних повідомлень (приймати або
      відхиляти)
    - Інтегрується з системою прав (наприклад, обхід перевірки для
      довірених користувачів)

Фактичні криптографічні операції виконує LXMF/RNS, а не LXMFy.

### Пісочниця Landlock LSM

На ядрах Linux з підтримкою Landlock (5.13+) LXMFy може обмежувати
доступ до файлової системи для процесу бота і для зовнішніх скриптових
коґів.

**Пісочниця процесу бота**

Коли `landlock_enabled=True` (типово) і бот не працює в `test_mode`,
бот викликає `apply_landlock_sandbox()` під час ініціалізації. Системні
каталоги доступні лише для читання; сховище бота, конфігурація, коґи,
конфігурація Reticulum і тимчасові шляхи лишаються доступними для
запису.

``` python
bot = LXMFBot(
    name="SecureBot",
    landlock_enabled=True,
)

status = bot.get_landlock_status()
# ключі status: landlock_kernel_supported, landlock_requested,
# landlock_auto_enabled, landlock_disabled_by_env, landlock_active
```

**Перевизначення через середовище**

- `LXMFY_LANDLOCK=0`: вимкнути Landlock навіть на підтримуваних ядрах
- `LXMFY_LANDLOCK=1`: спробувати Landlock на Linux незалежно від
  автовизначення
- не встановлено: слідувати `landlock_enabled` і автовизначенню ядра

**Пісочниця зовнішніх коґів**

Скриптові коґи використовують `external_cogs_sandbox_type`. У режимі
`auto` перевага надається Landlock, коли він доступний, бо він не
потребує зовнішніх інструментів. Повний список параметрів пісочниці
див. у посібнику [Створення ботів](creating-bots.md).

### Закріплення ідентифікатора

LXMFy підтримує опційне закріплення ідентифікатора для запобігання
імітації, якщо ідентифікатор ротовано або скомпрометовано. Коли
увімкнено, бот "закріплює" LXMF-адресу до першого побаченого публічного
ключа.

``` python
bot = LXMFBot(
    identity_pinning_enabled=True
)
```

### Методи SignatureManager

`SignatureManager` доступний як `bot.signature_manager`, коли
`signature_verification_enabled=True`:

- `should_verify_message(sender)`: визначає, чи слід перевіряти
  повідомлення від даного відправника
- `handle_unsigned_message(sender, message_hash)`: обробляє
  повідомлення без валідних підписів відповідно до політики

### Як працюють підписи LXMF

LXMF автоматично підписує всі вихідні повідомлення ідентифікатором RNS
відправника під час операції `pack()`. Коли повідомлення отримано, LXMF
перевіряє підписи і надає:

- `message.signature_validated`: булеве значення, що вказує, чи валідний
  підпис
- `message.unverified_reason`: код причини, якщо валідація не вдалася
  (наприклад, `SIGNATURE_INVALID`, `SOURCE_UNKNOWN`)

LXMFy використовує ці вбудовані властивості LXMF для застосування
політики підписів вашого бота.

## Доставка повідомлень

LXMFy надає розширені функції доставки повідомлень, включно з вузлами
поширення та автоматичними повторними спробами:

### Вузли поширення

Надсилайте повідомлення через конкретні вузли поширення для підвищення
надійності в мережі Reticulum:

``` python
# Налаштуйте вузол поширення один раз на рівні конфігурації/виконання
bot.set_propagation_node("<propagation_node_hash>")

# Надсилання з налаштованою поведінкою доставки
bot.send(
    destination_hash,
    "Message content"
)

# Хеш вузла поширення має бути валідним вузлом поширення LXMF
# у мережі Reticulum
```

Вузол також можна задати під час створення через
`propagation_node="<hash>"`, або бот може знаходити вузли сам:

``` python
bot = LXMFBot(
    name="AutoBot",
    autopeer_propagation=True, # вчить вузли з announces
    autopeer_maxdepth=4,       # ігнорує вузли глибше ніж 4 hops
)
```

`bot.get_propagation_node_status()` повідомляє про ручний вузол,
виявлені вузли та вихідний вузол, що зараз використовується.

### Автоматичні повторні спроби

Налаштуйте автоматичні повторні спроби для невдалих прямих доставок:

``` python
bot = LXMFBot(
    name="ReliableBot",
    direct_delivery_retries=5,  # Повторювати пряму доставку до 5 разів
    propagation_fallback_enabled=True
)

bot.send(destination_hash, "Important message")

# direct_delivery_retries типово дорівнює 3
# Логіка повторів автоматично обробляє зворотні виклики доставки
```

Система повторів відстежує спроби доставки для кожного отримувача і
автоматично повторює невдалі доставки. Успішні доставки скидають
лічильник повторів для цього отримувача.

### Відкладені відправлення

Відправлення адресату, чию ідентичність вузол ще не чув, зазвичай
одразу провалюється. З `pending_sends_enabled` (типово) повідомлення
натомість тримається у сховищі, а потім автоматично виштовхується,
коли адресат анонсується або під час періодичного проходу.

``` python
bot = LXMFBot(
    pending_sends_enabled=True,
    pending_sends_max=200,     # найстаріші втримані повідомлення випадають понад це
    pending_sends_ttl=604800,  # втримані повідомлення спливають через 7 днів
    pending_sends_retry=300,   # секунди між проходами в run()
)

# Перевизначення для окремого відправлення
bot.send(dest, "hold this", defer=True)
bot.send(dest, "send or drop", defer=False)
```

Втримані відправлення з'являються як `held (unknown peers)` у
адмінській команді `/queue` і створюють події `deferred` у трекері
доставки.

### Персистентність повідомлень

Вихідні повідомлення можуть зберігатися на диску, щоб гарантувати їх
доставку навіть після перезапуску бота. Персистентність увімкнена
типово. Вихідна черга в пам'яті обмежена (`message_queue_size`, типово
50) і відкидає найстаріше повідомлення, коли заповнена. Невалідні хеші
отримувачів не відновлюються.

``` python
bot = LXMFBot(
    message_persistence_enabled=True,
    message_queue_size=50,
)
```

### Stamp-и та ticket-и

Вартість stamp змушує відправників виконувати proof-of-work перед тим,
як їхнє повідомлення буде прийнято, що стримує небажаний трафік. LXMFy
відкриває обидва боки механізму.

``` python
bot = LXMFBot(
    stamp_cost=16,          # вимагає цю вхідну вартість stamp
    require_stamps=True,    # відхиляє повідомлення з невалідними stamp
    include_tickets=True,   # дозволяє пірам відповідати без генерації stamp
)
```

- `stamp_cost` є вхідною вимогою. Вихідна вартість відправлення
  усе ще береться з announce піра, хіба що ви передасте `stamp_cost=`
  до `bot.send()`.
- `include_tickets` (типово True) додає ticket відповіді до вихідних
  повідомлень, тож пір із вимогою stamp може відповісти без оплати.
  Перевизначайте для окремого відправлення через `include_ticket=`.
- `request_unknown_identities=True` запитує в мережі ідентичність
  відправника, коли повідомлення надходить із невідомого джерела, що
  допомагає перевіркам stamp і підписів розв'язатися замість сліпого
  провалу.

Контроль під час виконання лежить у розділі «Керування роутером»: `set_inbound_stamp_cost`,
`enforce_stamps`, `ignore_stamps`, `generate_ticket` та методи
інспекції ticket-ів.

### Робота як вузол поширення

Бот може водночас бути вузлом поширення LXMF, зберігаючи повідомлення
для пірів, що офлайн:

``` python
bot = LXMFBot(
    enable_propagation_node=True,
    message_storage_limit_mb=500,
)

bot.set_message_storage_limit(750)
stats = bot.get_propagation_storage_stats()
```

`get_propagation_node_status()` працює для обох ролей: повідомляє про
вихідний вузол, який цей бот використовує, і про те, чи він сам слугує
вузлом. Пов'язані контролі: `announce_propagation_node()` рекламує
вузол, `set_retain_on_node()` зберігає доставлені повідомлення на ньому,
а `allow_control_identity()` / `disallow_control_identity()` керують
тим, які ідентичності можуть використовувати контрольний канал вузла.

### Події доставки

`bot.delivery` записує обмежений потік подій вихідного життєвого циклу,
щоб спостерігати за потоком повідомлень без читання логів. Стадії:
`queued`, `deferred`, `dispatched`, `delivered`, `failed`, `cancelled`,
`dropped`. Нещодавній хвіст персиститься у сховище і відновлюється при
запуску.

``` python
@bot.on_delivery_event()
def watch(event):
    print(event["stage"], event.get("destination"), event.get("reason"))

# Або пряма інспекція
recent = bot.delivery.recent(20)
failures = bot.delivery.recent(stage="failed")
to_peer = bot.delivery.recent(destination="aa11bb...")
```

Кожна подія є dict-ом із `ts`, `stage` і опційно `destination`,
`message_id`, `hash`, `method`, `attempts`, `reason`, `title`.

Адміни отримують команду `/delivery [limit]`, що рендерить ту саму
хронологію в чаті, а `lxmfy debug` показує підсумок хронології доставки
в перевірках pipeline відправлення.

### Вбудовані адміністративні команди

Ці команди реєструються автоматично й вимагають, щоб відправник був у
`admins`, коли права ввімкнено:

| Команда | Дія |
| --- | --- |
| `/queue` | Показує вихідну чергу роутера, внутрішню чергу та втримані відправлення |
| `/cancel <id|all>` | Скасовує очікуючі вихідні повідомлення |
| `/inbox [cancel <hash|all>]` | Перераховує або скасовує активні вхідні передачі |
| `/delivery [n]` | Показує останні n подій доставки (типово 15, макс. 50) |
| `/loadext <name>` | Завантажує розширення cog |
| `/reloadext <name>` | Перезавантажує завантажене розширення cog |

### Керування роутером

Тонкі обгортки над базовим `LXMRouter` для керування відправниками,
ticket-ами, керування вихідною чергою та синхронізації вузла
поширення. Усі приймають хеші адресатів як hex-рядки й повертають
`False`, коли роутер не працює (наприклад у `test_mode`).

**Керування відправниками (вхідне)**

- `ignore_destination(destination)` / `unignore_destination(destination)` / `is_ignored(destination)`:
  Відкидає вхідні повідомлення від відправника
- `allow_destination(destination)` / `disallow_destination(destination)`:
  Керування whitelist, коли роутер працює в режимі allow-list
- `prioritise_destination(destination)` / `unprioritise_destination(destination)`:
  Список пріоритетних відправників
- `set_inbound_stamp_cost(stamp_cost)`: Вимагає вартість stamp на
  вхідних повідомленнях (`None` очищає)
- `enforce_stamps()` / `ignore_stamps()`: Перемикачі вимоги вхідних
  stamp-ів

**Ticket-и**

- `generate_ticket(destination, expiry=None)`: Видає вхідний
  stamp-ticket для відправника
- `get_inbound_tickets(destination)`: Ticket-и, що утримуються для
  відправника
- `get_outbound_ticket(destination)` / `get_outbound_ticket_expiry(destination)` /
  `get_outbound_stamp_cost(destination)`: Стан вихідного ticket-а,
  дізнаний з мережі

**Вихідна черга**

- `outbound_queue()`: Знімок очікуючих вихідних повідомлень
- `get_outbound_progress(lxm_hash)`: Прогрес доставки для хеша
  повідомлення або `None`
- `cancel_outbound(message_id)`: Видаляє повідомлення з черги до
  доставки
- `delivery_link_available(destination)`: Чи існує активне
  RNS-з'єднання до адресата

**Вхідна черга**

- `has_message(message_hash)`: Чи вже було доставлено вхідний LXM-хеш
- `inbound_count()`: Активні вхідні передачі ресурсів у процесі
- `inbound_transfers()`: Знімок кожної передачі з хешем, розміром,
  прогресом і статусом
- `cancel_inbound(resource_hash)`: Перериває активну вхідну передачу
- `cancel_all_inbound()`: Перериває всі активні вхідні передачі,
  повертає скасовану кількість

**Виявлення пірів**

Метадані announce для адресатів, яких чув цей вузол:

- `get_peer_app_data(destination)`: Сирі байти announced app_data
- `get_peer_lxmf_data(destination)`: Декодовані метадані
  LXMF-announce (`display_name`, `stamp_cost`, `capabilities`) або
  `None`, коли пір не анонсував валідні дані LXMF
- `get_peer_announce(destination)`: Повний запис announce з hops,
  received_at, interface і app_data
- `list_peer_announces(limit=100)`: Усі почуті announces, найновіші
  першими

**Поширення**

- `sync_propagation_node(max_messages=None)`: Тягне повідомлення з
  налаштованого вузла поширення
- `cancel_propagation_sync()`: Зупиняє поточну синхронізацію
- `get_propagation_stats()`: Стан передачі та ліміти вузла або `None`
- `set_retain_on_node(retain)`: Зберігає доставлені повідомлення на
  вузлі
- `announce_propagation_node()`: Анонсує цей вузол як вузол поширення
- `allow_control_identity(destination)` / `disallow_control_identity(destination)`:
  Whitelist контрольного каналу поширення

**Прийом**

- `ingest_lxm_uri(uri)`: Імпортує повідомлення URI `lxm://` у вхідну
  чергу

## Діагностика

Коли повідомлення не течуть, дебагер перевіряє весь шлях замість
вгадування: конфігурацію Reticulum, стан спільного екземпляра,
інтерфейси, ідентичність, поведінку announce, конфігурацію доставки та
pipeline відправлення.

``` bash
lxmfy debug                          # повний doctor-звіт, збережений у файл
lxmfy debug probe <hash> --request-path --wait 30
lxmfy debug send <hash>              # відстежує тестове відправлення
lxmfy debug receive                  # перевіряє готовність прийому
lxmfy debug compare <hash_a> <hash_b>
lxmfy debug tips                     # виправлення поширених збоїв
```

Звіти типово редагуються задля приватності: домашні шляхи й хеші
обрізаються. `--json` видає машиночитаний вивід, `-o ФАЙЛ` записує
звіт, `--no-save` пропускає файл, `--no-privacy` зберігає повні значення
для локального використання, а `--no-color` або `NO_COLOR` вимикає
ANSI-вивід.

Ті самі перевірки можна викликати з коду:

``` python
report = bot.diagnose_connectivity()            # doctor-звіт як dict
probe = bot.diagnose_destination(               # дослідження ідентичності та шляху
    "<peer_hash>", request_path=True, wait=30,
)

debugger = bot.get_debugger()                   # повний API
checks = debugger.check_send_pipeline()
verdict = debugger.run_doctor(destination)
```

`lxmfy/debugger.py` також експортує самостійний помічник
`diagnose_destination(hash, ...)` плюс типи звітів `CheckResult`,
`DestinationProbe`, `DoctorReport` і `MessageDebugger` для власних
інструментів.

## Обробники повідомлень

LXMFy надає декоратори для обробки різних типів вхідних повідомлень:

### Обробник першого повідомлення

Обробляє перше повідомлення від кожного користувача:

``` python
@bot.on_first_message()
def welcome_user(sender, message):
    content = message.content.decode("utf-8")
    bot.send(sender, f"Welcome! You said: {content}")
    return True  # Поверніть True, щоб зупинити подальшу обробку
```

### Загальний обробник повідомлень

Обробляє всі вхідні повідомлення до обробки команд:

``` python
@bot.on_message()
def handle_all_messages(sender, message):
    content = message.content.decode("utf-8").strip()

    # Ваша логіка тут
    if content.startswith("echo:"):
        bot.send(sender, content[5:])
        return True  # Зупинити подальшу обробку

    return False  # Продовжити до обробки команд
```

Обробники повідомлень викликаються в такому порядку: 1. Обробник першого
повідомлення (якщо це перше повідомлення від цього відправника) 2.
Загальні обробники повідомлень (зареєстровані через `on_message()`) 3.
Обробка команд (якщо повідомлення починається з префікса команди)

### Резервний callback

`bot.received(fn)` реєструє callback, що виконується в кінці pipeline
для повідомлень, які ніщо інше не поглинуло: жоден обробник першого
повідомлення, жоден обробник `on_message` із поверненням True, жодна
відповідна команда чи NLP-інтент. Callback отримує той самий контекст
повідомлення, що й команди, з `msg.sender`, `msg.content`,
`msg.reply()` тощо.

``` python
@bot.received
def fallback(msg):
    msg.reply("Sorry, I did not understand that.")
```

Використовуйте як універсальний обробник для вільного тексту.

## Reticulum Relay Chat (RRC)

Боти можуть приєднуватися до хабів [RRC](https://rrc.kc1awv.net/) через
RNS Link з конвертами CBOR. Пакет: `lxmfy.rrc`.

### Параметри BotConfig

- `rrc_enabled` (bool, типово `False`): підключати налаштовані хаби при
  запуску
- `rrc_hubs` (список hex-хешів): хеші отримувачів хабів
- `rrc_rooms` (список str): кімнати для автоматичного приєднання після
  WELCOME
- `rrc_nick` (str або None): нікнейм у HELLO і повідомленнях кімнат
- `rrc_dest_name` (str, типово `"rrc.hub"`): ім'я отримувача,
  використане для побудови адреси хаба
- `rrc_auto_reconnect` (bool, типово `True`): перепідключатися після
  втрати link
- `rrc_persist_sessions` (bool, типово `True`): зберігати хаби і
  кімнати між перезапусками
- `reticulum_config_dir` (str або None): каталог конфігурації
  Reticulum. Також задається через `LXMFY_RETICULUM_CONFIG_DIR`.
  Використовуйте ту саму конфігурацію, що в MeshChatX (часто
  `~/.reticulum`), щоб анонси хаба були видимі.

### Приклад

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

# API часу виконання
# bot.connect_rrc(hub_hash, rooms=["general"])
# bot.rrc.send_message("general", "hello")
# bot.rrc.send_notice("general", "notice")
# bot.rrc.send_action("general", "waves")
# bot.rrc.join("ops")
# bot.rrc.part("ops")
# bot.rrc.status()
# bot.disconnect_rrc()
```

### Експортовані типи

- `RRCClient`: сесія з одним хабом
- `RRCManager`: менеджер кількох хабів (`bot.rrc`)
- `RRCMessage`: корисне навантаження події кімнати (`kind`, `room`,
  `text`, `nick`, `src`, `mention`, ...)
- `RRC_VERSION`: константа версії дротового протоколу
- `DEFAULT_DEST_NAME`: Типова назва адресата хаба
  (`"rrc.hub"`)
- `make_envelope`, `encode_envelope`, `decode_envelope`,
  `validate_envelope`, `normalize_room`: Помічники wire-формату для
  інструментів, що говорять із хабами напряму

Поширені події, що передаються обробникам `@bot.on_rrc`, включають
`status`, `welcome`, `joined`, `parted`, `msg`, `notice`, `action`,
`motd`, `error` і `rtt`.

# Шаблони

Фреймворк включає кілька готових до використання шаблонів ботів:

## EchoBot

Простий echo-бот, який повторює повідомлення:

``` python
from lxmfy.templates import EchoBot

bot = EchoBot()
bot.run()
```

## NoteBot

Бот для нотаток зі сховищем JSON:

``` python
from lxmfy.templates import NoteBot

bot = NoteBot()
bot.run()
```

## ReminderBot

Бот-нагадувач зі сховищем SQLite:

``` python
from lxmfy.templates import ReminderBot

bot = ReminderBot()
bot.run()
```

## RRCBot

RRC-бот для кімнат, який приєднується до налаштованих хабів і
відповідає на `@згадки`. Типово використовує хаб
`664fc0e8d2e448658e37bb3f34e6c88f`, кімнату `#general` і
`~/.reticulum`, коли доступний.

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

# Інструменти CLI

Фреймворк надає інструменти командного рядка для керування ботами.
Запуск `lxmfy` без аргументів відкриває інтерактивне меню.

``` bash
# Інтерактивний scaffold повного проєкту
lxmfy init mybot                 # тека проєкту, bot.py, cogs/, README
lxmfy init --here --yes          # поточна тека, приймає всі типові значення

# Створити один файл бота
lxmfy create mybot
lxmfy create --template echo mybot
lxmfy create --template rrc my_rrc_bot
lxmfy create mybot --no-cogs     # пропускає пакет cogs
lxmfy create --output dir/bot.py --name MyBot

# Запустити бота з шаблону
lxmfy run echo
lxmfy run rrc
lxmfy run reminder --name "MyReminder"

# Діагностувати з'єднання (див. розділ Діагностика)
lxmfy debug
lxmfy debug probe <hash> --request-path --wait 30

# Тестувати перевірку підписів з повідомленням
lxmfy signatures test

# Увімкнути перевірку підписів
lxmfy signatures enable

# Вимкнути перевірку підписів
lxmfy signatures disable
```

`lxmfy init` запитує назву проєкту, шаблон, backend сховища, префікс
команд і хеші адмінів. Кожне питання приймає натомість прапорець:
`--dir`, `--bot-name`, `--template`, `--storage`, `--prefix`,
`--admins`, `--no-cogs`, `--force`, `--yes`. На не-TTY stdin беруться
типові значення.

Шаблони для `create` і `run`: `basic`, `echo`, `reminder`, `note`,
`cogtest`, `rrc`.

# Обробка помилок

Перехоплюйте помилки завершення роботи та виконання навколо `bot.run()`:

``` python
try:
    bot.run()
except KeyboardInterrupt:
    bot.cleanup()
except Exception as e:
    logger.error(f"Error running bot: {str(e)}")
```

# Довідник модулів

Згенеровано з docstring у вихідному коді.

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
