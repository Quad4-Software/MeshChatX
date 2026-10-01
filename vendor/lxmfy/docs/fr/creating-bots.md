# Création de bots

## Structure de base

Un bot LXMFy minimal comprend :

1.  L'import de `LXMFBot`.
2.  L'instanciation de `LXMFBot` avec la configuration voulue.
3.  La définition de commandes ou de gestionnaires d'événements.
4.  Le lancement du bot avec `bot.run()`.

``` python
from lxmfy import LXMFBot

# 1. Instancier le bot
bot = LXMFBot(
    name="SimpleBot",
    command_prefix="!",
    storage_path="simple_data"
)

# 2. Définir les commandes
@bot.command(name="ping", description="Responds with pong")
def ping_command(ctx):
    # ctx est un objet de contexte contenant les infos du message
    # ctx.sender : hachage LXMF de l'expéditeur
    # ctx.content : contenu complet du message
    # ctx.args : liste des arguments après la commande
    # ctx.reply(message) : fonction pour envoyer une réponse
    #   (accepte aussi des arguments nommés comme title="My Title", lxmf_fields=some_fields)
    ctx.reply("Pong!")

# Pour les tâches longues, vous pouvez utiliser des commandes en thread :
# import time
# @bot.command(name="long_op", description="Performs a long operation in a separate thread", threaded=True)
# def long_op_command(ctx):
#     ctx.reply("Starting long operation...")
#     time.sleep(10) # Simule une opération longue
#     ctx.reply("Long operation complete!")
# Important : les commandes en thread ne doivent pas interagir directement avec RNS ou lxmfy.transport.py.

@bot.command(name="greet", description="Greets the user")
def greet_command(ctx):
    if ctx.args:
        name = " ".join(ctx.args)
        ctx.reply(f"Hello, {name}!")
    else:
        ctx.reply("Hello there! Tell me your name: !greet <your_name>")

# 3. Lancer le bot
if __name__ == "__main__":
    print(f"Starting bot: {bot.config.name}")
    print(f"Bot LXMF Address: {bot.local.hash}")
    bot.run()
```

## Utilisation des modèles

LXMFy fournit plusieurs modèles pour les types de bots courants. Vous
pouvez utiliser la CLI pour générer un fichier de bot à partir d'un
modèle.

Pour un répertoire de projet complet plutôt qu'un fichier
unique, `lxmfy init` génère `bot.py`, un paquet `cogs`, un README et
un `.gitignore`, en demandant au passage le modèle, le backend de
stockage, le préfixe de commandes et les hashes d'admin.

``` bash
# Créer un bot echo
lxmfy create --template echo my_echo_bot

# Créer un bot de rappels (utilise le stockage SQLite)
lxmfy create --template reminder my_reminder_bot

# Créer un bot de prise de notes (utilise le stockage JSON)
lxmfy create --template note my_note_bot

# Créer un bot de test de cogs (teste les fonctions de chargement des cogs)
lxmfy create --template cogtest my_cog_test_bot

# Créer un bot de salon RRC (rejoint des hubs et répond aux @mentions)
lxmfy create --template rrc my_rrc_bot

# Ou exécuter le modèle directement
lxmfy run rrc
```

Ces commandes créent un fichier Python (par ex. `my_echo_bot.py`) qui
importe et exécute le modèle choisi. Vous pouvez ensuite modifier le
fichier généré ou le code du modèle lui-même (`lxmfy/templates/...`).

**Exemple de fichier généré (`my_cog_test_bot.py`) :**

``` python
from lxmfy.templates import CogTestBot

if __name__ == "__main__":
    bot = CogTestBot() # Crée une instance du modèle CogTestBot
    # Vous pouvez éventuellement remplacer le nom par défaut :
    # bot.bot.name = "My Cog Test Bot"
    bot.run()
```

## Configuration du bot

Lors de la création d'une instance `LXMFBot`, vous pouvez passer divers
arguments nommés pour configurer son comportement. Voir la section
`BotConfig` de la [Référence API](api-reference.md) ou le [guide de
démarrage rapide](quick-start.md) pour la liste des options courantes.

