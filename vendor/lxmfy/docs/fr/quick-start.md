# Démarrage rapide

## Prérequis

- Python 3.11+
- Reticulum Network Stack (`pip install rns`, version 1.5.4+)
- LXMF (`pip install lxmf`, version 1.1.1+, installé automatiquement
  avec LXMFy)
- CBOR (`cborx`, installé automatiquement, requis pour RRC)

=== "PyPI"

    ``` bash
    pip install lxmfy
    ```

=== "Source"

    ``` bash
    git clone https://github.com/Quad4-Software/LXMFy
    cd LXMFy
    poetry install
    ```

## Création de votre premier bot (avec la CLI)

Utilisez la CLI LXMFy pour générer la structure d'un projet. Deux
façons :

- `lxmfy init` pose quelques questions (nom, modèle, stockage,
  préfixe, admins) et écrit un répertoire de projet prêt à lancer.
- `lxmfy create` écrit un fichier de bot unique avec les défauts, sans
  questions.

Ce guide utilise `lxmfy create`.

1.  **Ouvrez votre terminal** dans le répertoire où vous voulez créer
    le projet de votre bot.

2.  **Exécutez la commande de création :**

    ``` bash
    lxmfy create my_first_bot
    ```

    Cette commande génère les fichiers suivants :

    - `my_first_bot.py` : le fichier principal du bot, configuré avec
      des valeurs par défaut raisonnables.
    - `cogs/` : un répertoire pour les extensions du bot (cogs).
    - `cogs/__init__.py` : fait du répertoire `cogs` un paquet Python.
    - `cogs/basic.py` : un cog d'exemple avec les commandes simples
      "hello" et "about".
    - `data/` : un répertoire où le bot stocke ses données (en JSON par
      défaut).
    - `config/` : un répertoire où le bot stocke son identité et l'état
      de ses annonces.

3.  **Examinez le fichier `my_first_bot.py` :**

    ``` python
    from lxmfy import LXMFBot

    bot = LXMFBot(
        name="my_first_bot",  # Nom du bot utilisé dans les annonces et l'identité
        announce=600,         # Intervalle d'annonce en secondes (10 minutes)
        announce_immediately=True, # Annoncer au premier démarrage ?
        admins=set(),         # Ensemble des hachages d'adresses LXMF des admins
        hot_reloading=False,  # Activer/désactiver le rechargement à chaud des cogs
        rate_limit=5,         # Nombre max de messages par minute et par utilisateur
        cooldown=60,          # Période de refroidissement en secondes pour la limite de débit
        max_warnings=3,       # Avertissements avant bannissement pour spam
        warning_timeout=300,  # Délai (secondes) avant remise à zéro des avertissements
        command_prefix="/",   # Préfixe des commandes (par ex. /hello)
        cogs_dir="cogs",      # Répertoire de chargement des cogs
        cogs_enabled=True,    # Activer/désactiver le chargement des cogs
        permissions_enabled=False, # Activer/désactiver le système de permissions par rôles
        storage_type="json",  # Backend de stockage ("json", "sqlite", "msgpack" ou "memory")
        storage_path="data",  # Chemin des fichiers de stockage / de la base
        first_message_enabled=True, # Activer le traitement spécial des premiers messages
        event_logging_enabled=True, # Journaliser les événements dans le stockage ?
        max_logged_events=1000,   # Nombre max d'événements conservés au journal
        event_middleware_enabled=True, # Activer le middleware d'événements ?
        announce_enabled=True,   # Activer/désactiver les annonces réseau
        signature_verification_enabled=False, # Activer/désactiver la vérification cryptographique des signatures
        require_message_signatures=False     # Exiger que tous les messages soient signés
    )

    # Pour ajouter un admin, trouvez votre hachage d'adresse LXMF et ajoutez-le ici :
    # bot.config.admins.add("votre_hachage_lxmf_ici")
    # bot.admins = bot.config.admins # Pour que l'instance en cours le sache

    # Exemple de préparation d'un champ d'icône LXMF (optionnel)
    # from lxmfy import IconAppearance, pack_icon_appearance_field
    # try:
    #     icon_data = IconAppearance(icon_name="emoji_objects", fg_color=b'\xFF\xA5\x00', bg_color=b'\x8B\x45\x13') # Orange sur marron
    #     bot.icon_field = pack_icon_appearance_field(icon_data) # À conserver pour send/reply
    # except Exception as e:
    #     print(f"Impossible de préparer le champ d'icône : {e}")
    #     bot.icon_field = None

    if __name__ == "__main__":
        print(f"Démarrage du bot : {bot.config.name}")
        print(f"Adresse LXMF du bot : {bot.local.hash}") # Affiche l'adresse du bot
        bot.run()
    ```

