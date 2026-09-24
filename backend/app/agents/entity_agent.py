"""ENTITY & EVENT EXTRACTION AGENT.

NER (spaCy) + regex + normalization. A Transformers token-classification model is
used when one is available locally; otherwise the agent reports the spaCy+rule
hybrid backend it actually used (no fabricated model claims).
"""
from __future__ import annotations

import re
from typing import Any, Iterable, Optional

from . import indic

AGENT_NAME = "ENTITY_RESOLUTION_AGENT"

_NLP = None
_NLP_BACKEND = "UNINITIALISED"
_TRANSFORMER_NER = None


def _load_nlp():
    global _NLP, _NLP_BACKEND
    if _NLP is not None:
        return _NLP
    try:
        import spacy

        try:
            _NLP = spacy.load("en_core_web_sm")
            _NLP_BACKEND = "spaCy:en_core_web_sm"
        except Exception:
            _NLP = spacy.blank("en")
            _NLP_BACKEND = "spaCy:blank(en) + rules (statistical model not installed)"
    except Exception as exc:  # pragma: no cover
        _NLP = None
        _NLP_BACKEND = f"UNAVAILABLE ({exc})"
    return _NLP


def backend_info() -> dict[str, Any]:
    _load_nlp()
    return {
        "ner_backend": _NLP_BACKEND,
        "transformers_backend": (
            "TRANSFORMERS token-classification (not loaded - no local model weights present); "
            "spaCy statistical NER + deterministic rules used instead"
            if _TRANSFORMER_NER is None else "TRANSFORMERS token-classification"
        ),
        "rule_layer": "regex: vehicle registration, phone, account, IMEI/device, case id, date",
        "indic_layer": (
            "Devanagari/Tamil: Unicode script detection -> deterministic romanisation "
            "-> fuzzy match against the known case-graph vocabulary + month vocabulary "
            "+ postposition structure. NOT a trained Indic NER model: entities absent "
            "from the case vocabulary are reported at LOW confidence as structural candidates."
        ),
        "indic_supported_scripts": ["Devanagari", "Tamil"],
    }


PATTERNS: dict[str, re.Pattern[str]] = {
    "VEHICLE": re.compile(r"\b(?:[A-Z]{2}\s?\d{2}\s?[A-Z]{1,2}\s?\d{4})\b"),
    # Indian mobile formats. Matches +91XXXXXXXXXX, +91 XXXXX XXXXX,
    # 0XXXXXXXXXX and bare 10-digit domestic numbers, with optional
    # spaces / hyphens / dots as separators. Digit lookarounds stop the
    # pattern matching a fragment of a longer number (IMEI, account no.).
    "PHONE": re.compile(
        r"(?<![\d])"
        r"(?:(?:\+|00)[\s.\-]?91[\s.\-]?|0[\s.\-]?)?"
        r"[6-9]\d{4}[\s.\-]?\d{5}"
        r"(?![\d])"
    ),
    "ACCOUNT": re.compile(r"\b(?:AC|ACCT|A/C)[\s-]?(?:NO\.?\s*)?([0-9]{6,16})\b", re.I),
    "DEVICE": re.compile(r"\b(?:IMEI[\s:-]*)(\d{14,16})\b", re.I),
    "CASE": re.compile(r"\bCASE-\d{3,4}\b"),
    "DATE": re.compile(
        r"\b(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)"
        r"(?:\s+\d{4})?|\d{4}-\d{2}-\d{2})\b", re.I),
    "TIME": re.compile(r"\b([01]?\d|2[0-3]):[0-5]\d\b"),
}

EVENT_TRIGGERS = {
    "observed": "OBSERVATION", "seen": "OBSERVATION", "sighted": "OBSERVATION",
    "reported": "REPORT", "registered": "REGISTRATION", "recovered": "RECOVERY",
    "transferred": "TRANSACTION", "transaction": "TRANSACTION", "credited": "TRANSACTION",
    "debited": "TRANSACTION", "called": "COMMUNICATION", "contacted": "COMMUNICATION",
    "travelled": "MOVEMENT", "moved": "MOVEMENT", "parked": "MOVEMENT",
    "stopped": "MOVEMENT", "met": "CO_PRESENCE", "present": "CO_PRESENCE",
    # Indian police / intelligence-reporting vocabulary: these verbs carry the same
    # evidentiary force as the English defaults above and appear throughout the
    # FIR, station-report and note formats.
    "recorded": "OBSERVATION", "using": "OBSERVATION", "used": "OBSERVATION",
    "named": "REPORT", "associated": "ASSOCIATION", "holds": "ASSOCIATION",
    "signatory": "ASSOCIATION", "employer": "ASSOCIATION", "operates": "ASSOCIATION",
    "states": "REPORT", "stated": "REPORT", "seen": "OBSERVATION",
}

