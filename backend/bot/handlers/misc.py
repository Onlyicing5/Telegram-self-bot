"""
.ping  — Editing the trigger message with PONG (zero-spam policy).
.id    — Chat ID + Message ID of the current context.
.help  — Full command reference.
"""
import logging
from telethon import events
from backend.bot.handlers.guard import is_owner

logger = logging.getLogger(__name__)

_HELP = (
    "**LifeOS — Command Reference**\n\n"
    "**Utility**\n"
    "`.ping` — PONG\n"
    "`.id` — Chat ID + Message ID\n"
    "`.help` — This message\n\n"
    "**Save Engine** (reply to a message)\n"
    "`.save f` — Forward save (metadata + forward)\n"
    "`.save d` — Deep save (download + re-upload)\n"
    "`.preview <code>` — Show saved item metadata\n"
    "`.send <code>` — Forward saved asset to current chat\n\n"
    "**Organizer**\n"
    "`.organize list` — LifeOS data overview\n"
    "`.organize clean` — Purge logs older than 7 days\n"
    "`.del <n>` — Delete last n outgoing messages\n"
    "`.del id <msgid>` — Delete from msgid forward\n\n"
    "**Bio Engine**\n"
    "`.bio help` — Token reference\n"
    "`.bio template <tpl>` — Set template\n"
    "`.bio text <text>` — Set {text}\n"
    "`.bio mood <mood>` — Set {mood}\n"
    "`.bio on` — Start cron\n"
    "`.bio off` — Stop cron\n"
    "`.bio show` — Inspect state"
)


def register(client, owner_id: int):

    @client.on(events.NewMessage(outgoing=True, pattern=r"^\.ping$"))
    async def ping(event):
        if not is_owner(event, owner_id):
            return
        try:
            await event.edit("PONG")
        except Exception as exc:
            logger.warning("ping edit failed: %s", exc)

    @client.on(events.NewMessage(outgoing=True, pattern=r"^\.id$"))
    async def id_cmd(event):
        if not is_owner(event, owner_id):
            return
        try:
            chat_id = event.chat_id
            msg_id = event.message.id
            reply = await event.message.get_reply_message()
            lines = [f"**Chat ID:** `{chat_id}`", f"**Msg ID:** `{msg_id}`"]
            if reply:
                lines.append(f"**Reply Msg ID:** `{reply.id}`")
                lines.append(f"**Reply Sender ID:** `{reply.sender_id}`")
            await event.edit("\n".join(lines))
        except Exception as exc:
            logger.warning("id_cmd failed: %s", exc)

    @client.on(events.NewMessage(outgoing=True, pattern=r"^\.help$"))
    async def help_cmd(event):
        if not is_owner(event, owner_id):
            return
        try:
            await event.edit(_HELP)
        except Exception as exc:
            logger.warning("help edit failed: %s", exc)
