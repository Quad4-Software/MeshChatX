# Componentes principales

## LXMFBot

La clase principal del bot, que gestiona el enrutado de mensajes, el
procesamiento de comandos y el ciclo de vida del bot.

``` python
from lxmfy import LXMFBot

bot = LXMFBot(
    name="MyBot",
    command_prefix="/",
    admins=set(),
    config_path=None,                 # por defecto "config" en el directorio de trabajo
    reticulum_config_dir=None,        # o LXMFY_RETICULUM_CONFIG_DIR / "~/.reticulum"
    test_mode=False,                  # omite el arranque de RNS, para tests
    log_level="INFO",                 # nivel del logger de lxmfy, None no toca el logging
    loglevel=None,                    # nivel de log de RNS 0-7, None usa la config de reticulum

    # Announces
    announce=600,
    announce_immediately=True,
    announce_enabled=True,
    announce_display_name_file=None,  # archivo bajo config_path que sobrescribe el
                                      # nombre anunciado (archivo por defecto:
                                      # bot_display_name.txt)

    # Protección antispam
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

    # Almacenamiento, eventos, permisos
    storage_type="json",              # "json", "sqlite", "msgpack" o "memory"
    storage_path="data",
    permissions_enabled=False,
    first_message_enabled=True,
    event_logging_enabled=True,
    max_logged_events=1000,
    event_middleware_enabled=True,

    # Seguridad
    signature_verification_enabled=False,
    require_message_signatures=False,
    require_stamps=False,             # rechaza mensajes con stamps inválidos
    request_unknown_identities=False, # pide identidades de remitente a la red
    stamp_cost=None,                  # coste de stamp entrante, None lo desactiva
    include_tickets=True,             # adjunta tickets de respuesta a salientes
    identity_pinning_enabled=False,
    landlock_enabled=True,

    # Funciones opcionales
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
    propagation_node=None,            # hash del nodo de propagación saliente
    autopeer_propagation=False,       # descubre nodos de propagación por announces
    autopeer_maxdepth=4,              # profundidad máxima de saltos, None = sin límite
    enable_propagation_node=False,    # ejecuta este bot como nodo de propagación
    message_storage_limit_mb=500,     # tope de almacenamiento del nodo, solo modo nodo

    # Envíos diferidos
    pending_sends_enabled=True,       # retiene envíos a destinos desconocidos
    pending_sends_max=200,
    pending_sends_ttl=604800,         # 7 días
    pending_sends_retry=300,          # segundos entre barridos de reintento

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

Todas estas opciones son campos de `BotConfig`. `LXMFBot(**kwargs)`
pasa cada argumento de palabra clave, así que `bot.config` contiene los
valores resueltos.

### Métodos principales

- `run(delay=10)`: Inicia el bucle principal del bot
- `cleanup()`: Persiste las colas, cancela conversaciones y apaga el
  planificador, el router y RNS. Se llama automáticamente al salir de
  `run()`.
- `send(destination, message, title="Reply", lxmf_fields=None, stamp_cost=None, opportunistic=None, method=None, include_ticket=None, defer=None, reply_to=None, quote=None, thread=None)`:
  Envía un mensaje a un destino. `stamp_cost` sobrescribe el coste
  saliente de este mensaje, `opportunistic` sobrescribe
  `opportunistic_sending`, `include_ticket` sobrescribe
  `include_tickets` y `defer` sobrescribe `pending_sends_enabled`.
  `reply_to`, `quote` y `thread` establecen los campos de threading de
  respuesta.
- `send_with_attachment(destination, message, attachment, title="Reply", stamp_cost=None, opportunistic=None)`:
  Envía un mensaje con adjunto
- `command(name, description="No description provided", admin_only=False, permissions=None, usage=None, examples=None, category=None, aliases=None, threaded=False, rate_limit=None)`:
  Decorador para registrar comandos. `permissions` sobrescribe la
  barrera de `DefaultPerms` (`ALL` con `admin_only`, si no
  `USE_COMMANDS`), `threaded` ejecuta el callback en un hilo de
  trabajo, `rate_limit` limita las invocaciones por remitente y
  ventana de cooldown, y `usage`, `examples`, `category`, `aliases`
  alimentan el sistema de ayuda. Los comandos admiten argumentos con
  type hints para conversión automática.
- `intent(name, examples)`: Decorador para registrar manejadores de
  intents NLP.
- `nlp.export_model()`: Exporta los datos del modelo NLP entrenado.
- `nlp.import_model(model_data)`: Importa datos de modelo NLP
  exportados previamente.
- `request_link(destination_hash, callback=None, app_name="lxmf", *aspects)`:
  Solicita un enlace RNS a un destino. Permite `app_name` y `aspects`
  propios (por defecto "lxmf" y "delivery").
- `on_link(callback)`: Registra un manejador para enlaces RNS
  entrantes.
- `load_extension(name)`: Carga un módulo de extensión cog por nombre
  (p. ej. "cogs.utility").
- `reload_extension(name)`: Recarga un módulo de extensión cog.
- `add_cog(cog_instance)`: Añade una instancia de clase cog al bot.
- `remove_cog(cog_name)`: Quita un cog por su nombre de clase.
- `on_first_message()`: Decorador para manejar los primeros mensajes
  de usuarios
- `on_message()`: Decorador para manejar todos los mensajes (se llama
  antes del procesamiento de comandos)
- `received(function)`: Registra un callback invocado con el contexto
  del mensaje para cada mensaje entrante que atravesó la pipeline sin
  ser consumido por un comando o intent
- `on_reaction()`: Decorador para manejar reacciones entrantes. Los
  manejadores reciben `(sender, reaction)`, donde reaction lleva las
  claves `reaction_to`, `reaction_emoji` y `reaction_sender`
- `react(destination, message_hash, reaction)`: Envía una reacción a
  un mensaje mediante el campo LXMF `FIELD_REACTION`
- `validate()`: Ejecuta comprobaciones de validación sobre la
  configuración del bot
- `get_landlock_status()`: Devuelve la disponibilidad y el estado de
  activación de la sandbox Landlock LSM del proceso del bot
- `diagnose_destination(destination, request_path=False, wait=0.0)`:
  Sondea el estado de identidad y ruta de un hash de destino
- `diagnose_connectivity(destination=None, request_path=False, wait=0.0)`:
  Ejecuta el informe doctor completo y lo devuelve como dict
- `get_debugger()`: Devuelve un `Debugger` vinculado a este bot
- `set_propagation_node(node_hash)`: Fija el nodo de propagación
  saliente
- `get_propagation_node_status()`: Estado de los nodos de propagación
  salientes configurados, descubiertos y actualmente en uso
- `set_message_storage_limit(megabytes)`: Tope de almacenamiento al
  operar como nodo de propagación
- `get_propagation_storage_stats()`: Uso de almacenamiento del nodo,
  o un dict que explica por qué no está disponible
- `connect_rrc(hub_hash, rooms=None, nick=None, dest_name=None, auto_reconnect=None)`:
  Conecta a un hub RRC como cliente
- `disconnect_rrc(hub_hash=None)`: Desconecta una o todas las
  sesiones de hub RRC
- `on_rrc(callback=None)`: Decorador o registro de manejador para
  eventos RRC (`handler(event, client, payload)`)
- `on_delivery_event(callback=None)`: Suscribe al flujo de eventos de
  entrega saliente, como decorador o llamada directa

### Atributos

- `config`: La `BotConfig` resuelta
- `commands`, `cogs`: Registros de comandos y cogs
- `storage`: El backend de almacenamiento activo
- `scheduler`: `TaskScheduler` para tareas tipo cron
- `events`: `EventManager` para manejadores de eventos y dispatch
- `middleware`: `MiddlewareManager` para middleware de comandos
- `permissions`: `PermissionManager` para roles y flags
- `spam_protection`: `SpamProtection` para límites de tasa, avisos y
  baneos
- `signature_manager`: Capa de política de firmas
- `nlp`: El clasificador de intents (solo coincide con `nlp_enabled`)
- `delivery`: `DeliveryTracker`, el flujo de eventos salientes
- `conversations`: `ConversationManager` para preguntas `msg.ask`
- `rrc`: `RRCManager` para sesiones multi-hub, `None` hasta que RRC
  se active o `connect_rrc()` se ejecute
- `local`: La `RNS.Destination` del bot (su dirección LXMF es
  `bot.local.hash`)

## Nombre anunciado

El nombre que ven los peers viene de `name`, pero hay dos
sobrescrituras para los announces. Si `announce_display_name_file`
está definido y ese archivo existe bajo `config_path`, su contenido
gana. Si no, se lee `bot_display_name.txt` bajo `config_path` cuando
existe. En ambos casos, asignar `bot.name = "Nuevo nombre"`
resincroniza el nombre anunciado en tiempo de ejecución.

Esto permite a los operadores renombrar un bot sin tocar el código, y
que el nombre anunciado difiera del nombre interno de configuración.

## Comandos estructurados mediante campos LXMF

Los bots pueden recibir comandos enviados mediante el campo LXMF
`FIELD_COMMANDS` (`0x09`) y responder automáticamente con
`FIELD_RESULTS` (`0x0A`). Esto permite flujos de petición/respuesta
estructurados junto a los comandos de texto normales.

Los `FIELD_COMMANDS` entrantes se analizan y se enrutan por el mismo
registro de comandos que los de texto, compartiendo las comprobaciones
de permisos, el parseo de argumentos tipados, los hilos y el middleware.

``` python
from lxmfy import LXMFBot, FIELD_COMMANDS, FIELD_RESULTS, pack_result, unpack_commands

