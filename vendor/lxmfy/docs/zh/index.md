# LXMFy

用于在 [Reticulum 网络](https://reticulum.network/)上构建 [LXMF](https://github.com/Quad4-Software/LXMF) 机器人的 Python 框架。

```python
from lxmfy import LXMFBot

bot = LXMFBot(name="MyBot")

@bot.command(name="ping", description="Responds with pong")
def ping(ctx):
    ctx.reply("Pong!")

bot.run()
```

## 指南

- [快速上手](quick-start.md) - 安装 LXMFy，几分钟内让机器人接入网络
- [创建机器人](creating-bots.md) - 命令、Cog、存储、权限、RRC 和投递
- [API 参考](api-reference.md) - 配置选项、方法和模块文档

## 内置功能

- 命令注册表，支持带类型注解的参数、自动生成帮助和管理员限制
- 支持用 Python 或任何可执行语言编写的 Cog
- LXMF 字段命令, 回应, 回复 threading, 附件和图标外观
- 对话 (msg.ask), 免网络测试框架和连通性调试器
- 通过传播节点投递, 带重试, 延迟发送和队列持久化
- 可选的 NLP 意图、权限、签名、Landlock 沙箱
- 兼容 NomadNet 和 MeshChatX hub 的 RRC 房间客户端

## 下载

PDF、EPUB 和文本打包文档随 [GitHub releases](https://github.com/Quad4-Software/LXMFy/releases) 提供。

## 语言

- [English](../index.md)
- [Deutsch](../de/index.md)
- [Español](../es/index.md)
- [Français](../fr/index.md)
- [Português](../pt/index.md)
- [Українська](../uk/index.md)
- [Русский](../ru/index.md)
- [简体中文](index.md)
