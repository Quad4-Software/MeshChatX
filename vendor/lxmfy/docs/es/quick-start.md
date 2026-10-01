# Inicio rápido

## Requisitos previos

- Python 3.11+
- Reticulum Network Stack (`pip install rns`, versión 1.5.4+)
- LXMF (`pip install lxmf`, versión 1.1.1+, instalado automáticamente con
  LXMFy)
- CBOR (`cborx`, instalado automáticamente, necesario para RRC)

=== "PyPI"

    ``` bash
    pip install lxmfy
    ```

=== "Fuente"

    ``` bash
    git clone https://github.com/Quad4-Software/LXMFy
    cd LXMFy
    poetry install
    ```

## Creación de tu primer bot (con la CLI)

Usa la CLI de LXMFy para generar la estructura de un proyecto. Dos
formas:

- `lxmfy init` hace unas preguntas (nombre, plantilla, almacenamiento,
  prefijo, admins) y escribe un directorio de proyecto listo para
  ejecutar.
- `lxmfy create` escribe un único archivo de bot con defaults, sin
  preguntas.

Esta guía usa `lxmfy create`.

1.  **Abre tu terminal** en el directorio donde quieras crear el
    proyecto del bot.

2.  **Ejecuta el comando de creación:**

    ``` bash
    lxmfy create my_first_bot
    ```

    Este comando generará los siguientes archivos:

    - `my_first_bot.py`: el archivo principal del bot, configurado con
      valores predeterminados razonables.
    - `cogs/`: un directorio para las extensiones del bot (cogs).
    - `cogs/__init__.py`: convierte el directorio `cogs` en un paquete
      de Python.
    - `cogs/basic.py`: un cog de ejemplo con los comandos sencillos
      "hello" y "about".
    - `data/`: un directorio donde el bot guardará sus datos (en JSON
      por defecto).
    - `config/`: un directorio donde el bot guarda su identidad y el
      estado de los anuncios.

3.  **Revisa el archivo `my_first_bot.py`:**

    ``` python
    from lxmfy import LXMFBot

    bot = LXMFBot(
        name="my_first_bot",  # Nombre del bot usado en anuncios e identidad
        announce=600,         # Intervalo de anuncios en segundos (10 minutos)
        announce_immediately=True, # ¿Anunciar en el primer arranque?
        admins=set(),         # Conjunto de hashes de direcciones LXMF de administradores
        hot_reloading=False,  # Activar/desactivar la recarga en caliente de cogs
        rate_limit=5,         # Máximo de mensajes por minuto por usuario
        cooldown=60,          # Periodo de enfriamiento en segundos para el límite
        max_warnings=3,       # Avisos antes del baneo por spam
        warning_timeout=300,  # Tiempo (segundos) antes de reiniciar los avisos
        command_prefix="/",   # Prefijo de los comandos (p. ej., /hello)
        cogs_dir="cogs",      # Directorio desde el que cargar los cogs
        cogs_enabled=True,    # Activar/desactivar la carga de cogs
        permissions_enabled=False, # Activar/desactivar el sistema de permisos por roles
        storage_type="json",  # Backend de almacenamiento ("json", "sqlite", "msgpack" o "memory")
        storage_path="data",  # Ruta de los archivos de almacenamiento o base de datos
        first_message_enabled=True, # Activar el tratamiento especial de los primeros mensajes
        event_logging_enabled=True, # ¿Registrar eventos en el almacenamiento?
        max_logged_events=1000,   # Máximo de eventos a conservar en el registro
        event_middleware_enabled=True, # ¿Activar el middleware de eventos?
        announce_enabled=True,   # Activar/desactivar los anuncios de red
        signature_verification_enabled=False, # Activar/desactivar la verificación criptográfica de firmas
        require_message_signatures=False     # Exigir que todos los mensajes estén firmados
    )

    # Para añadir un administrador, busca tu hash de dirección LXMF y añádelo aquí:
    # bot.config.admins.add("your_lxmf_hash_here")
    # bot.admins = bot.config.admins # Para que la instancia en ejecución lo sepa

    # Ejemplo de preparación de un campo de icono LXMF (opcional)
    # from lxmfy import IconAppearance, pack_icon_appearance_field
    # try:
    #     icon_data = IconAppearance(icon_name="emoji_objects", fg_color=b'\xFF\xA5\x00', bg_color=b'\x8B\x45\x13') # Naranja sobre marrón
    #     bot.icon_field = pack_icon_appearance_field(icon_data) # Guardarlo para usarlo en send/reply
    # except Exception as e:
    #     print(f"No se pudo preparar el campo de icono: {e}")
    #     bot.icon_field = None

    if __name__ == "__main__":
        print(f"Starting bot: {bot.config.name}")
        print(f"Bot LXMF Address: {bot.local.hash}") # Imprime la dirección del bot
        bot.run()
    ```

