# Creación de bots

## Estructura básica

Un bot mínimo de LXMFy implica:

1.  Importar `LXMFBot`.
2.  Instanciar `LXMFBot` con la configuración deseada.
3.  Definir comandos o manejadores de eventos.
4.  Ejecutar el bot con `bot.run()`.

``` python
from lxmfy import LXMFBot

# 1. Instanciar el bot
bot = LXMFBot(
    name="SimpleBot",
    command_prefix="!",
    storage_path="simple_data"
)

# 2. Definir comandos
@bot.command(name="ping", description="Responds with pong")
def ping_command(ctx):
    # ctx es un objeto de contexto con información del mensaje
    # ctx.sender: hash LXMF del remitente
    # ctx.content: contenido completo del mensaje
    # ctx.args: lista de argumentos tras el comando
    # ctx.reply(message): función para enviar una respuesta
    #   (también acepta argumentos con nombre como title="My Title", lxmf_fields=some_fields)
    ctx.reply("Pong!")

# Para tareas de larga duración puedes usar comandos en hilos:
# import time
# @bot.command(name="long_op", description="Performs a long operation in a separate thread", threaded=True)
# def long_op_command(ctx):
#     ctx.reply("Starting long operation...")
#     time.sleep(10) # Simula una operación de larga duración
#     ctx.reply("Long operation complete!")
# Importante: los comandos en hilos no deben interactuar directamente con RNS ni con lxmfy.transport.py.

@bot.command(name="greet", description="Greets the user")
def greet_command(ctx):
    if ctx.args:
        name = " ".join(ctx.args)
        ctx.reply(f"Hello, {name}!")
    else:
        ctx.reply("Hello there! Tell me your name: !greet <your_name>")

# 3. Ejecutar el bot
if __name__ == "__main__":
    print(f"Starting bot: {bot.config.name}")
    print(f"Bot LXMF Address: {bot.local.hash}")
    bot.run()
```

## Uso de plantillas

LXMFy incluye varias plantillas para tipos de bot habituales. Puedes
usar la CLI para generar un archivo de bot basado en una plantilla.

Para un directorio de proyecto completo en lugar de un solo
archivo, `lxmfy init` genera `bot.py`, un paquete `cogs`, un README y
un `.gitignore`, preguntando por plantilla, backend de almacenamiento,
prefijo de comandos y hashes de admin por el camino.

``` bash
# Crear un bot eco
lxmfy create --template echo my_echo_bot

# Crear un bot de recordatorios (usa almacenamiento SQLite)
lxmfy create --template reminder my_reminder_bot

# Crear un bot de notas (usa almacenamiento JSON)
lxmfy create --template note my_note_bot

# Crear un bot de prueba de cogs (prueba las funciones de carga de cogs)
lxmfy create --template cogtest my_cog_test_bot

# Crear un bot de sala RRC (se une a hubs y responde a @menciones)
lxmfy create --template rrc my_rrc_bot

# O ejecutar la plantilla directamente
lxmfy run rrc
```

Al ejecutar estos comandos se crea un archivo de Python (p. ej.,
`my_echo_bot.py`) que importa y ejecuta la plantilla elegida. Después
puedes modificar el archivo generado o el propio código de la plantilla
(`lxmfy/templates/...`).

**Ejemplo de archivo generado (`my_cog_test_bot.py`):**

``` python
from lxmfy.templates import CogTestBot

if __name__ == "__main__":
    bot = CogTestBot() # Crea una instancia de la plantilla CogTestBot
    # Opcionalmente puedes cambiar el nombre por defecto:
    # bot.bot.name = "My Cog Test Bot"
    bot.run()
```

## Configuración del bot

Al crear una instancia de `LXMFBot` puedes pasar varios argumentos con
nombre para configurar su comportamiento. Consulta la sección
`BotConfig` en la [Referencia de API](api-reference.md) o la [Guía de
inicio rápido](quick-start.md) para ver la lista de opciones habituales.

