# Kernkomponenten

## LXMFBot

Die Hauptklasse des Bots. Sie übernimmt das Routing von Nachrichten,
die Befehlsverarbeitung und die Verwaltung des Bot-Lebenszyklus.

``` python
from lxmfy import LXMFBot

bot = LXMFBot(
    name="MyBot",
    command_prefix="/",
    admins=set(),
    config_path=None,                 # Standard "config" im Arbeitsverzeichnis
    reticulum_config_dir=None,        # oder LXMFY_RETICULUM_CONFIG_DIR / "~/.reticulum"
    test_mode=False,                  # RNS-Start überspringen, für Tests
    log_level="INFO",                 # lxmfy-Logger-Level, None lässt Logging unberührt
    loglevel=None,                    # RNS-Log-Level 0-7, None nutzt die Reticulum-Konfig

    # Announces
    announce=600,
    announce_immediately=True,
    announce_enabled=True,
    announce_display_name_file=None,  # Dateiname unter config_path, der den announced
                                      # Anzeigenamen überschreibt (Standarddatei:
                                      # bot_display_name.txt)

    # Spam-Schutz
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

    # Speicher, Ereignisse, Berechtigungen
    storage_type="json",              # "json", "sqlite", "msgpack" oder "memory"
    storage_path="data",
    permissions_enabled=False,
    first_message_enabled=True,
    event_logging_enabled=True,
    max_logged_events=1000,
    event_middleware_enabled=True,

    # Sicherheit
    signature_verification_enabled=False,
    require_message_signatures=False,
    require_stamps=False,             # Nachrichten mit ungültigen Stamps ablehnen
    request_unknown_identities=False, # Absender-Identitäten aus dem Netz anfordern
    stamp_cost=None,                  # eingehende Stamp-Kosten, None deaktiviert
    include_tickets=True,             # Reply-Tickets an Ausgangsnachrichten anhängen
    identity_pinning_enabled=False,
    landlock_enabled=True,

    # Optionale Funktionen
    nlp_enabled=False,
    nlp_threshold=0.5,
    link_support_enabled=False,
    lxmf_commands_enabled=True,

    # Zustellung
    message_persistence_enabled=True,
    message_queue_size=50,
    opportunistic_sending=True,
    direct_delivery_retries=3,
    propagation_fallback_enabled=True,
    propagation_node=None,            # Hash des ausgehenden Propagationsknotens
    autopeer_propagation=False,       # Propagationsknoten aus Announces erkennen
    autopeer_maxdepth=4,              # max. Hop-Tiefe für Autopeering, None = unbegrenzt
    enable_propagation_node=False,    # diesen Bot als Propagationsknoten betreiben
    message_storage_limit_mb=500,     # Speicherlimit des Knotens, nur Knotenmodus

    # Zurückgestellte Sends
    pending_sends_enabled=True,       # Sends für unbekannte Ziele zurückstellen
    pending_sends_max=200,
    pending_sends_ttl=604800,         # 7 Tage
    pending_sends_retry=300,          # Sekunden zwischen Wiederholungsläufen

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

Alle diese Optionen sind Felder von `BotConfig`. `LXMFBot(**kwargs)`
reicht jedes Schlüsselwortargument durch, sodass `bot.config` die
aufgelösten Werte enthält.

### Wichtige Methoden

- `run(delay=10)`: Hauptschleife des Bots starten
- `cleanup()`: Warteschlangen persistieren, Konversationen abbrechen,
  Scheduler, Router und RNS herunterfahren. Wird beim Verlassen von
  `run()` automatisch aufgerufen.
- `send(destination, message, title="Reply", lxmf_fields=None, stamp_cost=None, opportunistic=None, method=None, include_ticket=None, defer=None, reply_to=None, quote=None, thread=None)`:
  Nachricht an ein Ziel senden. `stamp_cost` überschreibt die
  Ausgangskosten für diese Nachricht, `opportunistic` überschreibt
  `opportunistic_sending`, `include_ticket` überschreibt
  `include_tickets` und `defer` überschreibt `pending_sends_enabled`.
  `reply_to`, `quote` und `thread` setzen die Reply-Threading-Felder.
- `send_with_attachment(destination, message, attachment, title="Reply", stamp_cost=None, opportunistic=None)`:
  Nachricht mit Anhang senden
- `command(name, description="No description provided", admin_only=False, permissions=None, usage=None, examples=None, category=None, aliases=None, threaded=False, rate_limit=None)`:
  Dekorator zur Registrierung von Befehlen. `permissions` überschreibt
  die `DefaultPerms`-Hürde (`ALL` bei `admin_only`, sonst
  `USE_COMMANDS`), `threaded` führt den Callback in einem
  Worker-Thread aus, `rate_limit` begrenzt Aufrufe pro Absender und
  Cooldown-Fenster, und `usage`, `examples`, `category`, `aliases`
  speisen das Hilfesystem. Befehle unterstützen typannotierte
  Argumente für automatische Konvertierung.
- `intent(name, examples)`: Dekorator zur Registrierung von
  NLP-Intent-Handlern.
- `nlp.export_model()`: Trainierte NLP-Modelldaten exportieren.
- `nlp.import_model(model_data)`: Zuvor exportierte NLP-Modelldaten
  importieren.
- `request_link(destination_hash, callback=None, app_name="lxmf", *aspects)`:
  RNS-Link zu einem Ziel anfordern. Erlaubt eigenes `app_name` und
  `aspects` (Standard "lxmf" und "delivery").
- `on_link(callback)`: Handler für eingehende RNS-Links registrieren.
- `load_extension(name)`: Cog-Erweiterungsmodul anhand des Namens
  laden (z. B. "cogs.utility").
- `reload_extension(name)`: Cog-Erweiterungsmodul neu laden.
- `add_cog(cog_instance)`: Cog-Klasseninstanz zum Bot hinzufügen.
- `remove_cog(cog_name)`: Cog anhand seines Klassennamens entfernen.
- `on_first_message()`: Dekorator zur Verarbeitung erster Nachrichten
  von Benutzern
- `on_message()`: Dekorator zur Verarbeitung aller Nachrichten (wird
  vor der Befehlsverarbeitung aufgerufen)
- `received(function)`: Callback registrieren, der mit dem
  Nachrichtenkontext für jede eingehende Nachricht aufgerufen wird,
  die die Pipeline durchlief, ohne von einem Befehl oder Intent
  konsumiert zu werden
- `on_reaction()`: Dekorator zur Verarbeitung eingehender Reaktionen.
  Handler erhalten `(sender, reaction)`, wobei reaction die Schlüssel
  `reaction_to`, `reaction_emoji` und `reaction_sender` enthält
- `react(destination, message_hash, reaction)`: Reaktion auf eine
  Nachricht über das LXMF-Feld `FIELD_REACTION` senden
- `validate()`: Validierungsprüfungen der Bot-Konfiguration ausführen
- `get_landlock_status()`: Verfügbarkeit und Aktivierungsstatus der
  Landlock-LSM-Sandbox für den Bot-Prozess zurückgeben
- `diagnose_destination(destination, request_path=False, wait=0.0)`:
  Identitäts- und Pfadstatus eines Ziel-Hashes prüfen
- `diagnose_connectivity(destination=None, request_path=False, wait=0.0)`:
  Vollständigen Doctor-Report ausführen und als Dict zurückgeben
- `get_debugger()`: Einen an diesen Bot gebundenen `Debugger`
  zurückgeben
- `set_propagation_node(node_hash)`: Ausgehenden Propagationsknoten
  festlegen
- `get_propagation_node_status()`: Konfigurierte, erkannte und aktuell
  genutzte ausgehende Propagationsknoten
- `set_message_storage_limit(megabytes)`: Speicherlimit im Betrieb als
  Propagationsknoten
- `get_propagation_storage_stats()`: Speichernutzung des Knotens oder
  ein Dict mit dem Grund der Nichtverfügbarkeit
- `connect_rrc(hub_hash, rooms=None, nick=None, dest_name=None, auto_reconnect=None)`:
  Als Client mit einem RRC-Hub verbinden
- `disconnect_rrc(hub_hash=None)`: Eine oder alle RRC-Hub-Sitzungen
  trennen
- `on_rrc(callback=None)`: Dekorator oder Handler-Registrierung für
  RRC-Ereignisse (`handler(event, client, payload)`)
- `on_delivery_event(callback=None)`: Den ausgehenden
  Zustell-Ereignisstrom abonnieren, als Dekorator oder direkter Aufruf

### Attribute

- `config`: Die aufgelöste `BotConfig`
- `commands`, `cogs`: Registrierungen für Befehle und Cogs
- `storage`: Das aktive Speicher-Backend
- `scheduler`: `TaskScheduler` für Cron-artige Aufgaben
- `events`: `EventManager` für Ereignis-Handler und Dispatch
- `middleware`: `MiddlewareManager` für Befehls-Middleware
- `permissions`: `PermissionManager` für Rollen und Flags
- `spam_protection`: `SpamProtection` für Rate-Limits, Verwarnungen,
  Bans
- `signature_manager`: Signatur-Richtlinienschicht
- `nlp`: Der Intent-Klassifikator (matched nur bei `nlp_enabled`)
- `delivery`: `DeliveryTracker`, der ausgehende Ereignisstrom
- `conversations`: `ConversationManager` für `msg.ask`-Fragen
- `rrc`: `RRCManager` für Multi-Hub-Sitzungen, `None` bis RRC
  aktiviert ist oder `connect_rrc()` läuft
- `local`: Die `RNS.Destination` des Bots (die LXMF-Adresse ist
  `bot.local.hash`)

## Angezeigter Announce-Name

Der Name, den Peers sehen, kommt aus `name`, aber zwei Überschreibungen
für Announces existieren. Wenn `announce_display_name_file` gesetzt ist
und die Datei unter `config_path` existiert, gewinnt ihr Inhalt.
Andernfalls wird `bot_display_name.txt` unter `config_path` gelesen,
falls vorhanden. In beiden Fällen synchronisiert
`bot.name = "Neuer Name"` den angezeigten Announce-Namen zur Laufzeit
neu.

So können Betreiber einen Bot umbenennen, ohne Code anzufassen, und
der announced Name kann vom internen Konfigurationsnamen abweichen.

## Strukturierte Befehle über LXMF-Felder

Bots können Befehle empfangen, die über das LXMF-Feld
`FIELD_COMMANDS` (`0x09`) gesendet werden, und antworten automatisch
mit `FIELD_RESULTS` (`0x0A`). Damit sind strukturierte
Anfrage/Antwort-Workflows neben normalen Textbefehlen möglich.

Eingehende `FIELD_COMMANDS` werden geparst und über dieselbe
Befehlsregistrierung wie Textbefehle geroutet, mit gemeinsamen
Berechtigungsprüfungen, typannotiertem Argument-Parsing, Threading und
Middleware.

``` python
from lxmfy import LXMFBot, FIELD_COMMANDS, FIELD_RESULTS, pack_result, unpack_commands

