# LXMFy

Python-Framework für [LXMF](https://github.com/Quad4-Software/LXMF)-Bots im [Reticulum-Netzwerk](https://reticulum.network/).

```python
from lxmfy import LXMFBot

bot = LXMFBot(name="MyBot")

@bot.command(name="ping", description="Antwortet mit pong")
def ping(ctx):
    ctx.reply("Pong!")

bot.run()
```

## Anleitungen

- [Schnellstart](quick-start.md) - LXMFy installieren und in wenigen Minuten einen Bot im Netzwerk betreiben
- [Bots erstellen](creating-bots.md) - Befehle, Cogs, Speicher, Berechtigungen, RRC und Zustellung
- [API-Referenz](api-reference.md) - Konfigurationsoptionen, Methoden und Moduldokumentation

## Enthalten

- Befehlsregistrierung mit typannotierten Argumenten, Hilfegenerierung und Admin-Beschränkung
- Cogs in Python oder jeder ausführbaren Sprache
- LXMF-Feldbefehle, Reaktionen, Antwort-Threading, Anhänge und Icon-Darstellung
- Konversationen (msg.ask), netzwerkfreier Test-Harness und Konnektivitäts-Debugger
- Zustellung über Propagationsknoten mit Wiederholungen, zurückgestellten Sends und persistenter Warteschlange
- Optionale NLP-Intents, Berechtigungen, Signaturen, Landlock-Sandboxing
- RRC-Raum-Client, kompatibel mit NomadNet- und MeshChatX-Hubs

## Download

PDF-, EPUB- und Text-Bundles sind an die [GitHub-Releases](https://github.com/Quad4-Software/LXMFy/releases) angehängt.

## Sprachen

- [English](../index.md)
- [Deutsch](index.md)
- [Español](../es/index.md)
- [Français](../fr/index.md)
- [Português](../pt/index.md)
- [Українська](../uk/index.md)
- [Русский](../ru/index.md)
- [简体中文](../zh/index.md)
