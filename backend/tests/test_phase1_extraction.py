"""PHASE 1 unit tests - extraction correctness.

Run:  cd backend && python3 -m unittest discover -s tests -v
      (or: python3 tests/test_phase1_extraction.py)
"""
from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents import document_agent, entity_agent, indic, resolution_agent  # noqa: E402


class TestPhonePattern(unittest.TestCase):
    """PHASE 1.1 - the PHONE pattern must match real Indian mobile formats.

    The previous pattern, `(?:\\+91[\\s-]?)?\\b[6-9]\\d{9}\\b`, returned [] for both
    `+919840012345` (no word boundary between the country code and the subscriber
    number, both are word characters) and `+91 98400 12345` (the subscriber number
    is written in two groups, so `\\d{9}` could not span it).
    """

    CASES = [
        ("Contact +919840012345 was recorded.", ["+919840012345"]),      # country code, no space
        ("Contact +91 98400 12345 was recorded.", ["+91 98400 12345"]),  # country code, spaces
        ("Contact 9840012345 was recorded.", ["9840012345"]),            # domestic 10-digit
        ("Contact 98400 12345 was recorded.", ["98400 12345"]),          # domestic, spaced
        ("Contact +91-98400-12345, verified.", ["+91-98400-12345"]),     # hyphens + trailing comma
        ("Contact 098400 12345 was recorded.", ["098400 12345"]),        # trunk prefix
        ("Contact +91.98400.12345 (landline).", ["+91.98400.12345"]),    # dot separators
        ("Mobile +91 9840012345.", ["+91 9840012345"]),                  # trailing full stop
    ]

    def test_matches_all_real_formats(self):
        for text, expected in self.CASES:
            with self.subTest(text=text):
                self.assertEqual(entity_agent.PATTERNS["PHONE"].findall(text), expected)

    def test_all_formats_normalise_to_one_entity(self):
        """Every spelling of the same number must collapse to a single entity, so
        the graph does not sprout one phone node per formatting variant."""
        seen = {entity_agent.normalize_value("PHONE", m)
                for text, _ in self.CASES
                for m in entity_agent.PATTERNS["PHONE"].findall(text)}
        self.assertEqual(seen, {"+919840012345"}, f"expected one canonical phone, got {seen}")

    def test_does_not_match_longer_digit_runs(self):
        """An IMEI or account number must not yield a spurious PHONE mention."""
        for text in ["IMEI 356938035643809 recorded.",
                     "Account A/C 3390112212345 debited.",
                     "Ref 1234567890123 raised."]:
            with self.subTest(text=text):
                self.assertEqual(entity_agent.PATTERNS["PHONE"].findall(text), [])

    def test_does_not_match_invalid_indian_prefix(self):
        for text in ["Number 1234567890 dialled.", "Number 5123456789 dialled."]:
            with self.subTest(text=text):
                self.assertEqual(entity_agent.PATTERNS["PHONE"].findall(text), [])


class TestIndicExtraction(unittest.TestCase):
    """PHASE 1.3 - Devanagari / Tamil text must yield real entities."""

    SENTENCE = ("रवि कुमार को 12 अगस्त को वाहन TN01AB1234 के साथ "
                "चेन्नई सेंट्रल में देखा गया।")
    VOCAB = {
        "PERSON": ["Ravi Kumar", "Arun Selvam", "Suresh Balan"],
        "LOCATION": ["Chennai Central", "T Nagar", "Guindy Industrial Estate"],
    }

    def test_script_detection(self):
        self.assertEqual(indic.dominant_script(self.SENTENCE), "devanagari")
        self.assertTrue(indic.is_indic(self.SENTENCE))

    def test_romanisation_is_faithful_and_folds_for_matching(self):
        # Romanisation stays faithful to the script ("kumaar" for कुमार) ...
        self.assertEqual(indic.romanise("रवि कुमार", drop_final_schwa=True), "ravi kumaar")
        # The matching layer tries both romanisation variants, so the strict form
        # (which keeps the inherent vowel before the final ई) is the one that folds
        # onto the English spelling.
        self.assertEqual(indic.fold_vowels(indic.romanise("चेन्नई")), "chennai")
        # ... and vowel-length folding (applied to BOTH sides of a comparison only)
        # is what makes it equivalent to the English spelling.
        self.assertEqual(indic.fold_vowels(indic.romanise("रवि कुमार", drop_final_schwa=True)),
                         "ravi kumar")

    def test_devanagari_sentence_yields_person_vehicle_location_date(self):
        result = entity_agent.run(self.SENTENCE, self.VOCAB)
        found = {(e["entity_type"], e["normalized"]) for e in result["entities"]}
        self.assertIn(("VEHICLE", "TN01AB1234"), found)
        self.assertIn(("PERSON", "Ravi Kumar"), found)
        self.assertIn(("LOCATION", "Chennai Central"), found)
        self.assertIn(("DATE", "12 August"), found)

    def test_devanagari_sentence_raises_an_observation_event(self):
        result = entity_agent.run(self.SENTENCE, self.VOCAB)
        self.assertTrue(result["events"], "no event extracted from an Indic sentence")
        event = result["events"][0]
        self.assertEqual(event["event_type"], "OBSERVATION")
        self.assertIn("Ravi Kumar", event["actors"])
        self.assertIn("TN01AB1234", event["actors"])
        self.assertEqual(event["language"], "INDIC")

    def test_tamil_sentence_yields_entities(self):
        tamil = ("சென்னை சென்ட்ரலில் ஆகஸ்ட் 12 அன்று வாகனம் TN01AB1234 உடன் "
                 "ரவி குமார் காணப்பட்டார்.")
        result = entity_agent.run(tamil, self.VOCAB)
        found = {(e["entity_type"], e["normalized"]) for e in result["entities"]}
        self.assertIn(("PERSON", "Ravi Kumar"), found)
        self.assertIn(("LOCATION", "Chennai Central"), found)
        self.assertIn(("VEHICLE", "TN01AB1234"), found)
        self.assertIn(("DATE", "12 August"), found)

    def test_structural_fallback_without_vocabulary(self):
        """With no vocabulary, postposition structure still yields LOW-confidence
        candidates rather than nothing."""
        result = entity_agent.run(self.SENTENCE)
        hints = [e for e in result["entities"] if "indic-structural" in " ".join(e["methods"])]
        self.assertTrue(hints, "no structural fallback candidates produced")
        self.assertTrue(all(e["confidence"] <= 0.6 for e in hints))


