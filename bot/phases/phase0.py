import discord
from discord import app_commands
import asyncio

from bot.config import SISTER_GUILD_ID, SISTER_CHANNEL_ID


async def enter(bot):
    """Enter Phase 0: create the game guild if needed, register /ping."""
    # Clear sister-server commands (handles reset from Phase 2)
    if SISTER_GUILD_ID:
        sister = discord.Object(id=SISTER_GUILD_ID)
        bot.tree.clear_commands(guild=sister)
        try:
            await bot.tree.sync(guild=sister)
        except discord.HTTPException:
            pass

    if not bot.state.game_guild_id:
        await _create_game_guild(bot)

    game_guild = discord.Object(id=int(bot.state.game_guild_id))
    bot.tree.clear_commands(guild=game_guild)

    @app_commands.command(name="ping", description="Ping the proxy")
    async def ping(interaction: discord.Interaction):
        await interaction.response.send_message("PONG", ephemeral=True)
        interaction.client.state.phase = 1
        from bot.phases import phase1
        asyncio.create_task(phase1.enter(interaction.client))

    bot.tree.add_command(ping, guild=game_guild)
    await bot.tree.sync(guild=game_guild)
    print(f"Phase 0 active \u2014 /ping registered on guild {bot.state.game_guild_id}")


async def _create_game_guild(bot):
    """Create the game server with #communications and #discoveries."""
    guild = await bot.create_guild(name="Entry Point")
    await asyncio.sleep(3)

    full_guild = bot.get_guild(guild.id)
    if not full_guild:
        full_guild = await bot.fetch_guild(guild.id)

    # Remove the default channels Discord creates
    try:
        channels = await full_guild.fetch_channels()
        for ch in channels:
            try:
                await ch.delete()
            except discord.HTTPException:
                pass
    except discord.HTTPException:
        pass

    # Create the two required channels
    comms = await full_guild.create_text_channel("communications")
    disco = await full_guild.create_text_channel("discoveries")

    # Persist IDs
    bot.state.game_guild_id = str(guild.id)
    bot.state.communications_channel_id = str(comms.id)
    bot.state.discoveries_channel_id = str(disco.id)

    # Generate a permanent invite and post it to the sister server
    invite = await comms.create_invite(max_age=0, max_uses=0)
    if SISTER_CHANNEL_ID:
        sister_ch = bot.get_channel(SISTER_CHANNEL_ID)
        if sister_ch:
            await sister_ch.send(f"\U0001F517 {invite.url}")

    print(f"Created guild '{guild.name}' ({guild.id})")