``` python
from lxmfy import LXMFBot

bot = LXMFBot(
    name="ConfiguredBot",
    announce=3600, # Anunciar cada hora
    admins={"your_admin_hash_here"}, # Definir administrador(es)
    command_prefix="$", # Usar '$' como prefijo
    storage_type="sqlite", # Usar base de datos SQLite
    storage_path="data/my_bot_data.db", # Ruta del archivo de la base de datos
    rate_limit=10, # Permitir 10 mensajes / minuto
    cooldown=30, # Enfriamiento de 30 segundos
    permissions_enabled=True # Activar permisos por roles
)

if __name__ == "__main__":
    # También puedes modificar la configuración tras la instanciación
    # Nota: algunos ajustes conviene definirlos en el init
    bot.config.max_warnings = 5
    bot.spam_protection.config.max_warnings = 5 # Actualizar también el protector de spam

    bot.run()
```

### Definir un icono del bot (campo LXMF)

Puedes darle a tu bot un icono personalizado que aparece en los clientes
LXMF compatibles. Usa el campo `LXMF.FIELD_ICON_APPEARANCE` y se puede
establecer al enviar mensajes.

Primero, asegúrate de tener los imports necesarios:

``` python
from lxmfy import IconAppearance, pack_icon_appearance_field
```

Después puedes definir y usar el icono:

``` python
# En tu clase de bot o en la configuración
icon_data = IconAppearance(
    icon_name="robot_2",  # Elegir de Material Symbols
    fg_color=b'\x00\xFF\x00',  # Verde
    bg_color=b'\x33\x33\x33'   # Gris oscuro
)
self.bot_icon_field = pack_icon_appearance_field(icon_data)

# Al enviar un mensaje o responder:
ctx.reply("Message from your bot!", lxmf_fields=self.bot_icon_field)
# o
# bot.send(destination, "Another message", lxmf_fields=self.bot_icon_field)
```

Este `self.bot_icon_field` se puede calcular una vez y reutilizar en
todos los mensajes que envíe el bot.

## Comandos estructurados mediante campos LXMF

Además de los comandos de texto, LXMFy admite comandos enviados a través
de los campos de mensaje LXMF usando `FIELD_COMMANDS` (`0x09`). Esto es
útil para flujos de petición/respuesta estructurados entre clientes LXMF
y bots.

Cuando un mensaje contiene `FIELD_COMMANDS`, el bot extrae el nombre del
comando y los argumentos, los dirige por el mismo registro de comandos
que los comandos de texto e incluye automáticamente `FIELD_RESULTS`
(`0x0A`) en la respuesta.

**Recepción de comandos estructurados**

``` python
from lxmfy import LXMFBot

bot = LXMFBot(name="FieldBot")

@bot.command(name="add", description="Add two numbers")
def add_command(ctx):
    if len(ctx.args) >= 2:
        try:
            result = float(ctx.args[0]) + float(ctx.args[1])
            ctx.reply(str(result))
        except ValueError:
            ctx.reply("Invalid numbers")
    else:
        ctx.reply("Usage: add <a> <b>")
```

El objeto `ctx` en los callbacks de comandos de campo incluye:

- `ctx.fields`: el dict de campos LXMF en bruto del mensaje entrante
- `ctx.request_id`: el `request_id` del `FIELD_COMMANDS` entrante (si lo
  hay)

**Envío de un comando estructurado desde un cliente LXMF**

``` python
import LXMF
from lxmfy import FIELD_COMMANDS

lxm = LXMF.LXMessage(
    destination,
    source,
    b"",  # el contenido puede estar vacío en comandos solo de campos
    desired_method=LXMF.LXMessage.DIRECT,
)
lxm.fields[FIELD_COMMANDS] = {
    "command": "add",
    "args": ["3", "5"],
    "request_id": "req-42",  # opcional, para correlación
}
router.handle_outbound(lxm)
```

**Desactivar los comandos de campo**

Si quieres que el bot ignore `FIELD_COMMANDS` y solo procese comandos de
texto, define:

``` python
bot = LXMFBot(
    name="TextOnlyBot",
    lxmf_commands_enabled=False,
)
```

## Uso de cogs (extensiones)

Los cogs permiten organizar los comandos y los listeners de eventos en
archivos separados (módulos), manteniendo más limpio el archivo
principal del bot.

1.  **Crea un directorio `cogs`** (o el que hayas puesto en `cogs_dir`
    de `BotConfig`).
2.  **Crea archivos de Python** dentro del directorio `cogs` (p. ej.,
    `utility.py`).
3.  **Define una clase** que herede de `lxmfy.Cog` (opcional pero
    recomendable) o simplemente una clase estándar.
4.  **Define comandos** como métodos de la clase usando el decorador
    `@Command`.
