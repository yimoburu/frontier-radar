from __future__ import annotations

import xml.etree.ElementTree as ET

from frontier_radar.collectors.base import fetch_bytes
from frontier_radar.models import NormalizedItem
from frontier_radar.raw import RawStore


ATOM = "{http://www.w3.org/2005/Atom}"


def text(node: ET.Element | None, default: str = "") -> str:
    return "".join(node.itertext()).strip() if node is not None else default


def atom_link(entry: ET.Element) -> str:
    links = [link for link in entry.findall(f"{ATOM}link") if link.attrib.get("href")]
    for link in links:
        if link.attrib.get("rel") == "alternate":
            return link.attrib["href"]
    for link in links:
        if link.attrib.get("rel") != "self":
            return link.attrib["href"]
    return links[0].attrib["href"] if links else ""


def parse_feed(xml: bytes, source: str, source_name: str, raw_path: str) -> list[NormalizedItem]:
    root = ET.fromstring(xml)
    items: list[NormalizedItem] = []
    if root.tag == f"{ATOM}feed":
        for entry in root.findall(f"{ATOM}entry"):
            link = atom_link(entry)
            author = text(entry.find(f"{ATOM}author/{ATOM}name"), source_name)
            items.append(
                NormalizedItem(
                    source=source,
                    source_type="feed",
                    title=text(entry.find(f"{ATOM}title")),
                    url=link,
                    author=author,
                    published_at=text(entry.find(f"{ATOM}updated"), "1970-01-01T00:00:00+00:00"),
                    summary=text(entry.find(f"{ATOM}summary")),
                    raw_path=raw_path,
                    tags=[source_name],
                    metrics={},
                    metadata={"feed": source_name},
                )
            )
    else:
        for entry in root.findall("./channel/item"):
            items.append(
                NormalizedItem(
                    source=source,
                    source_type="feed",
                    title=text(entry.find("title")),
                    url=text(entry.find("link")),
                    author=text(entry.find("author"), source_name),
                    published_at=text(entry.find("pubDate"), "1970-01-01T00:00:00+00:00"),
                    summary=text(entry.find("description")),
                    raw_path=raw_path,
                    tags=[source_name],
                    metrics={},
                    metadata={"feed": source_name},
                )
            )
    return [item for item in items if item.url and item.title]


def collect_rss(
    config: dict,
    raw_store: RawStore,
    now: str,
    source: str = "rss",
    errors: list[str] | None = None,
) -> list[NormalizedItem]:
    results: list[NormalizedItem] = []
    for feed in config.get("feeds", []):
        try:
            xml = fetch_bytes(feed["url"])
            raw_path = raw_store.write_snapshot(source, "xml", xml, now=now)
            results.extend(parse_feed(xml, source=source, source_name=feed["name"], raw_path=str(raw_path)))
        except Exception as exc:
            if errors is not None:
                errors.append(f"{source} feed {feed.get('name', feed.get('url', '<unknown>'))}: {exc}")
            continue
    return results