bot = LXMFBot(name="FieldBot")

@bot.command(name="status", description="Return bot status")
def status_cmd(ctx):
    # ctx.fields enthält das rohe LXMF-Felder-Dict
    # ctx.request_id wird automatisch gesetzt, wenn der Befehl eine enthielt
    ctx.reply("Bot is online")

# Senden eines strukturierten Befehls von einem anderen LXMF-Client:
# lxm.fields[FIELD_COMMANDS] = {"command": "status", "args": [], "request_id": "abc123"}
# router.handle_outbound(lxm)

# Die Bot-Antwort enthält automatisch FIELD_RESULTS mit Antwort und request_id.
```

Um die Verarbeitung von Feldbefehlen zu deaktivieren,
`lxmf_commands_enabled=False` in `BotConfig` setzen.

## Reaktionen

Reaktionen werden als LXMF-Feld `FIELD_REACTION` (`0x40`) in einer
ansonsten leeren Nachricht übertragen. `pack_reaction` und
`unpack_reaction` erzeugen und parsen dieses Feld.

``` python
from lxmfy import pack_reaction, unpack_reaction

# Eine Reaktion auf eine Nachricht senden
bot.react(destination_hash, message_hash_hex, "thumbs up emoji")

# Reaktionen empfangen
@bot.on_reaction()
def on_reaction(sender, reaction):
    # reaction["reaction_to"]  - Hex-Hash der Zielnachricht
    # reaction["reaction_emoji"] - Reaktionstext (bis zu 16 Zeichen)
    # reaction["reaction_sender"] - Absender
    print(f"{sender} reacted {reaction['reaction_emoji']} to {reaction['reaction_to']}")
    return True
```

Der Reaktionstext ist auf 16 druckbare Zeichen begrenzt. Das Rohfeld
bleibt in `ctx.fields` und `msg.fields` verfügbar (Kompatibilität).

## Antwort-Threading

Antworten können die LXMF-Felder `FIELD_REPLY_TO` (`0x30`),
`FIELD_REPLY_QUOTE` (`0x31`) und `FIELD_THREAD` (`0x08`) tragen.
Clients mit Threading, wie MeshChatX und Sideband, zeigen sie als echte
Zitat-Antworten statt als flache Nachrichten.

`msg.reply()` threaded automatisch: es setzt `FIELD_REPLY_TO` auf den
Hash der eingehenden Nachricht und `FIELD_THREAD` auf die Wurzel der
Konversation.

``` python
@bot.command("status")
def status(msg):
    msg.reply("all systems nominal")          # Threaded-Antwort
    msg.reply("flat", reply_to=None)          # Threading abwählen
    msg.reply("noted", quote=True)            # Eingangstext zitieren