# Indian police documents prefix names with an honorific (Thiru/Tmt/Shri/...).
# The accused block is often printed in ALL CAPS, which the statistical model
# reads as an ORGANIZATION - this rule recovers it as a PERSON.
_HONORIFIC_PERSON = re.compile(
    r"\b(?:Thiru|Tmt|Shri|Smt|Sri|Selvi|Mr|Mrs|Ms)\.?\s+"
    r"((?:[A-Za-z]\.\s*)?[A-Za-z][A-Za-z'.]*(?:\s+[A-Za-z][A-Za-z'.]*){0,2})")

# Greedy name capture can absorb the start of the next clause ("Ravi Kumar Was
# Observed"). Trailing function words are trimmed rather than kept as a name.
_NAME_TAIL_STOPWORDS = {
    "was", "were", "is", "are", "appeared", "appears", "before", "and", "the", "in",
    "at", "on", "of", "to", "for", "with", "has", "have", "had", "who", "which",
    "that", "aged", "age", "approx", "son", "daughter", "wife", "resident", "r/o",
    "s/o", "w/o", "d/o", "no", "not", "unknown", "reported", "stated", "deposed",
    "observed", "present", "years", "yrs",
}


def _trim_name(raw: str) -> str:
    tokens = raw.split()
    while tokens and tokens[-1].lower().strip(".,") in _NAME_TAIL_STOPWORDS:
        tokens.pop()
    return " ".join(tokens)


_STOP_ORG = {"police", "station", "fir", "cdr", "ocr", "imei", "bureau of"}

# --------------------------------------------------------------------------
# ALIAS heuristic guard
# --------------------------------------------------------------------------
# Abbreviated person forms ("R. Kumar", "S. Vasanthi") have exactly the same shape
# as dotted institutional abbreviations on Indian police forms ("P.S." = police
# station, "U.D." = unnatural death, "F.I.R", "G.D.", "I.O."). These two lists are
# the rejection filter; extend them here rather than tightening the pattern, which
# must keep catching genuine short forms.
# NOTE the closing guard: the original pattern ended in \b, which can never match
# after a final "." (a period is not a word character), so the "Ravi K." form was
# silently NEVER extracted while "Ravi K.was" - i.e. only the malformed glue cases -
# did match. (?!\w) keeps the intended "not glued to the next letter" behaviour and
# makes the trailing-initial form work as documented.
_ALIAS_PATTERN = re.compile(r"\b([A-Z]\.\s?[A-Z][a-z]+|[A-Z][a-z]+\s[A-Z]\.)(?!\w)")

_ALIAS_ABBREVIATIONS = {
    "P.S", "F.I.R", "G.D", "I.O", "U.D", "S.O", "C.O", "H.C", "O.C", "C.S",
    "DIST", "ADDL", "REGD", "NO", "SEC", "RS", "GOVT", "CR", "S.I", "D.S.P",
    "INSP", "SUB", "SUP", "ASST", "DY", "SR", "JR", "ETC", "ALIAS", "S/O", "W/O",
    "D/O", "R/O",
}

# Common institutional / form nouns. The capitalized component of an alias must
# look like a surname or given name, not like form vocabulary or a generic place
# descriptor. Kept deliberately narrow: real names ("Vasanthi", "Ganesan") pass.
_ALIAS_FORM_NOUNS = {
    # form / document vocabulary
    "case", "no", "number", "date", "year", "time", "name", "place", "address",
    "police", "station", "limits", "limit", "report", "inquest", "contents",
    "signature", "office", "officer", "charge", "rank", "section", "act", "rule",
    "page", "form", "annexure", "document", "reference", "details", "particulars",
    "complainant", "informant", "witness", "accused", "victim", "property",
    "jurisdiction", "district", "state", "court", "government",
    # generic position / place descriptors
    "outside", "inside", "within", "central", "north", "south", "east", "west",
    "upper", "lower", "main", "new", "old", "near", "opposite", "above", "below",
}