5.  **Crea una función `setup(bot)`** en el archivo del cog, que LXMFy
    llamará para registrar el cog.

**Ejemplo (`cogs/utility.py`):**

``` python
from lxmfy import Command
from lxmfy.commands import Cog  # Importar Cog si se hereda de él
import time

class UtilityCog: # O class UtilityCog(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = time.time()

    @Command(name="uptime", description="Shows bot uptime")
    # Nota: los métodos de los cogs suelen recibir 'self' y 'ctx'
    def uptime_command(self, ctx):
        uptime_seconds = time.time() - self.start_time
        ctx.reply(f"Bot has been running for {uptime_seconds:.2f} seconds.")

    @Command(name="info", description="Shows bot info")
    def info_command(self, ctx):
        info = (
            f"Bot Name: {self.bot.config.name}\n"
            f"Owner(s): {', '.join(self.bot.config.admins) or 'None'}\n"
            f"Prefix: {self.bot.config.command_prefix}"
        )
        ctx.reply(info)

    @Command(name="threaded_cog_task", description="Performs a long task in a cog thread", threaded=True)
    def threaded_cog_task(self, ctx):
        ctx.reply("Starting a long cog task... this will run in a separate thread.")
        time.sleep(7) # Simula una operación de larga duración
        ctx.reply("Long cog task completed!")

# Esta función es necesaria para que el cog se cargue
def setup(bot):
    cog_instance = UtilityCog(bot)
    bot.add_cog(cog_instance) # Registrar la instancia del cog en el bot
```

**Archivo principal del bot (`my_bot.py`):**

``` python
from lxmfy import LXMFBot

bot = LXMFBot(
    name="CogBot",
    cogs_enabled=True, # Asegurarse de que los cogs están activados (por defecto)
    cogs_dir="cogs" # Apuntar al directorio
)

if __name__ == "__main__":
    # Los cogs se cargan automáticamente durante la inicialización de LXMFBot
    # si cogs_enabled es True.
    bot.run()
```

Cuando el bot arranca, encontrará automáticamente `utility.py`, llamará
a su función `setup`, que crea una instancia de `UtilityCog` y la
registra con `bot.add_cog()`. Los comandos definidos en el cog
(`uptime`, `info`) quedarán disponibles.

## Cogs de scripts externos (soporte multilenguaje)

También puedes escribir extensiones del bot en lenguajes distintos de
Python (p. ej., Bash, Ruby, Perl, Go, C) usando cogs de scripts
externos.

1.  **Crea un script ejecutable** en tu directorio `cogs`.
2.  **Añade un shebang** al principio del script (p. ej.,
    `#!/bin/bash`).
3.  **Asegúrate de que el script es ejecutable** (`chmod +x
    tu_script`).

Cuando el bot arranca, registrará automáticamente cualquier archivo
ejecutable del directorio `cogs` (que no termine en `.py`) como comando
del bot.

**Protocolo de argumentos:**

- `$1`: hash LXMF del remitente.
- `$2`: contenido completo del mensaje.
- `$3`, `$4`, ...: argumentos individuales del comando.

**Variables de entorno:**

- `LXMFY_SENDER`: hash de identidad del remitente.
- `LXMFY_CONTENT`: contenido completo del mensaje.
- `LXMFY_HAS_ADMIN`: `true` o `false` según el estado de administrador
  del remitente.

**Ejemplo de cog en Bash (`cogs/greet.sh`):**

``` bash
#!/bin/bash
echo "Hello from Bash! You sent: $2"
```

Cuando un usuario envía `/greet hello`, el bot ejecutará este script y
responderá con su stdout: `Hello from Bash! You sent: /greet hello`.

## Clasificación local de intenciones con NLP

LXMFy incluye un clasificador de intenciones local. Compara el texto del
mensaje con frases de ejemplo etiquetadas cuando el texto no coincide
exactamente con un prefijo de comando.

1.  **Activa NLP** en la configuración del bot: `nlp_enabled=True`.
2.  **Define intents** con el decorador `@bot.intent`.

``` python
@bot.intent("help", examples=["how do I use this?", "show me commands", "help me please"])
def help_intent(msg):
    msg.reply("I can help! Try typing /help to see a list of commands.")
```

La coincidencia usa vectores TF-IDF y similitud del coseno. Toda la
puntuación se calcula en el host del bot. No se envía texto a ninguna
API externa.

**Exportación e importación del modelo**

