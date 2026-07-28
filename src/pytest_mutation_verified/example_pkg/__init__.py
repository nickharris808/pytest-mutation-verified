"""A tiny module used by the plugin's own tests and by the README example."""


def check_bounds(offset: int, length: int, capacity: int) -> bool:
    """True when a read of `length` at `offset` fits inside `capacity`."""
    return offset >= 0 and length >= 0 and offset + length <= capacity


def read(buf: bytes, offset: int, length: int):
    """Bounds-checked read. Returns None when the read would escape the buffer."""
    if not check_bounds(offset, length, len(buf)):
        return None
    return buf[offset : offset + length]
