# Criar bots

## Estrutura básica

Um bot LXMFy mínimo envolve:

1.  Importar `LXMFBot`.
2.  Instanciar `LXMFBot` com a configuração pretendida.
3.  Definir comandos ou manipuladores de eventos.
4.  Executar o bot com `bot.run()`.

``` python
from lxmfy import LXMFBot

# 1. Instanciar o bot
bot = LXMFBot(
    name="SimpleBot",
    command_prefix="!",
    storage_path="simple_data"
)

# 2. Definir comandos
@bot.command(name="ping", description="Responds with pong")
def ping_command(ctx):
    # ctx é um objeto de contexto com informação da mensagem
    # ctx.sender: hash LXMF do remetente
    # ctx.content: conteúdo completo da mensagem
    # ctx.args: lista de argumentos após o comando
    # ctx.reply(message): função para enviar uma resposta
    #   (também aceita argumentos nomeados como title="My Title", lxmf_fields=some_fields)
    ctx.reply("Pong!")

# Para tarefas de longa duração, pode usar comandos em thread:
# import time
# @bot.command(name="long_op", description="Performs a long operation in a separate thread", threaded=True)
# def long_op_command(ctx):
#     ctx.reply("Starting long operation...")
#     time.sleep(10) # Simula uma operação demorada
#     ctx.reply("Long operation complete!")
# Importante: comandos em thread não devem interagir diretamente com o RNS ou o lxmfy.transport.py.

@bot.command(name="greet", description="Greets the user")
def greet_command(ctx):
    if ctx.args:
        name = " ".join(ctx.args)
        ctx.reply(f"Hello, {name}!")
    else:
        ctx.reply("Hello there! Tell me your name: !greet <your_name>")

# 3. Executar o bot
if __name__ == "__main__":
    print(f"Starting bot: {bot.config.name}")
    print(f"Bot LXMF Address: {bot.local.hash}")
    bot.run()
```

## Utilizar templates

O LXMFy fornece vários templates para tipos de bot comuns. Pode usar a
CLI para gerar um ficheiro de bot a partir de um template.

Para um diretório de projeto completo em vez de um único
ficheiro, `lxmfy init` gera `bot.py`, um pacote `cogs`, um README e um
`.gitignore`, perguntando pelo caminho por template, backend de
armazenamento, prefixo de comandos e hashes de admin.

``` bash
# Criar um bot de eco
lxmfy create --template echo my_echo_bot

# Criar um bot de lembretes (usa armazenamento SQLite)
lxmfy create --template reminder my_reminder_bot

# Criar um bot de notas (usa armazenamento JSON)
lxmfy create --template note my_note_bot

# Criar um bot de teste de cogs (testa funcionalidades de carregamento de cogs)
lxmfy create --template cogtest my_cog_test_bot

# Criar um bot de sala RRC (entra em hubs e responde a @menções)
lxmfy create --template rrc my_rrc_bot

# Ou executar o template diretamente
lxmfy run rrc
```

Estes comandos criam um ficheiro Python (ex.: `my_echo_bot.py`) que
importa e executa o template escolhido. Pode depois modificar o ficheiro
gerado ou o próprio código do template (`lxmfy/templates/...`).

**Exemplo de ficheiro gerado (`my_cog_test_bot.py`):**

``` python
from lxmfy.templates import CogTestBot

if __name__ == "__main__":
    bot = CogTestBot() # Cria uma instância do template CogTestBot
    # Pode, opcionalmente, alterar o nome predefinido:
    # bot.bot.name = "My Cog Test Bot"
    bot.run()
```

## Configuração do bot

Ao criar uma instância de `LXMFBot`, pode passar vários argumentos
nomeados para configurar o seu comportamento. Consulte a secção
`BotConfig` na [Referência da API](api-reference.md) ou o [Guia de
início rápido](quick-start.md) para uma lista de opções comuns.