bot = LXMFBot(name="FieldBot")

@bot.command(name="status", description="Return bot status")
def status_cmd(ctx):
    # ctx.fields contiene el dict de campos LXMF en bruto
    # ctx.request_id se establece automáticamente si el comando lo incluía
    ctx.reply("Bot is online")

# Envío de un comando estructurado desde otro cliente LXMF:
# lxm.fields[FIELD_COMMANDS] = {"command": "status", "args": [], "request_id": "abc123"}
# router.handle_outbound(lxm)

# La respuesta del bot incluye automáticamente FIELD_RESULTS con la respuesta y el request_id.
```

Para desactivar el procesamiento de comandos de campo, define
`lxmf_commands_enabled=False` en `BotConfig`.

## Reacciones

Las reacciones viajan como el campo LXMF `FIELD_REACTION` (`0x40`) en un
mensaje por lo demás vacío. `pack_reaction` y `unpack_reaction`
construyen y analizan ese campo.

``` python
from lxmfy import pack_reaction, unpack_reaction

# Enviar una reacción a un mensaje
bot.react(destination_hash, message_hash_hex, "thumbs up emoji")

# Recibir reacciones
@bot.on_reaction()
def on_reaction(sender, reaction):
    # reaction["reaction_to"]  - hash en hex del mensaje objetivo
    # reaction["reaction_emoji"] - texto de la reacción (hasta 16 caracteres)
    # reaction["reaction_sender"] - remitente
    print(f"{sender} reacted {reaction['reaction_emoji']} to {reaction['reaction_to']}")
    return True
```

El texto de la reacción está limitado a 16 caracteres imprimibles. El
campo en bruto sigue disponible en `ctx.fields` y `msg.fields` por
compatibilidad.

## Threading de respuestas

Las respuestas pueden llevar los campos LXMF `FIELD_REPLY_TO` (`0x30`),
`FIELD_REPLY_QUOTE` (`0x31`) y `FIELD_THREAD` (`0x08`). Los clientes
que renderizan hilos, como MeshChatX y Sideband, los muestran como
respuestas citadas en lugar de mensajes planos.

`msg.reply()` hace threading automáticamente: establece
`FIELD_REPLY_TO` al hash del mensaje entrante y `FIELD_THREAD` a la
raíz de la conversación.

``` python
@bot.command("status")
def status(msg):
    msg.reply("all systems nominal")          # respuesta en hilo
    msg.reply("flat", reply_to=None)          # excluir el threading
    msg.reply("noted", quote=True)            # cita el texto entrante
