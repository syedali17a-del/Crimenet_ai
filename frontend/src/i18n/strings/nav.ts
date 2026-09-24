import type { Tri } from '../tri'

const en = {
  groups: {
    Command: 'Command',
    Analysis: 'Analysis',
    Reasoning: 'Reasoning',
    Assurance: 'Assurance',
  },
  items: {
    dashboard: 'Dashboard',
    workflow: 'Workflow',
    cases: 'Cases',
    evidence: 'Evidence',
    network: 'Network',
    timeline: 'Timeline',
    map: 'Map',
    crossCase: 'Cross-Case',
    entities: 'Entities',
    hypotheses: 'Hypotheses',
    informationGaps: 'Information Gaps',
    nextBestAction: 'Next-Best Action',
    audit: 'Audit',
    security: 'Security',
  },
  openNavigation: 'Open navigation',
  closeNavigation: 'Close navigation',
  collapseSidebar: 'Collapse',
  workflowCardTitle: 'Workflow',

  searchPlaceholder: 'Search cases, entities, evidence…',
  searchAria: 'Global search',
  searchNoMatch: (q: string) => `No authorized records match “${q}”.`,

  notifications: 'Notifications',
  pendingValidation: 'Pending human validation',
  pendingValidationEmpty: 'No candidate findings are awaiting verification in this scope.',
  reviewInNetwork: 'Review in Network Intelligence →',

  activeCaseAria: 'Active case',
  allAuthorizedCases: 'All authorized cases',
  caseContext: (id: string) => `Case context: ${id}`,
  contextAllCases: 'Context: all authorized cases',
  caseAccess: 'Case access',
  allCases: 'All cases',

  language: 'Language',
  languageAria: 'Change interface language',
  currentLanguage: 'Current language',
}

type Shape = typeof en

const ta: Shape = {
  groups: {
    Command: 'கட்டுப்பாடு',
    Analysis: 'பகுப்பாய்வு',
    Reasoning: 'பகுத்தறிவு',
    Assurance: 'உறுதிப்பாடு',
  },
  items: {
    dashboard: 'டாஷ்போர்டு',
    workflow: 'பணிப்பாய்வு',
    cases: 'வழக்குகள்',
    evidence: 'ஆதாரம்',
    network: 'நெட்வொர்க்',
    timeline: 'கால வரிசை',
    map: 'வரைபடம்',
    crossCase: 'வழக்கு-இடை',
    entities: 'நிறுவனங்கள்',
    hypotheses: 'கருதுகோள்கள்',
    informationGaps: 'தகவல் இடைவெளிகள்',
    nextBestAction: 'அடுத்த சிறந்த நடவடிக்கை',
    audit: 'தணிக்கை',
    security: 'பாதுகாப்பு',
  },
  openNavigation: 'வழிசெலுத்தலைத் திற',
  closeNavigation: 'வழிசெலுத்தலை மூடு',
  collapseSidebar: 'சுருக்கு',
  workflowCardTitle: 'பணிப்பாய்வு',

  searchPlaceholder: 'வழக்குகள், நிறுவனங்கள், ஆதாரங்களைத் தேடுக…',
  searchAria: 'பொதுத் தேடல்',
  searchNoMatch: (q: string) => `“${q}” உடன் பொருந்தும் அங்கீகரிக்கப்பட்ட பதிவுகள் இல்லை.`,

  notifications: 'அறிவிப்புகள்',
  pendingValidation: 'மனித சரிபார்ப்புக்குக் காத்திருப்பவை',
  pendingValidationEmpty: 'இந்த வரம்பில் சரிபார்ப்புக்குக் காத்திருக்கும் கண்டறிதல்கள் எதுவும் இல்லை.',
  reviewInNetwork: 'நெட்வொர்க் நுண்ணறிவில் பரிசீலிக்க →',

  activeCaseAria: 'செயலில் உள்ள வழக்கு',
  allAuthorizedCases: 'அங்கீகரிக்கப்பட்ட அனைத்து வழக்குகள்',
  caseContext: (id: string) => `வழக்கு சூழல்: ${id}`,
  contextAllCases: 'சூழல்: அங்கீகரிக்கப்பட்ட அனைத்து வழக்குகள்',
  caseAccess: 'வழக்கு அணுகல்',
  allCases: 'அனைத்து வழக்குகள்',

  language: 'மொழி',
  languageAria: 'இடைமுக மொழியை மாற்று',
  currentLanguage: 'தற்போதைய மொழி',
}

const hi: Shape = {
  groups: {
    Command: 'कमांड',
    Analysis: 'विश्लेषण',
    Reasoning: 'तर्क',
    Assurance: 'आश्वासन',
  },
  items: {
    dashboard: 'डैशबोर्ड',
    workflow: 'कार्यप्रवाह',
    cases: 'मामले',
    evidence: 'साक्ष्य',
    network: 'नेटवर्क',
    timeline: 'समयरेखा',
    map: 'मानचित्र',
    crossCase: 'क्रॉस-केस',
    entities: 'संस्थाएँ',
    hypotheses: 'परिकल्पनाएँ',
    informationGaps: 'सूचना अंतराल',
    nextBestAction: 'अगली सर्वोत्तम कार्रवाई',
    audit: 'ऑडिट',
    security: 'सुरक्षा',
  },
  openNavigation: 'नेविगेशन खोलें',
  closeNavigation: 'नेविगेशन बंद करें',
  collapseSidebar: 'सिकोड़ें',
  workflowCardTitle: 'कार्यप्रवाह',

  searchPlaceholder: 'मामले, संस्थाएँ, साक्ष्य खोजें…',
  searchAria: 'वैश्विक खोज',
  searchNoMatch: (q: string) => `“${q}” से मेल खाने वाला कोई अधिकृत रिकॉर्ड नहीं है।`,

  notifications: 'सूचनाएँ',
  pendingValidation: 'मानव सत्यापन हेतु लंबित',
  pendingValidationEmpty: 'इस दायरे में सत्यापन की प्रतीक्षा करने वाला कोई निष्कर्ष नहीं है।',
  reviewInNetwork: 'नेटवर्क इंटेलिजेंस में समीक्षा करें →',

  activeCaseAria: 'सक्रिय मामला',
  allAuthorizedCases: 'सभी अधिकृत मामले',
  caseContext: (id: string) => `मामला संदर्भ: ${id}`,
  contextAllCases: 'संदर्भ: सभी अधिकृत मामले',
  caseAccess: 'मामला पहुँच',
  allCases: 'सभी मामले',

  language: 'भाषा',
  languageAria: 'इंटरफ़ेस भाषा बदलें',
  currentLanguage: 'वर्तमान भाषा',
}

export const nav: Tri<Shape> = { en, ta, hi }
