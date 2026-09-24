from __future__ import annotations

import csv
import html
import json
import re
import subprocess
import sys
import time
import urllib.parse
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / "cache"
CACHE.mkdir(parents=True, exist_ok=True)
USER_AGENT = "CBCQV-reference-audit/2.0 (mailto:artifact@example.invalid)"


def normalize(text: str) -> list[str]:
    text = html.unescape(re.sub(r"<[^>]+>", " ", text or ""))
    return re.findall(r"[a-z0-9]+", text.lower())


def similarity(left: str, right: str) -> float:
    a, b = set(normalize(left)), set(normalize(right))
    return 1.0 if not a and not b else (len(a & b) / len(a | b) if a and b else 0.0)


def curl_json(url: str, cache_name: str) -> Any:
    path = CACHE / cache_name
    if not path.exists():
        subprocess.run(
            ["curl", "-fsSL", "--retry", "3", "--retry-delay", "1", "--max-time", "45", "-A", USER_AGENT, url, "-o", str(path)],
            check=True,
        )
        time.sleep(0.12)
    return json.loads(path.read_text(encoding="utf-8"))


def curl_text(url: str, cache_name: str) -> str:
    path = CACHE / cache_name
    if not path.exists():
        subprocess.run(
            ["curl", "-fsSL", "--retry", "3", "--retry-delay", "1", "--max-time", "45", "-A", USER_AGENT, url, "-o", str(path)],
            check=True,
        )
        time.sleep(0.12)
    return path.read_text(encoding="utf-8", errors="replace")


def query_crossref(candidate: dict[str, Any]) -> tuple[dict[str, Any], str]:
    key = candidate["key"]
    pinned = candidate.get("doi")
    items: list[dict[str, Any]] = []
    source = ""
    if pinned:
        url = "https://api.crossref.org/works/" + urllib.parse.quote(pinned, safe="")
        try:
            obj = curl_json(url, f"{key}-doi.json")
            items = [obj["message"]]
            source = "Crossref DOI lookup"
        except Exception:
            items = []
    if not items:
        params = urllib.parse.urlencode({"query.bibliographic": candidate["title"] + " " + candidate["author"], "rows": 5})
        obj = curl_json("https://api.crossref.org/works?" + params, f"{key}-query.json")
        items = obj["message"]["items"]
        source = "Crossref bibliographic query"
    scored = []
    for item in items:
        title = (item.get("title") or [""])[0]
        score = similarity(candidate["title"], title)
        authors = " ".join(a.get("family", "") for a in item.get("author", []))
        author_ok = candidate["author"].lower() in authors.lower() or candidate["author"] == "ACM"
        issued = item.get("issued", {}).get("date-parts", [[None]])[0][0]
        year_ok = issued is None or abs(int(issued) - int(candidate["year"])) <= 3
        scored.append((score + (0.08 if author_ok else 0) + (0.04 if year_ok else 0), score, author_ok, year_ok, item))
    if not scored:
        raise RuntimeError(f"no Crossref result for {key}")
    _, title_score, author_ok, year_ok, best = max(scored, key=lambda row: row[0])
    if title_score < 0.58 or not year_ok:
        raise RuntimeError(f"weak Crossref match for {key}: score={title_score:.3f}")
    if candidate["author"] != "ACM" and not author_ok and title_score < 0.82:
        raise RuntimeError(f"author mismatch for {key}")
    return best, source


def escape(value: str) -> str:
    value = html.unescape(re.sub(r"<[^>]+>", "", value or ""))
    replacements = {"&": r"\&", "%": r"\%", "#": r"\#", "_": r"\_"}
    return "".join(replacements.get(ch, ch) for ch in value)


def author_string(item: dict[str, Any], fallback: str) -> str:
    authors = []
    for author in item.get("author", []):
        family = author.get("family", "").strip()
        given = author.get("given", "").strip()
        if family:
            authors.append(escape(f"{family}, {given}" if given else family))
    return " and ".join(authors) if authors else "{" + escape(fallback) + "}"


