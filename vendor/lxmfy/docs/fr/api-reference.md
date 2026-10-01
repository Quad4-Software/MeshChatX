# Composants principaux

## LXMFBot

La classe principale du bot, qui gère le routage des messages, le
traitement des commandes et le cycle de vie du bot.

``` python
from lxmfy import LXMFBot

bot = LXMFBot(
    name="MyBot",
    command_prefix="/",
    admins=set(),
    config_path=None,                 # "config" par défaut dans le répertoire courant
    reticulum_config_dir=None,        # ou LXMFY_RETICULUM_CONFIG_DIR / "~/.reticulum"
    test_mode=False,                  # saute le démarrage RNS, pour les tests
    log_level="INFO",                 # niveau du logger lxmfy, None ne touche pas au logging
    loglevel=None,                    # niveau de log RNS 0-7, None suit la config reticulum

    # Announces
    announce=600,
    announce_immediately=True,
    announce_enabled=True,
    announce_display_name_file=None,  # fichier sous config_path qui remplace le nom
                                      # annoncé (fichier par défaut :
                                      # bot_display_name.txt)

    # Protection anti-spam
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

    # Stockage, événements, permissions
    storage_type="json",              # "json", "sqlite", "msgpack" ou "memory"
    storage_path="data",
    permissions_enabled=False,
    first_message_enabled=True,
    event_logging_enabled=True,
    max_logged_events=1000,
    event_middleware_enabled=True,

    # Sécurité
    signature_verification_enabled=False,
    require_message_signatures=False,
    require_stamps=False,             # rejette les messages aux stamps invalides
    request_unknown_identities=False, # demande les identités des expéditeurs au réseau
    stamp_cost=None,                  # coût de stamp entrant, None désactive
    include_tickets=True,             # joint des tickets de réponse aux envois
    identity_pinning_enabled=False,
    landlock_enabled=True,

    # Fonctions optionnelles
    nlp_enabled=False,
    nlp_threshold=0.5,
    link_support_enabled=False,
    lxmf_commands_enabled=True,

    # Livraison
    message_persistence_enabled=True,
    message_queue_size=50,
    opportunistic_sending=True,
    direct_delivery_retries=3,
    propagation_fallback_enabled=True,
    propagation_node=None,            # hash du nœud de propagation sortant
    autopeer_propagation=False,       # découvre les nœuds de propagation par announces
    autopeer_maxdepth=4,              # profondeur max en sauts, None = sans limite
    enable_propagation_node=False,    # fait de ce bot un nœud de propagation
    message_storage_limit_mb=500,     # plafond de stockage du nœud, mode nœud uniquement

    # Envois différés
    pending_sends_enabled=True,       # retient les envois vers des destinations inconnues
    pending_sends_max=200,
    pending_sends_ttl=604800,         # 7 jours
    pending_sends_retry=300,          # secondes entre les passages de retry

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

Toutes ces options sont des champs de `BotConfig`.
`LXMFBot(**kwargs)` transmet chaque argument nommé, donc `bot.config`
contient les valeurs résolues.

### Méthodes principales

- `run(delay=10)`: Démarre la boucle principale du bot
- `cleanup()`: Persiste les files, annule les conversations et arrête
  le planificateur, le routeur et RNS. Appelé automatiquement à la
  sortie de `run()`.
- `send(destination, message, title="Reply", lxmf_fields=None, stamp_cost=None, opportunistic=None, method=None, include_ticket=None, defer=None, reply_to=None, quote=None, thread=None)`:
  Envoie un message à une destination. `stamp_cost` remplace le coût
  sortant de ce message, `opportunistic` remplace
  `opportunistic_sending`, `include_ticket` remplace
  `include_tickets` et `defer` remplace `pending_sends_enabled`.
  `reply_to`, `quote` et `thread` définissent les champs de threading
  de réponse.
- `send_with_attachment(destination, message, attachment, title="Reply", stamp_cost=None, opportunistic=None)`:
  Envoie un message avec pièce jointe
- `command(name, description="No description provided", admin_only=False, permissions=None, usage=None, examples=None, category=None, aliases=None, threaded=False, rate_limit=None)`:
  Décorateur pour enregistrer des commandes. `permissions` remplace la
  barrière `DefaultPerms` (`ALL` si `admin_only`, sinon
  `USE_COMMANDS`), `threaded` exécute le callback dans un thread de
  travail, `rate_limit` plafonne les invocations par expéditeur et
  fenêtre de cooldown, et `usage`, `examples`, `category`, `aliases`
  alimentent le système d'aide. Les commandes prennent en charge les
  arguments annotés pour la conversion automatique.
- `intent(name, examples)`: Décorateur pour enregistrer des
  gestionnaires d'intents NLP.
- `nlp.export_model()`: Exporte les données du modèle NLP entraîné.
- `nlp.import_model(model_data)`: Importe des données de modèle NLP
  précédemment exportées.
- `request_link(destination_hash, callback=None, app_name="lxmf", *aspects)`:
  Demande un lien RNS vers une destination. Accepte un `app_name` et
  des `aspects` propres ("lxmf" et "delivery" par défaut).
- `on_link(callback)`: Enregistre un gestionnaire pour les liens RNS
  entrants.
- `load_extension(name)`: Charge un module d'extension cog par nom
  (ex. "cogs.utility").
- `reload_extension(name)`: Recharge un module d'extension cog.
- `add_cog(cog_instance)`: Ajoute une instance de classe cog au bot.
- `remove_cog(cog_name)`: Retire un cog par son nom de classe.
- `on_first_message()`: Décorateur pour traiter les premiers messages
  des utilisateurs
- `on_message()`: Décorateur pour traiter tous les messages (appelé
  avant le traitement des commandes)
- `received(function)`: Enregistre un callback invoqué avec le
  contexte du message pour chaque message entrant ayant traversé le
  pipeline sans être consommé par une commande ou un intent
- `on_reaction()`: Décorateur pour traiter les réactions entrantes.
  Les gestionnaires reçoivent `(sender, reaction)`, où reaction porte
  les clés `reaction_to`, `reaction_emoji` et `reaction_sender`
- `react(destination, message_hash, reaction)`: Envoie une réaction à
  un message via le champ LXMF `FIELD_REACTION`
- `validate()`: Lance les vérifications de validation de la
  configuration du bot
- `get_landlock_status()`: Renvoie la disponibilité et l'état
  d'activation de la sandbox Landlock LSM du processus du bot
- `diagnose_destination(destination, request_path=False, wait=0.0)`:
  Sonde l'état d'identité et de route d'un hash de destination
- `diagnose_connectivity(destination=None, request_path=False, wait=0.0)`:
  Exécute le rapport doctor complet et le renvoie en dict
- `get_debugger()`: Renvoie un `Debugger` lié à ce bot
- `set_propagation_node(node_hash)`: Épingle le nœud de propagation
  sortant
- `get_propagation_node_status()`: État des nœuds de propagation
  sortants configurés, découverts et actuellement utilisé
- `set_message_storage_limit(megabytes)`: Plafond de stockage en
  fonctionnement comme nœud de propagation
- `get_propagation_storage_stats()`: Usage de stockage du nœud, ou un
  dict expliquant l'indisponibilité
- `connect_rrc(hub_hash, rooms=None, nick=None, dest_name=None, auto_reconnect=None)`:
  Se connecte à un hub RRC en client
- `disconnect_rrc(hub_hash=None)`: Déconnecte une ou toutes les
  sessions de hub RRC
- `on_rrc(callback=None)`: Décorateur ou enregistrement de
  gestionnaire pour les événements RRC
  (`handler(event, client, payload)`)
- `on_delivery_event(callback=None)`: S'abonne au flux d'événements de
  livraison sortante, en décorateur ou appel direct

### Attributs

- `config`: La `BotConfig` résolue
- `commands`, `cogs`: Registres des commandes et cogs
- `storage`: Le backend de stockage actif
- `scheduler`: `TaskScheduler` pour les tâches type cron
- `events`: `EventManager` pour les gestionnaires d'événements et le
  dispatch
- `middleware`: `MiddlewareManager` pour le middleware de commandes
- `permissions`: `PermissionManager` pour les rôles et les flags
- `spam_protection`: `SpamProtection` pour les limites de débit, les
  avertissements et les bans
- `signature_manager`: Couche de politique de signatures
- `nlp`: Le classificateur d'intents (ne matche qu'avec
  `nlp_enabled`)
- `delivery`: `DeliveryTracker`, le flux d'événements sortants
- `conversations`: `ConversationManager` pour les questions `msg.ask`
- `rrc`: `RRCManager` pour les sessions multi-hubs, `None` tant que
  RRC n'est pas activé ou que `connect_rrc()` n'a pas tourné
- `local`: La `RNS.Destination` du bot (son adresse LXMF est
  `bot.local.hash`)

## Nom annoncé

Le nom que voient les pairs vient de `name`, mais deux dérogations
existent pour les announces. Si `announce_display_name_file` est défini
et que ce fichier existe sous `config_path`, son contenu l'emporte.
Sinon, `bot_display_name.txt` sous `config_path` est lu quand il
existe. Dans les deux cas, assigner `bot.name = "Nouveau nom"`
resynchronise le nom annoncé à l'exécution.

Les opérateurs peuvent ainsi renommer un bot sans toucher au code, et
le nom annoncé peut différer du nom interne de la configuration.

## Commandes structurées via les champs LXMF

Les bots peuvent recevoir des commandes envoyées via le champ LXMF
`FIELD_COMMANDS` (`0x09`) et répondre automatiquement avec
`FIELD_RESULTS` (`0x0A`). Cela permet des flux requête/réponse
structurés en parallèle des commandes textuelles normales.

Les `FIELD_COMMANDS` entrants sont analysés et routés dans le même
registre de commandes que les commandes textuelles, en partageant les
vérifications de permissions, l'analyse des arguments annotés, le
threading et le middleware.

``` python
from lxmfy import LXMFBot, FIELD_COMMANDS, FIELD_RESULTS, pack_result, unpack_commands