_ALIAS_NEIGHBOUR_ABBREV = re.compile(r"^[A-Za-z]\.$")
_ALIAS_PAREN_LABEL = re.compile(r"^\([a-z0-9]{1,3}\)$")


# Honorifics are stripped by the dedicated _HONORIFIC_PERSON rule; with the trailing
# period now matchable, "Thiru M." (honorific + initial of the NEXT word) also has the
# alias shape and must not be accepted as one.
_HONORIFIC_PREFIX_BEFORE = re.compile(
    r"(?:Thiru|Tirumathi|Tmt|Shri|Smt|Sri|Selvi|Mr|Mrs|Ms)\.?\s*$", re.I)

_ALIAS_HONORIFICS = {"thiru", "thirumathi", "tmt", "shri", "smt", "sri", "selvi",
                     "mr", "mrs", "ms", "dr", "sub", "insp"}


def _alias_candidates(text: str):
    """Yield ALIAS pattern matches, recovering the inner name after an honorific.

    "Thiru R. Selvaraj" makes the pattern match the honorific itself ("Thiru R.")
    and, because finditer scans forward from the end of a match, the real name would
    be skipped. After such a match the scan resumes one character in, so
    "R. Selvaraj" is found and the honorific fragment is dropped by the filter.
    """
    pos = 0
    while pos < len(text):
        m = _ALIAS_PATTERN.search(text, pos)
        if m is None:
            return
        yield m
        words = re.findall(r"[A-Za-z]+", m.group(0))
        pos = m.start() + 1 if words and words[0].lower() in _ALIAS_HONORIFICS else m.end()


def _alias_is_plausible(surface: str, before: str, after: str) -> bool:
    """Reject an ALIAS match that is really form structure, not a person's name."""
    words = [w for w in re.findall(r"[A-Za-z]+", surface) if len(w) > 1]
    if not words or any(w.lower() in _ALIAS_FORM_NOUNS for w in words):
        return False
    if words[0].lower() in _ALIAS_HONORIFICS:
        return False              # "Thiru M. Ganesan" -> "Thiru M" is not an alias

    before_words = before.split()
    if before_words:
        prev = before_words[-1]
        token = prev.strip("()").upper().rstrip(".")
        if token in _ALIAS_ABBREVIATIONS:
            return False
        if _ALIAS_NEIGHBOUR_ABBREV.match(prev) and prev.rstrip(".").isupper():
            return False          # "U.D. Case" -> "D. Case" is a fragment
        if _ALIAS_PAREN_LABEL.match(prev):
            return False          # "(d) Outside P.S. limits" -> form lettering

    after_words = after.split()
    if after_words:
        nxt = after_words[0].strip("()").upper().rstrip(".")
        if nxt in _ALIAS_ABBREVIATIONS:
            return False          # "Chennai Central P.S." / "Outside P.S. limits"
        if after.lstrip().startswith((".", " ",)) and after_words[0][:2] == "S.":
            return False
    return True

# An organisation is only accepted when (a) it is a known organisation from the case
# vocabulary, or (b) its name carries an organisational marker, or (c) it is a
# multi-word mixed-case proper name. This rejects document headings in capitals
# ("ACCOUNT ACTIVITY EXTRACT") and bare place names ("Madurai", "Chennai") that the
# statistical model labels as ORG.
_ORG_MARKERS = {
    "ltd", "limited", "pvt", "private", "inc", "corp", "corporation", "company", "co",
    "bank", "trust", "agency", "department", "bureau", "services", "service", "logistics",
    "spares", "stores", "works", "factory", "mills", "hospital", "college", "university",
    "institute", "authority", "board", "office", "unit", "cell", "committee", "society",
    "foundation", "enterprises", "traders", "transport", "travels", "hotels", "industries",
}


