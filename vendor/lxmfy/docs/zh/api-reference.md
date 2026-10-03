# 核心组件

## LXMFBot

主机器人类，负责消息路由、命令处理和机器人生命周期管理。

``` python
from lxmfy import LXMFBot

bot = LXMFBot(
    name="MyBot",
    command_prefix="/",
    admins=set(),
    config_path=None,                 # 默认为工作目录下的 "config"
    reticulum_config_dir=None,        # 或 LXMFY_RETICULUM_CONFIG_DIR / "~/.reticulum"
    test_mode=False,                  # 跳过 RNS 启动，用于测试
    log_level="INFO",                 # lxmfy 日志级别，None 则不动日志配置
    loglevel=None,                    # RNS 日志级别 0-7，None 使用 reticulum 配置

    # Announce
    announce=600,
    announce_immediately=True,
    announce_enabled=True,
    announce_display_name_file=None,  # config_path 下覆盖 announced 显示名的文件
                                      # (默认文件: bot_display_name.txt)

    # 反垃圾保护
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

    # 存储, 事件, 权限
    storage_type="json",              # "json", "sqlite", "msgpack" 或 "memory"
    storage_path="data",
    permissions_enabled=False,
    first_message_enabled=True,
    event_logging_enabled=True,
    max_logged_events=1000,
    event_middleware_enabled=True,

    # 安全
    signature_verification_enabled=False,
    require_message_signatures=False,
    require_stamps=False,             # 拒绝 stamp 无效的消息
    request_unknown_identities=False, # 向网络请求发送者身份
    stamp_cost=None,                  # 入站 stamp 成本, None 表示关闭
    include_tickets=True,             # 为出站消息附带回复 ticket
    identity_pinning_enabled=False,
    landlock_enabled=True,

    # 可选功能
    nlp_enabled=False,
    nlp_threshold=0.5,
    link_support_enabled=False,
    lxmf_commands_enabled=True,

    # 投递
    message_persistence_enabled=True,
    message_queue_size=50,
    opportunistic_sending=True,
    direct_delivery_retries=3,
    propagation_fallback_enabled=True,
    propagation_node=None,            # 出站传播节点的 hash
    autopeer_propagation=False,       # 从 announce 中发现传播节点
    autopeer_maxdepth=4,              # 自动发现的最大 hop 深度, None = 不限
    enable_propagation_node=False,    # 将本 bot 作为传播节点运行
    message_storage_limit_mb=500,     # 节点存储上限, 仅节点模式

    # 延迟发送
    pending_sends_enabled=True,       # 为未知目的地保留发送
    pending_sends_max=200,
    pending_sends_ttl=604800,         # 7 天
    pending_sends_retry=300,          # 重试扫描间隔秒数

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

所有这些选项都是 `BotConfig` 的字段。`LXMFBot(**kwargs)` 会透传
每个关键字参数, 因此 `bot.config` 包含解析后的值。

### 主要方法

- `run(delay=10)`: 启动 bot 的主循环
- `cleanup()`: 持久化队列, 取消对话, 关闭调度器, 路由器和 RNS。
  退出 `run()` 时自动调用。
- `send(destination, message, title="Reply", lxmf_fields=None, stamp_cost=None, opportunistic=None, method=None, include_ticket=None, defer=None, reply_to=None, quote=None, thread=None)`:
  向目的地发送消息。`stamp_cost` 覆盖此消息的出站成本,
  `opportunistic` 覆盖 `opportunistic_sending`, `include_ticket`
  覆盖 `include_tickets`, `defer` 覆盖 `pending_sends_enabled`。
  `reply_to`, `quote` 和 `thread` 设置回复 threading 字段。
- `send_with_attachment(destination, message, attachment, title="Reply", stamp_cost=None, opportunistic=None)`:
  发送带附件的消息
- `command(name, description="No description provided", admin_only=False, permissions=None, usage=None, examples=None, category=None, aliases=None, threaded=False, rate_limit=None)`:
  注册命令的装饰器。`permissions` 覆盖 `DefaultPerms` 门槛
  (`admin_only` 时为 `ALL`, 否则为 `USE_COMMANDS`), `threaded`
  在工作线程中执行回调, `rate_limit` 限制每个发送者在 cooldown
  窗口内的调用次数, `usage`, `examples`, `category`, `aliases`
  提供给帮助系统。命令支持类型注解参数的自动转换。
- `intent(name, examples)`: 注册 NLP intent 处理器的装饰器。
- `nlp.export_model()`: 导出训练好的 NLP 模型数据。
- `nlp.import_model(model_data)`: 导入先前导出的 NLP 模型数据。
- `request_link(destination_hash, callback=None, app_name="lxmf", *aspects)`:
  向目的地请求 RNS link。允许自定义 `app_name` 和 `aspects`
  (默认为 "lxmf" 和 "delivery")。
- `on_link(callback)`: 注册入站 RNS link 的处理器。
- `load_extension(name)`: 按名称加载 cog 扩展模块
  (例如 "cogs.utility")。
- `reload_extension(name)`: 重新加载 cog 扩展模块。
- `add_cog(cog_instance)`: 向 bot 添加 cog 类实例。
- `remove_cog(cog_name)`: 按类名移除 cog。
- `on_first_message()`: 处理用户首条消息的装饰器
- `on_message()`: 处理所有消息的装饰器 (在命令处理之前调用)
- `received(function)`: 注册一个回调, 对每条走完流水线但未被
  命令或 intent 消费的入站消息, 以消息上下文调用
- `on_reaction()`: 处理入站回应的装饰器。处理器接收
  `(sender, reaction)`, 其中 reaction 带有 `reaction_to`,
  `reaction_emoji` 和 `reaction_sender` 键
- `react(destination, message_hash, reaction)`: 通过 LXMF 字段
  `FIELD_REACTION` 对消息发送回应
- `validate()`: 对 bot 配置执行校验检查
- `get_landlock_status()`: 返回 bot 进程 Landlock LSM 沙箱的
  可用性与启用状态
- `diagnose_destination(destination, request_path=False, wait=0.0)`:
  探测目标 hash 的身份与路径状态
- `diagnose_connectivity(destination=None, request_path=False, wait=0.0)`:
  执行完整 doctor 报告并以 dict 返回
- `get_debugger()`: 返回绑定到本 bot 的 `Debugger`
- `set_propagation_node(node_hash)`: 固定出站传播节点
- `get_propagation_node_status()`: 已配置, 已发现以及当前使用的
  出站传播节点状态
- `set_message_storage_limit(megabytes)`: 作为传播节点运行时的
  存储上限
- `get_propagation_storage_stats()`: 节点存储用量, 或解释不可用
  原因的 dict
- `connect_rrc(hub_hash, rooms=None, nick=None, dest_name=None, auto_reconnect=None)`:
  以客户端身份连接 RRC hub
- `disconnect_rrc(hub_hash=None)`: 断开一个或全部 RRC hub 会话
- `on_rrc(callback=None)`: RRC 事件的装饰器或处理器注册
  (`handler(event, client, payload)`)
- `on_delivery_event(callback=None)`: 订阅出站投递事件流, 可作
  装饰器或直接调用

### 属性

- `config`: 解析后的 `BotConfig`
- `commands`, `cogs`: 命令与 cog 注册表
- `storage`: 当前存储后端
- `scheduler`: 用于类 cron 任务的 `TaskScheduler`
- `events`: 事件处理器与 dispatch 的 `EventManager`
- `middleware`: 命令中间件的 `MiddlewareManager`
- `permissions`: 角色与标志位的 `PermissionManager`
- `spam_protection`: 速率限制, 警告和封禁的 `SpamProtection`
- `signature_manager`: 签名策略层
- `nlp`: intent 分类器 (仅在 `nlp_enabled` 时匹配)
- `delivery`: `DeliveryTracker`, 出站事件流
- `conversations`: `msg.ask` 问题的 `ConversationManager`
- `rrc`: 多 hub 会话的 `RRCManager`, 在启用 RRC 或运行
  `connect_rrc()` 之前为 `None`
- `local`: bot 的 `RNS.Destination` (其 LXMF 地址为
  `bot.local.hash`)

## Announce 显示名

对端看到的名字来自 `name`, 但 announce 存在两个覆盖途径。若设置
了 `announce_display_name_file` 且该文件存在于 `config_path` 下,
其内容优先。否则, 若存在 `config_path` 下的
`bot_display_name.txt` 则读取它。两种情况下, 赋值
`bot.name = "New Name"` 都会在运行时重新同步 announced 显示名。

这样运营者可以不改代码就重命名 bot, 且 announced 名字可以与
配置中的内部名不同。

## 通过 LXMF 字段实现结构化命令

机器人可以接收通过 LXMF `FIELD_COMMANDS`（`0x09`）发送的命令，
并自动以 `FIELD_RESULTS`（`0x0A`）回复。这让结构化请求/响应
工作流可以与普通文本命令并存。

传入的 `FIELD_COMMANDS` 会被解析并路由到与文本命令相同的命令
注册表，共享权限检查、类型注解参数解析、线程化和中间件。

``` python
from lxmfy import LXMFBot, FIELD_COMMANDS, FIELD_RESULTS, pack_result, unpack_commands

