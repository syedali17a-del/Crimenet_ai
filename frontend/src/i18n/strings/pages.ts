import type { Tri } from '../tri'

/**
 * Page headers — the title / eyebrow / description block at the top of every
 * console view. Kept in one place so the whole application's headline copy can
 * be reviewed for tone and terminology in a single file per language.
 *
 * Identifiers embedded in these strings (SHA-256, JWT, RapidFuzz, OCR, API,
 * case ids) are algorithm and product names and are never translated.
 */
const en = {
  dashboard: {
    tagline: 'Investigator command center',
    title: 'Evidence → Network → Intelligence',
    description: '',
  },
  cases: {
    tagline: 'Case management',
    title: 'Investigation cases',
    description:
      'Every case is a scope boundary: authorization, evidence, entities and analysis are all constrained to the cases you are permitted to access.',
  },
  evidence: {
    tagline: 'Evidence management',
    title: 'Evidence registry & document intelligence',
    description:
      'Every item carries a source, timestamp, case, SHA-256 hash, provenance chain and verification status. Processing runs OCR-abstraction → cleaning → language detection → normalization → entity & event extraction.',
  },
  network: {
    tagline: 'Network intelligence',
    title: 'Evidence-aware relationship graph',
    description:
      'Every edge carries its relationship type, timestamp, source document, evidence ID, support level and verification status. Structural prominence is never an allegation.',
  },
  timeline: {
    tagline: 'Temporal analysis',
    title: 'Timeline & behavioural patterns',
    description:
      'Chronological reconstruction of evidence-backed events, repeated activity, activity spikes, temporal overlap and potential spatio-temporal convergence. Co-occurrence is a signal, never proof of contact.',
  },
  map: {
    tagline: 'Geospatial intelligence',
    title: 'Map & spatio-temporal convergence',
    description:
      'Only locations that appear in registered evidence are plotted. Marker weight reflects the number of evidence-backed events, never a risk score.',
  },
  crossCase: {
    tagline: 'Cross-case investigation',
    title: 'Shared identifiers across separate cases',
    description:
      'Cases are correlated on hard identifiers (vehicle, phone, account), fuzzy-matched names, shared locations and temporal proximity. Every association is a candidate that requires human verification.',
  },
  entities: {
    tagline: 'Entity resolution',
    title: 'Are these records the same identity?',
    description:
      'Normalization → token comparison → RapidFuzz fuzzy similarity → multi-attribute scoring. Identities are never merged automatically; the platform only proposes candidates for human decision.',
  },
  hypotheses: {
    tagline: 'Investigation reasoning',
    title: 'Competing hypotheses, ranked by evidence support',
    description:
      'For every observation the reasoning agent generates alternative explanations — including the innocent and the coincidental one — and ranks them only by the evidence that supports or contradicts them.',
  },
  gaps: {
    tagline: 'Known vs unknown',
    title: 'Information gap analysis',
    description:
      'For every analytical lead the platform states what is known, what is missing and what evidence would resolve the gap. Missing evidence is named explicitly — it is never inferred away.',
  },
  nextBest: {
    tagline: 'Next best analytical action',
    title: 'What should be examined next — and why',
    description:
      'Actions are ranked by expected information value: how many open gaps they close and how much they would strengthen or weaken the current leads. The catalogue contains analytical steps only.',
  },
  audit: {
    tagline: 'Audit & evidence integrity',
    title: 'Tamper-evident record of every action',
    description:
      'Every login, evidence action, analysis run and human decision is appended to a hash-chained audit trail. Evidence objects are hashed with SHA-256 at intake and re-verified on demand.',
  },
  security: {
    tagline: 'Settings & security',
    title: 'Security posture, access control and system profile',
    description:
      'Authentication, role-based authorization, case-level scoping, transport security, encryption, evidence hashing and the audit/ledger surface — all enforced server-side.',
  },
  workflow: {
    tagline: 'Investigation workflow',
    title: 'Run the pipeline end to end',
    description:
      'Login → Case → Evidence → Extraction → Resolution → Cross-case → Graph → Network → Timeline → Corroboration → Gaps → Next-best action → Human verification → Integrity → Audit. Every stage calls the real service and reports the real result.',
  },
  caseDetails: {
    tagline: 'Case',
    title: 'Case file',
    description: '',
  },
}