# A street / locality suffix means the value is a place, not an institution.
_STREET_SUFFIX_WORDS = {
    "road", "street", "lane", "avenue", "nagar", "colony", "chowk", "bazaar", "bazar",
    "junction", "puram", "cross", "salai", "theru", "veedhi", "highway", "bypass",
    "estate", "layout", "township", "complex",
}

_HONORIFIC_WORDS = {"thiru", "tirumathi", "tmt", "shri", "smt", "sri", "selvi",
                    "mr", "mrs", "ms", "dr"}


def _looks_like_place(value: str) -> bool:
    """An address line (street / estate / layout) is a LOCATION, not an institution."""
    tokens = [t.strip(".,").lower() for t in value.split()]
    return bool(tokens) and any(t in _STREET_SUFFIX_WORDS for t in tokens)


def _is_plausible_organisation(value: str, known_orgs: set[str]) -> bool:
    key = value.upper().rstrip(".").strip()
    if key in known_orgs:
        return True
    tokens = [t.strip(".,").lower() for t in value.split()]
    if any(t in _STREET_SUFFIX_WORDS for t in tokens):
        # "Wall Tax Road" is an address line the statistical model labels ORG
        return False
    if any(t in _ORG_MARKERS for t in tokens):
        return True
    if value.isupper():
        return False                      # a heading, not an entity name
    if tokens and tokens[0] == "the":
        # "the CrimeNet AI pipeline" / "THE CrimeNet AI PIPELINE": a description in a
        # sentence or a heading, not an organisation name (a real one carries a
        # marker word, which is checked above)
        return False
    return len(tokens) >= 3 and any(t[:1].isupper() for t in value.split())
# --------------------------------------------------------------------------
# Type validators - the statistical NER layer over-generates on form documents
# --------------------------------------------------------------------------
_MONTH_WORD = (r"jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|"
               r"aug(?:ust)?|sep(?:t|tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?")
_VALID_DATE = re.compile(
    rf"^\s*(?:\d{{1,2}}\s*(?:{_MONTH_WORD})\.?\s*(?:\d{{4}})?"
    rf"|(?:{_MONTH_WORD})\.?\s*\d{{1,2}}(?:\s*,?\s*\d{{4}})?"
    rf"|\d{{4}}-\d{{2}}-\d{{2}}|\d{{1,2}}[/.-]\d{{1,2}}[/.-]\d{{2,4}})\s*$", re.I)
_VALID_TIME = re.compile(r"^\s*(?:[01]?\d|2[0-3]):[0-5]\d(?:\s*[ap]\.?m\.?)?\s*$", re.I)
# Printed field labels and headings on Indian police/administrative forms. A
# general-purpose statistical model has no way to tell these apart from real
# entities, so they are rejected by a domain stoplist rather than guessed at.
_FORM_BOILERPLATE = re.compile(
    r"\b(?:sections?|acts?|pages?|signature|forms?|annexure|chassis|engine|"
    r"description|est|sl|total|details?|particulars?|date|times?|place|"
    r"names?|address|rank|tmt|thiru(?!\s+[a-z]+\s)|husband|wife|inquest|"
    r"complainant|informant|case diary|court|no|beat|occupation|nationality|"
    r"passport|mobile|status|police station|inspector|officer|property|properties|"
    r"persons?|unknown|nil|not applicable|reasons?|delay|value|synthetic|demo)\b",
    re.I)
_DIRECTIONAL = re.compile(r"^(?:north|south|east|west)(?:[- ](?:north|south|east|west))?$", re.I)
# "Rs." / "INR" are form noise only when they introduce an amount; as a bare token
# they collide with real place names such as "Coimbatore RS Puram".
_AMOUNT_MARKER = re.compile(r"\b(?:rs|inr)\.?\s*[\d,]+", re.I)