```

Für Sends, die keine Antworten sind, die Felder explizit übergeben:

``` python
bot.send(dest, "see above", reply_to=msg_hash_hex, quote="earlier text")
```

Eingehende Antworten werden auf dem Nachrichtenkontext geparst:

``` python
@bot.command("ctx")
def ctx_cmd(msg):
    msg.reply_to      # Hex-Hash, auf den diese Nachricht antwortet, oder None
    msg.reply_quote   # zitierter Text der Antwort, oder None
    msg.thread        # Hex-Hash der Thread-Wurzel, oder None
```

`pack_reply(message_hash, quote=..., thread=...)` und
`unpack_reply(fields)` sind für die manuelle Feldbehandlung exportiert.

## Konversationen

Befehle können dem Absender eine Frage stellen und seine nächste
Nachricht als Antwort behandeln, statt sie als Befehl zu dispatchen:

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

`msg.ask(prompt, timeout=..., validator=...)` blockiert den Handler,
bis die Antwort ankommt, der Timeout abläuft oder die Konversation
abgebrochen wird. Es gibt ein `Answer` mit `content`, `fields`,
`hash`, `sender` und einem `reply(text)`-Shortcut zurück.

Ein Validator lehnt schlechte Antworten ab und fragt erneut:

``` python
num = msg.ask(
    "Pick a number",
    validator=lambda a: None if a.content.isdigit() else "Digits only",
)
```

In Async-Befehlshandlern `await msg.ask_async(...)` verwenden. Für
lange Wartezeiten oder viele offene Konversationen den Callback-Stil
nutzen, damit kein Thread geparkt bleibt:

``` python
msg.ask(
    "Send the log file",
    on_answer=lambda ans: ans.reply("received"),
    on_timeout=lambda sender: bot.send(sender, "Too slow."),
    timeout=3600,
)
```

Hinweise:

- Ein registrierter Befehl während einer offenen Frage bricht die Frage
  ab und führt den Befehl aus. Benutzer haben immer einen Ausweg.
- `bot.conversations.pending_count()` und
  `bot.conversations.cancel(sender)` geben die Registry für Diagnose
  und Admin-Werkzeuge frei.
- Die Registry ist auf 1024 offene Fragen begrenzt. `ask` gibt `None`
  zurück, wenn sie voll ist.
- Blockierendes `ask` parkt den Zustell-Thread dieser Nachricht. Das
  ist bei Direktzustellungen sicher, aber Bots, die große Batches von
  einem Propagationsknoten synchronisieren, sollten
  `on_answer`-Callbacks bevorzugen.

## Speicher

Das Framework bietet drei Speicher-Backends:

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

storage = MemoryStorage() # Vollständig im Arbeitsspeicher
```

## Befehle

Befehlsregistrierung und -verarbeitung:

``` python
@bot.command(name="hello", description="Says hello")
def hello(ctx):
    ctx.reply(f"Hello {ctx.sender}!")
```

### Typannotierte Argumente

Befehle parsen und konvertieren Argumente automatisch anhand der
Typannotationen in der Callback-Funktion.

``` python
@bot.command(name="add", description="Adds two numbers")
def add(ctx, a: int, b: int):
    result = a + b
    ctx.reply(f"The result is {result}")
```

Hilfemetadaten und Zugriffskontrolle kommen aus zusätzlichen
Dekorator-Kwargs:

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

`permissions` überschreibt die Standardhürde: `USE_COMMANDS` für
normale Befehle, `ALL` für `admin_only`. `category` gruppiert den
Befehl in der `/help`-Ausgabe. `aliases` ist nur Hilfe-Metadatum:
Aliasnamen werden angezeigt, aber nicht für den Dispatch registriert,
sodass `/clear` `purge` nicht ausführt, es sei denn, es wird als
zweiter Befehl registriert.

### Pro-Befehl-Rate-Limits

Begrenzt, wie oft ein einzelner Absender einen Befehl innerhalb des
globalen `cooldown`-Fensters aufrufen darf. Beim Erreichen wird nur der
Aufruf abgelehnt, es gibt keine Verwarnungen oder Bans.

``` python
@bot.command(name="report", rate_limit=3)
def report(ctx):
    # jeder Absender kann diesen Befehl 3-mal pro Cooldown-Fenster aufrufen
    ...
```

Erfordert `permissions_enabled=True`, wie das globale Rate-Limit.
Benutzer mit der Admin-Rolle oder `BYPASS_SPAM` überspringen die
Prüfung.

## Spam-Schutz

`bot.spam_protection` setzt das globale Rate-Limit durch: ein Absender
darf `rate_limit` Nachrichten pro `cooldown`-Fenster senden. Bei
Überschreitung gibt es eine Verwarnung und die Nachricht wird
abgelehnt. Bei `max_warnings` wird der Absender gebannt. Verwarnungen
verfallen nach `warning_timeout` Sekunden ohne Fehlverhalten.

Spam-Prüfungen laufen im `message_received`-Ereignis und erfordern
`permissions_enabled=True`.

``` python
bot = LXMFBot(
    name="GuardedBot",
    permissions_enabled=True,
    rate_limit=5,        # Nachrichten pro Cooldown-Fenster
    cooldown=60,         # Fensterlänge in Sekunden
    max_warnings=3,      # Verwarnungen vor einem Ban
    warning_timeout=300, # Sekunden bis zum Zurücksetzen der Verwarnungen
)

# Ban manuell aufheben
bot.spam_protection.unban(sender_hash)
```

Verwarnungen, Bans und Zähler persistieren im konfigurierten
Speicher-Backend und überleben Neustarts. Absender mit `BYPASS_SPAM`
werden nie ratenlimitiert oder gebannt. Das `rate_limit` pro Befehl bei
`@bot.command` ist milder: es lehnt nur den Aufruf ab und warnt oder
bannt nie.

## Hilfesystem

Das Framework enthält einen interaktiven Hilfe-Generator, der
kategorisierte Hilfemenüs auf Basis der Cog- und Command-Metadaten
erzeugt.

``` python
# Der help-Befehl wird automatisch registriert.
# Benutzer können '/help' oder '/help <command>' verwenden
```

## Befehle in separaten Threads

Für lang laufende oder blockierende Operationen, die nicht direkt mit
dem Reticulum Network Stack interagieren, können Befehle in einem
separaten Thread laufen, damit der Bot reaktionsfähig bleibt.

``` python
import time

@bot.command(name="long_task", description="Performs a long-running task in a separate thread", threaded=True)
def long_task_command(ctx):
    ctx.reply("Starting a long task... please wait.")
    time.sleep(10) # Läuft in einem separaten Thread
    ctx.reply("Long task completed!")
```

