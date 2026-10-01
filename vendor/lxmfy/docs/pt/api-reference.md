# Componentes principais

## LXMFBot

A classe principal do bot, que trata do encaminhamento de mensagens, do
processamento de comandos e da gestão do ciclo de vida do bot.

``` python
from lxmfy import LXMFBot

bot = LXMFBot(
    name="MyBot",
    command_prefix="/",
    admins=set(),
    config_path=None,                 # "config" por padrão no diretório de trabalho
    reticulum_config_dir=None,        # ou LXMFY_RETICULUM_CONFIG_DIR / "~/.reticulum"
    test_mode=False,                  # salta a inicialização do RNS, para testes
    log_level="INFO",                 # nível do logger do lxmfy, None não toca no logging
    loglevel=None,                    # nível de log do RNS 0-7, None usa a config do reticulum

    # Announces
    announce=600,
    announce_immediately=True,
    announce_enabled=True,
    announce_display_name_file=None,  # arquivo sob config_path que sobrescreve o nome
                                      # anunciado (arquivo padrão:
                                      # bot_display_name.txt)

    # Proteção anti-spam
    rate_limit=5,
    cooldown=60,
    max_warnings=3,
    warning_timeout=300,

    # Cogs
    cogs_dir="cogs",
    cogs_enabled=True,
    dynamic_cogs_enabled=True,
    external_cogs_enabled=True,
    external_cogs_sandbox_enabled=True,
    external_cogs_sandbox_type="auto",  # "auto", "landlock", "bwrap", "firejail", "none"
    external_cogs_timeout=30,
    hot_reloading=False,

    # Armazenamento, eventos, permissões
    storage_type="json",              # "json", "sqlite", "msgpack" ou "memory"
    storage_path="data",
    permissions_enabled=False,
    first_message_enabled=True,
    event_logging_enabled=True,
    max_logged_events=1000,
    event_middleware_enabled=True,

    # Segurança
    signature_verification_enabled=False,
    require_message_signatures=False,
    require_stamps=False,             # rejeita mensagens com stamps inválidos
    request_unknown_identities=False, # pede identidades de remetente à rede
    stamp_cost=None,                  # custo de stamp de entrada, None desativa
    include_tickets=True,             # anexa tickets de resposta às saídas
    identity_pinning_enabled=False,
    landlock_enabled=True,

    # Funcionalidades opcionais
    nlp_enabled=False,
    nlp_threshold=0.5,
    link_support_enabled=False,
    lxmf_commands_enabled=True,

    # Entrega
    message_persistence_enabled=True,
    message_queue_size=50,
    opportunistic_sending=True,
    direct_delivery_retries=3,
    propagation_fallback_enabled=True,
    propagation_node=None,            # hash do nó de propagação de saída
    autopeer_propagation=False,       # descobre nós de propagação por announces
    autopeer_maxdepth=4,              # profundidade máxima de hops, None = sem limite
    enable_propagation_node=False,    # executa este bot como nó de propagação
    message_storage_limit_mb=500,     # limite de armazenamento do nó, só modo nó

    # Envios diferidos
    pending_sends_enabled=True,       # retém envios para destinos desconhecidos
    pending_sends_max=200,
    pending_sends_ttl=604800,         # 7 dias
    pending_sends_retry=300,          # segundos entre varreduras de retry

    # RRC
    rrc_enabled=False,
    rrc_hubs=[],
    rrc_rooms=[],
    rrc_nick=None,
    rrc_dest_name="rrc.hub",
    rrc_auto_reconnect=True,
    rrc_persist_sessions=True,
)
```

Todas estas opções são campos de `BotConfig`. `LXMFBot(**kwargs)`
encaminha cada argumento nomeado, por isso `bot.config` contém os
valores resolvidos.

### Métodos principais

- `run(delay=10)`: Inicia o loop principal do bot
- `cleanup()`: Persiste as filas, cancela conversações e desliga o
  agendador, o router e o RNS. Chamado automaticamente ao sair de
  `run()`.
- `send(destination, message, title="Reply", lxmf_fields=None, stamp_cost=None, opportunistic=None, method=None, include_ticket=None, defer=None, reply_to=None, quote=None, thread=None)`:
  Envia uma mensagem para um destino. `stamp_cost` sobrescreve o custo
  de saída desta mensagem, `opportunistic` sobrescreve
  `opportunistic_sending`, `include_ticket` sobrescreve
  `include_tickets` e `defer` sobrescreve `pending_sends_enabled`.
  `reply_to`, `quote` e `thread` definem os campos de threading de
  resposta.
- `send_with_attachment(destination, message, attachment, title="Reply", stamp_cost=None, opportunistic=None)`:
  Envia uma mensagem com anexo
- `command(name, description="No description provided", admin_only=False, permissions=None, usage=None, examples=None, category=None, aliases=None, threaded=False, rate_limit=None)`:
  Decorador para registar comandos. `permissions` sobrescreve a
  barreira `DefaultPerms` (`ALL` com `admin_only`, senão
  `USE_COMMANDS`), `threaded` executa o callback numa thread de
  trabalho, `rate_limit` limita invocações por remetente e janela de
  cooldown, e `usage`, `examples`, `category`, `aliases` alimentam o
  sistema de ajuda. Os comandos suportam argumentos anotados por tipo
  para conversão automática.
- `intent(name, examples)`: Decorador para registar manipuladores de
  intents NLP.
- `nlp.export_model()`: Exporta os dados do modelo NLP treinado.
- `nlp.import_model(model_data)`: Importa dados de modelo NLP
  exportados anteriormente.
- `request_link(destination_hash, callback=None, app_name="lxmf", *aspects)`:
  Pede um link RNS para um destino. Permite `app_name` e `aspects`
  próprios ("lxmf" e "delivery" por padrão).
- `on_link(callback)`: Regista um manipulador para links RNS de
  entrada.
- `load_extension(name)`: Carrega um módulo de extensão cog pelo nome
  (ex. "cogs.utility").
- `reload_extension(name)`: Recarrega um módulo de extensão cog.
- `add_cog(cog_instance)`: Adiciona uma instância de classe cog ao bot.
- `remove_cog(cog_name)`: Remove um cog pelo nome da classe.
- `on_first_message()`: Decorador para tratar as primeiras mensagens
  dos utilizadores
- `on_message()`: Decorador para tratar todas as mensagens (chamado
  antes do processamento de comandos)
- `received(function)`: Regista um callback invocado com o contexto da
  mensagem para cada mensagem de entrada que atravessou a pipeline sem
  ser consumida por um comando ou intent