def _is_valid(entity_type: str, surface: str, normalized: str) -> bool:
    """Reject values the type could not legitimately hold.

    Without this, `en_core_web_sm` labels bare years ("1860", "2016") and generic
    form headings ("Sections", "Inr") as DATE/ORGANIZATION in a document that is
    mostly a printed form, and those end up as graph nodes.
    """
    text = (surface or normalized or "").strip()
    if len(text) < 3:
        return False
    if entity_type == "DATE":
        return bool(_VALID_DATE.match(text))
    if entity_type == "TIME":
        return bool(_VALID_TIME.match(text))
    if entity_type == "ORGANIZATION":
        return not _FORM_BOILERPLATE.search(text) and not _AMOUNT_MARKER.search(text)
    if entity_type == "PERSON":
        # A person name must be at least two alphabetic tokens, or one token of
        # 4+ letters that is not a printed form label ("Tmt", "Rank" are labels).
        if _FORM_BOILERPLATE.search(text):
            return False
        tokens = re.findall(r"[A-Za-z\u0900-\u097F\u0B80-\u0BFF]{2,}", text)
        if len(tokens) >= 2:
            return True
        return bool(tokens) and len(tokens[0]) >= 4 and not re.search(r"\d", text)
    if entity_type == "LOCATION":
        if _FORM_BOILERPLATE.search(text) or _DIRECTIONAL.match(text.strip()):
            return False
        return bool(re.search(r"[A-Za-z\u0900-\u097F\u0B80-\u0BFF]{3}", text))
    if entity_type == "VEHICLE":
        return bool(re.match(r"^[A-Z]{2}\s?\d{2}\s?[A-Z]{1,3}\s?\d{4}$", text, re.I))
    return True




def normalize_value(entity_type: str, value: str) -> str:
    v = value.strip()
    if entity_type == "VEHICLE":
        return re.sub(r"[\s-]", "", v).upper()
    if entity_type == "PHONE":
        digits = re.sub(r"\D", "", v)
        return "+91" + digits[-10:]
    if entity_type in {"PERSON", "ALIAS"}:
        v = re.sub(r"\s+", " ", v)
        v = re.sub(r"[^A-Za-z. ]", "", v)
        return v.title().strip()
    if entity_type in {"LOCATION", "ORGANIZATION"}:
        return re.sub(r"\s+", " ", v).title().strip()
    if entity_type == "ACCOUNT":
        return re.sub(r"\D", "", v)
    return v.strip()


_LETTERS = re.compile(r"[^A-Za-z]")


def _letters(value: str) -> str:
    return _LETTERS.sub("", value).upper()


def reconcile_entities(entities: list[dict[str, Any]],
                       gazetteer: Optional[dict[str, Iterable[str]]] = None
                       ) -> list[dict[str, Any]]:
    """Cross-type reconciliation pass.

    The extraction layers run independently, so on a real police document the same
    span can surface under two types and a span can be a fragment of a longer
    mention. Measured against the labelled evaluation set (Phase 6) these were the
    remaining error sources, so they are removed here:

      1. a value already extracted as a LOCATION is not also an ORGANIZATION
         ("Chennai Central" is a place, not an institution);
      2. an ORGANIZATION that is a fragment of a LOCATION is dropped ("Chennai");
      3. an ORGANIZATION that is really a PERSON is dropped ("Divya Nair");
      4. a PERSON that is only a fragment of another PERSON in the same document
         is dropped ("Kumar" beside "R. Kumar");
      5. a PERSON that is just the letters of an identifier in the same document
         is dropped ("Tnab" against vehicle "TN01AB1234");
      6. values differing only by a trailing full stop are merged
         ("Coastal Logistics Pvt Ltd." == "Coastal Logistics Pvt Ltd").
    """
    by_type: dict[str, list[dict[str, Any]]] = {}
    for e in entities:
        by_type.setdefault(e["entity_type"], []).append(e)

    def key(value: str) -> str:
        return value.upper().rstrip(".").strip()

    locations = {key(e["normalized"]) for e in by_type.get("LOCATION", [])}
    known_orgs = {key(v) for v in (gazetteer or {}).get("ORGANIZATION", [])}
    persons = [key(e["normalized"]) for e in by_type.get("PERSON", [])]
    identifiers = [_letters(e["normalized"]) for t in ("VEHICLE", "DEVICE", "PHONE", "ACCOUNT")
                   for e in by_type.get(t, [])]
    kept: dict[tuple[str, str], dict[str, Any]] = {}

    for e in entities:
        etype, value = e["entity_type"], e["normalized"]
        k = key(value)
        if etype == "ORGANIZATION":
            if k in locations or any(k and k != loc and k in loc for loc in locations):
                continue
            if k in persons:
                continue
            if not _is_plausible_organisation(value, known_orgs):
                continue
        if etype == "PERSON":
            if any(k != other and k in other for other in persons):
                continue
            letters = _letters(value)
            if len(letters) >= 4 and letters in identifiers:
                continue
        merged = kept.get((etype, k))
        if merged is None:
            merged = dict(e)
            merged["normalized"] = value.rstrip(".").strip()
            kept[(etype, k)] = merged
        else:
            merged["mentions"] += e["mentions"]
            merged["offsets"].extend(e["offsets"])
            for m in e["methods"]:
                if m not in merged["methods"]:
                    merged["methods"].append(m)
    return [kept[k] for k in sorted(kept, key=lambda kk: (kk[0], kk[1]))]