Exporta e importa un modelo entrenado para que los bots más grandes
eviten reentrenar en cada arranque:

``` python
# Exportar el modelo
model_data = bot.nlp.export_model()
# Guardar model_data en un archivo o base de datos

# Más tarde, importarlo de nuevo
bot.nlp.import_model(model_data)
```

## Soporte de RNS Link

Los bots pueden establecer y responder a RNS Links directos para
tráfico con estado, streaming o mayor ancho de banda que un paquete LXMF
suelto.

1.  **Activa el soporte de Link** en la configuración:
    `link_support_enabled=True`.
2.  **Solicita un link**: `bot.request_link(destination_hash)`. También
    puedes indicar un nombre de app y aspects personalizados:
    `bot.request_link(dest, callback, "my_app", "aspect1")`.
3.  **Gestiona los links entrantes**: registra un callback con
    `bot.on_link(handler)`.

``` python
def handle_link(link):
    print(f"Link established with {RNS.hexrep(link.destination.hash)}")
    # Ahora puedes usar el link para comunicación RNS directa

bot.on_link(handle_link)
```

**Seguridad y sandbox:**

- **Timeouts:** los cogs externos tienen un timeout por defecto (30 s)
  para evitar bloqueos. Se configura con `external_cogs_timeout`.
- **Hilos:** todos los cogs externos se ejecutan en hilos separados y no
  bloquean el bot.
- **Sandbox del proceso del bot (solo Linux):** cuando
  `landlock_enabled=True` (por defecto) y el kernel soporta Landlock LSM
  (5.13+), el bot aplica un sandbox de sistema de archivos a su propio
  proceso tras el arranque. Las rutas escribibles se limitan al
  almacenamiento, la configuración, los cogs, la configuración de
  Reticulum y los directorios temporales. Se anula con la variable de
  entorno `LXMFY_LANDLOCK=0` para desactivarlo o `LXMFY_LANDLOCK=1` para
  forzar el intento.
- **Sandbox de cogs externos (solo Linux):** cuando
  `external_cogs_sandbox_enabled=True` (por defecto), los cogs de
  scripts ejecutables se ejecutan dentro de un entorno restringido.
  Define `external_cogs_sandbox_type` con uno de estos valores:
  - `auto` (por defecto): prefiere Landlock cuando está soportado, si no
    `bubblewrap` (`bwrap`), si no `firejail`
  - `landlock`: sandbox solo con Landlock mediante `preexec_fn` (reglas
    más estrictas que el sandbox del proceso del bot)
  - `bwrap`: sandbox de bubblewrap con bind de solo lectura
  - `firejail`: perfil privado de firejail sin red
  - `none`: sin sandbox para el subproceso
- **Estado:** llama a `bot.get_landlock_status()` para inspeccionar el
  soporte del kernel, si se pidió Landlock y si el sandbox del proceso
  del bot está activo.

## Manejo de mensajes

LXMFy ofrece varias formas de manejar los mensajes entrantes en
distintas fases del procesamiento.

### Manejador del primer mensaje

Maneja el primer mensaje de cada usuario nuevo (útil para mensajes de
bienvenida):

``` python
from lxmfy import LXMFBot

bot = LXMFBot(
    name="WelcomeBot",
    first_message_enabled=True  # Debe ser True (por defecto)
)

@bot.on_first_message()
def welcome_new_user(sender, message):
    content = message.content.decode("utf-8")
    bot.send(
        sender,
        f"Welcome to the bot! You said: {content}\n\n"
        "Type /help to see available commands."
    )
    return True  # Devolver True para detener el procesamiento de este mensaje

if __name__ == "__main__":
    bot.run()
```

### Manejador general de mensajes

Maneja todos los mensajes entrantes antes del procesamiento de comandos:

``` python
from lxmfy import LXMFBot

bot = LXMFBot(name="EchoBot")

@bot.on_message()
def echo_non_commands(sender, message):
    content = message.content.decode("utf-8").strip()

    # Comprobar si es un comando; si lo es, dejar que lo gestione el manejador de comandos
    if content.startswith(bot.config.command_prefix):
        command_name = content.split()[0][len(bot.config.command_prefix):]
        if command_name in bot.commands:
            return False  # Dejar que lo procese el manejador de comandos

    # No es un comando, devolverlo como eco
    bot.send(sender, f"You said: {content}")
    return False  # Devolver False para continuar el procesamiento (aunque no coincidirá ningún comando)

@bot.command(name="hello", description="Say hello")
def hello_command(ctx):
    ctx.reply("Hello! This is a command response.")

if __name__ == "__main__":
    bot.run()
```

