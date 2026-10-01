# Створення ботів

## Базова структура

Мінімальний бот LXMFy складається з таких кроків:

1.  Імпортуйте `LXMFBot`.
2.  Створіть екземпляр `LXMFBot` з потрібною конфігурацією.
3.  Визначте команди або обробники подій.
4.  Запустіть бота через `bot.run()`.

``` python
from lxmfy import LXMFBot

# 1. Створюємо екземпляр бота
bot = LXMFBot(
    name="SimpleBot",
    command_prefix="!",
    storage_path="simple_data"
)

# 2. Визначаємо команди
@bot.command(name="ping", description="Responds with pong")
def ping_command(ctx):
    # ctx - це об'єкт контексту з інформацією про повідомлення
    # ctx.sender: LXMF-хеш відправника
    # ctx.content: повний вміст повідомлення
    # ctx.args: список аргументів після команди
    # ctx.reply(message): функція для надсилання відповіді
    #   (також приймає іменовані аргументи, як-от title="My Title", lxmf_fields=some_fields)
    ctx.reply("Pong!")

# Для довготривалих задач можна використовувати команди в окремому потоці:
# import time
# @bot.command(name="long_op", description="Performs a long operation in a separate thread", threaded=True)
# def long_op_command(ctx):
#     ctx.reply("Starting long operation...")
#     time.sleep(10) # Імітація довготривалої операції
#     ctx.reply("Long operation complete!")
# Важливо: команди в окремих потоках не повинні напряму взаємодіяти з RNS або lxmfy.transport.py.

@bot.command(name="greet", description="Greets the user")
def greet_command(ctx):
    if ctx.args:
        name = " ".join(ctx.args)
        ctx.reply(f"Hello, {name}!")
    else:
        ctx.reply("Hello there! Tell me your name: !greet <your_name>")

# 3. Запускаємо бота
if __name__ == "__main__":
    print(f"Starting bot: {bot.config.name}")
    print(f"Bot LXMF Address: {bot.local.hash}")
    bot.run()
```

## Використання шаблонів

LXMFy надає кілька шаблонів для типових видів ботів. Ви можете
використати CLI для генерації файла бота на основі шаблону.

Для повної теки проєкту замість одного файлу `lxmfy init`
генерує `bot.py`, пакет `cogs`, README і `.gitignore`, дорогою питаючи
про шаблон, backend сховища, префікс команд і хеші адмінів.

``` bash
# Створити echo-бота
lxmfy create --template echo my_echo_bot

# Створити бота-нагадувача (використовує сховище SQLite)
lxmfy create --template reminder my_reminder_bot

# Створити бота для нотаток (використовує сховище JSON)
lxmfy create --template note my_note_bot

# Створити тестового бота для коґів (перевіряє завантаження коґів)
lxmfy create --template cogtest my_cog_test_bot

# Створити RRC-бота для кімнат (підключається до хабів і відповідає на @згадки)
lxmfy create --template rrc my_rrc_bot

# Або запустити шаблон напряму
lxmfy run rrc
```

Виконання цих команд створює файл Python (наприклад, `my_echo_bot.py`),
який імпортує й запускає вибраний шаблон. Далі ви можете змінити
згенерований файл або сам код шаблону (`lxmfy/templates/...`).

**Приклад згенерованого файла (`my_cog_test_bot.py`):**

``` python
from lxmfy.templates import CogTestBot

if __name__ == "__main__":
    bot = CogTestBot() # Створює екземпляр шаблону CogTestBot
    # За бажанням можна перевизначити типове ім'я:
    # bot.bot.name = "My Cog Test Bot"
    bot.run()
```

## Конфігурація бота

Під час створення екземпляра `LXMFBot` ви можете передавати різні
іменовані аргументи для налаштування його поведінки. Список поширених
параметрів див. у розділі `BotConfig` у [Довіднику
API](api-reference.md) або в [посібнику швидкого
старту](quick-start.md).

