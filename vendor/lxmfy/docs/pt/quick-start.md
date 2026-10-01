# Início rápido

## Pré-requisitos

- Python 3.11+
- Reticulum Network Stack (`pip install rns`, versão 1.5.4+)
- LXMF (`pip install lxmf`, versão 1.1.1+; instalado automaticamente com
  o LXMFy)
- CBOR (`cborx`, instalado automaticamente, necessário para RRC)

=== "PyPI"

    ``` bash
    pip install lxmfy
    ```

=== "Código-fonte"

    ``` bash
    git clone https://github.com/Quad4-Software/LXMFy
    cd LXMFy
    poetry install
    ```

## Criar o primeiro bot (usando a CLI)

Use a CLI do LXMFy para gerar a estrutura de um projeto. Duas
formas:

- `lxmfy init` faz algumas perguntas (nome, template, armazenamento,
  prefixo, admins) e escreve um diretório de projeto pronto a correr.
- `lxmfy create` escreve um único ficheiro de bot com defaults, sem
  perguntas.

Este guia usa `lxmfy create`.

1.  **Abra o terminal** no diretório onde quer criar o projeto do bot.

2.  **Execute o comando de criação:**

    ``` bash
    lxmfy create my_first_bot
    ```

    Este comando gera os seguintes ficheiros:

    - `my_first_bot.py`: o ficheiro principal do bot, configurado com
      predefinições sensatas.
    - `cogs/`: um diretório para extensões do bot (cogs).
    - `cogs/__init__.py`: torna o diretório `cogs` um pacote Python.
    - `cogs/basic.py`: um cog de exemplo com comandos simples "hello" e
      "about".
    - `data/`: um diretório onde o bot guarda os seus dados (JSON por
      predefinição).
    - `config/`: um diretório onde o bot guarda a sua identidade e o
      estado dos anúncios.

3.  **Reveja o ficheiro `my_first_bot.py`:**

    ``` python
    from lxmfy import LXMFBot

    bot = LXMFBot(
        name="my_first_bot",  # Nome do bot usado em anúncios/identidade
        announce=600,         # Intervalo de anúncio em segundos (10 minutos)
        announce_immediately=True, # Anunciar na primeira execução?
        admins=set(),         # Conjunto de hashes de endereços LXMF de administradores
        hot_reloading=False,  # Ativar/desativar o hot reloading de cogs
        rate_limit=5,         # Máx. de mensagens por minuto por utilizador
        cooldown=60,          # Período de cooldown em segundos para o rate limit
        max_warnings=3,       # Avisos antes de banimento por spam
        warning_timeout=300,  # Tempo (segundos) até os avisos serem repostos
        command_prefix="/",   # Prefixo dos comandos (ex.: /hello)
        cogs_dir="cogs",      # Diretório de onde carregar os cogs
        cogs_enabled=True,    # Ativar/desativar o carregamento de cogs
        permissions_enabled=False, # Ativar/desativar o sistema de permissões por papéis
        storage_type="json",  # Backend de armazenamento ("json", "sqlite", "msgpack" ou "memory")
        storage_path="data",  # Caminho para os ficheiros/base de dados de armazenamento
        first_message_enabled=True, # Ativar tratamento especial das primeiras mensagens
        event_logging_enabled=True, # Registar eventos no armazenamento?
        max_logged_events=1000,   # Máx. de eventos a manter no registo
        event_middleware_enabled=True, # Ativar o middleware de eventos?
        announce_enabled=True,   # Ativar/desativar anúncios na rede
        signature_verification_enabled=False, # Ativar/desativar a verificação criptográfica de assinaturas
        require_message_signatures=False     # Exigir que todas as mensagens sejam assinadas
    )

    # Para adicionar um administrador, encontre o hash do seu endereço LXMF e adicione-o aqui:
    # bot.config.admins.add("o_seu_hash_lxmf_aqui")
    # bot.admins = bot.config.admins # Garante que a instância em execução fica a par

    # Exemplo de preparação de um campo de ícone LXMF (opcional)
    # from lxmfy import IconAppearance, pack_icon_appearance_field
    # try:
    #     icon_data = IconAppearance(icon_name="emoji_objects", fg_color=b'\xFF\xA5\x00', bg_color=b'\x8B\x45\x13') # Laranja sobre castanho
    #     bot.icon_field = pack_icon_appearance_field(icon_data) # Guardar para usar em send/reply
    # except Exception as e:
    #     print(f"Não foi possível preparar o campo de ícone: {e}")
    #     bot.icon_field = None

    if __name__ == "__main__":
        print(f"A iniciar o bot: {bot.config.name}")
        print(f"Endereço LXMF do bot: {bot.local.hash}") # Imprime o endereço do bot
        bot.run()
    ```

