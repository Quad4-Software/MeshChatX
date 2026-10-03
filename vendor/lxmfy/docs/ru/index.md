# LXMFy

Python-фреймворк для ботов [LXMF](https://github.com/Quad4-Software/LXMF) в сети [Reticulum](https://reticulum.network/).

```python
from lxmfy import LXMFBot

bot = LXMFBot(name="MyBot")

@bot.command(name="ping", description="Отвечает pong")
def ping(ctx):
    ctx.reply("Pong!")

bot.run()
```

## Руководства

- [Быстрый старт](quick-start.md) - установите LXMFy и запустите бота в сети за минуты
- [Создание ботов](creating-bots.md) - команды, коги, хранилище, права, RRC и доставка
- [Справочник API](api-reference.md) - параметры конфигурации, методы и документация модулей

## Возможности

- Реестр команд с типизированными аргументами, генерацией помощи и админским доступом
- Коги на Python или любом исполняемом языке
- Полевые команды LXMF, реакции, трединг ответов, вложения и иконки
- Разговоры (msg.ask), тестовый стенд без сети и отладчик соединения
- Доставка через узел распространения с повторами, отложенными отправками и персистентной очередью
- Опциональные NLP-интенты, права, подписи, изоляция Landlock
- Клиент комнат RRC, совместимый с хабами NomadNet и MeshChatX

## Скачивание

Сборки в PDF, EPUB и текстовом формате прикреплены к [релизам на GitHub](https://github.com/Quad4-Software/LXMFy/releases).

## Языки

- [English](../index.md)
- [Deutsch](../de/index.md)
- [Español](../es/index.md)
- [Français](../fr/index.md)
- [Português](../pt/index.md)
- [Українська](../uk/index.md)
- [Русский](index.md)
- [简体中文](../zh/index.md)