def bib_entry(candidate: dict[str, Any], item: dict[str, Any]) -> str:
    item_type = item.get("type", "journal-article")
    if item_type in {"book", "monograph", "reference-book"}:
        kind = "book"
    elif item_type in {"book-chapter", "proceedings-article", "posted-content"}:
        kind = "inproceedings" if item_type == "proceedings-article" else "incollection"
    else:
        kind = "article"
    title = (item.get("title") or [candidate["title"]])[0]
    year = item.get("issued", {}).get("date-parts", [[candidate["year"]]])[0][0] or candidate["year"]
    fields = [
        ("author", "{" + author_string(item, candidate["author"]) + "}"),
        ("title", "{" + escape(title) + "}"),
        ("year", str(year)),
    ]
    container = (item.get("container-title") or [""])[0]
    if kind == "article" and container:
        fields.append(("journal", "{" + escape(container) + "}"))
    elif container:
        fields.append(("booktitle", "{" + escape(container) + "}"))
    for source, target in (("volume", "volume"), ("issue", "number"), ("page", "pages"), ("publisher", "publisher")):
        value = item.get(source)
        if value:
            fields.append((target, "{" + escape(str(value).replace("-", "--") if source == "page" else str(value)) + "}"))
    doi = item.get("DOI")
    if doi:
        fields.append(("doi", "{" + escape(doi.lower()) + "}"))
        fields.append(("url", "{https://doi.org/" + escape(doi.lower()) + "}"))
    lines = [f"@{kind}{{{candidate['key']},"]
    for index, (name, value) in enumerate(fields):
        comma = "," if index < len(fields) - 1 else ""
        lines.append(f"  {name} = {value}{comma}")
    lines.append("}")
    return "\n".join(lines)


def _meta_values(body: str, name: str) -> list[str]:
    patterns = [
        rf'<meta[^>]+name=["\']{re.escape(name)}["\'][^>]+content=["\']([^"\']+)["\'][^>]*>',
        rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']{re.escape(name)}["\'][^>]*>',
    ]
    values: list[str] = []
    for pattern in patterns:
        values.extend(re.findall(pattern, body, flags=re.I))
    return [html.unescape(value).strip() for value in values if value.strip()]