bot = LXMFBot(name="FieldBot")

@bot.command(name="status", description="Return bot status")
def status_cmd(ctx):
    # ctx.fields contient le dict brut des champs LXMF
    # ctx.request_id est renseigné automatiquement si la commande en incluait un
    ctx.reply("Bot is online")

# Envoi d'une commande structurée depuis un autre client LXMF :
# lxm.fields[FIELD_COMMANDS] = {"command": "status", "args": [], "request_id": "abc123"}
# router.handle_outbound(lxm)

# La réponse du bot inclut automatiquement FIELD_RESULTS avec la réponse et le request_id.
```

Pour désactiver le traitement des commandes par champs, définissez
`lxmf_commands_enabled=False` dans `BotConfig`.

## Réactions

Les réactions voyagent dans le champ LXMF `FIELD_REACTION` (`0x40`)
d'un message par ailleurs vide. `pack_reaction` et `unpack_reaction`
construisent et analysent ce champ.

``` python
from lxmfy import pack_reaction, unpack_reaction

# Envoyer une réaction à un message
bot.react(destination_hash, message_hash_hex, "thumbs up emoji")

# Recevoir des réactions
@bot.on_reaction()
def on_reaction(sender, reaction):
    # reaction["reaction_to"]  - hachage hex du message cible
    # reaction["reaction_emoji"] - texte de la réaction (16 caractères max)
    # reaction["reaction_sender"] - expéditeur
    print(f"{sender} reacted {reaction['reaction_emoji']} to {reaction['reaction_to']}")
    return True
```

Le texte de réaction est limité à 16 caractères imprimables. Le champ
brut reste disponible dans `ctx.fields` et `msg.fields` pour la
compatibilité.

## Threading des réponses

Les réponses peuvent porter les champs LXMF `FIELD_REPLY_TO` (`0x30`),
`FIELD_REPLY_QUOTE` (`0x31`) et `FIELD_THREAD` (`0x08`). Les clients
qui rendent les fils, comme MeshChatX et Sideband, les affichent comme
de vraies réponses citées plutôt que des messages plats.

`msg.reply()` threade automatiquement : il met `FIELD_REPLY_TO` au
hash du message entrant et `FIELD_THREAD` à la racine de la
conversation.

``` python
@bot.command("status")
def status(msg):
    msg.reply("all systems nominal")          # réponse threadée
    msg.reply("flat", reply_to=None)          # sortir du threading
    msg.reply("noted", quote=True)            # cite le texte entrant
