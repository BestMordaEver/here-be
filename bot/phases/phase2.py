import discord
from discord import app_commands
import asyncio

from bot.config import DEFAULT_CAESAR_SHIFT, SISTER_GUILD_ID, SISTER_CHANNEL_ID
from bot.utils import type_out_message

# Config keys visible in Phase 2 (superset of Phase 1)
PHASE2_VISIBLE = [
    "Server",
    "Communications channel",
    "Discovery channel",
    "Host",
    "Identity",
    "Directory",
    "Method",
    "Shift",
]

# Settable parameters in Phase 2
PHASE2_SETTABLE = {"Server", "Discovery channel", "Identity", "Method", "Shift"}

CONFIG_KEY_MAP = {
    "Server": "server",
    "Communications channel": "communications_channel",
    "Discovery channel": "discovery_channel",
    "Host": "host",
    "Identity": "identity",
    "Directory": "directory",
    "Method": "method",
    "Shift": "shift",
}


async def enter(bot):
    """Enter Phase 2 for the first time (from Phase 1 transition)."""
    state = bot.state
    state.set_config("host", "here-be")
    state.set_config("method", "Caesar")
    state.set_config("shift", DEFAULT_CAESAR_SHIFT)
    state.set_config("directory", [])
    await _sync_commands(bot)


async def resume(bot):
    """Resume Phase 2 after a restart — re-register commands, restart worker."""
    state = bot.state
    # Guard: if enter() was interrupted before setting Phase 2 config values
    if state.config.get("method") is None:
        state.set_config("host", "here-be")
        state.set_config("method", "Caesar")
        state.set_config("shift", DEFAULT_CAESAR_SHIFT)
        state.set_config("directory", state.discovered_endpoints or [])
    await _sync_commands(bot)


# ── command registration ────────────────────────────────


async def _sync_commands(bot):
    # Game guild: /configure
    game_guild = discord.Object(id=int(bot.state.game_guild_id))
    bot.tree.clear_commands(guild=game_guild)
    bot.tree.add_command(_make_configure_command(bot), guild=game_guild)
    await bot.tree.sync(guild=game_guild)

    # Sister guild: /talk, /discover
    if SISTER_GUILD_ID:
        sister_guild = discord.Object(id=SISTER_GUILD_ID)
        bot.tree.clear_commands(guild=sister_guild)
        bot.tree.add_command(_make_talk_command(bot), guild=sister_guild)
        bot.tree.add_command(_make_discover_command(bot), guild=sister_guild)
        await bot.tree.sync(guild=sister_guild)

    # Start the message-queue worker
    if not hasattr(bot, "_worker_task") or bot._worker_task.done():
        bot._worker_task = asyncio.create_task(_message_worker(bot))

    print("Phase 2 active \u2014 connection established")


# ── /configure (Phase 2 variant) ───────────────────────


def _make_configure_command(bot):
    @app_commands.command(
        name="configure",
        description="View or modify proxy configuration",
    )
    @app_commands.describe(
        parameter_name="Configuration parameter",
        parameter_value="New value",
    )
    async def configure(
        interaction: discord.Interaction,
        parameter_name: str = None,
        parameter_value: str = None,
    ):
        state = bot.state

        # No arguments → show full config
        if parameter_name is None:
            await interaction.response.send_message(
                _format_config(state), ephemeral=False
            )
            return

        # Name only → show that single entry
        if parameter_value is None:
            internal = CONFIG_KEY_MAP.get(parameter_name)
            if internal:
                val = state.config.get(internal, "???")
                if isinstance(val, list):
                    val = "\n  ".join(val) if val else "(empty)"
                await interaction.response.send_message(
                    f"{parameter_name} \u2014 {val}", ephemeral=False
                )
            else:
                await interaction.response.send_message(
                    "ERROR \u2014 unknown parameter", ephemeral=False
                )
            return

        # Both provided → attempt to set
        if parameter_name not in PHASE2_SETTABLE:
            await interaction.response.send_message(
                "ERROR \u2014 this action will disturb homeostasis",
                ephemeral=False,
            )
            return

        # ── Shift ──
        if parameter_name == "Shift":
            try:
                shift_val = int(parameter_value)
            except ValueError:
                await interaction.response.send_message(
                    f"Shift \u2014 {parameter_value} \u2717 REJECTED",
                    ephemeral=False,
                )
                return
            if shift_val == 0:
                await interaction.response.send_message(
                    "```\n\u26a0 SHIFT ZERO \u2014 RESETTING \u26a0\n```",
                    ephemeral=False,
                )
                await _factory_reset(bot)
                return
            state.set_config("shift", shift_val)
            await interaction.response.send_message(
                f"Shift \u2014 {shift_val} \u2713 UPDATED", ephemeral=False
            )
            return

        # ── Method ──
        if parameter_name == "Method":
            if parameter_value in state.discovered_methods:
                state.set_config("method", parameter_value)
                await interaction.response.send_message(
                    f"Method \u2014 {parameter_value} \u2713 UPDATED",
                    ephemeral=False,
                )
            else:
                await interaction.response.send_message(
                    "ERROR \u2014 method not recognized", ephemeral=False
                )
            return

        # ── Other settable params (Server, Discovery channel, Identity) ──
        internal = CONFIG_KEY_MAP[parameter_name]
        state.set_config(internal, parameter_value)
        await interaction.response.send_message(
            f"{parameter_name} \u2014 {parameter_value} \u2713 UPDATED",
            ephemeral=False,
        )

    @configure.autocomplete("parameter_name")
    async def _name_autocomplete(
        interaction: discord.Interaction, current: str
    ):
        return [
            app_commands.Choice(name=k, value=k)
            for k in PHASE2_VISIBLE
            if current.lower() in k.lower()
        ]

    return configure


