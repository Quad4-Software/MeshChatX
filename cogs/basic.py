from lxmfy import Command


class BasicCommands:
    def __init__(self, bot):
        self.bot = bot

    @Command(name="hello", description="Says hello")
    async def hello(self, ctx):
        ctx.reply(f"Hello {ctx.sender}!")

    @Command(name="about", description="About this bot")
    async def about(self, ctx):
        ctx.reply("I'm a bot created with LXMFy!")


def setup(bot):
    bot.add_cog(BasicCommands(bot))
