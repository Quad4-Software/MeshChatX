# Швидкий старт

## Вимоги

- Python 3.11+
- Reticulum Network Stack (`pip install rns`, версія 1.5.4+)
- LXMF (`pip install lxmf`, версія 1.1.1+; встановлюється автоматично разом із
  LXMFy)
- CBOR (`cborx`, встановлюється автоматично, потрібен для RRC)

=== "PyPI"

    ``` bash
    pip install lxmfy
    ```

=== "З вихідного коду"

    ``` bash
    git clone https://github.com/Quad4-Software/LXMFy
    cd LXMFy
    poetry install
    ```

## Створення першого бота (через CLI)

Використовуйте CLI LXMFy для створення каркаса проєкту. Два
способи:

- `lxmfy init` ставить кілька питань (назва, шаблон, сховище, префікс,
  адміни) і записує готову до запуску теку проєкту.
- `lxmfy create` записує один файл бота з типовими значеннями, без
  питань.

Цей посібник використовує `lxmfy create`.

1.  **Відкрийте термінал** у каталозі, де ви хочете створити проєкт
    бота.

2.  **Виконайте команду створення:**

    ``` bash
    lxmfy create my_first_bot
    ```

    Ця команда згенерує такі файли:

    - `my_first_bot.py`: основний файл бота з розумними типовими
      налаштуваннями.
    - `cogs/`: каталог для розширень бота (коґів).
    - `cogs/__init__.py`: робить каталог `cogs` пакетом Python.
    - `cogs/basic.py`: приклад коґа з простими командами "hello" і
      "about".
    - `data/`: каталог, де бот зберігатиме свої дані (типово у форматі
      JSON).
    - `config/`: каталог, де бот зберігає свій ідентифікатор і статус
      анонсів.

3.  **Перегляньте файл `my_first_bot.py`:**

    ``` python
    from lxmfy import LXMFBot

    bot = LXMFBot(
        name="my_first_bot",  # Ім'я бота, використовується в анонсах та ідентифікаторі
        announce=600,         # Інтервал анонсів у секундах (10 хвилин)
        announce_immediately=True, # Анонсувати при першому запуску?
        admins=set(),         # Множина хешів LXMF-адрес адміністраторів
        hot_reloading=False,  # Увімкнути/вимкнути гаряче перезавантаження коґів
        rate_limit=5,         # Максимум повідомлень за хвилину від користувача
        cooldown=60,          # Період очікування в секундах для обмеження частоти
        max_warnings=3,       # Попереджень до бану за спам
        warning_timeout=300,  # Час (секунди) до скидання попереджень
        command_prefix="/",   # Префікс команд (наприклад, /hello)
        cogs_dir="cogs",      # Каталог для завантаження коґів
        cogs_enabled=True,    # Увімкнути/вимкнути завантаження коґів
        permissions_enabled=False, # Увімкнути/вимкнути рольову систему прав
        storage_type="json",  # Бекенд сховища ("json", "sqlite", "msgpack" або "memory")
        storage_path="data",  # Шлях до файлів сховища/бази даних
        first_message_enabled=True, # Спеціальна обробка перших повідомлень
        event_logging_enabled=True, # Записувати події у сховище?
        max_logged_events=1000,   # Максимум подій у журналі
        event_middleware_enabled=True, # Увімкнути middleware подій?
        announce_enabled=True,   # Увімкнути/вимкнути мережеві анонси
        signature_verification_enabled=False, # Увімкнути/вимкнути криптографічну перевірку підписів
        require_message_signatures=False     # Вимагати підписи у всіх повідомлень
    )

    # Щоб додати адміністратора, знайдіть свій хеш LXMF-адреси і додайте його сюди:
    # bot.config.admins.add("your_lxmf_hash_here")
    # bot.admins = bot.config.admins # Щоб запущений екземпляр знав про це

    # Приклад підготовки поля іконки LXMF (необов'язково)
    # from lxmfy import IconAppearance, pack_icon_appearance_field
    # try:
    #     icon_data = IconAppearance(icon_name="emoji_objects", fg_color=b'\xFF\xA5\x00', bg_color=b'\x8B\x45\x13') # Помаранчева на коричневому
    #     bot.icon_field = pack_icon_appearance_field(icon_data) # Зберегти для send/reply
    # except Exception as e:
    #     print(f"Не вдалося підготувати поле іконки: {e}")
    #     bot.icon_field = None

    if __name__ == "__main__":
        print(f"Starting bot: {bot.config.name}")
        print(f"Bot LXMF Address: {bot.local.hash}") # Виводить адресу бота
        bot.run()
    ```

