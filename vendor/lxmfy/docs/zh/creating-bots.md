# 创建机器人

## 基本结构

一个最小的 LXMFy 机器人包含以下步骤：

1.  导入 `LXMFBot`。
2.  用所需配置实例化 `LXMFBot`。
3.  定义命令或事件处理器。
4.  使用 `bot.run()` 运行机器人。

``` python
from lxmfy import LXMFBot

# 1. 实例化机器人
bot = LXMFBot(
    name="SimpleBot",
    command_prefix="!",
    storage_path="simple_data"
)

# 2. 定义命令
@bot.command(name="ping", description="Responds with pong")
def ping_command(ctx):
    # ctx 是包含消息信息的上下文对象
    # ctx.sender: 发送者的 LXMF 哈希
    # ctx.content: 完整消息内容
    # ctx.args: 命令之后的参数列表
    # ctx.reply(message): 发送回复的函数
    #   （也可以接受关键字参数，如 title="My Title", lxmf_fields=some_fields）
    ctx.reply("Pong!")

# 对于耗时任务，可以使用线程化命令：
# import time
# @bot.command(name="long_op", description="Performs a long operation in a separate thread", threaded=True)
# def long_op_command(ctx):
#     ctx.reply("Starting long operation...")
#     time.sleep(10) # 模拟耗时操作
#     ctx.reply("Long operation complete!")
# 重要：线程化命令不应直接与 RNS 或 lxmfy.transport.py 交互。

@bot.command(name="greet", description="Greets the user")
def greet_command(ctx):
    if ctx.args:
        name = " ".join(ctx.args)
        ctx.reply(f"Hello, {name}!")
    else:
        ctx.reply("Hello there! Tell me your name: !greet <your_name>")

# 3. 运行机器人
if __name__ == "__main__":
    print(f"Starting bot: {bot.config.name}")
    print(f"Bot LXMF Address: {bot.local.hash}")
    bot.run()
```

## 使用模板

LXMFy 为常见机器人类型提供了若干模板。可以用 CLI 基于模板生成
机器人文件。

如果需要完整项目目录而不是单个文件, `lxmfy init` 会生成
`bot.py`, 一个 `cogs` 包, README 和 `.gitignore`, 并在过程中
询问模板, 存储后端, 命令前缀和 admin hash。

``` bash
# 创建一个 echo 机器人
lxmfy create --template echo my_echo_bot

# 创建一个提醒机器人（使用 SQLite 存储）
lxmfy create --template reminder my_reminder_bot

# 创建一个笔记机器人（使用 JSON 存储）
lxmfy create --template note my_note_bot

# 创建一个 Cog 测试机器人（测试 Cog 加载功能）
lxmfy create --template cogtest my_cog_test_bot

# 创建一个 RRC 房间机器人（加入 hub 并回复 @提及）
lxmfy create --template rrc my_rrc_bot

# 或者直接运行模板
lxmfy run rrc
```

运行这些命令会创建一个 Python 文件（例如 `my_echo_bot.py`），
它会导入并运行所选模板。之后可以修改生成的文件或模板代码本身
（`lxmfy/templates/...`）。

**生成的文件示例（`my_cog_test_bot.py`）：**

``` python
from lxmfy.templates import CogTestBot

if __name__ == "__main__":
    bot = CogTestBot() # 创建 CogTestBot 模板的实例
    # 可以选择性地覆盖默认名称：
    # bot.bot.name = "My Cog Test Bot"
    bot.run()
```

## 机器人配置

创建 `LXMFBot` 实例时，可以传入各种关键字参数来配置其行为。
常见选项列表见 [API 参考](api-reference.md)中的 `BotConfig`
小节，或[快速上手指南](quick-start.md)。

``` python
from lxmfy import LXMFBot

bot = LXMFBot(
    name="ConfiguredBot",
    announce=3600, # 每小时 announce 一次
    admins={"your_admin_hash_here"}, # 设置管理员用户
    command_prefix="$", # 使用 '$' 作为前缀
    storage_type="sqlite", # 使用 SQLite 数据库
    storage_path="data/my_bot_data.db", # 指定数据库文件路径
    rate_limit=10, # 允许每分钟 10 条消息
    cooldown=30, # 冷却 30 秒
    permissions_enabled=True # 启用基于角色的权限
)

if __name__ == "__main__":
    # 也可以在实例化之后修改配置
    # 注意：有些设置最好在初始化时设置
    bot.config.max_warnings = 5
    bot.spam_protection.config.max_warnings = 5 # 同步更新刷屏保护器

    bot.run()
```