# ── /talk ───────────────────────────────────────────────


def _make_talk_command(bot):
    @app_commands.command(
        name="talk", description="Send a message through Proxy"
    )
    @app_commands.describe(message="Message to relay")
    async def talk(interaction: discord.Interaction, message: str):
        await bot.message_queue.put(message)
        queue_size = bot.message_queue.qsize()
        label = "queued" if queue_size > 1 else "sending"
        await interaction.response.send_message(
            f"\u2713 {label} ({queue_size} in queue)", ephemeral=True
        )

    return talk


# ── /discover ───────────────────────────────────────────


def _make_discover_command(bot):
    @app_commands.command(
        name="discover",
        description="Announce a discovered endpoint",
    )
    @app_commands.describe(url="The discovered endpoint path or URL")
    async def discover(interaction: discord.Interaction, url: str):
        bot.state.add_endpoint(url)
        disco = bot.get_channel(int(bot.state.discoveries_channel_id))
        if disco:
            await disco.send(f"\U0001F4E1 New endpoint discovered: `{url}`")
        await interaction.response.send_message(
            f"\u2713 announced {url}", ephemeral=True
        )

    return discover


# ── player message relay ────────────────────────────────


async def relay_player_message(bot, message):
    """Relay a player message from #communications to the sister server."""
    if not SISTER_CHANNEL_ID:
        return
    sister_ch = bot.get_channel(SISTER_CHANNEL_ID)
    if not sister_ch:
        return

    embed = discord.Embed(
        description=message.content,
        color=0x5865F2,
        timestamp=message.created_at,
    )
    avatar_url = (
        message.author.display_avatar.url
        if message.author.display_avatar
        else None
    )
    embed.set_author(name=message.author.display_name, icon_url=avatar_url)
    await sister_ch.send(embed=embed)


# ── typing-effect message worker ────────────────────────


async def _message_worker(bot):
    """Background task that dequeues /talk messages and types them out."""
    while True:
        text = await bot.message_queue.get()
        try:
            channel = bot.get_channel(int(bot.state.communications_channel_id))
            if channel:
                await type_out_message(channel, text)
                await asyncio.sleep(1.5)
        except Exception as exc:
            print(f"Message worker error: {exc}")
        finally:
            bot.message_queue.task_done()


# ── factory reset ───────────────────────────────────────


def _format_config(state):
    cfg = state.config
    directory = cfg.get("directory", [])
    if isinstance(directory, list):
        dir_display = "\n  ".join(directory) if directory else "(empty)"
    else:
        dir_display = str(directory)

    lines = [
        f"Server \u2014 {cfg.get('server', '???')}",
        f"Communications channel \u2014 {cfg.get('communications_channel', '???')}",
        f"Discovery channel \u2014 {cfg.get('discovery_channel', '???')}",
        f"Host \u2014 {cfg.get('host', '???')}",
        f"Identity \u2014 {cfg.get('identity', '???')}",
        f"Directory \u2014 {dir_display}",
        f"Method \u2014 {cfg.get('method', '???')}",
        f"Shift \u2014 {cfg.get('shift', '???')}",
    ]
    return "```\n" + "\n".join(lines) + "\n```"


async def _factory_reset(bot):
    """Shift 0: delete the game guild, wipe state, restart from Phase 0."""
    game_guild_id = bot.state.game_guild_id
    if game_guild_id:
        guild = bot.get_guild(int(game_guild_id))
        if guild:
            try:
                await guild.delete()
            except discord.HTTPException as exc:
                print(f"Failed to delete guild: {exc}")

    # Clear sister-server commands
    if SISTER_GUILD_ID:
        sister = discord.Object(id=SISTER_GUILD_ID)
        bot.tree.clear_commands(guild=sister)
        try:
            await bot.tree.sync(guild=sister)
        except discord.HTTPException:
            pass

    bot.state.reset()
    from bot.phases import phase0
    await phase0.enter(bot)
