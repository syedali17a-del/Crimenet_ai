import type { Tri } from '../tri'

const en = {
  // ---- language selection screen (shown BEFORE login) --------------------
  chooseLanguage: 'Select Your Language',
  chooseLanguageHint: 'Choose the language for the entire investigator console.',
  chooseLanguageFoot:
    'You can change the language at any time from the top bar after signing in.',
  continue: 'Continue',
  selected: 'Selected',

  // ---- login -------------------------------------------------------------
  secureAccess: 'Secure Investigator Access',
  secureAccessSub: 'JWT session · RBAC · case-level authorization',
  userIdLabel: 'Officer / User ID',
  passwordLabel: 'Password',
  showPassword: 'Show password',
  hidePassword: 'Hide password',
  capsLockOn: 'Caps Lock is on',
  rememberSession: 'Remember session on this device',
  sessionLength: 'Session 480 min',
  signIn: 'Sign In',
  signInSteps: ['Authenticating credentials', 'Establishing JWT session', 'Loading authorized cases'],
  bothFieldsRequired: 'Officer/User ID and password are both required.',
  signInFailed: 'Sign-in failed. Please try again.',
  backendUnreachable:
    'The analytical services are not reachable. Confirm the backend is running on port 8000, then retry.',
  servicesOnline: 'Analytical services online',
  servicesOffline: 'Analytical services offline',
  servicesChecking: 'Checking analytical services…',

  demoAccounts: 'Demonstration accounts (synthetic)',
  demoAccountsHint: 'one click to fill',
  demoAccountsEmpty:
    'Demonstration accounts load from the backend. They will appear once the analytical services respond.',
  syntheticNotice:
    'All data in this environment is SYNTHETIC DEMONSTRATION DATA. No real person, vehicle, account or case is represented. Roles change what the backend authorizes — permissions are enforced server-side, never in the browser.',
  restrictedFooter: 'Restricted analytical environment · Access is logged to the audit trail',

  roleNote: {
    INVESTIGATOR: 'Assigned cases · process evidence · submit findings',
    ANALYST: 'Run analytical services across authorized cases',
    SUPERVISOR: 'Verify or reject findings · assign and close cases',
    ADMIN: 'Users, roles, permissions and the full assurance surface',
    DEFAULT: 'Authorized analytical access',
  },

  // ---- left intelligence panel -------------------------------------------
  intro:
    'CrimeNet AI reconstructs investigative networks strictly from the evidence that exists — extracting entities and events from fragmented records, resolving candidate identities, corroborating findings across independent analytical methods, and stating plainly what remains unknown.',
  pillars: [
    {
      title: 'Evidence-first',
      text: 'Every relationship carries its source document, timestamp, evidence ID and SHA-256 hash.',
    },
    {
      title: 'Reconstructed networks',
      text: 'Entities, vehicles, accounts and locations are linked only where evidence supports it.',
    },
    {
      title: 'Known vs unknown',
      text: 'The platform names what is missing instead of guessing — “Insufficient Evidence” is a valid answer.',
    },
    {
      title: 'Human-controlled',
      text: 'Identities are never auto-merged; analytical candidates require investigator verification.',
    },
  ],
  pipelineLabel: 'Analytical pipeline',
  pipeline: [
    'Evidence', 'Extraction', 'Resolution', 'Cross-case', 'Graph',
    'Analysis', 'Corroboration', 'Gaps', 'Validation', 'Audit',
  ],
}

type Shape = typeof en