``` python
from lxmfy import LXMFBot

bot = LXMFBot(
    name="ConfiguredBot",
    announce=3600, # Анонсувати щогодини
    admins={"your_admin_hash_here"}, # Задати адміністраторів
    command_prefix="$", # Використовувати '$' як префікс
    storage_type="sqlite", # Використовувати базу даних SQLite
    storage_path="data/my_bot_data.db", # Вказати шлях до файла БД
    rate_limit=10, # Дозволити 10 повідомлень за хвилину
    cooldown=30, # Період очікування 30 секунд
    permissions_enabled=True # Увімкнути рольові права
)

if __name__ == "__main__":
    # Конфігурацію також можна змінювати після створення екземпляра
    # Примітка: деякі параметри краще задавати під час ініціалізації
    bot.config.max_warnings = 5
    bot.spam_protection.config.max_warnings = 5 # Оновити також захист від спаму

    bot.run()
```

### Встановлення іконки бота (поле LXMF)

Ви можете задати боту власну іконку, яка відображатиметься у сумісних
клієнтах LXMF. Для цього використовується `LXMF.FIELD_ICON_APPEARANCE`,
її можна задавати під час надсилання повідомлень.

Спершу переконайтеся, що у вас є потрібні імпорти:

``` python
from lxmfy import IconAppearance, pack_icon_appearance_field
```

Далі ви можете визначити й використовувати іконку:

``` python
# У класі бота або під час налаштування
icon_data = IconAppearance(
    icon_name="robot_2",  # Виберіть з Material Symbols
    fg_color=b'\x00\xFF\x00',  # Зелений
    bg_color=b'\x33\x33\x33'   # Темно-сірий
)
self.bot_icon_field = pack_icon_appearance_field(icon_data)

# Під час надсилання повідомлення або відповіді:
ctx.reply("Message from your bot!", lxmf_fields=self.bot_icon_field)
# або
# bot.send(destination, "Another message", lxmf_fields=self.bot_icon_field)
```

Це `self.bot_icon_field` можна обчислити один раз і повторно
використовувати для всіх повідомлень бота.

## Структуровані команди через поля LXMF

Окрім текстових команд, LXMFy підтримує команди, надіслані через поля
повідомлень LXMF, за допомогою `FIELD_COMMANDS` (`0x09`). Це зручно для
структурованих процесів запит/відповідь між клієнтами LXMF і ботами.

Коли повідомлення містить `FIELD_COMMANDS`, бот витягує ім'я команди та
аргументи, спрямовує їх через той самий реєстр команд, що й текстові
команди, і автоматично додає `FIELD_RESULTS` (`0x0A`) у відповідь.

**Отримання структурованих команд**

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

Об'єкт `ctx` у зворотних викликах польових команд містить:

- `ctx.fields`: сирий словник полів LXMF з вхідного повідомлення
- `ctx.request_id`: `request_id` з вхідного `FIELD_COMMANDS` (якщо є)

**Надсилання структурованої команди з клієнта LXMF**

``` python
import LXMF
from lxmfy import FIELD_COMMANDS

lxm = LXMF.LXMessage(
    destination,
    source,
    b"",  # вміст може бути порожнім для команд лише з полями
    desired_method=LXMF.LXMessage.DIRECT,
)
lxm.fields[FIELD_COMMANDS] = {
    "command": "add",
    "args": ["3", "5"],
    "request_id": "req-42",  # необов'язково, для кореляції
}
router.handle_outbound(lxm)
```

**Вимкнення польових команд**

Якщо ви хочете, щоб бот ігнорував `FIELD_COMMANDS` і обробляв лише
текстові команди, задайте:

``` python
bot = LXMFBot(
    name="TextOnlyBot",
    lxmf_commands_enabled=False,
)
```

## Використання коґів (розширень)

Коґи дозволяють організувати команди та обробники подій в окремих файлах
(модулях), зберігаючи головний файл бота чистим.

1.  **Створіть каталог `cogs`** (або той, який ви задали в `cogs_dir` у
    `BotConfig`).
2.  **Створіть файли Python** всередині каталогу `cogs` (наприклад,
    `utility.py`).
3.  **Визначте клас**, який успадковує `lxmfy.Cog` (необов'язково, але
    гарна практика), або просто звичайний клас.