``` python
from lxmfy import LXMFBot

bot = LXMFBot(
    name="ConfiguredBot",
    announce=3600, # Annoncer toutes les heures
    admins={"your_admin_hash_here"}, # Définir les admins
    command_prefix="$", # Utiliser '$' comme préfixe
    storage_type="sqlite", # Utiliser une base SQLite
    storage_path="data/my_bot_data.db", # Chemin du fichier de base de données
    rate_limit=10, # Autoriser 10 messages / minute
    cooldown=30, # Refroidissement de 30 secondes
    permissions_enabled=True # Activer les permissions par rôles
)

if __name__ == "__main__":
    # Vous pouvez aussi modifier la config après l'instanciation
    # Remarque : certains réglages sont préférables à l'initialisation
    bot.config.max_warnings = 5
    bot.spam_protection.config.max_warnings = 5 # Mettre à jour aussi la protection anti-spam

    bot.run()
```

### Définir une icône de bot (champ LXMF)

Vous pouvez donner à votre bot une icône personnalisée qui apparaît
dans les clients LXMF compatibles. Elle utilise le champ
`LXMF.FIELD_ICON_APPEARANCE` et peut être définie à l'envoi des
messages.

Assurez-vous d'abord d'avoir les imports nécessaires :

``` python
from lxmfy import IconAppearance, pack_icon_appearance_field
```

Vous pouvez ensuite définir et utiliser l'icône :

``` python
# Dans votre classe de bot ou votre configuration
icon_data = IconAppearance(
    icon_name="robot_2",  # Choisir dans Material Symbols
    fg_color=b'\x00\xFF\x00',  # Vert
    bg_color=b'\x33\x33\x33'   # Gris foncé
)
self.bot_icon_field = pack_icon_appearance_field(icon_data)

# Lors de l'envoi d'un message ou d'une réponse :
ctx.reply("Message from your bot!", lxmf_fields=self.bot_icon_field)
# ou
# bot.send(destination, "Another message", lxmf_fields=self.bot_icon_field)
```

Ce `self.bot_icon_field` peut être précalculé et réutilisé pour tous
les messages envoyés par le bot.

## Commandes structurées via les champs LXMF

En plus des commandes textuelles, LXMFy prend en charge les commandes
envoyées via les champs de message LXMF avec `FIELD_COMMANDS` (`0x09`).
C'est utile pour les flux requête/réponse structurés entre clients LXMF
et bots.

Quand un message contient `FIELD_COMMANDS`, le bot extrait le nom de la
commande et ses arguments, les route dans le même registre de commandes
que les commandes textuelles, et inclut automatiquement `FIELD_RESULTS`
(`0x0A`) dans la réponse.

**Réception de commandes structurées**

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

L'objet `ctx` des callbacks de commandes par champs inclut :

