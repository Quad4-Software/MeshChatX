# Создание ботов

## Базовая структура

Минимальный бот LXMFy включает:

1.  Импорт `LXMFBot`.
2.  Создание экземпляра `LXMFBot` с нужной конфигурацией.
3.  Определение команд или обработчиков событий.
4.  Запуск бота через `bot.run()`.

``` python
from lxmfy import LXMFBot

# 1. Создаём экземпляр бота
bot = LXMFBot(
    name="SimpleBot",
    command_prefix="!",
    storage_path="simple_data"
)

# 2. Определяем команды
@bot.command(name="ping", description="Responds with pong")
def ping_command(ctx):
    # ctx — объект контекста с информацией о сообщении
    # ctx.sender: LXMF-хэш отправителя
    # ctx.content: полный текст сообщения
    # ctx.args: список аргументов после команды
    # ctx.reply(message): функция отправки ответа
    #   (принимает и именованные аргументы, например title="My Title", lxmf_fields=some_fields)
    ctx.reply("Pong!")

# Для долгих задач можно использовать потоковые команды:
# import time
# @bot.command(name="long_op", description="Performs a long operation in a separate thread", threaded=True)
# def long_op_command(ctx):
#     ctx.reply("Starting long operation...")
#     time.sleep(10) # Имитация долгой операции
#     ctx.reply("Long operation complete!")
# Важно: потоковые команды не должны напрямую обращаться к RNS или lxmfy.transport.py.

@bot.command(name="greet", description="Greets the user")
def greet_command(ctx):
    if ctx.args:
        name = " ".join(ctx.args)
        ctx.reply(f"Hello, {name}!")
    else:
        ctx.reply("Hello there! Tell me your name: !greet <your_name>")

# 3. Запускаем бота
if __name__ == "__main__":
    print(f"Starting bot: {bot.config.name}")
    print(f"Bot LXMF Address: {bot.local.hash}")
    bot.run()
```

## Использование шаблонов

LXMFy предоставляет несколько шаблонов для типовых ботов. CLI может сгенерировать файл бота на основе шаблона.

Для полной директории проекта вместо одного файла `lxmfy init`
генерирует `bot.py`, пакет `cogs`, README и `.gitignore`, по пути
спрашивая шаблон, backend хранилища, префикс команд и хеши админов.

``` bash
# Создать echo-бота
lxmfy create --template echo my_echo_bot

# Создать бота-напоминалку (использует хранилище SQLite)
lxmfy create --template reminder my_reminder_bot

# Создать бота для заметок (использует хранилище JSON)
lxmfy create --template note my_note_bot

# Создать тестового бота для когов (проверяет загрузку когов)
lxmfy create --template cogtest my_cog_test_bot

# Создать RRC-бота для комнат (подключается к хабам и отвечает на @упоминания)
lxmfy create --template rrc my_rrc_bot

# Или запустить шаблон напрямую
lxmfy run rrc
```

Эти команды создают Python-файл (например, `my_echo_bot.py`), который импортирует и запускает выбранный шаблон. Дальше можно изменять сгенерированный файл или сам код шаблона (`lxmfy/templates/...`).

**Пример сгенерированного файла (`my_cog_test_bot.py`):**

``` python
from lxmfy.templates import CogTestBot

if __name__ == "__main__":
    bot = CogTestBot() # Создаёт экземпляр шаблона CogTestBot
    # Можно переопределить имя по умолчанию:
    # bot.bot.name = "My Cog Test Bot"
    bot.run()
```

## Конфигурация бота

При создании экземпляра `LXMFBot` можно передать различные именованные аргументы для настройки поведения. Список основных опций — в разделе `BotConfig` [Справочника API](api-reference.md) и в [Быстром старте](quick-start.md).

