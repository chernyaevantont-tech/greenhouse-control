"""Author identity for the manuscript, from one file, or not at all.

Nothing in this repository invents an author name, an ORCID iD, an affiliation
or an e-mail address.  Until a human fills in ``authors.json`` next to this
module, both builds keep the red ``[[...REQUIRED]]`` placeholders they have
always carried; once it is filled in, the LaTeX assembler and the Word styling
pass read the *same* file, so the two front matters cannot disagree.

Two kinds of gap are treated differently, because they are different:

* **Identity is required.**  A name, its initials and an affiliation number must
  be present for every author listed.  A file that names one author and leaves
  the next as a placeholder is refused: a partly real author line is worse than
  an obviously unfinished one.
* **Contact details and statements may be pending.**  ORCID iDs, e-mail
  addresses, the CRediT sentence, funding, acknowledgments, conflicts and the
  data DOI are usually settled after the names are.  Leave them ``""`` and the
  manuscript prints the same loud ``[[...]]`` marker it printed before, which
  ``audit_mdpi.py`` still lists.  Nothing is quietly invented and nothing is
  quietly dropped.

Copy ``authors.example.json`` to ``authors.json`` to start.
"""
from __future__ import annotations

import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "authors.json")
EXAMPLE = os.path.join(HERE, "authors.example.json")

#: Identity: required of every author entry.
_REQUIRED_PER_AUTHOR = ("name", "initials", "affiliation")
#: Contact details: may be left empty and print as a marker.
_PENDING_PER_AUTHOR = ("orcid", "email")
#: Back-matter statements: may be left empty and keep the assembler's placeholder.
_PENDING_TOP = ("author_contributions", "funding", "acknowledgments",
                "conflicts_of_interest", "data_location")

ORCID_PENDING = "[[ORCID REQUIRED]]"
EMAIL_PENDING = "[[E-MAIL REQUIRED]]"