```

Pour les envois qui ne sont pas des réponses, passez les champs
explicitement :

``` python
bot.send(dest, "see above", reply_to=msg_hash_hex, quote="earlier text")
```

Les réponses entrantes sont parsées sur le contexte du message :

``` python
@bot.command("ctx")
def ctx_cmd(msg):
    msg.reply_to      # hash hex auquel ce message répond, ou None
    msg.reply_quote   # texte cité porté par la réponse, ou None
    msg.thread        # hash hex de la racine du fil, ou None
```

`pack_reply(message_hash, quote=..., thread=...)` et
`unpack_reply(fields)` sont exportés pour la gestion manuelle des
champs.

## Conversations

Les commandes peuvent poser une question à l'expéditeur et traiter son
message suivant comme la réponse, au lieu de le dispatcher comme
commande :

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

`msg.ask(prompt, timeout=..., validator=...)` bloque le gestionnaire
jusqu'à l'arrivée de la réponse, l'expiration du timeout ou
l'annulation de la conversation. Il renvoie un `Answer` avec
`content`, `fields`, `hash`, `sender` et un raccourci `reply(text)`.

Un validateur rejette les mauvaises réponses et repose la question :

``` python
num = msg.ask(
    "Pick a number",
    validator=lambda a: None if a.content.isdigit() else "Digits only",
)
```

Dans les gestionnaires async, utilisez `await msg.ask_async(...)`.
Pour les longues attentes, ou quand beaucoup de conversations peuvent
être ouvertes, utilisez le style par callbacks pour ne pas immobiliser
de thread :

``` python
msg.ask(
    "Send the log file",
    on_answer=lambda ans: ans.reply("received"),
    on_timeout=lambda sender: bot.send(sender, "Too slow."),
    timeout=3600,
)
```

Remarques :

- Envoyer une commande enregistrée pendant une question en attente
  annule la question et exécute la commande. L'utilisateur a toujours
  une porte de sortie.
- `bot.conversations.pending_count()` et
  `bot.conversations.cancel(sender)` exposent le registre pour le
  diagnostic et les outils d'admin.
- Le registre est plafonné à 1024 questions en attente. `ask` renvoie
  `None` quand il est plein.
- Un `ask` bloquant immobilise le thread de livraison qui traite ce
  message. C'est sûr pour les livraisons directes, mais les bots qui
  synchronisent de gros lots depuis un nœud de propagation devraient
  préférer les callbacks `on_answer`.

## Stockage

Le framework fournit trois backends de stockage :

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

storage = MemoryStorage() # Entièrement en mémoire
```

## Commandes

Enregistrement et traitement des commandes :

``` python
@bot.command(name="hello", description="Says hello")
def hello(ctx):
    ctx.reply(f"Hello {ctx.sender}!")
```

Les métadonnées d'aide et le contrôle d'accès viennent de kwargs
supplémentaires du décorateur :

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

`permissions` remplace la barrière par défaut : `USE_COMMANDS` pour
les commandes normales, `ALL` pour les `admin_only`. `category` groupe
la commande dans la sortie de `/help`. `aliases` n'est qu'une
métadonnée d'aide : les alias sont affichés aux utilisateurs mais ne
sont pas enregistrés pour le dispatch, donc `/clear` n'exécutera pas
`purge` sauf si vous l'enregistrez comme seconde commande.

### Arguments avec annotations de type

Les commandes analysent et convertissent automatiquement les arguments
d'après les annotations de type de la fonction de callback.

``` python
@bot.command(name="add", description="Adds two numbers")
def add(ctx, a: int, b: int):
    result = a + b
    ctx.reply(f"The result is {result}")
```

### Limites de débit par commande

Limite la fréquence à laquelle un même expéditeur peut invoquer une
commande dans la fenêtre globale de `cooldown`. À la limite, seule
l'invocation est rejetée, jamais d'avertissement ni de ban.

``` python
@bot.command(name="report", rate_limit=3)
def report(ctx):
    # chaque expéditeur peut l'appeler 3 fois par fenêtre de cooldown
    ...
```

Requiert `permissions_enabled=True`, comme la limite globale. Les
utilisateurs avec le rôle admin ou `BYPASS_SPAM` passent le contrôle.

## Protection anti-spam

`bot.spam_protection` applique la limite globale : un expéditeur peut
envoyer `rate_limit` messages par fenêtre de `cooldown`. Un dépassement
ajoute un avertissement et rejette le message. À `max_warnings`,
l'expéditeur est banni. Les avertissements expirent après
`warning_timeout` secondes sans infraction.

Les contrôles anti-spam tournent dans l'événement `message_received`
et requièrent `permissions_enabled=True`.

``` python
bot = LXMFBot(
    name="GuardedBot",
    permissions_enabled=True,
    rate_limit=5,        # messages par fenêtre de cooldown
    cooldown=60,         # durée de la fenêtre en secondes
    max_warnings=3,      # avertissements avant le ban
    warning_timeout=300, # secondes avant remise à zéro des avertissements
)

# Lever un ban manuellement
bot.spam_protection.unban(sender_hash)
```

Avertissements, bans et compteurs persistent dans le backend de
stockage configuré, donc les bans survivent aux redémarrages. Les
expéditeurs avec `BYPASS_SPAM` ne sont jamais limités ni bannis. Le
`rate_limit` par commande de `@bot.command` est plus doux : il ne
rejette que l'invocation et n'avertit ni ne bannit jamais.

## Système d'aide

Le framework inclut un générateur d'aide interactif qui produit des
menus d'aide catégorisés à partir des métadonnées des cogs et des
commandes.

``` python
# La commande help est enregistrée automatiquement.
# Les utilisateurs peuvent utiliser '/help' ou '/help <command>'
```

## Commandes en thread

Pour les opérations longues ou bloquantes qui n'interagissent pas
directement avec le Reticulum Network Stack, vous pouvez exécuter les
commandes dans un thread séparé pour garder le bot réactif.

