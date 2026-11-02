"""
Проверка документов на плагиат.

Модуль извлекает текст и изображения из документов (DOCX, PDF, TXT, MD,
ODT, RTF, DOC), сравнивает текстовое содержимое по шинглам и изображения
по перцептивным хешам (dHash + aHash).

Основные функции:
    check_plagiarism(file_path, candidates)      — сравнить файл с папкой/списком файлов;
    compare_documents(file_a, file_b)            — сравнить два документа;
    check_plagiarism_async(...)                  — асинхронная обёртка для aiogram;
    format_report(report)                        — человекочитаемый отчёт.

Пример:
    from tools.ap_tools import check_plagiarism, format_report

    report = check_plagiarism(
        "files/documents/works students/ПИ-21/Иванов/Лабораторная 1.docx",
        "files/documents/works students/ПИ-21",
        threshold=0.6,
    )
    print(format_report(report))

Зависимости:
    PyMuPDF (pymupdf) — извлечение текста и картинок из PDF.
    Для DOCX/ODT/TXT/MD дополнительные библиотеки не нужны.
    Для старых .doc/.rtf используется системная утилита textutil (macOS);
    на других ОС такие файлы лучше заранее сохранить в DOCX/PDF.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import html
import json
import logging
import re
import shutil
import subprocess
import unicodedata
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Iterator, Sequence

try:  # PyMuPDF 1.24+ устанавливается как пакет pymupdf, fitz — старый алиас
    import pymupdf as fitz
except ImportError:  # pragma: no cover - зависит от окружения
    try:
        import fitz  # type: ignore[no-redef]
    except ImportError:  # pragma: no cover
        fitz = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Настройки и константы
# ---------------------------------------------------------------------------

SUPPORTED_EXTENSIONS = {
    ".docx",
    ".docm",
    ".pdf",
    ".txt",
    ".md",
    ".markdown",
    ".odt",
    ".rtf",
    ".doc",
}

TEXT_EXTENSIONS = {".txt", ".md", ".markdown"}
SHINGLE_SIZE = 5                 # количество слов в одном шингле
MIN_TEXT_CHARS = 80              # меньше — считаем, что текста нет
MIN_IMAGE_SIDE = 64              # картинки меньше 64x64 (иконки) не сравниваем
MIN_IMAGE_BYTES = 4096           # слишком маленькие файлы — обычно логотипы
MAX_IMAGES_PER_DOC = 64
MAX_WORDS_FOR_SHINGLES = 250_000
MAX_CHARS_FOR_FRAGMENTS = 100_000
MAX_FRAGMENTS = 5
MIN_FRAGMENT_CHARS = 60
DEFAULT_THRESHOLD = 0.6
DEFAULT_IMAGE_THRESHOLD = 0.88
IMAGE_BONUS_WEIGHT = 0.15         # максимум, который добавляют совпавшие скриншоты

WORD_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
ODT_TEXT_NS = "{urn:oasis:names:tc:opendocument:xmlns:text:1.0}"
ODT_IMAGE_PREFIX = "Pictures/"

_WS_RE = re.compile(r"\s+")
_RTF_SPECIAL_RE = re.compile(r"\\[a-zA-Z]+-?\d* ?")
_RTF_HEX_RE = re.compile(r"\\'([0-9a-fA-F]{2})")


# ---------------------------------------------------------------------------
# Модели результата
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ImageFingerprint:
    """Перцептивный отпечаток изображения."""

    index: int
    name: str
    width: int
    height: int
    dhash: int
    ahash: int

    @property
    def size(self) -> tuple[int, int]:
        return self.width, self.height


@dataclass(frozen=True)
class ImageMatch:
    """Совпадение изображения из проверяемого документа с изображением кандидата."""

    source: ImageFingerprint
    target: ImageFingerprint
    similarity: float

    @property
    def distance(self) -> int:
        """Суммарное расстояние Хэмминга (0..128)."""
        return _hamming(self.source.dhash, self.target.dhash) + _hamming(
            self.source.ahash, self.target.ahash
        )


@dataclass(frozen=True)
class MatchedFragment:
    """Совпавший фрагмент текста."""

    source_preview: str
    target_preview: str
    chars: int
    similarity: float = 1.0


@dataclass(frozen=True)
class DocumentProfile:
    """Извлечённое содержимое документа."""

    path: Path
    text: str
    normalized: str
    shingles: frozenset[bytes]
    images: tuple[ImageFingerprint, ...]
    warnings: tuple[str, ...] = ()

    @property
    def word_count(self) -> int:
        return len(self.normalized.split()) if self.normalized else 0

    @property
    def char_count(self) -> int:
        return len(self.normalized)

    @property
    def has_text(self) -> bool:
        return self.char_count >= MIN_TEXT_CHARS

    @property
    def has_images(self) -> bool:
        return bool(self.images)


@dataclass
class DocumentComparison:
    """Результат сравнения двух документов."""

    source: Path
    target: Path
    text_similarity: float
    jaccard: float
    containment: float
    dice: float
    image_similarity: float
    duplicate_image_ratio: float
    overall_similarity: float
    exact_text_match: bool
    image_matches: list[ImageMatch] = field(default_factory=list)
    fragments: list[MatchedFragment] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def similarity_percent(self) -> float:
        return round(self.overall_similarity * 100, 1)

    @property
    def has_image_duplicates(self) -> bool:
        return bool(self.image_matches)

    def to_dict(self) -> dict:
        return {
            "source": str(self.source),
            "target": str(self.target),
            "text_similarity": round(self.text_similarity, 4),
            "jaccard": round(self.jaccard, 4),
            "containment": round(self.containment, 4),
            "dice": round(self.dice, 4),
            "image_similarity": round(self.image_similarity, 4),
            "duplicate_image_ratio": round(self.duplicate_image_ratio, 4),
            "overall_similarity": round(self.overall_similarity, 4),
            "exact_text_match": self.exact_text_match,
            "image_matches": [
                {
                    "source_image": match.source.name,
                    "source_size": list(match.source.size),
                    "target_image": match.target.name,
                    "target_size": list(match.target.size),
                    "similarity": round(match.similarity, 4),
                }
                for match in self.image_matches
            ],
            "fragments": [
                {
                    "source_preview": fragment.source_preview,
                    "target_preview": fragment.target_preview,
                    "chars": fragment.chars,
                    "similarity": round(fragment.similarity, 4),
                }
                for fragment in self.fragments
            ],
            "warnings": list(self.warnings),
        }


@dataclass
class PlagiarismReport:
    """Итоговый отчёт по проверке одного документа."""

    source: Path
    candidates_checked: int
    threshold: float
    image_threshold: float
    comparisons: list[DocumentComparison] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def best_match(self) -> DocumentComparison | None:
        return self.comparisons[0] if self.comparisons else None

    @property
    def overall_similarity(self) -> float:
        best = self.best_match
        return best.overall_similarity if best else 0.0

    @property
    def is_plagiarized(self) -> bool:
        best = self.best_match
        if not best:
            return False
        return best.exact_text_match or best.overall_similarity >= self.threshold

    @property
    def verdict(self) -> str:
        best = self.best_match
        if not best:
            return "нет документов для сравнения"
        if best.exact_text_match:
            return "полное совпадение"
        if best.overall_similarity >= 0.85:
            return "очень высокая схожесть"
        if best.overall_similarity >= self.threshold:
            return "высокая схожесть"
        if best.overall_similarity >= self.threshold * 0.6:
            return "частичное совпадение"
        return "уникально"

    def to_dict(self) -> dict:
        return {
            "source": str(self.source),
            "candidates_checked": self.candidates_checked,
            "threshold": self.threshold,
            "image_threshold": self.image_threshold,
            "overall_similarity": round(self.overall_similarity, 4),
            "is_plagiarized": self.is_plagiarized,
            "verdict": self.verdict,
            "best_match": self.best_match.to_dict() if self.best_match else None,
            "comparisons": [comparison.to_dict() for comparison in self.comparisons],
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }


# ---------------------------------------------------------------------------
# Извлечение текста и изображений
# ---------------------------------------------------------------------------


def _read_text_file(path: Path) -> str:
    """Читает текстовый файл, подбирая кодировку."""
    for encoding in ("utf-8-sig", "utf-8", "cp1251", "koi8-r", "latin-1"):
        try:
            return path.read_text(encoding=encoding)
        except (UnicodeDecodeError, UnicodeError):
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def _paragraph_text(paragraph: ET.Element) -> str:
    """Собирает текст абзаца, не дублируя текст вложенных абзацев (текстовые блоки)."""
    chunks: list[str] = []

    def walk(node: ET.Element) -> None:
        for child in node:
            tag = child.tag
            if tag == WORD_NS + "p":
                continue  # вложенный абзац будет обработан отдельно
            if tag == WORD_NS + "t":
                chunks.append(child.text or "")
            elif tag == WORD_NS + "tab":
                chunks.append("\t")
            elif tag in (WORD_NS + "br", WORD_NS + "cr"):
                chunks.append("\n")
            else:
                walk(child)

    walk(paragraph)
    return "".join(chunks).strip()


def _extract_docx(path: Path) -> tuple[str, list[tuple[str, bytes]], list[str]]:
    """Возвращает (текст, [(имя, байты изображения)], предупреждения)."""
    warnings: list[str] = []
    text_parts: list[str] = []
    images: list[tuple[str, bytes]] = []

    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())

        # document.xml + колонтитулы + сноски
        xml_parts = ["word/document.xml"]
        xml_parts += sorted(
            name
            for name in names
            if re.fullmatch(r"word/(header|footer)\d*\.xml", name)
        )
        xml_parts += [
            name
            for name in ("word/footnotes.xml", "word/endnotes.xml")
            if name in names
        ]

        for part in xml_parts:
            if part not in names:
                continue
            try:
                root = ET.fromstring(archive.read(part))
            except ET.ParseError as exc:
                warnings.append(f"{part}: не удалось разобрать XML ({exc})")
                continue
            for paragraph in root.iter(WORD_NS + "p"):
                line = _paragraph_text(paragraph)
                if line:
                    text_parts.append(line)

        for name in sorted(names):
            if name.startswith("word/media/") and not name.endswith("/"):
                try:
                    images.append((name, archive.read(name)))
                except (KeyError, OSError) as exc:
                    warnings.append(f"{name}: не удалось прочитать изображение ({exc})")

    return "\n".join(text_parts), images, warnings


def _extract_odt(path: Path) -> tuple[str, list[tuple[str, bytes]], list[str]]:
    warnings: list[str] = []
    text_parts: list[str] = []
    images: list[tuple[str, bytes]] = []

    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        if "content.xml" not in names:
            return "", [], ["ODT: отсутствует content.xml"]
        try:
            root = ET.fromstring(archive.read("content.xml"))
        except ET.ParseError as exc:
            return "", [], [f"ODT: не удалось разобрать content.xml ({exc})"]

        for paragraph in root.iter(ODT_TEXT_NS + "p"):
            line = "".join(paragraph.itertext()).strip()
            if line:
                text_parts.append(line)

        for name in sorted(names):
            if name.startswith(ODT_IMAGE_PREFIX) and not name.endswith("/"):
                try:
                    images.append((name, archive.read(name)))
                except (KeyError, OSError) as exc:
                    warnings.append(f"{name}: не удалось прочитать изображение ({exc})")

    return "\n".join(text_parts), images, warnings


def _extract_pdf(path: Path) -> tuple[str, list[tuple[str, bytes]], list[str]]:
    if fitz is None:
        return (
            "",
            [],
            [
                "PyMuPDF не установлен: PDF не будет прочитан. "
                "Установите зависимость командой pip install PyMuPDF."
            ],
        )

    warnings: list[str] = []
    text_parts: list[str] = []
    images: list[tuple[str, bytes]] = []
    document = None

    try:
        document = fitz.open(path)
        if document.needs_pass:
            return "", [], ["PDF защищён паролем — содержимое не извлечено."]

        seen_xrefs: set[int] = set()
        for page_number, page in enumerate(document, start=1):
            try:
                page_text = page.get_text("text")
                if page_text:
                    text_parts.append(page_text)
            except Exception as exc:  # pragma: no cover - зависит от файла
                warnings.append(f"PDF, стр. {page_number}: ошибка текста ({exc})")

            try:
                for image_info in page.get_images(full=True):
                    xref = image_info[0]
                    if xref in seen_xrefs:
                        continue
                    seen_xrefs.add(xref)
                    try:
                        extracted = document.extract_image(xref)
                    except Exception as exc:  # pragma: no cover
                        warnings.append(f"PDF, изображение {xref}: ошибка ({exc})")
                        continue
                    if extracted and extracted.get("image"):
                        images.append(
                            (
                                f"pdf_xref_{xref}.{extracted.get('ext', 'bin')}",
                                extracted["image"],
                            )
                        )
            except Exception as exc:  # pragma: no cover
                warnings.append(f"PDF, стр. {page_number}: ошибка изображений ({exc})")
    except Exception as exc:
        return "", [], [f"Не удалось открыть PDF: {exc}"]
    finally:
        if document is not None:
            try:
                document.close()
            except Exception:  # pragma: no cover
                pass

    text = "\n".join(text_parts)
    if len(re.sub(r"\s+", "", text)) < MIN_TEXT_CHARS:
        warnings.append(
            "PDF не содержит текстового слоя (похоже на скан). "
            "Для сравнения текста нужен OCR; изображения при этом всё равно сравниваются."
        )
    return text, images, warnings


def _extract_via_textutil(path: Path) -> tuple[str, list[str]]:
    """Извлекает текст через macOS-утилиту textutil (.doc, .rtf и др.)."""
    executable = shutil.which("textutil")
    if not executable:
        return "", [
            f"Формат {path.suffix} не поддерживается без утилиты textutil. "
            "Сохраните документ как DOCX или PDF."
        ]
    try:
        result = subprocess.run(
            [executable, "-convert", "txt", "-stdout", str(path)],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return "", [f"textutil: не удалось прочитать {path.name} ({exc})"]

    if result.returncode != 0:
        detail = (result.stderr or "").strip()
        return "", [f"textutil: ошибка чтения {path.name}" + (f": {detail}" if detail else "")]
    return result.stdout, []


def _extract_rtf_fallback(path: Path) -> str:
    """Очень простой запасной вариант для RTF без textutil."""
    raw = path.read_bytes().decode("cp1251", errors="replace")
    raw = _RTF_HEX_RE.sub(lambda match: chr(int(match.group(1), 16)), raw)
    raw = _RTF_SPECIAL_RE.sub(" ", raw)
    raw = raw.replace("\\{", "{").replace("\\}", "}").replace("\\\\", "\\")
    raw = raw.replace("{", " ").replace("}", " ")
    return raw


def _extract_raw(path: Path) -> tuple[str, list[tuple[str, bytes]], list[str]]:
    """Определяет формат и извлекает текст/изображения."""
    suffix = path.suffix.lower()

    if suffix in {".docx", ".docm"}:
        return _extract_docx(path)
    if suffix == ".odt":
        return _extract_odt(path)
    if suffix == ".pdf":
        return _extract_pdf(path)
    if suffix in TEXT_EXTENSIONS:
        return _read_text_file(path), [], []
    if suffix in {".doc", ".rtf"}:
        text, warnings = _extract_via_textutil(path)
        if text:
            return text, [], warnings
        if suffix == ".rtf" and not warnings:
            return _extract_rtf_fallback(path), [], warnings
        return "", [], warnings

    return "", [], [f"Формат {suffix or '<без расширения>'} не поддерживается."]


# ---------------------------------------------------------------------------
# Перцептивные хеши изображений
# ---------------------------------------------------------------------------


def _hamming(first: int, second: int) -> int:
    return (first ^ second).bit_count()


def _pixmap_to_gray(pixmap) -> object | None:
    """Приводит pixmap к оттенкам серого без альфа-канала."""
    try:
        if pixmap.alpha:
            pixmap = fitz.Pixmap(pixmap, 0)
        if pixmap.colorspace != fitz.csGRAY:
            pixmap = fitz.Pixmap(fitz.csGRAY, pixmap)
        return pixmap
    except Exception as exc:  # pragma: no cover - зависит от формата картинки
        logger.debug("Не удалось преобразовать изображение в grayscale: %s", exc)
        return None


def _resize_gray(pixmap, target_width: int, target_height: int) -> list[float]:
    """Уменьшает grayscale-изображение до target_width x target_height (box average)."""
    source_width = pixmap.width
    source_height = pixmap.height
    samples = pixmap.samples
    stride = pixmap.stride

    if source_width == target_width and source_height == target_height:
        return [
            float(samples[y * stride + x])
            for y in range(target_height)
            for x in range(target_width)
        ]

    result: list[float] = []
    for target_y in range(target_height):
        y0 = target_y * source_height // target_height
        y1 = max(y0 + 1, (target_y + 1) * source_height // target_height)
        for target_x in range(target_width):
            x0 = target_x * source_width // target_width
            x1 = max(x0 + 1, (target_x + 1) * source_width // target_width)
            total = 0
            count = 0
            for y in range(y0, y1):
                row_offset = y * stride
                for x in range(x0, x1):
                    total += samples[row_offset + x]
                    count += 1
            result.append(total / count if count else 0.0)
    return result


def _dhash(pixels: Sequence[float], width: int = 9, height: int = 8) -> int:
    """Разностный хеш: сравнивает соседние пиксели по горизонтали."""
    value = 0
    for y in range(height):
        row = y * width
        for x in range(width - 1):
            value = (value << 1) | int(pixels[row + x] > pixels[row + x + 1])
    return value


def _ahash(pixels: Sequence[float], width: int = 8, height: int = 8) -> int:
    """Средний хеш: сравнивает пиксели со средним значением."""
    average = sum(pixels) / len(pixels) if pixels else 0.0
    value = 0
    for pixel in pixels:
        value = (value << 1) | int(pixel > average)
    return value


def _fingerprint_image(
    data: bytes,
    index: int,
    name: str,
    min_side: int = MIN_IMAGE_SIDE,
    min_bytes: int = MIN_IMAGE_BYTES,
) -> ImageFingerprint | None:
    """Считает dHash/aHash изображения. Возвращает None для иконок и мусора."""
    if fitz is None or len(data) < min_bytes:
        return None

    try:
        pixmap = fitz.Pixmap(data)
    except Exception as exc:  # pragma: no cover - зависит от формата
        logger.debug("Не удалось открыть изображение %s: %s", name, exc)
        return None

    width, height = pixmap.width, pixmap.height
    if width < min_side or height < min_side:
        return None

    aspect = width / height if height else 0
    if aspect > 10 or aspect < 0.1:  # длинные полоски/разделители
        return None

    pixmap = _pixmap_to_gray(pixmap)
    if pixmap is None:
        return None

    # shrink() ускоряет обработку больших скриншотов: аргумент — степень двойки.
    # Уменьшаем не более чем до ~9x8, точный размер добиваем ручным усреднением.
    try:
        factor = 0
        while factor < 4:
            next_width = pixmap.width // (2 ** (factor + 1))
            next_height = pixmap.height // (2 ** (factor + 1))
            if next_width < 9 or next_height < 8:
                break
            factor += 1
        if factor:
            pixmap.shrink(factor)
    except Exception:  # pragma: no cover
        pass

    pixels = _resize_gray(pixmap, 9, 8)
    pixels_for_average = _resize_gray(pixmap, 8, 8)

    # Однотонные картинки (белый фон, черные плашки) не несут информации
    # и иначе совпадали бы друг с другом.
    if max(pixels) - min(pixels) < 8:
        return None

    return ImageFingerprint(
        index=index,
        name=name,
        width=width,
        height=height,
        dhash=_dhash(pixels),
        ahash=_ahash(pixels_for_average),
    )


def _image_similarity(first: ImageFingerprint, second: ImageFingerprint) -> float:
    """Схожесть двух изображений по dHash и aHash (0..1)."""
    # Отсекаем совсем разные пропорции: иконка не должна совпасть со скриншотом.
    width_ratio = max(first.width, second.width) / max(1, min(first.width, second.width))
    height_ratio = max(first.height, second.height) / max(1, min(first.height, second.height))
    if width_ratio > 2.5 or height_ratio > 2.5:
        return 0.0

    dhash_distance = _hamming(first.dhash, second.dhash)
    ahash_distance = _hamming(first.ahash, second.ahash)
    weighted_distance = dhash_distance * 0.7 + ahash_distance * 0.3
    return max(0.0, 1.0 - weighted_distance / 64.0)


# ---------------------------------------------------------------------------
# Текстовая схожесть
# ---------------------------------------------------------------------------


def normalize_text(text: str) -> str:
    """Нормализует текст: регистр, ё→е, пунктуация, лишние пробелы."""
    text = unicodedata.normalize("NFKC", text)
    text = text.lower().replace("ё", "е")
    text = re.sub(r"[^\w]+", " ", text, flags=re.UNICODE)
    return _WS_RE.sub(" ", text).strip()


def _make_shingles(words: Sequence[str], size: int = SHINGLE_SIZE) -> frozenset[bytes]:
    """Строит множество хешей словесных n-грамм."""
    if not words:
        return frozenset()
    if len(words) < size:
        words = tuple(words)
        digest = hashlib.blake2b(" ".join(words).encode("utf-8"), digest_size=8).digest()
        return frozenset({digest})

    shingles: set[bytes] = set()
    for index in range(len(words) - size + 1):
        chunk = " ".join(words[index : index + size]).encode("utf-8")
        shingles.add(hashlib.blake2b(chunk, digest_size=8).digest())
    return frozenset(shingles)


def _set_metrics(first: frozenset[bytes], second: frozenset[bytes]) -> tuple[float, float, float]:
    """Возвращает (jaccard, containment, dice) для двух множеств шинглов."""
    if not first or not second:
        return 0.0, 0.0, 0.0
    intersection = len(first & second)
    union = len(first | second)
    jaccard = intersection / union if union else 0.0
    containment = intersection / min(len(first), len(second))
    dice = 2 * intersection / (len(first) + len(second))
    return jaccard, containment, dice


def _text_similarity(
    first: DocumentProfile,
    second: DocumentProfile,
) -> tuple[float, float, float, float, bool]:
    """
    Возвращает (итоговая схожесть, jaccard, containment, dice, точное совпадение).

    Итоговая схожесть — смесь Dice и containment: Dice хорошо работает для
    документов одинакового размера, containment — когда скопирован фрагмент
    большого документа.
    """
    exact = bool(first.normalized) and first.normalized == second.normalized
    jaccard, containment, dice = _set_metrics(first.shingles, second.shingles)

    if exact:
        return 1.0, 1.0, 1.0, 1.0, True

    # Быстрая проверка полного вхождения (например, текст без титульного листа).
    if (
        first.normalized
        and second.normalized
        and min(len(first.normalized), len(second.normalized)) >= MIN_TEXT_CHARS
        and (
            first.normalized in second.normalized
            or second.normalized in first.normalized
        )
    ):
        containment = 1.0

    score = 0.7 * dice + 0.3 * containment
    return score, jaccard, containment, dice, False


def _clean_preview(text: str, limit: int = 240) -> str:
    preview = _WS_RE.sub(" ", text).strip()
    if len(preview) > limit:
        preview = preview[: limit - 1].rstrip() + "…"
    return preview


def _find_fragments(
    first: DocumentProfile,
    second: DocumentProfile,
    limit: int = MAX_FRAGMENTS,
) -> list[MatchedFragment]:
    """Ищет самые длинные совпавшие фрагменты через difflib."""
    if not first.normalized or not second.normalized:
        return []

    first_text = first.normalized[:MAX_CHARS_FOR_FRAGMENTS]
    second_text = second.normalized[:MAX_CHARS_FOR_FRAGMENTS]

    try:
        # autojunk=True защищает от квадратичной деградации на документах
        # с большим количеством повторов (например, таблицах из одинаковых слов).
        matcher = SequenceMatcher(None, first_text, second_text, autojunk=True)
        blocks = [
            block
            for block in matcher.get_matching_blocks()
            if block.size >= MIN_FRAGMENT_CHARS
        ]
    except Exception as exc:  # pragma: no cover - защита от экзотических случаев
        logger.debug("SequenceMatcher не смог найти фрагменты: %s", exc)
        return []

    blocks.sort(key=lambda block: block.size, reverse=True)
    fragments: list[MatchedFragment] = []
    for block in blocks[:limit]:
        source_fragment = first_text[block.a : block.a + block.size]
        target_fragment = second_text[block.b : block.b + block.size]
        fragments.append(
            MatchedFragment(
                source_preview=_clean_preview(source_fragment),
                target_preview=_clean_preview(target_fragment),
                chars=block.size,
            )
        )
    return fragments


# ---------------------------------------------------------------------------
# Профили документов
# ---------------------------------------------------------------------------


@lru_cache(maxsize=128)
def _cached_profile(path_string: str, modified_ns: int, size: int) -> DocumentProfile:
    """Кэширует профиль по пути, mtime и размеру (mtime/size — часть ключа)."""
    path = Path(path_string)
    text, raw_images, warnings = _extract_raw(path)
    normalized = normalize_text(text)
    words = normalized.split()

    if len(words) > MAX_WORDS_FOR_SHINGLES:
        warnings.append(
            f"Документ очень большой: для сравнения взяты первые "
            f"{MAX_WORDS_FOR_SHINGLES} слов."
        )
        words = words[:MAX_WORDS_FOR_SHINGLES]

    if len(normalized) < MIN_TEXT_CHARS:
        warnings.append(
            "Текст не извлечён или слишком короткий — сравнение идёт в основном по изображениям."
        )

    images: list[ImageFingerprint] = []
    seen_hashes: set[tuple[int, int]] = set()
    for index, (name, data) in enumerate(raw_images):
        if len(images) >= MAX_IMAGES_PER_DOC:
            warnings.append(
                f"Изображений больше {MAX_IMAGES_PER_DOC}: лишние пропущены."
            )
            break
        fingerprint = _fingerprint_image(data, index=index, name=name)
        if fingerprint is None:
            continue
        key = (fingerprint.dhash, fingerprint.ahash)
        if key in seen_hashes:
            continue
        seen_hashes.add(key)
        images.append(fingerprint)

    return DocumentProfile(
        path=path,
        text=text,
        normalized=normalized,
        shingles=_make_shingles(words),
        images=tuple(images),
        warnings=tuple(warnings),
    )


def load_document(path: str | Path, use_cache: bool = True) -> DocumentProfile:
    """
    Извлекает текст и изображения документа.

    Args:
        path: Путь к файлу.
        use_cache: Использовать кэш (по умолчанию True). Кэш автоматически
            учитывает дату изменения и размер файла.

    Raises:
        FileNotFoundError: Если файл не существует.
    """
    file_path = Path(path).expanduser().resolve()
    if not file_path.is_file():
        raise FileNotFoundError(f"Файл не найден: {file_path}")

    stat = file_path.stat()
    if not use_cache:
        return _cached_profile.__wrapped__(str(file_path), stat.st_mtime_ns, stat.st_size)
    return _cached_profile(str(file_path), stat.st_mtime_ns, stat.st_size)


def _best_image_matches(
    source_images: Sequence[ImageFingerprint],
    target_images: Sequence[ImageFingerprint],
    threshold: float,
) -> list[ImageMatch]:
    """Для каждой картинки источника ищет самую похожую картинку кандидата."""
    matches: list[ImageMatch] = []
    for source in source_images:
        best_target: ImageFingerprint | None = None
        best_similarity = 0.0
        for target in target_images:
            similarity = _image_similarity(source, target)
            if similarity > best_similarity:
                best_similarity = similarity
                best_target = target
        if best_target is not None and best_similarity >= threshold:
            matches.append(
                ImageMatch(
                    source=source,
                    target=best_target,
                    similarity=best_similarity,
                )
            )
    return matches


# ---------------------------------------------------------------------------
# Публичное API
# ---------------------------------------------------------------------------


def _compare_profiles(
    first: DocumentProfile,
    second: DocumentProfile,
    *,
    image_threshold: float,
    find_fragments: bool,
) -> DocumentComparison:
    """Сравнивает два уже извлечённых профиля документов."""
    if first.path == second.path:
        return DocumentComparison(
            source=first.path,
            target=second.path,
            text_similarity=1.0 if first.normalized else 0.0,
            jaccard=1.0 if first.shingles else 0.0,
            containment=1.0 if first.shingles else 0.0,
            dice=1.0 if first.shingles else 0.0,
            image_similarity=1.0 if first.images else 0.0,
            duplicate_image_ratio=1.0 if first.images else 0.0,
            overall_similarity=1.0 if (first.normalized or first.images) else 0.0,
            exact_text_match=bool(first.normalized),
            image_matches=[
                ImageMatch(source=image, target=image, similarity=1.0)
                for image in first.images
            ],
            warnings=["Файл сравнивается сам с собой."],
        )

    text_score, jaccard, containment, dice, exact = _text_similarity(first, second)
    image_matches = _best_image_matches(first.images, second.images, image_threshold)
    image_similarity = max((match.similarity for match in image_matches), default=0.0)

    total_images = len(first.images) + len(second.images)
    duplicate_image_ratio = (
        2 * len(image_matches) / total_images if total_images else 0.0
    )

    both_have_text = first.has_text and second.has_text
    both_have_images = first.has_images and second.has_images

    if exact:
        overall = 1.0
    elif both_have_text:
        overall = text_score
        # Совпавшие скриншоты усиливают подозрение, но не заменяют текстовое сравнение.
        if both_have_images:
            overall = text_score + IMAGE_BONUS_WEIGHT * duplicate_image_ratio * (
                1.0 - text_score
            )
    elif both_have_images:
        overall = duplicate_image_ratio
    else:
        overall = max(text_score, duplicate_image_ratio)

    fragments = _find_fragments(first, second) if find_fragments else []

    warnings = list(first.warnings) + [
        f"{second.path.name}: {warning}" for warning in second.warnings
    ]

    return DocumentComparison(
        source=first.path,
        target=second.path,
        text_similarity=text_score,
        jaccard=jaccard,
        containment=containment,
        dice=dice,
        image_similarity=image_similarity,
        duplicate_image_ratio=duplicate_image_ratio,
        overall_similarity=max(0.0, min(1.0, overall)),
        exact_text_match=exact,
        image_matches=image_matches,
        fragments=fragments,
        warnings=warnings,
    )


def compare_documents(
    file_a: str | Path,
    file_b: str | Path,
    *,
    image_threshold: float = DEFAULT_IMAGE_THRESHOLD,
    find_fragments: bool = True,
    use_cache: bool = True,
) -> DocumentComparison:
    """Сравнивает два документа и возвращает подробный результат."""
    first = load_document(file_a, use_cache=use_cache)
    second = load_document(file_b, use_cache=use_cache)
    return _compare_profiles(
        first,
        second,
        image_threshold=image_threshold,
        find_fragments=find_fragments,
    )


def _iter_candidate_files(candidates: str | Path | Iterable[str | Path]) -> Iterator[Path]:
    """Разворачивает папки/списки/генераторы в набор поддерживаемых файлов."""
    if isinstance(candidates, (str, Path)):
        candidates = [candidates]

    seen: set[Path] = set()
    for candidate in candidates:
        path = Path(candidate).expanduser()
        if not path.exists():
            logger.warning("Кандидат не найден: %s", path)
            continue
        if path.is_dir():
            paths = sorted(
                item
                for item in path.rglob("*")
                if item.is_file() and item.suffix.lower() in SUPPORTED_EXTENSIONS
            )
        else:
            paths = [path]
        for item in paths:
            resolved = item.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            yield resolved


def check_plagiarism(
    file_path: str | Path,
    candidates: str | Path | Iterable[str | Path] | None,
    *,
    threshold: float = DEFAULT_THRESHOLD,
    image_threshold: float = DEFAULT_IMAGE_THRESHOLD,
    find_fragments: bool = True,
    use_cache: bool = True,
    exclude_self: bool = True,
) -> PlagiarismReport:
    """
    Проверяет документ на плагиат по базе других документов.

    Args:
        file_path: Проверяемый файл.
        candidates: Папка (рекурсивно), один файл или список/генератор путей.
        threshold: Порог общей схожести (0..1), начиная с которого работа
            считается подозрительной. По умолчанию 0.6.
        image_threshold: Порог схожести скриншотов (0..1). По умолчанию 0.88.
        find_fragments: Искать совпавшие фрагменты текста для отчёта.
        use_cache: Кэшировать извлечённые документы.
        exclude_self: Исключить сам проверяемый файл из кандидатов.

    Returns:
        PlagiarismReport: Отчёт со всеми сравнениями, отсортированными по убыванию
        схожести. Лучшее совпадение — report.best_match.

    Raises:
        FileNotFoundError: Если проверяемый файл не существует.
        ValueError: Если пороги вне диапазона 0..1.
    """
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold должен быть в диапазоне 0..1")
    if not 0.0 <= image_threshold <= 1.0:
        raise ValueError("image_threshold должен быть в диапазоне 0..1")

    source_path = Path(file_path).expanduser().resolve()
    if not source_path.is_file():
        raise FileNotFoundError(f"Файл не найден: {source_path}")

    source = load_document(source_path, use_cache=use_cache)
    report = PlagiarismReport(
        source=source_path,
        candidates_checked=0,
        threshold=threshold,
        image_threshold=image_threshold,
        warnings=list(source.warnings),
    )

    if candidates is None:
        return report

    comparisons: list[DocumentComparison] = []
    for candidate_path in _iter_candidate_files(candidates):
        if exclude_self and candidate_path == source_path:
            continue
        try:
            candidate = load_document(candidate_path, use_cache=use_cache)
        except Exception as exc:
            report.errors.append(f"{candidate_path}: {exc}")
            continue

        report.candidates_checked += 1
        try:
            comparison = _compare_profiles(
                source,
                candidate,
                image_threshold=image_threshold,
                find_fragments=find_fragments,
            )
        except Exception as exc:
            report.errors.append(f"{candidate_path}: {exc}")
            continue
        comparisons.append(comparison)
        logger.debug(
            "Сравнение %s ↔ %s: %.1f%%",
            source_path.name,
            candidate_path.name,
            comparison.overall_similarity * 100,
        )

    comparisons.sort(key=lambda item: item.overall_similarity, reverse=True)
    report.comparisons = comparisons
    return report


async def check_plagiarism_async(
    file_path: str | Path,
    candidates: str | Path | Iterable[str | Path] | None,
    **kwargs,
) -> PlagiarismReport:
    """
    Асинхронная обёртка для aiogram: не блокирует event loop.

    Все аргументы совпадают с check_plagiarism.
    """
    return await asyncio.to_thread(check_plagiarism, file_path, candidates, **kwargs)


def format_report(
    report: PlagiarismReport,
    *,
    max_length: int = 3500,
    html_safe: bool = False,
) -> str:
    """
    Формирует текст отчёта для отправки в Telegram.

    Args:
        report: Результат check_plagiarism.
        max_length: Максимальная длина сообщения (Telegram — 4096).
        html_safe: Экранировать HTML-спецсимволы (если parse_mode=HTML).

    Returns:
        str: Готовый текст.
    """
    escape = html.escape if html_safe else (lambda value: value)
    best = report.best_match

    lines: list[str] = [
        "Проверка на плагиат",
        f"Файл: {escape(report.source.name)}",
        f"Проверено документов: {report.candidates_checked}",
        f"Вердикт: {escape(report.verdict.upper())} "
        f"({report.overall_similarity * 100:.1f}%)",
    ]

    if best:
        lines += [
            "",
            f"Лучшее совпадение: {escape(best.target.name)}",
            f"  общая схожесть: {best.overall_similarity * 100:.1f}%",
            f"  текст: {best.text_similarity * 100:.1f}% "
            f"(совпадение шинглов {best.dice * 100:.1f}%, "
            f"вхождение {best.containment * 100:.1f}%)",
        ]
        if best.exact_text_match:
            lines.append("  текст совпадает полностью")
        if best.image_matches:
            lines.append(
                f"  скриншоты: {best.image_similarity * 100:.1f}%, "
                f"совпало изображений: {len(best.image_matches)}"
            )
        elif best.image_similarity > 0:
            lines.append(
                f"  скриншоты: максимальная схожесть "
                f"{best.image_similarity * 100:.1f}% (ниже порога)"
            )

        if best.fragments:
            lines.append("  совпавшие фрагменты:")
            for fragment in best.fragments[:3]:
                lines.append(f"    • {escape(fragment.source_preview)}")

    other_matches = [
        comparison
        for comparison in report.comparisons[1:]
        if comparison.overall_similarity >= report.threshold * 0.5
    ]
    if other_matches:
        lines += ["", "Другие похожие работы:"]
        for comparison in other_matches[:5]:
            lines.append(
                f"  • {escape(comparison.target.name)} — "
                f"{comparison.overall_similarity * 100:.1f}%"
            )

    notable_warnings = report.warnings + [
        warning
        for comparison in report.comparisons[:1]
        for warning in comparison.warnings
    ]
    if notable_warnings:
        unique_warnings = list(dict.fromkeys(notable_warnings))
        lines += ["", "Предупреждения:"]
        lines += [f"  • {escape(warning)}" for warning in unique_warnings[:4]]

    if report.errors:
        lines += ["", "Ошибки:"]
        lines += [f"  • {escape(error)}" for error in report.errors[:3]]

    text = "\n".join(lines)
    if len(text) > max_length:
        text = text[: max_length - 20].rstrip() + "\n... (обрезано)"
    return text


__all__ = [
    "DocumentComparison",
    "DocumentProfile",
    "ImageFingerprint",
    "ImageMatch",
    "MatchedFragment",
    "PlagiarismReport",
    "check_plagiarism",
    "check_plagiarism_async",
    "compare_documents",
    "format_report",
    "load_document",
    "normalize_text",
]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Проверка документа на плагиат по папке или списку файлов."
    )
    parser.add_argument("file", help="проверяемый документ")
    parser.add_argument(
        "candidates",
        nargs="*",
        help="файлы или папки для сравнения (по умолчанию — папка проверяемого файла)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_THRESHOLD,
        help=f"порог общей схожести (по умолчанию {DEFAULT_THRESHOLD})",
    )
    parser.add_argument(
        "--image-threshold",
        type=float,
        default=DEFAULT_IMAGE_THRESHOLD,
        help=f"порог схожести скриншотов (по умолчанию {DEFAULT_IMAGE_THRESHOLD})",
    )
    parser.add_argument(
        "--no-fragments",
        action="store_true",
        help="не искать совпавшие фрагменты (быстрее)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="вывести отчёт в JSON",
    )
    parser.add_argument(
        "--html",
        action="store_true",
        help="экранировать HTML в текстовом отчёте",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    candidates = args.candidates or [str(Path(args.file).expanduser().resolve().parent)]
    try:
        report = check_plagiarism(
            args.file,
            candidates,
            threshold=args.threshold,
            image_threshold=args.image_threshold,
            find_fragments=not args.no_fragments,
        )
    except (FileNotFoundError, ValueError) as exc:
        parser.error(str(exc))
        return 2

    if args.json:
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(format_report(report, html_safe=args.html))
    return 1 if report.is_plagiarized else 0


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    raise SystemExit(main())