4.  **(Optionnel) Ajoutez votre hachage d'admin :**

    - Trouvez votre hachage d'adresse LXMF (par ex. depuis votre client
      Reticulum comme Sideband ou NomadNet).
    - Décommentez et modifiez la ligne `bot.config.admins.add(...)` dans
      `my_first_bot.py`, en remplaçant `"votre_hachage_lxmf_ici"` par
      votre hachage réel.

5.  **Lancez votre bot :**

    ``` bash
    python my_first_bot.py
    ```

    Votre bot démarre, affiche son adresse LXMF, peut envoyer un
    message d'annonce sur le réseau Reticulum, puis commence à écouter
    les messages.

## Interagir avec votre bot

1.  **Envoyez un message** à l'adresse LXMF du bot depuis votre client.
2.  **Essayez la commande d'exemple :** envoyez `/hello` au bot. Il
    devrait répondre "Hello `<votre_hachage>` !". Si vous avez
    décommenté l'exemple d'icône ci-dessus, cette réponse peut aussi
    porter une icône.
3.  **Essayez la commande d'aide :** envoyez `/help`.

Si rien n'arrive, lancez `lxmfy debug` depuis le répertoire du projet.
Il vérifie la configuration Reticulum, les interfaces, l'identité et
le pipeline d'envoi, et enregistre un rapport expurgé que vous pouvez
partager en demandant de l'aide.

## Quoi configurer ensuite

**Gestionnaires de messages**

- `@bot.on_first_message()` pour le premier message de chaque
  expéditeur
- `@bot.on_message()` pour tous les messages avant le traitement des
  commandes

**Livraison**

- `direct_delivery_retries` dans `LXMFBot(...)` réessaie la livraison
  directe avant le repli sur la propagation
- `propagation_node` (ou `bot.set_propagation_node(...)`) sélectionne
  un nœud de propagation LXMF précis
- La persistance de la file sortante est activée par défaut
  (`message_persistence_enabled=True`) avec une file bornée
  (`message_queue_size`)

**Reticulum Relay Chat (RRC)**

- Rejoignez des hubs avec `rrc_enabled=True` ou le modèle `rrc`
- Utilisez la même configuration Reticulum que MeshChatX ou votre hub
  (`reticulum_config_dir` ou `LXMFY_RETICULUM_CONFIG_DIR`, typiquement
  `~/.reticulum`)
- Voir [Création de bots](creating-bots.md#reticulum-relay-chat-rrc)
  pour les bots de salon et la découverte de hubs

**Sécurité**

- `signature_verification_enabled=True` vérifie les résultats de
  validation des signatures LXMF
- `require_message_signatures=True` rejette les messages non signés ou
  invalides
- Sous Linux, `landlock_enabled=True` (par défaut) applique une sandbox
  de système de fichiers Landlock LSM. Surchargez avec
  `LXMFY_LANDLOCK=0` ou `LXMFY_LANDLOCK=1`
- Les cogs en scripts externes peuvent utiliser Landlock, bubblewrap ou
  firejail via `external_cogs_sandbox_type`
- LXMF signe les messages sortants. LXMFy applique la politique de
  vérification et la sandbox optionnelle

**Développement**

- `make typecheck` exécute `pyright lxmfy`
- `make ci` exécute le lint, la vérification de types, la vérification
  de sécurité, les tests et le build

Voir [Création de bots](creating-bots.md) et la [Référence
API](api-reference.md) pour l'enregistrement des commandes, les cogs et
les détails de l'API.