``` python
import time

@bot.command(name="long_task", description="Performs a long-running task in a separate thread", threaded=True)
def long_task_command(ctx):
    ctx.reply("Starting a long task... please wait.")
    time.sleep(10) # S'exécute dans un thread séparé
    ctx.reply("Long task completed!")
```

!!! warning "Sécurité des threads"

    Les fonctions marquées `threaded=True` **ne doivent pas** interagir
    directement avec le Reticulum Network Stack (RNS) ni avec les
    composants qui dépendent de `lxmfy.transport.py`, car ils ne sont
    généralement pas thread-safe. Utilisez `ctx.reply()` pour renvoyer
    des messages à l'utilisateur depuis une commande en thread.

## Événements

Système d'événements pour traiter les différents événements du bot :

``` python
@bot.events.on("message_received", EventPriority.HIGHEST)
def handle_message(event):
    # event.data porte la charge utile, ex. sender et message
    event.cancel()  # arrête les gestionnaires suivants et le reste du traitement
```

Les gestionnaires tournent dans l'ordre `EventPriority` : `HIGHEST`,
`HIGH`, `NORMAL`, `LOW`. Le contrôle anti-spam lui-même est un
gestionnaire `message_received` en `HIGHEST`, donc annuler cet
événement est le mécanisme par lequel le limiteur jette les messages.

Dispatchez vos propres événements :

``` python
from lxmfy import Event

bot.events.dispatch(Event("order_placed", data={"user": ctx.sender}))
```

`event_logging_enabled`, `max_logged_events` et
`event_middleware_enabled` existent dans `BotConfig` mais ne sont pas
câblés : les événements ne sont pas écrits en stockage et
`bot.events.use()` est un stub. Considérez-les comme réservés.

## Tests

`lxmfy.testing.TestBot` est un `LXMFBot` préconfiguré pour les tests.
Aucune instance Reticulum ne démarre. Les messages entrants passent
par le vrai pipeline de réception (middleware, contrôles anti-spam,
permissions, dispatch) et les envois sortants sont capturés pour les
assertions.

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
  injecte un message et renvoie les objets `SentMessage` produits. Les
  expéditeurs sont nommés : `"alice"` correspond à un faux hash
  stable, ou passez directement un hash de destination hex.
- `bot.drain()` vide les messages sortants en file. `bot.outbox`
  accumule tout ce qui a été envoyé. `bot.last_sent(sender=...)`
  récupère le plus récent.
- `bot.wait_sent(n, timeout=...)` attend les commandes en thread.
- `bot.receive_later(content, sender=..., delay=...)` répond aux
  appels `msg.ask` bloquants depuis un thread daemon.
- `fake_message(content, source_hash=..., ...)` construit un message
  entrant pour piloter `bot._message_received` directement.

`SentMessage` enveloppe chaque message sortant capturé :
`destination` (hex), `content`, `title`, `fields`, `method`,
`include_ticket`, `stamp_cost` et `raw` pour l'objet sous-jacent.

La suite de tests du dépôt comprend aussi des scénarios de fiabilité
et de stress. Utilisez le lanceur de tests du dépôt pour les exécuter.

### Suite avancée de fiabilité

Le framework inclut une suite étendue de tests automatisés pour les
environnements difficiles :

- **Manifold Testing** : valide la topologie mathématique de l'espace
  vectoriel des intentions NLP.
- **Chaos Engineering** : simule le bit rot, les pannes de carte SD et
  la corruption du stockage.
- **Temporal Drift** : vérifie la résilience face aux sauts d'horloge
  système (±1 an).
- **Leak Detection** : suivi à long terme de la mémoire, des
  descripteurs de fichiers et des threads.

## Permissions

Système de permissions pour contrôler l'accès aux fonctions du bot :

``` python
from lxmfy import DefaultPerms

@bot.command(name="admin", description="Admin command", admin_only=True)
def admin_command(ctx):
    if ctx.is_admin:
        ctx.reply("Admin command executed")
```

Activez avec `permissions_enabled=True`. Flags de
`DefaultPerms` :

- `USE_BOT`, `SEND_MESSAGES`, `USE_COMMANDS` : accès de base
- `MANAGE_MESSAGES`, `MANAGE_COMMANDS`, `MANAGE_USERS` : élevés
- `BYPASS_RATELIMIT`, `BYPASS_SPAM`, `VIEW_ADMIN_COMMANDS` : spéciaux
- `VIEW_EVENTS`, `MANAGE_EVENTS`, `BYPASS_EVENT_CHECKS` : système
  d'événements
- `NONE`, `ALL` : raccourcis

`bot.permissions` gère les rôles et les attributions :

``` python
bot.permissions.create_role("moderator", DefaultPerms.MANAGE_MESSAGES | DefaultPerms.BYPASS_SPAM)
bot.permissions.assign_role(user_hash, "moderator")
bot.permissions.remove_role(user_hash, "moderator")
bot.permissions.has_permission(user_hash, DefaultPerms.USE_COMMANDS)
```

Rôles et attributions persistent dans le backend configuré. Deux
rôles intégrés existent et ne peuvent être supprimés : `user` (par
défaut) et `admin`, accordé automatiquement à chaque hash dans
`admins`.

## Middleware

Système de middleware pour traiter les messages et les événements :

``` python
from lxmfy import MiddlewareType

@bot.middleware.register(MiddlewareType.PRE_COMMAND)
def pre_command_middleware(ctx):
    # ctx enveloppe le contexte du message, ctx.cancelled le jette
    if "spamword" in ctx.data.content:
        ctx.cancel()
```

Trois points du pipeline exécutent le middleware :

- `PRE_COMMAND` : avant le dispatch des commandes, après les contrôles
  anti-spam. Si la chaîne renvoie `None`, le message est entièrement
  abandonné.
- `POST_COMMAND` : après le callback d'une commande (y compris les
  commandes en thread, qui le déclenchent dans le thread de travail).
- `PRE_EVENT` : avant le dispatch de l'événement `message_received`.

