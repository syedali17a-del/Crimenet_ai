import type { Tri } from '../tri'

/**
 * Evidence registry & document intelligence copy.
 *
 * Evidence ids, SHA-256 hashes, NER backend names and ledger block indices are
 * printed verbatim.
 */
const en = {
  allAuthorizedCases: 'All authorized cases',
  refresh: 'Refresh',
  upload: 'Upload evidence',
  itemsTitle: (n: number) => `Evidence items (${n})`,
  allTypes: 'All types',
  loading: 'Loading evidence registry…',
  noneInScope: 'No evidence is registered for this scope.',
  noneInScopeGap: 'Upload or select synthetic sample evidence to begin.',

  thEvidence: 'Evidence',
  thTypeSource: 'Type / Source',
  thCase: 'Case',
  thProcessing: 'Processing',
  thIntegrity: 'Integrity',
  thHash: 'Hash',

  detailTitle: 'Evidence detail',
  detailEmpty:
    'Select an evidence item to inspect its extracted text, provenance chain, ledger anchors and processing pipeline.',
  close: 'Close',
  ocrApplied: 'OCR applied',
  ocrNotApplied: 'OCR not applied',
  processingPipeline: 'Processing pipeline',
  registeredHash: 'Registered hash',
  processDocument: 'Process document',
  integrityCheck: 'Integrity check',
  verify: 'Verify',
  reject: 'Reject',
  verifyRationale: 'Source and integrity confirmed.',
  rejectRationale: 'Source reliability insufficient.',

  extractedContent: 'Extracted content',
  charactersInStorage: (n: number) => `${n} characters in object storage`,
  noTextContent: 'No text content available for this object.',
  entitiesExtracted: (n: number) => `Entities extracted (${n})`,
  nerBackend: 'NER backend',

  provenance: 'Provenance & chain of custody',
  ledgerAnchors: 'Permissioned ledger anchors',

  registerFailed: 'Evidence could not be registered.',
  registerTitle: 'Register evidence',
  registerSubtitle:
    'Synthetic demonstration environment. Uploaded objects are hashed (SHA-256), stored write-once and anchored to the permissioned ledger.',
  cancel: 'Cancel',
  registerAndProcess: 'Register & process',
  fieldCase: 'Case',
  selectCase: 'Select case…',
  fieldEvidenceType: 'Evidence type',
  fieldSource: 'Source',
  fieldSourcePlaceholder: 'Police Report / Telecom Record…',
  fieldText: 'Evidence text',
  fieldTextHint:
    'Native or preprocessed text. OCR is never simulated: image/PDF items are labelled PREPROCESSED SYNTHETIC TEXT.',
  fieldTextPlaceholder:
    'SYNTHETIC DEMONSTRATION DATA — e.g. Ravi Kumar was observed near Chennai Central using vehicle TN01AB1234 on 10 August.',
  fieldFile: 'File',
  fieldFileHint: 'Max 5 MB in this demonstration environment.',
  modeSample: 'Synthetic sample',
  modeText: 'Paste text',
  modeFile: 'Upload file',
  sampleNoteA: 'A labelled synthetic sample document for',
  sampleNoteB: 'will be registered, hashed and pushed through the document-intelligence pipeline.',
  processedToast: (id: string) => `${id} processed`,
  processedToastBody: 'Document pipeline complete — entities extracted.',
}

type Shape = typeof en