!!! warning "Threadsicherheit"

    Funktionen mit `threaded=True` **dürfen nicht** direkt mit dem
    Reticulum Network Stack (RNS) oder Komponenten interagieren, die
    auf `lxmfy.transport.py` aufbauen, da diese im Allgemeinen nicht
    threadsicher sind. Verwenden Sie `ctx.reply()`, um aus einem
    Threaded-Befehl heraus Nachrichten an den Benutzer zu senden.

## Ereignisse

Ereignissystem zur Verarbeitung verschiedener Bot-Ereignisse:

``` python
@bot.events.on("message_received", EventPriority.HIGHEST)
def handle_message(event):
    # event.data trägt die Nutzlast, z. B. sender und message
    event.cancel()  # spätere Handler und weitere Verarbeitung stoppen
```

Handler laufen in `EventPriority`-Reihenfolge: `HIGHEST`, `HIGH`,
`NORMAL`, `LOW`. Die Spam-Prüfung selbst ist ein
`message_received`-Handler mit `HIGHEST`, das Canceln dieses
Ereignisses ist also der Mechanismus, mit dem der Rate-Limiter
Nachrichten verwirft.

Eigene Ereignisse dispatchen:

``` python
from lxmfy import Event

bot.events.dispatch(Event("order_placed", data={"user": ctx.sender}))
```

`event_logging_enabled`, `max_logged_events` und
`event_middleware_enabled` existieren in `BotConfig`, sind aber nicht
verdrahtet: Ereignisse werden nicht in den Speicher geschrieben und
`bot.events.use()` ist ein Stub. Als reserviert behandeln.

## Testen

`lxmfy.testing.TestBot` ist ein für Tests vorkonfigurierter `LXMFBot`.
Es startet keine Reticulum-Instanz. Eingehende Nachrichten laufen durch
die echte Empfangspipeline (Middleware, Spam-Prüfungen, Berechtigungen,
Dispatch) und ausgehende Sends werden für Assertions abgefangen.

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
  injiziert eine Nachricht und gibt die erzeugten `SentMessage`-Objekte
  zurück. Absender sind benannt: `"alice"` mappt auf einen stabilen
  Fake-Hash, oder man übergibt direkt einen Hex-Ziel-Hash.
- `bot.drain()` holt die ausgehende Warteschlange ab. `bot.outbox`
  sammelt alles Gesendete. `bot.last_sent(sender=...)` liefert das
  neueste.
- `bot.wait_sent(n, timeout=...)` wartet auf Threaded-Befehle.
- `bot.receive_later(content, sender=..., delay=...)` beantwortet
  blockierende `msg.ask`-Aufrufe aus einem Daemon-Thread.
- `fake_message(content, source_hash=..., ...)` baut eine eingehende
  Nachricht, um `bot._message_received` direkt zu treiben.

`SentMessage` kapselt jede abgefangene Ausgangsnachricht:
`destination` (Hex), `content`, `title`, `fields`, `method`,
`include_ticket`, `stamp_cost` und `raw` für das zugrunde liegende
Objekt.

Die Projekt-Tests umfassen außerdem Zuverlässigkeits- und
Stresstest-Szenarien in der Testsuite des Repositorys. Führen Sie sie
mit dem Test-Runner des Repositorys aus.

### Erweiterte Zuverlässigkeits-Testsuite

Das Framework enthält eine umfangreiche Suite automatisierter Tests
für raue Umgebungsbedingungen:

- **Manifold Testing**: Validiert die mathematische Topologie des
  NLP-Intent-Vektorraums.
- **Chaos Engineering**: Simuliert Bitrott, SD-Karten-Ausfall und
  Speicherkorruption.
- **Temporal Drift**: Prüft die Robustheit gegenüber
  Systemuhrsprüngen (±1 Jahr).
- **Leak Detection**: Langzeit-Überwachung von Speicher,
  Dateideskriptoren und Threads.

## Berechtigungen

Berechtigungssystem zur Zugriffskontrolle auf Bot-Funktionen:

``` python
from lxmfy import DefaultPerms

@bot.command(name="admin", description="Admin command", admin_only=True)
def admin_command(ctx):
    if ctx.is_admin:
        ctx.reply("Admin command executed")
```

Mit `permissions_enabled=True` aktivieren. `DefaultPerms`-Flags:

- `USE_BOT`, `SEND_MESSAGES`, `USE_COMMANDS`: Basiszugriff
- `MANAGE_MESSAGES`, `MANAGE_COMMANDS`, `MANAGE_USERS`: erhöht
- `BYPASS_RATELIMIT`, `BYPASS_SPAM`, `VIEW_ADMIN_COMMANDS`: speziell
- `VIEW_EVENTS`, `MANAGE_EVENTS`, `BYPASS_EVENT_CHECKS`: Ereignissystem
- `NONE`, `ALL`: Kurzformen

`bot.permissions` verwaltet Rollen und Zuweisungen:

``` python
bot.permissions.create_role("moderator", DefaultPerms.MANAGE_MESSAGES | DefaultPerms.BYPASS_SPAM)
bot.permissions.assign_role(user_hash, "moderator")
bot.permissions.remove_role(user_hash, "moderator")
bot.permissions.has_permission(user_hash, DefaultPerms.USE_COMMANDS)
```

Rollen und Zuweisungen persistieren im konfigurierten Speicher-Backend.
Zwei eingebaute Rollen existieren und können nicht gelöscht werden:
`user` (Standard) und `admin`, die automatisch jedem Hash in `admins`
zugeteilt wird.

## Middleware

Middleware-System zur Verarbeitung von Nachrichten und Ereignissen:

``` python
from lxmfy import MiddlewareType

@bot.middleware.register(MiddlewareType.PRE_COMMAND)
def pre_command_middleware(ctx):
    # ctx kapselt den Nachrichtenkontext, ctx.cancelled verwirft ihn
    if "spamword" in ctx.data.content:
        ctx.cancel()
```

Drei Punkte in der Pipeline führen Middleware aus:

- `PRE_COMMAND`: vor dem Befehls-Dispatch, nach den Spam-Prüfungen.
  Gibt die Kette `None` zurück, wird die Nachricht komplett abgebrochen.
- `POST_COMMAND`: nach dem Callback eines Befehls (auch
  Threaded-Befehle, die ihn im Worker-Thread auslösen).
- `PRE_EVENT`: vor dem Dispatch des `message_received`-Ereignisses.

`POST_EVENT`, `REQUEST` und `RESPONSE` existieren in `MiddlewareType`,
aber noch nichts in der Pipeline führt sie aus.

## Anhänge

Unterstützung für das Senden von Dateien, Bildern und Audio:

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

## Icon-Darstellung (LXMF-Feld)