``` python
from lxmfy import LXMFBot

bot = LXMFBot(
    name="ConfiguredBot",
    announce=3600, # Anunciar a cada hora
    admins={"your_admin_hash_here"}, # Definir utilizador(es) administrador(es)
    command_prefix="$", # Usar '$' como prefixo
    storage_type="sqlite", # Usar base de dados SQLite
    storage_path="data/my_bot_data.db", # Especificar o caminho do ficheiro da BD
    rate_limit=10, # Permitir 10 mensagens / minuto
    cooldown=30, # Cooldown de 30 segundos
    permissions_enabled=True # Ativar permissões por papéis
)

if __name__ == "__main__":
    # Também pode modificar a configuração após a instanciação
    # Nota: algumas opções devem ser definidas durante a inicialização
    bot.config.max_warnings = 5
    bot.spam_protection.config.max_warnings = 5 # Atualizar também o protetor de spam

    bot.run()
```

### Definir um ícone para o bot (campo LXMF)

Pode dar ao bot um ícone personalizado que aparece em clientes LXMF
compatíveis. Usa o `LXMF.FIELD_ICON_APPEARANCE` e pode ser definido ao
enviar mensagens.

Primeiro, garanta que tem os imports necessários:

``` python
from lxmfy import IconAppearance, pack_icon_appearance_field
```

Depois, pode definir e usar o ícone:

``` python
# Na classe do bot ou na configuração
icon_data = IconAppearance(
    icon_name="robot_2",  # Escolha entre os Material Symbols
    fg_color=b'\x00\xFF\x00',  # Verde
    bg_color=b'\x33\x33\x33'   # Cinzento escuro
)
self.bot_icon_field = pack_icon_appearance_field(icon_data)

# Ao enviar uma mensagem ou responder:
ctx.reply("Message from your bot!", lxmf_fields=self.bot_icon_field)
# ou
# bot.send(destination, "Another message", lxmf_fields=self.bot_icon_field)
```

Este `self.bot_icon_field` pode ser pré-calculado e reutilizado em todas
as mensagens enviadas pelo bot.

## Comandos estruturados via campos LXMF

Além de comandos de texto, o LXMFy suporta comandos enviados em campos
de mensagem LXMF usando `FIELD_COMMANDS` (`0x09`). É útil para fluxos
estruturados de pedido/resposta entre clientes LXMF e bots.

Quando uma mensagem contém `FIELD_COMMANDS`, o bot extrai o nome do
comando e os argumentos, encaminha-os pelo mesmo registo de comandos dos
comandos de texto e inclui automaticamente `FIELD_RESULTS` (`0x0A`) na
resposta.

**Receção de comandos estruturados**

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

O objeto `ctx` nos callbacks de comandos por campos inclui:

- `ctx.fields`: o dicionário de campos LXMF em bruto da mensagem
  recebida
- `ctx.request_id`: o `request_id` do `FIELD_COMMANDS` recebido (se
  existir)

**Envio de um comando estruturado a partir de um cliente LXMF**

``` python
import LXMF
from lxmfy import FIELD_COMMANDS

lxm = LXMF.LXMessage(
    destination,
    source,
    b"",  # o conteúdo pode ser vazio em comandos apenas por campos
    desired_method=LXMF.LXMessage.DIRECT,
)
lxm.fields[FIELD_COMMANDS] = {
    "command": "add",
    "args": ["3", "5"],
    "request_id": "req-42",  # opcional, para correlação
}
router.handle_outbound(lxm)
```

**Desativar comandos por campos**

Se quiser que o bot ignore `FIELD_COMMANDS` e processe apenas comandos
de texto, defina:

``` python
bot = LXMFBot(
    name="TextOnlyBot",
    lxmf_commands_enabled=False,
)
```

## Utilizar cogs (extensões)

Os cogs permitem organizar comandos e listeners de eventos em ficheiros
separados (módulos), mantendo o ficheiro principal do bot mais limpo.

1.  **Crie um diretório `cogs`** (ou o que definiu em `cogs_dir` no
    `BotConfig`).
2.  **Crie ficheiros Python** dentro do diretório `cogs` (ex.:
    `utility.py`).
3.  **Defina uma classe** que herda de `lxmfy.Cog` (opcional, mas boa
    prática) ou que é apenas uma classe normal.