4.  **(Opcional) Añade tu hash de administrador:**

    - Busca tu hash de dirección LXMF (por ejemplo, en tu cliente de
      Reticulum como Sideband o NomadNet).
    - Descomenta y edita la línea `bot.config.admins.add(...)` en
      `my_first_bot.py`, sustituyendo `"your_lxmf_hash_here"` por tu
      hash real.

5.  **Ejecuta tu bot:**

    ``` bash
    python my_first_bot.py
    ```

    El bot arrancará, imprimirá su dirección LXMF, puede que envíe un
    anuncio por la red Reticulum y empezará a escuchar mensajes.

## Interacción con tu bot

1.  **Envía un mensaje** a la dirección LXMF del bot desde tu cliente.
2.  **Prueba el comando de ejemplo:** envía `/hello` al bot. Debería
    responder con "Hello `<tu_hash>`!". Si descomentaste el ejemplo del
    icono anterior, esta respuesta también puede llevar un icono.
3.  **Prueba el comando de ayuda:** envía `/help`.

Si no llega nada, ejecuta `lxmfy debug` desde el directorio del
proyecto. Comprueba la configuración de Reticulum, las interfaces, la
identidad y la pipeline de envío, y guarda un informe redactado que
puedes compartir al pedir ayuda.

## Qué configurar a continuación

**Manejadores de mensajes**

- `@bot.on_first_message()` para el primer mensaje de cada remitente
- `@bot.on_message()` para todos los mensajes antes del procesamiento de
  comandos

**Entrega**

- `direct_delivery_retries` en `LXMFBot(...)` reintenta la entrega
  directa antes de recurrir a la propagación
- `propagation_node` (o `bot.set_propagation_node(...)`) selecciona un
  nodo de propagación LXMF concreto
- La persistencia de la cola de salida está activada por defecto
  (`message_persistence_enabled=True`) con una cola limitada
  (`message_queue_size`)

**Reticulum Relay Chat (RRC)**

- Únete a hubs con `rrc_enabled=True` o la plantilla `rrc`
- Usa la misma configuración de Reticulum que MeshChatX o tu hub
  (`reticulum_config_dir` o `LXMFY_RETICULUM_CONFIG_DIR`, normalmente
  `~/.reticulum`)
- Consulta [Creación de bots](creating-bots.md#reticulum-relay-chat-rrc)
  para los bots de salas y el descubrimiento de hubs

**Seguridad**

- `signature_verification_enabled=True` comprueba los resultados de
  validación de firmas de LXMF
- `require_message_signatures=True` rechaza los mensajes sin firmar o
  inválidos
- En Linux, `landlock_enabled=True` (por defecto) aplica un sandbox de
  sistema de archivos Landlock LSM. Se anula con `LXMFY_LANDLOCK=0` o
  `LXMFY_LANDLOCK=1`
- Los cogs de scripts externos pueden usar Landlock, bubblewrap o
  firejail mediante `external_cogs_sandbox_type`
- LXMF firma los mensajes salientes. LXMFy aplica la política de
  verificación y el sandbox opcional

**Desarrollo**

- `make typecheck` ejecuta `pyright lxmfy`
- `make ci` ejecuta lint, typecheck, comprobación de seguridad, tests y
  build

Consulta [Creación de bots](creating-bots.md) y la [Referencia de
API](api-reference.md) para el registro de comandos, los cogs y los
detalles de la API.
