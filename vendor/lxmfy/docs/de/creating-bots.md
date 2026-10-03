# Bots erstellen

## Grundlegende Struktur

Ein minimaler LXMFy-Bot umfasst:

1.  Import von `LXMFBot`.
2.  Instanziierung von `LXMFBot` mit der gewünschten Konfiguration.
3.  Definition von Befehlen oder Ereignis-Handlern.
4.  Start des Bots mit `bot.run()`.

``` python
from lxmfy import LXMFBot

# 1. Bot instanziieren
bot = LXMFBot(
    name="SimpleBot",
    command_prefix="!",
    storage_path="simple_data"
)

# 2. Befehle definieren
@bot.command(name="ping", description="Responds with pong")
def ping_command(ctx):
    # ctx ist ein Kontextobjekt mit Informationen zur Nachricht
    # ctx.sender: LXMF-Hash des Absenders
    # ctx.content: vollständiger Nachrichteninhalt
    # ctx.args: Liste der Argumente nach dem Befehl
    # ctx.reply(message): Funktion zum Senden einer Antwort
    #   (akzeptiert auch Schlüsselwortargumente wie title="My Title", lxmf_fields=some_fields)
    ctx.reply("Pong!")

# Für lang laufende Aufgaben können Threaded-Befehle verwendet werden:
# import time
# @bot.command(name="long_op", description="Performs a long operation in a separate thread", threaded=True)
# def long_op_command(ctx):
#     ctx.reply("Starting long operation...")
#     time.sleep(10) # Simuliert eine lang laufende Operation
#     ctx.reply("Long operation complete!")
# Wichtig: Threaded-Befehle sollten nicht direkt mit RNS oder lxmfy.transport.py interagieren.

@bot.command(name="greet", description="Greets the user")
def greet_command(ctx):
    if ctx.args:
        name = " ".join(ctx.args)
        ctx.reply(f"Hello, {name}!")
    else:
        ctx.reply("Hello there! Tell me your name: !greet <your_name>")

# 3. Bot starten
if __name__ == "__main__":
    print(f"Starting bot: {bot.config.name}")
    print(f"Bot LXMF Address: {bot.local.hash}")
    bot.run()
```

## Verwendung von Vorlagen

LXMFy stellt mehrere Vorlagen für gängige Bot-Typen bereit. Mit der
CLI kann eine Bot-Datei auf Basis einer Vorlage generiert werden.

Für ein volles Projektverzeichnis statt einer einzelnen Datei
scaffoldet `lxmfy init` `bot.py`, ein `cogs`-Paket, ein README und
eine `.gitignore` und fragt unterwegs nach Vorlage, Speicher-Backend,
Befehlspräfix und Admin-Hashes.

``` bash
# Echo-Bot erstellen
lxmfy create --template echo my_echo_bot

# Reminder-Bot erstellen (verwendet SQLite-Speicher)
lxmfy create --template reminder my_reminder_bot

# Notizen-Bot erstellen (verwendet JSON-Speicher)
lxmfy create --template note my_note_bot

# Cog-Test-Bot erstellen (testet das Laden von Cogs)
lxmfy create --template cogtest my_cog_test_bot

# RRC-Raum-Bot erstellen (tritt Hubs bei und antwortet auf @mentions)
lxmfy create --template rrc my_rrc_bot

# Oder die Vorlage direkt ausführen
lxmfy run rrc
```

Diese Befehle erzeugen eine Python-Datei (z. B. `my_echo_bot.py`), die
die gewählte Vorlage importiert und ausführt. Anschließend können Sie
die generierte Datei oder den Vorlagencode selbst anpassen
(`lxmfy/templates/...`).

**Beispiel einer generierten Datei (`my_cog_test_bot.py`):**

``` python
from lxmfy.templates import CogTestBot

if __name__ == "__main__":
    bot = CogTestBot() # Erstellt eine Instanz der Vorlage CogTestBot
    # Der Standardname kann optional überschrieben werden:
    # bot.bot.name = "My Cog Test Bot"
    bot.run()
```

## Bot-Konfiguration