4.  **Defina comandos** como métodos da classe usando o decorador
    `@Command`.
5.  **Crie uma função `setup(bot)`** no ficheiro do cog, que o LXMFy
    chama para registar o cog.

**Exemplo (`cogs/utility.py`):**

``` python
from lxmfy import Command
from lxmfy.commands import Cog  # Importar Cog se herdar
import time

class UtilityCog: # Ou class UtilityCog(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = time.time()

    @Command(name="uptime", description="Shows bot uptime")
    # Nota: métodos em cogs recebem frequentemente 'self' e 'ctx'
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
        time.sleep(7) # Simula uma operação demorada
        ctx.reply("Long cog task completed!")

# Esta função é necessária para o cog ser carregado
def setup(bot):
    cog_instance = UtilityCog(bot)
    bot.add_cog(cog_instance) # Regista a instância do cog no bot
```

**Ficheiro principal do bot (`my_bot.py`):**

``` python
from lxmfy import LXMFBot

bot = LXMFBot(
    name="CogBot",
    cogs_enabled=True, # Garanta que os cogs estão ativos (predefinição)
    cogs_dir="cogs" # Apontar para o diretório
)

if __name__ == "__main__":
    # Os cogs são carregados automaticamente durante a inicialização do LXMFBot
    # se cogs_enabled for True.
    bot.run()
```

Quando o bot arranca, encontra automaticamente o `utility.py`, chama a
sua função `setup`, que cria uma instância de `UtilityCog` e a regista
com `bot.add_cog()`. Os comandos definidos no cog (`uptime`, `info`)
ficam então disponíveis.

## Cogs de scripts externos (suporte multilinguagem)

Também pode escrever extensões do bot noutras linguagens (ex.: Bash,
Ruby, Perl, Go, C) usando cogs de scripts externos.

1.  **Crie um script executável** no diretório `cogs`.
2.  **Adicione um shebang** no topo do script (ex.: `#!/bin/bash`).
3.  **Garanta que o script é executável** (`chmod +x your_script`).

Quando o bot arranca, regista automaticamente qualquer ficheiro
executável no diretório `cogs` (que não termine em `.py`) como comando
do bot.

**Protocolo de argumentos:**

- `$1`: hash LXMF do remetente.
- `$2`: conteúdo completo da mensagem.
- `$3`, `$4`, ...: argumentos individuais do comando.

**Variáveis de ambiente:**

- `LXMFY_SENDER`: o hash de identidade do remetente.
- `LXMFY_CONTENT`: o conteúdo completo da mensagem.
- `LXMFY_HAS_ADMIN`: `true` ou `false` conforme o estatuto de
  administrador do remetente.

**Exemplo de cog em Bash (`cogs/greet.sh`):**

``` bash
#!/bin/bash
echo "Hello from Bash! You sent: $2"
```

Quando um utilizador envia `/greet hello`, o bot executa este script e
responde com o seu stdout: `Hello from Bash! You sent: /greet hello`.

## Classificação local de intents NLP

O LXMFy inclui um classificador local de intents. Faz corresponder o
texto da mensagem a frases de exemplo etiquetadas quando o texto não
corresponde exatamente a um prefixo de comando.

1.  **Ative o NLP** na configuração do bot: `nlp_enabled=True`.
2.  **Defina intents** com o decorador `@bot.intent`.

``` python
@bot.intent("help", examples=["how do I use this?", "show me commands", "help me please"])
def help_intent(msg):
    msg.reply("I can help! Try typing /help to see a list of commands.")
```

A correspondência usa vetores TF-IDF e semelhança por cosseno. Todo o
cálculo corre no anfitrião do bot. Nenhum texto é enviado para uma API
externa.

**Exportação e importação do modelo**

Exporte e importe um modelo treinado para que bots maiores evitem o
retreino a cada arranque:

``` python
# Exportar o modelo
model_data = bot.nlp.export_model()
# Guardar model_data num ficheiro ou base de dados

# Mais tarde, importar de volta
bot.nlp.import_model(model_data)
```