- `ctx.fields` : le dict brut des champs LXMF du message entrant
- `ctx.request_id` : le `request_id` du `FIELD_COMMANDS` entrant
  (s'il y en a un)

**Envoi d'une commande structurée depuis un client LXMF**

``` python
import LXMF
from lxmfy import FIELD_COMMANDS

lxm = LXMF.LXMessage(
    destination,
    source,
    b"",  # le contenu peut être vide pour les commandes par champs seuls
    desired_method=LXMF.LXMessage.DIRECT,
)
lxm.fields[FIELD_COMMANDS] = {
    "command": "add",
    "args": ["3", "5"],
    "request_id": "req-42",  # optionnel, pour la corrélation
}
router.handle_outbound(lxm)
```

**Désactivation des commandes par champs**

Si vous voulez que le bot ignore `FIELD_COMMANDS` et ne traite que les
commandes textuelles, définissez :

``` python
bot = LXMFBot(
    name="TextOnlyBot",
    lxmf_commands_enabled=False,
)
```

## Utilisation des cogs (extensions)

Les cogs permettent d'organiser vos commandes et écouteurs d'événements
dans des fichiers séparés (modules), afin de garder un fichier de bot
principal plus propre.

1.  **Créez un répertoire `cogs`** (ou celui défini par `cogs_dir` dans
    `BotConfig`).
2.  **Créez des fichiers Python** dans le répertoire `cogs` (par ex.
    `utility.py`).
3.  **Définissez une classe** qui hérite de `lxmfy.Cog` (optionnel mais
    recommandé) ou qui est simplement une classe standard.
4.  **Définissez des commandes** comme méthodes de la classe avec le
    décorateur `@Command`.
5.  **Créez une fonction `setup(bot)`** dans le fichier du cog, que
    LXMFy appellera pour enregistrer le cog.

**Exemple (`cogs/utility.py`) :**

``` python
from lxmfy import Command
from lxmfy.commands import Cog  # Importer Cog en cas d'héritage
import time

class UtilityCog: # Ou class UtilityCog(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = time.time()

    @Command(name="uptime", description="Shows bot uptime")
    # Remarque : les méthodes des cogs prennent souvent 'self' et 'ctx'
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
        time.sleep(7) # Simule une opération longue
        ctx.reply("Long cog task completed!")

# Cette fonction est obligatoire pour que le cog soit chargé
def setup(bot):
    cog_instance = UtilityCog(bot)
    bot.add_cog(cog_instance) # Enregistre l'instance du cog auprès du bot
```

**Fichier principal du bot (`my_bot.py`) :**

``` python
from lxmfy import LXMFBot

bot = LXMFBot(
    name="CogBot",
    cogs_enabled=True, # Assurez-vous que les cogs sont activés (défaut)
    cogs_dir="cogs" # Pointe vers le répertoire
)

if __name__ == "__main__":
    # Les cogs sont chargés automatiquement pendant l'initialisation
    # de LXMFBot si cogs_enabled vaut True.
    bot.run()
```

Au démarrage, le bot trouve automatiquement `utility.py`, appelle sa
fonction `setup`, qui crée une instance de `UtilityCog` et
l'enregistre via `bot.add_cog()`. Les commandes définies dans le cog
(`uptime`, `info`) sont alors disponibles.

## Cogs en scripts externes (support multilangage)

Vous pouvez aussi écrire des extensions de bot dans des langages autres
que Python (Bash, Ruby, Perl, Go, C) avec les cogs en scripts externes.

1.  **Créez un script exécutable** dans votre répertoire `cogs`.
2.  **Ajoutez un shebang** en tête du script (par ex. `#!/bin/bash`).
3.  **Assurez-vous que le script est exécutable** (`chmod +x
    your_script`).

Au démarrage, le bot enregistre automatiquement tout fichier exécutable
du répertoire `cogs` (ne finissant pas par `.py`) comme commande du
bot.

**Protocole d'arguments :**

- `$1` : hachage LXMF de l'expéditeur.
- `$2` : contenu complet du message.
- `$3`, `$4`, ... : arguments individuels de la commande.

**Variables d'environnement :**

- `LXMFY_SENDER` : le hachage d'identité de l'expéditeur.
- `LXMFY_CONTENT` : le contenu complet du message.
- `LXMFY_HAS_ADMIN` : `true` ou `false` selon le statut admin de
  l'expéditeur.

**Exemple de cog Bash (`cogs/greet.sh`) :**

``` bash
#!/bin/bash
echo "Hello from Bash! You sent: $2"
```

Quand un utilisateur envoie `/greet hello`, le bot exécute ce script et
répond avec sa sortie standard : `Hello from Bash! You sent: /greet
hello`.

## Classification locale d'intentions NLP

LXMFy embarque un classifieur d'intentions local. Il fait correspondre
le texte des messages à des phrases d'exemple étiquetées quand le texte
ne correspond pas exactement à un préfixe de commande.

1.  **Activez le NLP** dans la configuration du bot :
    `nlp_enabled=True`.
2.  **Définissez des intentions** avec le décorateur `@bot.intent`.

``` python
@bot.intent("help", examples=["how do I use this?", "show me commands", "help me please"])
def help_intent(msg):
    msg.reply("I can help! Try typing /help to see a list of commands.")
```

La correspondance utilise des vecteurs TF-IDF et la similarité cosinus.
Tout le calcul s'effectue sur l'hôte du bot. Aucun texte n'est envoyé à
une API externe.

**Export et import du modèle**

Exportez et importez un modèle entraîné pour que les gros bots évitent
un réentraînement à chaque démarrage :

``` python
# Exporter le modèle
model_data = bot.nlp.export_model()
# Enregistrer model_data dans un fichier ou une base de données

# Plus tard, le réimporter
bot.nlp.import_model(model_data)
```

## Support de RNS Link

Les bots peuvent établir des liens RNS directs et y répondre, pour du
trafic avec état, en flux ou à plus haut débit que les paquets LXMF
unitaires.

1.  **Activez le support des liens** dans la configuration :
    `link_support_enabled=True`.
2.  **Demandez un lien** : `bot.request_link(destination_hash)`. Vous
    pouvez aussi préciser un nom d'application et des aspects
    personnalisés : `bot.request_link(dest, callback, "my_app",
    "aspect1")`.
3.  **Gérez les liens entrants** : enregistrez un callback avec
    `bot.on_link(handler)`.

``` python
def handle_link(link):
    print(f"Link established with {RNS.hexrep(link.destination.hash)}")
    # Vous pouvez maintenant utiliser le lien pour une communication RNS directe

bot.on_link(handle_link)
```

**Sécurité et sandbox :**

- **Timeouts :** les cogs externes ont un timeout par défaut (30 s)
  pour éviter les blocages. Configurable via `external_cogs_timeout`.
- **Threads :** tous les cogs externes s'exécutent dans des threads
  séparés et ne bloquent pas le bot.
- **Sandbox du processus du bot (Linux seulement) :** quand
  `landlock_enabled=True` (défaut) et que le noyau prend en charge
  Landlock LSM (5.13+), le bot applique une sandbox de système de
  fichiers à son propre processus après le démarrage. Les chemins
  inscriptibles sont limités au stockage, à la config, aux cogs, à la
  config Reticulum et aux répertoires temporaires. Surchargez avec la
  variable d'environnement `LXMFY_LANDLOCK=0` pour désactiver ou
  `LXMFY_LANDLOCK=1` pour forcer une tentative.
- **Sandbox des cogs externes (Linux seulement) :** quand
  `external_cogs_sandbox_enabled=True` (défaut), les cogs en scripts
  exécutables tournent dans un environnement restreint. Définissez
  `external_cogs_sandbox_type` parmi :
  - `auto` (défaut) : préfère Landlock s'il est pris en charge, sinon
    `bubblewrap` (`bwrap`), sinon `firejail`
  - `landlock` : sandbox Landlock seule via `preexec_fn` (règles plus
    étroites que la sandbox du processus du bot)
  - `bwrap` : sandbox bubblewrap en bind en lecture seule
  - `firejail` : profil privé firejail sans réseau
  - `none` : pas de sandbox pour le sous-processus
- **Statut :** appelez `bot.get_landlock_status()` pour inspecter le
  support noyau, si Landlock a été demandé, et si la sandbox du
  processus du bot est active.

## Gestion des messages

LXMFy offre plusieurs façons de gérer les messages entrants à
différentes étapes du traitement.

### Gestionnaire de premier message

Gérez le premier message de chaque nouvel utilisateur (utile pour les
messages de bienvenue) :

``` python
from lxmfy import LXMFBot

bot = LXMFBot(
    name="WelcomeBot",
    first_message_enabled=True  # Doit être True (défaut)
)

@bot.on_first_message()
def welcome_new_user(sender, message):
    content = message.content.decode("utf-8")
    bot.send(
        sender,
        f"Welcome to the bot! You said: {content}\n\n"
        "Type /help to see available commands."
    )
    return True  # Renvoyer True pour arrêter le traitement de ce message

if __name__ == "__main__":
    bot.run()
```

### Gestionnaire de messages général

Gérez tous les messages entrants avant le traitement des commandes :

``` python
from lxmfy import LXMFBot

bot = LXMFBot(name="EchoBot")

@bot.on_message()
def echo_non_commands(sender, message):
    content = message.content.decode("utf-8").strip()

    # Vérifie s'il s'agit d'une commande : si oui, laisser le gestionnaire de commandes s'en occuper
    if content.startswith(bot.config.command_prefix):
        command_name = content.split()[0][len(bot.config.command_prefix):]
        if command_name in bot.commands:
            return False  # Laisser le gestionnaire de commandes la traiter

    # Pas une commande : la renvoyer en écho
    bot.send(sender, f"You said: {content}")
    return False  # Renvoyer False pour continuer le traitement (aucune commande ne correspondra)

@bot.command(name="hello", description="Say hello")
def hello_command(ctx):
    ctx.reply("Hello! This is a command response.")

if __name__ == "__main__":
    bot.run()
```

Ordre de traitement des gestionnaires de messages :

1.  **Gestionnaire de premier message** (si
    `first_message_enabled=True` et que c'est le premier message de cet
    expéditeur)
2.  **Gestionnaires de messages généraux** (enregistrés avec
    `@bot.on_message()`)
3.  **Traitement des commandes** (si le message correspond à une
    commande enregistrée)

Les gestionnaires peuvent renvoyer `True` pour arrêter le traitement ou
`False` pour passer à l'étape suivante.

## Gestion des événements

Vous pouvez enregistrer des gestionnaires pour divers événements du bot
avec le décorateur `@bot.events.on()`.

``` python
from lxmfy import LXMFBot
from lxmfy.events import EventPriority # Optionnel, pour la priorité

bot = LXMFBot(name="EventBot")

@bot.events.on("message_received")
def log_message(event):
    # L'objet événement contient les détails
    sender = event.data.get("sender")
    message_content = event.data.get("message").content.decode('utf-8', errors='ignore')
    print(f"Received message from {sender}: {message_content}")

    # Vous pouvez annuler le traitement de l'événement (par ex. stopper la gestion du message)
    # if sender == "some_blocked_hash":
    #    event.cancel()

@bot.events.on("command_executed", priority=EventPriority.LOW)
def log_command(event):
    # Exemple : event.data peut contenir {'command_name': 'ping', 'sender': '...', ...}
    command_name = event.data.get('command_name', 'unknown')
    sender = event.data.get('sender', 'unknown')
    print(f"Command '{command_name}' executed by {sender}")

# Vous pouvez aussi définir des événements personnalisés
@bot.command(name="special")
def special_command(ctx):
    ctx.reply("Doing something special!")
    # Distribuer un événement personnalisé
    bot.events.dispatch(Event("special_action_taken", data={"user": ctx.sender}))

@bot.events.on("special_action_taken")
def handle_special(event):
    user = event.data.get("user")
    print(f"Special action was taken by user: {user}")


if __name__ == "__main__":
    bot.run()
```

Voir `lxmfy/events.py` pour plus de détails sur la structure `Event` et
les priorités.

## Stockage

LXMFy fournit des backends de stockage JSON, SQLite, MsgPack et en mémoire.

- **JSON :** simple et lisible. Adapté aux petits ensembles de données.
  Configurez avec `storage_type="json"` et
  `storage_path="your_data_dir"`.
- **SQLite :** plus efficace pour les gros ensembles de données ou les
  écritures fréquentes. Configurez avec `storage_type="sqlite"` et
  `storage_path="your_db_file.db"`.
- **MsgPack :** format binaire compact avec la même disposition
  un-fichier-par-clé que JSON. Configurez avec `storage_type="msgpack"`
  et `storage_path="your_data_dir"`.
- **Memory :** stockage entièrement en RAM. L'état est perdu à
  l'arrêt. Configurez avec `storage_type="memory"`.

Vous pouvez accéder à l'interface de stockage via `bot.storage` :

``` python
# Enregistrer des données
bot.storage.set("user_prefs:" + ctx.sender, {"theme": "dark"})

# Récupérer des données (avec une valeur par défaut)
prefs = bot.storage.get("user_prefs:" + ctx.sender, {})
theme = prefs.get("theme", "light")

# Vérifier l'existence de données
if bot.storage.exists("some_key"):
    print("Key exists!")

# Supprimer des données
bot.storage.delete("old_data_key")

# Chercher les clés par préfixe (utile pour lister les données utilisateur)
user_keys = bot.storage.scan("user_prefs:")
for key in user_keys:
    user_data = bot.storage.get(key)
    print(f"Data for {key}: {user_data}")
```

Voir `lxmfy/storage.py` et la référence API pour plus de détails.

## Permissions

LXMFy inclut un système de permissions par rôles optionnel. Activez-le
avec `permissions_enabled=True` lors de l'initialisation de `LXMFBot`.

- **Rôles :** définissez des rôles avec des permissions précises (par
  ex. `DefaultPerms.MANAGE_USERS`).
- **Permissions :** drapeaux granulaires définis dans `DefaultPerms`
  (par ex. `USE_COMMANDS`, `BYPASS_SPAM`).
- **Attribution :** attribuez des rôles à des hachages d'utilisateurs.

Voir `lxmfy/permissions.py`, la référence API et d'éventuels cogs
d'exemple (s'il en existe) pour les détails d'utilisation.