Beim Erstellen einer `LXMFBot`-Instanz können verschiedene
Schlüsselwortargumente übergeben werden, um das Verhalten zu
konfigurieren. Eine Liste gängiger Optionen finden Sie im Abschnitt
`BotConfig` der [API-Referenz](api-reference.md) oder im
[Schnellstart](quick-start.md).

``` python
from lxmfy import LXMFBot

bot = LXMFBot(
    name="ConfiguredBot",
    announce=3600, # Jede Stunde announcen
    admins={"your_admin_hash_here"}, # Admin-Benutzer festlegen
    command_prefix="$", # '$' als Präfix verwenden
    storage_type="sqlite", # SQLite-Datenbank verwenden
    storage_path="data/my_bot_data.db", # Pfad zur DB-Datei angeben
    rate_limit=10, # 10 Nachrichten / Minute erlauben
    cooldown=30, # Cooldown von 30 Sekunden
    permissions_enabled=True # Rollenbasierte Berechtigungen aktivieren
)

if __name__ == "__main__":
    # Die Konfiguration kann auch nach der Instanziierung geändert werden
    # Hinweis: Manche Einstellungen setzt man am besten bei der Initialisierung
    bot.config.max_warnings = 5
    bot.spam_protection.config.max_warnings = 5 # Spamschutz ebenfalls aktualisieren

    bot.run()
```

### Ein Bot-Icon setzen (LXMF-Feld)

Sie können Ihrem Bot ein eigenes Icon geben, das in kompatiblen
LXMF-Clients angezeigt wird. Dabei wird
`LXMF.FIELD_ICON_APPEARANCE` verwendet, das beim Senden von Nachrichten
gesetzt werden kann.

Zuerst die benötigten Importe:

``` python
from lxmfy import IconAppearance, pack_icon_appearance_field
```

Anschließend können Sie das Icon definieren und verwenden:

``` python
# In der Bot-Klasse oder beim Setup
icon_data = IconAppearance(
    icon_name="robot_2",  # Auswahl aus Material Symbols
    fg_color=b'\x00\xFF\x00',  # Grün
    bg_color=b'\x33\x33\x33'   # Dunkelgrau
)
self.bot_icon_field = pack_icon_appearance_field(icon_data)

# Beim Senden einer Nachricht oder Antwort:
ctx.reply("Message from your bot!", lxmf_fields=self.bot_icon_field)
# oder
# bot.send(destination, "Another message", lxmf_fields=self.bot_icon_field)
```

Dieses `self.bot_icon_field` kann vorausberechnet und für alle vom Bot
gesendeten Nachrichten wiederverwendet werden.

## Strukturierte Befehle über LXMF-Felder

Neben textbasierten Befehlen unterstützt LXMFy Befehle, die über
LXMF-Nachrichtenfelder mit `FIELD_COMMANDS` (`0x09`) gesendet werden.
Das ist nützlich für strukturierte Anfrage/Antwort-Workflows zwischen
LXMF-Clients und Bots.

Enthält eine Nachricht `FIELD_COMMANDS`, extrahiert der Bot
Befehlsname und Argumente, leitet sie über dieselbe
Befehlsregistrierung wie Textbefehle und fügt der Antwort automatisch
`FIELD_RESULTS` (`0x0A`) hinzu.

**Empfang strukturierter Befehle**

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

Das `ctx`-Objekt in Feldbefehl-Callbacks enthält:

- `ctx.fields`: das rohe LXMF-Felder-Dict der eingehenden Nachricht
- `ctx.request_id`: die `request_id` aus dem eingehenden
  `FIELD_COMMANDS` (falls vorhanden)

**Senden eines strukturierten Befehls von einem LXMF-Client**

``` python
import LXMF
from lxmfy import FIELD_COMMANDS

lxm = LXMF.LXMessage(
    destination,
    source,
    b"",  # Inhalt kann bei reinen Feldbefehlen leer sein
    desired_method=LXMF.LXMessage.DIRECT,
)
lxm.fields[FIELD_COMMANDS] = {
    "command": "add",
    "args": ["3", "5"],
    "request_id": "req-42",  # optional, zur Korrelation
}
router.handle_outbound(lxm)
```