type Shape = typeof en

const ta: Shape = {
  dashboard: {
    tagline: 'புலனாய்வாளர் கட்டளை மையம்',
    title: 'ஆதாரம் → நெட்வொர்க் → நுண்ணறிவு',
    description: '',
  },
  cases: {
    tagline: 'வழக்கு மேலாண்மை',
    title: 'விசாரணை வழக்குகள்',
    description:
      'ஒவ்வொரு வழக்கும் ஒரு எல்லை: அங்கீகாரம், ஆதாரம், நிறுவனங்கள் மற்றும் பகுப்பாய்வு அனைத்தும் நீங்கள் அணுக அனுமதிக்கப்பட்ட வழக்குகளுக்குள் மட்டுமே வரையறுக்கப்படுகின்றன.',
  },
  evidence: {
    tagline: 'ஆதார மேலாண்மை',
    title: 'ஆதாரப் பதிவேடு மற்றும் ஆவண நுண்ணறிவு',
    description:
      'ஒவ்வொரு பொருளும் மூலம், நேர முத்திரை, வழக்கு, SHA-256 ஹாஷ், மூலச் சங்கிலி மற்றும் சரிபார்ப்பு நிலையைக் கொண்டுள்ளது. செயலாக்கம்: OCR-சுருக்கம் → சுத்தம் → மொழி கண்டறிதல் → இயல்பாக்கம் → நிறுவனம் மற்றும் நிகழ்வுப் பிரித்தெடுத்தல்.',
  },
  network: {
    tagline: 'நெட்வொர்க் நுண்ணறிவு',
    title: 'ஆதாரம் சார்ந்த உறவு வரைபடம்',
    description:
      'ஒவ்வொரு இணைப்பும் அதன் உறவு வகை, நேர முத்திரை, மூல ஆவணம், ஆதார ID, ஆதரவு நிலை மற்றும் சரிபார்ப்பு நிலையைக் கொண்டுள்ளது. கட்டமைப்பு முக்கியத்துவம் ஒருபோதும் ஒரு குற்றச்சாட்டு அல்ல.',
  },
  timeline: {
    tagline: 'கால அடிப்படையிலான பகுப்பாய்வு',
    title: 'காலவரிசை மற்றும் நடத்தை முறைகள்',
    description:
      'ஆதாரம் உள்ள நிகழ்வுகளின் காலவரிசை மறுகட்டமைப்பு, மீண்டும் நிகழும் செயல்பாடு, செயல்பாட்டு உச்சங்கள், கால ஒன்றுபடல் மற்றும் சாத்தியமான கால-இட ஒருங்கிணைவு. ஒரே நேரத்தில் நிகழ்தல் ஒரு சமிக்ஞை மட்டுமே, தொடர்புக்கான சான்று அல்ல.',
  },
  map: {
    tagline: 'புவிசார் நுண்ணறிவு',
    title: 'வரைபடம் மற்றும் கால-இட ஒருங்கிணைவு',
    description:
      'பதிவு செய்யப்பட்ட ஆதாரங்களில் தோன்றும் இருப்பிடங்கள் மட்டுமே வரைபடத்தில் இடம்பெறும். குறிப்பான் அளவு ஆதாரம் உள்ள நிகழ்வுகளின் எண்ணிக்கையைக் காட்டுகிறது, ஆபத்து மதிப்பெண்ணை அல்ல.',
  },
  crossCase: {
    tagline: 'வழக்குகளுக்கிடையேயான விசாரணை',
    title: 'தனித்தனி வழக்குகளில் பகிரப்பட்ட அடையாளங்காட்டிகள்',
    description:
      'வழக்குகள் உறுதியான அடையாளங்காட்டிகள் (வாகனம், தொலைபேசி, கணக்கு), தோராய பெயர்ப் பொருத்தம், பகிரப்பட்ட இருப்பிடங்கள் மற்றும் கால நெருக்கம் ஆகியவற்றின் அடிப்படையில் தொடர்புபடுத்தப்படுகின்றன. ஒவ்வொரு தொடர்பும் மனிதச் சரிபார்ப்பு தேவைப்படும் ஒரு வேட்பாளர் மட்டுமே.',
  },
  entities: {
    tagline: 'அடையாளத் தீர்வு',
    title: 'இந்தப் பதிவுகள் ஒரே அடையாளமா?',
    description:
      'இயல்பாக்கம் → சொல் ஒப்பீடு → RapidFuzz தோராய ஒற்றுமை → பல-பண்பு மதிப்பீடு. அடையாளங்கள் ஒருபோதும் தானாக இணைக்கப்படுவதில்லை; அமைப்பு மனித முடிவுக்காக வேட்பாளர்களை மட்டுமே முன்மொழிகிறது.',
  },
  hypotheses: {
    tagline: 'விசாரணைப் பகுத்தறிவு',
    title: 'ஆதார ஆதரவின் அடிப்படையில் தரவரிசைப்படுத்தப்பட்ட போட்டி கருதுகோள்கள்',
    description:
      'ஒவ்வொரு அவதானிப்புக்கும் பகுத்தறிவு முகவர் மாற்று விளக்கங்களை உருவாக்குகிறது — குற்றமற்ற மற்றும் தற்செயலான விளக்கங்கள் உட்பட — அவற்றை ஆதரிக்கும் அல்லது மறுக்கும் ஆதாரங்களின் அடிப்படையில் மட்டுமே தரவரிசைப்படுத்துகிறது.',
  },
  gaps: {
    tagline: 'தெரிந்தவை vs தெரியாதவை',
    title: 'தகவல் இடைவெளிப் பகுப்பாய்வு',
    description:
      'ஒவ்வொரு பகுப்பாய்வுத் தடயத்திற்கும் என்ன தெரியும், என்ன இல்லை, எந்த ஆதாரம் அந்த இடைவெளியைத் தீர்க்கும் என்பதை அமைப்பு கூறுகிறது. இல்லாத ஆதாரம் வெளிப்படையாகப் பெயரிடப்படுகிறது — ஊகத்தால் நிரப்பப்படுவதில்லை.',
  },
  nextBest: {
    tagline: 'அடுத்த சிறந்த பகுப்பாய்வு நடவடிக்கை',
    title: 'அடுத்து எதை ஆய்வு செய்ய வேண்டும் — ஏன்',
    description:
      'நடவடிக்கைகள் எதிர்பார்க்கப்படும் தகவல் மதிப்பின் அடிப்படையில் தரவரிசைப்படுத்தப்படுகின்றன: அவை எத்தனை திறந்த இடைவெளிகளை மூடுகின்றன, தற்போதைய தடயங்களை எவ்வளவு வலுப்படுத்தும் அல்லது பலவீனப்படுத்தும். இப்பட்டியலில் பகுப்பாய்வு நடவடிக்கைகள் மட்டுமே உள்ளன.',
  },
  audit: {
    tagline: 'தணிக்கை மற்றும் ஆதார ஒருமைப்பாடு',
    title: 'ஒவ்வொரு செயலுக்கும் சேதம் புலப்படும் பதிவு',
    description:
      'ஒவ்வொரு உள்நுழைவு, ஆதாரச் செயல், பகுப்பாய்வு இயக்கம் மற்றும் மனித முடிவும் ஹாஷ்-சங்கிலிப் பதிவில் சேர்க்கப்படுகிறது. ஆதாரப் பொருள்கள் பெறப்படும்போது SHA-256 ஆல் ஹாஷ் செய்யப்பட்டு, தேவைப்படும்போது மீண்டும் சரிபார்க்கப்படுகின்றன.',
  },
  security: {
    tagline: 'அமைப்புகள் மற்றும் பாதுகாப்பு',
    title: 'பாதுகாப்பு நிலை, அணுகல் கட்டுப்பாடு மற்றும் அமைப்பு விவரக்குறிப்பு',
    description:
      'அங்கீகாரம், பணி அடிப்படையிலான அனுமதி, வழக்கு அளவிலான வரம்பு, பரிமாற்றப் பாதுகாப்பு, மறையாக்கம், ஆதார ஹாஷிங் மற்றும் தணிக்கை/லெட்ஜர் பரப்பு — அனைத்தும் சேவையகத்தில் அமல்படுத்தப்படுகின்றன.',
  },
  workflow: {
    tagline: 'விசாரணைப் பணிப்பாய்வு',
    title: 'முழுப் பணித்தொடரையும் இயக்கவும்',
    description:
      'உள்நுழைவு → வழக்கு → ஆதாரம் → பிரித்தெடுத்தல் → தீர்வு → வழக்குகளுக்கிடையே → வரைபடம் → நெட்வொர்க் → காலவரிசை → உறுதிப்படுத்தல் → இடைவெளிகள் → அடுத்த நடவடிக்கை → மனிதச் சரிபார்ப்பு → ஒருமைப்பாடு → தணிக்கை. ஒவ்வொரு நிலையும் உண்மையான சேவையை அழைத்து உண்மையான முடிவைத் தெரிவிக்கிறது.',
  },
  caseDetails: {
    tagline: 'வழக்கு',
    title: 'வழக்குக் கோப்பு',
    description: '',
  },
}