def extract_entities(text: str, gazetteer: Optional[dict[str, Iterable[str]]] = None
                     ) -> list[dict[str, Any]]:
    """Return deduplicated entity mentions with type, surface form, normalized value,
    extraction method and character offsets."""
    found: dict[tuple[str, str], dict[str, Any]] = {}

    def add(etype: str, surface: str, method: str, start: int, end: int, conf: float,
            canonical: Optional[str] = None) -> None:
        # `canonical` lets a non-Latin surface (e.g. 'चेन्नई सेंट्रल') resolve to
        # the existing graph label ('Chennai Central') so mentions merge instead
        # of creating duplicate entities.
        norm = canonical or normalize_value(etype, surface)
        if not norm or len(norm) < 2:
            return
        # Validate the canonical form when the extractor already resolved one
        # (an Indic date resolves to '12 August' before validation).
        if not _is_valid(etype, canonical or surface, norm):
            return
        key = (etype, norm)
        item = found.get(key)
        if item is None:
            found[key] = {
                "entity_type": etype, "surface": surface.strip(), "normalized": norm,
                "methods": [method], "mentions": 1, "offsets": [[start, end]],
                "confidence": conf,
            }
            if canonical and canonical.strip() != surface.strip():
                found[key]["canonical_form"] = canonical.strip()
                found[key]["transliterated_from"] = surface.strip()
        else:
            item["mentions"] += 1
            item["offsets"].append([start, end])
            if canonical and "canonical_form" not in item and canonical.strip() != surface.strip():
                item["canonical_form"] = canonical.strip()
                item["transliterated_from"] = surface.strip()
            if method not in item["methods"]:
                item["methods"].append(method)
                item["confidence"] = min(0.99, item["confidence"] + 0.08)

    # --- rule layer --------------------------------------------------------
    for m in _HONORIFIC_PERSON.finditer(text):
        name = _trim_name(m.group(1))
        if name:
            add("PERSON", name, "honorific-pattern", m.start(1), m.start(1) + len(name), 0.8)
    for etype, pattern in PATTERNS.items():
        for m in pattern.finditer(text):
            add(etype, m.group(0), "regex", m.start(), m.end(), 0.9 if etype != "DATE" else 0.8)

    # --- statistical NER layer --------------------------------------------
    nlp = _load_nlp()
    if nlp is not None:
        try:
            doc = nlp(text)
            label_map = {
                "PERSON": "PERSON", "GPE": "LOCATION", "LOC": "LOCATION", "FAC": "LOCATION",
                "ORG": "ORGANIZATION", "DATE": "DATE", "TIME": "TIME", "MONEY": "AMOUNT",
            }
            for ent in getattr(doc, "ents", []):
                mapped = label_map.get(ent.label_)
                if not mapped:
                    continue
                # The statistical model is en_core_web_sm: it has never seen
                # Devanagari or Tamil training data, so its spans there are noise
                # (it labelled "रवि कुमार को 12" as an ORGANIZATION). Indic spans are
                # handled by the dedicated Indic layer below instead.
                if indic.is_indic(ent.text):
                    continue
                span_text = ent.text
                if mapped == "ORGANIZATION" and ent.text.lower() in _STOP_ORG:
                    continue
                if mapped == "ORGANIZATION":
                    # "Thiru Ravi Kumar": the model labels the whole honorific + name
                    # span as an organisation. Strip the honorific so this mention
                    # merges with the one the _HONORIFIC_PERSON rule already found,
                    # instead of creating an ORGANIZATION node for a person.
                    first, _, rest = ent.text.strip().partition(" ")
                    if first.strip(".,").lower() in _HONORIFIC_WORDS and rest.strip():
                        mapped, span_text = "PERSON", rest.strip()
                    elif _looks_like_place(ent.text):
                        # "Wall Tax Road" / "Guindy Industrial Estate": an address is a
                        # LOCATION in this schema, not an institution
                        mapped = "LOCATION"
                add(mapped, span_text, f"ner:{_NLP_BACKEND}", ent.start_char, ent.end_char, 0.75)
        except Exception:
            pass

    # --- gazetteer layer (known case locations / organizations) ------------
    if gazetteer:
        low = text.lower()
        for etype, values in gazetteer.items():
            for value in values:
                idx = low.find(value.lower())
                if idx >= 0:
                    # keep the known vocabulary label verbatim ("Coimbatore RS Puram",
                    # not title-cased "Coimbatore Rs Puram") so graph labels stay stable
                    add(etype, value, "gazetteer", idx, idx + len(value), 0.85, canonical=value)

    # --- Indic script layer (Devanagari / Tamil) ---------------------------
    indic_notes: list[dict[str, Any]] = []
    if indic.is_indic(text):
        # 4a. date vocabulary - Hindi/Tamil month names -> canonical English form
        for d in indic.extract_indic_dates(text):
            add("DATE", d["surface"], "indic-date-vocabulary", d["start"], d["end"], 0.85,
                canonical=d["canonical"])
            indic_notes.append({**d, "layer": "indic-date-vocabulary"})

        # 4b. lexical match against the known entity vocabulary (transliterate
        #     -> fuzzy match). No name is hard-coded: the vocabulary is the graph.
        #
        #     The sentence structure tells us which entity type this phrase SHOULD
        #     be, and that type is passed to the matcher: a locative postposition
        #     means LOCATION, an accusative/ergative one or sentence-initial subject
        #     position means PERSON. With a known type, a match against a DIFFERENT
        #     type must clear a materially higher bar and be plausible for that type
        #     (see indic.match_vocabulary / _surface_supports_type) - this is what
        #     stops a personal name being filed as an organisation.
        vocab = {k: list(v) for k, v in (gazetteer or {}).items() if v}
        structural = indic.candidate_mentions(text) + indic.sentence_initial_subjects(text)
        hint_by_offset = {(c["start"], c["end"]): c["entity_type"] for c in structural}
        for chunk in indic.phrase_chunks(text):
            surface, start, end = chunk["surface"], chunk["start"], chunk["end"]
            preferred = hint_by_offset.get((start, end))
            if preferred is None and chunk["following"] in set(indic._LOCATIVE_MARKERS):
                preferred = "LOCATION"
            elif preferred is None and chunk["following"] in set(indic._ACCUSATIVE_MARKERS):
                preferred = "PERSON"
            hit = indic.match_vocabulary(surface, vocab, preferred_type=preferred) if vocab else None
            if hit:
                add(hit["entity_type"], surface, "indic-transliteration+vocabulary",
                    start, end, 0.82, canonical=hit["canonical"])
                indic_notes.append({"layer": "indic-transliteration+vocabulary",
                                    "surface": surface, "canonical": hit["canonical"],
                                    "entity_type": hit["entity_type"], "score": hit["score"],
                                    "preferred_type": preferred,
                                    "match_kind": hit.get("match_kind")})

        # 4c. structural fallback - postposition pattern and sentence-initial
        #     subject position, LOW confidence, only for phrases the vocabulary did
        #     not already cover. The English rule layer already treats a
        #     sentence-initial proper noun as the subject; this mirrors it for Indic
        #     text, where the subject precedes the verb and carries no case marker.
        covered = {(n.get("surface") or "") for n in indic_notes if n.get("canonical")}
        structural_seen: set[tuple[str, str]] = set()
        for cand in structural:
            if cand["surface"] in covered:
                continue
            # A phrase can satisfy two structural hints (a sentence-initial subject
            # that is also followed by an accusative marker). Counting it twice would
            # push a structural candidate's confidence above the LOW band, so it is
            # recorded once.
            if (cand["entity_type"], cand["surface"]) in structural_seen:
                continue
            structural_seen.add((cand["entity_type"], cand["surface"]))
            roman = indic.romanise(cand["surface"])
            add(cand["entity_type"], cand["surface"], f"indic-structural ({cand['hint']})",
                cand["start"], cand["end"], 0.55, canonical=roman.title() if roman else None)
            indic_notes.append({"layer": "indic-structural", **cand, "romanised": roman})

    # alias heuristic: abbreviated person forms like "R. Kumar" / "Ravi K."
    # PHASE 3: the pattern alone also fires on form-structure artifacts, because
    # institutional vocabulary has the same shape ("(c) Outside P.S. limits",
    # "Chennai Central P.S.", "U.D. Case No."). Each match is therefore checked
    # against the abbreviation / form-noun lists below before it is accepted.
    for m in _alias_candidates(text):
        surface = m.group(0)
        before = text[max(0, m.start() - 24):m.start()]
        after = text[m.end():m.end() + 24]
        if not _alias_is_plausible(surface, before, after):
            continue
        add("ALIAS", surface, "alias-pattern", m.start(), m.end(), 0.7)

    return reconcile_entities(list(found.values()), gazetteer)


