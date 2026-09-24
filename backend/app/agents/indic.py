"""INDIC SCRIPT LAYER - deterministic Devanagari / Tamil handling for extraction.

Why this module exists
----------------------
spaCy's `en_core_web_sm` pipeline is trained on Latin-script English and labels
nothing in Devanagari or Tamil text, and a rule layer built on `[A-Za-z]` deletes
Indic names entirely. Rather than silently returning nothing for Indian-language
documents, this module provides an explicitly-scoped, offline, deterministic path:

  1. SCRIPT DETECTION   - Unicode-range census (always reliable, no model needed).
  2. ROMANISATION       - reversible Devanagari/Tamil -> Latin transliteration
                          (ISO-15919-lite, tuned to Indian-English spellings),
                          with optional word-final schwa deletion.
  3. LEXICAL MATCHING   - romanised Indic mentions are fuzzy-matched against the
                          *known entity vocabulary* already in the knowledge graph
                          (person labels/aliases, location and organisation names).
                          No name is hard-coded here.
  4. STRUCTURAL HINTS   - postposition / case-marker heuristics (को, ने, में, पर /
                          இல், உடன்) used when the vocabulary contains no match.
  5. DATE RESOLUTION    - Devanagari and Tamil month names resolved to the same
                          canonical form the English DATE rule layer emits.

HONEST SCOPE STATEMENT
-----------------------
This is NOT a trained Indic NER model. It recovers mentions that either (a) match a
known entity in the case graph, or (b) match Indic date/month vocabulary and
postposition structure. Free-text Indic narrative that names an entity absent from
the vocabulary will yield a LOW-confidence structural candidate rather than a
confident extraction. The agent reports which layer produced every mention
(`methods`) so the limitation is visible rather than hidden.

No dependency outside the declared stack is used: pure Python + `unicodedata`.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any, Iterable, Optional

# --------------------------------------------------------------------------
# 1. Script census
# --------------------------------------------------------------------------
_SCRIPT_RANGES: dict[str, tuple[tuple[int, int], ...]] = {
    "latin": ((0x0041, 0x007A), (0x00C0, 0x024F)),
    "devanagari": ((0x0900, 0x097F), (0xA8E0, 0xA8FF)),
    "tamil": ((0x0B80, 0x0BFF),),
    "bengali": ((0x0980, 0x09FF),),
    "gurmukhi": ((0x0A00, 0x0A7F),),
    "telugu": ((0x0C00, 0x0C7F),),
    "kannada": ((0x0C80, 0x0CFF),),
    "malayalam": ((0x0D00, 0x0D7F),),
}


def script_census(text: str) -> dict[str, int]:
    """Count letters per script. Whitespace, digits and punctuation are ignored."""
    census: dict[str, int] = {}
    for ch in text:
        if not ch.isalpha():
            continue
        cp = ord(ch)
        for name, ranges in _SCRIPT_RANGES.items():
            if any(lo <= cp <= hi for lo, hi in ranges):
                census[name] = census.get(name, 0) + 1
                break
        else:
            census["other"] = census.get("other", 0) + 1
    return census


def dominant_script(text: str) -> str:
    census = {k: v for k, v in script_census(text).items() if k != "other"}
    if not census:
        return "unknown"
    return max(census, key=lambda k: census[k])


# --------------------------------------------------------------------------
# 2. Romanisation
# --------------------------------------------------------------------------
# Devanagari ---------------------------------------------------------------
_DEV_INDEPENDENT_VOWELS = {
    "\u0904": "a", "\u0905": "a", "\u0906": "aa", "\u0907": "i", "\u0908": "ii",
    "\u0909": "u", "\u090A": "uu", "\u090B": "ri", "\u0960": "ri", "\u090C": "lri",
    "\u090D": "e", "\u090E": "e", "\u090F": "e", "\u0910": "ai",
    "\u0911": "o", "\u0912": "o", "\u0913": "o", "\u0914": "au",
}
_DEV_MATRAS = {
    "\u093E": "aa", "\u093F": "i", "\u0940": "ii", "\u0941": "u", "\u0942": "uu",
    "\u0943": "ri", "\u0944": "ri", "\u0962": "lri", "\u0963": "lri",
    "\u0945": "e", "\u0946": "e", "\u0947": "e", "\u0948": "ai",
    "\u0949": "o", "\u094A": "o", "\u094B": "o", "\u094C": "au",
}
_DEV_CONSONANTS = {
    "\u0915": "k", "\u0916": "kh", "\u0917": "g", "\u0918": "gh", "\u0919": "ng",
    "\u091A": "ch", "\u091B": "chh", "\u091C": "j", "\u091D": "jh", "\u091E": "ny",
    "\u091F": "t", "\u0920": "th", "\u0921": "d", "\u0922": "dh", "\u0923": "n",
    "\u0924": "t", "\u0925": "th", "\u0926": "d", "\u0927": "dh", "\u0928": "n",
    "\u0929": "n", "\u092A": "p", "\u092B": "ph", "\u092C": "b", "\u092D": "bh",
    "\u092E": "m", "\u092F": "y", "\u0930": "r", "\u0931": "r", "\u0932": "l",
    "\u0933": "l", "\u0934": "l", "\u0935": "v", "\u0936": "sh", "\u0937": "sh",
    "\u0938": "s", "\u0939": "h",
    # nukta forms (Urdu-derived sounds)
    "\u0958": "k", "\u0959": "kh", "\u095A": "g", "\u095B": "z", "\u095C": "r",
    "\u095D": "rh", "\u095E": "f", "\u095F": "y",
}
_DEV_VIRAMA = {"\u094D"}
_DEV_MODIFIERS = {"\u0901": "n", "\u0902": "n", "\u0903": "h", "\u093C": "", "\u0951": "",
                  "\u0952": "", "\u0953": "", "\u0954": ""}

# Tamil --------------------------------------------------------------------
_TAM_INDEPENDENT_VOWELS = {
    "\u0B85": "a", "\u0B86": "aa", "\u0B87": "i", "\u0B88": "ii", "\u0B89": "u",
    "\u0B8A": "uu", "\u0B8E": "e", "\u0B8F": "ee", "\u0B90": "ai",
    "\u0B92": "o", "\u0B93": "oo", "\u0B94": "au",
}
_TAM_MATRAS = {
    "\u0BBE": "aa", "\u0BBF": "i", "\u0BC0": "ii", "\u0BC1": "u", "\u0BC2": "uu",
    "\u0BC6": "e", "\u0BC7": "ee", "\u0BC8": "ai", "\u0BCA": "o", "\u0BCB": "oo",
    "\u0BCC": "au",
}
_TAM_CONSONANTS = {
    "\u0B95": "k", "\u0B99": "ng", "\u0B9A": "ch", "\u0B9E": "ny", "\u0B9F": "t",
    "\u0BA3": "n", "\u0BA4": "t", "\u0BA8": "n", "\u0BA9": "n", "\u0BAA": "p",
    "\u0BAE": "m", "\u0BAF": "y", "\u0BB0": "r", "\u0BB1": "r", "\u0BB2": "l",
    "\u0BB3": "l", "\u0BB4": "zh", "\u0BB5": "v", "\u0BB6": "sh", "\u0BB7": "sh",
    "\u0BB8": "s", "\u0BB9": "h", "\u0B9C": "j",
}
_TAM_VIRAMA = {"\u0BCD"}
_TAM_MODIFIERS = {"\u0B82": "", "\u0BB0\u0BC1": ""}  # ayutha ezhuthu + ligature

_ROMANISERS = {
    "devanagari": (_DEV_INDEPENDENT_VOWELS, _DEV_MATRAS, _DEV_CONSONANTS, _DEV_VIRAMA, _DEV_MODIFIERS),
    "tamil": (_TAM_INDEPENDENT_VOWELS, _TAM_MATRAS, _TAM_CONSONANTS, _TAM_VIRAMA, _TAM_MODIFIERS),
}


def _romanise_run(run: str, script: str, drop_final_schwa: bool) -> str:
    vowels, matras, cons, viramas, modifiers = _ROMANISERS[script]
    out: list[str] = []
    pending_consonant = False
    reached_end = False
    for idx, ch in enumerate(run):
        if ch in viramas:
            pending_consonant = False
            continue
        if ch in matras:
            out.append(matras[ch])
            pending_consonant = False
            continue
        if ch in cons:
            if pending_consonant:
                out.append("a")
            out.append(cons[ch])
            pending_consonant = True
            continue
        if ch in vowels:
            if pending_consonant and not (drop_final_schwa and idx == len(run) - 1):
                out.append("a")
            out.append(vowels[ch])
            pending_consonant = False
            continue
        if ch in modifiers:
            out.append(modifiers[ch])
            pending_consonant = False
            continue
        # unknown symbol inside the run: flush inherent vowel, copy through
        if pending_consonant:
            out.append("a")
            pending_consonant = False
        out.append(ch)
        reached_end = True
    if pending_consonant and not (drop_final_schwa and not reached_end):
        out.append("a")
    return "".join(out)


_RUN_SPLIT = re.compile(r"([^\u0900-\u097F\u0B80-\u0BFF]+)")


def romanisations(text: str, script: Optional[str] = None) -> list[str]:
    """Return [strict, word-final-schwa-deleted] romanisations of Indic text.

    Both variants are produced because Hindi schwa deletion is not exceptionless
    (वाहन -> "vahan" but कुमार -> "kumar"); the matcher scores against both.
    """
    script = script or dominant_script(text)
    if script not in _ROMANISERS:
        return [text]
    results = []
    for drop in (False, True):
        parts = _RUN_SPLIT.split(text)
        pieces = []
        for i, part in enumerate(parts):
            if i % 2 == 1:
                pieces.append(part)
            elif part:
                pieces.append(_romanise_run(part, script, drop))
        results.append(re.sub(r"\s+", " ", "".join(pieces)).strip())
    return results


def romanise(text: str, script: Optional[str] = None, drop_final_schwa: bool = False) -> str:
    return romanisations(text, script)[1 if drop_final_schwa else 0]


# --------------------------------------------------------------------------
# 3. Evidence-vocabulary matching
# --------------------------------------------------------------------------
def _phonetic_key(token: str) -> str:
    """Consonant-class skeleton, used as a strong-equivalence bonus signal."""
    token = re.sub(r"[^a-z]", "", token.lower())
    token = re.sub(r"(.)\1+", r"\1", token)          # collapse geminates
    classes = {
        "k": "k", "c": "k", "q": "k", "g": "k",       # velars
        "j": "j", "z": "j",                            # palatals / sibilant voiced
        "t": "t", "d": "t",                            # dentals/retroflexes
        "n": "n", "m": "n",                            # nasals
        "p": "p", "b": "p", "f": "p", "v": "p",       # labials
        "s": "s", "x": "s",                            # sibilants
        "r": "r", "l": "l", "y": "y", "h": "h", "w": "p",
    }
    return "".join(classes.get(ch, "") for ch in token if not ch.isdigit())


_LONG_VOWEL_FOLDS = (("aa", "a"), ("ii", "i"), ("uu", "u"), ("ee", "e"), ("oo", "o"))


def fold_vowels(text: str) -> str:
    """Collapse long/short vowel distinctions. Applied to BOTH sides of a
    comparison only - it makes "kumaar" and "kumar" equivalent for matching while
    the stored romanisation stays faithful to the source script."""
    out = (text or "").lower()
    for long, short in _LONG_VOWEL_FOLDS:
        out = out.replace(long, short)
    return out


def _alignment_score(a: str, b: str) -> float:
    """Max of whole-string fuzzy ratios and a per-token best-alignment mean.

    Per-token alignment matters for Indic romanisation because word boundaries
    survive transliteration but spelling conventions do not ("sentrl" vs "central").
    """
    try:
        from rapidfuzz import fuzz
    except Exception:  # pragma: no cover - rapidfuzz is a declared dependency
        return 0.0
    a, b = fold_vowels(a).strip(), fold_vowels(b).strip()
    if not a or not b:
        return 0.0
    if a == b:
        return 100.0
    whole = max(fuzz.ratio(a, b), fuzz.token_sort_ratio(a, b),
                fuzz.token_set_ratio(a, b), fuzz.partial_ratio(a, b))
    ta, tb = a.split(), b.split()
    if ta and tb:
        per_token = sum(max(fuzz.ratio(x, y) for y in tb) for x in ta) / len(ta)
        whole = max(whole, per_token)
    ka, kb = _phonetic_key(a), _phonetic_key(b)
    if ka and ka == kb:
        whole = max(whole, 92.0)
    return round(whole, 2)


def _length_ratio_ok(a: str, b: str, tolerance: float = 0.45) -> bool:
    """Guard against short-token false matches ("Ram" matching "Rameshwaram")."""
    la, lb = len(a.replace(" ", "")), len(b.replace(" ", ""))
    if not max(la, lb):
        return False
    return abs(la - lb) / max(la, lb) <= tolerance


# --------------------------------------------------------------------------
# 3a. Case-suffix stripping (Dravidian agglutination)
# --------------------------------------------------------------------------
# Tamil attaches case markers to the noun ("சென்னை சென்ட்ரலில்" = "at Chennai
# Central"), so the surface that reaches the matcher still carries the suffix and
# scores below threshold against the stored label. These endings are stripped and
# the variant re-romanised. Hindi postpositions are separate tokens and are handled
# by phrase_chunks(), so this list is Tamil-first by design.
_CASE_SUFFIXES = (
    # Tamil - attached case markers use vowel SIGNS (ில் = U+0BBF), not the
    # independent vowel (இ = U+0B87); 'சென்ட்ரலில்' ends with U+0BBF + U+0BB2 + U+0BCD.
    "ிலிருந்து", "லிருந்து", "ில்", "ில", "ின்", "ோடு", "ுடன்", "ை", "க்கு", "ால்",
    "ுக்", "ல்", "கு", "ோ",
    # Hindi - postpositions are separate tokens, kept for robustness
    "में", "मे", "को", "ने", "से", "पर",
)


def surface_variants(surface: str) -> list[str]:
    """The surface itself plus case-suffix-stripped variants worth matching."""
    variants = [surface]
    for suffix in _CASE_SUFFIXES:
        if surface.endswith(suffix) and len(surface) > len(suffix) + 1:
            stem = surface[: -len(suffix)]
            if len(_INDIC_SINGLE.findall(stem)) >= 1 and len(stem.strip()) >= 3:
                variants.append(stem.strip())
    return variants


# --------------------------------------------------------------------------
# 3b. Type-shape gate - the fix for a PERSON phrase matching an ORGANIZATION entry
# --------------------------------------------------------------------------
# A cross-type fuzzy match must be *plausible for that type*, not merely similar.
# Without this gate the matcher returned the best-scoring label regardless of type,
# so a person's name could be tagged ORGANIZATION ("ரவி குமார்" -> "Thiru Ravi
# Kumar", score 100) and the person entity was never created.
_ORG_MARKERS_SURFACE = (
    # Latin
    "pvt", "ltd", "limited", "inc", "corp", "corporation", "company", "co.", "bank",
    "trust", "agency", "department", "bureau", "services", "service", "logistics",
    "spares", "stores", "works", "factory", "mills", "hospital", "college",
    "university", "institute", "authority", "board", "office", "committee",
    "enterprises", "traders", "transport", "industries", "foundation",
    # Devanagari
    "कंपनी", "कम्पनी", "निगम", "संस्था", "प्राइवेट", "लिमिटेड", "बैंक", "विभाग",
    # Tamil
    "நிறுவனம்", "நிறுவனத்தின்", "கம்பெனி", "பிரைவேட்", "லிமிடெட்", "வங்கி",
    "துறை", "அமைப்பு",
)


def _surface_supports_type(surface: str, entity_type: str,
                           romanised: str = "") -> bool:
    """Is `surface` shaped like `entity_type`? Used only for CROSS-type matches."""
    haystack = f"{surface} {romanised}".lower()
    has_org_marker = any(marker.lower() in haystack for marker in _ORG_MARKERS_SURFACE)
    tokens = [t for t in _INDIC_SINGLE.findall(surface) if t not in _stopwords()]
    if entity_type == "ORGANIZATION":
        return has_org_marker
    if entity_type == "PERSON":
        # a business/place name is not a person, and a bare fragment is not either
        return not has_org_marker and 1 <= len(tokens) <= 4
    if entity_type in {"LOCATION", "VEHICLE", "PHONE", "ACCOUNT", "DEVICE"}:
        return True
    return True


# --------------------------------------------------------------------------
# 3c. Vocabulary matching
# --------------------------------------------------------------------------
def match_vocabulary(surface: str, vocabulary: dict[str, Iterable[str]],
                     min_score: float = 80.0,
                     preferred_type: Optional[str] = None,
                     cross_type_min_score: float = 95.0,
                     allow_cross_type: bool = True) -> Optional[dict[str, Any]]:
    """Fuzzy-match an Indic mention against the known entity vocabulary.

    Same-type matches (when `preferred_type` is known from the sentence structure)
    need `min_score`. A match against a DIFFERENT type has to clear a materially
    higher bar (`cross_type_min_score`) *and* be plausible for that type shape, so a
    loose cross-type match never wins over "no match".

    Returns {"entity_type", "canonical", "score", "romanised", "match_kind"} or None.
    """
    best_same: Optional[dict[str, Any]] = None
    best_cross: Optional[dict[str, Any]] = None
    for variant in surface_variants(surface):
        for roman in romanisations(variant):
            if not roman.strip():
                continue
            for etype, labels in vocabulary.items():
                same_type = preferred_type is not None and etype == preferred_type
                for label in labels:
                    score = _alignment_score(roman, label)
                    if score < min_score or not _length_ratio_ok(roman, label):
                        continue
                    if not same_type:
                        # A type-different match is only considered when the surface is
                        # PLAUSIBLE for that type (a person's name is not an
                        # organisation just because the strings are similar) and, when
                        # the sentence structure told us the phrase's own type, it must
                        # additionally clear the higher cross-type bar.
                        if not allow_cross_type:
                            continue
                        if not _surface_supports_type(surface, etype, roman):
                            continue
                        if preferred_type is not None and score < cross_type_min_score:
                            continue
                    candidate = {"entity_type": etype, "canonical": label, "score": score,
                                 "romanised": roman, "stripped_suffix":
                                     variant != surface,
                                 "match_kind": "same-type" if same_type else "cross-type"}
                    if same_type:
                        if best_same is None or score > best_same["score"]:
                            best_same = candidate
                    elif best_cross is None or score > best_cross["score"]:
                        best_cross = candidate
    if best_same is not None:
        return best_same
    return best_cross


# --------------------------------------------------------------------------
# 4. Structural hints (postpositions / case markers)
# --------------------------------------------------------------------------
# Locative / dative / ergative markers that follow a noun phrase.
_LOCATIVE_MARKERS = ("में", "मे", "पर", "இல்", "இல", "மேல்", "उपर")
_ACCUSATIVE_MARKERS = ("को", "ने", "கு", "ஐ", "உடன்", "साथ", "கொண்டு", "இருந்து", "से")
_VEHICLE_WORDS = ("वाहन", "गाड़ी", "गाडी", "कार", "मोटर", "வாகனம்", "கார்", "வண்டி")
_OBSERVATION_WORDS = (
    "देखा", "देखी", "देखे", "गया", "गई", "हुआ", "हुई", "बताया", "लिखा", "मिला",
    "காணப்பட்டார்", "காணப்பட்டது", "காணப்பட்டன", "பார்த்த", "இருந்த", "சென்ற", "வந்த",
    "தெரிவித்தார்", "கூறினார்", "அறியவந்தது",
)
# Letters + vowel signs + matras + virama only: danda (U+0964/5) and Indic
# digits are excluded so they never glue onto a phrase.
_INDIC_ALPHA = "\u0900-\u0963\u0970-\u097F\u0B80-\u0BE5\u0BF0-\u0BF2"
_INDIC_SINGLE = re.compile("[" + _INDIC_ALPHA + "]+")

# Closed-class function words, observation verbs and generic nouns. Chunk
# segmentation splits on these so multi-word phrases ("चेन्नई सेंट्रल") stay intact
# while postpositions ("को", "में") are stripped from the candidate surface.
_FUNCTION_WORDS = {
    # Devanagari - case markers, postpositions, particles
    "का", "की", "के", "को", "ने", "में", "मे", "पर", "से", "साथ", "तक", "ही", "भी",
    "और", "या", "एक", "यह", "वह", "वो", "इस", "उस", "कि", "जो", "नहीं", "कर", "किया",
    "द्वारा", "बाद", "पहले", "नाम", "पता", "स्थान", "तारीख", "दिनांक", "समय",
    # Devanagari - copulas / participles / observation verbs
    "है", "हैं", "था", "थी", "थे", "गया", "गई", "गए", "हुआ", "हुई", "हुए", "रहा", "रही",
    "रहे", "होगा", "देखा", "देखी", "देखे", "बताया", "लिखा", "मिला", "पाया", "आया",
    # Tamil - case markers, postpositions, particles
    "இல்", "இல", "உடன்", "கு", "ஐ", "இருந்து", "ஒரு", "அந்த", "இந்த", "மற்றும்",
    "என்று", "ஆகும்", "பெயர்", "முகவரி", "தேதி", "நேரம்", "என",
    # Tamil - copulas / participles / observation verbs
    "ஆகும்", "ஆவார்", "ஆக", "இருந்த", "இருந்தது", "சென்ற", "வந்த", "காணப்பட்டது",
    "காணப்பட்டார்", "பார்த்த", "தெரிவித்தார்", "கூறினார்", "என்பது",
}
# Vehicle words plus the inflected Tamil forms that appear glued to the following
# noun phrase in FIR narrative ("வாகனத்துடன்" = "with the vehicle").
_VEHICLE_TOKENS = set(_VEHICLE_WORDS) | {
    "வாகனம்", "வாகனத்துடன்", "வாகனத்தில்", "வாகனத்தை", "வாகனத்தின்", "வாகனங்கள்",
    "காரில்", "காருடன்", "வண்டியில்", "वाहनों",
}

# --------------------------------------------------------------------------
# Common nouns that are NEVER a person's name.
#
# FIR narrative is written in short factual sentences, so a common noun lands in
# sentence-initial position all the time: "फोन +919840012345 दर्ज किया गया।"
# ("the phone ... was recorded"). The structural rule below would otherwise read
# that noun as the subject - i.e. as a PERSON - because it sits at a sentence
# boundary and the sentence contains an observation verb.
#
# Same convention as _VEHICLE_WORDS: a module-level tuple of bare surface forms,
# matched as EXACT tokens (never as prefixes or substrings). Exact matching keeps
# two failure modes away: a real name that merely contains one of these strings
# is untouched, and an inflected form we did not list simply falls through to the
# existing conservative checks rather than being silently dropped.
#
# A leading stoplist token is stripped rather than the whole phrase being
# discarded, so "आरोपी रवि कुमार" still yields the person "रवि कुमार".
_SUBJECT_STOPLIST = (
    # --- Devanagari: devices and telecom objects ---------------------------------
    "फोन", "फ़ोन", "मोबाइल", "मोबाइलफोन", "मोबाइल फोन", "नंबर", "नम्बर", "कॉल", "संदेश",
    "एसएमएस", "सिम", "इंटरनेट", "डिवाइस",
    # --- Devanagari: records, documents, role nouns ------------------------------
    "खाता", "बैंक", "राशि", "लेनदेन", "हस्तांतरण", "विवरण", "जानकारी", "शिकायत",
    "रिपोर्ट", "प्रतिवेदन", "पंजीकरण", "अभिलेख", "साक्ष्य", "गवाह", "मामला", "प्रकरण",
    "घटना", "जांच", "जाँच", "अभियोग", "आरोपी", "आरोप", "मुल्जिम", "शिकायतकर्ता",
    "दस्तावेज", "कागजात", "प्रविष्टि", "टिप्पणी", "सूचना",
    # --- Tamil: devices and telecom objects --------------------------------------
    "செல்போன்", "போன்", "தொலைபேசி", "கைபேசி", "அலைபேசி", "எண்", "இலக்கம்", "செய்தி",
    "குறுஞ்செய்தி", "சிம்", "இணையம்",
    # --- Tamil: records, documents, role nouns -----------------------------------
    "கணக்கு", "வங்கி", "பணம்", "தொகை", "பரிவர்த்தனை", "விவரம்", "தகவல்", "புகார்",
    "அறிக்கை", "வழக்கு", "சாட்சி", "ஆவணம்", "நிகழ்வு", "விசாரணை", "குற்றம்", "நபர்",
    "மனு", "ஆட்சேபனை", "பதிவு", "குறிப்பு", "அறிவிப்பு",
)
_STOPWORDS_CACHE: "set[str] | None" = None
_MAX_PHRASE_TOKENS = 4


def _stopwords() -> set[str]:
    """Function words + vehicle nouns + month names (months are handled by the
    date layer, not as entity phrases). Built lazily because the month table is
    declared further down."""
    global _STOPWORDS_CACHE
    if _STOPWORDS_CACHE is None:
        _STOPWORDS_CACHE = _FUNCTION_WORDS | set(_VEHICLE_WORDS) | set(_MONTH_NAMES)
    return _STOPWORDS_CACHE


def _indic_tokens(text: str) -> list[tuple[str, int, int]]:
    return [(m.group(0), m.start(), m.end()) for m in _INDIC_SINGLE.finditer(text)]


def phrase_chunks(text: str) -> list[dict[str, Any]]:
    """Extract candidate noun phrases: maximal runs of Indic *content* words.

    Function words / verbs / generic nouns act as boundaries, and a non-Indic
    character (digit, latin word, punctuation) breaks a chunk. Each chunk also
    records the following function word so structural hints can use it.
    """
    tokens = _indic_tokens(text)
    chunks: list[dict[str, Any]] = []
    current: list[tuple[str, int, int]] = []

    def flush(next_word: str) -> None:
        if current:
            words = [t[0] for t in current]
            chunks.append({
                "surface": text[current[0][1]:current[-1][2]],
                "start": current[0][1], "end": current[-1][2],
                "tokens": words, "following": next_word,
            })
            current.clear()

    for idx, (tok, start, end) in enumerate(tokens):
        next_tok = tokens[idx + 1][0] if idx + 1 < len(tokens) else ""
        next_start = tokens[idx + 1][1] if idx + 1 < len(tokens) else len(text)
        if tok in _stopwords() or len(tok) < 2:
            flush(tok)
            continue
        # "வாகனத்துடன்" (vehicle+with) / "வாகனம்" glue a vehicle word onto the next
        # noun phrase; treat such a token as a boundary so the following place name
        # stays a chunk of its own.
        if tok in _VEHICLE_TOKENS:
            flush(tok)
            continue
        if current and start - current[-1][2] > 2:
            flush("")
        if len(current) >= _MAX_PHRASE_TOKENS:
            flush("")
        # a chunk must not straddle a sentence break
        if current and re.search(r"[।.!?\n]", text[current[-1][2]:start]):
            flush("")
        current.append((tok, start, end))
        if next_tok in _stopwords():
            flush(next_tok)
        elif not next_tok and next_start == len(text):
            flush("")
    flush("")
    return chunks


def token_runs(text: str, min_tokens: int = 1) -> list[tuple[str, int, int]]:
    """Backwards-compatible raw Indic token runs (no function-word segmentation)."""
    return [(c["surface"], c["start"], c["end"]) for c in phrase_chunks(text)
            if len(c["tokens"]) >= min_tokens]


def candidate_mentions(text: str) -> list[dict[str, Any]]:
    """Structural candidates from postposition structure, used when a phrase does
    not match the known vocabulary. LOW confidence by construction."""
    locative = set(_LOCATIVE_MARKERS)
    accusative = set(_ACCUSATIVE_MARKERS)
    out: list[dict[str, Any]] = []
    for chunk in phrase_chunks(text):
        following = chunk["following"]
        if following in locative and len(chunk["tokens"]) >= 1:
            # "मोबाइल फोन ... पर" / "செல்போன் ... இல்" is a device, not a place: a
            # chunk made up only of common nouns never becomes a LOCATION.
            if all(t in _SUBJECT_STOPLIST for t in chunk["tokens"]):
                continue
            out.append({"entity_type": "LOCATION", "surface": chunk["surface"],
                        "start": chunk["start"], "end": chunk["end"],
                        "hint": "locative postposition"})
        elif following in accusative and len(chunk["tokens"]) >= 2:
            out.append({"entity_type": "PERSON", "surface": chunk["surface"],
                        "start": chunk["start"], "end": chunk["end"],
                        "hint": "accusative/ergative postposition"})
    return out


def _sentence_start(text: str, index: int) -> bool:
    prefix = text[:index].rstrip()
    return not prefix or prefix[-1] in "।.!?\n"


def sentence_initial_subjects(text: str, max_tokens: int = 3) -> list[dict[str, Any]]:
    """Sentence-initial Indic noun phrases -> LOW-confidence PERSON candidates.

    The English rule layer already treats a sentence-initial proper noun as the
    subject (of an observation/action verb). Indic text needs the same rule,
    because `candidate_mentions()` only proposes PERSON when an accusative/ergative
    marker FOLLOWS the phrase - and a subject at the start of a sentence precedes
    the verb instead, so it produced no candidate at all.

    Deliberately conservative: the phrase must be at a sentence boundary, be 1-3
    content tokens, not be an organisation (marker word) or a place-with-locative,
    and the sentence must contain an observation/action trigger or the phrase must
    be followed by an accusative/ergative marker.

    A leading common noun is stripped before that decision ("फोन +91..." -> nothing
    left -> no candidate; "आरोपी रवि कुमार" -> "रवि कुमार"), because a device,
    document or role noun in sentence-initial position is not a person's name.
    """
    out: list[dict[str, Any]] = []
    for chunk in phrase_chunks(text):
        if not _sentence_start(text, chunk["start"]):
            continue
        surface = chunk["surface"]
        start = chunk["start"]
        words = list(chunk["tokens"])
        while words and words[0] in _SUBJECT_STOPLIST:
            surface = surface[len(words[0]):]
            start += len(words[0])
            lead = len(surface) - len(surface.lstrip())
            surface = surface.lstrip()
            start += lead
            words = words[1:]
        tokens = [t for t in words if t not in _stopwords()]
        if not tokens or len(tokens) > max_tokens:
            continue
        following = chunk["following"]
        if following in set(_LOCATIVE_MARKERS):
            continue                       # that is a LOCATION hint, handled separately
        if any(marker.lower() in surface.lower() for marker in _ORG_MARKERS_SURFACE):
            continue                       # an organisation name, not a person
        if not (observation_trigger(text) or following in set(_ACCUSATIVE_MARKERS)):
            continue
        out.append({"entity_type": "PERSON", "surface": surface,
                    "start": start, "end": chunk["end"],
                    "hint": "sentence-initial subject"})
    return out


def is_indic_trigger(token: str) -> bool:
    return any(token.startswith(word) or word in token for word in _OBSERVATION_WORDS + _VEHICLE_WORDS)


def observation_trigger(sentence: str) -> Optional[str]:
    """Indic observation verb acting as an event trigger, if present.

    "देखा गया" / "कாணப்பட்டார்" are the Indic equivalents of "was observed" - they
    carry the same evidential meaning, so they raise the same OBSERVATION event.
    """
    for word in _OBSERVATION_WORDS:
        if word in sentence:
            return word
    return None


# --------------------------------------------------------------------------
# 5. Month / date vocabulary
# --------------------------------------------------------------------------
_MONTH_NAMES: dict[str, int] = {
    # English
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7, "aug": 8, "sep": 9,
    "sept": 9, "oct": 10, "nov": 11, "dec": 12,
    # Devanagari (with common spelling variants)
    "जनवरी": 1, "फरवरी": 2, "फ़रवरी": 2, "मार्च": 3, "अप्रैल": 4, "अप्रेल": 4, "मई": 5,
    "जून": 6, "जुलाई": 7, "अगस्त": 8, "सितंबर": 9, "सितम्बर": 9, "सितम्भर": 9,
    "अक्तूबर": 10, "अक्टूबर": 10, "अक्टुबर": 10, "नवंबर": 11, "नवम्बर": 11,
    "दिसंबर": 12, "दिसम्बर": 12,
    # Tamil
    "ஜனவரி": 1, "பிப்ரவரி": 2, "மார்ச்": 3, "மார்ச": 3, "ஏப்ரல்": 4, "மே": 5,
    "ஜூன்": 6, "ஜூலை": 7, "ஆகஸ்ட்": 8, "ஆகஸ்ட": 8, "செப்டம்பர்": 9, "செப்டெம்பர்": 9,
    "அக்டோபர்": 10, "அக்டோபர்": 10, "நவம்பர்": 11, "டிசம்பர்": 12,
}

_MONTH_LABELS = ["January", "February", "March", "April", "May", "June", "July",
                 "August", "September", "October", "November", "December"]

_MONTH_ALT = "|".join(sorted((re.escape(m) for m in _MONTH_NAMES), key=len, reverse=True))
_DATE_WITH_DAY = re.compile(r"(\d{1,2})\s*(" + _MONTH_ALT + r")")
_DATE_WITH_DAY_REV = re.compile(r"(" + _MONTH_ALT + r")\s*(\d{1,2})")
_YEAR_NEAR = re.compile(r"(20\d{2})")


def extract_indic_dates(text: str) -> list[dict[str, Any]]:
    """Resolve Devanagari/Tamil month names into the canonical English form the
    Latin DATE layer already emits (e.g. "12 August"), plus an ISO value when a
    year is present anywhere in the same sentence."""
    out: list[dict[str, Any]] = []
    for match in _DATE_WITH_DAY.finditer(text):
        day, month_token = int(match.group(1)), match.group(2)
        month = _MONTH_NAMES.get(month_token.lower()) or _MONTH_NAMES.get(month_token)
        if not month or not 1 <= day <= 31:
            continue
        out.append(_date_record(day, month, match.start(), match.end(), text, match.group(0)))
    for match in _DATE_WITH_DAY_REV.finditer(text):
        month_token, day = match.group(1), int(match.group(2))
        month = _MONTH_NAMES.get(month_token.lower()) or _MONTH_NAMES.get(month_token)
        if not month or not 1 <= day <= 31:
            continue
        if any(m["start"] == match.start() for m in out):
            continue
        out.append(_date_record(day, month, match.start(), match.end(), text, match.group(0)))
    return out


def _date_record(day: int, month: int, start: int, end: int, text: str,
                 surface: str) -> dict[str, Any]:
    window = text[max(0, start - 40):end + 40]
    year_match = _YEAR_NEAR.search(window)
    canonical = f"{day} {_MONTH_LABELS[month - 1]}"
    iso = (f"{year_match.group(1)}-{month:02d}-{day:02d}" if year_match else f"{month:02d}-{day:02d}")
    return {"surface": surface.strip(), "canonical": canonical, "iso": iso,
            "day": day, "month": month, "start": start, "end": end}


def is_indic(text: str, min_letters: int = 2) -> bool:
    census = script_census(text)
    return sum(v for k, v in census.items() if k not in {"latin", "other"}) >= min_letters


def script_summary(text: str) -> dict[str, Any]:
    census = script_census(text)
    return {
        "scripts": census,
        "dominant": dominant_script(text),
        "indic_present": is_indic(text),
    }