bot = LXMFBot(name="FieldBot")

@bot.command(name="status", description="Return bot status")
def status_cmd(ctx):
    # ctx.fields 包含原始 LXMF 字段字典
    # 如果命令带有 request_id，ctx.request_id 会自动设置
    ctx.reply("Bot is online")

# 从另一个 LXMF 客户端发送结构化命令：
# lxm.fields[FIELD_COMMANDS] = {"command": "status", "args": [], "request_id": "abc123"}
# router.handle_outbound(lxm)

# 机器人的回复会自动包含 FIELD_RESULTS，其中有响应内容和 request_id。
```

要禁用字段命令处理，在 `BotConfig` 中设置
`lxmf_commands_enabled=False`。

## 回应

回应以 LXMF `FIELD_REACTION`（`0x40`）字段的形式承载在一条
其余部分为空的消息上。`pack_reaction` 和 `unpack_reaction`
用于构造和解析该字段。

``` python
from lxmfy import pack_reaction, unpack_reaction

# 对一条消息发送回应
bot.react(destination_hash, message_hash_hex, "thumbs up emoji")

# 接收回应
@bot.on_reaction()
def on_reaction(sender, reaction):
    # reaction["reaction_to"]  - 目标消息的十六进制哈希
    # reaction["reaction_emoji"] - 回应文本（最多 16 个字符）
    # reaction["reaction_sender"] - 发送者
    print(f"{sender} reacted {reaction['reaction_emoji']} to {reaction['reaction_to']}")
    return True