## Vérification des signatures

LXMFy fournit la configuration pour la signature et la vérification
cryptographiques intégrées de LXMF. Tous les messages LXMF sont
automatiquement signés par la pile LXMF/RNS. LXMFy vous permet
simplement d'appliquer des politiques de vérification des signatures.

**Configuration :**

Activez la vérification des signatures dans la configuration du bot :

``` python
bot = LXMFBot(
    name="SecureBot",
    signature_verification_enabled=True,  # Activer la vérification des signatures
    require_message_signatures=False      # Mettre True pour rejeter les messages non signés
)
```

**Fonctionnement :**

LXMF gère automatiquement toutes les opérations cryptographiques :

1.  **Messages sortants :** LXMF signe automatiquement tous les
    messages avec l'identité RNS de l'expéditeur pendant l'empaquetage.
2.  **Messages entrants :** LXMF valide automatiquement les signatures
    avec l'identité RNS de l'expéditeur et fournit les résultats de
    validation.
3.  **Rôle de LXMFy :** LXMFy vérifie les résultats de validation de
    LXMF et applique votre politique :
    - Si `signature_verification_enabled=False` : tous les messages
      sont acceptés (défaut)
    - Si `signature_verification_enabled=True` et
      `require_message_signatures=False` : les messages sont acceptés
      mais les signatures absentes ou invalides sont journalisées
    - Si `signature_verification_enabled=True` et
      `require_message_signatures=True` : les messages non signés ou
      invalides sont rejetés