## Suporte de RNS Links

Os bots podem estabelecer e responder a RNS Links diretos para tráfego
com estado, streaming ou de maior largura de banda do que pacotes LXMF
individuais.

1.  **Ative o suporte de links** na configuração:
    `link_support_enabled=True`.
2.  **Peça um link**: `bot.request_link(destination_hash)`. Também pode
    especificar um nome de aplicação e aspects personalizados:
    `bot.request_link(dest, callback, "my_app", "aspect1")`.
3.  **Trate links recebidos**: registe um callback com
    `bot.on_link(handler)`.

``` python
def handle_link(link):
    print(f"Link established with {RNS.hexrep(link.destination.hash)}")
    # Pode agora usar o link para comunicação RNS direta

bot.on_link(handle_link)
```

**Segurança e sandboxing:**

- **Timeouts:** os cogs externos têm um timeout predefinido (30s) para
  evitar bloqueios. Configurável via `external_cogs_timeout`.
- **Threads:** todos os cogs externos correm em threads separadas e não
  bloqueiam o bot.
- **Sandbox do processo do bot (apenas Linux):** quando
  `landlock_enabled=True` (predefinição) e o kernel suporta Landlock LSM
  (5.13+), o bot aplica uma sandbox de sistema de ficheiros ao próprio
  processo após o arranque. Os caminhos com escrita limitam-se ao
  armazenamento, configuração, cogs, configuração Reticulum e diretórios
  temporários. Use a variável de ambiente `LXMFY_LANDLOCK=0` para
  desativar ou `LXMFY_LANDLOCK=1` para forçar a tentativa.
- **Sandbox dos cogs externos (apenas Linux):** quando
  `external_cogs_sandbox_enabled=True` (predefinição), os cogs de script
  executáveis correm num ambiente restrito. Defina
  `external_cogs_sandbox_type` para um de:
  - `auto` (predefinição): prefere Landlock quando suportado, senão
    `bubblewrap` (`bwrap`), senão `firejail`
  - `landlock`: sandbox só com Landlock via `preexec_fn` (regras mais
    restritas que a sandbox do processo do bot)
  - `bwrap`: sandbox bubblewrap com bind só de leitura
  - `firejail`: perfil privado firejail sem rede
  - `none`: sem sandbox de subprocesso
- **Estado:** chame `bot.get_landlock_status()` para inspecionar o
  suporte do kernel, se o Landlock foi pedido e se a sandbox do processo
  do bot está ativa.

## Tratar mensagens

O LXMFy oferece várias formas de tratar mensagens recebidas em
diferentes fases do processamento.

### Manipulador da primeira mensagem

Trate a primeira mensagem de cada novo utilizador (útil para mensagens
de boas-vindas):

``` python
from lxmfy import LXMFBot

bot = LXMFBot(
    name="WelcomeBot",
    first_message_enabled=True  # Tem de ser True (predefinição)
)

@bot.on_first_message()
def welcome_new_user(sender, message):
    content = message.content.decode("utf-8")
    bot.send(
        sender,
        f"Welcome to the bot! You said: {content}\n\n"
        "Type /help to see available commands."
    )
    return True  # Devolva True para parar o processamento desta mensagem

if __name__ == "__main__":
    bot.run()
```

### Manipulador geral de mensagens

Trate todas as mensagens recebidas antes do processamento de comandos:

``` python
from lxmfy import LXMFBot

bot = LXMFBot(name="EchoBot")

@bot.on_message()
def echo_non_commands(sender, message):
    content = message.content.decode("utf-8").strip()

    # Verificar se é um comando - se for, deixar o manipulador de comandos tratar
    if content.startswith(bot.config.command_prefix):
        command_name = content.split()[0][len(bot.config.command_prefix):]
        if command_name in bot.commands:
            return False  # Deixar o manipulador de comandos processar

    # Não é um comando, fazer eco de volta
    bot.send(sender, f"You said: {content}")
    return False  # Devolver False para continuar o processamento (embora nenhum comando corresponda)

@bot.command(name="hello", description="Say hello")
def hello_command(ctx):
    ctx.reply("Hello! This is a command response.")

if __name__ == "__main__":
    bot.run()
```