```

Para envíos que no son respuestas, pasa los campos explícitamente:

``` python
bot.send(dest, "see above", reply_to=msg_hash_hex, quote="earlier text")
```

Las respuestas entrantes se parsean en el contexto del mensaje:

``` python
@bot.command("ctx")
def ctx_cmd(msg):
    msg.reply_to      # hash hex al que responde este mensaje, o None
    msg.reply_quote   # texto citado que lleva la respuesta, o None
    msg.thread        # hash hex de la raíz del hilo, o None
```

`pack_reply(message_hash, quote=..., thread=...)` y
`unpack_reply(fields)` se exportan para el manejo manual de campos.

## Conversaciones

Los comandos pueden hacer una pregunta al remitente y tratar su
siguiente mensaje como la respuesta, en lugar de despacharlo como
comando:

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

`msg.ask(prompt, timeout=..., validator=...)` bloquea el manejador
hasta que llega la respuesta, salta el timeout o se cancela la
conversación. Devuelve un `Answer` con `content`, `fields`, `hash`,
`sender` y un atajo `reply(text)`.

Un validador rechaza respuestas incorrectas y repite la pregunta:

``` python
num = msg.ask(
    "Pick a number",
    validator=lambda a: None if a.content.isdigit() else "Digits only",
)
```

En manejadores async usa `await msg.ask_async(...)`. Para esperas
largas, o cuando puede haber muchas conversaciones abiertas, usa el
estilo de callbacks para no dejar un hilo aparcado:

``` python
msg.ask(
    "Send the log file",
    on_answer=lambda ans: ans.reply("received"),
    on_timeout=lambda sender: bot.send(sender, "Too slow."),
    timeout=3600,
)
```

Notas:

- Enviar un comando registrado mientras hay una pregunta pendiente
  cancela la pregunta y ejecuta el comando. Los usuarios siempre
  tienen vía de escape.
- `bot.conversations.pending_count()` y
  `bot.conversations.cancel(sender)` exponen el registro para
  diagnóstico y herramientas de administración.
- El registro está limitado a 1024 preguntas pendientes. `ask`
  devuelve `None` cuando está lleno.
- El `ask` bloqueante aparca el hilo de entrega que maneja ese
  mensaje. Es seguro para entregas directas, pero los bots que
  sincronizan grandes lotes desde un nodo de propagación deberían
  preferir callbacks `on_answer`.

## Almacenamiento

El framework ofrece tres backends de almacenamiento:

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

storage = MemoryStorage() # Íntegramente en memoria
```

## Comandos

Registro y manejo de comandos:

``` python
@bot.command(name="hello", description="Says hello")
def hello(ctx):
    ctx.reply(f"Hello {ctx.sender}!")
```

Los metadatos de ayuda y el control de acceso vienen de kwargs
extra del decorador:

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

`permissions` sobrescribe la barrera por defecto: `USE_COMMANDS` para
comandos normales, `ALL` para los `admin_only`. `category` agrupa el
comando en la salida de `/help`. `aliases` es solo metadato de ayuda:
los alias se muestran a los usuarios pero no se registran para
dispatch, así que `/clear` no ejecutará `purge` salvo que lo registres
como segundo comando.

### Argumentos con type hints

Los comandos analizan y convierten automáticamente los argumentos según
los type hints de la función callback.

``` python
@bot.command(name="add", description="Adds two numbers")
def add(ctx, a: int, b: int):
    result = a + b
    ctx.reply(f"The result is {result}")
```

### Límites de tasa por comando

Limita cuántas veces un mismo remitente puede invocar un comando
dentro de la ventana global de `cooldown`. Al alcanzarlo solo se
rechaza la invocación, nunca añade avisos ni baneos.

``` python
@bot.command(name="report", rate_limit=3)
def report(ctx):
    # cada remitente puede llamarlo 3 veces por periodo de cooldown
    ...
```

Requiere `permissions_enabled=True`, como el límite global. Los
usuarios con rol admin o `BYPASS_SPAM` saltan la comprobación.

## Protección antispam

`bot.spam_protection` aplica el límite global: un remitente puede
enviar `rate_limit` mensajes dentro de cada ventana de `cooldown`.
Excederlo añade un aviso y rechaza el mensaje. A `max_warnings` el
remitente queda baneado. Los avisos caducan tras `warning_timeout`
segundos sin infracciones.

Las comprobaciones de spam corren dentro del evento
`message_received` y requieren `permissions_enabled=True`.

``` python
bot = LXMFBot(
    name="GuardedBot",
    permissions_enabled=True,
    rate_limit=5,        # mensajes por ventana de cooldown
    cooldown=60,         # duración de la ventana en segundos
    max_warnings=3,      # avisos antes del baneo
    warning_timeout=300, # segundos hasta que los avisos se reinician
)

# Levantar un baneo manualmente
bot.spam_protection.unban(sender_hash)
```

Los avisos, baneos y contadores persisten en el backend de
almacenamiento configurado, así que los baneos sobreviven a
reinicios. Los remitentes con `BYPASS_SPAM` nunca se limitan ni se
banean. El `rate_limit` por comando de `@bot.command` es más suave:
solo rechaza la invocación y nunca avisa ni banea.

## Sistema de ayuda

El framework incluye un generador interactivo de ayuda que ofrece menús
categorizados basados en los metadatos de Cog y Command.

``` python
# El comando de ayuda se registra automáticamente.
# Los usuarios pueden usar '/help' o '/help <command>'
```

## Comandos en hilos

Para operaciones de larga duración o bloqueantes que no interactúan
directamente con el Reticulum Network Stack, puedes ejecutar comandos en
un hilo separado para que el bot siga respondiendo.

