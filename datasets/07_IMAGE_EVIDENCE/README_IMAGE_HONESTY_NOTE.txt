SYNTHETIC DEMONSTRATION DATA - IMAGE EVIDENCE HONESTY NOTE
================================================================================

WHAT THESE IMAGES ARE
  * AI-generated pictures produced for this prototype, then overlaid with a
    synthetic camera OSD (camera id, timestamp, location) using a drawing
    library. The number plate in the ANPR crop was drawn on, not photographed.

WHAT THESE IMAGES ARE NOT
  * They are not photographs.
  * They are not CCTV footage.
  * They do not depict any real person, vehicle, place or event.
  * No face in any image is a real person's face and no facial recognition,
    face matching or person identification has been performed on them.

WHAT THE PLATFORM DOES WITH THEM
  * It registers the object, computes its SHA-256 digest and stores the digest
    in an append-only ledger.
  * It does NOT run OCR. No OCR engine is installed in this environment, and the
    platform says so explicitly on the evidence record
    (ocr_applied = FALSE, text_origin = PREPROCESSED_SYNTHETIC_TEXT).
  * The text associated with an image item is a human-written synthetic
    description, and it is labelled as such rather than presented as a machine
    reading of the picture.

THE INTEGRITY DEMONSTRATION
  * EV-2042 is deliberately altered in storage AFTER its hash was registered.
  * Running the integrity check on EV-2042 therefore reports INTEGRITY_MISMATCH
    while the other nine items report VERIFIED.
  * This is the intended behaviour and is the point of the demonstration.