Orden de procesamiento de los manejadores de mensajes:

1.  **Manejador del primer mensaje** (si `first_message_enabled=True` y
    es el primer mensaje del remitente)
2.  **Manejadores generales de mensajes** (registrados con
    `@bot.on_message()`)
3.  **Procesamiento de comandos** (si el mensaje coincide con un comando
    registrado)

Los manejadores pueden devolver `True` para detener el procesamiento o
`False` para continuar a la siguiente fase.

## Manejo de eventos

Puedes registrar manejadores para varios eventos del bot con el
decorador `@bot.events.on()`.

``` python
from lxmfy import LXMFBot
from lxmfy.events import EventPriority # Opcional, para prioridad

bot = LXMFBot(name="EventBot")

@bot.events.on("message_received")
def log_message(event):
    # El objeto event contiene los detalles
    sender = event.data.get("sender")
    message_content = event.data.get("message").content.decode('utf-8', errors='ignore')
    print(f"Received message from {sender}: {message_content}")

    # Puedes cancelar el procesamiento del evento (p. ej., detener el manejo del mensaje)
    # if sender == "some_blocked_hash":
    #    event.cancel()

@bot.events.on("command_executed", priority=EventPriority.LOW)
def log_command(event):
    # Ejemplo: event.data puede contener {'command_name': 'ping', 'sender': '...', ...}
    command_name = event.data.get('command_name', 'unknown')
    sender = event.data.get('sender', 'unknown')
    print(f"Command '{command_name}' executed by {sender}")

# También puedes definir eventos personalizados
@bot.command(name="special")
def special_command(ctx):
    ctx.reply("Doing something special!")
    # Emitir un evento personalizado
    bot.events.dispatch(Event("special_action_taken", data={"user": ctx.sender}))

@bot.events.on("special_action_taken")
def handle_special(event):
    user = event.data.get("user")
    print(f"Special action was taken by user: {user}")


if __name__ == "__main__":
    bot.run()
```

Consulta `lxmfy/events.py` para más detalles sobre la estructura `Event`
y las prioridades.

## Almacenamiento

LXMFy ofrece backends de almacenamiento JSON, SQLite, MsgPack y en memoria.

- **JSON:** simple y legible. Adecuado para conjuntos de datos
  pequeños. Se configura con `storage_type="json"` y
  `storage_path="your_data_dir"`.
- **SQLite:** más eficiente para conjuntos de datos grandes o escrituras
  frecuentes. Se configura con `storage_type="sqlite"` y
  `storage_path="your_db_file.db"`.
- **MsgPack:** formato binario compacto con el mismo diseño de un
  archivo por clave que JSON. Se configura con `storage_type="msgpack"`
  y `storage_path="your_data_dir"`.
- **Memory:** almacenamiento íntegramente en RAM. El estado se pierde al
  apagar. Se configura con `storage_type="memory"`.

Puedes acceder a la interfaz de almacenamiento mediante `bot.storage`:

``` python
# Guardar datos
bot.storage.set("user_prefs:" + ctx.sender, {"theme": "dark"})

# Obtener datos (con un valor por defecto)
prefs = bot.storage.get("user_prefs:" + ctx.sender, {})
theme = prefs.get("theme", "light")

# Comprobar si existen datos
if bot.storage.exists("some_key"):
    print("Key exists!")

# Borrar datos
bot.storage.delete("old_data_key")

# Buscar claves con un prefijo (útil para listar datos de usuario)
user_keys = bot.storage.scan("user_prefs:")
for key in user_keys:
    user_data = bot.storage.get(key)
    print(f"Data for {key}: {user_data}")
```

Consulta `lxmfy/storage.py` y la referencia de API para más detalles.

## Permisos

LXMFy incluye un sistema opcional de permisos por roles. Actívalo con
`permissions_enabled=True` al inicializar `LXMFBot`.

- **Roles:** define roles con permisos concretos (p. ej.,
  `DefaultPerms.MANAGE_USERS`).
- **Permisos:** flags granulares definidos en `DefaultPerms` (p. ej.,
  `USE_COMMANDS`, `BYPASS_SPAM`).