### 设置机器人图标（LXMF 字段）

你可以给机器人设置自定义图标，它会显示在兼容的 LXMF 客户端中。
这使用 `LXMF.FIELD_ICON_APPEARANCE`，可以在发送消息时设置。

首先，确保引入了所需的模块：

``` python
from lxmfy import IconAppearance, pack_icon_appearance_field
```

然后即可定义并使用图标：

``` python
# 在你的机器人类或初始化代码中
icon_data = IconAppearance(
    icon_name="robot_2",  # 从 Material Symbols 中选择
    fg_color=b'\x00\xFF\x00',  # 绿色
    bg_color=b'\x33\x33\x33'   # 深灰色
)
self.bot_icon_field = pack_icon_appearance_field(icon_data)

# 发送消息或回复时：
ctx.reply("Message from your bot!", lxmf_fields=self.bot_icon_field)
# 或
# bot.send(destination, "Another message", lxmf_fields=self.bot_icon_field)
```

这个 `self.bot_icon_field` 可以预先计算好，供机器人发送的所有
消息复用。

## 通过 LXMF 字段实现结构化命令

除文本命令外，LXMFy 还支持通过 LXMF 消息字段发送的命令，即
`FIELD_COMMANDS`（`0x09`）。这对 LXMF 客户端与机器人之间的
结构化请求/响应工作流很有用。

当消息包含 `FIELD_COMMANDS` 时，机器人会提取命令名和参数，
将其路由到与文本命令相同的命令注册表，并自动在回复中包含
`FIELD_RESULTS`（`0x0A`）。

**接收结构化命令**

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

字段命令回调中的 `ctx` 对象包含：

- `ctx.fields`：传入消息的原始 LXMF 字段字典
- `ctx.request_id`：传入 `FIELD_COMMANDS` 中的 `request_id`
  （如果有）

**从 LXMF 客户端发送结构化命令**

``` python
import LXMF
from lxmfy import FIELD_COMMANDS

lxm = LXMF.LXMessage(
    destination,
    source,
    b"",  # 纯字段命令的内容可以为空
    desired_method=LXMF.LXMessage.DIRECT,
)
lxm.fields[FIELD_COMMANDS] = {
    "command": "add",
    "args": ["3", "5"],
    "request_id": "req-42",  # 可选，用于关联请求
}
router.handle_outbound(lxm)
```

**禁用字段命令**

如果你希望机器人忽略 `FIELD_COMMANDS`，只处理文本命令，设置：

``` python
bot = LXMFBot(
    name="TextOnlyBot",
    lxmf_commands_enabled=False,
)
```

## 使用 Cog（扩展）

Cog 允许你把命令和事件监听器组织到独立的文件（模块）中，
使主机器人文件更整洁。

1.  **创建一个 `cogs` 目录**（或你在 `BotConfig` 中通过
    `cogs_dir` 设置的任意目录）。
2.  **在 `cogs` 目录中创建 Python 文件**（例如 `utility.py`）。
3.  **定义一个类**，继承自 `lxmfy.Cog`（可选，但推荐），或者
    只是一个普通类。
4.  **在类中定义命令**，使用 `@Command` 装饰器标记方法。
5.  **在 Cog 文件中创建 `setup(bot)` 函数**，LXMFy 会调用它
    来注册该 Cog。

**示例（`cogs/utility.py`）：**

``` python
from lxmfy import Command
from lxmfy.commands import Cog  # 如果要继承，导入 Cog
import time

class UtilityCog: # 或者 class UtilityCog(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = time.time()

    @Command(name="uptime", description="Shows bot uptime")
    # 注意：Cog 中的方法通常接收 'self' 和 'ctx'
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
        time.sleep(7) # 模拟耗时操作
        ctx.reply("Long cog task completed!")

# 加载该 Cog 必须有这个函数
def setup(bot):
    cog_instance = UtilityCog(bot)
    bot.add_cog(cog_instance) # 向机器人注册 Cog 实例
```

**主机器人文件（`my_bot.py`）：**