```

回应文本上限为 16 个可打印字符。原始字段仍可在 `ctx.fields`
和 `msg.fields` 中访问以保持兼容。

## 回复 Threading

回复可以携带 LXMF 字段 `FIELD_REPLY_TO` (`0x30`),
`FIELD_REPLY_QUOTE` (`0x31`) 和 `FIELD_THREAD` (`0x08`)。渲染
thread 的客户端, 如 MeshChatX 和 Sideband, 会将其显示为真正的
引用回复, 而不是平铺消息。

`msg.reply()` 自动 threading: 将 `FIELD_REPLY_TO` 设为入站消息的
hash, `FIELD_THREAD` 设为会话根。

``` python
@bot.command("status")
def status(msg):
    msg.reply("all systems nominal")          # threaded 回复
    msg.reply("flat", reply_to=None)          # 退出 threading
    msg.reply("noted", quote=True)            # 引用入站文本
```

对于并非回复的发送, 显式传入字段:

``` python
bot.send(dest, "see above", reply_to=msg_hash_hex, quote="earlier text")
```

入站回复会解析到消息上下文上:

``` python
@bot.command("ctx")
def ctx_cmd(msg):
    msg.reply_to      # 此消息回复的 hex hash, 或 None
    msg.reply_quote   # 回复携带的引用文本, 或 None
    msg.thread        # thread 根的 hex hash, 或 None
```

`pack_reply(message_hash, quote=..., thread=...)` 和
`unpack_reply(fields)` 已导出, 供手动处理字段使用。

## 对话

命令可以向发送者提问, 并把其下一条消息当作回答, 而不是作为
命令分发:

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

`msg.ask(prompt, timeout=..., validator=...)` 阻塞处理器, 直到
回答到达, 超时触发或对话被取消。它返回一个 `Answer`, 带有
`content`, `fields`, `hash`, `sender` 和 `reply(text)` 快捷方法。

验证器会拒绝不合格的回答并重新提问:

``` python
num = msg.ask(
    "Pick a number",
    validator=lambda a: None if a.content.isdigit() else "Digits only",
)
```

在异步命令处理器中使用 `await msg.ask_async(...)`。对于较长的
等待, 或可能同时存在大量对话的情况, 使用回调风格, 避免线程
被挂起:

``` python
msg.ask(
    "Send the log file",
    on_answer=lambda ans: ans.reply("received"),
    on_timeout=lambda sender: bot.send(sender, "Too slow."),
    timeout=3600,
)
```

注意:

- 在问题等待期间发送已注册的命令会取消该问题并执行命令。
  用户始终有退出途径。
- `bot.conversations.pending_count()` 和
  `bot.conversations.cancel(sender)` 为诊断和管理工具开放了
  注册表。
- 注册表上限为 1024 个待回答问题。满了之后 `ask` 返回 `None`。
- 阻塞式 `ask` 会挂起处理该消息的投递线程。对直接投递是安全
  的, 但从传播节点同步大批量消息的 bot 应优先使用 `on_answer`
  回调。

## 存储

框架提供三种存储后端：

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

storage = MemoryStorage() # 完全在内存中
```

## 命令

命令注册和处理：

``` python
@bot.command(name="hello", description="Says hello")
def hello(ctx):
    ctx.reply(f"Hello {ctx.sender}!")
```

帮助元数据和访问控制来自装饰器的额外 kwargs:

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

`permissions` 覆盖默认门槛: 普通命令为 `USE_COMMANDS`,
`admin_only` 为 `ALL`。`category` 在 `/help` 输出中对命令分组。
`aliases` 只是帮助元数据: 别名会展示给用户, 但不会注册到分发,
所以 `/clear` 不会执行 `purge`, 除非你再注册一个同名命令。

### 类型注解参数

命令会根据回调函数中的类型注解自动解析和转换参数。

``` python
@bot.command(name="add", description="Adds two numbers")
def add(ctx, a: int, b: int):
    result = a + b
    ctx.reply(f"The result is {result}")
```

### 单命令速率限制

限制同一发送者在全局 `cooldown` 窗口内调用某命令的次数。达到
上限时仅拒绝本次调用, 不会产生警告或封禁。

``` python
@bot.command(name="report", rate_limit=3)
def report(ctx):
    # 每个发送者每个 cooldown 周期可调用 3 次
    ...
```

与全局速率限制一样需要 `permissions_enabled=True`。拥有 admin
角色或 `BYPASS_SPAM` 的用户会跳过检查。

## 反垃圾保护

`bot.spam_protection` 执行全局限制: 发送者在每个 `cooldown`
窗口内最多发送 `rate_limit` 条消息。超限会增加一次警告并拒绝
该消息。达到 `max_warnings` 后发送者被封禁。警告在
`warning_timeout` 秒无违规后过期。

垃圾检查在 `message_received` 事件内运行, 需要
`permissions_enabled=True`。

``` python
bot = LXMFBot(
    name="GuardedBot",
    permissions_enabled=True,
    rate_limit=5,        # 每个 cooldown 窗口的消息数
    cooldown=60,         # 窗口时长 (秒)
    max_warnings=3,      # 封禁前的警告次数
    warning_timeout=300, # 警告重置前的秒数
)

# 手动解除封禁
bot.spam_protection.unban(sender_hash)
```

警告, 封禁和计数器持久化在配置的存储后端中, 因此封禁在重启后
仍然有效。拥有 `BYPASS_SPAM` 的发送者永远不会被限速或封禁。
`@bot.command` 上的单命令 `rate_limit` 更温和: 仅拒绝调用, 从
不警告或封禁。

## 帮助系统

框架内置交互式帮助生成器，基于 Cog 和 Command 元数据生成
美观、分类的帮助菜单。