const ta: Shape = {
  allAuthorizedCases: 'அங்கீகரிக்கப்பட்ட அனைத்து வழக்குகள்',
  refresh: 'புதுப்பி',
  upload: 'ஆதாரத்தைப் பதிவேற்று',
  itemsTitle: (n) => `ஆதாரப் பொருள்கள் (${n})`,
  allTypes: 'அனைத்து வகைகள்',
  loading: 'ஆதாரப் பதிவேடு ஏற்றப்படுகிறது…',
  noneInScope: 'இந்த வரம்பில் ஆதாரம் எதுவும் பதிவு செய்யப்படவில்லை.',
  noneInScopeGap: 'தொடங்க ஆதாரத்தைப் பதிவேற்றவும் அல்லது செயற்கை மாதிரி ஆதாரத்தைத் தேர்ந்தெடுக்கவும்.',

  thEvidence: 'ஆதாரம்',
  thTypeSource: 'வகை / மூலம்',
  thCase: 'வழக்கு',
  thProcessing: 'செயலாக்கம்',
  thIntegrity: 'ஒருமைப்பாடு',
  thHash: 'ஹாஷ்',

  detailTitle: 'ஆதார விவரம்',
  detailEmpty:
    'பிரித்தெடுக்கப்பட்ட உரை, மூலச் சங்கிலி, லெட்ஜர் இணைப்புகள் மற்றும் செயலாக்கத் தொடரைப் பார்க்க ஒரு ஆதாரப் பொருளைத் தேர்ந்தெடுக்கவும்.',
  close: 'மூடு',
  ocrApplied: 'OCR பயன்படுத்தப்பட்டது',
  ocrNotApplied: 'OCR பயன்படுத்தப்படவில்லை',
  processingPipeline: 'செயலாக்கத் தொடர்',
  registeredHash: 'பதிவு செய்யப்பட்ட ஹாஷ்',
  processDocument: 'ஆவணத்தைச் செயலாக்கு',
  integrityCheck: 'ஒருமைப்பாட்டுச் சரிபார்ப்பு',
  verify: 'சரிபார்',
  reject: 'நிராகரி',
  verifyRationale: 'மூலமும் ஒருமைப்பாடும் உறுதிப்படுத்தப்பட்டன.',
  rejectRationale: 'மூலத்தின் நம்பகத்தன்மை போதுமானதாக இல்லை.',

  extractedContent: 'பிரித்தெடுக்கப்பட்ட உள்ளடக்கம்',
  charactersInStorage: (n) => `பொருள் சேமிப்பில் ${n} எழுத்துகள்`,
  noTextContent: 'இந்தப் பொருளுக்கு உரை உள்ளடக்கம் எதுவும் இல்லை.',
  entitiesExtracted: (n) => `பிரித்தெடுக்கப்பட்ட நிறுவனங்கள் (${n})`,
  nerBackend: 'NER பின்தளம்',

  provenance: 'மூலம் மற்றும் காவல் சங்கிலி',
  ledgerAnchors: 'அனுமதி அடிப்படையிலான லெட்ஜர் இணைப்புகள்',

  registerFailed: 'ஆதாரத்தைப் பதிவு செய்ய முடியவில்லை.',
  registerTitle: 'ஆதாரத்தைப் பதிவு செய்',
  registerSubtitle:
    'செயற்கை விளக்கச் சூழல். பதிவேற்றப்பட்ட பொருள்கள் ஹாஷ் (SHA-256) செய்யப்பட்டு, ஒருமுறை மட்டும் எழுதக்கூடிய வகையில் சேமிக்கப்பட்டு, அனுமதி அடிப்படையிலான லெட்ஜருடன் இணைக்கப்படுகின்றன.',
  cancel: 'ரத்து',
  registerAndProcess: 'பதிவு செய்து செயலாக்கு',
  fieldCase: 'வழக்கு',
  selectCase: 'வழக்கைத் தேர்ந்தெடு…',
  fieldEvidenceType: 'ஆதார வகை',
  fieldSource: 'மூலம்',
  fieldSourcePlaceholder: 'காவல் அறிக்கை / தொலைத்தொடர்பு பதிவு…',
  fieldText: 'ஆதார உரை',
  fieldTextHint:
    'சொந்த அல்லது முன்செயலாக்கப்பட்ட உரை. OCR ஒருபோதும் போலியாகச் செய்யப்படுவதில்லை: படம்/PDF பொருள்கள் PREPROCESSED SYNTHETIC TEXT எனக் குறிக்கப்படுகின்றன.',
  fieldTextPlaceholder:
    'செயற்கை விளக்கத் தரவு — எ.கா. ரவி குமார் ஆகஸ்ட் 10 அன்று TN01AB1234 வாகனத்துடன் சென்னை சென்ட்ரல் அருகே காணப்பட்டார்.',
  fieldFile: 'கோப்பு',
  fieldFileHint: 'இந்த விளக்கச் சூழலில் அதிகபட்சம் 5 MB.',
  modeSample: 'செயற்கை மாதிரி',
  modeText: 'உரையை ஒட்டு',
  modeFile: 'கோப்பைப் பதிவேற்று',
  sampleNoteA: 'இதற்கான குறியிடப்பட்ட செயற்கை மாதிரி ஆவணம்:',
  sampleNoteB: 'பதிவு செய்யப்பட்டு, ஹாஷ் செய்யப்பட்டு, ஆவண நுண்ணறிவுத் தொடர் வழியாகச் செலுத்தப்படும்.',
  processedToast: (id) => `${id} செயலாக்கப்பட்டது`,
  processedToastBody: 'ஆவணத் தொடர் நிறைவடைந்தது — நிறுவனங்கள் பிரித்தெடுக்கப்பட்டன.',
}