``` python
from lxmfy import LXMFBot

bot = LXMFBot(
    name="CogBot",
    cogs_enabled=True, # 确保启用了 Cog（默认开启）
    cogs_dir="cogs" # 指向该目录
)

if __name__ == "__main__":
    # 如果 cogs_enabled 为 True，
    # Cog 会在 LXMFBot 初始化期间自动加载。
    bot.run()
```

机器人启动时会自动找到 `utility.py`，调用其 `setup` 函数，
该函数创建 `UtilityCog` 实例并通过 `bot.add_cog()` 注册。
之后 Cog 中定义的命令（`uptime`、`info`）即可使用。

## 外部脚本 Cog（多语言支持）

你也可以用 Python 以外的语言（例如 Bash、Ruby、Perl、Go、C）
编写机器人扩展，即外部脚本 Cog。

1.  **在 `cogs` 目录中创建一个可执行脚本。**
2.  **在脚本顶部添加 shebang**（例如 `#!/bin/bash`）。
3.  **确保脚本可执行**（`chmod +x your_script`）。

机器人启动时，会自动把 `cogs` 目录中任何不以 `.py` 结尾的
可执行文件注册为机器人命令。

**参数协议：**

- `$1`：发送者的 LXMF 哈希。
- `$2`：完整消息内容。
- `$3`、`$4`、...：各命令参数。

**环境变量：**

- `LXMFY_SENDER`：发送者的身份哈希。
- `LXMFY_CONTENT`：完整消息内容。
- `LXMFY_HAS_ADMIN`：根据发送者的管理员状态为 `true` 或
  `false`。

**Bash Cog 示例（`cogs/greet.sh`）：**

``` bash
#!/bin/bash
echo "Hello from Bash! You sent: $2"
```

当用户发送 `/greet hello` 时，机器人会执行该脚本并用其 stdout
回复：`Hello from Bash! You sent: /greet hello`。

## 本地 NLP 意图分类

LXMFy 内置一个本地意图分类器。当消息文本没有精确匹配命令前缀
时，它会把文本与带标签的示例短语匹配。

1.  **在机器人配置中启用 NLP**：`nlp_enabled=True`。
2.  **使用 `@bot.intent` 装饰器定义意图。**

``` python
@bot.intent("help", examples=["how do I use this?", "show me commands", "help me please"])
def help_intent(msg):
    msg.reply("I can help! Try typing /help to see a list of commands.")
```

匹配使用 TF-IDF 向量和余弦相似度。所有评分都在机器人所在主机
上运行，不会把文本发送到外部 API。

**模型导出和导入**

导出并导入训练好的模型，让较大的机器人不必每次启动都重新
训练：

``` python
# 导出模型
model_data = bot.nlp.export_model()
# 把 model_data 保存到文件或数据库

# 之后重新导入
bot.nlp.import_model(model_data)
```

## RNS Link 支持

机器人可以建立并响应直接的 RNS Link，用于有状态、流式或比单个
LXMF 数据包更高带宽的流量。

1.  **在配置中启用 Link 支持**：`link_support_enabled=True`。
2.  **请求 link**：`bot.request_link(destination_hash)`。也可以
    指定自定义应用名和 aspects：
    `bot.request_link(dest, callback, "my_app", "aspect1")`。
3.  **处理传入 link**：用 `bot.on_link(handler)` 注册回调。

``` python
def handle_link(link):
    print(f"Link established with {RNS.hexrep(link.destination.hash)}")
    # 现在可以使用该 link 进行直接的 RNS 通信

bot.on_link(handle_link)
```

**安全与沙箱：**

- **超时：** 外部 Cog 有默认超时（30 秒）以防止挂起。可通过
  `external_cogs_timeout` 配置。
- **线程：** 所有外部 Cog 都在独立线程中运行，不会阻塞机器人。
- **机器人进程沙箱（仅 Linux）：** 当 `landlock_enabled=True`
  （默认）且内核支持 Landlock LSM（5.13+）时，机器人会在启动后
  对自身进程应用文件系统沙箱。可写路径仅限于存储、配置、Cog、
  Reticulum 配置和临时目录。可用环境变量 `LXMFY_LANDLOCK=0`
  禁用，或用 `LXMFY_LANDLOCK=1` 强制尝试。
