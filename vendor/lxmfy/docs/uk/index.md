# LXMFy

Python-фреймворк для створення ботів [LXMF](https://github.com/Quad4-Software/LXMF) у мережі [Reticulum](https://reticulum.network/).

```python
from lxmfy import LXMFBot

bot = LXMFBot(name="MyBot")

@bot.command(name="ping", description="Відповідає pong")
def ping(ctx):
    ctx.reply("Pong!")

bot.run()
```

## Посібники

- [Швидкий старт](quick-start.md) - встановіть LXMFy і запустіть бота в мережі за лічені хвилини
- [Створення ботів](creating-bots.md) - команди, коґи, сховище, права, RRC і доставка
- [Довідник API](api-reference.md) - параметри конфігурації, методи й документація модулів

## Можливості

- Реєстр команд із типізованими аргументами, генерацією довідки та адміністративним доступом
- Коґи на Python або будь-якою виконуваною мовою
- Польові команди LXMF, реакції, тредування відповідей, вкладення й іконки
- Розмови (msg.ask), тестовий стенд без мережі та дебагер з'єднання
- Доставка через вузол поширення з повторами, відкладеними відправленнями та персистентною чергою
- Опційні NLP-інтенти, права, підписи, ізоляція Landlock
- Клієнт кімнат RRC, сумісний із хабами NomadNet і MeshChatX

## Завантаження

Збірки у форматах PDF, EPUB і текстовому прикріплені до [релізів на GitHub](https://github.com/Quad4-Software/LXMFy/releases).

## Мови

- [English](../index.md)
- [Deutsch](../de/index.md)
- [Español](../es/index.md)
- [Français](../fr/index.md)
- [Português](../pt/index.md)
- [Українська](index.md)
- [Русский](../ru/index.md)
- [简体中文](../zh/index.md)