``` python
import time

@bot.command(name="long_task", description="Performs a long-running task in a separate thread", threaded=True)
def long_task_command(ctx):
    ctx.reply("Starting a long task... please wait.")
    time.sleep(10) # Esto se ejecuta en un hilo separado
    ctx.reply("Long task completed!")
```

!!! warning "Seguridad en hilos"

    Las funciones marcadas como `threaded=True` **no deben** interactuar
    directamente con el Reticulum Network Stack (RNS) ni con ningún
    componente que dependa de `lxmfy.transport.py`, ya que en general no
    son seguros para hilos. Usa `ctx.reply()` para enviar mensajes al
    usuario desde un comando en hilo.

## Eventos

Sistema de eventos para manejar distintos eventos del bot:

``` python
@bot.events.on("message_received", EventPriority.HIGHEST)
def handle_message(event):
    # event.data lleva la carga, p. ej. sender y message
    event.cancel()  # detiene manejadores posteriores y el resto del procesamiento
```

Los manejadores corren en orden `EventPriority`: `HIGHEST`, `HIGH`,
`NORMAL`, `LOW`. La propia comprobación de spam es un manejador de
`message_received` con `HIGHEST`, así que cancelar ese evento es cómo
el limitador descarta mensajes.

Despacha eventos propios:

``` python
from lxmfy import Event

bot.events.dispatch(Event("order_placed", data={"user": ctx.sender}))
```

`event_logging_enabled`, `max_logged_events` y
`event_middleware_enabled` existen en `BotConfig` pero no están
conectados: los eventos no se escriben en almacenamiento y
`bot.events.use()` es un stub. Trátalos como reservados.

## Testing

`lxmfy.testing.TestBot` es un `LXMFBot` preconfigurado para tests. No
arranca ninguna instancia de Reticulum. Los mensajes entrantes pasan
por la pipeline real de recepción (middleware, comprobaciones de spam,
permisos, dispatch) y los envíos salientes se capturan para
aserciones.

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
  inyecta un mensaje y devuelve los objetos `SentMessage` que
  produjo. Los remitentes son nombrados: `"alice"` mapea a un hash
  falso estable, o pasa directamente un hash de destino hex.
- `bot.drain()` vacía los mensajes salientes en cola. `bot.outbox`
  acumula todo lo enviado. `bot.last_sent(sender=...)` obtiene el más
  reciente.
- `bot.wait_sent(n, timeout=...)` espera a comandos en hilo.
- `bot.receive_later(content, sender=..., delay=...)` responde a
  llamadas `msg.ask` bloqueantes desde un hilo daemon.
- `fake_message(content, source_hash=..., ...)` construye un mensaje
  entrante para invocar `bot._message_received` directamente.

`SentMessage` envuelve cada mensaje saliente capturado: `destination`
(hex), `content`, `title`, `fields`, `method`, `include_ticket`,
`stamp_cost` y `raw` para el objeto subyacente.

La suite de tests del repositorio también incluye escenarios de
fiabilidad y estrés. Usa el ejecutor de tests del repositorio para
correrlos.

### Suite avanzada de fiabilidad

El framework incluye una amplia suite de tests automatizados para
entornos difíciles:

- **Manifold Testing**: valida la topología matemática del espacio
  vectorial de intents NLP.
- **Chaos Engineering**: simula degradación de bits, fallo de tarjeta SD
  y corrupción del almacenamiento.
- **Temporal Drift**: verifica la resiliencia ante saltos del reloj del
  sistema (±1 año).
- **Leak Detection**: seguimiento a largo plazo de memoria, descriptores
  de archivo e hilos.

## Permisos

Sistema de permisos para controlar el acceso a las funciones del bot:

``` python
from lxmfy import DefaultPerms

@bot.command(name="admin", description="Admin command", admin_only=True)
def admin_command(ctx):
    if ctx.is_admin:
        ctx.reply("Admin command executed")
```

Actívalo con `permissions_enabled=True`. Flags de
`DefaultPerms`:

- `USE_BOT`, `SEND_MESSAGES`, `USE_COMMANDS`: acceso básico
- `MANAGE_MESSAGES`, `MANAGE_COMMANDS`, `MANAGE_USERS`: elevado
- `BYPASS_RATELIMIT`, `BYPASS_SPAM`, `VIEW_ADMIN_COMMANDS`: especial
- `VIEW_EVENTS`, `MANAGE_EVENTS`, `BYPASS_EVENT_CHECKS`: sistema de
  eventos
- `NONE`, `ALL`: atajos

`bot.permissions` gestiona roles y asignaciones:

``` python
bot.permissions.create_role("moderator", DefaultPerms.MANAGE_MESSAGES | DefaultPerms.BYPASS_SPAM)
bot.permissions.assign_role(user_hash, "moderator")
bot.permissions.remove_role(user_hash, "moderator")
bot.permissions.has_permission(user_hash, DefaultPerms.USE_COMMANDS)
```

Roles y asignaciones persisten en el backend configurado. Existen dos
roles integrados que no se pueden borrar: `user` (por defecto) y
`admin`, que se otorga automáticamente a cada hash en `admins`.

## Middleware

Sistema de middleware para procesar mensajes y eventos:

``` python
from lxmfy import MiddlewareType

@bot.middleware.register(MiddlewareType.PRE_COMMAND)
def pre_command_middleware(ctx):
    # ctx envuelve el contexto del mensaje, ctx.cancelled lo descarta
    if "spamword" in ctx.data.content:
        ctx.cancel()
```

Tres puntos de la pipeline ejecutan middleware:

- `PRE_COMMAND`: antes del dispatch de comandos, tras las
  comprobaciones de spam. Si la cadena devuelve `None`, el mensaje se
  aborta por completo.
- `POST_COMMAND`: después del callback de un comando (incluidos los
  comandos en hilo, que lo disparan en el hilo de trabajo).
- `PRE_EVENT`: antes del dispatch del evento `message_received`.