4.  **Визначте команди** як методи класу з декоратором `@Command`.
5.  **Створіть функцію `setup(bot)`** у файлі коґа, яку LXMFy викличе
    для реєстрації коґа.

**Приклад (`cogs/utility.py`):**

``` python
from lxmfy import Command
from lxmfy.commands import Cog  # Імпортуйте Cog, якщо успадковуєте його
import time

class UtilityCog: # Або class UtilityCog(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = time.time()

    @Command(name="uptime", description="Shows bot uptime")
    # Примітка: методи в коґах зазвичай приймають 'self' і 'ctx'
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
        time.sleep(7) # Імітація довготривалої операції
        ctx.reply("Long cog task completed!")

# Ця функція обов'язкова для завантаження коґа
def setup(bot):
    cog_instance = UtilityCog(bot)
    bot.add_cog(cog_instance) # Реєструє екземпляр коґа в боті
```

**Головний файл бота (`my_bot.py`):**

``` python
from lxmfy import LXMFBot

bot = LXMFBot(
    name="CogBot",
    cogs_enabled=True, # Переконайтеся, що коґи увімкнені (типово так)
    cogs_dir="cogs" # Вкажіть каталог
)

if __name__ == "__main__":
    # Коґи завантажуються автоматично під час ініціалізації LXMFBot,
    # якщо cogs_enabled дорівнює True.
    bot.run()
```

Під час запуску бот автоматично знайде `utility.py`, викличе його
функцію `setup`, яка створить екземпляр `UtilityCog` і зареєструє його
через `bot.add_cog()`. Команди, визначені в коґі (`uptime`, `info`),
стануть доступними.

## Зовнішні скриптові коґи (підтримка інших мов)

Ви також можете писати розширення бота мовами, відмінними від Python
(наприклад, Bash, Ruby, Perl, Go, C), використовуючи зовнішні скриптові
коґи.

1.  **Створіть виконуваний скрипт** у вашому каталозі `cogs`.
2.  **Додайте shebang** на початку скрипта (наприклад, `#!/bin/bash`).
3.  **Переконайтеся, що скрипт виконуваний** (`chmod +x your_script`).

Під час запуску бот автоматично зареєструє будь-який виконуваний файл у
каталозі `cogs` (який не закінчується на `.py`) як команду бота.

**Протокол аргументів:**

- `$1`: LXMF-хеш відправника.
- `$2`: повний вміст повідомлення.
- `$3`, `$4`, ...: окремі аргументи команди.

**Змінні середовища:**

- `LXMFY_SENDER`: хеш ідентифікатора відправника.
- `LXMFY_CONTENT`: повний вміст повідомлення.
- `LXMFY_HAS_ADMIN`: `true` або `false` залежно від статусу
  адміністратора відправника.

**Приклад коґа на Bash (`cogs/greet.sh`):**

``` bash
#!/bin/bash
echo "Hello from Bash! You sent: $2"
```

Коли користувач надсилає `/greet hello`, бот виконає цей скрипт і
відповість його stdout: `Hello from Bash! You sent: /greet hello`.

## Локальна класифікація інтентів (NLP)

LXMFy постачається з локальним класифікатором інтентів. Він зіставляє
текст повідомлення з позначеними прикладами фраз, коли текст не збігається
точно з префіксом команди.

1.  **Увімкніть NLP** у конфігурації бота: `nlp_enabled=True`.
2.  **Визначте інтенти** за допомогою декоратора `@bot.intent`.

``` python
@bot.intent("help", examples=["how do I use this?", "show me commands", "help me please"])
def help_intent(msg):
    msg.reply("I can help! Try typing /help to see a list of commands.")
```

Зіставлення використовує вектори TF-IDF і косинусну подібність. Усе
оцінювання виконується на хості бота. Жоден текст не надсилається до
зовнішнього API.

**Експорт та імпорт моделі**

Експортуйте й імпортуйте навчену модель, щоб більші боти не проходили
повторне навчання при кожному запуску:

``` python
# Експорт моделі
model_data = bot.nlp.export_model()
# Збережіть model_data у файл або базу даних

# Пізніше імпортуйте її назад
bot.nlp.import_model(model_data)
```

## Підтримка RNS Link