``` python
from lxmfy import LXMFBot

bot = LXMFBot(
    name="ConfiguredBot",
    announce=3600, # Анонсировать раз в час
    admins={"your_admin_hash_here"}, # Задать администратора(ов)
    command_prefix="$", # Использовать '$' как префикс
    storage_type="sqlite", # Использовать базу SQLite
    storage_path="data/my_bot_data.db", # Путь к файлу БД
    rate_limit=10, # Разрешить 10 сообщений / минуту
    cooldown=30, # Охлаждение 30 секунд
    permissions_enabled=True # Включить ролевые права
)

if __name__ == "__main__":
    # Конфигурацию можно менять и после создания экземпляра
    # Внимание: часть настроек лучше задавать при инициализации
    bot.config.max_warnings = 5
    bot.spam_protection.config.max_warnings = 5 # Обновить и защиту от спама

    bot.run()
```

### Установка иконки бота (поле LXMF)

Боту можно назначить пользовательскую иконку, которая отображается в совместимых клиентах LXMF. Используется `LXMF.FIELD_ICON_APPEARANCE`, поле можно задавать при отправке сообщений.

Сначала нужные импорты:

``` python
from lxmfy import IconAppearance, pack_icon_appearance_field
```

Затем определяем и используем иконку:

``` python
# В классе бота или при настройке
icon_data = IconAppearance(
    icon_name="robot_2",  # Выбор из Material Symbols
    fg_color=b'\x00\xFF\x00',  # Зелёный
    bg_color=b'\x33\x33\x33'   # Тёмно-серый
)
self.bot_icon_field = pack_icon_appearance_field(icon_data)

# При отправке сообщения или ответе:
ctx.reply("Message from your bot!", lxmf_fields=self.bot_icon_field)
# или
# bot.send(destination, "Another message", lxmf_fields=self.bot_icon_field)
```

`self.bot_icon_field` можно вычислить один раз и переиспользовать для всех сообщений бота.

## Структурированные команды через поля LXMF

Помимо текстовых команд LXMFy поддерживает команды, переданные через поля сообщений LXMF — `FIELD_COMMANDS` (`0x09`). Это удобно для структурированных запросов и ответов между клиентами LXMF и ботами.

Когда сообщение содержит `FIELD_COMMANDS`, бот извлекает имя команды и аргументы, направляет их через тот же реестр команд, что и текстовые, и автоматически включает `FIELD_RESULTS` (`0x0A`) в ответ.

**Приём структурированных команд**

``` python
from lxmfy import LXMFBot

bot = LXMFBot(name="FieldBot")

@bot.command(name="add", description="Add two numbers")
def add_command(ctx):
    if len(ctx.args) >= 2:
        try:
            result = float(ctx.args[0]) + float(ctx.args[1])
            ctx.reply(str(result))
        except ValueError:
            ctx.reply("Invalid numbers")
    else:
        ctx.reply("Usage: add <a> <b>")
```

Объект `ctx` в обработчиках полевых команд включает:

- `ctx.fields`: исходный словарь полей LXMF входящего сообщения
- `ctx.request_id`: `request_id` из входящего `FIELD_COMMANDS` (если есть)

**Отправка структурированной команды из клиента LXMF**

``` python
import LXMF
from lxmfy import FIELD_COMMANDS

lxm = LXMF.LXMessage(
    destination,
    source,
    b"",  # содержимое может быть пустым для команд только через поля
    desired_method=LXMF.LXMessage.DIRECT,
)
lxm.fields[FIELD_COMMANDS] = {
    "command": "add",
    "args": ["3", "5"],
    "request_id": "req-42",  # необязательно, для корреляции
}
router.handle_outbound(lxm)
```

**Отключение полевых команд**

Чтобы бот игнорировал `FIELD_COMMANDS` и обрабатывал только текстовые команды:

``` python
bot = LXMFBot(
    name="TextOnlyBot",
    lxmf_commands_enabled=False,
)
```

## Использование когов (расширений)

Коги позволяют организовать команды и обработчики событий в отдельных файлах (модулях), чтобы основной файл бота оставался чистым.

1.  **Создайте каталог `cogs`** (или тот, что указан в `cogs_dir` в `BotConfig`).
2.  **Создайте Python-файлы** внутри каталога `cogs` (например, `utility.py`).
3.  **Определите класс**, наследующий `lxmfy.Cog` (необязательно, но хорошая практика), либо обычный класс.
4.  **Определите команды** как методы класса с декоратором `@Command`.
5.  **Создайте функцию `setup(bot)`** в файле кога — LXMFy вызовет её для регистрации кога.