``` python
# help 命令会自动注册。
# 用户可以使用 '/help' 或 '/help <command>'
```

## 线程化命令

对于不直接与 Reticulum Network Stack 交互的耗时或阻塞操作，
可以让命令在独立线程中运行，保持机器人响应性。

``` python
import time

@bot.command(name="long_task", description="Performs a long-running task in a separate thread", threaded=True)
def long_task_command(ctx):
    ctx.reply("Starting a long task... please wait.")
    time.sleep(10) # 这在独立线程中运行
    ctx.reply("Long task completed!")
```

!!! warning "线程安全"

    标记为 `threaded=True` 的函数**不得**直接与 Reticulum
    Network Stack（RNS）或任何依赖 `lxmfy.transport.py` 的组件
    交互，因为它们通常不是线程安全的。在线程化命令中向用户
    回发消息请使用 `ctx.reply()`。

## 事件

用于处理各类 bot 事件的事件系统:

``` python
@bot.events.on("message_received", EventPriority.HIGHEST)
def handle_message(event):
    # event.data 携带负载, 如 sender 和 message
    event.cancel()  # 停止后续处理器和其余处理
```

处理器按 `EventPriority` 顺序运行: `HIGHEST`, `HIGH`, `NORMAL`,
`LOW`。垃圾检查本身是一个 `HIGHEST` 的 `message_received`
处理器, 因此取消该事件就是限速器丢弃消息的机制。

分发你自己的事件:

``` python
from lxmfy import Event

bot.events.dispatch(Event("order_placed", data={"user": ctx.sender}))
```

`event_logging_enabled`, `max_logged_events` 和
`event_middleware_enabled` 存在于 `BotConfig`, 但未接线: 事件不
会写入存储, `bot.events.use()` 是空实现。请将其视为保留项。

## 测试

`lxmfy.testing.TestBot` 是为测试预配置的 `LXMFBot`。不启动任何
Reticulum 实例。入站消息会走真实的接收流水线 (中间件, 垃圾检
查, 权限, 分发), 出站发送被捕获以供断言。

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
  注入一条消息并返回产生的 `SentMessage` 对象。发送者是命名
  的: `"alice"` 映射到一个稳定的假 hash, 或直接传入 hex 目标
  hash。
- `bot.drain()` 取出排队的出站消息。`bot.outbox` 累积所有已发
  送内容。`bot.last_sent(sender=...)` 获取最近一条。
- `bot.wait_sent(n, timeout=...)` 等待线程化命令。
- `bot.receive_later(content, sender=..., delay=...)` 从 daemon
  线程回应阻塞式 `msg.ask` 调用。
- `fake_message(content, source_hash=..., ...)` 构造一条入站消息,
  用于直接驱动 `bot._message_received`。

`SentMessage` 封装每条捕获的出站消息: `destination` (hex),
`content`, `title`, `fields`, `method`, `include_ticket`,
`stamp_cost` 和 `raw` (底层对象)。

仓库的测试套件还包括可靠性和压力场景。使用仓库的测试运行器
执行。

### 高级可靠性测试套件

框架包含一套针对严苛环境的大规模自动化测试：

- **Manifold Testing**：校验 NLP 意图向量空间的数学拓扑。
- **Chaos Engineering**：模拟位衰减、SD 卡故障和存储损坏。
- **Temporal Drift**：验证对系统时钟跳变（±1 年）的抵抗力。
- **Leak Detection**：长期跟踪内存、文件描述符和线程。

## 权限

用于控制机器人功能访问的权限系统：

``` python
from lxmfy import DefaultPerms

@bot.command(name="admin", description="Admin command", admin_only=True)
def admin_command(ctx):
    if ctx.is_admin:
        ctx.reply("Admin command executed")
```

通过 `permissions_enabled=True` 启用。`DefaultPerms`
标志位:

- `USE_BOT`, `SEND_MESSAGES`, `USE_COMMANDS`: 基础访问
- `MANAGE_MESSAGES`, `MANAGE_COMMANDS`, `MANAGE_USERS`: 高级
- `BYPASS_RATELIMIT`, `BYPASS_SPAM`, `VIEW_ADMIN_COMMANDS`: 特殊
- `VIEW_EVENTS`, `MANAGE_EVENTS`, `BYPASS_EVENT_CHECKS`: 事件系统
- `NONE`, `ALL`: 快捷方式

`bot.permissions` 管理角色与指派:

``` python
bot.permissions.create_role("moderator", DefaultPerms.MANAGE_MESSAGES | DefaultPerms.BYPASS_SPAM)
bot.permissions.assign_role(user_hash, "moderator")
bot.permissions.remove_role(user_hash, "moderator")
bot.permissions.has_permission(user_hash, DefaultPerms.USE_COMMANDS)
```

角色与指派持久化在配置的存储后端中。存在两个不可删除的内置
角色: `user` (默认) 和 `admin`, 后者自动授予 `admins` 中的每个
hash。

## 中间件

用于处理消息和事件的中间件系统:

``` python
from lxmfy import MiddlewareType

@bot.middleware.register(MiddlewareType.PRE_COMMAND)
def pre_command_middleware(ctx):
    # ctx 封装消息上下文, ctx.cancelled 会丢弃它
    if "spamword" in ctx.data.content:
        ctx.cancel()
```

流水线中有三个点会执行中间件:

- `PRE_COMMAND`: 在命令分发之前, 垃圾检查之后。若链条返回
  `None`, 消息被完全丢弃。
- `POST_COMMAND`: 在命令回调之后 (包括线程化命令, 它们在工作
  线程中触发)。