class TestNameNormalisation(unittest.TestCase):
    """PHASE 1.3 - normalize_name must not delete non-Latin characters."""

    def test_indic_names_survive_normalisation(self):
        for name in ["रवि कुमार", "ரவி குமார்", "রবি কুমার"]:
            with self.subTest(name=name):
                self.assertNotEqual(resolution_agent.normalize_name(name), "")

    def test_cross_script_names_match_after_romanisation(self):
        for name in ["रवि कुमार", "ரவி குமார்"]:
            with self.subTest(name=name):
                score = resolution_agent.fuzzy_similarity(name, "Ravi Kumar")
                self.assertGreaterEqual(score["token_set_ratio"], 90.0,
                                        f"{name} vs 'Ravi Kumar' scored {score}")

    def test_unrelated_indic_name_does_not_match(self):
        score = resolution_agent.fuzzy_similarity("रवि कुमार", "Arun Selvam")
        self.assertLess(score["token_set_ratio"], 60.0)

    def test_punctuation_and_digits_are_dropped(self):
        self.assertEqual(resolution_agent.normalize_name("  Thiru  Ravi   Kumar (34) "),
                         "ravi kumar")


class TestLanguageDetection(unittest.TestCase):
    """PHASE 1.2 - detect_language must actually detect, not return a constant."""

    def test_english_detected(self):
        r = document_agent.detect_language(
            "On 18 August at 10:05, vehicle TN01AB1234 was observed at Chennai Central.")
        self.assertEqual(r["language"], "en")

    def test_hindi_detected(self):
        r = document_agent.detect_language(
            "रवि कुमार को 12 अगस्त को वाहन TN01AB1234 के साथ चेन्नई सेंट्रल में देखा गया।")
        self.assertEqual(r["language"], "hi")
        self.assertEqual(r["script_hint"], "devanagari")

    def test_tamil_detected(self):
        r = document_agent.detect_language(
            "சென்னை சென்ட்ரலில் ஆகஸ்ட் 12 அன்று வாகனம் TN01AB1234 உடன் ரவி குமார் காணப்பட்டார்.")
        self.assertEqual(r["language"], "ta")
        self.assertEqual(r["script_hint"], "tamil")

    def test_method_is_declared_and_deterministic(self):
        text = "रवि कुमार को 12 अगस्त को वाहन TN01AB1234 के साथ चेन्नई सेंट्रल में देखा गया।"
        results = {document_agent.detect_language(text)["language"] for _ in range(5)}
        self.assertEqual(len(results), 1, "language detection is not deterministic")
        self.assertIn("langdetect", document_agent.detect_language(text)["engine"])


class TestPdfTextExtraction(unittest.TestCase):
    """PHASE 2.3 - a PDF must be read through its text layer, not as raw bytes."""

    PDF = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))), "datasets", "01_FIR",
        "FIR_0412-2025_CASE-101_Chennai-Central.pdf")

    @unittest.skipUnless(os.path.exists(PDF), "synthetic FIR PDF not present")
    def test_pdf_text_layer_extracted(self):
        with open(self.PDF, "rb") as fh:
            data = fh.read()
        result = document_agent.pdf_extractor.extract(data)
        self.assertTrue(result["has_text_layer"])
        self.assertEqual(result["pages"], 2)

    @unittest.skipUnless(os.path.exists(PDF), "synthetic FIR PDF not present")
    def test_raw_bytes_would_have_been_garbage(self):
        """Demonstrates the original defect: the raw bytes are PDF internals."""
        with open(self.PDF, "rb") as fh:
            data = fh.read()
        raw = data.decode("utf-8", errors="ignore")
        extracted = document_agent.pdf_extractor.extract(data)["text"]
        # Raw bytes expose PDF object/stream/xref plumbing; the text layer does not.
        self.assertIn("obj", raw[:2000])
        self.assertNotIn("xref", extracted.lower())
        self.assertNotIn("endobj", extracted.lower())

    @unittest.skipUnless(os.path.exists(PDF), "synthetic FIR PDF not present")
    def test_entities_from_pdf_look_like_an_fir(self):
        with open(self.PDF, "rb") as fh:
            data = fh.read()
        text = document_agent.pdf_extractor.extract(data)["text"]
        result = entity_agent.run(document_agent.clean_text(text), {})
        values = {e["normalized"] for e in result["entities"]}
        self.assertIn("TN01AB1234", values, "vehicle registration missing from the real FIR")
        self.assertTrue(any("Ravi Kumar" in v for v in values),
                        f"accused name missing; got {sorted(values)}")
        self.assertTrue(any("Chennai" in v for v in values), "location missing")
        # The FIR form writes the occurrence date as dd/mm/yyyy; the rule layer
        # must surface it as a DATE either way.
        self.assertTrue(any(v in {"10 August", "2025-08-10", "10/08/2025"} for v in values),
                        f"occurrence date missing; got {sorted(values)}")
        self.assertTrue(any("Vasanthi" in v for v in values),
                        f"complainant name missing; got {sorted(values)}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