Ordem de processamento dos manipuladores de mensagens:

1.  **Manipulador da primeira mensagem** (se `first_message_enabled=True`
    e for a primeira mensagem deste remetente)
2.  **Manipuladores gerais de mensagens** (registados com
    `@bot.on_message()`)
3.  **Processamento de comandos** (se a mensagem corresponder a um
    comando registado)

Os manipuladores podem devolver `True` para parar o processamento ou
`False` para continuar para a fase seguinte.

## Tratar eventos

Pode registar manipuladores para vários eventos do bot usando o
decorador `@bot.events.on()`.

``` python
from lxmfy import LXMFBot
from lxmfy.events import EventPriority # Opcional para prioridade

bot = LXMFBot(name="EventBot")

@bot.events.on("message_received")
def log_message(event):
    # O objeto de evento contém detalhes
    sender = event.data.get("sender")
    message_content = event.data.get("message").content.decode('utf-8', errors='ignore')
    print(f"Received message from {sender}: {message_content}")

    # Pode cancelar o processamento do evento (ex.: parar o tratamento da mensagem)
    # if sender == "some_blocked_hash":
    #    event.cancel()

@bot.events.on("command_executed", priority=EventPriority.LOW)
def log_command(event):
    # Exemplo: event.data pode conter {'command_name': 'ping', 'sender': '...', ...}
    command_name = event.data.get('command_name', 'unknown')
    sender = event.data.get('sender', 'unknown')
    print(f"Command '{command_name}' executed by {sender}")

# Também pode definir eventos personalizados
@bot.command(name="special")
def special_command(ctx):
    ctx.reply("Doing something special!")
    # Emitir um evento personalizado
    bot.events.dispatch(Event("special_action_taken", data={"user": ctx.sender}))

@bot.events.on("special_action_taken")
def handle_special(event):
    user = event.data.get("user")
    print(f"Special action was taken by user: {user}")


if __name__ == "__main__":
    bot.run()
```

Consulte `lxmfy/events.py` para mais detalhes sobre a estrutura `Event`
e as prioridades.

## Armazenamento

O LXMFy fornece backends de armazenamento JSON, SQLite, MsgPack e em memória.

- **JSON:** simples, legível por humanos. Bom para conjuntos de dados
  pequenos. Configure com `storage_type="json"` e
  `storage_path="your_data_dir"`.
- **SQLite:** mais eficiente para conjuntos de dados maiores ou escritas
  frequentes. Configure com `storage_type="sqlite"` e
  `storage_path="your_db_file.db"`.
- **MsgPack:** formato binário compacto com o mesmo layout de um
  ficheiro por chave do JSON. Configure com `storage_type="msgpack"` e
  `storage_path="your_data_dir"`.
- **Memory:** armazenamento inteiramente em RAM. O estado perde-se no
  encerramento. Configure com `storage_type="memory"`.

Pode aceder à interface de armazenamento via `bot.storage`:

``` python
# Guardar dados
bot.storage.set("user_prefs:" + ctx.sender, {"theme": "dark"})

# Obter dados (com valor predefinido)
prefs = bot.storage.get("user_prefs:" + ctx.sender, {})
theme = prefs.get("theme", "light")

# Verificar se os dados existem
if bot.storage.exists("some_key"):
    print("Key exists!")

# Apagar dados
bot.storage.delete("old_data_key")

# Procurar chaves com um prefixo (útil para listar dados de utilizadores)
user_keys = bot.storage.scan("user_prefs:")
for key in user_keys:
    user_data = bot.storage.get(key)
    print(f"Data for {key}: {user_data}")
```

Consulte `lxmfy/storage.py` e a referência da API para mais detalhes.

## Permissões

O LXMFy inclui um sistema opcional de permissões por papéis. Ative-o com
`permissions_enabled=True` durante a inicialização do `LXMFBot`.

- **Papéis:** defina papéis com permissões específicas (ex.:
  `DefaultPerms.MANAGE_USERS`).