**Пример (`cogs/utility.py`):**

``` python
from lxmfy import Command
from lxmfy.commands import Cog  # Импорт Cog при наследовании
import time

class UtilityCog: # Или class UtilityCog(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = time.time()

    @Command(name="uptime", description="Shows bot uptime")
    # Внимание: методы в когах обычно принимают 'self' и 'ctx'
    def uptime_command(self, ctx):
        uptime_seconds = time.time() - self.start_time
        ctx.reply(f"Bot has been running for {uptime_seconds:.2f} seconds.")

    @Command(name="info", description="Shows bot info")
    def info_command(self, ctx):
        info = (
            f"Bot Name: {self.bot.config.name}\n"
            f"Owner(s): {', '.join(self.bot.config.admins) or 'None'}\n"
            f"Prefix: {self.bot.config.command_prefix}"
        )
        ctx.reply(info)

    @Command(name="threaded_cog_task", description="Performs a long task in a cog thread", threaded=True)
    def threaded_cog_task(self, ctx):
        ctx.reply("Starting a long cog task... this will run in a separate thread.")
        time.sleep(7) # Имитация долгой операции
        ctx.reply("Long cog task completed!")

# Эта функция обязательна для загрузки кога
def setup(bot):
    cog_instance = UtilityCog(bot)
    bot.add_cog(cog_instance) # Регистрация экземпляра кога в боте
```

**Основной файл бота (`my_bot.py`):**

``` python
from lxmfy import LXMFBot

bot = LXMFBot(
    name="CogBot",
    cogs_enabled=True, # Убедитесь, что коги включены (по умолчанию)
    cogs_dir="cogs" # Укажите каталог
)

if __name__ == "__main__":
    # Коги загружаются автоматически при инициализации LXMFBot,
    # если cogs_enabled равно True.
    bot.run()
```

При запуске бот автоматически найдёт `utility.py`, вызовет его функцию `setup`, которая создаст экземпляр `UtilityCog` и зарегистрирует его через `bot.add_cog()`. Команды кога (`uptime`, `info`) станут доступны.

## Внешние скриптовые коги (поддержка других языков)

Расширения бота можно писать и на других языках (Bash, Ruby, Perl, Go, C) через внешние скриптовые коги.

1.  **Создайте исполняемый скрипт** в каталоге `cogs`.
2.  **Добавьте shebang** в начало скрипта (например, `#!/bin/bash`).
3.  **Убедитесь, что скрипт исполняемый** (`chmod +x your_script`).

При запуске бот автоматически зарегистрирует любой исполняемый файл в каталоге `cogs` (не заканчивающийся на `.py`) как команду бота.

**Протокол аргументов:**

- `$1`: LXMF-хэш отправителя.
- `$2`: полный текст сообщения.
- `$3`, `$4`, ...: отдельные аргументы команды.

**Переменные окружения:**

- `LXMFY_SENDER`: хэш идентификатора отправителя.
- `LXMFY_CONTENT`: полный текст сообщения.
- `LXMFY_HAS_ADMIN`: `true` или `false` в зависимости от статуса администратора у отправителя.

**Пример кога на Bash (`cogs/greet.sh`):**

``` bash
#!/bin/bash
echo "Hello from Bash! You sent: $2"
```

Когда пользователь отправляет `/greet hello`, бот выполнит этот скрипт и ответит его stdout: `Hello from Bash! You sent: /greet hello`.

## Локальная классификация намерений (NLP)

LXMFy поставляется с локальным классификатором намерений. Он сопоставляет текст сообщения с размеченными примерами фраз, когда текст не совпадает с префиксом команды в точности.

1.  **Включите NLP** в конфигурации бота: `nlp_enabled=True`.
2.  **Определите намерения** декоратором `@bot.intent`.

``` python
@bot.intent("help", examples=["how do I use this?", "show me commands", "help me please"])
def help_intent(msg):
    msg.reply("I can help! Try typing /help to see a list of commands.")
```

Сопоставление использует векторы TF-IDF и косинусное сходство. Всё вычисление выполняется на хосте бота. Текст не отправляется во внешние API.

