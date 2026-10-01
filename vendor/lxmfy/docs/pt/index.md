# LXMFy

Framework Python para criar bots [LXMF](https://github.com/Quad4-Software/LXMF) na [rede Reticulum](https://reticulum.network/).

```python
from lxmfy import LXMFBot

bot = LXMFBot(name="MyBot")

@bot.command(name="ping", description="Responde com pong")
def ping(ctx):
    ctx.reply("Pong!")

bot.run()
```

## Guias

- [Início rápido](quick-start.md) - instale o LXMFy e ponha um bot na rede em minutos
- [Criar bots](creating-bots.md) - comandos, cogs, armazenamento, permissões, RRC e entrega
- [Referência da API](api-reference.md) - opções de configuração, métodos e documentação dos módulos

## Incluído

- Registo de comandos com argumentos anotados por tipo, geração de ajuda e restrição a administradores
- Cogs em Python ou em qualquer linguagem executável
- Comandos em campos LXMF, reações, threading de respostas, anexos e aparência de ícone
- Conversações (msg.ask), harness de teste sem rede e depurador de conectividade
- Entrega por nó de propagação com repetições, envios diferidos e persistência da fila
- Intents NLP opcionais, permissões, assinaturas, sandboxing com Landlock
- Cliente de salas RRC compatível com hubs NomadNet e MeshChatX

## Transferências

Os pacotes em PDF, EPUB e texto estão anexados às [releases do GitHub](https://github.com/Quad4-Software/LXMFy/releases).

## Idiomas

- [English](../index.md)
- [Deutsch](../de/index.md)
- [Español](../es/index.md)
- [Français](../fr/index.md)
- [Português](index.md)
- [Українська](../uk/index.md)
- [Русский](../ru/index.md)
- [简体中文](../zh/index.md)
