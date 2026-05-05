import discord
from discord.ext import commands
import asyncio

from bot.config import DISCORD_TOKEN
from bot.state import BotState


class ProxyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)

        self.state = BotState()
        self.message_queue = asyncio.Queue()
        self._setup_lock = asyncio.Lock()

    async def setup_hook(self):
        self.state.load()

    async def on_ready(self):
        async with self._setup_lock:
            print(f"Proxy online as {self.user} (phase {self.state.phase})")
            await self._resume_phase()

    async def _resume_phase(self):
        phase = self.state.phase
        if phase == 0:
            from bot.phases import phase0
            await phase0.enter(self)
        elif phase == 1:
            from bot.phases import phase1
            await phase1.resume(self)
        elif phase == 2:
            from bot.phases import phase2
            await phase2.resume(self)

    async def on_message(self, message):
        if message.author.bot:
            return

        # Phase 2: relay player messages from #communications to the sister server
        if (
            self.state.phase == 2
            and self.state.communications_channel_id
            and message.channel.id == int(self.state.communications_channel_id)
        ):
            from bot.phases import phase2
            await phase2.relay_player_message(self, message)

        await self.process_commands(message)


def main():
    if not DISCORD_TOKEN:
        print("Error: DISCORD_BOT_TOKEN not set in environment")
        return
    bot = ProxyBot()
    bot.run(DISCORD_TOKEN)


if __name__ == "__main__":
    main()