`POST_EVENT`, `REQUEST` y `RESPONSE` existen en `MiddlewareType`,
pero nada en la pipeline los ejecuta todavía.

## Adjuntos

Soporte para enviar archivos, imágenes y audio:

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

## Icono de apariencia (campo LXMF)

Puedes definir un icono personalizado para tu bot que los clientes LXMF
compatibles pueden mostrar. Usa el campo `LXMF.FIELD_ICON_APPEARANCE`.

``` python
from lxmfy import IconAppearance, pack_icon_appearance_field
import LXMF # Necesario para LXMF.FIELD_ICON_APPEARANCE

# Definir la apariencia del icono
icon_data = IconAppearance(
    icon_name="smart_toy",  # Nombre de Material Symbols
    fg_color=b'\xFF\xFF\xFF',  # Primer plano blanco (3 bytes)
    bg_color=b'\x4A\x90\xE2'   # Fondo azul (3 bytes)
)

# Empaquetarlo en el formato de campo LXMF
icon_lxmf_field = pack_icon_appearance_field(icon_data)

# Enviar un mensaje con este icono
bot.send(
    destination_hash_str,
    "Hello from your friendly bot!",
    title="Bot Message",
    lxmf_fields=icon_lxmf_field
)

# También puedes combinarlo con otros campos, como adjuntos:
# attachment_field = pack_attachment(some_attachment)
# combined_fields = {**icon_lxmf_field, **attachment_field}
# bot.send(destination, "Message with icon and attachment", lxmf_fields=combined_fields)
```

## Scheduler

Sistema de planificación de tareas:

``` python
@bot.scheduler.schedule(name="daily_task", cron_expr="0 0 * * *")
def daily_task():
    # Se ejecuta cada día a medianoche
    pass
```

## Firmas

LXMFy ofrece opciones de configuración para la firma y verificación
criptográfica de mensajes integrada en LXMF:

``` python
from lxmfy import LXMFBot

bot = LXMFBot(
    name="SecureBot",
    signature_verification_enabled=True,  # Activar la comprobación de firmas
    require_message_signatures=False      # Poner a True para rechazar mensajes sin firmar
)
```

!!! note "Gestión de firmas"

    LXMF gestiona automáticamente toda la firma y verificación
    criptográfica usando identidades RNS. El `SignatureManager` de
    LXMFy es una capa de configuración que:

    - Controla si se aplica la verificación de firmas
    - Determina la política para mensajes sin firmar (aceptar o
      rechazar)
    - Se integra con el sistema de permisos (p. ej., omitir la
      verificación para usuarios de confianza)

Las operaciones criptográficas reales las realiza LXMF/RNS, no LXMFy.

### Sandbox Landlock LSM

En kernels de Linux con soporte de Landlock (5.13+), LXMFy puede
restringir el acceso al sistema de archivos del proceso del bot y de los
cogs de scripts externos.

**Sandbox del proceso del bot**

Cuando `landlock_enabled=True` (por defecto) y no se ejecuta en
`test_mode`, el bot llama a `apply_landlock_sandbox()` durante la
inicialización. Los directorios del sistema quedan de solo lectura. El
almacenamiento del bot, la configuración, los cogs, la configuración de
Reticulum y las rutas temporales siguen siendo escribibles.

``` python
bot = LXMFBot(
    name="SecureBot",
    landlock_enabled=True,
)

status = bot.get_landlock_status()
# claves de status: landlock_kernel_supported, landlock_requested,
# landlock_auto_enabled, landlock_disabled_by_env, landlock_active
```

**Anulación por entorno**

- `LXMFY_LANDLOCK=0`: desactiva Landlock incluso en kernels compatibles
- `LXMFY_LANDLOCK=1`: intenta Landlock en Linux con independencia de la
  autodetección
- sin definir: sigue `landlock_enabled` y la autodetección del kernel

**Sandbox de cogs externos**

Los cogs de scripts usan `external_cogs_sandbox_type`. En modo `auto` se
prefiere Landlock cuando está disponible porque no requiere herramientas
externas. Consulta la guía [Creación de bots](creating-bots.md) para la
lista completa de opciones de sandbox.

### Identity pinning

LXMFy admite identity pinning opcional para evitar la suplantación si
una identidad rota o se ve comprometida. Cuando está activado, el bot
"fija" una dirección LXMF a la primera clave pública vista.

``` python
bot = LXMFBot(
    identity_pinning_enabled=True
)
```

### Métodos de SignatureManager

El `SignatureManager` está disponible como `bot.signature_manager`
cuando `signature_verification_enabled=True`:

- `should_verify_message(sender)`: determina si un mensaje del remitente
  dado debe verificarse
- `handle_unsigned_message(sender, message_hash)`: gestiona los mensajes
  sin firmas válidas según la política

### Cómo funcionan las firmas LXMF

LXMF firma automáticamente todos los mensajes salientes usando la
identidad RNS del remitente durante la operación `pack()`. Al recibir
mensajes, LXMF valida las firmas y proporciona:

- `message.signature_validated`: booleano que indica si la firma es
  válida
- `message.unverified_reason`: código de motivo si la validación falló
  (p. ej., `SIGNATURE_INVALID`, `SOURCE_UNKNOWN`)

LXMFy usa estas propiedades integradas de LXMF para aplicar la política
de firmas de tu bot.

## Entrega de mensajes

LXMFy ofrece funciones avanzadas de entrega de mensajes, incluidos nodos
de propagación y reintentos automáticos:

### Nodos de propagación

Envía mensajes a través de nodos de propagación concretos para mejorar
la fiabilidad en la red Reticulum:

``` python
# Configurar el nodo de propagación una vez a nivel de config/ejecución
bot.set_propagation_node("<propagation_node_hash>")

# Enviar usando el comportamiento de entrega configurado
bot.send(
    destination_hash,
    "Message content"
)

# El hash del nodo de propagación debe ser un nodo de propagación LXMF
# válido en la red Reticulum
```

También puedes fijar el nodo en la construcción con
`propagation_node="<hash>"`, o dejar que el bot descubra nodos por sí
mismo:

``` python
bot = LXMFBot(
    name="AutoBot",
    autopeer_propagation=True, # aprende nodos desde announces
    autopeer_maxdepth=4,       # ignora nodos a más de 4 saltos
)
```

`bot.get_propagation_node_status()` informa del nodo manual, los nodos
descubiertos y el nodo saliente actualmente en uso.

### Reintentos automáticos

Configura los reintentos automáticos para las entregas directas
fallidas:

``` python
bot = LXMFBot(
    name="ReliableBot",
    direct_delivery_retries=5,  # Reintentar la entrega directa hasta 5 veces
    propagation_fallback_enabled=True
)

bot.send(destination_hash, "Important message")

# direct_delivery_retries por defecto es 3
# La lógica de reintento gestiona automáticamente los callbacks de entrega
```

El sistema de reintentos registra los intentos de entrega por destino y
reintenta automáticamente las entregas fallidas. Las entregas correctas
reinician el contador de reintentos de ese destino.

### Envíos diferidos

Enviar a un destino cuya identidad el nodo aún no ha oído suele fallar
directamente. Con `pending_sends_enabled` (por defecto) el mensaje se
retiene en almacenamiento y se vacía automáticamente cuando el destino
anuncia o en un barrido periódico.

``` python
bot = LXMFBot(
    pending_sends_enabled=True,
    pending_sends_max=200,     # los mensajes retenidos más antiguos caen más allá de esto
    pending_sends_ttl=604800,  # los mensajes retenidos caducan a los 7 días
    pending_sends_retry=300,   # segundos entre barridos en run()
)

# Sobrescritura por envío
bot.send(dest, "hold this", defer=True)
bot.send(dest, "send or drop", defer=False)
```

Los envíos retenidos aparecen como `held (unknown peers)` en el
comando admin `/queue` y producen eventos `deferred` en el tracker de
entrega.

### Persistencia de mensajes

Los mensajes salientes se pueden persistir en disco para garantizar su
entrega incluso tras un reinicio del bot. La persistencia está activada
por defecto. La cola de salida en memoria está limitada
(`message_queue_size`, 50 por defecto) y descarta el mensaje más antiguo
cuando se llena. Los hashes de destino inválidos no se restauran.

``` python
bot = LXMFBot(
    message_persistence_enabled=True,
    message_queue_size=50,
)
```

### Stamps y tickets

Los costes de stamp hacen que los remitentes paguen proof-of-work
antes de que su mensaje sea aceptado, lo que frena el tráfico no
solicitado. LXMFy expone ambos lados del mecanismo.

``` python
bot = LXMFBot(
    stamp_cost=16,          # exige este coste de stamp entrante
    require_stamps=True,    # rechaza mensajes con stamps inválidos
    include_tickets=True,   # deja que los peers respondan sin generar un stamp
)
```

- `stamp_cost` es el requisito entrante. El coste saliente de un envío
  sigue saliendo del announce del peer salvo que pases `stamp_cost=`
  a `bot.send()`.
- `include_tickets` (por defecto True) adjunta un ticket de respuesta
  a los mensajes salientes, para que un peer que exige stamps pueda
  contestar sin pagar. Sobrescríbelo por envío con `include_ticket=`.
- `request_unknown_identities=True` pide a la red una identidad de
  remitente cuando llega un mensaje de origen desconocido, ayudando a
  que las comprobaciones de stamps y firmas resuelvan en lugar de
  fallar a ciegas.

