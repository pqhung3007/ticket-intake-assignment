"""Password hashing with stdlib scrypt (memory-hard; no extra dependency).

Stored format: scrypt$N$r$p$salt$hash (base64). Parameters travel with the hash so they can be
raised later without invalidating existing passwords.
"""

import base64
import hashlib
import hmac
import os

_N, _R, _P = 2**14, 8, 1
MIN_LENGTH = 10


def _b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode()


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P, dklen=32)
    return f"scrypt${_N}${_R}${_P}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt, digest = stored.split("$")
        if scheme != "scrypt":
            return False
        expected = base64.b64decode(digest)
        actual = hashlib.scrypt(
            password.encode(), salt=base64.b64decode(salt), n=int(n), r=int(r), p=int(p), dklen=len(expected)
        )
    except ValueError:
        return False
    return hmac.compare_digest(actual, expected)


# Verified when the account does not exist, so "unknown email" costs the same as "wrong password".
DUMMY_HASH = hash_password("not-a-real-password")
