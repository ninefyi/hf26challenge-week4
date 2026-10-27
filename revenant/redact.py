"""Hide secrets in a command before any model sees it. Replaces, never guesses meaning."""
import re

_URL = re.compile(r"\b[a-zA-Z][a-zA-Z0-9+.-]*://[^\s'\"]+")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_ENV_SECRET = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*(?:KEY|TOKEN|SECRET|PASSWORD|PASSWD|PASS)[A-Za-z0-9_]*)=(\S+)", re.I)
_BEARER = re.compile(r"(?i)\b(bearer|token|basic)\s+[A-Za-z0-9._~+/=-]{8,}")
_LONG_TOKEN = re.compile(r"\b(?=[A-Za-z0-9_-]*\d)(?=[A-Za-z0-9_-]*[A-Za-z])[A-Za-z0-9_-]{24,}\b")
_LONG_NUM = re.compile(r"\b\d{6,}\b")
_IPV4 = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")


def redact(command: str, names: tuple[str, ...] = ()) -> str:
    out = _ENV_SECRET.sub(lambda m: f"{m.group(1)}=<secret>", command)
    out = _BEARER.sub(lambda m: f"{m.group(1)} <secret>", out)
    out = _URL.sub("<url>", out)
    out = _EMAIL.sub("<email>", out)
    out = _IPV4.sub("<ip>", out)
    out = _LONG_TOKEN.sub("<token>", out)
    out = _LONG_NUM.sub("<number>", out)
    for name in names:
        out = re.sub(re.escape(name), "<name>", out, flags=re.I)
    return out