- **Permissões:** flags granulares definidas em `DefaultPerms` (ex.:
  `USE_COMMANDS`, `BYPASS_SPAM`).
- **Atribuição:** atribua papéis a hashes de utilizadores.

Consulte `lxmfy/permissions.py`, a referência da API e eventuais cogs de
exemplo (se existirem) para detalhes de utilização.

## Verificação de assinaturas

O LXMFy fornece configuração para a assinatura e verificação
criptográfica de mensagens integrada no LXMF. Todas as mensagens LXMF
são automaticamente assinadas pela stack LXMF/RNS - o LXMFy apenas
permite aplicar políticas de verificação de assinaturas.

**Configuração:**

Ative a verificação de assinaturas na configuração do bot:

``` python
bot = LXMFBot(
    name="SecureBot",
    signature_verification_enabled=True,  # Ativar a verificação de assinaturas
    require_message_signatures=False      # Definir como True para rejeitar mensagens não assinadas
)
```

**Como funciona:**

O LXMF trata automaticamente de todas as operações criptográficas:

1.  **Mensagens enviadas:** o LXMF assina automaticamente todas as
    mensagens usando a identidade RNS do remetente durante o
    empacotamento da mensagem.
2.  **Mensagens recebidas:** o LXMF valida automaticamente as assinaturas
    usando a identidade RNS do remetente e fornece os resultados da
    validação.
3.  **Papel do LXMFy:** o LXMFy verifica os resultados da validação do
    LXMF e aplica a sua política:
    - Se `signature_verification_enabled=False`: todas as mensagens são
      aceites (predefinição)
    - Se `signature_verification_enabled=True` e
      `require_message_signatures=False`: as mensagens são aceites, mas
      assinaturas ausentes/inválidas são registadas
    - Se `signature_verification_enabled=True` e
      `require_message_signatures=True`: mensagens não assinadas ou
      inválidas são rejeitadas
4.  **Integração com permissões:** utilizadores com a permissão
    `BYPASS_SPAM` podem ignorar os requisitos de verificação de
    assinaturas.

**Gestão via CLI:**

Pode gerir as definições de verificação de assinaturas usando a CLI:

``` bash
# Testar a verificação de assinaturas
lxmfy signatures test

# Ativar a verificação de assinaturas
lxmfy signatures enable

# Desativar a verificação de assinaturas
lxmfy signatures disable
```

**Detalhes técnicos:**

O LXMF usa assinaturas Ed25519 fornecidas pelo sistema criptográfico
RNS. Cada mensagem LXMF inclui a assinatura do remetente, validada
contra a sua identidade RNS conhecida. O LXMFy apenas lê as propriedades
`message.signature_validated` e `message.unverified_reason` do LXMF para
aplicar a política de segurança do bot.

## Entrega de mensagens

### Utilizar nós de propagação

Envie mensagens através de nós de propagação LXMF específicos:

``` python
from lxmfy import LXMFBot

bot = LXMFBot(name="PropagationBot")

@bot.command(name="send", description="Send via propagation node")
def send_command(ctx):
    # Definir um nó de propagação específico uma vez (nível de configuração)
    bot.set_propagation_node("<propagation_node_hash_here>")

    # Enviar usando a estratégia de entrega configurada
    bot.send(
        ctx.sender,
        "This message will use direct delivery with propagation fallback as configured"
    )
```

Use um nó de propagação quando o destino está offline ou a entrega
direta continua a falhar no caminho atual.

### Configurar repetições

Configure tentativas automáticas de repetição para entregas falhadas via
configuração do bot:

``` python
from lxmfy import LXMFBot

bot = LXMFBot(name="ReliableBot")

bot = LXMFBot(
    name="ReliableBot",
    direct_delivery_retries=5,  # Repetir a entrega direta até 5 vezes
    propagation_fallback_enabled=True
)

@bot.command(name="important", description="Send important message with retries")
def important_command(ctx):
    bot.send(ctx.sender, "This is an important message")

@bot.command(name="normal", description="Send with default retries")
def normal_command(ctx):
    # O direct_delivery_retries predefinido é 3
    bot.send(ctx.sender, "This message uses default retry settings")
```