**Экспорт и импорт модели**

Экспортируйте и импортируйте обученную модель, чтобы большие боты не переобучались при каждом запуске:

``` python
# Экспорт модели
model_data = bot.nlp.export_model()
# Сохраните model_data в файл или базу данных

# Позже импортируйте обратно
bot.nlp.import_model(model_data)
```

## Поддержка RNS Link

Боты могут устанавливать и принимать прямые RNS Link для состоятельного, потокового или более ёмкого трафика, чем отдельные пакеты LXMF.

1.  **Включите поддержку Link** в конфигурации: `link_support_enabled=True`.
2.  **Запросите link**: `bot.request_link(destination_hash)`. Можно также указать своё имя приложения и аспекты: `bot.request_link(dest, callback, "my_app", "aspect1")`.
3.  **Обрабатывайте входящие link**: зарегистрируйте обработчик через `bot.on_link(handler)`.

``` python
def handle_link(link):
    print(f"Link established with {RNS.hexrep(link.destination.hash)}")
    # Теперь link можно использовать для прямого взаимодействия RNS

bot.on_link(handle_link)
```

**Безопасность и изоляция:**

- **Таймауты:** у внешних когов есть таймаут по умолчанию (30 с) против зависаний. Настраивается через `external_cogs_timeout`.
- **Потоки:** все внешние коги работают в отдельных потоках и не блокируют бота.
- **Песочница процесса бота (только Linux):** когда `landlock_enabled=True` (по умолчанию) и ядро поддерживает Landlock LSM (5.13+), бот применяет файловую песочницу к собственному процессу после запуска. Записываемые пути ограничены хранилищем, конфигурацией, когами, конфигурацией Reticulum и временными каталогами. Отключить — переменной окружения `LXMFY_LANDLOCK=0`, принудительно включить — `LXMFY_LANDLOCK=1`.
- **Песочница внешних когов (только Linux):** когда `external_cogs_sandbox_enabled=True` (по умолчанию), исполняемые скриптовые коги работают в ограниченном окружении. `external_cogs_sandbox_type` принимает значения:
  - `auto` (по умолчанию): предпочитает Landlock, если поддерживается, иначе `bubblewrap` (`bwrap`), иначе `firejail`
  - `landlock`: только Landlock через `preexec_fn` (правила уже, чем у песочницы процесса бота)
  - `bwrap`: песочница bubblewrap с read-only bind
  - `firejail`: приватный профиль firejail без сети
  - `none`: без песочницы для подпроцесса
- **Статус:** вызов `bot.get_landlock_status()` показывает поддержку ядром, был ли запрошен Landlock и активна ли песочница процесса бота.

## Обработка сообщений

LXMFy предоставляет несколько способов обрабатывать входящие сообщения на разных стадиях.

### Обработчик первого сообщения

Обработка первого сообщения от каждого нового пользователя (полезно для приветствий):

``` python
from lxmfy import LXMFBot

bot = LXMFBot(
    name="WelcomeBot",
    first_message_enabled=True  # Должно быть True (по умолчанию)
)

@bot.on_first_message()
def welcome_new_user(sender, message):
    content = message.content.decode("utf-8")
    bot.send(
        sender,
        f"Welcome to the bot! You said: {content}\n\n"
        "Type /help to see available commands."
    )
    return True  # Верните True, чтобы остановить дальнейшую обработку сообщения

if __name__ == "__main__":
    bot.run()
```

### Общий обработчик сообщений

Обработка всех входящих сообщений до обработки команд:

``` python
from lxmfy import LXMFBot

bot = LXMFBot(name="EchoBot")

@bot.on_message()
def echo_non_commands(sender, message):
    content = message.content.decode("utf-8").strip()

    # Проверяем, команда ли это — тогда пусть обрабатывает обработчик команд
    if content.startswith(bot.config.command_prefix):
        command_name = content.split()[0][len(bot.config.command_prefix):]
        if command_name in bot.commands:
            return False  # Отдать обработчику команд

    # Не команда — эхо обратно
    bot.send(sender, f"You said: {content}")
    return False  # Верните False для продолжения обработки (команды всё равно не совпадут)

@bot.command(name="hello", description="Say hello")
def hello_command(ctx):
    ctx.reply("Hello! This is a command response.")

if __name__ == "__main__":
    bot.run()
```

