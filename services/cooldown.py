import time


class CooldownStore:
    def __init__(self) -> None:
        self._last_seen: dict[int, float] = {}

    def remaining(self, user_id: int, cooldown_seconds: int) -> int:
        now = time.monotonic()
        previous = self._last_seen.get(user_id, 0)
        remaining = int(cooldown_seconds - (now - previous))
        if remaining <= 0:
            self._last_seen[user_id] = now
            return 0
        return remaining


cooldown_store = CooldownStore()