O sistema de repetição:

- Regista automaticamente as tentativas de entrega por destino
- Repete entregas diretas falhadas até `direct_delivery_retries`
- Repõe o contador de repetições numa entrega bem-sucedida
- Regista tentativas e falhas de repetição para depuração

### Envios diferidos e stamps

Dois detalhes de entrega que vale a pena conhecer cedo:

- **Envios diferidos**: quando a identidade do destino ainda não é
  conhecida, `send()` retém a mensagem em armazenamento (as chaves de
  configuração `pending_sends_*` controlam o backlog) e despeja-a
  quando o peer anuncia. Passa `defer=False` a um envio para descartar
  em vez de reter.
- **Stamps**: `stamp_cost` define um requisito de proof-of-work de
  entrada, `require_stamps` rejeita mensagens que o falham, e
  `include_tickets` (padrão) anexa tickets de resposta para que os
  peers possam responder ao teu bot sem pagar o seu próprio custo de
  stamp.

Quando a entrega falha, `lxmfy debug` percorre todo o caminho
(configuração, instância, interfaces, identidade, pipeline de envio) e
escreve um relatório redigido que podes partilhar. As mesmas
verificações são chamáveis como `bot.diagnose_connectivity()` e
`bot.diagnose_destination(hash)`.

Vê a [Referência de API](api-reference.md#entrega-de-mensagens) para
toda a superfície de entrega: repetições, nós de propagação,
persistência de fila, o fluxo de eventos de entrega e os comandos de
administração `/queue`, `/cancel`, `/inbox`, `/delivery`.

## Reticulum Relay Chat (RRC)

Os bots LXMFy podem entrar em hubs [RRC](https://rrc.kc1awv.net/) como
clientes normais através de RNS Links usando envelopes CBOR. É
compatível com hubs estilo NomadNet e rrcd (incluindo o MeshChatX quando
aloja ou entra no mesmo hub).

### A configuração Reticulum importa

O bot tem de usar a **mesma** rede Reticulum do hub. O MeshChatX usa
tipicamente `~/.reticulum` com interfaces backbone ou TCP. O diretório
`config/` local do projeto usa frequentemente um nome de instância
isolado e apenas AutoInterface, por isso os anúncios do hub nunca chegam
e aparece `Hub identity unknown`.

Prefira uma destas opções:

- Defina `reticulum_config_dir` para a configuração do seu utilizador
  (normalmente `~/.reticulum`)
- Ou exporte `LXMFY_RETICULUM_CONFIG_DIR=~/.reticulum`
- Mantenha o MeshChatX ou o `rnsd` em execução para a instância
  partilhada estar ativa antes do bot arrancar

O template `rrc` usa `~/.reticulum` por predefinição quando esse
diretório existe.

### Início rápido com o template

``` bash
lxmfy run rrc
```

Predefinições:

- Hub: `664fc0e8d2e448658e37bb3f34e6c88f`
- Sala: `#general`
- Configuração Reticulum: `~/.reticulum` (ou
  `LXMFY_RETICULUM_CONFIG_DIR`)

Deve ver registos de ligação ao hub, welcome, auto-join e `RRC joined
#general`.

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

Ou ligue em tempo de execução:

``` python
bot.connect_rrc("hub_destination_hash", rooms=["general"])
bot.rrc.send_message("general", "hello room")
bot.rrc.send_action("general", "waves")
bot.disconnect_rrc()
```

### Comportamento da sessão

- HELLO / WELCOME, JOIN / PART, MSG / NOTICE / ACTION, PING / PONG,
  ERROR, RESOURCE_ENVELOPE
- Reconexão automática com reentrada nas salas após WELCOME
- Limite de hubs e aplicação de rate limit no lado do cliente
- Persistência de sessão entre reinícios (`rrc_persist_sessions`, ativa
  por predefinição)
- A persistência da fila LXMF de saída é separada
  (`message_persistence_enabled`)
