# LXMFy

Python framework for building [LXMF](https://github.com/Quad4-Software/LXMF) bots on the [Reticulum Network](https://reticulum.network/).

```python
from lxmfy import LXMFBot

bot = LXMFBot(name="MyBot")

@bot.command(name="ping", description="Responds with pong")
def ping(ctx):
    ctx.reply("Pong!")

bot.run()
```

## Guides

- [Quick Start](quick-start.md) - install LXMFy and get a bot on the network in minutes
- [Creating Bots](creating-bots.md) - commands, cogs, storage, permissions, RRC, and delivery
- [API Reference](api-reference.md) - configuration options, methods, and module docs

## Included

- Command registry with type-hinted arguments, help generation, and admin gating
- Cogs in Python or any executable language
- LXMF field commands, reactions, reply threading, attachments, and icon appearance
- Conversations (msg.ask), a no-network test harness, and a connectivity debugger
- Propagation node delivery with retries, deferred sends, and queue persistence
- Optional NLP intents, permissions, signatures, Landlock sandboxing
- RRC room client compatible with NomadNet and MeshChatX hubs

## Download

PDF, EPUB, and text bundles are attached to [GitHub releases](https://github.com/Quad4-Software/LXMFy/releases).

## Languages

- [English](index.md)
- [Deutsch](de/index.md)
- [Español](es/index.md)
- [Français](fr/index.md)
- [Português](pt/index.md)
- [Українська](uk/index.md)
- [Русский](ru/index.md)
- [简体中文](zh/index.md)