- `on_reaction()`: Decorador para tratar reações de entrada. Os
  manipuladores recebem `(sender, reaction)`, onde reaction leva as
  chaves `reaction_to`, `reaction_emoji` e `reaction_sender`
- `react(destination, message_hash, reaction)`: Envia uma reação a uma
  mensagem via o campo LXMF `FIELD_REACTION`
- `validate()`: Executa verificações de validação na configuração do
  bot
- `get_landlock_status()`: Devolve a disponibilidade e o estado de
  ativação da sandbox Landlock LSM do processo do bot
- `diagnose_destination(destination, request_path=False, wait=0.0)`:
  Sonda o estado de identidade e rota de um hash de destino
- `diagnose_connectivity(destination=None, request_path=False, wait=0.0)`:
  Executa o relatório doctor completo e devolve-o como dict
- `get_debugger()`: Devolve um `Debugger` ligado a este bot
- `set_propagation_node(node_hash)`: Fixa o nó de propagação de saída
- `get_propagation_node_status()`: Estado dos nós de propagação de
  saída configurados, descobertos e atualmente em uso
- `set_message_storage_limit(megabytes)`: Limite de armazenamento ao
  operar como nó de propagação
- `get_propagation_storage_stats()`: Uso de armazenamento do nó, ou um
  dict a explicar por que não está disponível
- `connect_rrc(hub_hash, rooms=None, nick=None, dest_name=None, auto_reconnect=None)`:
  Liga a um hub RRC como cliente
- `disconnect_rrc(hub_hash=None)`: Desliga uma ou todas as sessões de
  hub RRC
- `on_rrc(callback=None)`: Decorador ou registo de manipulador para
  eventos RRC (`handler(event, client, payload)`)
- `on_delivery_event(callback=None)`: Subscreve o fluxo de eventos de
  entrega de saída, como decorador ou chamada direta

### Atributos

- `config`: A `BotConfig` resolvida
- `commands`, `cogs`: Registos de comandos e cogs
- `storage`: O backend de armazenamento ativo
- `scheduler`: `TaskScheduler` para tarefas tipo cron
- `events`: `EventManager` para manipuladores de eventos e dispatch
- `middleware`: `MiddlewareManager` para middleware de comandos
- `permissions`: `PermissionManager` para papéis e flags
- `spam_protection`: `SpamProtection` para limites de taxa, avisos e
  banimentos
- `signature_manager`: Camada de política de assinaturas
- `nlp`: O classificador de intents (só corresponde com `nlp_enabled`)
- `delivery`: `DeliveryTracker`, o fluxo de eventos de saída
- `conversations`: `ConversationManager` para perguntas `msg.ask`
- `rrc`: `RRCManager` para sessões multi-hub, `None` até o RRC ser
  ativado ou `connect_rrc()` correr
- `local`: A `RNS.Destination` do bot (o seu endereço LXMF é
  `bot.local.hash`)

## Nome anunciado

O nome que os peers veem vem de `name`, mas existem duas
sobrescrituras para announces. Se `announce_display_name_file` estiver
definido e esse ficheiro existir sob `config_path`, o seu conteúdo
vence. Caso contrário, `bot_display_name.txt` sob `config_path` é lido
quando presente. Em qualquer caso, atribuir `bot.name = "Novo nome"`
ressincroniza o nome anunciado em tempo de execução.

Isto permite aos operadores renomear um bot sem tocar no código, e o
nome anunciado pode diferir do nome interno da configuração.

## Comandos estruturados via campos LXMF

Os bots podem receber comandos enviados via `FIELD_COMMANDS` (`0x09`)
do LXMF e responder automaticamente com `FIELD_RESULTS` (`0x0A`). Isto
permite fluxos estruturados de pedido/resposta em paralelo com os
comandos de texto normais.

Os `FIELD_COMMANDS` recebidos são analisados e encaminhados pelo mesmo
registo de comandos dos comandos de texto, partilhando verificações de
permissões, parsing de argumentos anotados por tipo, threading e
middleware.

``` python
from lxmfy import LXMFBot, FIELD_COMMANDS, FIELD_RESULTS, pack_result, unpack_commands

bot = LXMFBot(name="FieldBot")

@bot.command(name="status", description="Return bot status")
def status_cmd(ctx):
    # ctx.fields contém o dicionário de campos LXMF em bruto
    # ctx.request_id é definido automaticamente se o comando incluir um
    ctx.reply("Bot is online")

# Enviar um comando estruturado a partir de outro cliente LXMF:
# lxm.fields[FIELD_COMMANDS] = {"command": "status", "args": [], "request_id": "abc123"}
# router.handle_outbound(lxm)

# A resposta do bot inclui automaticamente FIELD_RESULTS com a resposta e o request_id.
```

Para desativar o processamento de comandos por campos, defina
`lxmf_commands_enabled=False` no `BotConfig`.

## Reações

As reações viajam no campo LXMF `FIELD_REACTION` (`0x40`) de uma
mensagem por outro lado vazia. `pack_reaction` e `unpack_reaction`
constroem e analisam esse campo.

``` python
from lxmfy import pack_reaction, unpack_reaction

# Enviar uma reação a uma mensagem
bot.react(destination_hash, message_hash_hex, "thumbs up emoji")

# Receber reações
@bot.on_reaction()
def on_reaction(sender, reaction):
    # reaction["reaction_to"]  - hash hex da mensagem alvo
    # reaction["reaction_emoji"] - texto da reação (até 16 caracteres)
    # reaction["reaction_sender"] - remetente
    print(f"{sender} reacted {reaction['reaction_emoji']} to {reaction['reaction_to']}")
    return True
```

O texto da reação está limitado a 16 caracteres imprimíveis. O campo em
bruto continua disponível em `ctx.fields` e `msg.fields` para
compatibilidade.

## Threading de respostas

As respostas podem carregar os campos LXMF `FIELD_REPLY_TO` (`0x30`),
`FIELD_REPLY_QUOTE` (`0x31`) e `FIELD_THREAD` (`0x08`). Clientes que
renderizam threads, como MeshChatX e Sideband, mostram-nas como
respostas citadas em vez de mensagens planas.

`msg.reply()` faz threading automaticamente: define `FIELD_REPLY_TO`
com o hash da mensagem de entrada e `FIELD_THREAD` com a raiz da
conversação.

``` python
@bot.command("status")
def status(msg):
    msg.reply("all systems nominal")          # resposta em thread
    msg.reply("flat", reply_to=None)          # sair do threading
    msg.reply("noted", quote=True)            # cita o texto de entrada
```

Para envios que não são respostas, passa os campos explicitamente:

``` python
bot.send(dest, "see above", reply_to=msg_hash_hex, quote="earlier text")
```

As respostas de entrada são parseadas no contexto da mensagem:

``` python
@bot.command("ctx")
def ctx_cmd(msg):
    msg.reply_to      # hash hex a que esta mensagem responde, ou None
    msg.reply_quote   # texto citado que a resposta carrega, ou None
    msg.thread        # hash hex da raiz do thread, ou None
```

`pack_reply(message_hash, quote=..., thread=...)` e
`unpack_reply(fields)` são exportados para manuseamento manual de
campos.

## Conversações

Os comandos podem fazer uma pergunta ao remetente e tratar a sua
mensagem seguinte como a resposta, em vez de a despachar como comando:

``` python
@bot.command("report")
def report(msg):
    title = msg.ask("Report title?", timeout=300)
    if title is None:
        msg.reply("Timed out.")
        return
    body = msg.ask("Describe the issue.", timeout=600)
    if body is None:
        msg.reply("Timed out.")
        return
    msg.reply(f"Filed: {title.content}")
```

`msg.ask(prompt, timeout=..., validator=...)` bloqueia o manipulador
até a resposta chegar, o timeout disparar ou a conversação ser
cancelada. Devolve um `Answer` com `content`, `fields`, `hash`,
`sender` e um atalho `reply(text)`.

Um validador rejeita respostas más e volta a perguntar:

``` python
num = msg.ask(
    "Pick a number",
    validator=lambda a: None if a.content.isdigit() else "Digits only",
)
```

Em manipuladores async usa `await msg.ask_async(...)`. Para esperas
longas, ou quando podem existir muitas conversações abertas, usa o
estilo de callbacks para não deixar uma thread parada:

``` python
msg.ask(
    "Send the log file",
    on_answer=lambda ans: ans.reply("received"),
    on_timeout=lambda sender: bot.send(sender, "Too slow."),
    timeout=3600,
)
```

Notas:

- Enviar um comando registado enquanto uma pergunta está pendente
  cancela a pergunta e executa o comando. Os utilizadores têm sempre
  uma saída.
- `bot.conversations.pending_count()` e
  `bot.conversations.cancel(sender)` expõem o registo para
  diagnóstico e ferramentas de administração.
- O registo está limitado a 1024 perguntas pendentes. `ask` devolve
  `None` quando está cheio.
- Um `ask` bloqueante estaciona a thread de entrega que trata essa
  mensagem. É seguro para entregas diretas, mas bots que sincronizam
  grandes lotes de um nó de propagação devem preferir callbacks
  `on_answer`.

## Armazenamento

O framework fornece três backends de armazenamento:

### JSONStorage

``` python
from lxmfy import JSONStorage

storage = JSONStorage("data")
```

### SQLiteStorage

``` python
from lxmfy import SQLiteStorage

storage = SQLiteStorage("data/bot.db")
```

### MsgPackStorage

``` python
from lxmfy.storage import MsgPackStorage

storage = MsgPackStorage("data") # {key}.msgpack files
```

### MemoryStorage

``` python
from lxmfy.storage import MemoryStorage

storage = MemoryStorage() # Inteiramente em memória
```

## Comandos

Registo e tratamento de comandos:

``` python
@bot.command(name="hello", description="Says hello")
def hello(ctx):
    ctx.reply(f"Hello {ctx.sender}!")
```

Os metadados de ajuda e o controlo de acesso vêm de kwargs extra
do decorador:

``` python
from lxmfy import DefaultPerms

@bot.command(
    name="purge",
    description="Clear stored data",
    permissions=DefaultPerms.MANAGE_MESSAGES,
    usage="/purge <key>",
    examples=["/purge cache"],
    category="Admin",
    aliases=["clear"],
)
def purge(ctx, key: str):
    bot.storage.delete(key)
    ctx.reply(f"Deleted {key}")
```

`permissions` sobrescreve a barreira por defeito: `USE_COMMANDS` para
comandos normais, `ALL` para os `admin_only`. `category` agrupa o
comando na saída do `/help`. `aliases` é apenas metadado de ajuda: os
alias são mostrados aos utilizadores mas não são registados para
dispatch, por isso `/clear` não executa `purge` a menos que o registes
como segundo comando.

### Argumentos anotados por tipo

Os comandos analisam e convertem automaticamente os argumentos com base
nas anotações de tipo da função de callback.

``` python
@bot.command(name="add", description="Adds two numbers")
def add(ctx, a: int, b: int):
    result = a + b
    ctx.reply(f"The result is {result}")
```

### Limites de taxa por comando

Limita quantas vezes um mesmo remetente pode invocar um comando dentro
da janela global de `cooldown`. Ao atingir, apenas a invocação é
rejeitada, nunca adiciona avisos nem banimentos.

``` python
@bot.command(name="report", rate_limit=3)
def report(ctx):
    # cada remetente pode chamar isto 3 vezes por período de cooldown
    ...
```

Requer `permissions_enabled=True`, como o limite global. Utilizadores
com papel admin ou `BYPASS_SPAM` saltam a verificação.

## Proteção anti-spam

`bot.spam_protection` aplica o limite global: um remetente pode enviar
`rate_limit` mensagens por janela de `cooldown`. Exceder adiciona um
aviso e rejeita a mensagem. A `max_warnings` o remetente é banido. Os
avisos caducam após `warning_timeout` segundos sem infrações.

As verificações de spam correm dentro do evento `message_received` e
requerem `permissions_enabled=True`.

``` python
bot = LXMFBot(
    name="GuardedBot",
    permissions_enabled=True,
    rate_limit=5,        # mensagens por janela de cooldown
    cooldown=60,         # duração da janela em segundos
    max_warnings=3,      # avisos antes do banimento
    warning_timeout=300, # segundos até os avisos reiniciarem
)

# Levantar um banimento manualmente
bot.spam_protection.unban(sender_hash)
```

Avisos, banimentos e contadores persistem no backend de armazenamento
configurado, por isso os banimentos sobrevivem a reinícios. Remetentes
com `BYPASS_SPAM` nunca são limitados nem banidos. O `rate_limit` por
comando de `@bot.command` é mais suave: só rejeita a invocação e nunca
avisa nem bane.

## Sistema de ajuda

O framework inclui um gerador de ajuda interativo que produz menus de
ajuda categorizados com base nos metadados de Cog e Command.

``` python
# O comando help é registado automaticamente.
# Os utilizadores podem usar '/help' ou '/help <command>'
```

## Comandos em thread