Боти можуть встановлювати прямі RNS Link і відповідати на них для
стануваного, потокового або широкосмугового трафіку, ніж дозволяють
окремі пакети LXMF.

1.  **Увімкніть підтримку Link** у конфігурації:
    `link_support_enabled=True`.
2.  **Запросіть link**: `bot.request_link(destination_hash)`. Ви також
    можете вказати власне ім'я застосунку та аспекти:
    `bot.request_link(dest, callback, "my_app", "aspect1")`.
3.  **Обробляйте вхідні link**: зареєструйте зворотний виклик через
    `bot.on_link(handler)`.

``` python
def handle_link(link):
    print(f"Link established with {RNS.hexrep(link.destination.hash)}")
    # Тепер ви можете використовувати link для прямої комунікації RNS

bot.on_link(handle_link)
```

**Безпека та ізоляція:**

- **Таймаути:** зовнішні коґи мають типовий таймаут (30 с), щоб
  запобігти зависанню. Налаштовується через `external_cogs_timeout`.
- **Потоки:** усі зовнішні коґи виконуються в окремих потоках і не
  блокують бота.
- **Пісочниця процесу бота (лише Linux):** коли `landlock_enabled=True`
  (типово) і ядро підтримує Landlock LSM (5.13+), бот після запуску
  застосовує файлову пісочницю до власного процесу. Шляхи, доступні для
  запису, обмежені сховищем, конфігурацією, коґами, конфігурацією
  Reticulum і тимчасовими каталогами. Перевизначається змінною
  середовища `LXMFY_LANDLOCK=0` для вимкнення або `LXMFY_LANDLOCK=1`,
  щоб примусово спробувати.
- **Пісочниця зовнішніх коґів (лише Linux):** коли
  `external_cogs_sandbox_enabled=True` (типово), виконувані скриптові
  коґи працюють в обмеженому середовищі. Задайте
  `external_cogs_sandbox_type` одним із:
  - `auto` (типово): надає перевагу Landlock, якщо підтримується, інакше
    `bubblewrap` (`bwrap`), інакше `firejail`
  - `landlock`: пісочниця лише на Landlock через `preexec_fn` (вужчі
    правила, ніж у пісочниці процесу бота)
  - `bwrap`: пісочниця bubblewrap з монтуванням лише для читання
  - `firejail`: приватний профіль firejail без мережі
  - `none`: без пісочниці підпроцесу
- **Статус:** викличте `bot.get_landlock_status()`, щоб перевірити
  підтримку ядра, чи було запитано Landlock, і чи активна пісочниця
  процесу бота.

## Обробка повідомлень

LXMFy надає кілька способів обробки вхідних повідомлень на різних
етапах.

### Обробник першого повідомлення

Обробляє перше повідомлення від кожного нового користувача (зручно для
привітань):

``` python
from lxmfy import LXMFBot

bot = LXMFBot(
    name="WelcomeBot",
    first_message_enabled=True  # Має бути True (типово)
)

@bot.on_first_message()
def welcome_new_user(sender, message):
    content = message.content.decode("utf-8")
    bot.send(
        sender,
        f"Welcome to the bot! You said: {content}\n\n"
        "Type /help to see available commands."
    )
    return True  # Поверніть True, щоб зупинити подальшу обробку цього повідомлення

if __name__ == "__main__":
    bot.run()
```

### Загальний обробник повідомлень

Обробляє всі вхідні повідомлення до обробки команд:

``` python
from lxmfy import LXMFBot

bot = LXMFBot(name="EchoBot")

@bot.on_message()
def echo_non_commands(sender, message):
    content = message.content.decode("utf-8").strip()

    # Перевіряємо, чи це команда - якщо так, даємо обробнику команд впоратися
    if content.startswith(bot.config.command_prefix):
        command_name = content.split()[0][len(bot.config.command_prefix):]
        if command_name in bot.commands:
            return False  # Даємо обробнику команд опрацювати її

    # Не команда, відлунюємо її назад
    bot.send(sender, f"You said: {content}")
    return False  # Поверніть False, щоб продовжити обробку (хоча жодна команда не збіжиться)

@bot.command(name="hello", description="Say hello")
def hello_command(ctx):
    ctx.reply("Hello! This is a command response.")

if __name__ == "__main__":
    bot.run()
```

