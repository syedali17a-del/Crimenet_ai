import type { Tri } from '../tri'

/**
 * Boot sequence copy.
 *
 * The splash runs BEFORE the language selection screen on a first visit, so it
 * renders in the last language the user chose (or English on a cold start).
 * Step detail lines that echo backend values (version, classification, health
 * status) keep their identifiers verbatim.
 */
const en = {
  stepClient: 'Initialising secure client',
  stepServices: 'Contacting analytical services',
  stepPlatform: 'Reading platform profile',
  stepSession: 'Restoring investigator session',

  detailClientReady: 'TLS session · JWT client ready',
  detailApiOnline: 'API online',
  detailNoResponse: 'No response from the analytical services',
  detailProfileUnavailable: 'Platform profile unavailable — continuing',
  detailSessionFound: 'Existing session found',
  detailNoSession: 'No active session — sign-in required',

  unreachableTitle: 'Analytical services unreachable',
  unreachableBody:
    'The CrimeNet AI analytical services are not reachable. Start the backend (uvicorn on port 8000) and retry — the platform will not present a sign-in form it cannot honour.',
  retryHandshake: 'Retry handshake',
  continueOffline: 'Continue offline',
  footer: 'Synthetic demonstration data · Restricted analytical environment',
}

type Shape = typeof en

const ta: Shape = {
  stepClient: 'பாதுகாப்பான கிளையண்ட் தொடங்கப்படுகிறது',
  stepServices: 'பகுப்பாய்வு சேவைகளுடன் தொடர்பு கொள்ளப்படுகிறது',
  stepPlatform: 'தள விவரக்குறிப்பு படிக்கப்படுகிறது',
  stepSession: 'புலனாய்வாளர் அமர்வு மீட்டெடுக்கப்படுகிறது',

  detailClientReady: 'TLS அமர்வு · JWT கிளையண்ட் தயார்',
  detailApiOnline: 'API இயங்குகிறது',
  detailNoResponse: 'பகுப்பாய்வு சேவைகளிடமிருந்து பதில் இல்லை',
  detailProfileUnavailable: 'தள விவரக்குறிப்பு கிடைக்கவில்லை — தொடர்கிறது',
  detailSessionFound: 'ஏற்கனவே உள்ள அமர்வு கண்டறியப்பட்டது',
  detailNoSession: 'செயலில் உள்ள அமர்வு இல்லை — உள்நுழைவு தேவை',

  unreachableTitle: 'பகுப்பாய்வு சேவைகளை அணுக முடியவில்லை',
  unreachableBody:
    'CrimeNet AI பகுப்பாய்வு சேவைகளை அணுக முடியவில்லை. பின்தளத்தை (போர்ட் 8000 இல் uvicorn) இயக்கி மீண்டும் முயற்சிக்கவும் — நிறைவேற்ற முடியாத உள்நுழைவுப் படிவத்தை இந்த அமைப்பு காட்டாது.',
  retryHandshake: 'கைகுலுக்கலை மீண்டும் முயற்சி',
  continueOffline: 'இணைப்பின்றி தொடர',
  footer: 'செயற்கை விளக்கத் தரவு · கட்டுப்படுத்தப்பட்ட பகுப்பாய்வுச் சூழல்',
}

const hi: Shape = {
  stepClient: 'सुरक्षित क्लाइंट आरंभ किया जा रहा है',
  stepServices: 'विश्लेषणात्मक सेवाओं से संपर्क किया जा रहा है',
  stepPlatform: 'प्लेटफ़ॉर्म प्रोफ़ाइल पढ़ी जा रही है',
  stepSession: 'अन्वेषक सत्र पुनर्स्थापित किया जा रहा है',

  detailClientReady: 'TLS सत्र · JWT क्लाइंट तैयार',
  detailApiOnline: 'API ऑनलाइन',
  detailNoResponse: 'विश्लेषणात्मक सेवाओं से कोई उत्तर नहीं',
  detailProfileUnavailable: 'प्लेटफ़ॉर्म प्रोफ़ाइल अनुपलब्ध — जारी है',
  detailSessionFound: 'मौजूदा सत्र मिला',
  detailNoSession: 'कोई सक्रिय सत्र नहीं — साइन-इन आवश्यक',

  unreachableTitle: 'विश्लेषणात्मक सेवाएँ अनुपलब्ध',
  unreachableBody:
    'CrimeNet AI विश्लेषणात्मक सेवाएँ उपलब्ध नहीं हैं। बैकएंड (पोर्ट 8000 पर uvicorn) प्रारंभ करें और पुनः प्रयास करें — यह प्लेटफ़ॉर्म ऐसा साइन-इन फ़ॉर्म नहीं दिखाएगा जिसे वह पूरा नहीं कर सकता।',
  retryHandshake: 'हैंडशेक पुनः प्रयास करें',
  continueOffline: 'ऑफ़लाइन जारी रखें',
  footer: 'सिंथेटिक प्रदर्शन डेटा · प्रतिबंधित विश्लेषणात्मक वातावरण',
}

export const boot: Tri<Shape> = { en, ta, hi }