Sie können für Ihren Bot ein eigenes Icon setzen, das kompatible
LXMF-Clients anzeigen können. Dabei wird
`LXMF.FIELD_ICON_APPEARANCE` verwendet.

``` python
from lxmfy import IconAppearance, pack_icon_appearance_field
import LXMF # Erforderlich für LXMF.FIELD_ICON_APPEARANCE

# Icon-Darstellung definieren
icon_data = IconAppearance(
    icon_name="smart_toy",  # Name aus Material Symbols
    fg_color=b'\xFF\xFF\xFF',  # Weißer Vordergrund (3 Bytes)
    bg_color=b'\x4A\x90\xE2'   # Blauer Hintergrund (3 Bytes)
)

# In das LXMF-Feldformat packen
icon_lxmf_field = pack_icon_appearance_field(icon_data)

# Nachricht mit diesem Icon senden
bot.send(
    destination_hash_str,
    "Hello from your friendly bot!",
    title="Bot Message",
    lxmf_fields=icon_lxmf_field
)

# Kann auch mit anderen Feldern kombiniert werden, z. B. Anhängen:
# attachment_field = pack_attachment(some_attachment)
# combined_fields = {**icon_lxmf_field, **attachment_field}
# bot.send(destination, "Message with icon and attachment", lxmf_fields=combined_fields)
```

## Scheduler

System zur Aufgabenplanung:

``` python
@bot.scheduler.schedule(name="daily_task", cron_expr="0 0 * * *")
def daily_task():
    # Läuft täglich um Mitternacht
    pass
```

## Signaturen

LXMFy bietet Konfigurationsoptionen für die in LXMF eingebaute
kryptografische Nachrichtensignierung und -prüfung:

``` python
from lxmfy import LXMFBot

bot = LXMFBot(
    name="SecureBot",
    signature_verification_enabled=True,  # Signaturprüfung aktivieren
    require_message_signatures=False      # Auf True setzen, um unsignierte Nachrichten abzulehnen
)
```

!!! note "Verarbeitung von Signaturen"

    LXMF führt alle kryptografischen Signatur- und Prüfoperationen
    automatisch mit RNS-Identitäten aus. Der `SignatureManager` von
    LXMFy ist eine Konfigurationsschicht, die:

    - steuert, ob die Signaturprüfung erzwungen wird
    - die Richtlinie für unsignierte Nachrichten festlegt (annehmen
      oder ablehnen)
    - sich in das Berechtigungssystem integriert (z. B. Prüfung für
      vertrauenswürdige Benutzer umgehen)

Die eigentlichen kryptografischen Operationen führt LXMF/RNS aus,
nicht LXMFy.

### Landlock-LSM-Sandbox

Auf Linux-Kerneln mit Landlock-Unterstützung (5.13+) kann LXMFy den
Dateisystemzugriff für den Bot-Prozess und für externe Skript-Cogs
einschränken.

**Sandbox des Bot-Prozesses**

Wenn `landlock_enabled=True` (Standard) und der Bot nicht im
`test_mode` läuft, ruft der Bot `apply_landlock_sandbox()` während
der Initialisierung auf. Systemverzeichnisse sind nur lesbar.
Bot-Speicher, Konfiguration, Cogs, Reticulum-Konfiguration und
Temp-Pfade bleiben schreibbar.

``` python
bot = LXMFBot(
    name="SecureBot",
    landlock_enabled=True,
)

status = bot.get_landlock_status()
# status-Schlüssel: landlock_kernel_supported, landlock_requested,
# landlock_auto_enabled, landlock_disabled_by_env, landlock_active
```

**Überschreibung per Umgebungsvariable**

- `LXMFY_LANDLOCK=0`: Landlock auch auf unterstützten Kerneln
  deaktivieren
- `LXMFY_LANDLOCK=1`: Landlock unter Linux unabhängig von der
  Auto-Erkennung versuchen
- nicht gesetzt: `landlock_enabled` und Kernel-Auto-Erkennung folgen

**Sandbox für externe Cogs**

Skript-Cogs verwenden `external_cogs_sandbox_type`. Im Modus `auto`
wird Landlock bevorzugt, wenn verfügbar, da keine externen Werkzeuge
nötig sind. Die vollständige Liste der Sandbox-Optionen steht in der
Anleitung [Bots erstellen](creating-bots.md).

### Identitäts-Pinning

LXMFy unterstützt optionales Identitäts-Pinning, um
Identitätsdiebstahl zu verhindern, falls eine Identität rotiert oder
kompromittiert wird. Wenn aktiviert, "pinnt" der Bot eine
LXMF-Adresse an den zuerst gesehenen öffentlichen Schlüssel.

``` python
bot = LXMFBot(
    identity_pinning_enabled=True
)
```

### SignatureManager-Methoden

Der `SignatureManager` ist als `bot.signature_manager` verfügbar,
wenn `signature_verification_enabled=True`:

- `should_verify_message(sender)`: Feststellen, ob eine Nachricht des
  gegebenen Absenders geprüft werden soll
- `handle_unsigned_message(sender, message_hash)`: Nachrichten ohne
  gültige Signatur gemäß Richtlinie behandeln

### Wie LXMF-Signaturen funktionieren

LXMF signiert alle ausgehenden Nachrichten automatisch mit der
RNS-Identität des Absenders während der `pack()`-Operation. Beim
Empfang validiert LXMF die Signaturen und stellt bereit:

- `message.signature_validated`: Boolescher Wert, ob die Signatur
  gültig ist
- `message.unverified_reason`: Grundcode, falls die Validierung
  fehlschlug (z. B. `SIGNATURE_INVALID`, `SOURCE_UNKNOWN`)

LXMFy nutzt diese eingebauten LXMF-Eigenschaften, um die
Signaturrichtlinie Ihres Bots durchzusetzen.

## Nachrichtenzustellung

LXMFy bietet erweiterte Zustellfunktionen, darunter
Propagationsknoten und automatische Wiederholungen:

### Propagationsknoten

Nachrichten über bestimmte Propagationsknoten senden, um die
Zustellzuverlässigkeit im Reticulum-Netzwerk zu erhöhen:

``` python
# Propagationsknoten einmalig auf Konfigurations-/Laufzeitebene setzen
bot.set_propagation_node("<propagation_node_hash>")

# Mit konfiguriertem Zustellverhalten senden
bot.send(
    destination_hash,
    "Message content"
)

# Der Propagationsknoten-Hash sollte ein gültiger LXMF-Propagationsknoten
# im Reticulum-Netzwerk sein
```

Der Knoten kann auch bei der Erstellung mit `propagation_node="<hash>"`
gesetzt werden, oder der Bot erkennt Knoten selbst:

``` python
bot = LXMFBot(
    name="AutoBot",
    autopeer_propagation=True, # Knoten aus Announces lernen
    autopeer_maxdepth=4,       # Knoten tiefer als 4 Hops ignorieren
)
```