**Feldbefehle deaktivieren**

Wenn der Bot `FIELD_COMMANDS` ignorieren und nur Textbefehle
verarbeiten soll:

``` python
bot = LXMFBot(
    name="TextOnlyBot",
    lxmf_commands_enabled=False,
)
```

## Cogs verwenden (Erweiterungen)

Cogs erlauben es, Befehle und Ereignis-Listener in separaten Dateien
(Module) zu organisieren, damit die Haupt-Bot-Datei übersichtlich
bleibt.

1.  **Erstellen Sie ein `cogs`-Verzeichnis** (oder das Verzeichnis,
    das Sie in `BotConfig` als `cogs_dir` gesetzt haben).
2.  **Erstellen Sie Python-Dateien** im `cogs`-Verzeichnis (z. B.
    `utility.py`).
3.  **Definieren Sie eine Klasse**, die von `lxmfy.Cog` erbt
    (optional, aber gute Praxis), oder eine gewöhnliche Klasse.
4.  **Definieren Sie Befehle** als Methoden der Klasse mit dem
    `@Command`-Dekorator.
5.  **Erstellen Sie eine `setup(bot)`-Funktion** in der Cog-Datei, die
    LXMFy zur Registrierung des Cogs aufruft.

**Beispiel (`cogs/utility.py`):**

``` python
from lxmfy import Command
from lxmfy.commands import Cog  # Cog importieren, falls geerbt wird
import time

class UtilityCog: # Oder class UtilityCog(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = time.time()

    @Command(name="uptime", description="Shows bot uptime")
    # Hinweis: Methoden in Cogs nehmen oft 'self' und 'ctx' entgegen
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
        time.sleep(7) # Simuliert eine lang laufende Operation
        ctx.reply("Long cog task completed!")

# Diese Funktion ist erforderlich, damit der Cog geladen wird
def setup(bot):
    cog_instance = UtilityCog(bot)
    bot.add_cog(cog_instance) # Cog-Instanz beim Bot registrieren
```

**Haupt-Bot-Datei (`my_bot.py`):**

``` python
from lxmfy import LXMFBot

bot = LXMFBot(
    name="CogBot",
    cogs_enabled=True, # Sicherstellen, dass Cogs aktiviert sind (Standard)
    cogs_dir="cogs" # Auf das Verzeichnis verweisen
)

if __name__ == "__main__":
    # Cogs werden automatisch während der LXMFBot-Initialisierung geladen,
    # wenn cogs_enabled True ist.
    bot.run()
```

Beim Start findet der Bot automatisch `utility.py`, ruft dessen
`setup`-Funktion auf, die eine Instanz von `UtilityCog` erstellt und mit
`bot.add_cog()` registriert. Die im Cog definierten Befehle (`uptime`,
`info`) stehen dann zur Verfügung.

## Externe Skript-Cogs (Unterstützung mehrerer Sprachen)

Bot-Erweiterungen können auch in anderen Sprachen als Python
geschrieben werden (z. B. Bash, Ruby, Perl, Go, C), über externe
Skript-Cogs.

1.  **Erstellen Sie ein ausführbares Skript** in Ihrem
    `cogs`-Verzeichnis.
2.  **Fügen Sie einen Shebang** am Anfang des Skripts hinzu (z. B.
    `#!/bin/bash`).
3.  **Stellen Sie sicher, dass das Skript ausführbar ist**
    (`chmod +x your_script`).

Beim Start registriert der Bot automatisch jede ausführbare Datei im
`cogs`-Verzeichnis (die nicht auf `.py` endet) als Bot-Befehl.

**Argumentprotokoll:**

- `$1`: LXMF-Hash des Absenders.
- `$2`: Vollständiger Nachrichteninhalt.
- `$3`, `$4`, ...: Einzelne Befehlsargumente.

**Umgebungsvariablen:**