4.  **Intégration des permissions :** les utilisateurs avec la
    permission `BYPASS_SPAM` peuvent contourner les exigences de
    vérification des signatures.

**Gestion via la CLI :**

Vous pouvez gérer les réglages de vérification des signatures avec la
CLI :

``` bash
# Tester la vérification des signatures
lxmfy signatures test

# Activer la vérification des signatures
lxmfy signatures enable

# Désactiver la vérification des signatures
lxmfy signatures disable
```

**Détails techniques :**

LXMF utilise des signatures Ed25519 fournies par le système
cryptographique de RNS. Chaque message LXMF inclut la signature de
l'expéditeur, validée contre son identité RNS connue. LXMFy lit
simplement les propriétés `message.signature_validated` et
`message.unverified_reason` de LXMF pour appliquer la politique de
sécurité de votre bot.

## Livraison des messages

### Utilisation des nœuds de propagation

Envoyez des messages via des nœuds de propagation LXMF précis :

``` python
from lxmfy import LXMFBot

bot = LXMFBot(name="PropagationBot")

@bot.command(name="send", description="Send via propagation node")
def send_command(ctx):
    # Définir un nœud de propagation précis une fois (au niveau config)
    bot.set_propagation_node("<propagation_node_hash_here>")

    # Envoyer avec la stratégie de livraison configurée
    bot.send(
        ctx.sender,
        "This message will use direct delivery with propagation fallback as configured"
    )
```