4.  **(Необов'язково) Додайте свій хеш адміністратора:**

    - Знайдіть свій хеш LXMF-адреси (наприклад, у клієнті Reticulum,
      такому як Sideband або NomadNet).
    - Розкоментуйте й відредагуйте рядок `bot.config.admins.add(...)` у
      `my_first_bot.py`, замінивши `"your_lxmf_hash_here"` на свій
      справжній хеш.

5.  **Запустіть бота:**

    ``` bash
    python my_first_bot.py
    ```

    Бот запуститься, виведе свою LXMF-адресу, може надіслати анонс у
    мережу Reticulum і почне приймати повідомлення.

## Взаємодія з ботом

1.  **Надішліть повідомлення** на LXMF-адресу бота зі свого клієнта.
2.  **Спробуйте приклад команди:** надішліть боту `/hello`. Він має
    відповісти "Hello `<your_hash>`!". Якщо ви розкоментували приклад з
    іконкою вище, відповідь може також містити іконку.
3.  **Спробуйте команду довідки:** надішліть `/help`.

Якщо нічого не приходить, запустіть `lxmfy debug` у теці проєкту. Він
перевіряє конфігурацію Reticulum, інтерфейси, ідентичність і pipeline
відправлення та зберігає редагований звіт, яким можна поділитися,
просячи допомоги.

## Що налаштувати далі

**Обробники повідомлень**

- `@bot.on_first_message()` для першого повідомлення від кожного
  відправника
- `@bot.on_message()` для всіх повідомлень до обробки команд

**Доставка**

- `direct_delivery_retries` у `LXMFBot(...)` повторює пряму доставку
  перед переходом на propagation
- `propagation_node` (або `bot.set_propagation_node(...)`) вибирає
  конкретний вузол поширення LXMF
- Персистентність вихідної черги увімкнена типово
  (`message_persistence_enabled=True`) з обмеженою чергою
  (`message_queue_size`)

**Reticulum Relay Chat (RRC)**

- Підключайтеся до хабів з `rrc_enabled=True` або шаблоном `rrc`
- Використовуйте ту саму конфігурацію Reticulum, що в MeshChatX або
  вашого хаба (`reticulum_config_dir` або `LXMFY_RETICULUM_CONFIG_DIR`,
  зазвичай `~/.reticulum`)
- Див. [Створення ботів](creating-bots.md#reticulum-relay-chat-rrc) про
  ботів для кімнат і виявлення хабів

**Безпека**

- `signature_verification_enabled=True` перевіряє результати валідації
  підписів LXMF
- `require_message_signatures=True` відхиляє непідписані або невалідні
  повідомлення
- У Linux `landlock_enabled=True` (типово) застосовує файлову пісочницю
  Landlock LSM. Перевизначається через `LXMFY_LANDLOCK=0` або
  `LXMFY_LANDLOCK=1`
- Зовнішні скриптові коґи можуть використовувати Landlock, bubblewrap
  або firejail через `external_cogs_sandbox_type`
- LXMF підписує вихідні повідомлення. LXMFy забезпечує політику
  перевірки та опційну ізоляцію

**Розробка**

- `make typecheck` запускає `pyright lxmfy`
- `make ci` запускає лінт, перевірку типів, перевірку безпеки, тести та
  збірку

Див. [Створення ботів](creating-bots.md) і [Довідник
API](api-reference.md) про реєстрацію команд, коґи та деталі API.