- **外部 Cog 沙箱（仅 Linux）：** 当
  `external_cogs_sandbox_enabled=True`（默认）时，可执行脚本
  Cog 在受限环境中运行。`external_cogs_sandbox_type` 可设置为
  以下之一：
  - `auto`（默认）：优先使用 Landlock（若支持），否则用
    `bubblewrap`（`bwrap`），再否则用 `firejail`
  - `landlock`：通过 `preexec_fn` 实现的纯 Landlock 沙箱
    （规则比机器人进程沙箱更窄）
  - `bwrap`：bubblewrap 只读绑定沙箱
  - `firejail`：firejail 私有配置，无网络
  - `none`：不使用子进程沙箱
- **状态：** 调用 `bot.get_landlock_status()` 可查看内核支持
  情况、是否请求了 Landlock，以及机器人进程沙箱是否激活。

## 处理消息

LXMFy 提供了多种在处理的不同阶段处理传入消息的方式。

### 首条消息处理器

处理每个新用户的首条消息（适用于欢迎消息）：

``` python
from lxmfy import LXMFBot

bot = LXMFBot(
    name="WelcomeBot",
    first_message_enabled=True  # 必须为 True（默认）
)

@bot.on_first_message()
def welcome_new_user(sender, message):
    content = message.content.decode("utf-8")
    bot.send(
        sender,
        f"Welcome to the bot! You said: {content}\n\n"
        "Type /help to see available commands."
    )
    return True  # 返回 True 以停止该消息的进一步处理

if __name__ == "__main__":
    bot.run()
```

### 通用消息处理器

在命令处理之前处理所有传入消息：

``` python
from lxmfy import LXMFBot

bot = LXMFBot(name="EchoBot")

@bot.on_message()
def echo_non_commands(sender, message):
    content = message.content.decode("utf-8").strip()

    # 检查是否为命令，是则交给命令处理器
    if content.startswith(bot.config.command_prefix):
        command_name = content.split()[0][len(bot.config.command_prefix):]
        if command_name in bot.commands:
            return False  # 交给命令处理器处理

    # 不是命令，回显它
    bot.send(sender, f"You said: {content}")
    return False  # 返回 False 继续处理（虽然不会有命令匹配）

@bot.command(name="hello", description="Say hello")
def hello_command(ctx):
    ctx.reply("Hello! This is a command response.")

if __name__ == "__main__":
    bot.run()
```

消息处理器的处理顺序：

1.  **首条消息处理器**（当 `first_message_enabled=True` 且这是
    该发送者的首条消息时）
2.  **通用消息处理器**（通过 `@bot.on_message()` 注册）
3.  **命令处理**（当消息匹配某个已注册命令时）

处理器可以返回 `True` 停止进一步处理，或返回 `False` 继续到
下一阶段。

## 处理事件

你可以使用 `@bot.events.on()` 装饰器为各种机器人事件注册
处理器。

``` python
from lxmfy import LXMFBot
from lxmfy.events import EventPriority # 可选，用于优先级

bot = LXMFBot(name="EventBot")

@bot.events.on("message_received")
def log_message(event):
    # Event 对象包含详细信息
    sender = event.data.get("sender")
    message_content = event.data.get("message").content.decode('utf-8', errors='ignore')
    print(f"Received message from {sender}: {message_content}")

    # 可以取消事件处理（例如停止消息处理）
    # if sender == "some_blocked_hash":
    #    event.cancel()

@bot.events.on("command_executed", priority=EventPriority.LOW)
def log_command(event):
    # 示例：event.data 可能包含 {'command_name': 'ping', 'sender': '...', ...}
    command_name = event.data.get('command_name', 'unknown')
    sender = event.data.get('sender', 'unknown')
    print(f"Command '{command_name}' executed by {sender}")

# 也可以定义自定义事件
@bot.command(name="special")
def special_command(ctx):
    ctx.reply("Doing something special!")
    # 派发一个自定义事件
    bot.events.dispatch(Event("special_action_taken", data={"user": ctx.sender}))

@bot.events.on("special_action_taken")
def handle_special(event):
    user = event.data.get("user")
    print(f"Special action was taken by user: {user}")


if __name__ == "__main__":
    bot.run()
```

`Event` 结构和优先级的更多细节见 `lxmfy/events.py`。

## 存储

LXMFy 提供 JSON、SQLite、MsgPack 和内存四种存储后端。

- **JSON：** 简单、可读，适合小数据集。用
  `storage_type="json"` 和 `storage_path="your_data_dir"` 配置。
