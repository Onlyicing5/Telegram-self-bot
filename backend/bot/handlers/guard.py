"""
Permission guard — single source of truth.
Every handler calls `is_owner` before executing any logic.
"""


def is_owner(event, owner_id: int) -> bool:
    return bool(event.sender_id and event.sender_id == owner_id)