Порядок обработки сообщений:

1.  **Обработчик первого сообщения** (если `first_message_enabled=True` и это первое сообщение от отправителя)
2.  **Общие обработчики сообщений** (зарегистрированные через `@bot.on_message()`)
3.  **Обработка команд** (если сообщение совпадает с зарегистрированной командой)

Обработчики могут возвращать `True`, чтобы остановить дальнейшую обработку, или `False`, чтобы перейти к следующей стадии.

## Обработка событий

Обработчики различных событий бота регистрируются декоратором `@bot.events.on()`.

``` python
from lxmfy import LXMFBot
from lxmfy.events import EventPriority # Необязательно, для приоритета

bot = LXMFBot(name="EventBot")

@bot.events.on("message_received")
def log_message(event):
    # Объект события содержит детали
    sender = event.data.get("sender")
    message_content = event.data.get("message").content.decode('utf-8', errors='ignore')
    print(f"Received message from {sender}: {message_content}")

    # Обработку события можно отменить (например, остановить обработку сообщения)
    # if sender == "some_blocked_hash":
    #    event.cancel()

@bot.events.on("command_executed", priority=EventPriority.LOW)
def log_command(event):
    # Пример: event.data может содержать {'command_name': 'ping', 'sender': '...', ...}
    command_name = event.data.get('command_name', 'unknown')
    sender = event.data.get('sender', 'unknown')
    print(f"Command '{command_name}' executed by {sender}")

# Можно определять и свои события
@bot.command(name="special")
def special_command(ctx):
    ctx.reply("Doing something special!")
    # Отправка пользовательского события
    bot.events.dispatch(Event("special_action_taken", data={"user": ctx.sender}))

@bot.events.on("special_action_taken")
def handle_special(event):
    user = event.data.get("user")
    print(f"Special action was taken by user: {user}")


if __name__ == "__main__":
    bot.run()
```

Подробности о структуре `Event` и приоритетах — в `lxmfy/events.py`.

## Хранилище

LXMFy предоставляет бэкенды хранилища JSON, SQLite, MsgPack и In-Memory.

- **JSON:** простой, читаемый человеком. Подходит для небольших данных. Настройка: `storage_type="json"` и `storage_path="your_data_dir"`.
- **SQLite:** эффективнее для больших данных или частых записей. Настройка: `storage_type="sqlite"` и `storage_path="your_db_file.db"`.
- **MsgPack:** компактный бинарный формат с той же раскладкой
  файл-на-ключ, что и JSON. Настройка: `storage_type="msgpack"` и
  `storage_path="your_data_dir"`.
- **Memory:** хранилище полностью в ОЗУ. Состояние теряется при остановке. Настройка: `storage_type="memory"`.

Доступ к хранилищу — через `bot.storage`:

``` python
# Сохранить данные
bot.storage.set("user_prefs:" + ctx.sender, {"theme": "dark"})

# Получить данные (со значением по умолчанию)
prefs = bot.storage.get("user_prefs:" + ctx.sender, {})
theme = prefs.get("theme", "light")

# Проверить существование данных
if bot.storage.exists("some_key"):
    print("Key exists!")

# Удалить данные
bot.storage.delete("old_data_key")

# Сканировать ключи по префиксу (удобно для перечисления данных пользователей)
user_keys = bot.storage.scan("user_prefs:")
for key in user_keys:
    user_data = bot.storage.get(key)
    print(f"Data for {key}: {user_data}")
```

Подробности — в `lxmfy/storage.py` и справочнике API.

## Права доступа

LXMFy включает необязательную ролевую систему прав. Включается через `permissions_enabled=True` при инициализации `LXMFBot`.

- **Роли:** роли с конкретными правами (например, `DefaultPerms.MANAGE_USERS`).
- **Права:** гранулярные флаги в `DefaultPerms` (например, `USE_COMMANDS`, `BYPASS_SPAM`).
- **Назначение:** роли назначаются хэшам пользователей.

