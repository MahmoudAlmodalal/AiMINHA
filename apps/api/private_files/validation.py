"""Small strict accepted-format subset, with bounded archive/image expansion."""

import io
import posixpath
import warnings
import zipfile
from pathlib import PurePath
from typing import Any
from xml.etree import ElementTree

from identity.security import IdentityError

MIMES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}
MAX_FILE_BYTES = 5_000_000
MAX_STUDENT_BYTES = 10_000_000
MAX_GLOBAL_BYTES = 750_000_000


def rejected() -> IdentityError:
    return IdentityError("FILE_TYPE_REJECTED", 422, "Unsupported or unsafe file content")


def envelope(name: str, mime: str, data: bytes) -> None:
    if not data or len(data) > MAX_FILE_BYTES:
        raise IdentityError("FILE_TOO_LARGE", 413, "Files must contain 1 to 5,000,000 bytes")
    if (
        not isinstance(name, str)
        or len(name) > 255
        or PurePath(name).name != name
        or "\\" in name
        or any(ord(char) < 32 for char in name)
    ):
        raise rejected()
    extension = PurePath(name).suffix.lower()
    if MIMES.get(extension) != mime:
        raise rejected()
    signature = {
        "application/pdf": b"%PDF-",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": b"PK\x03\x04",
        "image/png": b"\x89PNG\r\n\x1a\n",
        "image/jpeg": b"\xff\xd8\xff",
    }[mime]
    if not data.startswith(signature):
        raise rejected()


def _docx(data: bytes) -> None:
    content_ns = "http://schemas.openxmlformats.org/package/2006/content-types"
    relationships_ns = "http://schemas.openxmlformats.org/package/2006/relationships"
    word_ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    main_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"
    office_relationship = (
        "http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"
    )
    parsed: dict[str, Any] = {}
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        entries = archive.infolist()
        names = [entry.filename for entry in entries]
        if (
            len(entries) > 200
            or len(names) != len(set(names))
            or not {"[Content_Types].xml", "word/document.xml", "_rels/.rels"}.issubset(names)
            or sum(entry.file_size for entry in entries) > 20_000_000
        ):
            raise rejected()
        for entry in entries:
            name = entry.filename
            if (
                name.startswith("/")
                or "\\" in name
                or "\x00" in name
                or posixpath.normpath(name) != name.rstrip("/")
                or ".." in name.split("/")
                or entry.flag_bits & 1
                or entry.file_size > 2_000_000
                or entry.file_size > max(entry.compress_size, 1) * 100
                or any(
                    value in name.lower()
                    for value in ("vbaproject", "embeddings/", "activex/", "customui/")
                )
            ):
                raise rejected()
            if entry.is_dir():
                continue
            content = archive.read(entry)
            if name.endswith((".xml", ".rels")):
                decoded = content.decode("utf-8")
                if (
                    "\x00" in decoded
                    or "<!DOCTYPE" in decoded.upper()
                    or "<!ENTITY" in decoded.upper()
                ):
                    raise rejected()
                root = ElementTree.fromstring(content)  # noqa: S314 -- DTD/entities rejected above.
                parsed[name] = root
                for node in root.iter():
                    if node.attrib.get("TargetMode", "").lower() == "external":
                        raise rejected()
                    if node.tag.rsplit("}", 1)[-1] in {
                        "altChunk",
                        "object",
                        "oleObject",
                        "instrText",
                    }:
                        raise rejected()
                if name.endswith(".rels"):
                    if root.tag != "{" + relationships_ns + "}Relationships":
                        raise rejected()
                    base = (
                        "" if name == "_rels/.rels" else posixpath.dirname(posixpath.dirname(name))
                    )
                    for relationship in root:
                        target = relationship.attrib.get("Target", "")
                        if (
                            relationship.tag != "{" + relationships_ns + "}Relationship"
                            or not target
                            or ":" in target
                            or "\\" in target
                            or posixpath.normpath(posixpath.join(base, target.lstrip("/")))
                            not in names
                        ):
                            raise rejected()
            elif not name.lower().endswith((".png", ".jpg", ".jpeg")):
                raise rejected()
        content_types = parsed["[Content_Types].xml"]
        root_relationships = parsed["_rels/.rels"]
        main_relationships = [
            rel for rel in root_relationships if rel.attrib.get("Type") == office_relationship
        ]
        document = parsed["word/document.xml"]
        if (
            content_types.tag != "{" + content_ns + "}Types"
            or not any(
                node.tag == "{" + content_ns + "}Override"
                and node.attrib.get("PartName") == "/word/document.xml"
                and node.attrib.get("ContentType") == main_type
                for node in content_types
            )
            or len(main_relationships) != 1
            or main_relationships[0].attrib.get("Target", "").lstrip("/") != "word/document.xml"
            or document.tag != "{" + word_ns + "}document"
            or document.find("{" + word_ns + "}body") is None
        ):
            raise rejected()
    # Final independent OPC parser verifies this is an actual openable DOCX package.
    from docx import Document

    Document(io.BytesIO(data))


def _pdf(data: bytes) -> None:
    from pypdf import PdfReader
    from pypdf.generic import DictionaryObject

    if not data.rstrip().endswith(b"%%EOF"):
        raise rejected()
    reader = PdfReader(io.BytesIO(data), strict=True)
    if reader.is_encrypted or not 1 <= len(reader.pages) <= 100:
        raise rejected()
    forbidden = {
        "/JavaScript",
        "/JS",
        "/OpenAction",
        "/AA",
        "/Launch",
        "/EmbeddedFiles",
        "/RichMedia",
        "/XFA",
        "/AcroForm",
        "/SubmitForm",
        "/ImportData",
        "/GoToR",
        "/URI",
        "/EF",
        "/A",
        "/Annots",
    }
    seen: set[int] = set()
    pending: list[Any] = [reader.trailer]
    while pending:
        if len(seen) > 20_000:
            raise rejected()
        node = pending.pop()
        if hasattr(node, "get_object"):
            node = node.get_object()
        identity = id(node)
        if identity in seen:
            continue
        seen.add(identity)
        if isinstance(node, DictionaryObject):
            if forbidden.intersection(node):
                raise rejected()
            pending.extend(node.values())
        elif isinstance(node, list):
            pending.extend(node)


def structural(mime: str, data: bytes) -> None:
    """Invoke only on already malware-scanned bytes, never as preview/conversion."""
    try:
        if mime == "application/pdf":
            _pdf(data)
        elif mime.endswith("wordprocessingml.document"):
            _docx(data)
        else:
            from PIL import Image

            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(io.BytesIO(data)) as image:
                    if (
                        image.format != {"image/png": "PNG", "image/jpeg": "JPEG"}[mime]
                        or image.width * image.height > 25_000_000
                        or getattr(image, "n_frames", 1) != 1
                    ):
                        raise rejected()
                    image.verify()
            if mime == "image/png" and not data.endswith(b"\x00\x00\x00\x00IEND\xaeB`\x82"):
                raise rejected()
            if mime == "image/jpeg" and not data.endswith(b"\xff\xd9"):
                raise rejected()
    except IdentityError:
        raise
    except Exception as exc:
        raise rejected() from exc