- **SQLite：** 对更大数据集或频繁写入更高效。用
  `storage_type="sqlite"` 和 `storage_path="your_db_file.db"`
  配置。
- **MsgPack：** 紧凑的二进制格式，与 JSON 同样采用每键一个文件的
  布局。用 `storage_type="msgpack"` 和
  `storage_path="your_data_dir"` 配置。
- **内存：** 完全在 RAM 中存储，关闭后状态丢失。用
  `storage_type="memory"` 配置。

可以通过 `bot.storage` 访问存储接口：

``` python
# 保存数据
bot.storage.set("user_prefs:" + ctx.sender, {"theme": "dark"})

# 获取数据（带默认值）
prefs = bot.storage.get("user_prefs:" + ctx.sender, {})
theme = prefs.get("theme", "light")

# 检查数据是否存在
if bot.storage.exists("some_key"):
    print("Key exists!")

# 删除数据
bot.storage.delete("old_data_key")

# 按前缀扫描键（便于枚举用户数据）
user_keys = bot.storage.scan("user_prefs:")
for key in user_keys:
    user_data = bot.storage.get(key)
    print(f"Data for {key}: {user_data}")
```

更多细节见 `lxmfy/storage.py` 和 API 参考。

## 权限

LXMFy 包含一个可选的基于角色的权限系统。在 `LXMFBot` 初始化时
用 `permissions_enabled=True` 启用。

- **角色：** 定义带有特定权限的角色（例如
  `DefaultPerms.MANAGE_USERS`）。
- **权限：** 在 `DefaultPerms` 中定义的细粒度标志（例如
  `USE_COMMANDS`、`BYPASS_SPAM`）。
- **分配：** 把角色分配给用户哈希。

用法细节见 `lxmfy/permissions.py`、API 参考和示例 Cog
（如果有的话）。

## 签名校验

LXMFy 为 LXMF 内置的加密消息签名与校验提供配置。所有 LXMF
消息都由 LXMF/RNS 协议栈自动签名，LXMFy 只是允许你强制执行
签名校验策略。

**配置：**

在机器人配置中启用签名校验：

``` python
bot = LXMFBot(
    name="SecureBot",
    signature_verification_enabled=True,  # 启用签名检查
    require_message_signatures=False      # 设为 True 可拒绝未签名消息
)
```

**工作原理：**

LXMF 自动处理所有加密操作：

1.  **出站消息：** LXMF 在打包消息时使用发送者的 RNS 身份
    自动为所有消息签名。
2.  **入站消息：** LXMF 使用发送者的 RNS 身份自动校验签名，
    并提供校验结果。
3.  **LXMFy 的角色：** LXMFy 检查 LXMF 的校验结果并执行你的
    策略：
    - 若 `signature_verification_enabled=False`：接受所有消息
      （默认）
    - 若 `signature_verification_enabled=True` 且
      `require_message_signatures=False`：接受消息，但会记录
      未签名或签名无效的情况
    - 若 `signature_verification_enabled=True` 且
      `require_message_signatures=True`：拒绝未签名或无效的
      消息
4.  **与权限系统集成：** 拥有 `BYPASS_SPAM` 权限的用户可以
    绕过签名校验要求。

**CLI 管理：**

你可以使用 CLI 管理签名校验设置：

``` bash
# 测试签名校验
lxmfy signatures test

# 启用签名校验
lxmfy signatures enable

# 禁用签名校验
lxmfy signatures disable
```

**技术细节：**

LXMF 使用 RNS 加密体系提供的 Ed25519 签名。每条 LXMF 消息都
包含发送者的签名，并依据其已知 RNS 身份进行校验。LXMFy 只是
读取 LXMF 的 `message.signature_validated` 属性和
`message.unverified_reason` 来执行机器人的安全策略。

## 消息投递

### 使用传播节点

通过特定的 LXMF 传播节点发送消息：

``` python
from lxmfy import LXMFBot

bot = LXMFBot(name="PropagationBot")

@bot.command(name="send", description="Send via propagation node")
def send_command(ctx):
    # 只设置一次特定的传播节点（配置层面）
    bot.set_propagation_node("<propagation_node_hash_here>")

    # 按配置好的投递策略发送
    bot.send(
        ctx.sender,
        "This message will use direct delivery with propagation fallback as configured"
    )
```