def official_entry(candidate: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    body = curl_text(candidate["official_url"], f"{candidate['key']}-official.html")
    tokens = normalize(candidate["title"])
    body_lower = " ".join(normalize(body))
    coverage = sum(1 for token in set(tokens) if token in body_lower) / max(1, len(set(tokens)))
    if coverage < 0.65:
        raise RuntimeError(f"official page title coverage too low for {candidate['key']}: {coverage:.3f}")

    citation_title = (_meta_values(body, "citation_title") or [candidate["title"]])[0]
    authors = _meta_values(body, "citation_author")
    publication = (_meta_values(body, "citation_conference_title") or _meta_values(body, "citation_journal_title"))
    first_page = (_meta_values(body, "citation_firstpage") or [""])[0]
    last_page = (_meta_values(body, "citation_lastpage") or [""])[0]
    date_value = (_meta_values(body, "citation_publication_date") or _meta_values(body, "citation_date") or [str(candidate["year"])])[0]
    year_match = re.search(r'(19|20)\d{2}', date_value)
    resolved_year = int(year_match.group(0)) if year_match else candidate["year"]

    if "usenix.org" in candidate["official_url"]:
        kind = "inproceedings"
        venue = publication[0] if publication else "USENIX Symposium on Networked Systems Design and Implementation"
        author_value = " and ".join(escape(author) for author in authors) if authors else escape(candidate["author"])
        fields = [
            ("author", "{" + author_value + "}"),
            ("title", "{" + escape(citation_title) + "}"),
            ("booktitle", "{" + escape(venue) + "}"),
            ("year", "{" + str(resolved_year) + "}"),
        ]
        if first_page:
            pages = first_page + ("--" + last_page if last_page and last_page != first_page else "")
            fields.append(("pages", "{" + escape(pages) + "}"))
        fields.append(("url", "{" + candidate["official_url"] + "}"))
    else:
        kind = "misc"
        fields = [
            ("author", "{{Association for Computing Machinery}}"),
            ("title", "{" + escape(citation_title) + "}"),
            ("year", "{" + str(resolved_year) + "}"),
            ("url", "{" + candidate["official_url"] + "}"),
        ]
        authors = ["Association for Computing Machinery"]
        venue = "ACM Publications Policy"

    lines = [f"@{kind}{{{candidate['key']},"]
    for index, (field, value) in enumerate(fields):
        lines.append(f"  {field} = {value}{',' if index < len(fields)-1 else ''}")
    lines.append("}")
    entry = "\n".join(lines)
    audit = {
        "key": candidate["key"], "theme": candidate["theme"], "expected_title": candidate["title"],
        "resolved_title": citation_title, "expected_year": candidate["year"], "resolved_year": resolved_year,
        "identifier": candidate["official_url"], "source": "official publisher/conference page",
        "title_similarity": round(similarity(candidate["title"], citation_title), 4), "status": "verified",
        "official_token_coverage": round(coverage, 4), "resolved_authors": authors,
        "resolved_container": venue,
    }
    if audit["title_similarity"] < 0.65:
        raise RuntimeError(f"official metadata title mismatch for {candidate['key']}")
    return entry, audit

def main() -> None:
    candidates = json.loads((ROOT / "candidates.json").read_text(encoding="utf-8"))
    entries = []
    audit = []
    failures = []
    seen_identifiers = set()
    for candidate in candidates:
        try:
            if candidate.get("official_url"):
                entry, record = official_entry(candidate)
            else:
                item, source = query_crossref(candidate)
                doi = item.get("DOI", "").lower()
                if not doi:
                    raise RuntimeError("resolved Crossref record lacks DOI")
                if doi in seen_identifiers:
                    raise RuntimeError(f"duplicate DOI {doi}")
                seen_identifiers.add(doi)
                resolved_title = (item.get("title") or [""])[0]
                resolved_year = item.get("issued", {}).get("date-parts", [[None]])[0][0]
                record = {
                    "key": candidate["key"], "theme": candidate["theme"], "expected_title": candidate["title"],
                    "resolved_title": resolved_title, "expected_year": candidate["year"], "resolved_year": resolved_year,
                    "identifier": doi, "source": source, "title_similarity": round(similarity(candidate["title"], resolved_title), 4),
                    "status": "verified",
                }
                entry = bib_entry(candidate, item)
            entries.append(entry)
            audit.append(record)
        except Exception as exc:
            failures.append({"key": candidate["key"], "error": str(exc)})

    theme_counts = Counter(record["theme"] for record in audit)
    required_themes = {"combinatorics": 9, "formal": 14, "diagnosis": 9, "network": 10, "queueing": 12, "reproducibility": 4}
    if len(audit) < 64:
        raise SystemExit(f"only {len(audit)} references verified; failures={failures}")
    for theme, minimum in required_themes.items():
        if theme_counts[theme] < minimum:
            raise SystemExit(f"theme {theme} has {theme_counts[theme]} verified references, needs {minimum}; failures={failures}")

    (ROOT / "references.bib").write_text("\n\n".join(entries) + "\n", encoding="utf-8")
    report = {
        "schema": "cbcqv-reference-audit-v2",
        "registry": "Crossref REST API for DOI records; official publisher/conference pages for non-DOI records",
        "verified_count": len(audit),
        "candidate_count": len(candidates),
        "theme_counts": dict(sorted(theme_counts.items())),
        "failures": failures,
        "records": audit,
    }
    (ROOT / "reference-audit.json").write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    with (ROOT / "reference-audit.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["key", "theme", "status", "expected_title", "resolved_title", "expected_year", "resolved_year", "identifier", "source", "title_similarity"])
        writer.writeheader()
        for record in audit:
            writer.writerow({name: record.get(name, "") for name in writer.fieldnames})

    groups: dict[str, list[str]] = {}
    for record in audit:
        groups.setdefault(record["theme"], []).append(record["key"])
    lines = ["% Generated by artifact/references/verify_references.py"]
    command_names = {
        "combinatorics": "CombinatoricsRefs", "formal": "FormalRefs", "diagnosis": "DiagnosisRefs",
        "network": "NetworkRefs", "queueing": "QueueingRefs", "reproducibility": "ReproRefs",
    }
    for theme, command in command_names.items():
        lines.append("\\newcommand{\\" + command + "}{\\cite{" + ",".join(groups[theme]) + "}}")
    lines.append(r"\newcommand{\VerifiedReferenceCount}{" + str(len(audit)) + "}")
    (ROOT / "reference-groups.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"verified": len(audit), "themes": dict(theme_counts), "failures": failures}, sort_keys=True))


if __name__ == "__main__":
    main()
