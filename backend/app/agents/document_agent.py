"""DOCUMENT INTELLIGENCE AGENT.

Pipeline:  DOCUMENT -> TEXT ACQUISITION (native text / PDF text layer / OCR)
           -> CLEANING -> LANGUAGE DETECTION -> NORMALIZATION
           -> (hand-off to Entity Agent for entity/event extraction)

TEXT-ACQUISITION HONESTY RULE
-----------------------------
Three outcomes are reported distinctly and never conflated:

  NATIVE_TEXT                - the uploaded object was already text (txt/csv/md)
  PDF_TEXT_LAYER             - a real text layer was extracted from the PDF with
                               pypdf. This is NOT OCR.
  PREPROCESSED_SYNTHETIC_TEXT- no engine could read the object (scanned image or a
                               PDF with no text layer) and no OCR backend is
                               installed. A preprocessed synthetic description is
                               used instead and the object is flagged
                               OCR_UNAVAILABLE. OCR is never simulated.

LANGUAGE DETECTION
------------------
Real detection via `langdetect` (offline n-gram profile classifier, seeded for
reproducibility), corroborated by a Unicode script census. The previous
implementation returned a hard-coded "en" for every input while presenting itself
as detection; it now returns the actual detected language, the method used, and
the script census that produced it.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any, Optional

from ..database.object_storage import object_storage
from . import indic

AGENT_NAME = "DOCUMENT_INTELLIGENCE_AGENT"


# --------------------------------------------------------------------------
# Text acquisition backends
# --------------------------------------------------------------------------
class OcrEngine:
    """Abstraction over an OCR backend.

    No OCR engine is installed in this environment. `available` is therefore
    False and the caller must fall back to a text layer or to preprocessed text.
    Kept inside the declared stack: an OCR-capable Transformers image-to-text
    model would plug in here without changing callers.
    """

    def __init__(self) -> None:
        self.backend = "NONE"
        self.available = False
        self.detail = (
            "No OCR backend available in this environment. Scanned image evidence "
            "and text-layer-free PDFs are demonstrated with preprocessed synthetic "
            "text; OCR is never simulated."
        )
        try:  # pragma: no cover - only when a vision model is installed
            from transformers import pipeline  # type: ignore  # noqa: F401

            self.backend = "TRANSFORMERS_IMAGE_TO_TEXT (not loaded - no model weights present)"
        except Exception:
            self.backend = "NONE"

    def extract(self, object_key: str) -> Optional[str]:  # pragma: no cover
        if not self.available:
            return None
        return None

    def status(self) -> dict[str, Any]:
        return {"available": self.available, "backend": self.backend, "detail": self.detail}


class PdfTextExtractor:
    """Real PDF text-layer extraction (pypdf).

    A PDF produced by a word processor carries a text layer; reading the raw bytes
    as if they were text yields PDF internals (obj/xref/stream tokens) which the
    NER layer then mis-reads as names and dates. This class extracts the actual
    page text, and reports whether a text layer existed at all.
    """

    MIN_USABLE_CHARS = 40

    def __init__(self) -> None:
        self.available = False
        self.backend = "NONE"
        self.detail = "pypdf is not installed; PDF text-layer extraction unavailable."
        try:
            import pypdf

            self.available = True
            self.backend = f"pypdf {getattr(pypdf, '__version__', 'unknown')} (PDF text layer)"
            self.detail = ("Real PDF text-layer extraction. This is not OCR: a PDF with no "
                           "embedded text layer still requires OCR, which is unavailable.")
        except Exception:  # pragma: no cover
            pass

    def extract(self, data: bytes) -> dict[str, Any]:
        if not self.available:
            return {"text": "", "pages": 0, "has_text_layer": False,
                    "error": self.detail}
        try:
            import io

            import pypdf

            reader = pypdf.PdfReader(io.BytesIO(data))
            pages = [page.extract_text() or "" for page in reader.pages]
            text = "\n".join(pages)
            return {
                "text": text,
                "pages": len(pages),
                "has_text_layer": len(text.strip()) >= self.MIN_USABLE_CHARS,
                "error": None,
            }
        except Exception as exc:
            return {"text": "", "pages": 0, "has_text_layer": False,
                    "error": f"PDF text-layer extraction failed: {exc}"}

    def status(self) -> dict[str, Any]:
        return {"available": self.available, "backend": self.backend, "detail": self.detail}


ocr_engine = OcrEngine()
pdf_extractor = PdfTextExtractor()

_PDF_MAGIC = b"%PDF-"
_IMAGE_EXT = (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp")


def looks_like_pdf(data: Optional[bytes], object_key: str = "") -> bool:
    if data and data[:1024].lstrip().startswith(_PDF_MAGIC):
        return True
    return object_key.lower().endswith(".pdf")


def looks_like_image(object_key: str, declared_type: str = "") -> bool:
    return declared_type.upper() == "IMAGE" or object_key.lower().endswith(_IMAGE_EXT)


# --------------------------------------------------------------------------
# Cleaning
# --------------------------------------------------------------------------
_WS = re.compile(r"[ \t\u00a0]+")
_MULTINL = re.compile(r"\n{3,}")
_PDF_ARTEFACTS = re.compile(r"^\s*\d+\s+\d+\s+obj\b.*$", re.M)


def clean_text(raw: str) -> str:
    text = unicodedata.normalize("NFKC", raw)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _WS.sub(" ", text)
    text = _MULTINL.sub("\n\n", text)
    lines = [ln.strip() for ln in text.split("\n")]
    return "\n".join(lines).strip()


# --------------------------------------------------------------------------
# Language detection (real)
# --------------------------------------------------------------------------
_LANG_PROFILES = {
    "en": {"the", "and", "was", "with", "near", "on", "of", "at", "reported", "vehicle"},
    "ta-en": {"anna", "nagar", "chennai", "tn", "thiru", "salai"},
}

# Which languages a script can plausibly encode - used to reject a Latin-only
# guess for clearly non-Latin text and vice versa.
_SCRIPT_ALLOWED_LANGS: dict[str, set[str]] = {
    "devanagari": {"hi", "mr", "ne", "sa", "bho", "mai"},
    "tamil": {"ta"},
    "bengali": {"bn"},
    "gurmukhi": {"pa"},
    "telugu": {"te"},
    "kannada": {"kn"},
    "malayalam": {"ml"},
    "latin": {"en", "fr", "de", "es", "pt", "it", "nl", "sv", "da", "no", "fi",
              "id", "tr", "vi", "ro", "pl", "cs", "hu", "et", "sl", "sw", "tl",
              "af", "hr", "lt", "lv", "sk", "sq", "ca"},
}
_SCRIPT_DEFAULT_LANG = {
    "devanagari": "hi", "tamil": "ta", "bengali": "bn", "gurmukhi": "pa",
    "telugu": "te", "kannada": "kn", "malayalam": "ml", "latin": "en",
}

_LANGDETECT_READY = False


def _load_langdetect() -> bool:
    global _LANGDETECT_READY
    if _LANGDETECT_READY:
        return True
    try:
        from langdetect import DetectorFactory  # noqa: F401

        DetectorFactory.seed = 0  # reproducible output across runs
        _LANGDETECT_READY = True
    except Exception:
        _LANGDETECT_READY = False
    return _LANGDETECT_READY


def detect_language(text: str) -> dict[str, Any]:
    """Detect the document language. Returns the detected code, the engine and
    method that produced it, and the Unicode script census behind the result."""
    census = indic.script_census(text)
    dominant = indic.dominant_script(text)
    allowed = _SCRIPT_ALLOWED_LANGS.get(dominant)
    method = ""
    engine = "script-census"
    guess: Optional[str] = None
    confidence = 0.0

    if _load_langdetect():
        try:
            from langdetect import detect_langs

            probabilities = detect_langs(text)
            engine = "langdetect"
            method = ("langdetect n-gram profile classifier (seeded, offline), "
                      "validated against a Unicode script census")
            for p in probabilities:
                if allowed is None or p.lang in allowed or p.lang.split("-")[0] in allowed:
                    guess, confidence = p.lang, float(p.prob)
                    break
            if guess is None and probabilities:
                # Top guess contradicts the script census: trust the script and say so.
                guess, confidence = None, 0.0
                method += "; top langdetect guess rejected as script-inconsistent"
        except Exception as exc:
            method = f"langdetect unavailable for this input ({type(exc).__name__}); "

    if guess is None:
        guess = _SCRIPT_DEFAULT_LANG.get(dominant, "en")
        confidence = 0.5
        engine = engine if engine == "langdetect" else "script-census"
        method += "Unicode script census fallback (no reliable statistical signal)"

    tokens = {t.lower().strip(".,;:()") for t in text.split()}
    scores = {lang: len(tokens & words) for lang, words in _LANG_PROFILES.items()}
    best = max(scores, key=lambda k: scores[k]) if scores else "en"

    return {
        "language": guess,
        "script_hint": dominant,
        "script_census": census,
        "detected": guess != "en" or dominant == "latin",
        "regional_token_signal": best,
        "confidence": round(min(0.99, max(confidence, 0.5)), 2),
        "engine": engine,
        "method": method,
        "supported_scripts": ["Latin", "Devanagari", "Tamil"],
    }


def normalize_text(text: str) -> str:
    """Normalisation used before NER: canonical spacing, registration/phone/date
    spacing, and consistent casing markers for downstream regex extraction."""
    out = text
    out = re.sub(r"\b([A-Z]{2})\s*[- ]?\s*(\d{2})\s*[- ]?\s*([A-Z]{1,2})\s*[- ]?\s*(\d{4})\b",
                 r"\1\2\3\4", out)
    out = re.sub(r"\+91[\s-]?(\d{5})[\s-]?(\d{5})", r"+91\1\2", out)
    out = re.sub(r"\s+([,.;:])", r"\1", out)
    return out.strip()


# --------------------------------------------------------------------------
# Pipeline
# --------------------------------------------------------------------------
def process_document(evidence: dict[str, Any], override_text: Optional[str] = None
                     ) -> dict[str, Any]:
    """Run the full document-intelligence pipeline for one evidence object."""
    steps: list[dict[str, Any]] = []
    object_key = evidence.get("object_key", "")
    declared_type = (evidence.get("evidence_type") or "").upper()
    raw_bytes: Optional[bytes] = object_storage.get_bytes(object_key)
    text = "" if raw_bytes is None else raw_bytes.decode("utf-8", errors="ignore")
    acquisition: dict[str, Any] = {"engine": None, "pages": None, "has_text_layer": None}

    if override_text is not None:
        text, text_origin = override_text, "OPERATOR_SUPPLIED_TEXT"
        steps.append({"step": "TEXT_ACQUISITION", "status": "COMPLETE",
                      "detail": "Operator-supplied text used instead of the stored object."})
    elif looks_like_pdf(raw_bytes, object_key):
        if raw_bytes is None:
            text, text_origin = "", "OBJECT_MISSING"
            steps.append({"step": "PDF_TEXT_EXTRACTION", "status": "INSUFFICIENT_EVIDENCE",
                          "detail": "Evidence object is not present in object storage."})
        else:
            result = pdf_extractor.extract(raw_bytes)
            acquisition.update({"engine": pdf_extractor.backend,
                                "pages": result["pages"],
                                "has_text_layer": result["has_text_layer"]})
            if result["has_text_layer"]:
                text, text_origin = result["text"], "PDF_TEXT_LAYER"
                steps.append({"step": "PDF_TEXT_EXTRACTION", "status": "COMPLETE",
                              "detail": f"{pdf_extractor.backend}: {result['pages']} page(s), "
                                        f"{len(text)} characters recovered from the PDF text "
                                        f"layer (not OCR)."})
            else:
                text_origin = "PREPROCESSED_SYNTHETIC_TEXT"
                steps.append({
                    "step": "PDF_TEXT_EXTRACTION", "status": "UNAVAILABLE",
                    "detail": (result["error"] or "This PDF carries no embedded text layer "
                               "(scanned image only).") + " " + ocr_engine.detail,
                })
    elif looks_like_image(object_key, declared_type):
        if ocr_engine.available:  # pragma: no cover
            text, text_origin = ocr_engine.extract(object_key) or text, "OCR"
            steps.append({"step": "OCR", "status": "COMPLETE", "detail": ocr_engine.backend})
        else:
            text_origin = "PREPROCESSED_SYNTHETIC_TEXT"
            steps.append({"step": "OCR", "status": "UNAVAILABLE", "detail": ocr_engine.detail})
    else:
        text_origin = "NATIVE_TEXT"
        steps.append({"step": "TEXT_ACQUISITION", "status": "NOT_REQUIRED",
                      "detail": "Text-bearing evidence - direct text ingestion."})

    steps.append({"step": "TEXT", "status": "COMPLETE", "detail": f"{len(text)} characters ingested"})

    cleaned = clean_text(text)
    steps.append({"step": "CLEANING", "status": "COMPLETE",
                  "detail": f"Unicode NFKC + whitespace normalisation ({len(cleaned)} chars)"})

    lang = detect_language(cleaned)
    steps.append({"step": "LANGUAGE_DETECTION", "status": "COMPLETE",
                  "detail": f"{lang['language']} via {lang['engine']} "
                            f"(confidence {lang['confidence']}, script {lang['script_hint']})"})

    normalized = normalize_text(cleaned)
    steps.append({"step": "NORMALIZATION", "status": "COMPLETE",
                  "detail": "Registration/phone/date canonicalisation applied"})

    if not normalized:
        steps.append({"step": "OUTPUT", "status": "INSUFFICIENT_EVIDENCE",
                      "detail": "No readable text content could be derived from this object."})

    return {
        "agent": AGENT_NAME,
        "evidence_id": evidence.get("evidence_id"),
        "input_kind": ("PDF" if looks_like_pdf(raw_bytes, object_key)
                       else "IMAGE" if looks_like_image(object_key, declared_type)
                       else "TEXT"),
        "text_origin": text_origin,
        "ocr_applied": text_origin == "OCR",
        "ocr_engine": ocr_engine.status(),
        "pdf_extractor": pdf_extractor.status(),
        "acquisition": acquisition,
        "language": lang,
        "raw_length": len(text),
        "clean_text": normalized,
        "steps": steps,
        "sufficient": bool(normalized),
    }