- **Asignación:** asigna roles a hashes de usuario.

Consulta `lxmfy/permissions.py`, la referencia de API y posiblemente
cogs de ejemplo (si se crean) para los detalles de uso.

## Verificación de firmas

LXMFy ofrece configuración para la firma y verificación criptográfica de
mensajes integrada en LXMF. Todos los mensajes LXMF se firman
automáticamente en la pila LXMF/RNS - LXMFy simplemente permite aplicar
políticas de verificación de firmas.

**Configuración:**

Activa la verificación de firmas en la configuración del bot:

``` python
bot = LXMFBot(
    name="SecureBot",
    signature_verification_enabled=True,  # Activar la comprobación de firmas
    require_message_signatures=False      # Poner a True para rechazar mensajes sin firmar
)
```

**Cómo funciona:**

LXMF gestiona automáticamente todas las operaciones criptográficas:

1.  **Mensajes salientes:** LXMF firma automáticamente todos los
    mensajes usando la identidad RNS del remitente durante el
    empaquetado.
2.  **Mensajes entrantes:** LXMF valida automáticamente las firmas
    usando la identidad RNS del remitente y devuelve los resultados.
3.  **Papel de LXMFy:** LXMFy comprueba los resultados de validación de
    LXMF y aplica tu política:
    - Si `signature_verification_enabled=False`: se aceptan todos los
      mensajes (por defecto)
    - Si `signature_verification_enabled=True` y
      `require_message_signatures=False`: los mensajes se aceptan pero
      las firmas ausentes o inválidas se registran
    - Si `signature_verification_enabled=True` y
      `require_message_signatures=True`: los mensajes sin firmar o
      inválidos se rechazan
4.  **Integración con permisos:** los usuarios con el permiso
    `BYPASS_SPAM` pueden omitir los requisitos de verificación de
    firmas.

**Gestión por CLI:**

Puedes gestionar los ajustes de verificación de firmas con la CLI:

``` bash
# Probar la verificación de firmas
lxmfy signatures test

# Activar la verificación de firmas
lxmfy signatures enable

# Desactivar la verificación de firmas
lxmfy signatures disable
```

**Detalles técnicos:**

LXMF usa firmas Ed25519 proporcionadas por el sistema criptográfico de
RNS. Cada mensaje LXMF incluye la firma del remitente, que se valida
contra su identidad RNS conocida. LXMFy simplemente lee la propiedad
`message.signature_validated` de LXMF y `message.unverified_reason` para
aplicar la política de seguridad de tu bot.

## Entrega de mensajes

### Uso de nodos de propagación

Envía mensajes a través de nodos de propagación LXMF concretos:

``` python
from lxmfy import LXMFBot

bot = LXMFBot(name="PropagationBot")

@bot.command(name="send", description="Send via propagation node")
def send_command(ctx):
    # Definir un nodo de propagación concreto una vez (a nivel de config)
    bot.set_propagation_node("<propagation_node_hash_here>")

    # Enviar usando la estrategia de entrega configurada
    bot.send(
        ctx.sender,
        "This message will use direct delivery with propagation fallback as configured"
    )
```

Usa un nodo de propagación cuando el destino esté desconectado o la
entrega directa falle repetidamente en la ruta actual.

### Configuración de reintentos

Configura los reintentos automáticos para entregas fallidas en la
configuración del bot:

``` python
from lxmfy import LXMFBot

bot = LXMFBot(name="ReliableBot")

bot = LXMFBot(
    name="ReliableBot",
    direct_delivery_retries=5,  # Reintentar la entrega directa hasta 5 veces
    propagation_fallback_enabled=True
)

@bot.command(name="important", description="Send important message with retries")
def important_command(ctx):
    bot.send(ctx.sender, "This is an important message")

@bot.command(name="normal", description="Send with default retries")
def normal_command(ctx):
    # direct_delivery_retries por defecto es 3
    bot.send(ctx.sender, "This message uses default retry settings")
```

El sistema de reintentos:

- Registra automáticamente los intentos de entrega por destino
- Reintenta las entregas directas fallidas hasta
  `direct_delivery_retries` veces
- Reinicia el contador de reintentos tras una entrega correcta
- Registra los intentos y fallos de reintento para depuración

### Envíos diferidos y stamps

Dos detalles de entrega que conviene conocer pronto:

- **Envíos diferidos**: cuando la identidad del destino aún no se
  conoce, `send()` retiene el mensaje en almacenamiento (las claves de
  configuración `pending_sends_*` controlan la reserva) y lo vacía
  cuando el peer anuncia. Pasa `defer=False` a un envío para descartar
  en lugar de retener.
- **Stamps**: `stamp_cost` establece un requisito de proof-of-work
  entrante, `require_stamps` rechaza los mensajes que no lo cumplen, y
  `include_tickets` (por defecto) adjunta tickets de respuesta para
  que los peers puedan contestar a tu bot sin pagar su propio coste de
  stamp.

Cuando la entrega falla, `lxmfy debug` recorre todo el camino
(configuración, instancia, interfaces, identidad, pipeline de envío) y
escribe un informe redactado que puedes compartir. Las mismas
comprobaciones se pueden llamar como `bot.diagnose_connectivity()` y
`bot.diagnose_destination(hash)`.

Consulta la [Referencia de API](api-reference.md#entrega-de-mensajes)
para toda la superficie de entrega: reintentos, nodos de propagación,
persistencia de cola, el flujo de eventos de entrega y los comandos de
administración `/queue`, `/cancel`, `/inbox`, `/delivery`.

## Reticulum Relay Chat (RRC)

Los bots de LXMFy pueden unirse a hubs de [RRC](https://rrc.kc1awv.net/)
como clientes normales sobre RNS Links usando sobres CBOR. Esto es
compatible con NomadNet y con hubs de estilo rrcd (incluido MeshChatX
cuando aloja el mismo hub o se une a él).

### La configuración de Reticulum importa

El bot debe usar la **misma** red Reticulum que el hub. MeshChatX suele
usar `~/.reticulum` con interfaces backbone o TCP. El directorio
`config/` local del proyecto suele usar un nombre de instancia aislado y
solo AutoInterface, de modo que los anuncios del hub nunca llegan y ves
`Hub identity unknown`.

Prefiere una de estas opciones:

- Define `reticulum_config_dir` con tu configuración de usuario
  (normalmente `~/.reticulum`)
- O exporta `LXMFY_RETICULUM_CONFIG_DIR=~/.reticulum`
- Mantén MeshChatX o `rnsd` en ejecución para que la instancia
  compartida esté activa antes de que arranque el bot

La plantilla `rrc` usa `~/.reticulum` por defecto cuando ese directorio
existe.

### Inicio rápido con la plantilla

``` bash
lxmfy run rrc
```

Valores por defecto:

- Hub: `664fc0e8d2e448658e37bb3f34e6c88f`
- Sala: `#general`
- Configuración de Reticulum: `~/.reticulum` (o
  `LXMFY_RETICULUM_CONFIG_DIR`)

Deberías ver logs de conexión al hub, welcome, unión automática y
`RRC joined #general`.

### Bot RRC programático

``` python
from lxmfy import LXMFBot, RRCMessage

bot = LXMFBot(
    name="RoomBot",
    reticulum_config_dir="~/.reticulum",
    rrc_enabled=True,
    rrc_hubs=["your_rrc_hub_destination_hash"],
    rrc_rooms=["general"],
    rrc_nick="RoomBot",
    rrc_auto_reconnect=True,
    rrc_persist_sessions=True,
)

@bot.on_rrc
def on_rrc(event, client, payload):
    if event == "welcome":
        bot.logger.info("Welcomed by hub")
        return
    if event != "msg" or not isinstance(payload, RRCMessage):
        return
    if payload.mention and payload.room:
        client.send_message(
            payload.room,
            f"Heard you, {payload.nick}",
        )

bot.run()
```

O conéctate en tiempo de ejecución:

``` python
bot.connect_rrc("hub_destination_hash", rooms=["general"])
bot.rrc.send_message("general", "hello room")
bot.rrc.send_action("general", "waves")
bot.disconnect_rrc()
```

### Comportamiento de la sesión

- HELLO / WELCOME, JOIN / PART, MSG / NOTICE / ACTION, PING / PONG,
  ERROR, RESOURCE_ENVELOPE
- Reconexión automática con reingreso a las salas tras WELCOME
- Límite de hubs y aplicación de rate-limit del lado del cliente
- Persistencia de sesiones entre reinicios (`rrc_persist_sessions`,
  activada por defecto)
- La persistencia de la cola LXMF saliente es independiente
  (`message_persistence_enabled`)