- `PRE_EVENT`: 在 `message_received` 事件分发之前。

`POST_EVENT`, `REQUEST` 和 `RESPONSE` 存在于 `MiddlewareType`,
但目前流水线中没有任何环节执行它们。

## 附件

支持发送文件、图片和音频：

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

## 图标外观（LXMF 字段）

你可以为机器人设置自定义图标，兼容的 LXMF 客户端可以显示它。
这使用 `LXMF.FIELD_ICON_APPEARANCE`。

``` python
from lxmfy import IconAppearance, pack_icon_appearance_field
import LXMF # 需要 LXMF.FIELD_ICON_APPEARANCE

# 定义图标外观
icon_data = IconAppearance(
    icon_name="smart_toy",  # 来自 Material Symbols 的名称
    fg_color=b'\xFF\xFF\xFF',  # 白色前景（3 字节）
    bg_color=b'\x4A\x90\xE2'   # 蓝色背景（3 字节）
)

# 打包成 LXMF 字段格式
icon_lxmf_field = pack_icon_appearance_field(icon_data)

# 发送带此图标的消息
bot.send(
    destination_hash_str,
    "Hello from your friendly bot!",
    title="Bot Message",
    lxmf_fields=icon_lxmf_field
)

# 也可以与其他字段组合，例如附件：
# attachment_field = pack_attachment(some_attachment)
# combined_fields = {**icon_lxmf_field, **attachment_field}
# bot.send(destination, "Message with icon and attachment", lxmf_fields=combined_fields)
```

## 调度器

任务调度系统：

``` python
@bot.scheduler.schedule(name="daily_task", cron_expr="0 0 * * *")
def daily_task():
    # 每天午夜运行
    pass
```

## 签名

LXMFy 为 LXMF 内置的加密消息签名与校验提供配置选项：

``` python
from lxmfy import LXMFBot

bot = LXMFBot(
    name="SecureBot",
    signature_verification_enabled=True,  # 启用签名检查
    require_message_signatures=False      # 设为 True 可拒绝未签名消息
)
```

!!! note "签名处理"

    LXMF 使用 RNS 身份自动处理所有加密签名和校验。LXMFy 的
    `SignatureManager` 是一个配置层，负责：

    - 控制是否强制执行签名校验
    - 确定对未签名消息的策略（接受或拒绝）
    - 与权限系统集成（例如可信用户可跳过校验）

实际的加密操作由 LXMF/RNS 执行，而不是 LXMFy。

### Landlock LSM 沙箱

在支持 Landlock 的 Linux 内核（5.13+）上，LXMFy 可以限制
机器人进程和外部脚本 Cog 的文件系统访问。

**机器人进程沙箱**

当 `landlock_enabled=True`（默认）且未运行于 `test_mode` 时，
机器人会在初始化期间调用 `apply_landlock_sandbox()`。系统目录
为只读；机器人存储、配置、Cog、Reticulum 配置和临时路径保持
可写。

``` python
bot = LXMFBot(
    name="SecureBot",
    landlock_enabled=True,
)

status = bot.get_landlock_status()
# status 的键：landlock_kernel_supported、landlock_requested、
# landlock_auto_enabled、landlock_disabled_by_env、landlock_active
```

**环境变量覆盖**

- `LXMFY_LANDLOCK=0`：即使内核支持也禁用 Landlock
- `LXMFY_LANDLOCK=1`：在 Linux 上无论自动检测结果如何都尝试
  Landlock
- 未设置：遵循 `landlock_enabled` 和内核自动检测

**外部 Cog 沙箱**

脚本 Cog 使用 `external_cogs_sandbox_type`。在 `auto` 模式下
优先使用 Landlock（若可用），因为它不需要外部工具。完整的
沙箱选项列表见[创建机器人](creating-bots.md)指南。

### 身份固定

LXMFy 支持可选的身份固定，防止身份被轮换或泄露后遭到冒充。
启用后，机器人会把一个 LXMF 地址“固定”到首次见到的公钥。

``` python
bot = LXMFBot(
    identity_pinning_enabled=True
)
```

### SignatureManager 方法

当 `signature_verification_enabled=True` 时，可通过
`bot.signature_manager` 访问 `SignatureManager`：

- `should_verify_message(sender)`：判断来自给定发送者的消息
  是否应校验
- `handle_unsigned_message(sender, message_hash)`：按策略处理
  缺少有效签名的消息

### LXMF 签名的工作原理

LXMF 在 `pack()` 操作期间使用发送者的 RNS 身份自动为所有出站
消息签名。接收消息时，LXMF 校验签名并提供：

- `message.signature_validated`：布尔值，表示签名是否有效
- `message.unverified_reason`：校验失败时的原因码（例如
  `SIGNATURE_INVALID`、`SOURCE_UNKNOWN`）

LXMFy 使用这些 LXMF 内置属性来执行机器人的签名策略。

## 消息投递

LXMFy 提供高级消息投递功能，包括传播节点和自动重试：

### 传播节点

通过特定传播节点发送消息，提高在 Reticulum 网络上的可靠性：

``` python
# 在配置/运行时层面只设置一次传播节点
bot.set_propagation_node("<propagation_node_hash>")

# 按配置好的投递行为发送
bot.send(
    destination_hash,
    "Message content"
)

# 传播节点哈希应该是 Reticulum 网络上
# 一个有效的 LXMF 传播节点
```

也可以在构造时用 `propagation_node="<hash>"` 固定节点,
或让 bot 自行发现节点:

``` python
bot = LXMFBot(
    name="AutoBot",
    autopeer_propagation=True, # 从 announce 中学习节点
    autopeer_maxdepth=4,       # 忽略深度超过 4 跳的节点
)
```

`bot.get_propagation_node_status()` 报告手动节点, 发现的节点以及
当前使用的出站节点。

### 自动重试

为失败的直接投递配置自动重试次数：

``` python
bot = LXMFBot(
    name="ReliableBot",
    direct_delivery_retries=5,  # 直接投递最多重试 5 次
    propagation_fallback_enabled=True
)

bot.send(destination_hash, "Important message")

# direct_delivery_retries 默认为 3
# 重试逻辑会自动处理投递回调
```

重试系统会跟踪每个目标的投递尝试次数，并自动重试失败的投递。
投递成功后会重置该目标的重试计数器。

### 延迟发送

向节点尚未听闻其身份的目的地发送通常会直接失败。在
`pending_sends_enabled` (默认) 下, 消息会被保留在存储中, 并在
目的地 announce 时或周期性扫描时自动发出。

``` python
bot = LXMFBot(
    pending_sends_enabled=True,
    pending_sends_max=200,     # 超过此数后最旧的保留消息被丢弃
    pending_sends_ttl=604800,  # 保留消息 7 天后过期
    pending_sends_retry=300,   # run() 中扫描间隔秒数
)

# 单次发送覆盖
bot.send(dest, "hold this", defer=True)
bot.send(dest, "send or drop", defer=False)
```

被保留的发送在管理命令 `/queue` 中显示为 `held (unknown
peers)`, 并在投递跟踪器中产生 `deferred` 事件。

### 消息持久化

出站消息可以持久化到磁盘，确保机器人重启后仍能送达。持久化
默认开启。内存出站队列有上限（`message_queue_size`，默认 50），
满了之后会丢弃最旧的消息。无效的目标哈希不会被恢复。

``` python
bot = LXMFBot(
    message_persistence_enabled=True,
    message_queue_size=50,
)
```

### Stamps 与 tickets

Stamp 成本让发送者在消息被接受前支付 proof-of-work, 从而抑制
不受欢迎的流量。LXMFy 暴露了该机制的两端。

``` python
bot = LXMFBot(
    stamp_cost=16,          # 要求此入站 stamp 成本
    require_stamps=True,    # 拒绝 stamp 无效的消息
    include_tickets=True,   # 允许对端回复而无需生成 stamp
)
```

- `stamp_cost` 是入站要求。发送的出站成本仍来自对端的
  announce, 除非向 `bot.send()` 传入 `stamp_cost=`。
- `include_tickets` (默认 True) 为出站消息附带回复 ticket, 使
  要求 stamp 的对端可以免费回复。可用 `include_ticket=` 按发送
  覆盖。
- `request_unknown_identities=True` 在收到未知来源的消息时向
  网络请求发送者身份, 帮助 stamp 和签名校验解析身份而不是盲目
  失败。

运行时控制在 《路由器控制》 一节:
`set_inbound_stamp_cost`, `enforce_stamps`, `ignore_stamps`,
`generate_ticket` 以及 ticket 检查方法。

### 作为传播节点运行

一个 bot 可以同时充当 LXMF 传播节点, 为离线的对端存储消息:

``` python
bot = LXMFBot(
    enable_propagation_node=True,
    message_storage_limit_mb=500,
)

bot.set_message_storage_limit(750)
stats = bot.get_propagation_storage_stats()
```

`get_propagation_node_status()` 对两种角色都有效: 报告本 bot
使用的出站节点以及它自身是否作为节点服务。相关控制:
`announce_propagation_node()` 对外宣传该节点,
`set_retain_on_node()` 在节点上保留已投递消息,
`allow_control_identity()` / `disallow_control_identity()` 管理
哪些身份可以使用节点的控制通道。

### 投递事件

`bot.delivery` 记录一个有界的出站生命周期事件流, 无需读日志
即可观察消息流。阶段: `queued`, `deferred`, `dispatched`,
`delivered`, `failed`, `cancelled`, `dropped`。最近的一段会持久
化到存储并在启动时恢复。

``` python
@bot.on_delivery_event()
def watch(event):
    print(event["stage"], event.get("destination"), event.get("reason"))

# 或直接检查
recent = bot.delivery.recent(20)
failures = bot.delivery.recent(stage="failed")
to_peer = bot.delivery.recent(destination="aa11bb...")
```

每个事件是一个 dict, 含 `ts`, `stage` 以及可选的 `destination`,
`message_id`, `hash`, `method`, `attempts`, `reason`, `title`。

管理员有 `/delivery [limit]` 命令, 可在聊天中渲染同一时间线,
`lxmfy debug` 在发送流水线检查中显示投递时间线摘要。

### 内置管理命令

这些命令自动注册, 并在启用权限时要求发送者在 `admins` 中:

| 命令 | 作用 |
| --- | --- |
| `/queue` | 显示路由器出站队列, 内部队列和保留的发送 |
| `/cancel <id|all>` | 取消待投递的出站消息 |
| `/inbox [cancel <hash|all>]` | 列出或取消活跃的入站传输 |
| `/delivery [n]` | 显示最近 n 条投递事件 (默认 15, 最多 50) |
| `/loadext <name>` | 加载一个 cog 扩展 |
| `/reloadext <name>` | 重新加载已加载的 cog 扩展 |

### 路由器控制