_ORCID = re.compile(r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$")


class AuthorshipError(RuntimeError):
    """authors.json exists but cannot be used as it stands."""


def _blank(value) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def load(path: str = PATH):
    """Return the validated authorship record, or ``None`` if there is no file."""
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    problems: list[str] = []

    affiliations = [a for a in data.get("affiliations", []) if not _blank(a)]
    if not affiliations:
        problems.append("affiliations: at least one full postal affiliation is required")

    authors = data.get("authors") or []
    if not authors:
        problems.append("authors: at least one author is required")

    corresponding = []
    seen_initials: dict[str, int] = {}
    for i, author in enumerate(authors, 1):
        for key in _REQUIRED_PER_AUTHOR:
            if key not in author or _blank(author.get(key)):
                problems.append(f"author {i}: missing or empty: {key}")
        for key in _PENDING_PER_AUTHOR:
            if key not in author:
                problems.append(f"author {i}: {key} must be present "
                                f'(use "" while it is still pending)')
        orcid = str(author.get("orcid", "")).strip()
        if orcid and not _ORCID.match(orcid):
            problems.append(f"author {i}: orcid is not in 0000-0000-0000-0000 form: {orcid!r}")
        index = author.get("affiliation")
        if isinstance(index, int) and not (1 <= index <= len(affiliations)):
            problems.append(f"author {i}: affiliation {index} does not exist "
                            f"(there are {len(affiliations)})")
        initials = str(author.get("initials", "")).strip()
        if initials:
            first = seen_initials.setdefault(initials, i)
            if first != i:
                problems.append(f"author {i}: initials {initials!r} already belong to "
                                f"author {first}; CRediT roles would be ambiguous")
        if author.get("corresponding"):
            corresponding.append(i)

    if len(corresponding) != 1:
        problems.append("exactly one author must carry \"corresponding\": true "
                        f"(found {len(corresponding)})")

    used = {a.get("affiliation") for a in authors}
    for n in range(1, len(affiliations) + 1):
        if n not in used:
            problems.append(f"affiliation {n} is listed but no author uses it")

    for key in _PENDING_TOP:
        if key not in data:
            problems.append(f'{key} must be present (use "" while it is still pending)')

    if problems:
        raise AuthorshipError(
            "authors.json cannot be used as it stands.\n  - " + "\n  - ".join(problems))
    return data


def corresponding_author(data: dict) -> dict:
    return next(a for a in data["authors"] if a.get("corresponding"))


def orcid_of(author: dict) -> str:
    """The iD, or the marker where one is required and still missing.

    MDPI requires an ORCID iD for the corresponding author and displays it for
    anyone else who has one.  A missing iD is therefore a blocker for exactly
    one author, and only that author carries a marker on the title page; for the
    rest nothing is printed until an iD exists.  ``pending()`` lists them all
    either way, so none is forgotten.
    """
    orcid = str(author.get("orcid", "")).strip()
    if orcid:
        return orcid
    return ORCID_PENDING if author.get("corresponding") else ""


def email_of(author: dict) -> str:
    return str(author.get("email", "")).strip() or EMAIL_PENDING


def pending(data: dict) -> list[str]:
    """Human-readable list of what is still missing.  Empty means submittable."""
    out = []
    for author in data["authors"]:
        if not str(author.get("orcid", "")).strip():
            out.append(f"ORCID iD for {author['name']}")
        if not str(author.get("email", "")).strip():
            out.append(f"e-mail for {author['name']}")
    for key in _PENDING_TOP:
        if _blank(data.get(key)):
            out.append(key)
    return out


# ---------------------------------------------------------------------------
# LaTeX
# ---------------------------------------------------------------------------

def _tex_escape(text: str) -> str:
    for bad, good in (("&", r"\&"), ("%", r"\%"), ("#", r"\#"), ("_", r"\_")):
        text = text.replace(bad, good)
    return text


def _tex_marker(text: str) -> str:
    """Pending values stay red in the PDF, like the placeholders they replace."""
    if text.startswith("[["):
        return r"\textcolor{red}{" + _tex_escape(text) + "}"
    return _tex_escape(text)


def _affiliation_contacts(data: dict, n: int) -> str:
    """``e-mail (I.N.)`` for every author at affiliation ``n``, MDPI style."""
    return "; ".join(f"{email_of(a)} ({a['initials']})"
                     for a in data["authors"] if a["affiliation"] == n)


def latex_author_block(data: dict) -> str:
    """The ``\\author{...}`` block, in the shape the placeholder block used."""
    lines = ["\\author{%"]
    for i, author in enumerate(data["authors"]):
        name = _tex_escape(author["name"])
        star = ",*" if author.get("corresponding") else ""
        joint = "  " if i == 0 else "  \\and "
        lines.append(f"{joint}\\textbf{{{name}}}$^{{{author['affiliation']}{star}}}$")
        orcid = orcid_of(author)
        if orcid:
            lines.append(f"  \\ \\textsuperscript{{{_tex_marker(orcid)}}}")
    lines[-1] = lines[-1] + " \\\\[4pt]"
    for n, affiliation in enumerate(data["affiliations"], 1):
        tail = " \\\\" if n < len(data["affiliations"]) else ""
        contacts = "; ".join(
            f"{_tex_marker(email_of(a))} ({_tex_escape(a['initials'])})"
            for a in data["authors"] if a["affiliation"] == n)
        lines.append(f"  \\small $^{{{n}}}${_tex_escape(affiliation)}; {contacts}{tail}")
    corres = corresponding_author(data)
    lines.append(r"  \\[2pt] \small $^{*}$Correspondence: "
                 + _tex_marker(email_of(corres)))
    lines.append("}")
    return "\n".join(lines)


def latex_fields(data: dict) -> dict:
    """Back-matter statements that are actually filled in, ready to substitute.

    Keys that are still empty are left out, so the assembler keeps its own
    placeholder text for them.
    """
    mapping = {
        "@@AUTHOR_CONTRIBUTIONS@@": "author_contributions",
        "@@FUNDING@@": "funding",
        "@@CONFLICTS@@": "conflicts_of_interest",
        "@@DATA_LOCATION@@": "data_location",
        "@@ACKNOWLEDGMENTS@@": "acknowledgments",
    }
    return {token: _tex_escape(data[key])
            for token, key in mapping.items() if not _blank(data.get(key))}


# ---------------------------------------------------------------------------
# Word
# ---------------------------------------------------------------------------

def word_front_matter(data: dict) -> dict:
    """The three front-matter pieces the Word styler writes.

    ``names`` is a list of (text, superscript, bold) runs; ``affiliations`` and
    ``correspondence`` are (bold-prefix, rest) pairs.
    """
    runs: list[tuple[str, str, bool]] = []
    for i, author in enumerate(data["authors"]):
        if i:
            runs.append(("; ", "", False))
        star = ",*" if author.get("corresponding") else ""
        runs.append((author["name"], f"{author['affiliation']}{star}", True))
        orcid = orcid_of(author)
        if orcid:
            runs.append((" " + orcid, "", False))
    affiliations = []
    for n, affiliation in enumerate(data["affiliations"], 1):
        affiliations.append((f"{n} ", f"{affiliation}; {_affiliation_contacts(data, n)}"))
    return {
        "names": runs,
        "affiliations": affiliations,
        "correspondence": ("* Correspondence: ", email_of(corresponding_author(data))),
    }