`POST_EVENT`, `REQUEST` et `RESPONSE` existent dans `MiddlewareType`,
mais rien dans le pipeline ne les exécute encore.

## Pièces jointes

Prise en charge de l'envoi de fichiers, d'images et d'audio :

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

## Apparence de l'icône (champ LXMF)

Vous pouvez définir une icône personnalisée pour votre bot, que les
clients LXMF compatibles peuvent afficher. Elle utilise le champ
`LXMF.FIELD_ICON_APPEARANCE`.

``` python
from lxmfy import IconAppearance, pack_icon_appearance_field
import LXMF # Requis pour LXMF.FIELD_ICON_APPEARANCE

# Définir l'apparence de l'icône
icon_data = IconAppearance(
    icon_name="smart_toy",  # Nom depuis Material Symbols
    fg_color=b'\xFF\xFF\xFF',  # Premier plan blanc (3 octets)
    bg_color=b'\x4A\x90\xE2'   # Arrière-plan bleu (3 octets)
)

# L'empaqueter au format du champ LXMF
icon_lxmf_field = pack_icon_appearance_field(icon_data)

# Envoyer un message avec cette icône
bot.send(
    destination_hash_str,
    "Hello from your friendly bot!",
    title="Bot Message",
    lxmf_fields=icon_lxmf_field
)

# Vous pouvez aussi la combiner avec d'autres champs, comme des pièces jointes :
# attachment_field = pack_attachment(some_attachment)
# combined_fields = {**icon_lxmf_field, **attachment_field}
# bot.send(destination, "Message with icon and attachment", lxmf_fields=combined_fields)
```

## Planificateur

Système de planification de tâches :

``` python
@bot.scheduler.schedule(name="daily_task", cron_expr="0 0 * * *")
def daily_task():
    # Exécution quotidienne à minuit
    pass
```

## Signatures

LXMFy fournit des options de configuration pour la signature et la
vérification cryptographiques intégrées de LXMF :

``` python
from lxmfy import LXMFBot

bot = LXMFBot(
    name="SecureBot",
    signature_verification_enabled=True,  # Activer les vérifications de signature
    require_message_signatures=False      # Mettre True pour rejeter les messages non signés
)
```

!!! note "Gestion des signatures"

    LXMF gère automatiquement toute la signature et la vérification
    cryptographiques via les identités RNS. Le `SignatureManager` de
    LXMFy est une couche de configuration qui :

    - Contrôle si la vérification des signatures est appliquée
    - Détermine la politique pour les messages non signés (accepter ou
      rejeter)
    - S'intègre au système de permissions (par ex. contourner la
      vérification pour les utilisateurs de confiance)

Les opérations cryptographiques réelles sont effectuées par LXMF/RNS,
pas par LXMFy.

### Sandbox Landlock LSM

Sur les noyaux Linux prenant en charge Landlock (5.13+), LXMFy peut
restreindre l'accès au système de fichiers pour le processus du bot et
pour les cogs en scripts externes.

**Sandbox du processus du bot**

Quand `landlock_enabled=True` (défaut) et hors `test_mode`, le bot
appelle `apply_landlock_sandbox()` pendant l'initialisation. Les
répertoires système sont en lecture seule. Le stockage du bot, la
config, les cogs, la config Reticulum et les chemins temporaires
restent inscriptibles.

``` python
bot = LXMFBot(
    name="SecureBot",
    landlock_enabled=True,
)

status = bot.get_landlock_status()
# clés de status : landlock_kernel_supported, landlock_requested,
# landlock_auto_enabled, landlock_disabled_by_env, landlock_active
```

**Surcharge par variable d'environnement**

- `LXMFY_LANDLOCK=0` : désactive Landlock même sur les noyaux
  compatibles
- `LXMFY_LANDLOCK=1` : tente Landlock sous Linux quelle que soit
  l'auto-détection
- non définie : suit `landlock_enabled` et l'auto-détection du noyau

**Sandbox des cogs externes**

Les cogs en scripts utilisent `external_cogs_sandbox_type`. En mode
`auto`, Landlock est préféré quand il est disponible car il ne requiert
aucun outil externe. Voir le guide [Création de
bots](creating-bots.md) pour la liste complète des options de sandbox.

### Épinglage d'identité

LXMFy prend en charge un épinglage d'identité optionnel pour empêcher
l'usurpation si une identité est remplacée ou compromise. Quand il est
activé, le bot "épingle" une adresse LXMF à la première clé publique
vue.

``` python
bot = LXMFBot(
    identity_pinning_enabled=True
)
```

### Méthodes de SignatureManager

Le `SignatureManager` est disponible via `bot.signature_manager` quand
`signature_verification_enabled=True` :

- `should_verify_message(sender)` : détermine si un message d'un
  expéditeur donné doit être vérifié
- `handle_unsigned_message(sender, message_hash)` : traite les messages
  sans signature valide selon la politique

### Fonctionnement des signatures LXMF

LXMF signe automatiquement tous les messages sortants avec l'identité
RNS de l'expéditeur pendant l'opération `pack()`. À la réception, LXMF
valide les signatures et fournit :

- `message.signature_validated` : booléen indiquant si la signature est
  valide
- `message.unverified_reason` : code de raison si la validation a
  échoué (par ex. `SIGNATURE_INVALID`, `SOURCE_UNKNOWN`)

LXMFy utilise ces propriétés LXMF intégrées pour appliquer la politique
de signature de votre bot.

## Livraison des messages

LXMFy fournit des fonctions de livraison de messages avancées, dont les
nœuds de propagation et les réessais automatiques :

### Nœuds de propagation

Envoyez des messages via des nœuds de propagation précis pour une
meilleure fiabilité sur le réseau Reticulum :

``` python
# Configurer le nœud de propagation une fois, au niveau config/runtime
bot.set_propagation_node("<propagation_node_hash>")

# Envoyer avec le comportement de livraison configuré
bot.send(
    destination_hash,
    "Message content"
)

# Le hachage du nœud de propagation doit être un nœud de propagation LXMF valide
# sur le réseau Reticulum
```

Vous pouvez aussi fixer le nœud à la construction avec
`propagation_node="<hash>"`, ou laisser le bot découvrir les nœuds
lui-même :