- `LXMFY_SENDER`: Der Identitäts-Hash des Absenders.
- `LXMFY_CONTENT`: Der vollständige Nachrichteninhalt.
- `LXMFY_HAS_ADMIN`: `true` oder `false`, je nach Admin-Status des
  Absenders.

**Beispiel eines Bash-Cogs (`cogs/greet.sh`):**

``` bash
#!/bin/bash
echo "Hello from Bash! You sent: $2"
```

Wenn ein Benutzer `/greet hello` sendet, führt der Bot dieses Skript
aus und antwortet mit dessen stdout:
`Hello from Bash! You sent: /greet hello`.

## Lokale NLP-Intent-Klassifizierung

LXMFy enthält einen lokalen Intent-Klassifizierer. Er ordnet
Nachrichtentext markierten Beispielphrasen zu, wenn der Text nicht
exakt einem Befehlspräfix entspricht.

1.  **Aktivieren Sie NLP** in der Bot-Konfiguration:
    `nlp_enabled=True`.
2.  **Definieren Sie Intents** mit dem `@bot.intent`-Dekorator.

``` python
@bot.intent("help", examples=["how do I use this?", "show me commands", "help me please"])
def help_intent(msg):
    msg.reply("I can help! Try typing /help to see a list of commands.")
```

Der Abgleich nutzt TF-IDF-Vektoren und Kosinus-Ähnlichkeit. Die
gesamte Bewertung läuft auf dem Bot-Host. Es wird kein Text an eine
externe API gesendet.

**Modell exportieren und importieren**

Exportieren und importieren Sie ein trainiertes Modell, damit größere
Bots nicht bei jedem Start neu trainieren müssen:

``` python
# Modell exportieren
model_data = bot.nlp.export_model()
# model_data in einer Datei oder Datenbank speichern

# Später wieder importieren
bot.nlp.import_model(model_data)
```

## RNS-Link-Unterstützung

Bots können direkte RNS-Links aufbauen und beantworten, für
zustandsbehafteten, streaming- oder höherbandbreitigen Verkehr als
einzelne LXMF-Pakete.

1.  **Aktivieren Sie die Link-Unterstützung** in der Konfiguration:
    `link_support_enabled=True`.
2.  **Link anfordern**: `bot.request_link(destination_hash)`. Optional
    mit eigenem App-Namen und Aspekten:
    `bot.request_link(dest, callback, "my_app", "aspect1")`.
3.  **Eingehende Links behandeln**: Einen Callback mit
    `bot.on_link(handler)` registrieren.

``` python
def handle_link(link):
    print(f"Link established with {RNS.hexrep(link.destination.hash)}")
    # Der Link kann nun für direkte RNS-Kommunikation genutzt werden

bot.on_link(handle_link)
```

**Sicherheit und Sandboxing:**

- **Timeouts:** Externe Cogs haben einen Standard-Timeout (30 s)
  gegen Hängenbleiben. Konfigurierbar über `external_cogs_timeout`.
- **Threading:** Alle externen Cogs laufen in separaten Threads und
  blockieren den Bot nicht.
- **Sandbox des Bot-Prozesses (nur Linux):** Wenn
  `landlock_enabled=True` (Standard) und der Kernel Landlock LSM
  unterstützt (5.13+), wendet der Bot nach dem Start eine
  Dateisystem-Sandbox auf den eigenen Prozess an. Schreibbare Pfade
  sind auf Speicher, Konfiguration, Cogs, Reticulum-Konfiguration und
  Temp-Verzeichnisse beschränkt. Mit der Umgebungsvariablen
  `LXMFY_LANDLOCK=0` deaktivieren oder mit `LXMFY_LANDLOCK=1` einen
  Versuch erzwingen.
- **Sandbox für externe Cogs (nur Linux):** Wenn
  `external_cogs_sandbox_enabled=True` (Standard), laufen ausführbare
  Skript-Cogs in einer eingeschränkten Umgebung. Setzen Sie
  `external_cogs_sandbox_type` auf einen der folgenden Werte:
  - `auto` (Standard): Landlock bevorzugen, wenn unterstützt, sonst
    `bubblewrap` (`bwrap`), sonst `firejail`
  - `landlock`: reine Landlock-Sandbox über `preexec_fn` (engere
    Regeln als die Sandbox des Bot-Prozesses)
  - `bwrap`: bubblewrap-Sandbox mit Read-Only-Binds
  - `firejail`: privates firejail-Profil ohne Netzwerk
  - `none`: keine Subprozess-Sandbox