当目标离线或当前路径上的直接投递持续失败时，可以使用传播
节点。

### 配置重试

通过机器人配置为投递失败的消息配置自动重试：

``` python
from lxmfy import LXMFBot

bot = LXMFBot(name="ReliableBot")

bot = LXMFBot(
    name="ReliableBot",
    direct_delivery_retries=5,  # 直接投递最多重试 5 次
    propagation_fallback_enabled=True
)

@bot.command(name="important", description="Send important message with retries")
def important_command(ctx):
    bot.send(ctx.sender, "This is an important message")

@bot.command(name="normal", description="Send with default retries")
def normal_command(ctx):
    # direct_delivery_retries 默认为 3
    bot.send(ctx.sender, "This message uses default retry settings")
```

重试系统会：

- 自动跟踪每个目标的投递尝试次数
- 对失败的直接投递最多重试 `direct_delivery_retries` 次
- 投递成功后重置重试计数器
- 记录重试尝试和失败以便调试

### 延迟发送与 stamps

两个值得尽早了解的投递细节:

- **延迟发送**: 当目的地身份未知时, `send()` 会把消息保留在
  存储中 (`pending_sends_*` 配置项控制积压), 并在对端
  announce 时发出。向发送传入 `defer=False` 则丢弃而非保留。
- **Stamps**: `stamp_cost` 设置入站 proof-of-work 要求,
  `require_stamps` 拒绝不满足要求的消息, `include_tickets`
  (默认) 附带回复 ticket, 让对端无需支付自己的 stamp 成本
  即可回复你的 bot。

当投递异常时, `lxmfy debug` 会走完整条链路 (配置, 实例, 接口,
身份, 发送流水线) 并生成一份可分享的脱敏报告。同样的检查也可
以通过 `bot.diagnose_connectivity()` 和
`bot.diagnose_destination(hash)` 调用。

完整的投递功能见 [API 参考](api-reference.md): 重试,
传播节点, 队列持久化, 投递事件流以及管理命令 `/queue`,
`/cancel`, `/inbox`, `/delivery`。

## Reticulum Relay Chat (RRC)

LXMFy 机器人可以作为普通客户端通过 RNS Link 加入
[RRC](https://rrc.kc1awv.net/) hub，使用 CBOR 封包。这与
NomadNet 和 rrcd 风格的 hub 兼容（包括 MeshChatX 托管或加入
同一 hub 的情况）。

### Reticulum 配置很关键

机器人必须与 hub 使用**同一个** Reticulum 网络。MeshChatX
通常使用 `~/.reticulum` 配合骨干网或 TCP 接口。项目本地的
`config/` 目录往往使用独立的实例名且只用 AutoInterface，
这样 hub 的 announce 永远到不了，你会看到
`Hub identity unknown`。

建议采用以下之一：

- 把 `reticulum_config_dir` 设为你的用户配置（通常是
  `~/.reticulum`）
- 或者导出 `LXMFY_RETICULUM_CONFIG_DIR=~/.reticulum`
- 保持 MeshChatX 或 `rnsd` 运行，让共享实例在机器人启动前
  就绪

`rrc` 模板在该目录存在时默认使用 `~/.reticulum`。

### 用模板快速开始

``` bash
lxmfy run rrc
```

默认值：

- Hub：`664fc0e8d2e448658e37bb3f34e6c88f`
- 房间：`#general`
- Reticulum 配置：`~/.reticulum`（或
  `LXMFY_RETICULUM_CONFIG_DIR`）

你应该能在日志中看到 hub 连接、welcome、自动加入以及
`RRC joined #general`。

### 编程方式实现 RRC 机器人

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

也可以在运行时连接：

``` python
bot.connect_rrc("hub_destination_hash", rooms=["general"])
bot.rrc.send_message("general", "hello room")
bot.rrc.send_action("general", "waves")
bot.disconnect_rrc()
```

### 会话行为

- HELLO / WELCOME、JOIN / PART、MSG / NOTICE / ACTION、
  PING / PONG、ERROR、RESOURCE_ENVELOPE
- 断线自动重连，并在 WELCOME 之后重新加入房间
- 客户端侧的 hub 上限和限流执行
- 跨重启的会话持久化（`rrc_persist_sessions`，默认开启）
- 出站 LXMF 队列持久化是独立功能
  （`message_persistence_enabled`）