Порядок обробки обробників повідомлень:

1.  **Обробник першого повідомлення** (якщо `first_message_enabled=True`
    і це перше повідомлення від відправника)
2.  **Загальні обробники повідомлень** (зареєстровані через
    `@bot.on_message()`)
3.  **Обробка команд** (якщо повідомлення збігається з зареєстрованою
    командою)

Обробники можуть повертати `True`, щоб зупинити подальшу обробку, або
`False`, щоб перейти до наступного етапу.

## Обробка подій

Ви можете реєструвати обробники для різних подій бота за допомогою
декоратора `@bot.events.on()`.

``` python
from lxmfy import LXMFBot
from lxmfy.events import EventPriority # Необов'язково, для пріоритету

bot = LXMFBot(name="EventBot")

@bot.events.on("message_received")
def log_message(event):
    # Об'єкт події містить деталі
    sender = event.data.get("sender")
    message_content = event.data.get("message").content.decode('utf-8', errors='ignore')
    print(f"Received message from {sender}: {message_content}")

    # Ви можете скасувати обробку події (наприклад, зупинити обробку повідомлення)
    # if sender == "some_blocked_hash":
    #    event.cancel()

@bot.events.on("command_executed", priority=EventPriority.LOW)
def log_command(event):
    # Приклад: event.data може містити {'command_name': 'ping', 'sender': '...', ...}
    command_name = event.data.get('command_name', 'unknown')
    sender = event.data.get('sender', 'unknown')
    print(f"Command '{command_name}' executed by {sender}")

# Ви також можете визначати власні події
@bot.command(name="special")
def special_command(ctx):
    ctx.reply("Doing something special!")
    # Надіслати власну подію
    bot.events.dispatch(Event("special_action_taken", data={"user": ctx.sender}))

@bot.events.on("special_action_taken")
def handle_special(event):
    user = event.data.get("user")
    print(f"Special action was taken by user: {user}")


if __name__ == "__main__":
    bot.run()
```

Докладніше про структуру `Event` і пріоритети див. `lxmfy/events.py`.

## Сховище

LXMFy надає бекенди сховища JSON, SQLite, MsgPack та In-Memory.

- **JSON:** простий, читабельний для людини. Підходить для невеликих
  наборів даних. Налаштовується через `storage_type="json"` і
  `storage_path="your_data_dir"`.
- **SQLite:** ефективніший для більших наборів даних або частих записів.
  Налаштовується через `storage_type="sqlite"` і
  `storage_path="your_db_file.db"`.
- **MsgPack:** компактний бінарний формат із тим самим розкладом
  файл-на-ключ, що й JSON. Налаштовується через
  `storage_type="msgpack"` і `storage_path="your_data_dir"`.
- **Memory:** сховище повністю в оперативній пам'яті. Стан втрачається
  після вимкнення. Налаштовується через `storage_type="memory"`.

Доступ до інтерфейсу сховища здійснюється через `bot.storage`:

``` python
# Зберегти дані
bot.storage.set("user_prefs:" + ctx.sender, {"theme": "dark"})

# Отримати дані (зі значенням за замовчуванням)
prefs = bot.storage.get("user_prefs:" + ctx.sender, {})
theme = prefs.get("theme", "light")

# Перевірити існування даних
if bot.storage.exists("some_key"):
    print("Key exists!")

# Видалити дані
bot.storage.delete("old_data_key")

# Сканувати ключі за префіксом (зручно для перелічення даних користувачів)
user_keys = bot.storage.scan("user_prefs:")
for key in user_keys:
    user_data = bot.storage.get(key)
    print(f"Data for {key}: {user_data}")
```

Докладніше див. `lxmfy/storage.py` і довідник API.

## Права доступу

LXMFy включає опційну рольову систему прав. Увімкніть її через
`permissions_enabled=True` під час ініціалізації `LXMFBot`.

- **Ролі:** визначайте ролі з конкретними правами (наприклад,
  `DefaultPerms.MANAGE_USERS`).
