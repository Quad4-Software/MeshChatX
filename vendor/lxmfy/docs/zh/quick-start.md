# 快速上手

## 前置要求

- Python 3.11+
- Reticulum Network Stack（`pip install rns`，版本 1.5.4+）
- LXMF（`pip install lxmf`，版本 1.1.1+；随 LXMFy 自动安装）
- CBOR（`cborx`，自动安装，RRC 需要）

=== "PyPI"

    ``` bash
    pip install lxmfy
    ```

=== "源码"

    ``` bash
    git clone https://github.com/Quad4-Software/LXMFy
    cd LXMFy
    poetry install
    ```

## 创建你的第一个机器人（使用 CLI）

使用 LXMFy CLI 生成项目骨架。两种方式:

- `lxmfy init` 会问几个问题 (名称, 模板, 存储, 前缀, admins),
  并写出一个可直接运行的项目目录。
- `lxmfy create` 用默认值写出单个 bot 文件, 不提问。

本指南使用 `lxmfy create`。

1.  **打开终端**，进入你想创建机器人项目的目录。

2.  **运行 create 命令：**

    ``` bash
    lxmfy create my_first_bot
    ```

    该命令会生成以下文件：

    - `my_first_bot.py`：机器人主文件，已配置合理的默认值。
    - `cogs/`：存放机器人扩展（Cog）的目录。
    - `cogs/__init__.py`：使 `cogs` 目录成为 Python 包。
    - `cogs/basic.py`：示例 Cog，包含简单的 "hello" 和 "about"
      命令。
    - `data/`：机器人存放数据的目录（默认使用 JSON）。
    - `config/`：机器人存放身份标识和 announce 状态的目录。

3.  **查看 `my_first_bot.py` 文件：**

    ``` python
    from lxmfy import LXMFBot

    bot = LXMFBot(
        name="my_first_bot",  # 机器人名称，用于 announce 和身份标识
        announce=600,         # announce 间隔（秒），即 10 分钟
        announce_immediately=True, # 首次运行时立即 announce？
        admins=set(),         # 管理员 LXMF 地址哈希集合
        hot_reloading=False,  # 启用/禁用 Cog 热重载
        rate_limit=5,         # 每用户每分钟最大消息数
        cooldown=60,          # 限流的冷却时间（秒）
        max_warnings=3,       # 因刷屏被封禁前的警告次数
        warning_timeout=300,  # 警告重置前的时长（秒）
        command_prefix="/",   # 命令前缀（例如 /hello）
        cogs_dir="cogs",      # 加载 Cog 的目录
        cogs_enabled=True,    # 启用/禁用加载 Cog
        permissions_enabled=False, # 启用/禁用基于角色的权限系统
        storage_type="json",  # 存储后端（"json"、"sqlite"、"msgpack" 或 "memory"）
        storage_path="data",  # 存储文件/数据库的路径
        first_message_enabled=True, # 启用对首条消息的特殊处理
        event_logging_enabled=True, # 将事件记录到存储？
        max_logged_events=1000,   # 日志中最多保留的事件数
        event_middleware_enabled=True, # 启用事件中间件？
        announce_enabled=True,   # 启用/禁用网络 announce
        signature_verification_enabled=False, # 启用/禁用加密签名校验
        require_message_signatures=False     # 要求所有消息都必须签名
    )

    # 要添加管理员，找到你的 LXMF 地址哈希并加到这里：
    # bot.config.admins.add("your_lxmf_hash_here")
    # bot.admins = bot.config.admins # 确保运行中的实例知晓

    # 准备 LXMF 图标字段的示例（可选）
    # from lxmfy import IconAppearance, pack_icon_appearance_field
    # try:
    #     icon_data = IconAppearance(icon_name="emoji_objects", fg_color=b'\xFF\xA5\x00', bg_color=b'\x8B\x45\x13') # 棕底橙色
    #     bot.icon_field = pack_icon_appearance_field(icon_data) # 保存供 send/reply 使用
    # except Exception as e:
    #     print(f"Could not prepare icon field: {e}")
    #     bot.icon_field = None

    if __name__ == "__main__":
        print(f"Starting bot: {bot.config.name}")
        print(f"Bot LXMF Address: {bot.local.hash}") # 打印机器人地址
        bot.run()
    ```

4.  **（可选）添加你的管理员哈希：**

    - 找到你的 LXMF 地址哈希（例如在 Sideband 或 NomadNet 等
      Reticulum 客户端中查看）。
    - 在 `my_first_bot.py` 中取消注释并编辑
      `bot.config.admins.add(...)` 一行，把 `"your_lxmf_hash_here"`
      替换为你的实际哈希。

5.  **运行机器人：**

    ``` bash
    python my_first_bot.py
    ```

    机器人会启动，打印其 LXMF 地址，可能在 Reticulum 网络上发送
    announce 消息，并开始监听消息。

## 与机器人交互

1.  **从你的客户端**向机器人的 LXMF 地址发送一条消息。
2.  **试试示例命令：** 向机器人发送 `/hello`。它应回复
    "Hello `<your_hash>`!"。如果你取消了上面图标示例的注释，
    该回复可能还会带上图标。
3.  **试试帮助命令：** 发送 `/help`。

如果没有任何消息到达, 在项目目录下运行 `lxmfy debug`。它会检
查 Reticulum 配置, 接口, 身份和发送流水线, 并保存一份脱敏报
告, 你可以在求助时分享。

## 接下来可以配置什么

**消息处理器**

- `@bot.on_first_message()` 处理每个发送者的首条消息
- `@bot.on_message()` 在命令处理之前处理所有消息

**投递**

- `LXMFBot(...)` 中的 `direct_delivery_retries` 会在回退到传播
  节点之前重试直接投递
- `propagation_node`（或 `bot.set_propagation_node(...)`）选择
  特定的 LXMF 传播节点
- 出站队列持久化默认开启（`message_persistence_enabled=True`），
  队列有上限（`message_queue_size`）

**Reticulum Relay Chat (RRC)**

- 使用 `rrc_enabled=True` 或 `rrc` 模板加入 hub
- 使用与 MeshChatX 或你的 hub 相同的 Reticulum 配置
  （`reticulum_config_dir` 或 `LXMFY_RETICULUM_CONFIG_DIR`，通常为
  `~/.reticulum`）
- 房间机器人和 hub 发现见[创建机器人](creating-bots.md#reticulum-relay-chat-rrc)

**安全**

- `signature_verification_enabled=True` 检查 LXMF 签名校验结果
- `require_message_signatures=True` 拒绝未签名或无效的消息
- 在 Linux 上，`landlock_enabled=True`（默认）应用 Landlock LSM
  文件系统沙箱。可用 `LXMFY_LANDLOCK=0` 或 `LXMFY_LANDLOCK=1`
  覆盖
- 外部脚本 Cog 可通过 `external_cogs_sandbox_type` 使用
  Landlock、bubblewrap 或 firejail
- LXMF 为出站消息签名。LXMFy 负责执行校验策略和可选的沙箱隔离

**开发**

- `make typecheck` 运行 `pyright lxmfy`
- `make ci` 运行 lint、类型检查、安全检查、测试和构建

命令注册、Cog 和 API 细节见[创建机器人](creating-bots.md)和
[API 参考](api-reference.md)。