4.  **(Opcional) Adicione o seu hash de administrador:**

    - Encontre o hash do seu endereço LXMF (por exemplo, no seu cliente
      Reticulum, como o Sideband ou o NomadNet).
    - Descomente e edite a linha `bot.config.admins.add(...)` em
      `my_first_bot.py`, substituindo `"o_seu_hash_lxmf_aqui"` pelo seu
      hash real.

5.  **Execute o bot:**

    ``` bash
    python my_first_bot.py
    ```

    O bot arranca, imprime o seu endereço LXMF, pode enviar um anúncio
    para a rede Reticulum e começa a escutar mensagens.

## Interagir com o bot

1.  **Envie uma mensagem** para o endereço LXMF do bot a partir do seu
    cliente.
2.  **Experimente o comando de exemplo:** envie `/hello` ao bot. Deve
    responder com "Hello `<o_seu_hash>`!". Se descomentou o exemplo do
    ícone acima, esta resposta também pode trazer um ícone.
3.  **Experimente o comando de ajuda:** envie `/help`.

Se nada chegar, execute `lxmfy debug` a partir do diretório do
projeto. Ele verifica a configuração do Reticulum, as interfaces, a
identidade e a pipeline de envio, e guarda um relatório redigido que
pode partilhar ao pedir ajuda.

## O que configurar a seguir

**Manipuladores de mensagens**

- `@bot.on_first_message()` para a primeira mensagem de cada remetente
- `@bot.on_message()` para todas as mensagens antes do processamento de
  comandos

**Entrega**

- `direct_delivery_retries` em `LXMFBot(...)` repete a entrega direta
  antes de recorrer à propagação
- `propagation_node` (ou `bot.set_propagation_node(...)`) seleciona um
  nó de propagação LXMF específico
- A persistência da fila de saída está ativa por predefinição
  (`message_persistence_enabled=True`) com uma fila limitada
  (`message_queue_size`)

**Reticulum Relay Chat (RRC)**

- Ligue-se a hubs com `rrc_enabled=True` ou o template `rrc`
- Use a mesma configuração Reticulum do MeshChatX ou do seu hub
  (`reticulum_config_dir` ou `LXMFY_RETICULUM_CONFIG_DIR`, tipicamente
  `~/.reticulum`)
- Consulte [Criar bots](creating-bots.md#reticulum-relay-chat-rrc) para
  bots de sala e descoberta de hubs

**Segurança**

- `signature_verification_enabled=True` verifica os resultados da
  validação de assinaturas LXMF
- `require_message_signatures=True` rejeita mensagens não assinadas ou
  inválidas
- No Linux, `landlock_enabled=True` (predefinição) aplica uma sandbox
  Landlock LSM ao sistema de ficheiros. Pode ser sobreposto com
  `LXMFY_LANDLOCK=0` ou `LXMFY_LANDLOCK=1`
- Cogs de scripts externos podem usar Landlock, bubblewrap ou firejail
  através de `external_cogs_sandbox_type`
- O LXMF assina as mensagens enviadas. O LXMFy aplica a política de
  verificação e o sandboxing opcional

**Desenvolvimento**

- `make typecheck` executa `pyright lxmfy`
- `make ci` executa lint, typecheck, verificação de segurança, testes e
  build

Consulte [Criar bots](creating-bots.md) e a [Referência da
API](api-reference.md) para registo de comandos, cogs e detalhes da API.
