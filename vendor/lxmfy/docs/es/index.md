# LXMFy

Framework de Python para crear bots de [LXMF](https://github.com/Quad4-Software/LXMF) en la [red Reticulum](https://reticulum.network/).

```python
from lxmfy import LXMFBot

bot = LXMFBot(name="MyBot")

@bot.command(name="ping", description="Responds with pong")
def ping(ctx):
    ctx.reply("Pong!")

bot.run()
```

## Guías

- [Inicio rápido](quick-start.md) - instala LXMFy y pon un bot en la red en minutos
- [Creación de bots](creating-bots.md) - comandos, cogs, almacenamiento, permisos, RRC y entrega
- [Referencia de API](api-reference.md) - opciones de configuración, métodos y documentación de los módulos

## Incluido

- Registro de comandos con argumentos tipados, generación de ayuda y restricción a administradores
- Cogs en Python o en cualquier lenguaje ejecutable
- Comandos por campos LXMF, reacciones, threading de respuestas, adjuntos e icono de apariencia
- Conversaciones (msg.ask), harness de tests sin red y depurador de conectividad
- Entrega mediante nodo de propagación con reintentos, envíos diferidos y cola persistente
- Intents NLP opcionales, permisos, firmas y sandbox Landlock
- Cliente de salas RRC compatible con hubs de NomadNet y MeshChatX

## Descarga

Los paquetes en PDF, EPUB y texto están adjuntos a los [releases de GitHub](https://github.com/Quad4-Software/LXMFy/releases).

## Idiomas

- [English](../index.md)
- [Deutsch](../de/index.md)
- [Español](index.md)
- [Français](../fr/index.md)
- [Português](../pt/index.md)
- [Українська](../uk/index.md)
- [Русский](../ru/index.md)
- [简体中文](../zh/index.md)