Para operações demoradas ou bloqueantes que não interagem diretamente
com a Reticulum Network Stack, pode executar comandos numa thread
separada para manter o bot responsivo.

``` python
import time

@bot.command(name="long_task", description="Performs a long-running task in a separate thread", threaded=True)
def long_task_command(ctx):
    ctx.reply("Starting a long task... please wait.")
    time.sleep(10) # Isto corre numa thread separada
    ctx.reply("Long task completed!")
```

!!! warning "Segurança de threads"

    Funções marcadas como `threaded=True` **não devem** interagir
    diretamente com a Reticulum Network Stack (RNS) nem com componentes
    que dependam de `lxmfy.transport.py`, pois geralmente não são
    thread-safe. Use `ctx.reply()` para enviar mensagens ao utilizador a
    partir de um comando em thread.

## Eventos

Sistema de eventos para tratar vários eventos do bot:

``` python
@bot.events.on("message_received", EventPriority.HIGHEST)
def handle_message(event):
    # event.data carrega o payload, ex. sender e message
    event.cancel()  # para manipuladores posteriores e o resto do processamento
```

Os manipuladores correm por ordem `EventPriority`: `HIGHEST`, `HIGH`,
`NORMAL`, `LOW`. A própria verificação de spam é um manipulador de
`message_received` com `HIGHEST`, por isso cancelar esse evento é como
o limitador descarta mensagens.

Despacha eventos teus:

``` python
from lxmfy import Event

bot.events.dispatch(Event("order_placed", data={"user": ctx.sender}))
```

`event_logging_enabled`, `max_logged_events` e
`event_middleware_enabled` existem em `BotConfig` mas não estão
ligados: os eventos não são escritos no armazenamento e
`bot.events.use()` é um stub. Trata-os como reservados.

## Testes

`lxmfy.testing.TestBot` é um `LXMFBot` pré-configurado para testes.
Não arranca nenhuma instância Reticulum. As mensagens de entrada
passam pela pipeline real de receção (middleware, verificações de
spam, permissões, dispatch) e os envios de saída são capturados para
asserções.

``` python
from lxmfy import TestBot

def test_ping():
    with TestBot() as bot:
        @bot.command("ping")
        def ping(msg):
            msg.reply("pong")

        sent = bot.receive("/ping", sender="alice")
        assert sent[0].content == "pong"
        assert sent[0].destination == bot.sender_hex("alice")
```

- `bot.receive(content, sender=..., fields=..., message_hash=...)`
  injeta uma mensagem e devolve os objetos `SentMessage` que produziu.
  Os remetentes são nomeados: `"alice"` mapeia para um hash falso
  estável, ou passa diretamente um hash de destino hex.
- `bot.drain()` esvazia as mensagens de saída em fila. `bot.outbox`
  acumula tudo o que foi enviado. `bot.last_sent(sender=...)` obtém o
  mais recente.
- `bot.wait_sent(n, timeout=...)` espera por comandos em thread.
- `bot.receive_later(content, sender=..., delay=...)` responde a
  chamadas `msg.ask` bloqueantes a partir de uma thread daemon.
- `fake_message(content, source_hash=..., ...)` constrói uma mensagem
  de entrada para conduzir `bot._message_received` diretamente.

`SentMessage` embrulha cada mensagem de saída capturada: `destination`
(hex), `content`, `title`, `fields`, `method`, `include_ticket`,
`stamp_cost` e `raw` para o objeto subjacente.

A suite de testes do repositório também inclui cenários de
fiabilidade e stress. Usa o executor de testes do repositório para os
correr.

### Suite avançada de fiabilidade

O framework inclui uma suite extensa de testes automatizados para
ambientes hostis:

- **Testes de manifold**: valida a topologia matemática do espaço
  vetorial de intents NLP.
- **Engenharia do caos**: simula bit-rot, falha de cartão SD e corrupção
  de armazenamento.
- **Desvio temporal**: verifica a resiliência a saltos do relógio do
  sistema (±1 ano).
- **Deteção de fugas**: acompanhamento a longo prazo de memória,
  descritores de ficheiros e threads.

## Permissões

Sistema de permissões para controlar o acesso às funcionalidades do bot:

``` python
from lxmfy import DefaultPerms

@bot.command(name="admin", description="Admin command", admin_only=True)
def admin_command(ctx):
    if ctx.is_admin:
        ctx.reply("Admin command executed")
```

Ativa com `permissions_enabled=True`. Flags de
`DefaultPerms`:

- `USE_BOT`, `SEND_MESSAGES`, `USE_COMMANDS`: acesso básico
- `MANAGE_MESSAGES`, `MANAGE_COMMANDS`, `MANAGE_USERS`: elevado
- `BYPASS_RATELIMIT`, `BYPASS_SPAM`, `VIEW_ADMIN_COMMANDS`: especial
- `VIEW_EVENTS`, `MANAGE_EVENTS`, `BYPASS_EVENT_CHECKS`: sistema de
  eventos
- `NONE`, `ALL`: atalhos

`bot.permissions` gere papéis e atribuições:

``` python
bot.permissions.create_role("moderator", DefaultPerms.MANAGE_MESSAGES | DefaultPerms.BYPASS_SPAM)
bot.permissions.assign_role(user_hash, "moderator")
bot.permissions.remove_role(user_hash, "moderator")
bot.permissions.has_permission(user_hash, DefaultPerms.USE_COMMANDS)
```

Papéis e atribuições persistem no backend configurado. Existem dois
papéis integrados que não podem ser apagados: `user` (padrão) e
`admin`, que é concedido automaticamente a cada hash em `admins`.

## Middleware

Sistema de middleware para processar mensagens e eventos:

``` python
from lxmfy import MiddlewareType

@bot.middleware.register(MiddlewareType.PRE_COMMAND)
def pre_command_middleware(ctx):
    # ctx embrulha o contexto da mensagem, ctx.cancelled descarta-o
    if "spamword" in ctx.data.content:
        ctx.cancel()
```

Três pontos da pipeline executam middleware:

- `PRE_COMMAND`: antes do dispatch de comandos, depois das
  verificações de spam. Se a cadeia devolver `None`, a mensagem é
  abortada por completo.
- `POST_COMMAND`: depois do callback de um comando (incluindo comandos
  em thread, que o disparam na thread de trabalho).
- `PRE_EVENT`: antes do dispatch do evento `message_received`.

`POST_EVENT`, `REQUEST` e `RESPONSE` existem em `MiddlewareType`, mas
nada na pipeline os executa ainda.

## Anexos

Suporte para envio de ficheiros, imagens e áudio:

``` python
from lxmfy import Attachment, AttachmentType

attachment = Attachment(
    type=AttachmentType.IMAGE,
    name="image.jpg",
    data=image_data,
    format="jpg"
)
bot.send_with_attachment(destination, "Here's an image", attachment)
```

## Aparência de ícone (campo LXMF)

Pode definir um ícone personalizado para o bot que clientes LXMF
compatíveis conseguem apresentar. Usa o `LXMF.FIELD_ICON_APPEARANCE`.

``` python
from lxmfy import IconAppearance, pack_icon_appearance_field
import LXMF # Necessário para LXMF.FIELD_ICON_APPEARANCE

# Definir a aparência do ícone
icon_data = IconAppearance(
    icon_name="smart_toy",  # Nome dos Material Symbols
    fg_color=b'\xFF\xFF\xFF',  # Primeiro plano branco (3 bytes)
    bg_color=b'\x4A\x90\xE2'   # Fundo azul (3 bytes)
)

# Empacotar no formato de campo LXMF
icon_lxmf_field = pack_icon_appearance_field(icon_data)

# Enviar uma mensagem com este ícone
bot.send(
    destination_hash_str,
    "Hello from your friendly bot!",
    title="Bot Message",
    lxmf_fields=icon_lxmf_field
)

# Também pode combiná-lo com outros campos, como anexos:
# attachment_field = pack_attachment(some_attachment)
# combined_fields = {**icon_lxmf_field, **attachment_field}
# bot.send(destination, "Message with icon and attachment", lxmf_fields=combined_fields)
```

## Agendador

Sistema de agendamento de tarefas:

``` python
@bot.scheduler.schedule(name="daily_task", cron_expr="0 0 * * *")
def daily_task():
    # Executar diariamente à meia-noite
    pass
```

## Assinaturas

O LXMFy fornece opções de configuração para a assinatura e verificação
criptográfica de mensagens integrada no LXMF:

``` python
from lxmfy import LXMFBot

bot = LXMFBot(
    name="SecureBot",
    signature_verification_enabled=True,  # Ativar a verificação de assinaturas
    require_message_signatures=False      # Definir como True para rejeitar mensagens não assinadas
)
```

!!! note "Gestão de assinaturas"

    O LXMF trata automaticamente de toda a assinatura e verificação
    criptográfica usando identidades RNS. O `SignatureManager` do LXMFy
    é uma camada de configuração que:

    - Controla se a verificação de assinaturas é aplicada
    - Determina a política para mensagens não assinadas (aceitar ou
      rejeitar)
    - Integra com o sistema de permissões (ex.: ignorar a verificação
      para utilizadores de confiança)

As operações criptográficas propriamente ditas são executadas pelo
LXMF/RNS, não pelo LXMFy.

### Sandbox Landlock LSM

Em kernels Linux com suporte a Landlock (5.13+), o LXMFy pode restringir
o acesso ao sistema de ficheiros para o processo do bot e para cogs de
scripts externos.

**Sandbox do processo do bot**

Quando `landlock_enabled=True` (predefinição) e não está em `test_mode`,
o bot chama `apply_landlock_sandbox()` durante a inicialização. Os
diretórios do sistema ficam só de leitura; o armazenamento do bot, a
configuração, os cogs, a configuração Reticulum e os caminhos temporários
mantêm-se graváveis.

``` python
bot = LXMFBot(
    name="SecureBot",
    landlock_enabled=True,
)

status = bot.get_landlock_status()
# chaves de status: landlock_kernel_supported, landlock_requested,
# landlock_auto_enabled, landlock_disabled_by_env, landlock_active
```

**Sobreposição por variável de ambiente**

- `LXMFY_LANDLOCK=0`: desativa o Landlock mesmo em kernels suportados
- `LXMFY_LANDLOCK=1`: tenta o Landlock em Linux independentemente da
  deteção automática
- não definida: segue `landlock_enabled` e a deteção automática do
  kernel

**Sandbox dos cogs externos**

Os cogs de script usam `external_cogs_sandbox_type`. No modo `auto`, o
Landlock é preferido quando disponível por não precisar de ferramentas
externas. Consulte o guia [Criar bots](creating-bots.md) para a lista
completa de opções de sandbox.

### Fixação de identidade

O LXMFy suporta fixação de identidade opcional (identity pinning) para
evitar personificação se uma identidade for rodada ou comprometida.
Quando ativa, o bot "fixa" um endereço LXMF à primeira chave pública
vista.

``` python
bot = LXMFBot(
    identity_pinning_enabled=True
)
```

### Métodos do SignatureManager

O `SignatureManager` está disponível como `bot.signature_manager` quando
`signature_verification_enabled=True`:

- `should_verify_message(sender)`: determina se uma mensagem do
  remetente dado deve ser verificada
- `handle_unsigned_message(sender, message_hash)`: trata mensagens sem
  assinatura válida conforme a política

### Como funcionam as assinaturas LXMF

O LXMF assina automaticamente todas as mensagens enviadas usando a
identidade RNS do remetente durante a operação `pack()`. Quando as
mensagens são recebidas, o LXMF valida as assinaturas e fornece:

- `message.signature_validated`: booleano que indica se a assinatura é
  válida
- `message.unverified_reason`: código de motivo se a validação falhar
  (ex.: `SIGNATURE_INVALID`, `SOURCE_UNKNOWN`)

O LXMFy usa estas propriedades integradas do LXMF para aplicar a
política de assinaturas do bot.

## Entrega de mensagens

O LXMFy fornece funcionalidades avançadas de entrega de mensagens,
incluindo nós de propagação e repetições automáticas:

### Nós de propagação

Envie mensagens através de nós de propagação específicos para maior
fiabilidade na rede Reticulum:

``` python
# Configurar o nó de propagação uma vez, ao nível da configuração/execução
bot.set_propagation_node("<propagation_node_hash>")

# Enviar usando o comportamento de entrega configurado
bot.send(
    destination_hash,
    "Message content"
)

# O hash do nó de propagação deve ser um nó de propagação LXMF válido
# na rede Reticulum
```

Também podes fixar o nó na construção com
`propagation_node="<hash>"`, ou deixar o bot descobrir nós sozinho:

``` python
bot = LXMFBot(
    name="AutoBot",
    autopeer_propagation=True, # aprende nós a partir de announces
    autopeer_maxdepth=4,       # ignora nós a mais de 4 hops
)
```

`bot.get_propagation_node_status()` reporta o nó manual, os nós
descobertos e o nó de saída atualmente em uso.

### Repetições automáticas

Configure tentativas automáticas de repetição para entregas diretas
falhadas:

``` python
bot = LXMFBot(
    name="ReliableBot",
    direct_delivery_retries=5,  # Repetir a entrega direta até 5 vezes
    propagation_fallback_enabled=True
)

bot.send(destination_hash, "Important message")

# O direct_delivery_retries predefinido é 3
# A lógica de repetição trata automaticamente dos callbacks de entrega
```

O sistema de repetição acompanha as tentativas de entrega por destino e
repete automaticamente as entregas falhadas. Entregas bem-sucedidas
repõem o contador de repetições desse destino.

### Envios diferidos

Enviar para um destino cuja identidade o nó ainda não ouviu falha
normalmente de imediato. Com `pending_sends_enabled` (padrão) a
mensagem fica retida em armazenamento e é despejada automaticamente
quando o destino anuncia ou numa varredura periódica.

``` python
bot = LXMFBot(
    pending_sends_enabled=True,
    pending_sends_max=200,     # as mensagens retidas mais antigas caem além disto
    pending_sends_ttl=604800,  # as mensagens retidas expiram após 7 dias
    pending_sends_retry=300,   # segundos entre varreduras em run()
)

# Sobrescritura por envio
bot.send(dest, "hold this", defer=True)
bot.send(dest, "send or drop", defer=False)
```

Os envios retidos aparecem como `held (unknown peers)` no comando
admin `/queue` e produzem eventos `deferred` no tracker de entrega.

### Persistência de mensagens

As mensagens de saída podem ser persistidas em disco para garantir a
entrega mesmo após um reinício do bot. A persistência está ativa por
predefinição. A fila de saída em memória é limitada
(`message_queue_size`, predefinição 50) e descarta a mensagem mais
antiga quando cheia. Hashes de destino inválidos não são restaurados.

``` python
bot = LXMFBot(
    message_persistence_enabled=True,
    message_queue_size=50,
)
```

### Stamps e tickets

Os custos de stamp fazem os remetentes pagar proof-of-work antes da
mensagem ser aceite, o que trava tráfego não solicitado. O LXMFy
expõe os dois lados do mecanismo.

``` python
bot = LXMFBot(
    stamp_cost=16,          # exige este custo de stamp de entrada
    require_stamps=True,    # rejeita mensagens com stamps inválidos
    include_tickets=True,   # deixa os peers responderem sem gerar um stamp
)
```

- `stamp_cost` é o requisito de entrada. O custo de saída de um envio
  continua a vir do announce do peer salvo se passares `stamp_cost=`
  a `bot.send()`.
- `include_tickets` (True por padrão) anexa um ticket de resposta às
  mensagens de saída, para que um peer que exige stamps possa
  responder sem pagar. Sobrescreve por envio com `include_ticket=`.
- `request_unknown_identities=True` pede à rede uma identidade de
  remetente quando uma mensagem chega de origem desconhecida, o que
  ajuda as verificações de stamps e assinaturas a resolver em vez de
  falharem às cegas.

