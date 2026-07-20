"""
Helper bot client factory.

Creates a Telethon ``TelegramClient`` using a bot token (not a user session).
The helper bot is optional — if ``BOT_TOKEN`` is not set, ``build_helper``
returns ``None`` and all inline UI features are silently disabled.

The helper bot uses the same Telethon connection parameters as the self-bot
for consistency: auto-reconnect, 5 retries, 2s delay, 60s flood-sleep.
"""
import logging

from telethon import TelegramClient
from telethon.sessions import StringSession

logger = logging.getLogger(__name__)

_client: TelegramClient | None = None


def is_available() -> bool:
    """Return True if the helper bot was successfully started."""
    return _client is not None and _client.is_connected()


async def build_helper(bot_token: str) -> TelegramClient | None:
    """
    Create and connect the helper bot client.

    Returns the connected ``TelegramClient`` or ``None`` if no token is set.
    Raises ``RuntimeError`` if the token is set but invalid.
    """
    global _client

    if not bot_token:
        logger.info("Helper bot: no BOT_TOKEN set — inline UI disabled")
        return None

    client = TelegramClient(
        StringSession(),
        int(__import__("os").getenv("API_ID", "0")),
        __import__("os").getenv("API_HASH", ""),
        system_version="4.16.30-vxCUSTOM",
        device_model="LifeOS-Helper",
        auto_reconnect=True,
        connection_retries=5,
        retry_delay=2,
        flood_sleep_threshold=60,
    )

    await client.connect()

    if not await client.is_user_authorized():
        raise RuntimeError(
            "Helper bot token is invalid or unauthorized. "
            "Check BOT_TOKEN — it must be a valid bot token from BotFather."
        )

    me = await client.get_me()
    logger.info("Helper bot connected as @%s (id=%s)", me.username, me.id)
    _client = client
    return client


async def disconnect_helper() -> None:
    """Disconnect the helper bot cleanly."""
    global _client
    if _client is not None:
        try:
            await _client.disconnect()
        except Exception as exc:
            logger.warning("Helper bot disconnect error: %s", exc)
        _client = None


def get_client() -> TelegramClient | None:
    """Return the current helper bot client (or None)."""
    return _client