- **Status:** `bot.get_landlock_status()` aufrufen, um
  Kernel-Unterstützung, ob Landlock angefordert wurde und ob die
  Sandbox des Bot-Prozesses aktiv ist, zu prüfen.

## Nachrichten verarbeiten

LXMFy bietet mehrere Wege, eingehende Nachrichten in verschiedenen
Verarbeitungsstufen zu behandeln.

### Handler für erste Nachrichten

Die erste Nachricht jedes neuen Benutzers verarbeiten (nützlich für
Willkommensnachrichten):

``` python
from lxmfy import LXMFBot

bot = LXMFBot(
    name="WelcomeBot",
    first_message_enabled=True  # Muss True sein (Standard)
)

@bot.on_first_message()
def welcome_new_user(sender, message):
    content = message.content.decode("utf-8")
    bot.send(
        sender,
        f"Welcome to the bot! You said: {content}\n\n"
        "Type /help to see available commands."
    )
    return True  # True zurückgeben, um die weitere Verarbeitung dieser Nachricht zu stoppen

if __name__ == "__main__":
    bot.run()
```

### Allgemeiner Nachrichten-Handler

Alle eingehenden Nachrichten vor der Befehlsverarbeitung verarbeiten:

``` python
from lxmfy import LXMFBot

bot = LXMFBot(name="EchoBot")

@bot.on_message()
def echo_non_commands(sender, message):
    content = message.content.decode("utf-8").strip()

    # Prüfen, ob dies ein Befehl ist - wenn ja, den Befehls-Handler verarbeiten lassen
    if content.startswith(bot.config.command_prefix):
        command_name = content.split()[0][len(bot.config.command_prefix):]
        if command_name in bot.commands:
            return False  # Dem Befehls-Handler überlassen

    # Kein Befehl, als Echo zurücksenden
    bot.send(sender, f"You said: {content}")
    return False  # False zurückgeben, um die Verarbeitung fortzusetzen (es wird ohnehin kein Befehl passen)

@bot.command(name="hello", description="Say hello")
def hello_command(ctx):
    ctx.reply("Hello! This is a command response.")

if __name__ == "__main__":
    bot.run()
```

Verarbeitungsreihenfolge der Nachrichten-Handler:

1.  **Handler für erste Nachrichten** (wenn
    `first_message_enabled=True` und dies die erste Nachricht des
    Absenders ist)
2.  **Allgemeine Nachrichten-Handler** (registriert mit
    `@bot.on_message()`)
3.  **Befehlsverarbeitung** (wenn die Nachricht zu einem
    registrierten Befehl passt)

Handler können `True` zurückgeben, um die weitere Verarbeitung zu
stoppen, oder `False`, um mit der nächsten Stufe fortzufahren.

## Ereignisse verarbeiten

Für verschiedene Bot-Ereignisse können Handler mit dem
`@bot.events.on()`-Dekorator registriert werden.

``` python
from lxmfy import LXMFBot
from lxmfy.events import EventPriority # Optional für die Priorität

bot = LXMFBot(name="EventBot")

@bot.events.on("message_received")
def log_message(event):
    # Das Ereignisobjekt enthält Details
    sender = event.data.get("sender")
    message_content = event.data.get("message").content.decode('utf-8', errors='ignore')
    print(f"Received message from {sender}: {message_content}")

    # Die Ereignisverarbeitung kann abgebrochen werden (z. B. Nachrichtenverarbeitung stoppen)
    # if sender == "some_blocked_hash":
    #    event.cancel()

@bot.events.on("command_executed", priority=EventPriority.LOW)
def log_command(event):
    # Beispiel: event.data könnte {'command_name': 'ping', 'sender': '...', ...} enthalten
    command_name = event.data.get('command_name', 'unknown')
    sender = event.data.get('sender', 'unknown')
    print(f"Command '{command_name}' executed by {sender}")

# Es können auch eigene Ereignisse definiert werden
@bot.command(name="special")
def special_command(ctx):
    ctx.reply("Doing something special!")
    # Ein eigenes Ereignis auslösen
    bot.events.dispatch(Event("special_action_taken", data={"user": ctx.sender}))

@bot.events.on("special_action_taken")
def handle_special(event):
    user = event.data.get("user")
    print(f"Special action was taken by user: {user}")


if __name__ == "__main__":
    bot.run()
```

