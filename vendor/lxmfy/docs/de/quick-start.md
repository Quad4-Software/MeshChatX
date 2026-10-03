# Schnellstart

## Voraussetzungen

- Python 3.11+
- Reticulum Network Stack (`pip install rns`, Version 1.5.4+)
- LXMF (`pip install lxmf`, Version 1.1.1+, wird automatisch mit
  LXMFy installiert)
- CBOR (`cborx`, wird automatisch installiert, für RRC erforderlich)

=== "PyPI"

    ``` bash
    pip install lxmfy
    ```

=== "Quellcode"

    ``` bash
    git clone https://github.com/Quad4-Software/LXMFy
    cd LXMFy
    poetry install
    ```

## Den ersten Bot erstellen (über die CLI)

Verwenden Sie die LXMFy-CLI, um ein Projektgerüst zu erstellen. Zwei
Wege:

- `lxmfy init` stellt ein paar Fragen (Name, Vorlage, Speicher,
  Präfix, Admins) und schreibt ein lauffertiges Projektverzeichnis.
- `lxmfy create` schreibt eine einzelne Bot-Datei mit Defaults, ohne
  Fragen.

Diese Anleitung verwendet `lxmfy create`.

1.  **Öffnen Sie ein Terminal** in dem Verzeichnis, in dem Sie Ihr
    Bot-Projekt erstellen möchten.

2.  **Führen Sie den create-Befehl aus:**

    ``` bash
    lxmfy create my_first_bot
    ```

    Dieser Befehl erzeugt die folgenden Dateien:

    - `my_first_bot.py`: Ihre Haupt-Bot-Datei mit sinnvollen
      Standardeinstellungen.
    - `cogs/`: Ein Verzeichnis für Bot-Erweiterungen (Cogs).
    - `cogs/__init__.py`: Macht das Verzeichnis `cogs` zu einem
      Python-Paket.
    - `cogs/basic.py`: Ein Beispiel-Cog mit einfachen "hello"- und
      "about"-Befehlen.
    - `data/`: Ein Verzeichnis, in dem der Bot seine Daten speichert
      (standardmäßig JSON).
    - `config/`: Ein Verzeichnis, in dem der Bot seine Identität und
      den Announce-Status speichert.

3.  **Prüfen Sie die Datei `my_first_bot.py`:**

    ``` python
    from lxmfy import LXMFBot

    bot = LXMFBot(
        name="my_first_bot",  # Bot-Name, wird in Announces/Identität verwendet
        announce=600,         # Announce-Intervall in Sekunden (10 Minuten)
        announce_immediately=True, # Beim ersten Start announcen?
        admins=set(),         # Menge der LXMF-Adress-Hashes der Admins
        hot_reloading=False,  # Hot-Reloading der Cogs ein-/ausschalten
        rate_limit=5,         # Max. Nachrichten pro Minute pro Benutzer
        cooldown=60,          # Cooldown-Dauer in Sekunden für das Rate-Limit
        max_warnings=3,       # Verwarnungen vor einem Bann wegen Spam
        warning_timeout=300,  # Zeit (Sekunden) bis Verwarnungen zurückgesetzt werden
        command_prefix="/",   # Präfix für Befehle (z. B. /hello)
        cogs_dir="cogs",      # Verzeichnis, aus dem Cogs geladen werden
        cogs_enabled=True,    # Laden der Cogs ein-/ausschalten
        permissions_enabled=False, # Rollenbasiertes Berechtigungssystem ein-/ausschalten
        storage_type="json",  # Speicher-Backend ("json", "sqlite", "msgpack" oder "memory")
        storage_path="data",  # Pfad für Speicherdateien/Datenbank
        first_message_enabled=True, # Sonderbehandlung für erste Nachrichten aktivieren
        event_logging_enabled=True, # Ereignisse im Speicher protokollieren?
        max_logged_events=1000,   # Max. Ereignisse im Protokoll
        event_middleware_enabled=True, # Ereignis-Middleware aktivieren?
        announce_enabled=True,   # Netzwerk-Announces ein-/ausschalten
        signature_verification_enabled=False, # Kryptografische Signaturprüfung ein-/ausschalten
        require_message_signatures=False     # Signaturen für alle Nachrichten verlangen
    )

    # Um einen Admin hinzuzufügen, finden Sie Ihren LXMF-Adress-Hash und tragen ihn hier ein:
    # bot.config.admins.add("your_lxmf_hash_here")
    # bot.admins = bot.config.admins # Damit die laufende Instanz es übernimmt

    # Beispiel zur Vorbereitung eines LXMF-Icon-Felds (optional)
    # from lxmfy import IconAppearance, pack_icon_appearance_field
    # try:
    #     icon_data = IconAppearance(icon_name="emoji_objects", fg_color=b'\xFF\xA5\x00', bg_color=b'\x8B\x45\x13') # Orange auf Braun
    #     bot.icon_field = pack_icon_appearance_field(icon_data) # Für send/reply speichern
    # except Exception as e:
    #     print(f"Icon-Feld konnte nicht vorbereitet werden: {e}")
    #     bot.icon_field = None

    if __name__ == "__main__":
        print(f"Starte Bot: {bot.config.name}")
        print(f"LXMF-Adresse des Bots: {bot.local.hash}") # Gibt die Adresse des Bots aus
        bot.run()
    ```