对底层 `LXMRouter` 的轻封装, 覆盖发送者控制, ticket, 出站队列
管理和传播节点同步。所有方法接受 hex 字符串形式的目标 hash,
在路由器未运行时 (例如 `test_mode`) 返回 `False`。

**发送者控制 (入站)**

- `ignore_destination(destination)` / `unignore_destination(destination)` / `is_ignored(destination)`:
  丢弃来自某发送者的入站消息
- `allow_destination(destination)` / `disallow_destination(destination)`:
  路由器处于 allow-list 模式时的白名单管理
- `prioritise_destination(destination)` / `unprioritise_destination(destination)`:
  优先发送者名单
- `set_inbound_stamp_cost(stamp_cost)`: 对入站消息要求 stamp
  成本 (`None` 清除)
- `enforce_stamps()` / `ignore_stamps()`: 入站 stamp 强制开关

**Tickets**

- `generate_ticket(destination, expiry=None)`: 为发送者签发入站
  stamp ticket
- `get_inbound_tickets(destination)`: 为发送者持有的 ticket
- `get_outbound_ticket(destination)` / `get_outbound_ticket_expiry(destination)` /
  `get_outbound_stamp_cost(destination)`: 从网络学到的出站
  ticket 状态

**出站队列**

- `outbound_queue()`: 待投递出站消息的快照
- `get_outbound_progress(lxm_hash)`: 某消息 hash 的投递进度或
  `None`
- `cancel_outbound(message_id)`: 在投递前移除排队消息
- `delivery_link_available(destination)`: 是否存在指向目标的活跃
  RNS link

**入站队列**

- `has_message(message_hash)`: 入站 LXM hash 是否已投递
- `inbound_count()`: 进行中的活跃入站资源传输数
- `inbound_transfers()`: 每个传输的快照, 含 hash, 大小, 进度和
  状态
- `cancel_inbound(resource_hash)`: 中止一个活跃的入站传输
- `cancel_all_inbound()`: 中止所有活跃的入站传输, 返回取消数量

**对端发现**

本节点听闻过的目的地的 announce 元数据:

- `get_peer_app_data(destination)`: 原始 announced app_data 字节
- `get_peer_lxmf_data(destination)`: 解码后的 LXMF announce 元
  数据 (`display_name`, `stamp_cost`, `capabilities`), 对端未
  announce 有效 LXMF 数据时为 `None`
- `get_peer_announce(destination)`: 完整 announce 记录, 含 hops,
  received_at, interface 和 app_data
- `list_peer_announces(limit=100)`: 所有听闻的 announce, 最新者
  在前

**传播**

- `sync_propagation_node(max_messages=None)`: 从配置的传播节点拉
  取消息
- `cancel_propagation_sync()`: 停止进行中的同步
- `get_propagation_stats()`: 节点传输状态与限制, 或 `None`
- `set_retain_on_node(retain)`: 在节点上保留已投递消息
- `announce_propagation_node()`: 将本节点 announce 为传播节点
- `allow_control_identity(destination)` / `disallow_control_identity(destination)`:
  传播控制通道白名单

**导入**

- `ingest_lxm_uri(uri)`: 将 `lxm://` URI 消息导入入站队列

## 诊断

当消息不通时, 调试器会检查整条链路而不是靠猜: Reticulum 配置,
共享实例状态, 接口, 身份, announce 行为, 投递配置和发送流水
线。

``` bash
lxmfy debug                          # 完整 doctor 报告, 保存到文件
lxmfy debug probe <hash> --request-path --wait 30
lxmfy debug send <hash>              # 跟踪一次测试发送
lxmfy debug receive                  # 检查接收就绪状态
lxmfy debug compare <hash_a> <hash_b>
lxmfy debug tips                     # 常见故障的修复建议
```

报告默认做了隐私脱敏: home 路径和 hash 会被截断。`--json` 输出
机器可读结果, `-o FILE` 写出报告, `--no-save` 跳过文件,
`--no-privacy` 保留完整值供本地使用, `--no-color` 或 `NO_COLOR`
关闭 ANSI 输出。

同样的检查也可以在代码中调用:

``` python
report = bot.diagnose_connectivity()            # doctor 报告的 dict
probe = bot.diagnose_destination(               # 身份与路径探测
    "<peer_hash>", request_path=True, wait=30,
)

debugger = bot.get_debugger()                   # 完整 API
checks = debugger.check_send_pipeline()
verdict = debugger.run_doctor(destination)
```

`lxmfy/debugger.py` 还导出了独立的 `diagnose_destination(hash,
...)` 帮助函数, 以及报告类型 `CheckResult`, `DestinationProbe`,
`DoctorReport` 和 `MessageDebugger`, 供自建工具使用。

## 消息处理器

LXMFy 提供用于处理不同类型传入消息的装饰器：

### 首条消息处理器

处理每个用户的首条消息：

``` python
@bot.on_first_message()
def welcome_user(sender, message):
    content = message.content.decode("utf-8")
    bot.send(sender, f"Welcome! You said: {content}")
    return True  # 返回 True 停止进一步处理
```

### 通用消息处理器

在命令处理之前处理所有传入消息：

``` python
@bot.on_message()
def handle_all_messages(sender, message):
    content = message.content.decode("utf-8").strip()

    # 此处为自定义逻辑
    if content.startswith("echo:"):
        bot.send(sender, content[5:])
        return True  # 停止进一步处理

    return False  # 继续到命令处理
```

消息处理器按以下顺序调用：1. 首条消息处理器（如果这是该
发送者的首条消息）2. 通用消息处理器（通过 `on_message()`
注册）3. 命令处理（如果消息以命令前缀开头）