Utilisez un nœud de propagation quand la destination est hors ligne ou
que la livraison directe échoue systématiquement sur le chemin actuel.

### Configuration des réessais

Configurez les réessais automatiques pour les livraisons échouées via
la config du bot :

``` python
from lxmfy import LXMFBot

bot = LXMFBot(name="ReliableBot")

bot = LXMFBot(
    name="ReliableBot",
    direct_delivery_retries=5,  # Réessayer la livraison directe jusqu'à 5 fois
    propagation_fallback_enabled=True
)

@bot.command(name="important", description="Send important message with retries")
def important_command(ctx):
    bot.send(ctx.sender, "This is an important message")

@bot.command(name="normal", description="Send with default retries")
def normal_command(ctx):
    # direct_delivery_retries vaut 3 par défaut
    bot.send(ctx.sender, "This message uses default retry settings")
```

Le système de réessais :

- Suit automatiquement les tentatives de livraison par destination
- Réessaie les livraisons directes échouées jusqu'à
  `direct_delivery_retries`
- Remet le compteur de réessais à zéro après une livraison réussie
- Journalise les tentatives de réessai et les échecs pour le débogage

### Envois différés et stamps

Deux détails de livraison à connaître tôt :

- **Envois différés** : quand l'identité de la destination n'est pas
  encore connue, `send()` retient le message en stockage (les clés de
  configuration `pending_sends_*` contrôlent le backlog) et le vide
  quand le pair annonce. Passez `defer=False` à un envoi pour jeter
  plutôt que retenir.
