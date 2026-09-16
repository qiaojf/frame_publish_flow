import struct
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO


@dataclass(frozen=True, slots=True)
class ImageDimensions:
    width: int
    height: int


JPEG_SOF_MARKERS = {
    0xC0,
    0xC1,
    0xC2,
    0xC3,
    0xC5,
    0xC6,
    0xC7,
    0xC9,
    0xCA,
    0xCB,
    0xCD,
    0xCE,
    0xCF,
}


def _jpeg_dimensions(stream: BinaryIO) -> ImageDimensions:
    if stream.read(2) != b"\xff\xd8":
        raise ValueError("invalid JPEG signature")
    while True:
        byte = stream.read(1)
        while byte and byte != b"\xff":
            byte = stream.read(1)
        if not byte:
            break
        marker = stream.read(1)
        while marker == b"\xff":
            marker = stream.read(1)
        if not marker:
            break
        marker_value = marker[0]
        if marker_value in {0x01, 0xD8, 0xD9} or 0xD0 <= marker_value <= 0xD7:
            continue
        length_bytes = stream.read(2)
        if len(length_bytes) != 2:
            break
        segment_length = struct.unpack(">H", length_bytes)[0]
        if segment_length < 2:
            break
        if marker_value in JPEG_SOF_MARKERS:
            data = stream.read(5)
            if len(data) != 5:
                break
            height, width = struct.unpack(">HH", data[1:])
            if width > 0 and height > 0:
                return ImageDimensions(width=width, height=height)
            break
        stream.seek(segment_length - 2, 1)
    raise ValueError("JPEG dimensions not found")


def _webp_dimensions(stream: BinaryIO) -> ImageDimensions:
    if stream.read(4) != b"RIFF":
        raise ValueError("invalid WebP signature")
    stream.seek(4, 1)
    if stream.read(4) != b"WEBP":
        raise ValueError("invalid WebP signature")
    while True:
        chunk_type = stream.read(4)
        chunk_size_raw = stream.read(4)
        if len(chunk_type) != 4 or len(chunk_size_raw) != 4:
            break
        chunk_size = struct.unpack("<I", chunk_size_raw)[0]
        data = stream.read(min(chunk_size, 32))
        if chunk_type == b"VP8X" and len(data) >= 10:
            width = int.from_bytes(data[4:7], "little") + 1
            height = int.from_bytes(data[7:10], "little") + 1
            return ImageDimensions(width=width, height=height)
        if chunk_type == b"VP8 " and len(data) >= 10 and data[3:6] == b"\x9d\x01\x2a":
            width = struct.unpack("<H", data[6:8])[0] & 0x3FFF
            height = struct.unpack("<H", data[8:10])[0] & 0x3FFF
            return ImageDimensions(width=width, height=height)
        if chunk_type == b"VP8L" and len(data) >= 5 and data[0] == 0x2F:
            bits = int.from_bytes(data[1:5], "little")
            width = (bits & 0x3FFF) + 1
            height = ((bits >> 14) & 0x3FFF) + 1
            return ImageDimensions(width=width, height=height)
        unread = chunk_size - len(data)
        if unread > 0:
            stream.seek(unread, 1)
        if chunk_size % 2:
            stream.seek(1, 1)
    raise ValueError("WebP dimensions not found")


def read_image_dimensions(path: Path) -> ImageDimensions:
    """Read JPG/PNG/WebP dimensions without decoding the full image."""

    with path.open("rb") as stream:
        signature = stream.read(12)
        stream.seek(0)
        if signature.startswith(b"\x89PNG\r\n\x1a\n"):
            header = stream.read(24)
            if len(header) < 24 or header[12:16] != b"IHDR":
                raise ValueError("invalid PNG header")
            width, height = struct.unpack(">II", header[16:24])
            if width <= 0 or height <= 0:
                raise ValueError("invalid PNG dimensions")
            return ImageDimensions(width=width, height=height)
        if signature.startswith(b"\xff\xd8"):
            return _jpeg_dimensions(stream)
        if signature.startswith(b"RIFF") and signature[8:12] == b"WEBP":
            return _webp_dimensions(stream)
    raise ValueError("unsupported or invalid image")