`bot.get_propagation_node_status()` meldet den manuellen Knoten, die
erkannten Knoten und den aktuell genutzten ausgehenden Knoten.

### Automatische Wiederholungen

Automatische Wiederholungsversuche für fehlgeschlagene
Direktzustellungen konfigurieren:

``` python
bot = LXMFBot(
    name="ReliableBot",
    direct_delivery_retries=5,  # Direktzustellung bis zu 5-mal wiederholen
    propagation_fallback_enabled=True
)

bot.send(destination_hash, "Important message")

# direct_delivery_retries ist standardmäßig 3
# Die Wiederholungslogik verarbeitet Zustell-Callbacks automatisch
```

Das Wiederholungssystem verfolgt Zustellversuche pro Ziel und
wiederholt fehlgeschlagene Zustellungen automatisch. Erfolgreiche
Zustellungen setzen den Zähler für dieses Ziel zurück.

### Zurückgestellte Sends

Ein Send an ein Ziel, dessen Identität der Knoten noch nicht gehört
hat, schlägt normalerweise direkt fehl. Mit `pending_sends_enabled`
(Standard) wird die Nachricht stattdessen im Speicher gehalten und
automatisch geflusht, wenn das Ziel announcet oder beim periodischen
Lauf.

``` python
bot = LXMFBot(
    pending_sends_enabled=True,
    pending_sends_max=200,     # älteste gehaltene Nachrichten fallen darüber hinaus
    pending_sends_ttl=604800,  # gehaltene Nachrichten laufen nach 7 Tagen ab
    pending_sends_retry=300,   # Sekunden zwischen den Läufen in run()
)

# Überschreibung pro Send
bot.send(dest, "hold this", defer=True)
bot.send(dest, "send or drop", defer=False)
```

Gehaltene Sends erscheinen als `held (unknown peers)` im Admin-Befehl
`/queue` und erzeugen `deferred`-Ereignisse im Delivery-Tracker.

### Nachrichten-Persistenz

Ausgehende Nachrichten können auf die Festplatte persistiert werden,
damit sie auch nach einem Neustart des Bots zugestellt werden.
Persistenz ist standardmäßig aktiviert. Die Ausgangswarteschlange im
Speicher ist begrenzt (`message_queue_size`, Standard 50) und
verwirft bei Volllast die älteste Nachricht. Ungültige Ziel-Hashes
werden nicht wiederhergestellt.

``` python
bot = LXMFBot(
    message_persistence_enabled=True,
    message_queue_size=50,
)
```

### Stamps und Tickets

Stamp-Kosten lassen Absender Proof-of-Work zahlen, bevor ihre Nachricht
akzeptiert wird, was unerwünschten Verkehr drosselt. LXMFy legt beide
Seiten des Mechanismus offen.

``` python
bot = LXMFBot(
    stamp_cost=16,          # diese eingehenden Stamp-Kosten verlangen
    require_stamps=True,    # Nachrichten mit ungültigen Stamps ablehnen
    include_tickets=True,   # Peers ohne Stamp-Aufwand antworten lassen
)
```

- `stamp_cost` ist die eingehende Anforderung. Die Ausgangskosten eines
  Sends kommen weiterhin aus dem Announce des Peers, außer
  `stamp_cost=` wird an `bot.send()` übergeben.
- `include_tickets` (Standard True) hängt ein Reply-Ticket an
  ausgehende Nachrichten, damit ein Peer mit Stamp-Pflicht antworten
  kann, ohne zu zahlen. Pro Send mit `include_ticket=` überschreiben.
- `request_unknown_identities=True` fordert vom Netz eine
  Absender-Identität an, wenn eine Nachricht aus unbekannter Quelle
  ankommt, damit Stamp- und Signaturprüfungen auflösen statt blind zu
  scheitern.