``` python
bot = LXMFBot(
    name="AutoBot",
    autopeer_propagation=True, # apprend les nœuds depuis les announces
    autopeer_maxdepth=4,       # ignore les nœuds à plus de 4 sauts
)
```

`bot.get_propagation_node_status()` rapporte le nœud manuel, les nœuds
découverts et le nœud sortant actuellement utilisé.

### Réessais automatiques

Configurez les réessais automatiques pour les livraisons directes
échouées :

``` python
bot = LXMFBot(
    name="ReliableBot",
    direct_delivery_retries=5,  # Réessayer la livraison directe jusqu'à 5 fois
    propagation_fallback_enabled=True
)

bot.send(destination_hash, "Important message")

# direct_delivery_retries vaut 3 par défaut
# La logique de réessai gère automatiquement les callbacks de livraison
```

Le système de réessais suit les tentatives de livraison par destination
et réessaie automatiquement les livraisons échouées. Les livraisons
réussies remettent le compteur de réessais à zéro pour cette
destination.

### Envois différés

Envoyer vers une destination dont le nœud n'a pas encore entendu
l'identité échoue normalement tout de suite. Avec
`pending_sends_enabled` (par défaut), le message est plutôt retenu en
stockage puis vidé automatiquement quand la destination annonce ou
lors d'un passage périodique.

``` python
bot = LXMFBot(
    pending_sends_enabled=True,
    pending_sends_max=200,     # les plus vieux messages retenus tombent au-delà
    pending_sends_ttl=604800,  # les messages retenus expirent après 7 jours
    pending_sends_retry=300,   # secondes entre les passages dans run()
)

# Dérogation par envoi
bot.send(dest, "hold this", defer=True)
bot.send(dest, "send or drop", defer=False)
```

Les envois retenus apparaissent comme `held (unknown peers)` dans la
commande admin `/queue` et produisent des événements `deferred` dans
le tracker de livraison.

### Persistance des messages

Les messages sortants peuvent être persistés sur disque pour garantir
leur livraison même après un redémarrage du bot. La persistance est
activée par défaut. La file sortante en mémoire est bornée
(`message_queue_size`, défaut 50) et supprime le plus ancien message
quand elle est pleine. Les hachages de destination invalides ne sont
pas restaurés.

``` python
bot = LXMFBot(
    message_persistence_enabled=True,
    message_queue_size=50,
)
```

### Stamps et tickets

Les coûts de stamp font payer une preuve de travail aux expéditeurs
avant que leur message soit accepté, ce qui freine le trafic non
sollicité. LXMFy expose les deux côtés du mécanisme.

``` python
bot = LXMFBot(
    stamp_cost=16,          # exige ce coût de stamp entrant
    require_stamps=True,    # rejette les messages aux stamps invalides
    include_tickets=True,   # laisse les pairs répondre sans générer de stamp
)
```

- `stamp_cost` est l'exigence entrante. Le coût sortant d'un envoi
  vient toujours de l'announce du pair sauf si vous passez
  `stamp_cost=` à `bot.send()`.
- `include_tickets` (True par défaut) joint un ticket de réponse aux
  messages sortants, pour qu'un pair qui exige des stamps puisse
  répondre sans payer. Remplacez par envoi avec `include_ticket=`.
- `request_unknown_identities=True` demande au réseau une identité
  d'expéditeur quand un message arrive d'une source inconnue, ce qui
  aide les contrôles de stamps et de signatures à aboutir plutôt que
  d'échouer à l'aveugle.