4.  **(Optional) Eigenen Admin-Hash hinzufügen:**

    - Ermitteln Sie Ihren LXMF-Adress-Hash (z. B. in Ihrem
      Reticulum-Client wie Sideband oder NomadNet).
    - Entfernen Sie die Auskommentierung der Zeile
      `bot.config.admins.add(...)` in `my_first_bot.py` und ersetzen
      Sie `"your_lxmf_hash_here"` durch Ihren tatsächlichen Hash.

5.  **Bot starten:**

    ``` bash
    python my_first_bot.py
    ```

    Der Bot startet, gibt seine LXMF-Adresse aus, sendet
    gegebenenfalls einen Announce ins Reticulum-Netzwerk und beginnt,
    auf Nachrichten zu warten.

## Mit dem Bot interagieren

1.  **Senden Sie eine Nachricht** von Ihrem Client an die
    LXMF-Adresse des Bots.
2.  **Testen Sie den Beispielbefehl:** Senden Sie `/hello` an den
    Bot. Er sollte mit "Hello `<dein_hash>`!" antworten. Wenn Sie das
    Icon-Beispiel oben einkommentiert haben, kann die Antwort auch ein
    Icon enthalten.
3.  **Testen Sie den Hilfebefehl:** Senden Sie `/help`.

Wenn nichts ankommt, führen Sie `lxmfy debug` im Projektverzeichnis
aus. Es prüft Reticulum-Konfiguration, Interfaces, Identität und
Send-Pipeline und speichert einen redigierten Report, den Sie beim
Hilfeersuchen teilen können.

## Was als Nächstes konfigurieren

**Nachrichten-Handler**

- `@bot.on_first_message()` für die erste Nachricht jedes Absenders
- `@bot.on_message()` für alle Nachrichten vor der Befehlsverarbeitung

**Zustellung**

- `direct_delivery_retries` in `LXMFBot(...)` wiederholt die
  Direktzustellung, bevor auf Propagation zurückgegriffen wird
- `propagation_node` (oder `bot.set_propagation_node(...)`) wählt
  einen bestimmten LXMF-Propagationsknoten
- Die Persistenz der Ausgangswarteschlange ist standardmäßig aktiviert
  (`message_persistence_enabled=True`) mit begrenzter Warteschlange
  (`message_queue_size`)

**Reticulum Relay Chat (RRC)**

- Hubs mit `rrc_enabled=True` oder der Vorlage `rrc` beitreten
- Dieselbe Reticulum-Konfiguration wie MeshChatX oder Ihr Hub
  verwenden (`reticulum_config_dir` oder
  `LXMFY_RETICULUM_CONFIG_DIR`, üblicherweise `~/.reticulum`)
- Siehe [Bots erstellen](creating-bots.md#reticulum-relay-chat-rrc)
  für Raum-Bots und Hub-Erkennung

**Sicherheit**

- `signature_verification_enabled=True` prüft die Ergebnisse der
  LXMF-Signaturvalidierung
- `require_message_signatures=True` weist unsignierte oder ungültige
  Nachrichten ab
- Unter Linux aktiviert `landlock_enabled=True` (Standard) eine
  Landlock-LSM-Dateisystem-Sandbox. Überschreiben mit
  `LXMFY_LANDLOCK=0` oder `LXMFY_LANDLOCK=1`
- Externe Skript-Cogs können Landlock, bubblewrap oder firejail über
  `external_cogs_sandbox_type` nutzen
- LXMF signiert ausgehende Nachrichten. LXMFy setzt die
  Prüfrichtlinie und optionales Sandboxing durch

**Entwicklung**

- `make typecheck` führt `pyright lxmfy` aus
- `make ci` führt Lint, Typecheck, Sicherheitsprüfung, Tests und Build
  aus

Siehe [Bots erstellen](creating-bots.md) und
[API-Referenz](api-reference.md) für Befehlsregistrierung, Cogs und
API-Details.