const hi: Shape = {
  dashboard: {
    tagline: 'अन्वेषक कमांड सेंटर',
    title: 'साक्ष्य → नेटवर्क → आसूचना',
    description: '',
  },
  cases: {
    tagline: 'केस प्रबंधन',
    title: 'अन्वेषण केस',
    description:
      'प्रत्येक केस एक सीमा है: प्राधिकरण, साक्ष्य, इकाइयाँ और विश्लेषण सभी उन्हीं केसों तक सीमित हैं जिन तक आपकी पहुँच अनुमत है।',
  },
  evidence: {
    tagline: 'साक्ष्य प्रबंधन',
    title: 'साक्ष्य रजिस्टर और दस्तावेज़ आसूचना',
    description:
      'प्रत्येक मद के साथ स्रोत, समय-चिह्न, केस, SHA-256 हैश, अभिरक्षा शृंखला और सत्यापन स्थिति जुड़ी है। प्रसंस्करण क्रम: OCR-अमूर्तन → सफ़ाई → भाषा पहचान → सामान्यीकरण → इकाई एवं घटना निष्कर्षण।',
  },
  network: {
    tagline: 'नेटवर्क आसूचना',
    title: 'साक्ष्य-आधारित संबंध ग्राफ़',
    description:
      'प्रत्येक कड़ी अपने संबंध प्रकार, समय-चिह्न, स्रोत दस्तावेज़, साक्ष्य ID, समर्थन स्तर और सत्यापन स्थिति के साथ आती है। संरचनात्मक प्रमुखता कभी आरोप नहीं है।',
  },
  timeline: {
    tagline: 'कालिक विश्लेषण',
    title: 'समयरेखा और व्यवहार प्रतिरूप',
    description:
      'साक्ष्य-समर्थित घटनाओं का कालानुक्रमिक पुनर्निर्माण, दोहरावदार गतिविधि, गतिविधि उछाल, कालिक अतिव्यापन और संभावित काल-स्थानिक अभिसरण। सह-उपस्थिति एक संकेत है, संपर्क का प्रमाण नहीं।',
  },
  map: {
    tagline: 'भू-स्थानिक आसूचना',
    title: 'मानचित्र और काल-स्थानिक अभिसरण',
    description:
      'केवल वे स्थान अंकित हैं जो पंजीकृत साक्ष्य में आते हैं। चिह्न का आकार साक्ष्य-समर्थित घटनाओं की संख्या दर्शाता है, कोई जोखिम स्कोर नहीं।',
  },
  crossCase: {
    tagline: 'अंतर-केस अन्वेषण',
    title: 'अलग-अलग केसों में साझा पहचानकर्ता',
    description:
      'केसों का सहसंबंध ठोस पहचानकर्ताओं (वाहन, फ़ोन, खाता), अनुमानित नाम-मिलान, साझा स्थानों और कालिक निकटता पर किया जाता है। प्रत्येक संबंध एक अभ्यर्थी है जिसे मानव सत्यापन चाहिए।',
  },
  entities: {
    tagline: 'इकाई समाधान',
    title: 'क्या ये अभिलेख एक ही पहचान हैं?',
    description:
      'सामान्यीकरण → टोकन तुलना → RapidFuzz अनुमानित समानता → बहु-गुण अंकन। पहचानें कभी स्वतः विलय नहीं की जातीं; प्लेटफ़ॉर्म केवल मानव निर्णय हेतु अभ्यर्थी प्रस्तावित करता है।',
  },
  hypotheses: {
    tagline: 'अन्वेषण तर्कण',
    title: 'साक्ष्य समर्थन के अनुसार क्रमित प्रतिस्पर्धी परिकल्पनाएँ',
    description:
      'प्रत्येक अवलोकन के लिए तर्कण एजेंट वैकल्पिक व्याख्याएँ उत्पन्न करता है — निर्दोष और संयोगवश वाली भी — और उन्हें केवल समर्थक या विरोधी साक्ष्य के आधार पर क्रमित करता है।',
  },
  gaps: {
    tagline: 'ज्ञात बनाम अज्ञात',
    title: 'सूचना अंतराल विश्लेषण',
    description:
      'प्रत्येक विश्लेषणात्मक सूत्र के लिए प्लेटफ़ॉर्म बताता है कि क्या ज्ञात है, क्या अनुपलब्ध है और कौन-सा साक्ष्य उस अंतराल को भरेगा। अनुपलब्ध साक्ष्य स्पष्ट रूप से नामित होता है — उसे अनुमान से नहीं भरा जाता।',
  },
  nextBest: {
    tagline: 'अगली सर्वोत्तम विश्लेषणात्मक कार्रवाई',
    title: 'आगे किसकी जाँच हो — और क्यों',
    description:
      'कार्रवाइयाँ अपेक्षित सूचना-मूल्य के अनुसार क्रमित होती हैं: वे कितने खुले अंतराल भरती हैं और वर्तमान सूत्रों को कितना मज़बूत या कमज़ोर करेंगी। इस सूची में केवल विश्लेषणात्मक चरण हैं।',
  },
  audit: {
    tagline: 'अंकेक्षण और साक्ष्य अखंडता',
    title: 'प्रत्येक क्रिया का छेड़छाड़-सूचक अभिलेख',
    description:
      'प्रत्येक लॉगिन, साक्ष्य क्रिया, विश्लेषण संचालन और मानव निर्णय एक हैश-शृंखलित अंकेक्षण पथ में जोड़ा जाता है। साक्ष्य वस्तुएँ ग्रहण के समय SHA-256 से हैश की जाती हैं और माँग पर पुनः सत्यापित होती हैं।',
  },
  security: {
    tagline: 'सेटिंग्स और सुरक्षा',
    title: 'सुरक्षा स्थिति, पहुँच नियंत्रण और सिस्टम प्रोफ़ाइल',
    description:
      'प्रमाणीकरण, भूमिका-आधारित प्राधिकरण, केस-स्तरीय सीमन, ट्रांसपोर्ट सुरक्षा, कूटलेखन, साक्ष्य हैशिंग और अंकेक्षण/लेजर सतह — सब सर्वर पर लागू।',
  },
  workflow: {
    tagline: 'अन्वेषण कार्यप्रवाह',
    title: 'पूरी पाइपलाइन आद्योपांत चलाएँ',
    description:
      'लॉगिन → केस → साक्ष्य → निष्कर्षण → समाधान → अंतर-केस → ग्राफ़ → नेटवर्क → समयरेखा → संपुष्टि → अंतराल → अगली कार्रवाई → मानव सत्यापन → अखंडता → अंकेक्षण। प्रत्येक चरण वास्तविक सेवा को कॉल करता है और वास्तविक परिणाम बताता है।',
  },
  caseDetails: {
    tagline: 'केस',
    title: 'केस फ़ाइल',
    description: '',
  },
}

export const pages: Tri<Shape> = { en, ta, hi }