- **Права:** гранулярні прапорці, визначені в `DefaultPerms`
  (наприклад, `USE_COMMANDS`, `BYPASS_SPAM`).
- **Призначення:** призначайте ролі хешам користувачів.

Деталі використання див. у `lxmfy/permissions.py`, довіднику API та,
можливо, прикладах коґів (якщо такі створено).

## Перевірка підписів

LXMFy надає конфігурацію для вбудованого в LXMF криптографічного
підписування та перевірки повідомлень. Усі повідомлення LXMF
автоматично підписуються стеком LXMF/RNS - LXMFy лише дозволяє
застосовувати політики перевірки підписів.

**Конфігурація:**

Увімкніть перевірку підписів у конфігурації бота:

``` python
bot = LXMFBot(
    name="SecureBot",
    signature_verification_enabled=True,  # Увімкнути перевірку підписів
    require_message_signatures=False      # Встановіть True, щоб відхиляти непідписані повідомлення
)
```

**Як це працює:**

LXMF автоматично виконує всі криптографічні операції:

1.  **Вихідні повідомлення:** LXMF автоматично підписує всі повідомлення
    ідентифікатором RNS відправника під час пакування повідомлення.
2.  **Вхідні повідомлення:** LXMF автоматично перевіряє підписи за
    ідентифікатором RNS відправника і надає результати валідації.
3.  **Роль LXMFy:** LXMFy перевіряє результати валідації LXMF і
    застосовує вашу політику:
    - Якщо `signature_verification_enabled=False`: усі повідомлення
      приймаються (типово)
    - Якщо `signature_verification_enabled=True` і
      `require_message_signatures=False`: повідомлення приймаються, але
      непідписані/невалідні підписи записуються в журнал
    - Якщо `signature_verification_enabled=True` і
      `require_message_signatures=True`: непідписані або невалідні
      повідомлення відхиляються
4.  **Інтеграція з правами:** користувачі з правом `BYPASS_SPAM` можуть
    обходити вимоги перевірки підписів.

**Керування через CLI:**

Ви можете керувати налаштуваннями перевірки підписів через CLI:

``` bash
# Перевірити перевірку підписів
lxmfy signatures test

# Увімкнути перевірку підписів
lxmfy signatures enable

# Вимкнути перевірку підписів
lxmfy signatures disable
```

**Технічні деталі:**

LXMF використовує підписи Ed25519, які надає криптографічна система RNS.
Кожне повідомлення LXMF містить підпис відправника, який перевіряється
за його відомим ідентифікатором RNS. LXMFy просто читає властивість LXMF
`message.signature_validated` і `message.unverified_reason`, щоб
застосовувати політику безпеки вашого бота.

## Доставка повідомлень

### Використання вузлів поширення

Надсилайте повідомлення через конкретні вузли поширення LXMF:

``` python
from lxmfy import LXMFBot

bot = LXMFBot(name="PropagationBot")

@bot.command(name="send", description="Send via propagation node")
def send_command(ctx):
    # Задайте конкретний вузол поширення один раз (на рівні конфігурації)
    bot.set_propagation_node("<propagation_node_hash_here>")

    # Надсилання з налаштованою стратегією доставки
    bot.send(
        ctx.sender,
        "This message will use direct delivery with propagation fallback as configured"
    )
```

Використовуйте вузол поширення, коли отримувач офлайн або пряма
доставка постійно не вдається на поточному шляху.

### Налаштування повторних спроб

Налаштуйте автоматичні повторні спроби для невдалих доставок
повідомлень через конфігурацію бота:

``` python
from lxmfy import LXMFBot

bot = LXMFBot(name="ReliableBot")

bot = LXMFBot(
    name="ReliableBot",
    direct_delivery_retries=5,  # Повторювати пряму доставку до 5 разів
    propagation_fallback_enabled=True
)

@bot.command(name="important", description="Send important message with retries")
def important_command(ctx):
    bot.send(ctx.sender, "This is an important message")

@bot.command(name="normal", description="Send with default retries")
def normal_command(ctx):
    # direct_delivery_retries типово дорівнює 3
    bot.send(ctx.sender, "This message uses default retry settings")
```