- **Stamps** : `stamp_cost` fixe une exigence de preuve de travail
  entrante, `require_stamps` rejette les messages qui la ratent, et
  `include_tickets` (par défaut) joint des tickets de réponse pour que
  les pairs puissent répondre à votre bot sans payer leur propre coût
  de stamp.

Quand la livraison déconne, `lxmfy debug` parcourt tout le chemin
(configuration, instance, interfaces, identité, pipeline d'envoi) et
écrit un rapport expurgé à partager. Les mêmes contrôles sont
appelables via `bot.diagnose_connectivity()` et
`bot.diagnose_destination(hash)`.

Voir la [Référence API](api-reference.md#livraison-des-messages) pour
toute la surface de livraison : réessais, nœuds de propagation,
persistance de file, le flux d'événements de livraison et les
commandes d'administration `/queue`, `/cancel`, `/inbox`, `/delivery`.

## Reticulum Relay Chat (RRC)

Les bots LXMFy peuvent rejoindre des hubs [RRC](https://rrc.kc1awv.net/)
comme clients ordinaires via des liens RNS avec des enveloppes CBOR.
C'est compatible avec NomadNet et les hubs de style rrcd (y compris
MeshChatX quand il héberge ou rejoint le même hub).

### La configuration Reticulum est importante

Le bot doit utiliser le **même** réseau Reticulum que le hub.
MeshChatX utilise typiquement `~/.reticulum` avec des interfaces
backbone ou TCP. Le répertoire `config/` local au projet utilise
souvent un nom d'instance isolé et AutoInterface seul, donc les
annonces du hub n'arrivent jamais et vous voyez `Hub identity
unknown`.

Préférez l'une de ces options :

- Définissez `reticulum_config_dir` sur votre config utilisateur
  (généralement `~/.reticulum`)
- Ou exportez `LXMFY_RETICULUM_CONFIG_DIR=~/.reticulum`
- Gardez MeshChatX ou `rnsd` en cours d'exécution pour que l'instance
  partagée soit active avant le démarrage du bot

Le modèle `rrc` utilise `~/.reticulum` par défaut quand ce répertoire
existe.

### Démarrage rapide avec le modèle

``` bash
lxmfy run rrc
```

Valeurs par défaut :

- Hub : `664fc0e8d2e448658e37bb3f34e6c88f`
- Salon : `#general`
- Config Reticulum : `~/.reticulum` (ou
  `LXMFY_RETICULUM_CONFIG_DIR`)

Vous devriez voir des journaux pour la connexion au hub, le welcome,
l'auto-join, et `RRC joined #general`.

### Bot RRC programmatique

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

Ou connectez-vous à l'exécution :

``` python
bot.connect_rrc("hub_destination_hash", rooms=["general"])
bot.rrc.send_message("general", "hello room")
bot.rrc.send_action("general", "waves")
bot.disconnect_rrc()
```

### Comportement de session

- HELLO / WELCOME, JOIN / PART, MSG / NOTICE / ACTION, PING / PONG,
  ERROR, RESOURCE_ENVELOPE
- Reconnexion automatique avec re-join des salons après WELCOME
- Application côté client de la limite de hubs et de la limite de débit
- Persistance des sessions entre les redémarrages
  (`rrc_persist_sessions`, activé par défaut)
- La persistance de la file LXMF sortante est séparée
  (`message_persistence_enabled`)
