"""photo_file_attributes モジュールのテスト。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import piexif
import pytest
from PIL import Image

from photomanager.photo_file_attributes import (
    NotImageFileError,
    PhotoFileAttributes,
    _decode_exif_str,
    _parse_exif_datetime,
)


def test_missing_file_raises_file_not_found(tmp_path: Path) -> None:
    path = tmp_path / "nope.jpg"
    with pytest.raises(FileNotFoundError, match="ファイルが存在しません"):
        PhotoFileAttributes(path)


def test_non_image_raises_not_image_file_error(tmp_path: Path) -> None:
    path = tmp_path / "readme.txt"
    path.write_text("not an image", encoding="utf-8")
    with pytest.raises(NotImageFileError, match="画像ファイルとして認識できません"):
        PhotoFileAttributes(path)


def test_png_without_exif_reports_basic_fields(tmp_path: Path) -> None:
    path = tmp_path / "one.png"
    Image.new("RGB", (1, 1), color="red").save(path)

    attrs = PhotoFileAttributes(path)

    assert attrs.original_path == path.resolve()
    assert attrs.filename == "one.png"
    assert attrs.file_size == path.stat().st_size
    assert attrs.taken_at is None
    assert attrs.camera_model is None


def test_constructor_accepts_str_path(tmp_path: Path) -> None:
    path = tmp_path / "s.png"
    Image.new("RGB", (1, 1)).save(path)

    attrs = PhotoFileAttributes(str(path))

    assert attrs.original_path == path.resolve()


def test_jpeg_with_exif_reads_datetime_and_model(tmp_path: Path) -> None:
    path = tmp_path / "exif.jpg"
    img = Image.new("RGB", (4, 4), color="green")
    exif_dict = {
        "0th": {piexif.ImageIFD.Model: b"TestCam X1"},
        "Exif": {
            piexif.ExifIFD.DateTimeOriginal: b"2023:05:01 12:34:56",
        },
    }
    exif_bytes = piexif.dump(exif_dict)
    img.save(path, "JPEG", exif=exif_bytes, quality=95)

    attrs = PhotoFileAttributes(path)

    assert attrs.taken_at == datetime(2023, 5, 1, 12, 34, 56)
    assert attrs.camera_model == "TestCam X1"
    assert attrs.filename == "exif.jpg"
    assert attrs.file_size == path.stat().st_size


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("2023:01:15 08:30:00", datetime(2023, 1, 15, 8, 30, 0)),
        ("2023-01-15 08:30:00", datetime(2023, 1, 15, 8, 30, 0)),
        ("  2023:01:15 08:30:00  ", datetime(2023, 1, 15, 8, 30, 0)),
    ],
)
def test_parse_exif_datetime_valid(raw: str, expected: datetime) -> None:
    assert _parse_exif_datetime(raw) == expected


def test_parse_exif_datetime_invalid_returns_none() -> None:
    assert _parse_exif_datetime("not a date") is None
    assert _parse_exif_datetime(123) is None


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("  Alpha  ", "Alpha"),
        (b"BytesCam\x00", "BytesCam"),
        ("", None),
        (b"", None),
    ],
)
def test_decode_exif_str(raw: object, expected: str | None) -> None:
    assert _decode_exif_str(raw) == expected