Weitere Details zur `Event`-Struktur und zu Prioritäten finden Sie in
`lxmfy/events.py`.

## Speicher

LXMFy bietet JSON-, SQLite-, MsgPack- und In-Memory-Speicher-Backends.

- **JSON:** Einfach, menschenlesbar. Gut für kleine Datenmengen.
  Konfiguration mit `storage_type="json"` und
  `storage_path="your_data_dir"`.
- **SQLite:** Effizienter bei größeren Datenmengen oder häufigen
  Schreibvorgängen. Konfiguration mit `storage_type="sqlite"` und
  `storage_path="your_db_file.db"`.
- **MsgPack:** Kompaktes Binärformat mit demselben
  Datei-pro-Schlüssel-Layout wie JSON. Konfiguration mit
  `storage_type="msgpack"` und `storage_path="your_data_dir"`.
- **Memory:** Speicher vollständig im RAM. Zustand geht beim
  Herunterfahren verloren. Konfiguration mit `storage_type="memory"`.

Auf die Speicherschnittstelle greifen Sie über `bot.storage` zu:

``` python
# Daten speichern
bot.storage.set("user_prefs:" + ctx.sender, {"theme": "dark"})

# Daten abrufen (mit Standardwert)
prefs = bot.storage.get("user_prefs:" + ctx.sender, {})
theme = prefs.get("theme", "light")

# Prüfen, ob Daten existieren
if bot.storage.exists("some_key"):
    print("Key exists!")

# Daten löschen
bot.storage.delete("old_data_key")

# Schlüssel mit einem Präfix durchsuchen (nützlich zum Auflisten von Benutzerdaten)
user_keys = bot.storage.scan("user_prefs:")
for key in user_keys:
    user_data = bot.storage.get(key)
    print(f"Data for {key}: {user_data}")
```

Weitere Details in `lxmfy/storage.py` und in der API-Referenz.

## Berechtigungen

LXMFy enthält ein optionales rollenbasiertes Berechtigungssystem.
Aktivierung mit `permissions_enabled=True` bei der
`LXMFBot`-Initialisierung.

- **Rollen:** Rollen mit bestimmten Berechtigungen definieren (z. B.
  `DefaultPerms.MANAGE_USERS`).
- **Berechtigungen:** Granulare Flags in `DefaultPerms` (z. B.
  `USE_COMMANDS`, `BYPASS_SPAM`).
- **Zuweisung:** Rollen werden Benutzer-Hashes zugewiesen.

Details zur Verwendung finden Sie in `lxmfy/permissions.py`, in der
API-Referenz und gegebenenfalls in Beispiel-Cogs.

## Signaturprüfung

LXMFy bietet Konfiguration für die in LXMF eingebaute kryptografische
Nachrichtensignierung und -prüfung. Alle LXMF-Nachrichten werden vom
LXMF/RNS-Stack automatisch signiert. LXMFy erlaubt lediglich die
Durchsetzung von Prüfrichtlinien.

**Konfiguration:**

Aktivieren Sie die Signaturprüfung in der Bot-Konfiguration:

``` python
bot = LXMFBot(
    name="SecureBot",
    signature_verification_enabled=True,  # Signaturprüfung aktivieren
    require_message_signatures=False      # Auf True setzen, um unsignierte Nachrichten abzulehnen
)
```

**Funktionsweise:**

LXMF führt alle kryptografischen Operationen automatisch aus:

1.  **Ausgehende Nachrichten:** LXMF signiert alle Nachrichten beim
    Packen automatisch mit der RNS-Identität des Absenders.
2.  **Eingehende Nachrichten:** LXMF validiert Signaturen automatisch
    anhand der RNS-Identität des Absenders und liefert
    Validierungsergebnisse.
3.  **Rolle von LXMFy:** LXMFy prüft die Validierungsergebnisse von
    LXMF und setzt Ihre Richtlinie durch:
    - Bei `signature_verification_enabled=False`: Alle Nachrichten
      werden akzeptiert (Standard)
    - Bei `signature_verification_enabled=True` und
      `require_message_signatures=False`: Nachrichten werden
      akzeptiert, aber unsignierte/ungültige Signaturen werden
      protokolliert
    - Bei `signature_verification_enabled=True` und
      `require_message_signatures=True`: Unsignierte oder ungültige
      Nachrichten werden abgelehnt
4.  **Integration der Berechtigungen:** Benutzer mit der Berechtigung
    `BYPASS_SPAM` können die Signaturprüfung umgehen.

**Verwaltung über die CLI:**

Die Einstellungen der Signaturprüfung lassen sich über die CLI
verwalten:

``` bash
# Signaturprüfung testen
lxmfy signatures test

# Signaturprüfung aktivieren
lxmfy signatures enable

# Signaturprüfung deaktivieren
lxmfy signatures disable
```

**Technische Details:**

LXMF verwendet Ed25519-Signaturen aus dem RNS-Kryptosystem. Jede
LXMF-Nachricht enthält die Signatur des Absenders, die gegen die
bekannte RNS-Identität validiert wird. LXMFy liest lediglich die
LXMF-Eigenschaften `message.signature_validated` und
`message.unverified_reason`, um die Sicherheitsrichtlinie Ihres Bots
durchzusetzen.

## Nachrichtenzustellung

### Propagationsknoten verwenden

Nachrichten über bestimmte LXMF-Propagationsknoten senden:

``` python
from lxmfy import LXMFBot

bot = LXMFBot(name="PropagationBot")

@bot.command(name="send", description="Send via propagation node")
def send_command(ctx):
    # Einen bestimmten Propagationsknoten einmalig setzen (Konfigurationsebene)
    bot.set_propagation_node("<propagation_node_hash_here>")

    # Mit konfigurierter Zustellstrategie senden
    bot.send(
        ctx.sender,
        "This message will use direct delivery with propagation fallback as configured"
    )
```

Verwenden Sie einen Propagationsknoten, wenn das Ziel offline ist
oder die Direktzustellung auf dem aktuellen Pfad wiederholt
fehlschlägt.

### Wiederholungsversuche konfigurieren

Automatische Wiederholungsversuche für fehlgeschlagene
Nachrichtenzustellungen über die Bot-Konfiguration einstellen:

``` python
from lxmfy import LXMFBot

bot = LXMFBot(name="ReliableBot")

bot = LXMFBot(
    name="ReliableBot",
    direct_delivery_retries=5,  # Direktzustellung bis zu 5-mal wiederholen
    propagation_fallback_enabled=True
)

@bot.command(name="important", description="Send important message with retries")
def important_command(ctx):
    bot.send(ctx.sender, "This is an important message")

@bot.command(name="normal", description="Send with default retries")
def normal_command(ctx):
    # direct_delivery_retries ist standardmäßig 3
    bot.send(ctx.sender, "This message uses default retry settings")
```

Das Wiederholungssystem:

- Verfolgt Zustellversuche automatisch pro Ziel
- Wiederholt fehlgeschlagene Direktzustellungen bis zu
  `direct_delivery_retries`-mal
- Setzt den Wiederholungszähler nach erfolgreicher Zustellung zurück
- Protokolliert Wiederholungsversuche und Fehler zur Fehlersuche

### Zurückgestellte Sends und Stamps

Zwei Zustelldetails lohnt es früh zu kennen:

- **Zurückgestellte Sends**: Wenn die Zielidentität noch nicht bekannt
  ist, hält `send()` die Nachricht im Speicher (die
  `pending_sends_*`-Konfigurationsschlüssel steuern den Rückstau) und
  flusht sie, wenn der Peer announcet. `defer=False` an einem Send
  verwirft statt zu halten.
- **Stamps**: `stamp_cost` setzt eine eingehende
  Proof-of-Work-Anforderung, `require_stamps` lehnt Nachrichten ab, die
  sie nicht erfüllen, und `include_tickets` (Standard) hängt
  Reply-Tickets an, damit Peers Ihrem Bot antworten können, ohne
  eigene Stamp-Kosten zu zahlen.

Wenn die Zustellung nicht funktioniert, läuft `lxmfy debug` den ganzen
Pfad ab (Konfiguration, Instanz, Interfaces, Identität, Send-Pipeline)
und schreibt einen redigierten Report zum Teilen. Dieselben Prüfungen
sind als `bot.diagnose_connectivity()` und
`bot.diagnose_destination(hash)` aufrufbar.

Siehe die [API-Referenz](api-reference.md#nachrichtenzustellung) für
die volle Zustellfläche: Wiederholungen, Propagationsknoten,
Warteschlangen-Persistenz, den Zustell-Ereignisstrom und die
Admin-Befehle `/queue`, `/cancel`, `/inbox`, `/delivery`.

## Reticulum Relay Chat (RRC)

LXMFy-Bots können [RRC](https://rrc.kc1awv.net/)-Hubs als gewöhnliche
Clients über RNS-Links mit CBOR-Envelopes beitreten. Kompatibel mit
Hubs im NomadNet- und rrcd-Stil (einschließlich MeshChatX, wenn es
denselben Hub hostet oder ihm beitritt).

### Die Reticulum-Konfiguration ist wichtig

Der Bot muss **dasselbe** Reticulum-Netzwerk wie der Hub verwenden.
MeshChatX nutzt üblicherweise `~/.reticulum` mit Backbone- oder
TCP-Interfaces. Das projektlokale `config/`-Verzeichnis verwendet oft
einen isolierten Instanznamen und nur AutoInterface, sodass
Hub-Announces nie ankommen und Sie `Hub identity unknown` sehen.

Bevorzugen Sie eines davon:

- `reticulum_config_dir` auf Ihre Benutzerkonfiguration setzen
  (üblicherweise `~/.reticulum`)
- Oder `LXMFY_RETICULUM_CONFIG_DIR=~/.reticulum` exportieren
- MeshChatX oder `rnsd` laufen lassen, damit die geteilte Instanz vor
  dem Bot-Start aktiv ist

Die `rrc`-Vorlage verwendet standardmäßig `~/.reticulum`, wenn dieses
Verzeichnis existiert.

### Schnellstart mit der Vorlage

``` bash
lxmfy run rrc
```

Standardwerte:

- Hub: `664fc0e8d2e448658e37bb3f34e6c88f`
- Raum: `#general`
- Reticulum-Konfiguration: `~/.reticulum` (oder
  `LXMFY_RETICULUM_CONFIG_DIR`)

Im Log sollten Einträge für Hub-Verbindung, Welcome, Auto-Join und
`RRC joined #general` erscheinen.

### Programmgesteuerter RRC-Bot

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

Oder zur Laufzeit verbinden:

``` python
bot.connect_rrc("hub_destination_hash", rooms=["general"])
bot.rrc.send_message("general", "hello room")
bot.rrc.send_action("general", "waves")
bot.disconnect_rrc()
```

### Sitzungsverhalten

- HELLO / WELCOME, JOIN / PART, MSG / NOTICE / ACTION, PING / PONG,
  ERROR, RESOURCE_ENVELOPE
- Auto-Reconnect mit erneutem Raum-Beitritt nach WELCOME
- Clientseitige Durchsetzung von Hub-Limit und Rate-Limit
- Persistenz der Sitzungen über Neustarts hinweg
  (`rrc_persist_sessions`, standardmäßig aktiviert)
- Persistenz der ausgehenden LXMF-Warteschlange ist separat
  (`message_persistence_enabled`)
