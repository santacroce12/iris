"""Utilidades XML para ISAPI.

Se ignoran los namespaces porque varían entre firmwares (isapi.org, hikvision, psialliance).
"""

from typing import Any
from xml.etree.ElementTree import Element

from defusedxml import ElementTree

from app.drivers.errors import InvalidResponse

ISAPI_NS = "http://www.isapi.org/ver20/XMLSchema"


def local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def parse(content: bytes | str) -> Element:
    try:
        return ElementTree.fromstring(content)
    except ElementTree.ParseError as exc:
        raise InvalidResponse(f"XML inválido: {exc}") from exc


def find(node: Element, *path: str) -> Element | None:
    """Busca por nombre local, sin distinguir mayúsculas, siguiendo `path` desde `node`."""
    current: Element | None = node
    for name in path:
        if current is None:
            return None
        wanted = name.lower()
        current = next((c for c in current if local(c.tag).lower() == wanted), None)
    return current


def find_all(node: Element, name: str) -> list[Element]:
    wanted = name.lower()
    return [e for e in node.iter() if local(e.tag).lower() == wanted]


def text(node: Element | None, *path: str) -> str | None:
    target = find(node, *path) if node is not None and path else node
    if target is None or target.text is None:
        return None
    value = target.text.strip()
    return value or None


def to_int(value: str | None) -> int | None:
    try:
        return int(value) if value is not None else None
    except ValueError:
        return None


def to_dict(node: Element) -> Any:
    """XML → dict. Etiquetas repetidas se vuelven listas; hojas devuelven su texto."""
    children = list(node)
    if not children:
        return (node.text or "").strip()
    result: dict[str, Any] = {}
    for child in children:
        key = local(child.tag)
        value = to_dict(child)
        if key in result:
            if not isinstance(result[key], list):
                result[key] = [result[key]]
            result[key].append(value)
        else:
            result[key] = value
    return result
