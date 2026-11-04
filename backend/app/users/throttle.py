import time

from app.core.errors import TooManyRequests


class LoginThrottle:
    """Locks an email out after repeated failed sign-ins.

    ponytail: in-process memory, so each replica counts on its own and a restart resets it.
    Move to the database or a shared cache if the app runs on many replicas.
    """

    def __init__(self, max_failures: int = 5, window_seconds: float = 900) -> None:
        self.max_failures = max_failures
        self.window = window_seconds
        self._failures: dict[str, list[float]] = {}

    def _recent(self, key: str) -> list[float]:
        cutoff = time.monotonic() - self.window
        recent = [t for t in self._failures.get(key, []) if t > cutoff]
        if recent:
            self._failures[key] = recent
        else:
            self._failures.pop(key, None)
        return recent

    def check(self, key: str) -> None:
        if len(self._recent(key)) >= self.max_failures:
            raise TooManyRequests("Too many failed sign-in attempts. Try again in a few minutes.")

    def fail(self, key: str) -> None:
        if len(self._failures) > 10_000:  # bound memory against floods of made-up emails
            self._failures.clear()
        self._failures.setdefault(key, []).append(time.monotonic())

    def clear(self, key: str) -> None:
        self._failures.pop(key, None)