### 兜底回调

`bot.received(fn)` 注册一个回调, 在流水线末尾处理未被任何其他
环节消费的消息: 没有首条消息处理器, 没有返回 True 的
`on_message` 处理器, 也没有匹配的命令或 NLP intent。回调收到
与命令相同的消息上下文, 包括 `msg.sender`, `msg.content`,
`msg.reply()` 等。

``` python
@bot.received
def fallback(msg):
    msg.reply("Sorry, I did not understand that.")
```

可作为自由文本输入的兜底处理。

## Reticulum Relay Chat (RRC)

机器人可以通过 RNS Link 以 CBOR 封包加入
[RRC](https://rrc.kc1awv.net/) hub。包：`lxmfy.rrc`。

### BotConfig 选项

- `rrc_enabled`（bool，默认 `False`）：启动时连接已配置的
  hub
- `rrc_hubs`（十六进制哈希列表）：hub 目标哈希
- `rrc_rooms`（str 列表）：WELCOME 之后自动加入的房间
- `rrc_nick`（str 或 None）：HELLO 和房间消息中的昵称
- `rrc_dest_name`（str，默认 `"rrc.hub"`）：用于构造 hub
  目标的目标名称
- `rrc_auto_reconnect`（bool，默认 `True`）：link 断开后自动
  重连
- `rrc_persist_sessions`（bool，默认 `True`）：跨重启持久化
  hub 和房间
- `reticulum_config_dir`（str 或 None）：Reticulum 配置目录。
  也可用 `LXMFY_RETICULUM_CONFIG_DIR` 设置。使用与 MeshChatX
  相同的配置（通常是 `~/.reticulum`），这样 hub 的 announce
  才可见。

### 示例

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

# 运行时 API
# bot.connect_rrc(hub_hash, rooms=["general"])
# bot.rrc.send_message("general", "hello")
# bot.rrc.send_notice("general", "notice")
# bot.rrc.send_action("general", "waves")
# bot.rrc.join("ops")
# bot.rrc.part("ops")
# bot.rrc.status()
# bot.disconnect_rrc()
```

### 导出类型

- `RRCClient`：单 hub 会话
- `RRCManager`：多 hub 管理器（`bot.rrc`）
- `RRCMessage`：房间事件负载（`kind`、`room`、`text`、
  `nick`、`src`、`mention` 等）
- `RRC_VERSION`：线路协议版本常量
- `DEFAULT_DEST_NAME`: 默认 hub 目标名 (`"rrc.hub"`)
- `make_envelope`, `encode_envelope`, `decode_envelope`,
  `validate_envelope`, `normalize_room`: 供直接与 hub 通信的工具
  使用的 wire 格式帮助函数

传给 `@bot.on_rrc` 处理器的常见事件包括 `status`、`welcome`、
`joined`、`parted`、`msg`、`notice`、`action`、`motd`、
`error` 和 `rtt`。

# 模板

框架包含若干可直接使用的机器人模板：

## EchoBot

简单的 echo 机器人，复述收到的消息：

``` python
from lxmfy.templates import EchoBot

bot = EchoBot()
bot.run()
```

## NoteBot

使用 JSON 存储的笔记机器人：

``` python
from lxmfy.templates import NoteBot

bot = NoteBot()
bot.run()
```

## ReminderBot

使用 SQLite 存储的提醒机器人：

``` python
from lxmfy.templates import ReminderBot

bot = ReminderBot()
bot.run()
```

## RRCBot

RRC 房间机器人，加入配置的 hub 并回复 `@提及`。默认 hub 为
`664fc0e8d2e448658e37bb3f34e6c88f`，房间为 `#general`，并在
可用时使用 `~/.reticulum`。

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

# CLI 工具

框架提供了用于 bot 管理的命令行工具。不带参数运行 `lxmfy` 会
打开交互式菜单。

``` bash
# 交互式 scaffold 完整项目
lxmfy init mybot                 # 项目目录, bot.py, cogs/, README
lxmfy init --here --yes          # 当前目录, 接受全部默认值

# 创建单个 bot 文件
lxmfy create mybot
lxmfy create --template echo mybot
lxmfy create --template rrc my_rrc_bot
lxmfy create mybot --no-cogs     # 跳过 cogs 包
lxmfy create --output dir/bot.py --name MyBot

# 运行模板 bot
lxmfy run echo
lxmfy run rrc
lxmfy run reminder --name "MyReminder"

# 诊断连通性 (见诊断一节)
lxmfy debug
lxmfy debug probe <hash> --request-path --wait 30

# 用一条消息测试签名校验
lxmfy signatures test

# 启用签名校验
lxmfy signatures enable

# 禁用签名校验
lxmfy signatures disable
```

`lxmfy init` 会询问项目名称, 模板, 存储后端, 命令前缀和 admin
hash。每个问题都可以改用 flag: `--dir`, `--bot-name`,
`--template`, `--storage`, `--prefix`, `--admins`, `--no-cogs`,
`--force`, `--yes`。在非 TTY 的 stdin 上则直接采用默认值。

`create` 和 `run` 的模板: `basic`, `echo`, `reminder`, `note`,
`cogtest`, `rrc`。

# 错误处理

在 `bot.run()` 周围捕获关停和运行时故障：

``` python
try:
    bot.run()
except KeyboardInterrupt:
    bot.cleanup()
except Exception as e:
    logger.error(f"Error running bot: {str(e)}")
```

# 模块参考

由源码 docstring 生成。

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