Подробности использования — в `lxmfy/permissions.py`, справочнике API и примерах когов.

## Проверка подписей

LXMFy предоставляет настройки для встроенной криптографической подписи и проверки сообщений LXMF. Все сообщения LXMF автоматически подписываются стеком LXMF/RNS — LXMFy позволяет применять политику проверки подписей.

**Конфигурация:**

Включите проверку подписей в конфигурации бота:

``` python
bot = LXMFBot(
    name="SecureBot",
    signature_verification_enabled=True,  # Включить проверку подписей
    require_message_signatures=False      # True — отклонять неподписанные сообщения
)
```

**Как это работает:**

LXMF автоматически выполняет все криптографические операции:

1.  **Исходящие сообщения:** LXMF автоматически подписывает все сообщения идентификатором RNS отправителя при упаковке.
2.  **Входящие сообщения:** LXMF автоматически проверяет подписи по идентификатору RNS отправителя и предоставляет результаты проверки.
3.  **Роль LXMFy:** LXMFy проверяет результаты валидации LXMF и применяет вашу политику:
    - Если `signature_verification_enabled=False`: все сообщения принимаются (по умолчанию)
    - Если `signature_verification_enabled=True` и `require_message_signatures=False`: сообщения принимаются, но неподписанные/невалидные подписи записываются в журнал
    - Если `signature_verification_enabled=True` и `require_message_signatures=True`: неподписанные или невалидные сообщения отклоняются
4.  **Интеграция с правами:** пользователи с правом `BYPASS_SPAM` могут обходить требования проверки подписей.

**Управление через CLI:**

Настройками проверки подписей можно управлять через CLI:

``` bash
# Проверить проверку подписей
lxmfy signatures test

# Включить проверку подписей
lxmfy signatures enable

# Отключить проверку подписей
lxmfy signatures disable
```

**Технические детали:**

LXMF использует подписи Ed25519 из криптосистемы RNS. Каждое сообщение LXMF содержит подпись отправителя, которая проверяется по известному идентификатору RNS. LXMFy просто читает свойства `message.signature_validated` и `message.unverified_reason` из LXMF для применения политики безопасности бота.

## Доставка сообщений

### Использование узлов распространения

Отправка сообщений через конкретные узлы распространения LXMF:

``` python
from lxmfy import LXMFBot

bot = LXMFBot(name="PropagationBot")

@bot.command(name="send", description="Send via propagation node")
def send_command(ctx):
    # Установить конкретный узел распространения один раз (на уровне конфигурации)
    bot.set_propagation_node("<propagation_node_hash_here>")

    # Отправить с настроенной стратегией доставки
    bot.send(
        ctx.sender,
        "This message will use direct delivery with propagation fallback as configured"
    )
```

Используйте узел распространения, когда получатель офлайн или прямая доставка постоянно не проходит по текущему пути.

### Настройка повторных попыток

Автоматические повторные попытки для неудачных доставок настраиваются в конфигурации бота:

``` python
from lxmfy import LXMFBot

bot = LXMFBot(name="ReliableBot")

bot = LXMFBot(
    name="ReliableBot",
    direct_delivery_retries=5,  # Повторять прямую доставку до 5 раз
    propagation_fallback_enabled=True
)

@bot.command(name="important", description="Send important message with retries")
def important_command(ctx):
    bot.send(ctx.sender, "This is an important message")

@bot.command(name="normal", description="Send with default retries")
def normal_command(ctx):
    # direct_delivery_retries по умолчанию равно 3
    bot.send(ctx.sender, "This message uses default retry settings")
```

Система повторных попыток:

- Автоматически отслеживает попытки доставки по каждому получателю
- Повторяет неудачные прямые доставки до `direct_delivery_retries` раз
- Сбрасывает счётчик повторов после успешной доставки
- Записывает попытки и неудачи в журнал для отладки

### Отложенные отправки и stamp-ы

Две детали доставки, которые стоит знать заранее:

- **Отложенные отправки**: когда идентичность адресата ещё не
  известна, `send()` удерживает сообщение в хранилище (ключи
  конфигурации `pending_sends_*` управляют отставанием) и выталкивает
  его, когда пир анонсируется. Передайте `defer=False` в отправку,
  чтобы отбросить вместо удержания.