const ta: Shape = {
  chooseLanguage: 'உங்கள் மொழியைத் தேர்ந்தெடுக்கவும்',
  chooseLanguageHint: 'முழு புலனாய்வுக் கட்டுப்பாட்டு அமைப்பிற்கான மொழியைத் தேர்ந்தெடுக்கவும்.',
  chooseLanguageFoot:
    'உள்நுழைந்த பிறகு மேல் பட்டியில் இருந்து எப்போது வேண்டுமானாலும் மொழியை மாற்றலாம்.',
  continue: 'தொடர',
  selected: 'தேர்ந்தெடுக்கப்பட்டது',

  secureAccess: 'பாதுகாப்பான புலனாய்வாளர் அணுகல்',
  secureAccessSub: 'JWT அமர்வு · RBAC · வழக்கு அளவிலான அங்கீகாரம்',
  userIdLabel: 'அதிகாரி / பயனர் ID',
  passwordLabel: 'கடவுச்சொல்',
  showPassword: 'கடவுச்சொல்லைக் காட்டு',
  hidePassword: 'கடவுச்சொல்லை மறை',
  capsLockOn: 'Caps Lock இயக்கத்தில் உள்ளது',
  rememberSession: 'இந்தச் சாதனத்தில் அமர்வை நினைவில் வைக்கவும்',
  sessionLength: 'அமர்வு 480 நிமிடங்கள்',
  signIn: 'உள்நுழை',
  signInSteps: [
    'சான்றுகள் சரிபார்க்கப்படுகின்றன',
    'JWT அமர்வு உருவாக்கப்படுகிறது',
    'அங்கீகரிக்கப்பட்ட வழக்குகள் ஏற்றப்படுகின்றன',
  ],
  bothFieldsRequired: 'அதிகாரி/பயனர் ID மற்றும் கடவுச்சொல் இரண்டும் கட்டாயம்.',
  signInFailed: 'உள்நுழைவு தோல்வியடைந்தது. மீண்டும் முயற்சிக்கவும்.',
  backendUnreachable:
    'பகுப்பாய்வு சேவைகளை அணுக முடியவில்லை. பின்தள சேவை போர்ட் 8000 இல் இயங்குகிறதா எனச் சரிபார்த்து மீண்டும் முயற்சிக்கவும்.',
  servicesOnline: 'பகுப்பாய்வு சேவைகள் இயங்குகின்றன',
  servicesOffline: 'பகுப்பாய்வு சேவைகள் இயங்கவில்லை',
  servicesChecking: 'பகுப்பாய்வு சேவைகள் சரிபார்க்கப்படுகின்றன…',

  demoAccounts: 'விளக்கக் கணக்குகள் (செயற்கை)',
  demoAccountsHint: 'ஒரு சொடுக்கில் நிரப்பவும்',
  demoAccountsEmpty:
    'விளக்கக் கணக்குகள் பின்தளத்திலிருந்து ஏற்றப்படும். பகுப்பாய்வு சேவைகள் பதிலளித்ததும் அவை தோன்றும்.',
  syntheticNotice:
    'இந்தச் சூழலில் உள்ள அனைத்துத் தரவும் செயற்கை விளக்கத் தரவு ஆகும். எந்த உண்மையான நபர், வாகனம், கணக்கு அல்லது வழக்கும் இதில் இல்லை. பணி நிலைகள் பின்தளம் அளிக்கும் அனுமதியை மாற்றுகின்றன — அனுமதிகள் சேவையகத்தில் அமல்படுத்தப்படுகின்றன, உலாவியில் அல்ல.',
  restrictedFooter: 'கட்டுப்படுத்தப்பட்ட பகுப்பாய்வுச் சூழல் · அணுகல் தணிக்கைப் பதிவில் பதிவாகும்',

  roleNote: {
    INVESTIGATOR: 'ஒதுக்கப்பட்ட வழக்குகள் · ஆதாரம் செயலாக்கம் · கண்டறிதல் சமர்ப்பிப்பு',
    ANALYST: 'அங்கீகரிக்கப்பட்ட வழக்குகளில் பகுப்பாய்வு சேவைகளை இயக்குதல்',
    SUPERVISOR: 'கண்டறிதல்களைச் சரிபார்த்தல் அல்லது நிராகரித்தல் · வழக்குகளை ஒதுக்குதல், மூடுதல்',
    ADMIN: 'பயனர்கள், பணி நிலைகள், அனுமதிகள் மற்றும் முழு உறுதிப்பாட்டுப் பரப்பு',
    DEFAULT: 'அங்கீகரிக்கப்பட்ட பகுப்பாய்வு அணுகல்',
  },

  intro:
    'CrimeNet AI, இருக்கும் ஆதாரங்களை மட்டுமே அடிப்படையாகக் கொண்டு விசாரணை நெட்வொர்க்குகளை மறுகட்டமைக்கிறது — சிதறிய பதிவுகளிலிருந்து நிறுவனங்களையும் நிகழ்வுகளையும் பிரித்தெடுத்து, சாத்தியமான அடையாளங்களைத் தீர்த்து, சுயாதீன பகுப்பாய்வு முறைகள் மூலம் கண்டறிதல்களை உறுதிப்படுத்தி, தெரியாதவை எவை என்பதைத் தெளிவாகக் கூறுகிறது.',
  pillars: [
    {
      title: 'ஆதாரம் முதன்மை',
      text: 'ஒவ்வொரு தொடர்பும் அதன் மூல ஆவணம், நேர முத்திரை, ஆதார ID மற்றும் SHA-256 ஹாஷுடன் வருகிறது.',
    },
    {
      title: 'மறுகட்டமைக்கப்பட்ட நெட்வொர்க்குகள்',
      text: 'ஆதாரம் ஆதரிக்கும் இடங்களில் மட்டுமே நிறுவனங்கள், வாகனங்கள், கணக்குகள், இருப்பிடங்கள் இணைக்கப்படுகின்றன.',
    },
    {
      title: 'தெரிந்தவை vs தெரியாதவை',
      text: 'ஊகிக்காமல் எவை காணவில்லை என்பதை அமைப்பு பெயரிடுகிறது — “போதுமான ஆதாரங்கள் இல்லை” என்பதும் ஒரு சரியான பதில்.',
    },
    {
      title: 'மனிதக் கட்டுப்பாடு',
      text: 'அடையாளங்கள் தானாக இணைக்கப்படுவதில்லை; பகுப்பாய்வுச் சாத்தியங்களுக்குப் புலனாய்வாளர் சரிபார்ப்பு தேவை.',
    },
  ],
  pipelineLabel: 'பகுப்பாய்வுப் பாதை',
  pipeline: [
    'ஆதாரம', 'பிரித்தெடுத்தல்', 'அடையாளத் தீர்வு', 'வழக்கு-இடை', 'வரைபடம்',
    'பகுப்பாய்வு', 'உறுதிப்பாடு', 'இடைவெளிகள்', 'சரிபார்ப்பு', 'தணிக்கை',
  ],
}