Le contrôle à l'exécution est sous [Contrôles du
routeur](#controles-du-routeur) : `set_inbound_stamp_cost`,
`enforce_stamps`, `ignore_stamps`, `generate_ticket` et les méthodes
d'inspection de tickets.

### Fonctionner comme nœud de propagation

Un bot peut aussi servir de nœud de propagation LXMF, stockant les
messages des pairs hors ligne :

``` python
bot = LXMFBot(
    enable_propagation_node=True,
    message_storage_limit_mb=500,
)

bot.set_message_storage_limit(750)
stats = bot.get_propagation_storage_stats()
```

`get_propagation_node_status()` couvre les deux rôles : il rapporte le
nœud sortant utilisé par ce bot et si celui-ci sert lui-même de nœud.
Contrôles liés : `announce_propagation_node()` annonce le nœud,
`set_retain_on_node()` conserve les messages livrés dessus, et
`allow_control_identity()` / `disallow_control_identity()` gèrent
quelles identités peuvent utiliser le canal de contrôle du nœud.

### Événements de livraison

`bot.delivery` enregistre un flux borné d'événements du cycle de vie
sortant pour observer le flux de messages sans lire les logs. Étapes :
`queued`, `deferred`, `dispatched`, `delivered`, `failed`,
`cancelled`, `dropped`. La queue récente est persistée en stockage et
restaurée au démarrage.

``` python
@bot.on_delivery_event()
def watch(event):
    print(event["stage"], event.get("destination"), event.get("reason"))

# Ou inspection directe
recent = bot.delivery.recent(20)
failures = bot.delivery.recent(stage="failed")
to_peer = bot.delivery.recent(destination="aa11bb...")
```

Chaque événement est un dict avec `ts`, `stage` et optionnellement
`destination`, `message_id`, `hash`, `method`, `attempts`, `reason`,
`title`.

Les admins disposent d'une commande `/delivery [limit]` qui rend la
même chronologie dans le chat, et `lxmfy debug` affiche un résumé de
la chronologie des livraisons dans les contrôles du pipeline
d'envoi.

### Commandes d'administration intégrées

Ces commandes sont enregistrées automatiquement et exigent que
l'expéditeur soit dans `admins` quand les permissions sont activées :

| Commande | Action |
| --- | --- |
| `/queue` | Affiche la file sortante du routeur, la file interne et les envois retenus |
| `/cancel <id|all>` | Annule les messages sortants en attente |
| `/inbox [cancel <hash|all>]` | Liste ou annule les transferts entrants actifs |
| `/delivery [n]` | Affiche les n derniers événements de livraison (15 par défaut, max 50) |
| `/loadext <name>` | Charge une extension cog |
| `/reloadext <name>` | Recharge une extension cog chargée |

### Contrôles du routeur

Fines surcouches au-dessus du `LXMRouter` sous-jacent pour le contrôle
des expéditeurs, les tickets, la gestion de la file sortante et la
synchronisation du nœud de propagation. Tous prennent les hashes de
destination en strings hex et renvoient `False` quand le routeur ne
tourne pas (par exemple en `test_mode`).

**Contrôle des expéditeurs (entrant)**

- `ignore_destination(destination)` / `unignore_destination(destination)` / `is_ignored(destination)`:
  Jette les messages entrants d'un expéditeur
- `allow_destination(destination)` / `disallow_destination(destination)`:
  Gestion de la whitelist quand le routeur tourne en mode allow-list
- `prioritise_destination(destination)` / `unprioritise_destination(destination)`:
  Liste des expéditeurs prioritaires
- `set_inbound_stamp_cost(stamp_cost)`: Exige un coût de stamp sur les
  messages entrants (`None` efface)
- `enforce_stamps()` / `ignore_stamps()`: Bascule de l'exigence de
  stamps entrants

**Tickets**

- `generate_ticket(destination, expiry=None)`: Émet un ticket de stamp
  entrant pour un expéditeur
- `get_inbound_tickets(destination)`: Tickets détenus pour un
  expéditeur
- `get_outbound_ticket(destination)` / `get_outbound_ticket_expiry(destination)` /
  `get_outbound_stamp_cost(destination)`: État du ticket sortant
  appris du réseau

**File sortante**

- `outbound_queue()`: Snapshot des messages sortants en attente
- `get_outbound_progress(lxm_hash)`: Progression de livraison d'un
  hash de message, ou `None`
- `cancel_outbound(message_id)`: Retire un message en file avant la
  livraison
- `delivery_link_available(destination)`: Si un lien RNS actif existe
  vers la destination

**File entrante**

- `has_message(message_hash)`: Si un hash LXM entrant a déjà été
  livré
- `inbound_count()`: Transferts entrants de ressources en cours
- `inbound_transfers()`: Snapshot de chaque transfert avec hash,
  taille, progression et statut
- `cancel_inbound(resource_hash)`: Avorte un transfert entrant actif
- `cancel_all_inbound()`: Avorte tous les transferts entrants actifs,
  renvoie le nombre annulé

**Découverte de pairs**

Métadonnées d'announce des destinations que ce nœud a entendues :

- `get_peer_app_data(destination)`: Bytes app_data annoncés bruts
- `get_peer_lxmf_data(destination)`: Métadonnées d'announce LXMF
  décodées (`display_name`, `stamp_cost`, `capabilities`), ou `None`
  quand le pair n'a pas annoncé de données LXMF valides
- `get_peer_announce(destination)`: Enregistrement d'announce complet
  avec hops, received_at, interface et app_data
- `list_peer_announces(limit=100)`: Tous les announces entendus, le
  plus récent d'abord

**Propagation**

- `sync_propagation_node(max_messages=None)`: Récupère les messages du
  nœud de propagation configuré
- `cancel_propagation_sync()`: Stoppe une synchronisation en cours
- `get_propagation_stats()`: État de transfert et limites du nœud, ou
  `None`
- `set_retain_on_node(retain)`: Conserve les messages livrés sur le
  nœud
- `announce_propagation_node()`: Annonce ce nœud comme nœud de
  propagation
- `allow_control_identity(destination)` / `disallow_control_identity(destination)`:
  Whitelist du canal de contrôle de propagation

**Ingestion**

- `ingest_lxm_uri(uri)`: Importe un message URI `lxm://` dans la file
  entrante

## Diagnostic

Quand les messages ne circulent pas, le débogueur vérifie tout le
chemin au lieu de deviner : configuration Reticulum, état de
l'instance partagée, interfaces, identité, comportement d'announce,
configuration de livraison et pipeline d'envoi.

``` bash
lxmfy debug                          # rapport doctor complet, enregistré dans un fichier
lxmfy debug probe <hash> --request-path --wait 30
lxmfy debug send <hash>              # trace un envoi de test
lxmfy debug receive                  # vérifie la disponibilité en réception
lxmfy debug compare <hash_a> <hash_b>
lxmfy debug tips                     # corrections des erreurs courantes
```

Les rapports sont expurgés pour la vie privée par défaut : les chemins
home et les hashes sont tronqués. `--json` émet une sortie lisible
machine, `-o FICHIER` écrit le rapport, `--no-save` saute le fichier,
`--no-privacy` conserve les valeurs complètes pour un usage local, et
`--no-color` ou `NO_COLOR` désactive la sortie ANSI.

Les mêmes contrôles sont appelables depuis le code :

``` python
report = bot.diagnose_connectivity()            # rapport doctor en dict
probe = bot.diagnose_destination(               # sonde d'identité et de route
    "<peer_hash>", request_path=True, wait=30,
)

debugger = bot.get_debugger()                   # API complète
checks = debugger.check_send_pipeline()
verdict = debugger.run_doctor(destination)
```

`lxmfy/debugger.py` exporte aussi un helper autonome
`diagnose_destination(hash, ...)` plus les types de rapport
`CheckResult`, `DestinationProbe`, `DoctorReport` et `MessageDebugger`
pour vos outils.

## Gestionnaires de messages

LXMFy fournit des décorateurs pour gérer différents types de messages
entrants :

### Gestionnaire de premier message

Gérez le premier message de chaque utilisateur :

``` python
@bot.on_first_message()
def welcome_user(sender, message):
    content = message.content.decode("utf-8")
    bot.send(sender, f"Welcome! You said: {content}")
    return True  # Renvoyer True pour arrêter le traitement
```

### Gestionnaire de messages général

Gérez tous les messages entrants avant le traitement des commandes :

``` python
@bot.on_message()
def handle_all_messages(sender, message):
    content = message.content.decode("utf-8").strip()

    # Logique personnalisée ici
    if content.startswith("echo:"):
        bot.send(sender, content[5:])
        return True  # Arrêter le traitement

    return False  # Continuer vers le traitement des commandes
```

Les gestionnaires de messages sont appelés dans cet ordre : 1.
Gestionnaire de premier message (si c'est le premier message de cet
expéditeur) 2. Gestionnaires de messages généraux (enregistrés avec
`on_message()`) 3. Traitement des commandes (si le message commence par
le préfixe de commande)

### Callback de repli

`bot.received(fn)` enregistre un callback qui s'exécute en fin de
pipeline pour les messages que rien d'autre n'a consommés : aucun
gestionnaire de premier message, aucun gestionnaire `on_message`
renvoyant True, aucune commande ou intent NLP correspondant. Le
callback reçoit le même contexte de message que les commandes, avec
`msg.sender`, `msg.content`, `msg.reply()` et le reste.

``` python
@bot.received
def fallback(msg):
    msg.reply("Sorry, I did not understand that.")
```

À utiliser en fourre-tout pour la saisie en texte libre.

## Reticulum Relay Chat (RRC)

Les bots peuvent rejoindre des hubs [RRC](https://rrc.kc1awv.net/) via
des liens RNS avec des enveloppes CBOR. Paquet : `lxmfy.rrc`.

### Options de BotConfig

- `rrc_enabled` (bool, défaut `False`) : connecte les hubs configurés
  au démarrage
- `rrc_hubs` (liste de hachages hex) : hachages de destination des hubs
- `rrc_rooms` (liste de str) : salons à rejoindre automatiquement après
  WELCOME
- `rrc_nick` (str ou None) : pseudo dans HELLO et les messages de salon
- `rrc_dest_name` (str, défaut `"rrc.hub"`) : nom de destination utilisé
  pour construire la destination du hub
- `rrc_auto_reconnect` (bool, défaut `True`) : reconnecte après une
  perte de lien
- `rrc_persist_sessions` (bool, défaut `True`) : persiste les hubs et
  les salons entre les redémarrages
- `reticulum_config_dir` (str ou None) : répertoire de config
  Reticulum. Définissable aussi via `LXMFY_RETICULUM_CONFIG_DIR`.
  Utilisez la même config que MeshChatX (souvent `~/.reticulum`) pour
  que les annonces des hubs soient visibles.

### Exemple

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

# API d'exécution
# bot.connect_rrc(hub_hash, rooms=["general"])
# bot.rrc.send_message("general", "hello")
# bot.rrc.send_notice("general", "notice")
# bot.rrc.send_action("general", "waves")
# bot.rrc.join("ops")
# bot.rrc.part("ops")
# bot.rrc.status()
# bot.disconnect_rrc()
```

### Types exportés

- `RRCClient` : session mono-hub
- `RRCManager` : gestionnaire multi-hubs (`bot.rrc`)
- `RRCMessage` : charge utile d'événement de salon (`kind`, `room`,
  `text`, `nick`, `src`, `mention`, ...)
- `RRC_VERSION` : constante de version du protocole réseau
- `DEFAULT_DEST_NAME`: Nom de destination de hub par défaut
  (`"rrc.hub"`)
- `make_envelope`, `encode_envelope`, `decode_envelope`,
  `validate_envelope`, `normalize_room`: Helpers de format wire pour
  les outils qui parlent directement aux hubs

Les événements courants passés aux gestionnaires `@bot.on_rrc`
incluent `status`, `welcome`, `joined`, `parted`, `msg`, `notice`,
`action`, `motd`, `error` et `rtt`.

# Modèles

Le framework inclut plusieurs modèles de bots prêts à l'emploi :

## EchoBot

Bot echo simple qui répète les messages :

``` python
from lxmfy.templates import EchoBot

bot = EchoBot()
bot.run()
```

## NoteBot

Bot de prise de notes avec stockage JSON :

``` python
from lxmfy.templates import NoteBot

bot = NoteBot()
bot.run()
```

## ReminderBot

Bot de rappels avec stockage SQLite :

``` python
from lxmfy.templates import ReminderBot

bot = ReminderBot()
bot.run()
```

## RRCBot

Bot de salon RRC qui rejoint les hubs configurés et répond aux
`@mentions`. Utilise par défaut le hub
`664fc0e8d2e448658e37bb3f34e6c88f`, le salon `#general` et
`~/.reticulum` quand il est disponible.

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

# Outils CLI

Le framework fournit des outils en ligne de commande pour la gestion
des bots. Lancer `lxmfy` sans argument ouvre un menu interactif.

``` bash
# Scaffold interactif d'un projet complet
lxmfy init mybot                 # répertoire du projet, bot.py, cogs/, README
lxmfy init --here --yes          # répertoire courant, accepte tous les défauts

# Créer un fichier de bot unique
lxmfy create mybot
lxmfy create --template echo mybot
lxmfy create --template rrc my_rrc_bot
lxmfy create mybot --no-cogs     # saute le paquet cogs
lxmfy create --output dir/bot.py --name MyBot

# Exécuter un bot de modèle
lxmfy run echo
lxmfy run rrc
lxmfy run reminder --name "MyReminder"

# Diagnostiquer la connectivité (voir la section Diagnostic)
lxmfy debug
lxmfy debug probe <hash> --request-path --wait 30

# Tester la vérification de signature avec un message
lxmfy signatures test

# Activer la vérification de signature
lxmfy signatures enable

# Désactiver la vérification de signature
lxmfy signatures disable
```

`lxmfy init` demande le nom du projet, le modèle, le backend de
stockage, le préfixe de commandes et les hashes d'admin. Chaque
question accepte un flag à la place : `--dir`, `--bot-name`,
`--template`, `--storage`, `--prefix`, `--admins`, `--no-cogs`,
`--force`, `--yes`. Sur un stdin non-TTY, les défauts sont pris.

Modèles pour `create` et `run` : `basic`, `echo`, `reminder`, `note`,
`cogtest`, `rrc`.

# Gestion des erreurs

Capturez les erreurs d'arrêt et d'exécution autour de `bot.run()` :

``` python
try:
    bot.run()
except KeyboardInterrupt:
    bot.cleanup()
except Exception as e:
    logger.error(f"Error running bot: {str(e)}")
```

# Référence des modules

Généré à partir des docstrings des sources.

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