Laufzeitkontrolle liegt unter [Router-Steuerung](#router-steuerung):
`set_inbound_stamp_cost`, `enforce_stamps`, `ignore_stamps`,
`generate_ticket` und die Ticket-Inspektionsmethoden.

### Als Propagationsknoten laufen

Ein Bot kann zugleich als LXMF-Propagationsknoten dienen und
Nachrichten für offline Peers speichern:

``` python
bot = LXMFBot(
    enable_propagation_node=True,
    message_storage_limit_mb=500,
)

bot.set_message_storage_limit(750)
stats = bot.get_propagation_storage_stats()
```

`get_propagation_node_status()` funktioniert für beide Rollen: es
meldet den ausgehenden Knoten, den dieser Bot nutzt, und ob er selbst
als Knoten dient. Verwandte Steuerungen:
`announce_propagation_node()` bewirbt den Knoten,
`set_retain_on_node()` behält zugestellte Nachrichten darauf, und
`allow_control_identity()` / `disallow_control_identity()` verwalten,
welche Identitäten den Steuerkanal des Knotens nutzen dürfen.

### Zustell-Ereignisse

`bot.delivery` zeichnet einen begrenzten Strom ausgehender
Lebenszyklus-Ereignisse auf, sodass der Nachrichtenfluss ohne
Log-Lektüre beobachtbar ist. Stufen: `queued`, `deferred`,
`dispatched`, `delivered`, `failed`, `cancelled`, `dropped`. Das
jüngste Ende wird im Speicher persistiert und beim Start
wiederhergestellt.

``` python
@bot.on_delivery_event()
def watch(event):
    print(event["stage"], event.get("destination"), event.get("reason"))

# Oder direkt inspizieren
recent = bot.delivery.recent(20)
failures = bot.delivery.recent(stage="failed")
to_peer = bot.delivery.recent(destination="aa11bb...")
```

Jedes Ereignis ist ein Dict mit `ts`, `stage` und optional
`destination`, `message_id`, `hash`, `method`, `attempts`, `reason`,
`title`.

Admins erhalten einen `/delivery [limit]`-Befehl, der dieselbe
Zeitleiste im Chat rendert, und `lxmfy debug` zeigt eine
Zustell-Zeitleisten-Zusammenfassung in den Send-Pipeline-Prüfungen.

### Eingebaute Admin-Befehle

Diese Befehle werden automatisch registriert und verlangen, dass der
Absender in `admins` steht, wenn Berechtigungen aktiviert sind:

| Befehl | Aktion |
| --- | --- |
| `/queue` | Router-Ausgangswarteschlange, interne Warteschlange und gehaltene Sends anzeigen |
| `/cancel <id|all>` | Ausstehende ausgehende Nachrichten abbrechen |
| `/inbox [cancel <hash|all>]` | Aktive eingehende Übertragungen listen oder abbrechen |
| `/delivery [n]` | Die letzten n Zustellereignisse zeigen (Standard 15, max. 50) |
| `/loadext <name>` | Cog-Erweiterung laden |
| `/reloadext <name>` | Geladene Cog-Erweiterung neu laden |

### Router-Steuerung

Dünne Wrapper über den zugrunde liegenden `LXMRouter` für
Absendersteuerung, Tickets, Ausgangswarteschlangen-Verwaltung und
Propagationsknoten-Sync. Alle nehmen Ziel-Hashes als Hex-Strings und
geben `False` zurück, wenn der Router nicht läuft (etwa im
`test_mode`).

**Absendersteuerung (eingehend)**

- `ignore_destination(destination)` / `unignore_destination(destination)` / `is_ignored(destination)`:
  Eingehende Nachrichten eines Absenders verwerfen
- `allow_destination(destination)` / `disallow_destination(destination)`:
  Whitelist-Verwaltung, wenn der Router im Allow-List-Modus läuft
- `prioritise_destination(destination)` / `unprioritise_destination(destination)`:
  Liste priorisierter Absender
- `set_inbound_stamp_cost(stamp_cost)`: Stamp-Kosten für eingehende
  Nachrichten verlangen (`None` löscht)
- `enforce_stamps()` / `ignore_stamps()`: Eingehende
  Stamp-Durchsetzung umschalten

**Tickets**

- `generate_ticket(destination, expiry=None)`: Ein eingehendes
  Stamp-Ticket für einen Absender ausstellen
- `get_inbound_tickets(destination)`: Für einen Absender gehaltene
  Tickets
- `get_outbound_ticket(destination)` / `get_outbound_ticket_expiry(destination)` /
  `get_outbound_stamp_cost(destination)`: Aus dem Netz gelerntes
  ausgehendes Ticket

**Ausgangswarteschlange**

- `outbound_queue()`: Snapshot ausstehender ausgehender Nachrichten
- `get_outbound_progress(lxm_hash)`: Zustellfortschritt für einen
  Nachrichten-Hash oder `None`
- `cancel_outbound(message_id)`: Eine wartende Nachricht vor der
  Zustellung entfernen
- `delivery_link_available(destination)`: Ob ein aktiver RNS-Link zum
  Ziel existiert

**Eingangswarteschlange**

- `has_message(message_hash)`: Ob ein eingehender LXM-Hash bereits
  zugestellt wurde
- `inbound_count()`: Laufende aktive Eingangs-Ressourcenübertragungen
- `inbound_transfers()`: Snapshot jeder Übertragung mit Hash, Größe,
  Fortschritt und Status
- `cancel_inbound(resource_hash)`: Eine aktive Eingangsübertragung
  abbrechen
- `cancel_all_inbound()`: Jede aktive Eingangsübertragung abbrechen,
  gibt die Anzahl zurück

**Peer-Erkennung**

Announce-Metadaten für Ziele, die dieser Knoten gehört hat:

- `get_peer_app_data(destination)`: Rohe announced app_data-Bytes
- `get_peer_lxmf_data(destination)`: Dekodierte
  LXMF-Announce-Metadaten (`display_name`, `stamp_cost`,
  `capabilities`) oder `None`, wenn der Peer keine gültigen LXMF-Daten
  announced hat
- `get_peer_announce(destination)`: Vollständiger Announce-Datensatz
  mit Hops, received_at, Interface und app_data
- `list_peer_announces(limit=100)`: Alle gehörten Announces, neueste
  zuerst

**Propagation**

- `sync_propagation_node(max_messages=None)`: Nachrichten vom
  konfigurierten Propagationsknoten abrufen
- `cancel_propagation_sync()`: Einen laufenden Sync stoppen
- `get_propagation_stats()`: Übertragungsstatus und Limits des Knotens
  oder `None`
- `set_retain_on_node(retain)`: Zugestellte Nachrichten auf dem Knoten
  behalten
- `announce_propagation_node()`: Diesen Knoten als Propagationsknoten
  announcen
- `allow_control_identity(destination)` / `disallow_control_identity(destination)`:
  Whitelist des Propagations-Steuerkanals

**Ingest**

- `ingest_lxm_uri(uri)`: Eine `lxm://`-URI-Nachricht in die
  Eingangswarteschlange importieren

## Diagnose

Wenn Nachrichten nicht fließen, prüft der Debugger den ganzen Pfad
statt zu raten: Reticulum-Konfiguration, Shared-Instance-Status,
Interfaces, Identität, Announce-Verhalten, Zustellkonfiguration und
Send-Pipeline.

``` bash
lxmfy debug                          # vollständiger Doctor-Report, in Datei gespeichert
lxmfy debug probe <hash> --request-path --wait 30
lxmfy debug send <hash>              # einen Testsend nachverfolgen
lxmfy debug receive                  # Empfangsbereitschaft prüfen
lxmfy debug compare <hash_a> <hash_b>
lxmfy debug tips                     # Korrekturen für häufige Fehler
```

Reports sind standardmäßig datenschutzreduziert: Home-Pfade und Hashes
werden gekürzt. `--json` erzeugt maschinenlesbare Ausgabe, `-o DATEI`
schreibt den Report, `--no-save` überspringt die Datei, `--no-privacy`
behält volle Werte für lokale Nutzung, und `--no-color` oder
`NO_COLOR` deaktiviert ANSI-Ausgabe.

Dieselben Prüfungen sind aus Code aufrufbar:

``` python
report = bot.diagnose_connectivity()            # Doctor-Report als Dict
probe = bot.diagnose_destination(               # Identitäts- und Pfadprobe
    "<peer_hash>", request_path=True, wait=30,
)

debugger = bot.get_debugger()                   # volle API
checks = debugger.check_send_pipeline()
verdict = debugger.run_doctor(destination)
```

`lxmfy/debugger.py` exportiert außerdem einen eigenständigen
`diagnose_destination(hash, ...)`-Helper plus die Report-Typen
`CheckResult`, `DestinationProbe`, `DoctorReport` und `MessageDebugger`
für eigenes Tooling.

## Nachrichten-Handler

LXMFy stellt Dekoratoren für verschiedene Arten eingehender
Nachrichten bereit:

### Handler für erste Nachrichten

Die erste Nachricht jedes Benutzers verarbeiten:

``` python
@bot.on_first_message()
def welcome_user(sender, message):
    content = message.content.decode("utf-8")
    bot.send(sender, f"Welcome! You said: {content}")
    return True  # True zurückgeben, um die weitere Verarbeitung zu stoppen
```

### Allgemeiner Nachrichten-Handler

Alle eingehenden Nachrichten vor der Befehlsverarbeitung verarbeiten:

``` python
@bot.on_message()
def handle_all_messages(sender, message):
    content = message.content.decode("utf-8").strip()

    # Eigene Logik hier
    if content.startswith("echo:"):
        bot.send(sender, content[5:])
        return True  # Weitere Verarbeitung stoppen

    return False  # Weiter zur Befehlsverarbeitung
```

Nachrichten-Handler werden in dieser Reihenfolge aufgerufen:
1. Handler für erste Nachrichten (wenn dies die erste Nachricht
dieses Absenders ist) 2. Allgemeine Nachrichten-Handler (registriert
mit `on_message()`) 3. Befehlsverarbeitung (wenn die Nachricht mit
dem Befehlspräfix beginnt)

### Fallback-Callback

`bot.received(fn)` registriert einen Callback, der am Ende der Pipeline
für Nachrichten läuft, die nichts anderes konsumiert hat: kein
First-Message-Handler, kein `on_message`-Handler mit True-Rückgabe,
kein passender Befehl oder NLP-Intent. Der Callback erhält denselben
Nachrichtenkontext wie Befehle, mit `msg.sender`, `msg.content`,
`msg.reply()` und mehr.

``` python
@bot.received
def fallback(msg):
    msg.reply("Sorry, I did not understand that.")
```

Als Catch-all für Freitext-Eingaben verwenden.

## Reticulum Relay Chat (RRC)

Bots können [RRC](https://rrc.kc1awv.net/)-Hubs über RNS-Links mit
CBOR-Envelopes beitreten. Paket: `lxmfy.rrc`.

### BotConfig-Optionen

- `rrc_enabled` (bool, Standard `False`): Konfigurierte Hubs beim
  Start verbinden
- `rrc_hubs` (Liste von Hex-Hashes): Ziel-Hashes der Hubs
- `rrc_rooms` (Liste von Strings): Räume, die nach WELCOME automatisch
  betreten werden
- `rrc_nick` (String oder None): Nickname in HELLO und Raumnachrichten
- `rrc_dest_name` (String, Standard `"rrc.hub"`): Zielname zum Aufbau
  der Hub-Destination
- `rrc_auto_reconnect` (bool, Standard `True`): Nach Link-Verlust neu
  verbinden
- `rrc_persist_sessions` (bool, Standard `True`): Hubs und Räume über
  Neustarts hinweg speichern
- `reticulum_config_dir` (String oder None):
  Reticulum-Konfigurationsverzeichnis. Kann auch über
  `LXMFY_RETICULUM_CONFIG_DIR` gesetzt werden. Dieselbe Konfiguration
  wie MeshChatX verwenden (oft `~/.reticulum`), damit Hub-Announces
  sichtbar sind.

### Beispiel

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

# Laufzeit-API
# bot.connect_rrc(hub_hash, rooms=["general"])
# bot.rrc.send_message("general", "hello")
# bot.rrc.send_notice("general", "notice")
# bot.rrc.send_action("general", "waves")
# bot.rrc.join("ops")
# bot.rrc.part("ops")
# bot.rrc.status()
# bot.disconnect_rrc()
```

### Exportierte Typen

- `RRCClient`: Sitzung mit einem Hub
- `RRCManager`: Manager für mehrere Hubs (`bot.rrc`)
- `RRCMessage`: Payload eines Raumereignisses (`kind`, `room`,
  `text`, `nick`, `src`, `mention`, ...)
- `RRC_VERSION`: Konstante der Wire-Protokollversion
- `DEFAULT_DEST_NAME`: Standard-Hub-Zielname (`"rrc.hub"`)
- `make_envelope`, `encode_envelope`, `decode_envelope`,
  `validate_envelope`, `normalize_room`: Wire-Format-Helper für
  Tooling, das direkt mit Hubs spricht

Übliche Ereignisse, die an `@bot.on_rrc`-Handler übergeben werden:
`status`, `welcome`, `joined`, `parted`, `msg`, `notice`, `action`,
`motd`, `error` und `rtt`.

# Vorlagen

Das Framework enthält mehrere einsatzbereite Bot-Vorlagen:

## EchoBot

Einfacher Echo-Bot, der Nachrichten wiederholt:

``` python
from lxmfy.templates import EchoBot

bot = EchoBot()
bot.run()
```

## NoteBot

Notizen-Bot mit JSON-Speicher:

``` python
from lxmfy.templates import NoteBot

bot = NoteBot()
bot.run()
```

## ReminderBot

Erinnerungs-Bot mit SQLite-Speicher:

``` python
from lxmfy.templates import ReminderBot

bot = ReminderBot()
bot.run()
```

## RRCBot

RRC-Raum-Bot, der konfigurierten Hubs beitritt und auf `@mentions`
antwortet. Standardmäßig Hub `664fc0e8d2e448658e37bb3f34e6c88f`,
Raum `#general` und `~/.reticulum`, falls verfügbar.

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

# CLI-Werkzeuge

Das Framework stellt Kommandozeilen-Werkzeuge für die Bot-Verwaltung
bereit. `lxmfy` ohne Argumente öffnet ein interaktives Menü.

``` bash
# Ein volles Projekt interaktiv scaffolden
lxmfy init mybot                 # Projektverzeichnis, bot.py, cogs/, README
lxmfy init --here --yes          # aktuelles Verzeichnis, alle Defaults annehmen

# Eine einzelne Bot-Datei erstellen
lxmfy create mybot
lxmfy create --template echo mybot
lxmfy create --template rrc my_rrc_bot
lxmfy create mybot --no-cogs     # das Cogs-Paket überspringen
lxmfy create --output dir/bot.py --name MyBot

# Einen Vorlagen-Bot ausführen
lxmfy run echo
lxmfy run rrc
lxmfy run reminder --name "MyReminder"

# Konnektivität diagnostizieren (siehe Abschnitt Diagnose)
lxmfy debug
lxmfy debug probe <hash> --request-path --wait 30

# Signaturprüfung mit einer Nachricht testen
lxmfy signatures test

# Signaturprüfung aktivieren
lxmfy signatures enable

# Signaturprüfung deaktivieren
lxmfy signatures disable
```

`lxmfy init` fragt nach Projektname, Vorlage, Speicher-Backend,
Befehlspräfix und Admin-Hashes. Jede Frage akzeptiert stattdessen ein
Flag: `--dir`, `--bot-name`, `--template`, `--storage`, `--prefix`,
`--admins`, `--no-cogs`, `--force`, `--yes`. Auf nicht-TTY-stdin werden
die Defaults genommen.

Vorlagen für `create` und `run`: `basic`, `echo`, `reminder`, `note`,
`cogtest`, `rrc`.

# Fehlerbehandlung

Shutdown- und Laufzeitfehler rund um `bot.run()` abfangen:

``` python
try:
    bot.run()
except KeyboardInterrupt:
    bot.cleanup()
except Exception as e:
    logger.error(f"Error running bot: {str(e)}")
```

# Modulreferenz

Wird aus den Docstrings des Quellcodes generiert.

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