const hi: Shape = {
  allAuthorizedCases: 'सभी अधिकृत केस',
  refresh: 'ताज़ा करें',
  upload: 'साक्ष्य अपलोड करें',
  itemsTitle: (n) => `साक्ष्य मदें (${n})`,
  allTypes: 'सभी प्रकार',
  loading: 'साक्ष्य रजिस्टर लोड हो रहा है…',
  noneInScope: 'इस दायरे में कोई साक्ष्य पंजीकृत नहीं है।',
  noneInScopeGap: 'आरंभ करने हेतु साक्ष्य अपलोड करें या सिंथेटिक नमूना साक्ष्य चुनें।',

  thEvidence: 'साक्ष्य',
  thTypeSource: 'प्रकार / स्रोत',
  thCase: 'केस',
  thProcessing: 'प्रसंस्करण',
  thIntegrity: 'अखंडता',
  thHash: 'हैश',

  detailTitle: 'साक्ष्य विवरण',
  detailEmpty:
    'निष्कर्षित पाठ, अभिरक्षा शृंखला, लेजर लंगर और प्रसंस्करण पाइपलाइन देखने हेतु कोई साक्ष्य मद चुनें।',
  close: 'बंद करें',
  ocrApplied: 'OCR लागू',
  ocrNotApplied: 'OCR लागू नहीं',
  processingPipeline: 'प्रसंस्करण पाइपलाइन',
  registeredHash: 'पंजीकृत हैश',
  processDocument: 'दस्तावेज़ संसाधित करें',
  integrityCheck: 'अखंडता जाँच',
  verify: 'सत्यापित करें',
  reject: 'अस्वीकार करें',
  verifyRationale: 'स्रोत और अखंडता की पुष्टि हुई।',
  rejectRationale: 'स्रोत की विश्वसनीयता अपर्याप्त।',

  extractedContent: 'निष्कर्षित सामग्री',
  charactersInStorage: (n) => `ऑब्जेक्ट स्टोरेज में ${n} वर्ण`,
  noTextContent: 'इस वस्तु के लिए कोई पाठ सामग्री उपलब्ध नहीं है।',
  entitiesExtracted: (n) => `निष्कर्षित इकाइयाँ (${n})`,
  nerBackend: 'NER बैकएंड',

  provenance: 'उद्गम और अभिरक्षा शृंखला',
  ledgerAnchors: 'अनुमति-आधारित लेजर लंगर',

  registerFailed: 'साक्ष्य पंजीकृत नहीं किया जा सका।',
  registerTitle: 'साक्ष्य पंजीकृत करें',
  registerSubtitle:
    'सिंथेटिक प्रदर्शन वातावरण। अपलोड की गई वस्तुएँ हैश (SHA-256) की जाती हैं, राइट-वन्स संग्रहीत होती हैं और अनुमति-आधारित लेजर से जुड़ती हैं।',
  cancel: 'रद्द करें',
  registerAndProcess: 'पंजीकृत करें और संसाधित करें',
  fieldCase: 'केस',
  selectCase: 'केस चुनें…',
  fieldEvidenceType: 'साक्ष्य प्रकार',
  fieldSource: 'स्रोत',
  fieldSourcePlaceholder: 'पुलिस रिपोर्ट / दूरसंचार अभिलेख…',
  fieldText: 'साक्ष्य पाठ',
  fieldTextHint:
    'मूल या पूर्व-संसाधित पाठ। OCR का अनुकरण कभी नहीं किया जाता: छवि/PDF मदें PREPROCESSED SYNTHETIC TEXT के रूप में अंकित होती हैं।',
  fieldTextPlaceholder:
    'सिंथेटिक प्रदर्शन डेटा — उदा. रवि कुमार 10 अगस्त को वाहन TN01AB1234 के साथ चेन्नई सेंट्रल के पास देखे गए।',
  fieldFile: 'फ़ाइल',
  fieldFileHint: 'इस प्रदर्शन वातावरण में अधिकतम 5 MB।',
  modeSample: 'सिंथेटिक नमूना',
  modeText: 'पाठ चिपकाएँ',
  modeFile: 'फ़ाइल अपलोड करें',
  sampleNoteA: 'इसके लिए अंकित सिंथेटिक नमूना दस्तावेज़:',
  sampleNoteB: 'पंजीकृत, हैश और दस्तावेज़-आसूचना पाइपलाइन से होकर संसाधित किया जाएगा।',
  processedToast: (id) => `${id} संसाधित`,
  processedToastBody: 'दस्तावेज़ पाइपलाइन पूर्ण — इकाइयाँ निष्कर्षित।',
}

export const evidence: Tri<Shape> = { en, ta, hi }