O controlo em tempo de execução está em [Controlos do
router](#controlos-do-router): `set_inbound_stamp_cost`,
`enforce_stamps`, `ignore_stamps`, `generate_ticket` e os métodos de
inspeção de tickets.

### Operar como nó de propagação

Um bot pode também servir de nó de propagação LXMF, armazenando
mensagens para peers offline:

``` python
bot = LXMFBot(
    enable_propagation_node=True,
    message_storage_limit_mb=500,
)

bot.set_message_storage_limit(750)
stats = bot.get_propagation_storage_stats()
```

`get_propagation_node_status()` serve para ambos os papéis: reporta o
nó de saída que este bot usa e se ele próprio atua como nó. Controlos
relacionados: `announce_propagation_node()` anuncia o nó,
`set_retain_on_node()` mantém as mensagens entregues nele, e
`allow_control_identity()` / `disallow_control_identity()` gerem que
identidades podem usar o canal de controlo do nó.

### Eventos de entrega

`bot.delivery` regista um fluxo limitado de eventos do ciclo de vida
de saída para observar o fluxo de mensagens sem ler logs. Fases:
`queued`, `deferred`, `dispatched`, `delivered`, `failed`,
`cancelled`, `dropped`. A cauda recente é persistida em armazenamento
e restaurada no arranque.

``` python
@bot.on_delivery_event()
def watch(event):
    print(event["stage"], event.get("destination"), event.get("reason"))

# Ou inspeção direta
recent = bot.delivery.recent(20)
failures = bot.delivery.recent(stage="failed")
to_peer = bot.delivery.recent(destination="aa11bb...")
```

Cada evento é um dict com `ts`, `stage` e, opcionalmente,
`destination`, `message_id`, `hash`, `method`, `attempts`, `reason`,
`title`.

Os admins têm um comando `/delivery [limit]` que renderiza a mesma
linha temporal no chat, e `lxmfy debug` mostra um resumo da linha
temporal de entregas nas verificações da pipeline de envio.

### Comandos de administração integrados

Estes comandos são registados automaticamente e exigem que o remetente
esteja em `admins` quando as permissões estão ativas:

| Comando | Ação |
| --- | --- |
| `/queue` | Mostra a fila de saída do router, a fila interna e os envios retidos |
| `/cancel <id|all>` | Cancela mensagens de saída pendentes |
| `/inbox [cancel <hash|all>]` | Lista ou cancela transferências de entrada ativas |
| `/delivery [n]` | Mostra os últimos n eventos de entrega (padrão 15, máx. 50) |
| `/loadext <name>` | Carrega uma extensão cog |
| `/reloadext <name>` | Recarrega uma extensão cog carregada |

### Controlos do router

Wrappers finos sobre o `LXMRouter` subjacente para controlo de
remetentes, tickets, gestão da fila de saída e sincronização do nó de
propagação. Todos aceitam hashes de destino como strings hex e
devolvem `False` quando o router não está a correr (por exemplo em
`test_mode`).

**Controlo de remetentes (entrada)**

- `ignore_destination(destination)` / `unignore_destination(destination)` / `is_ignored(destination)`:
  Descarta mensagens de entrada de um remetente
- `allow_destination(destination)` / `disallow_destination(destination)`:
  Gestão de whitelist quando o router corre em modo allow-list
- `prioritise_destination(destination)` / `unprioritise_destination(destination)`:
  Lista de remetentes priorizados
- `set_inbound_stamp_cost(stamp_cost)`: Exige um custo de stamp em
  mensagens de entrada (`None` limpa)
- `enforce_stamps()` / `ignore_stamps()`: Comutadores de exigência de
  stamps de entrada

**Tickets**

- `generate_ticket(destination, expiry=None)`: Emite um ticket de
  stamp de entrada para um remetente
- `get_inbound_tickets(destination)`: Tickets detidos para um
  remetente
- `get_outbound_ticket(destination)` / `get_outbound_ticket_expiry(destination)` /
  `get_outbound_stamp_cost(destination)`: Estado do ticket de saída
  aprendido da rede

**Fila de saída**

- `outbound_queue()`: Snapshot das mensagens de saída pendentes
- `get_outbound_progress(lxm_hash)`: Progresso de entrega de um hash
  de mensagem, ou `None`
- `cancel_outbound(message_id)`: Remove uma mensagem em fila antes da
  entrega
- `delivery_link_available(destination)`: Se existe um link RNS ativo
  para o destino

**Fila de entrada**

- `has_message(message_hash)`: Se um hash LXM de entrada já foi
  entregue
- `inbound_count()`: Transferências de entrada de recursos ativas em
  curso
- `inbound_transfers()`: Snapshot de cada transferência com hash,
  tamanho, progresso e estado
- `cancel_inbound(resource_hash)`: Aborta uma transferência de entrada
  ativa
- `cancel_all_inbound()`: Aborta todas as transferências de entrada
  ativas, devolve a contagem cancelada

**Descoberta de peers**

Metadados de announce de destinos que este nó ouviu:

- `get_peer_app_data(destination)`: Bytes app_data anunciados em bruto
- `get_peer_lxmf_data(destination)`: Metadados de announce LXMF
  descodificados (`display_name`, `stamp_cost`, `capabilities`), ou
  `None` quando o peer não anunciou dados LXMF válidos
- `get_peer_announce(destination)`: Registo de announce completo com
  hops, received_at, interface e app_data
- `list_peer_announces(limit=100)`: Todos os announces ouvidos, o mais
  recente primeiro

**Propagação**

- `sync_propagation_node(max_messages=None)`: Puxa mensagens do nó de
  propagação configurado
- `cancel_propagation_sync()`: Para uma sincronização em curso
- `get_propagation_stats()`: Estado de transferência e limites do nó,
  ou `None`
- `set_retain_on_node(retain)`: Mantém as mensagens entregues no nó
- `announce_propagation_node()`: Anuncia este nó como nó de propagação
- `allow_control_identity(destination)` / `disallow_control_identity(destination)`:
  Whitelist do canal de controlo de propagação

**Ingestão**

- `ingest_lxm_uri(uri)`: Importa uma mensagem URI `lxm://` para a fila
  de entrada

## Diagnóstico

Quando as mensagens não fluem, o depurador verifica todo o caminho em
vez de adivinhar: configuração do Reticulum, estado da instância
partilhada, interfaces, identidade, comportamento de announce,
configuração de entrega e a pipeline de envio.

``` bash
lxmfy debug                          # relatório doctor completo, guardado em ficheiro
lxmfy debug probe <hash> --request-path --wait 30
lxmfy debug send <hash>              # segue um envio de teste
lxmfy debug receive                  # verifica a prontidão de receção
lxmfy debug compare <hash_a> <hash_b>
lxmfy debug tips                     # correções de falhas comuns
```

Os relatórios são redigidos por privacidade por padrão: caminhos home
e hashes são truncados. `--json` emite saída legível por máquina,
`-o FICHEIRO` escreve o relatório, `--no-save` salta o ficheiro,
`--no-privacy` mantém os valores completos para uso local, e
`--no-color` ou `NO_COLOR` desativa a saída ANSI.

As mesmas verificações são chamáveis a partir de código:

``` python
report = bot.diagnose_connectivity()            # relatório doctor como dict
probe = bot.diagnose_destination(               # sonda de identidade e rota
    "<peer_hash>", request_path=True, wait=30,
)

debugger = bot.get_debugger()                   # API completa
checks = debugger.check_send_pipeline()
verdict = debugger.run_doctor(destination)
```

`lxmfy/debugger.py` também exporta um helper autónomo
`diagnose_destination(hash, ...)` mais os tipos de relatório
`CheckResult`, `DestinationProbe`, `DoctorReport` e `MessageDebugger`
para ferramentas próprias.

## Manipuladores de mensagens

O LXMFy fornece decoradores para tratar diferentes tipos de mensagens
recebidas:

### Manipulador da primeira mensagem

Trate a primeira mensagem de cada utilizador:

``` python
@bot.on_first_message()
def welcome_user(sender, message):
    content = message.content.decode("utf-8")
    bot.send(sender, f"Welcome! You said: {content}")
    return True  # Devolver True para parar o processamento
```

### Manipulador geral de mensagens

Trate todas as mensagens recebidas antes do processamento de comandos:

``` python
@bot.on_message()
def handle_all_messages(sender, message):
    content = message.content.decode("utf-8").strip()

    # Lógica personalizada aqui
    if content.startswith("echo:"):
        bot.send(sender, content[5:])
        return True  # Parar o processamento

    return False  # Continuar para o processamento de comandos
```

Os manipuladores de mensagens são chamados nesta ordem: 1. Manipulador
da primeira mensagem (se for a primeira mensagem deste remetente)
2. Manipuladores gerais de mensagens (registados com `on_message()`)
3. Processamento de comandos (se a mensagem começar com o prefixo de
comando)

### Callback de recurso

`bot.received(fn)` regista um callback que corre no fim da pipeline
para mensagens que mais nada consumiu: nenhum manipulador de primeira
mensagem, nenhum manipulador `on_message` que devolvesse True, nenhum
comando ou intent NLP correspondente. O callback recebe o mesmo
contexto de mensagem que os comandos, com `msg.sender`, `msg.content`,
`msg.reply()` e o resto.

``` python
@bot.received
def fallback(msg):
    msg.reply("Sorry, I did not understand that.")
```

Usa-o como apanha-geral para entrada de texto livre.

## Reticulum Relay Chat (RRC)

Os bots podem entrar em hubs [RRC](https://rrc.kc1awv.net/) através de
RNS Links com envelopes CBOR. Pacote: `lxmfy.rrc`.

### Opções do BotConfig

- `rrc_enabled` (bool, predefinição `False`): ligar aos hubs
  configurados no arranque
- `rrc_hubs` (lista de hashes hex): hashes de destino dos hubs
- `rrc_rooms` (lista de str): salas a entrar automaticamente após
  WELCOME
- `rrc_nick` (str ou None): nickname no HELLO e nas mensagens de sala
- `rrc_dest_name` (str, predefinição `"rrc.hub"`): nome de destino usado
  para construir o destino do hub
- `rrc_auto_reconnect` (bool, predefinição `True`): religar após perda
  do link
- `rrc_persist_sessions` (bool, predefinição `True`): persistir hubs e
  salas entre reinícios
- `reticulum_config_dir` (str ou None): diretório de configuração
  Reticulum. Também definível via `LXMFY_RETICULUM_CONFIG_DIR`. Use a
  mesma configuração do MeshChatX (frequentemente `~/.reticulum`) para
  os anúncios do hub serem visíveis.

### Exemplo

``` python
from lxmfy import LXMFBot, RRCMessage

bot = LXMFBot(
    name="RoomBot",
    reticulum_config_dir="~/.reticulum",
    rrc_enabled=True,
    rrc_hubs=["664fc0e8d2e448658e37bb3f34e6c88f"],
    rrc_rooms=["general"],
    rrc_nick="RoomBot",
)

@bot.on_rrc
def on_rrc(event, client, payload):
    if event == "msg" and isinstance(payload, RRCMessage) and payload.mention:
        client.send_message(payload.room, f"Hi {payload.nick}")

# API em tempo de execução
# bot.connect_rrc(hub_hash, rooms=["general"])
# bot.rrc.send_message("general", "hello")
# bot.rrc.send_notice("general", "notice")
# bot.rrc.send_action("general", "waves")
# bot.rrc.join("ops")
# bot.rrc.part("ops")
# bot.rrc.status()
# bot.disconnect_rrc()
```

### Tipos exportados

- `RRCClient`: sessão de um único hub
- `RRCManager`: gestor multi-hub (`bot.rrc`)
- `RRCMessage`: payload de evento de sala (`kind`, `room`, `text`,
  `nick`, `src`, `mention`, ...)
- `RRC_VERSION`: constante da versão do protocolo de rede
- `DEFAULT_DEST_NAME`: Nome de destino de hub por padrão
  (`"rrc.hub"`)
- `make_envelope`, `encode_envelope`, `decode_envelope`,
  `validate_envelope`, `normalize_room`: Helpers de formato wire para
  ferramentas que falam diretamente com hubs

Os eventos comuns passados aos manipuladores `@bot.on_rrc` incluem
`status`, `welcome`, `joined`, `parted`, `msg`, `notice`, `action`,
`motd`, `error` e `rtt`.

# Templates

O framework inclui vários templates de bot prontos a usar:

## EchoBot

Bot de eco simples que repete as mensagens:

``` python
from lxmfy.templates import EchoBot

bot = EchoBot()
bot.run()
```

## NoteBot

Bot de notas com armazenamento JSON:

``` python
from lxmfy.templates import NoteBot

bot = NoteBot()
bot.run()
```

## ReminderBot

Bot de lembretes com armazenamento SQLite:

``` python
from lxmfy.templates import ReminderBot

bot = ReminderBot()
bot.run()
```

## RRCBot

Bot de sala RRC que entra nos hubs configurados e responde a
`@menções`. Usa por predefinição o hub
`664fc0e8d2e448658e37bb3f34e6c88f`, a sala `#general` e `~/.reticulum`
quando disponível.

``` python
from lxmfy.templates import RRCBot

bot = RRCBot(
    hubs=["664fc0e8d2e448658e37bb3f34e6c88f"],
    rooms=["general"],
    nick="RRCBot",
    reticulum_config_dir="~/.reticulum",
)
bot.run()
```

# Ferramentas CLI

O framework fornece ferramentas de linha de comandos para a gestão de
bots. Executar `lxmfy` sem argumentos abre um menu interativo.

``` bash
# Scaffold interativo de um projeto completo
lxmfy init mybot                 # diretório do projeto, bot.py, cogs/, README
lxmfy init --here --yes          # diretório atual, aceita todos os defaults

# Criar um único ficheiro de bot
lxmfy create mybot
lxmfy create --template echo mybot
lxmfy create --template rrc my_rrc_bot
lxmfy create mybot --no-cogs     # salta o pacote cogs
lxmfy create --output dir/bot.py --name MyBot

# Executar um bot de template
lxmfy run echo
lxmfy run rrc
lxmfy run reminder --name "MyReminder"

# Diagnosticar conectividade (ver a secção Diagnóstico)
lxmfy debug
lxmfy debug probe <hash> --request-path --wait 30

# Testar a verificação de assinaturas com uma mensagem
lxmfy signatures test

# Ativar a verificação de assinaturas
lxmfy signatures enable

# Desativar a verificação de assinaturas
lxmfy signatures disable
```

`lxmfy init` pergunta pelo nome do projeto, template, backend de
armazenamento, prefixo de comandos e hashes de admin. Cada pergunta
aceita um flag em seu lugar: `--dir`, `--bot-name`, `--template`,
`--storage`, `--prefix`, `--admins`, `--no-cogs`, `--force`, `--yes`.
Com stdin não-TTY toma os defaults.

Templates para `create` e `run`: `basic`, `echo`, `reminder`, `note`,
`cogtest`, `rrc`.

# Tratamento de erros

Capture falhas de encerramento e de execução à volta de `bot.run()`:

``` python
try:
    bot.run()
except KeyboardInterrupt:
    bot.cleanup()
except Exception as e:
    logger.error(f"Error running bot: {str(e)}")
```

# Referência de módulos

Gerado a partir das docstrings do código-fonte.

::: lxmfy.LXMFBot

::: lxmfy.BotConfig

::: lxmfy.Command

::: lxmfy.Attachment

::: lxmfy.AttachmentType

::: lxmfy.IconAppearance

::: lxmfy.Event

::: lxmfy.EventManager

::: lxmfy.EventPriority

::: lxmfy.MiddlewareContext

::: lxmfy.MiddlewareManager

::: lxmfy.MiddlewareType

::: lxmfy.DefaultPerms

::: lxmfy.PermissionManager

::: lxmfy.Role

::: lxmfy.HelpFormatter

::: lxmfy.HelpSystem

::: lxmfy.TaskScheduler

::: lxmfy.ScheduledTask

::: lxmfy.Storage

::: lxmfy.JSONStorage

::: lxmfy.SQLiteStorage

::: lxmfy.storage.MemoryStorage

::: lxmfy.MsgPackStorage

::: lxmfy.ConversationManager

::: lxmfy.Answer

::: lxmfy.DeliveryTracker

::: lxmfy.TestBot

::: lxmfy.SentMessage

::: lxmfy.Debugger

::: lxmfy.MessageDebugger

::: lxmfy.DoctorReport

::: lxmfy.DestinationProbe

::: lxmfy.CheckResult

::: lxmfy.RRCClient

::: lxmfy.RRCManager

::: lxmfy.RRCMessage
