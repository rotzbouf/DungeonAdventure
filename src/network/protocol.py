"""
Wire protocol — length-prefixed JSON frames.

Frame format:  [4-byte big-endian uint32 body-length][UTF-8 JSON body]

All messages are plain dicts with a "type" key.
"""
from __future__ import annotations
import json
import struct

_HEADER = struct.Struct(">I")   # 4-byte big-endian unsigned int


def pack(msg: dict) -> bytes:
    """Serialise *msg* to a complete frame ready to write to a socket."""
    body = json.dumps(msg, separators=(',', ':')).encode()
    return _HEADER.pack(len(body)) + body


class Unpacker:
    """
    Feed raw bytes in arbitrary chunks; call feed() to get decoded messages.
    Maintains an internal buffer so partial frames are handled correctly.
    """

    def __init__(self):
        self._buf = bytearray()

    def feed(self, data: bytes) -> list[dict]:
        """Append *data* to the buffer and return all complete messages."""
        self._buf += data
        out: list[dict] = []
        while len(self._buf) >= 4:
            (length,) = _HEADER.unpack_from(self._buf)
            if len(self._buf) < 4 + length:
                break
            body = bytes(self._buf[4 : 4 + length])
            del self._buf[: 4 + length]
            try:
                out.append(json.loads(body))
            except json.JSONDecodeError:
                pass   # drop malformed frame silently
        return out
