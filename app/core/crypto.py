"""
Шифрование/дешифрование настроек.
Поддерживает Windows DPAPI и кроссплатформенный fallback (HMAC-SHA256).
"""
import json
import hmac
import base64
import hashlib
import platform
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

# Секрет для fallback-шифрования
_APP_SECRET = "KIwcVIWqzrPoBzrlTdN1lvnTcpX7sikf"


def _is_windows() -> bool:
    return platform.system().lower().startswith("win")


# ─── DPAPI (Windows only) ───────────────────────────────────────────

def _dpapi_protect(data: bytes) -> bytes:
    """Шифрует данные через Windows DPAPI."""
    import ctypes
    from ctypes import wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [
            ("cbData", wintypes.DWORD),
            ("pbData", ctypes.POINTER(ctypes.c_char)),
        ]

    crypt = ctypes.windll.crypt32.CryptProtectData
    crypt.argtypes = [
        ctypes.POINTER(DATA_BLOB), wintypes.LPWSTR,
        ctypes.POINTER(DATA_BLOB), ctypes.c_void_p,
        ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(DATA_BLOB),
    ]
    crypt.restype = wintypes.BOOL

    in_blob = DATA_BLOB(
        cbData=len(data),
        pbData=ctypes.cast(
            ctypes.create_string_buffer(data),
            ctypes.POINTER(ctypes.c_char),
        ),
    )
    out_blob = DATA_BLOB()

    if not crypt(
        ctypes.byref(in_blob), None, None, None, None, 0,
        ctypes.byref(out_blob),
    ):
        raise RuntimeError("DPAPI CryptProtectData failed")

    try:
        return ctypes.string_at(out_blob.pbData, out_blob.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(out_blob.pbData)


def _dpapi_unprotect(data: bytes) -> bytes:
    """Дешифрует данные через Windows DPAPI."""
    import ctypes
    from ctypes import wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [
            ("cbData", wintypes.DWORD),
            ("pbData", ctypes.POINTER(ctypes.c_char)),
        ]

    crypt = ctypes.windll.crypt32.CryptUnprotectData
    crypt.argtypes = [
        ctypes.POINTER(DATA_BLOB), ctypes.POINTER(wintypes.LPWSTR),
        ctypes.POINTER(DATA_BLOB), ctypes.c_void_p,
        ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(DATA_BLOB),
    ]
    crypt.restype = wintypes.BOOL

    in_blob = DATA_BLOB(
        cbData=len(data),
        pbData=ctypes.cast(
            ctypes.create_string_buffer(data),
            ctypes.POINTER(ctypes.c_char),
        ),
    )
    out_blob = DATA_BLOB()

    if not crypt(
        ctypes.byref(in_blob), None, None, None, None, 0,
        ctypes.byref(out_blob),
    ):
        raise RuntimeError("DPAPI CryptUnprotectData failed")

    try:
        return ctypes.string_at(out_blob.pbData, out_blob.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(out_blob.pbData)


# ─── Fallback (кроссплатформенный) ──────────────────────────────────

def _fallback_key() -> bytes:
    return hashlib.sha256(_APP_SECRET.encode("utf-8")).digest()


def _fallback_encrypt(data: bytes) -> bytes:
    key = _fallback_key()
    mac = hmac.new(key, data, hashlib.sha256).digest()
    return base64.b64encode(mac + data)


def _fallback_decrypt(packed: bytes) -> bytes:
    raw = base64.b64decode(packed)
    key = _fallback_key()
    mac_stored = raw[:32]
    data = raw[32:]
    mac_computed = hmac.new(key, data, hashlib.sha256).digest()
    if not hmac.compare_digest(mac_stored, mac_computed):
        raise RuntimeError("Settings integrity check failed")
    return data


# ─── Публичный API ──────────────────────────────────────────────────

def encrypt_dict(d: Dict[str, Any]) -> bytes:
    """Сериализует dict в JSON и шифрует."""
    data = json.dumps(
        d, ensure_ascii=False, separators=(",", ":"), sort_keys=True,
    ).encode("utf-8")

    if _is_windows():
        try:
            return b"WDP1" + _dpapi_protect(data)
        except Exception:
            logger.warning("DPAPI недоступен, используем fallback")

    return b"FBK1" + _fallback_encrypt(data)


def decrypt_dict(blob: bytes) -> Dict[str, Any]:
    """Дешифрует blob и возвращает dict."""
    if not blob:
        return {}

    try:
        if blob.startswith(b"WDP1"):
            return json.loads(
                _dpapi_unprotect(blob[4:]).decode("utf-8")
            )
        if blob.startswith(b"FBK1"):
            return json.loads(
                _fallback_decrypt(blob[4:]).decode("utf-8")
            )
        # Попытка прочитать как незашифрованный JSON (миграция)
        return json.loads(blob.decode("utf-8", errors="replace"))
    except Exception:
        logger.exception("Не удалось расшифровать настройки")
        return {}