def extract_events(text: str, entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sentence-scoped event extraction: trigger verb + participating entities."""
    events: list[dict[str, Any]] = []
    # Do not split after a single-capital-letter initial ("R. Kumar", "Ravi K. was"):
    # doing so severed the subject from its predicate and destroyed the very
    # co-occurrence the relationship is derived from.
    sentences = [s.strip() for s in
                 re.split(r"(?<![A-Z]\.)(?<=[.!?\u0964])\s*|\n+", text) if s.strip()]
    for idx, sent in enumerate(sentences):
        low = sent.lower()
        trigger = next((t for t in EVENT_TRIGGERS if t in low), None)
        event_type = EVENT_TRIGGERS[trigger] if trigger else None
        if trigger is None:
            # Indic observation verbs (देखा गया / காணப்பட்டார்) carry the same
            # evidential weight as their English counterparts.
            indic_trigger = indic.observation_trigger(sent)
            if indic_trigger:
                trigger, event_type = indic_trigger, "OBSERVATION"
        if trigger is None:
            continue
        participants = [e for e in entities
                        if any(e["surface"].lower() in low or e["normalized"].lower() in low
                               for _ in [0])]
        dates = [e["normalized"] for e in participants if e["entity_type"] == "DATE"]
        times = [e["normalized"] for e in participants if e["entity_type"] == "TIME"]
        locations = [e["normalized"] for e in participants if e["entity_type"] == "LOCATION"]
        # Organisations and devices are participants too: "Coastal Logistics Pvt Ltd
        # ... at Chennai Port" and "IMEI ... present with R. Kumar" are exactly the
        # associations an investigator needs to see.
        actors = [e["normalized"] for e in participants
                  if e["entity_type"] in {"PERSON", "ALIAS", "VEHICLE", "PHONE", "ACCOUNT",
                                          "DEVICE", "ORGANIZATION"}]
        if not actors:
            continue
        events.append({
            "sentence_index": idx,
            "event_type": event_type,
            "language": "INDIC" if indic.is_indic(sent) else "LATIN",
            "trigger": trigger,
            "text": sent,
            "actors": actors[:8],
            "locations": locations[:4],
            "dates": dates[:3],
            "times": times[:3],
        })
    return events


def run(text: str, gazetteer: Optional[dict[str, Iterable[str]]] = None) -> dict[str, Any]:
    entities = extract_entities(text, gazetteer)
    events = extract_events(text, entities)
    counts: dict[str, int] = {}
    for e in entities:
        counts[e["entity_type"]] = counts.get(e["entity_type"], 0) + 1
    return {
        "agent": AGENT_NAME,
        "backend": backend_info(),
        "entities": entities,
        "events": events,
        "counts": counts,
        "scripts": indic.script_summary(text),
        "sufficient": bool(entities),
        "note": ("No entities could be extracted - INSUFFICIENT EVIDENCE for entity-level analysis."
                 if not entities else ""),
    }
