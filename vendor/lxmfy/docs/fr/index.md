# LXMFy

Framework Python pour créer des bots [LXMF](https://github.com/Quad4-Software/LXMF) sur le [réseau Reticulum](https://reticulum.network/).

```python
from lxmfy import LXMFBot

bot = LXMFBot(name="MyBot")

@bot.command(name="ping", description="Répond avec pong")
def ping(ctx):
    ctx.reply("Pong!")

bot.run()
```

## Guides

- [Démarrage rapide](quick-start.md) - installez LXMFy et mettez un bot sur le réseau en quelques minutes
- [Création de bots](creating-bots.md) - commandes, cogs, stockage, permissions, RRC et livraison
- [Référence API](api-reference.md) - options de configuration, méthodes et documentation des modules

## Inclus

- Registre de commandes avec arguments annotés, génération d'aide et restriction admin
- Cogs en Python ou dans tout langage exécutable
- Commandes par champs LXMF, réactions, threading des réponses, pièces jointes et apparence d'icône
- Conversations (msg.ask), harness de test sans réseau et débogueur de connectivité
- Livraison via nœud de propagation avec réessais, envois différés et persistance de la file
- Intentions NLP optionnelles, permissions, signatures, sandbox Landlock
- Client de salons RRC compatible avec les hubs NomadNet et MeshChatX

## Téléchargement

Les bundles PDF, EPUB et texte sont attachés aux [releases GitHub](https://github.com/Quad4-Software/LXMFy/releases).

## Langues

- [English](../index.md)
- [Deutsch](../de/index.md)
- [Español](../es/index.md)
- [Français](index.md)
- [Português](../pt/index.md)
- [Українська](../uk/index.md)
- [Русский](../ru/index.md)
- [简体中文](../zh/index.md)