El control en tiempo de ejecución está en [Controles del
router](#controles-del-router): `set_inbound_stamp_cost`,
`enforce_stamps`, `ignore_stamps`, `generate_ticket` y los métodos de
inspección de tickets.

### Operar como nodo de propagación

Un bot puede hacer también de nodo de propagación LXMF, almacenando
mensajes para peers que están offline:

``` python
bot = LXMFBot(
    enable_propagation_node=True,
    message_storage_limit_mb=500,
)

bot.set_message_storage_limit(750)
stats = bot.get_propagation_storage_stats()
```

`get_propagation_node_status()` sirve para ambos roles: informa del
nodo saliente que usa este bot y de si él mismo actúa como nodo.
Controles relacionados: `announce_propagation_node()` anuncia el nodo,
`set_retain_on_node()` conserva los mensajes entregados en él, y
`allow_control_identity()` / `disallow_control_identity()` gestionan
qué identidades pueden usar el canal de control del nodo.

### Eventos de entrega

`bot.delivery` registra un flujo acotado de eventos del ciclo de vida
saliente para observar el flujo de mensajes sin leer logs. Fases:
`queued`, `deferred`, `dispatched`, `delivered`, `failed`,
`cancelled`, `dropped`. La cola reciente se persiste en almacenamiento
y se restaura al arrancar.

``` python
@bot.on_delivery_event()
def watch(event):
    print(event["stage"], event.get("destination"), event.get("reason"))

# O inspección directa
recent = bot.delivery.recent(20)
failures = bot.delivery.recent(stage="failed")
to_peer = bot.delivery.recent(destination="aa11bb...")
```

Cada evento es un dict con `ts`, `stage` y, opcionalmente,
`destination`, `message_id`, `hash`, `method`, `attempts`, `reason`,
`title`.

Los admins disponen de un comando `/delivery [limit]` que renderiza la
misma línea temporal en el chat, y `lxmfy debug` muestra un resumen de
la línea temporal de entregas en las comprobaciones de la pipeline de
envío.

### Comandos de administración integrados

Estos comandos se registran automáticamente y exigen que el remitente
esté en `admins` cuando los permisos están activados:

| Comando | Acción |
| --- | --- |
| `/queue` | Muestra la cola saliente del router, la cola interna y los envíos retenidos |
| `/cancel <id|all>` | Cancela mensajes salientes pendientes |
| `/inbox [cancel <hash|all>]` | Lista o cancela transferencias entrantes activas |
| `/delivery [n]` | Muestra los últimos n eventos de entrega (por defecto 15, máx. 50) |
| `/loadext <name>` | Carga una extensión cog |
| `/reloadext <name>` | Recarga una extensión cog cargada |

### Controles del router

Wrappers finos sobre el `LXMRouter` subyacente para control de
remitentes, tickets, gestión de la cola saliente y sincronización del
nodo de propagación. Todos toman hashes de destino como strings hex y
devuelven `False` cuando el router no está corriendo (por ejemplo en
`test_mode`).

**Control de remitentes (entrante)**

- `ignore_destination(destination)` / `unignore_destination(destination)` / `is_ignored(destination)`:
  Descarta mensajes entrantes de un remitente
- `allow_destination(destination)` / `disallow_destination(destination)`:
  Gestión de whitelist cuando el router corre en modo allow-list
- `prioritise_destination(destination)` / `unprioritise_destination(destination)`:
  Lista de remitentes priorizados
- `set_inbound_stamp_cost(stamp_cost)`: Exige un coste de stamp en
  mensajes entrantes (`None` lo borra)
- `enforce_stamps()` / `ignore_stamps()`: Conmutadores de exigencia de
  stamps entrantes

**Tickets**

- `generate_ticket(destination, expiry=None)`: Emite un ticket de
  stamp entrante para un remitente
- `get_inbound_tickets(destination)`: Tickets retenidos para un
  remitente
- `get_outbound_ticket(destination)` / `get_outbound_ticket_expiry(destination)` /
  `get_outbound_stamp_cost(destination)`: Estado del ticket saliente
  aprendido de la red

**Cola saliente**

- `outbound_queue()`: Snapshot de mensajes salientes pendientes
- `get_outbound_progress(lxm_hash)`: Progreso de entrega de un hash de
  mensaje, o `None`
- `cancel_outbound(message_id)`: Quita un mensaje en cola antes de la
  entrega
- `delivery_link_available(destination)`: Si existe un enlace RNS
  activo al destino

**Cola entrante**

- `has_message(message_hash)`: Si un hash LXM entrante ya fue entregado
- `inbound_count()`: Transferencias entrantes de recursos activas en
  curso
- `inbound_transfers()`: Snapshot de cada transferencia con hash,
  tamaño, progreso y estado
- `cancel_inbound(resource_hash)`: Aborta una transferencia entrante
  activa
- `cancel_all_inbound()`: Aborta todas las transferencias entrantes
  activas, devuelve la cuenta cancelada

**Descubrimiento de peers**

Metadatos de announce de destinos que este nodo ha oído:

- `get_peer_app_data(destination)`: Bytes app_data anunciados en crudo
- `get_peer_lxmf_data(destination)`: Metadatos de announce LXMF
  decodificados (`display_name`, `stamp_cost`, `capabilities`), o
  `None` cuando el peer no ha anunciado datos LXMF válidos
- `get_peer_announce(destination)`: Registro de announce completo con
  hops, received_at, interface y app_data
- `list_peer_announces(limit=100)`: Todos los announces oídos, el más
  reciente primero

**Propagación**

- `sync_propagation_node(max_messages=None)`: Trae mensajes del nodo
  de propagación configurado
- `cancel_propagation_sync()`: Detiene una sincronización en curso
- `get_propagation_stats()`: Estado de transferencia y límites del
  nodo, o `None`
- `set_retain_on_node(retain)`: Conserva los mensajes entregados en el
  nodo
- `announce_propagation_node()`: Anuncia este nodo como nodo de
  propagación
- `allow_control_identity(destination)` / `disallow_control_identity(destination)`:
  Whitelist del canal de control de propagación

**Ingesta**

- `ingest_lxm_uri(uri)`: Importa un mensaje URI `lxm://` a la cola
  entrante

## Diagnóstico

Cuando los mensajes no fluyen, el depurador comprueba todo el camino
en lugar de adivinar: configuración de Reticulum, estado de la
instancia compartida, interfaces, identidad, comportamiento de
announce, configuración de entrega y la pipeline de envío.

``` bash
lxmfy debug                          # informe doctor completo, guardado en archivo
lxmfy debug probe <hash> --request-path --wait 30
lxmfy debug send <hash>              # traza un envío de prueba
lxmfy debug receive                  # comprueba la disponibilidad de recepción
lxmfy debug compare <hash_a> <hash_b>
lxmfy debug tips                     # correcciones de fallos comunes
```

Los informes se redactan por privacidad por defecto: las rutas home y
los hashes se truncan. `--json` emite salida legible por máquina,
`-o ARCHIVO` escribe el informe, `--no-save` omite el archivo,
`--no-privacy` conserva los valores completos para uso local, y
`--no-color` o `NO_COLOR` desactiva la salida ANSI.

Las mismas comprobaciones se pueden llamar desde código:

``` python
report = bot.diagnose_connectivity()            # informe doctor como dict
probe = bot.diagnose_destination(               # sondeo de identidad y ruta
    "<peer_hash>", request_path=True, wait=30,
)

debugger = bot.get_debugger()                   # API completa
checks = debugger.check_send_pipeline()
verdict = debugger.run_doctor(destination)
```

`lxmfy/debugger.py` también exporta un helper independiente
`diagnose_destination(hash, ...)` más los tipos de informe
`CheckResult`, `DestinationProbe`, `DoctorReport` y `MessageDebugger`
para herramientas propias.

## Manejadores de mensajes

LXMFy ofrece decoradores para manejar distintos tipos de mensajes
entrantes:

### Manejador del primer mensaje

Maneja el primer mensaje de cada usuario:

``` python
@bot.on_first_message()
def welcome_user(sender, message):
    content = message.content.decode("utf-8")
    bot.send(sender, f"Welcome! You said: {content}")
    return True  # Devolver True para detener el procesamiento
```

### Manejador general de mensajes

Maneja todos los mensajes entrantes antes del procesamiento de comandos:

``` python
@bot.on_message()
def handle_all_messages(sender, message):
    content = message.content.decode("utf-8").strip()

    # Lógica personalizada aquí
    if content.startswith("echo:"):
        bot.send(sender, content[5:])
        return True  # Detener el procesamiento

    return False  # Continuar al procesamiento de comandos
```

Los manejadores de mensajes se llaman en este orden: 1. Manejador del
primer mensaje (si es el primer mensaje de este remitente) 2.
Manejadores generales de mensajes (registrados con `on_message()`) 3.
Procesamiento de comandos (si el mensaje empieza por el prefijo de
comandos)

### Callback de reserva

`bot.received(fn)` registra un callback que corre al final de la
pipeline para mensajes que nada más consumió: ningún manejador de
primer mensaje, ningún manejador `on_message` que devolviera True,
ningún comando o intent NLP coincidente. El callback recibe el mismo
contexto de mensaje que los comandos, con `msg.sender`, `msg.content`,
`msg.reply()` y demás.

``` python
@bot.received
def fallback(msg):
    msg.reply("Sorry, I did not understand that.")
```

Úsalo como comodín para entrada de texto libre.

## Reticulum Relay Chat (RRC)

Los bots pueden unirse a hubs de [RRC](https://rrc.kc1awv.net/) sobre
RNS Links con sobres CBOR. Paquete: `lxmfy.rrc`.

### Opciones de BotConfig

- `rrc_enabled` (bool, por defecto `False`): conectar los hubs
  configurados al arrancar
- `rrc_hubs` (lista de hashes en hex): hashes de destino de los hubs
- `rrc_rooms` (lista de str): salas a las que unirse tras WELCOME
- `rrc_nick` (str o None): nick en HELLO y mensajes de sala
- `rrc_dest_name` (str, por defecto `"rrc.hub"`): nombre de destino
  usado para construir el destino del hub
- `rrc_auto_reconnect` (bool, por defecto `True`): reconectar tras la
  pérdida del link
- `rrc_persist_sessions` (bool, por defecto `True`): persistir hubs y
  salas entre reinicios
- `reticulum_config_dir` (str o None): directorio de configuración de
  Reticulum. También se define con `LXMFY_RETICULUM_CONFIG_DIR`. Usa la
  misma configuración que MeshChatX (a menudo `~/.reticulum`) para que
  los anuncios del hub sean visibles.

### Ejemplo

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

# API en tiempo de ejecución
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

- `RRCClient`: sesión de un solo hub
- `RRCManager`: gestor multi-hub (`bot.rrc`)
- `RRCMessage`: payload de evento de sala (`kind`, `room`, `text`,
  `nick`, `src`, `mention`, ...)
- `RRC_VERSION`: constante de versión del protocolo de red
- `DEFAULT_DEST_NAME`: Nombre de destino de hub por defecto
  (`"rrc.hub"`)
- `make_envelope`, `encode_envelope`, `decode_envelope`,
  `validate_envelope`, `normalize_room`: Helpers de formato wire para
  herramientas que hablan directamente con hubs

Los eventos habituales que reciben los manejadores de `@bot.on_rrc`
incluyen `status`, `welcome`, `joined`, `parted`, `msg`, `notice`,
`action`, `motd`, `error` y `rtt`.

# Plantillas

El framework incluye varias plantillas de bot listas para usar:

## EchoBot

Bot eco sencillo que repite los mensajes:

``` python
from lxmfy.templates import EchoBot

bot = EchoBot()
bot.run()
```

## NoteBot

Bot de notas con almacenamiento JSON:

``` python
from lxmfy.templates import NoteBot

bot = NoteBot()
bot.run()
```

## ReminderBot

Bot de recordatorios con almacenamiento SQLite:

``` python
from lxmfy.templates import ReminderBot

bot = ReminderBot()
bot.run()
```

## RRCBot

Bot de sala RRC que se une a los hubs configurados y responde a las
`@menciones`. Usa por defecto el hub
`664fc0e8d2e448658e37bb3f34e6c88f`, la sala `#general` y `~/.reticulum`
cuando está disponible.

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

# Herramientas CLI

El framework ofrece herramientas de línea de comandos para la gestión
de bots. Ejecutar `lxmfy` sin argumentos abre un menú interactivo.

``` bash
# Scaffold interactivo de un proyecto completo
lxmfy init mybot                 # directorio del proyecto, bot.py, cogs/, README
lxmfy init --here --yes          # directorio actual, acepta todos los defaults

# Crear un único archivo de bot
lxmfy create mybot
lxmfy create --template echo mybot
lxmfy create --template rrc my_rrc_bot
lxmfy create mybot --no-cogs     # omite el paquete de cogs
lxmfy create --output dir/bot.py --name MyBot

# Ejecutar un bot de plantilla
lxmfy run echo
lxmfy run rrc
lxmfy run reminder --name "MyReminder"

# Diagnosticar conectividad (ver la sección Diagnóstico)
lxmfy debug
lxmfy debug probe <hash> --request-path --wait 30

# Probar la verificación de firmas con un mensaje
lxmfy signatures test

# Activar la verificación de firmas
lxmfy signatures enable

# Desactivar la verificación de firmas
lxmfy signatures disable
```

`lxmfy init` pregunta por nombre de proyecto, plantilla, backend de
almacenamiento, prefijo de comandos y hashes de admin. Cada pregunta
acepta un flag en su lugar: `--dir`, `--bot-name`, `--template`,
`--storage`, `--prefix`, `--admins`, `--no-cogs`, `--force`, `--yes`.
Con stdin no-TTY toma los defaults.

Plantillas para `create` y `run`: `basic`, `echo`, `reminder`, `note`,
`cogtest`, `rrc`.

# Manejo de errores

Captura los fallos de apagado y de ejecución alrededor de `bot.run()`:

``` python
try:
    bot.run()
except KeyboardInterrupt:
    bot.cleanup()
except Exception as e:
    logger.error(f"Error running bot: {str(e)}")
```

# Referencia de módulos

Generada a partir de los docstrings del código fuente.

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