Система повторних спроб:

- Автоматично відстежує спроби доставки для кожного отримувача
- Повторює невдалі прямі доставки до `direct_delivery_retries` разів
- Скидає лічильник повторів після успішної доставки
- Записує спроби повторів і невдачі в журнал для налагодження

### Відкладені відправлення та stamp-и

Дві деталі доставки, які варто знати заздалегідь:

- **Відкладені відправлення**: коли ідентичність адресата ще
  невідома, `send()` тримає повідомлення у сховищі (ключі конфігурації
  `pending_sends_*` керують відставанням) і виштовхує його, коли пір
  анонсується. Передайте `defer=False` у відправлення, щоб відкинути
  замість утримання.
- **Stamp-и**: `stamp_cost` встановлює вимогу proof-of-work на вхід,
  `require_stamps` відхиляє повідомлення, що її не виконують, а
  `include_tickets` (типово) додає ticket-и відповіді, щоб піри могли
  відповісти вашому ботові без оплати власної вартості stamp.

Коли доставка працює погано, `lxmfy debug` проходить увесь шлях
(конфігурація, екземпляр, інтерфейси, ідентичність, pipeline
відправлення) і пише редагований звіт, яким можна поділитися. Ті самі
перевірки доступні як `bot.diagnose_connectivity()` і
`bot.diagnose_destination(hash)`.

Дивіться [Довідник API](api-reference.md) для
всієї поверхні доставки: повтори, вузли поширення, персистентність
черги, потік подій доставки та адміністративні команди `/queue`,
`/cancel`, `/inbox`, `/delivery`.

## Reticulum Relay Chat (RRC)

Боти LXMFy можуть приєднуватися до хабів [RRC](https://rrc.kc1awv.net/)
як звичайні клієнти через RNS Link з конвертами CBOR. Це сумісно з
NomadNet і хабами у стилі rrcd (включно з MeshChatX, коли він хостить
той самий хаб або приєднується до нього).

### Конфігурація Reticulum має значення

Бот повинен використовувати **ту саму** мережу Reticulum, що й хаб.
MeshChatX зазвичай використовує `~/.reticulum` з інтерфейсами backbone
або TCP. Локальний каталог `config/` проєкту часто використовує
ізольоване ім'я екземпляра і лише AutoInterface, тому анонси хаба
ніколи не надходять, і ви бачите `Hub identity unknown`.

Використайте один із варіантів:

- Задайте `reticulum_config_dir` на вашу конфігурацію користувача
  (зазвичай `~/.reticulum`)
- Або експортуйте `LXMFY_RETICULUM_CONFIG_DIR=~/.reticulum`
- Тримайте MeshChatX або `rnsd` запущеними, щоб спільний екземпляр був
  активний до запуску бота

Шаблон `rrc` типово використовує `~/.reticulum`, якщо цей каталог
існує.

### Швидкий старт із шаблоном

``` bash
lxmfy run rrc
```

Типові значення:

- Хаб: `664fc0e8d2e448658e37bb3f34e6c88f`
- Кімната: `#general`
- Конфігурація Reticulum: `~/.reticulum` (або
  `LXMFY_RETICULUM_CONFIG_DIR`)

Ви маєте побачити журнали підключення до хаба, welcome, автоматичного
приєднання і `RRC joined #general`.

### Програмний RRC-бот

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

Або підключіться під час виконання:

``` python
bot.connect_rrc("hub_destination_hash", rooms=["general"])
bot.rrc.send_message("general", "hello room")
bot.rrc.send_action("general", "waves")
bot.disconnect_rrc()
```

### Поведінка сесії

- HELLO / WELCOME, JOIN / PART, MSG / NOTICE / ACTION, PING / PONG,
  ERROR, RESOURCE_ENVELOPE
- Автоматичне перепідключення з повторним приєднанням до кімнат після
  WELCOME
- Клієнтське застосування ліміту хаба та обмеження частоти
- Персистентність сесій між перезапусками (`rrc_persist_sessions`,
  типово увімкнено)
- Персистентність вихідної черги LXMF окрема
  (`message_persistence_enabled`)
