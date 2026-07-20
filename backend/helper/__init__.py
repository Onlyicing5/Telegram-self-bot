"""
Helper Bot — inline keyboard / callback query infrastructure.

The helper bot is a *secondary* Telegram client (bot token, not user session)
that handles inline UI concerns only:
  - inline keyboards
  - callback queries
  - inline menus
  - editing inline messages

The self-bot (Telethon StringSession) remains the brain — it processes
commands and business logic. The helper bot is purely a presentation layer
for interactive Telegram UI elements that require a bot token.

Architecture:
  - ``build_helper(bot_token)`` — creates and connects the Telethon
    ``TelegramClient`` for the bot. Returns ``None`` if no token is set.
  - ``register_callback_handlers(client, owner_id)`` — wires the
    callback-query router onto the helper client.
  - ``panels`` module — provides ``InlinePanelBuilder`` for constructing
    inline keyboards and ``register_panel`` for registering panel handlers.

Lifecycle:
  - Started in ``main.py`` Phase 3.5 (after self-bot handlers, before web).
  - Stopped in shutdown (disconnected cleanly, zero orphans).
  - If ``BOT_TOKEN`` is not set, the helper bot is simply skipped — the
    self-bot continues to work without inline UI.
"""
from backend.helper.client import build_helper, is_available
from backend.helper.panels import (
    InlinePanelBuilder,
    register_panel,
    get_panel,
)

__all__ = [
    "build_helper",
    "is_available",
    "InlinePanelBuilder",
    "register_panel",
    "get_panel",
]