const hi: Shape = {
  chooseLanguage: 'अपनी भाषा चुनें',
  chooseLanguageHint: 'सम्पूर्ण जाँच कंसोल के लिए भाषा चुनें।',
  chooseLanguageFoot:
    'साइन इन करने के बाद आप किसी भी समय शीर्ष बार से भाषा बदल सकते हैं।',
  continue: 'जारी रखें',
  selected: 'चयनित',

  secureAccess: 'सुरक्षित जाँचकर्ता पहुँच',
  secureAccessSub: 'JWT सत्र · RBAC · मामला-स्तरीय प्राधिकरण',
  userIdLabel: 'अधिकारी / उपयोगकर्ता ID',
  passwordLabel: 'पासवर्ड',
  showPassword: 'पासवर्ड दिखाएँ',
  hidePassword: 'पासवर्ड छिपाएँ',
  capsLockOn: 'Caps Lock चालू है',
  rememberSession: 'इस डिवाइस पर सत्र याद रखें',
  sessionLength: 'सत्र 480 मिनट',
  signIn: 'साइन इन',
  signInSteps: [
    'प्रमाण-पत्र सत्यापित किए जा रहे हैं',
    'JWT सत्र स्थापित किया जा रहा है',
    'अधिकृत मामले लोड किए जा रहे हैं',
  ],
  bothFieldsRequired: 'अधिकारी/उपयोगकर्ता ID और पासवर्ड दोनों आवश्यक हैं।',
  signInFailed: 'साइन-इन विफल रहा। कृपया पुनः प्रयास करें।',
  backendUnreachable:
    'विश्लेषणात्मक सेवाएँ उपलब्ध नहीं हैं। जाँचें कि बैकएंड पोर्ट 8000 पर चल रहा है, फिर पुनः प्रयास करें।',
  servicesOnline: 'विश्लेषणात्मक सेवाएँ ऑनलाइन',
  servicesOffline: 'विश्लेषणात्मक सेवाएँ ऑफ़लाइन',
  servicesChecking: 'विश्लेषणात्मक सेवाएँ जाँची जा रही हैं…',

  demoAccounts: 'प्रदर्शन खाते (सिंथेटिक)',
  demoAccountsHint: 'भरने के लिए एक क्लिक',
  demoAccountsEmpty:
    'प्रदर्शन खाते बैकएंड से लोड होते हैं। विश्लेषणात्मक सेवाओं के उत्तर देते ही ये दिखाई देंगे।',
  syntheticNotice:
    'इस वातावरण का सारा डेटा सिंथेटिक प्रदर्शन डेटा है। कोई वास्तविक व्यक्ति, वाहन, खाता या मामला प्रस्तुत नहीं किया गया है। भूमिकाएँ बदलती हैं कि बैकएंड क्या अधिकृत करता है — अनुमतियाँ सर्वर पर लागू होती हैं, ब्राउज़र में कभी नहीं।',
  restrictedFooter: 'प्रतिबंधित विश्लेषणात्मक वातावरण · पहुँच ऑडिट ट्रेल में दर्ज होती है',

  roleNote: {
    INVESTIGATOR: 'सौंपे गए मामले · साक्ष्य संसाधन · निष्कर्ष प्रस्तुत करना',
    ANALYST: 'अधिकृत मामलों पर विश्लेषणात्मक सेवाएँ चलाना',
    SUPERVISOR: 'निष्कर्ष सत्यापित या अस्वीकृत करना · मामले सौंपना और बंद करना',
    ADMIN: 'उपयोगकर्ता, भूमिकाएँ, अनुमतियाँ और सम्पूर्ण आश्वासन क्षेत्र',
    DEFAULT: 'अधिकृत विश्लेषणात्मक पहुँच',
  },

  intro:
    'CrimeNet AI केवल उपलब्ध साक्ष्यों के आधार पर जाँच नेटवर्क का पुनर्निर्माण करता है — बिखरे रिकॉर्ड से संस्थाएँ और घटनाएँ निकालता है, संभावित पहचानों का निर्धारण करता है, स्वतंत्र विश्लेषणात्मक विधियों से निष्कर्षों की पुष्टि करता है, और जो अज्ञात है उसे स्पष्ट रूप से बताता है।',
  pillars: [
    {
      title: 'साक्ष्य सर्वोपरि',
      text: 'प्रत्येक संबंध अपने स्रोत दस्तावेज़, समय-चिह्न, साक्ष्य ID और SHA-256 हैश के साथ आता है।',
    },
    {
      title: 'पुनर्निर्मित नेटवर्क',
      text: 'संस्थाएँ, वाहन, खाते और स्थान केवल वहीं जोड़े जाते हैं जहाँ साक्ष्य उनका समर्थन करता है।',
    },
    {
      title: 'ज्ञात बनाम अज्ञात',
      text: 'अनुमान लगाने के बजाय मंच बताता है कि क्या अनुपलब्ध है — “पर्याप्त साक्ष्य नहीं” भी एक वैध उत्तर है।',
    },
    {
      title: 'मानव-नियंत्रित',
      text: 'पहचानें कभी स्वतः विलय नहीं होतीं; विश्लेषणात्मक संभावनाओं के लिए जाँचकर्ता का सत्यापन आवश्यक है।',
    },
  ],
  pipelineLabel: 'विश्लेषणात्मक प्रवाह',
  pipeline: [
    'साक्ष्य', 'निष्कर्षण', 'पहचान-निर्धारण', 'क्रॉस-केस', 'ग्राफ़',
    'विश्लेषण', 'पुष्टिकरण', 'अंतराल', 'सत्यापन', 'ऑडिट',
  ],
}

export const auth: Tri<Shape> = { en, ta, hi }
