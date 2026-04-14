"""1 ファイルにつき写真メタデータを保持する。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PIL import Image, UnidentifiedImageError
from PIL.ExifTags import IFD

_EXIF_DATETIME_ORIGINAL = 36867  # DateTimeOriginal
_EXIF_DATETIME = 306  # DateTime
_EXIF_MODEL = 272  # Model


class NotImageFileError(ValueError):
    """パスが指すファイルを画像として解釈できない場合に送出する。"""


def _parse_exif_datetime(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(value.strip(), fmt)
        except ValueError:
            continue
    return None


def _decode_exif_str(value: object) -> str | None:
    if isinstance(value, str):
        text = value.strip().strip("\x00")
        return text or None
    if isinstance(value, bytes):
        text = value.decode("utf-8", errors="replace").strip().strip("\x00")
        return text or None
    return None


def _read_exif_datetime_and_model(img: Image.Image) -> tuple[datetime | None, str | None]:
    taken: datetime | None = None
    model: str | None = None
    exif = img.getexif()
    if not exif:
        return taken, model

    exif_ifd: dict[int, object] = {}
    try:
        exif_ifd = exif.get_ifd(IFD.Exif)
    except (KeyError, ValueError, TypeError):
        exif_ifd = {}

    dt_raw = exif.get(_EXIF_DATETIME_ORIGINAL) or exif_ifd.get(_EXIF_DATETIME_ORIGINAL)
    if dt_raw is None:
        dt_raw = exif.get(_EXIF_DATETIME) or exif_ifd.get(_EXIF_DATETIME)
    taken = _parse_exif_datetime(dt_raw)

    model_raw = exif.get(_EXIF_MODEL) or exif_ifd.get(_EXIF_MODEL)
    model = _decode_exif_str(model_raw)
    return taken, model


class PhotoFileAttributes:
    """1 インスタンスが 1 つの画像ファイルの属性を表す。"""

    def __init__(self, path: str | Path) -> None:
        self._original_path = Path(path).expanduser().resolve()
        if not self._original_path.is_file():
            raise FileNotFoundError(f"ファイルが存在しません: {self._original_path}")

        try:
            with Image.open(self._original_path) as img:
                img.load()
                taken_at, camera_model = _read_exif_datetime_and_model(img)
        except UnidentifiedImageError as exc:
            raise NotImageFileError(
                f"画像ファイルとして認識できません: {self._original_path}"
            ) from exc
        except PermissionError:
            raise
        except OSError as exc:
            raise NotImageFileError(
                f"画像ファイルとして認識できません: {self._original_path}"
            ) from exc

        self._taken_at = taken_at
        self._camera_model = camera_model
        self._file_size = self._original_path.stat().st_size

    @property
    def original_path(self) -> Path:
        """オリジナルファイルパス（絶対パスに正規化）。"""
        return self._original_path

    @property
    def filename(self) -> str:
        """ファイル名。"""
        return self._original_path.name

    @property
    def taken_at(self) -> datetime | None:
        """撮影日時（EXIF が無い・解釈できない場合は None）。"""
        return self._taken_at

    @property
    def file_size(self) -> int:
        """ファイルサイズ（バイト）。"""
        return self._file_size

    @property
    def camera_model(self) -> str | None:
        """撮影したカメラのモデル名（EXIF が無い場合は None）。"""
        return self._camera_model