- **Stamp-ы**: `stamp_cost` устанавливает требование proof-of-work на
  вход, `require_stamps` отклоняет сообщения, которые его не
  выполняют, а `include_tickets` (по умолчанию) прикладывает ticket-ы
  ответа, чтобы пиры могли ответить вашему боту без оплаты собственной
  стоимости stamp.

Когда доставка работает плохо, `lxmfy debug` проходит весь путь
(конфигурация, экземпляр, интерфейсы, идентичность, pipeline
отправки) и пишет редактированный отчёт, которым можно поделиться. Те
же проверки доступны как `bot.diagnose_connectivity()` и
`bot.diagnose_destination(hash)`.

Смотрите [Справочник API](api-reference.md) для
всей поверхности доставки: повторы, узлы распространения,
персистентность очереди, поток событий доставки и административные
команды `/queue`, `/cancel`, `/inbox`, `/delivery`.

## Reticulum Relay Chat (RRC)

Боты LXMFy могут подключаться к хабам [RRC](https://rrc.kc1awv.net/) как обычные клиенты по RNS Link с конвертами CBOR. Совместимо с хабами стиля NomadNet и rrcd (включая MeshChatX, когда он хостит или подключён к тому же хабу).

### Конфигурация Reticulum важна

Бот должен использовать **ту же** сеть Reticulum, что и хаб. MeshChatX обычно использует `~/.reticulum` с backbone или TCP-интерфейсами. Локальный каталог `config/` проекта часто использует изолированное имя экземпляра и только AutoInterface, поэтому анонсы хаба не приходят и вы видите `Hub identity unknown`.

Предпочтительно одно из:

- Установить `reticulum_config_dir` в пользовательскую конфигурацию (обычно `~/.reticulum`)
- Или экспортировать `LXMFY_RETICULUM_CONFIG_DIR=~/.reticulum`
- Держать запущенным MeshChatX или `rnsd`, чтобы общий экземпляр был поднят до старта бота

Шаблон `rrc` по умолчанию использует `~/.reticulum`, если этот каталог существует.

### Быстрый старт с шаблоном

``` bash
lxmfy run rrc
```

По умолчанию:

- Хаб: `664fc0e8d2e448658e37bb3f34e6c88f`
- Комната: `#general`
- Конфигурация Reticulum: `~/.reticulum` (или `LXMFY_RETICULUM_CONFIG_DIR`)

В журнале должны появиться записи о подключении к хабу, welcome, авто-join и `RRC joined #general`.

### Программный RRC-бот

``` python
from lxmfy import LXMFBot, RRCMessage

bot = LXMFBot(
    name="RoomBot",
    reticulum_config_dir="~/.reticulum",
    rrc_enabled=True,
    rrc_hubs=["your_rrc_hub_destination_hash"],
    rrc_rooms=["general"],
    rrc_nick="RoomBot",
    rrc_auto_reconnect=True,
    rrc_persist_sessions=True,
)

@bot.on_rrc
def on_rrc(event, client, payload):
    if event == "welcome":
        bot.logger.info("Welcomed by hub")
        return
    if event != "msg" or not isinstance(payload, RRCMessage):
        return
    if payload.mention and payload.room:
        client.send_message(
            payload.room,
            f"Heard you, {payload.nick}",
        )

bot.run()
```

Или подключение во время работы:

``` python
bot.connect_rrc("hub_destination_hash", rooms=["general"])
bot.rrc.send_message("general", "hello room")
bot.rrc.send_action("general", "waves")
bot.disconnect_rrc()
```

### Поведение сессии

- HELLO / WELCOME, JOIN / PART, MSG / NOTICE / ACTION, PING / PONG, ERROR, RESOURCE_ENVELOPE
- Автопереподключение с повторным входом в комнаты после WELCOME
- Клиентское применение лимита хаба и rate-limit
- Персистентность сессий между перезапусками (`rrc_persist_sessions`, по умолчанию включена)
- Персистентность исходящей очереди LXMF настраивается отдельно (`message_persistence_enabled`)
