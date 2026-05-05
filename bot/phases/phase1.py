import discord
from discord import app_commands
import asyncio
import random

from bot.utils import get_garbage_messages

# Config keys visible in /configure during Phase 1
PHASE1_VISIBLE = [
    "Server",
    "Communications channel",
    "Discovery channel",
    "Host",
    "Identity",
    "Directory",
]

# Only these three can be set in Phase 1; everything else returns the homeostasis error
PHASE1_SETTABLE = {"Server", "Discovery channel", "Identity"}

# Maps display names to internal config dict keys
CONFIG_KEY_MAP = {
    "Server": "server",
    "Communications channel": "communications_channel",
    "Discovery channel": "discovery_channel",
    "Host": "host",
    "Identity": "identity",
    "Directory": "directory",
}


async def enter(bot):
    """Enter Phase 1 for the first time: post the boot sequence, then register /configure."""
    comms = bot.get_channel(int(bot.state.communications_channel_id))
    if comms:
        for msg_text in get_garbage_messages():
            await comms.send(f"```\n{msg_text}\n```")
            await asyncio.sleep(random.uniform(2.0, 4.0))

        host = bot.state.host_string
        await comms.send(
            f"`/home/{host}/Proxy: multiple configuration errors \u2014 "
            f"SERVER_ID_MISMATCH, DISCOVERIES_ID_MISMATCH, IDENTITY_MISMATCH`"
        )

    await _sync_configure(bot)
    print("Phase 1 active \u2014 /configure registered")


async def resume(bot):
    """Resume Phase 1 after a restart (no garbage replay)."""
    await _sync_configure(bot)

    # If the player already fixed everything before the restart, advance
    if _phase1_complete(bot.state):
        comms = bot.get_channel(int(bot.state.communications_channel_id))
        await _transition_to_phase2(bot, comms)
    else:
        print("Phase 1 resumed \u2014 /configure registered")


# ── internal helpers ────────────────────────────────────


async def _sync_configure(bot):
    game_guild = discord.Object(id=int(bot.state.game_guild_id))
    bot.tree.clear_commands(guild=game_guild)
    bot.tree.add_command(_make_configure_command(bot), guild=game_guild)
    await bot.tree.sync(guild=game_guild)


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
                await interaction.response.send_message(
                    f"{parameter_name} \u2014 {val}", ephemeral=False
                )
            else:
                await interaction.response.send_message(
                    "ERROR \u2014 unknown parameter", ephemeral=False
                )
            return

        # Both provided → try to set
        if parameter_name not in PHASE1_SETTABLE:
            await interaction.response.send_message(
                "ERROR \u2014 this action will disturb homeostasis",
                ephemeral=False,
            )
            return

        internal = CONFIG_KEY_MAP[parameter_name]
        expected = _get_expected(state, parameter_name)

        if parameter_value == expected:
            state.set_config(internal, parameter_value)
            await interaction.response.send_message(
                f"{parameter_name} \u2014 {parameter_value} \u2713 UPDATED",
                ephemeral=False,
            )
            if _phase1_complete(state):
                await _transition_to_phase2(bot, interaction.channel)
        else:
            await interaction.response.send_message(
                f"{parameter_name} \u2014 {parameter_value} \u2717 REJECTED",
                ephemeral=False,
            )

    @configure.autocomplete("parameter_name")
    async def _name_autocomplete(
        interaction: discord.Interaction, current: str
    ):
        return [
            app_commands.Choice(name=k, value=k)
            for k in PHASE1_VISIBLE
            if current.lower() in k.lower()
        ]

    return configure


def _format_config(state):
    cfg = state.config
    lines = [
        f"Server \u2014 {cfg.get('server', '???')}",
        f"Communications channel \u2014 {cfg.get('communications_channel', '???')}",
        f"Discovery channel \u2014 {cfg.get('discovery_channel', '???')}",
        f"Host \u2014 {cfg.get('host', '???')}",
        f"Identity \u2014 {cfg.get('identity', '???')}",
        f"Directory \u2014 {cfg.get('directory', 'ERROR')}",
    ]
    return "```\n" + "\n".join(lines) + "\n```"


def _get_expected(state, parameter_name):
    if parameter_name == "Server":
        return str(state.game_guild_id)
    if parameter_name == "Discovery channel":
        return str(state.discoveries_channel_id)
    if parameter_name == "Identity":
        return "Proxy"
    return None


def _phase1_complete(state):
    cfg = state.config
    return (
        cfg.get("server") == str(state.game_guild_id)
        and cfg.get("discovery_channel") == str(state.discoveries_channel_id)
        and cfg.get("identity") == "Proxy"
    )


async def _transition_to_phase2(bot, channel):
    host = bot.state.host_string
    if channel:
        await channel.send(
            f"`/home/{host}/Proxy: configuration resolved. Establishing connection...`"
        )
    bot.state.phase = 2
    from bot.phases import phase2
    await phase2.enter(bot)
