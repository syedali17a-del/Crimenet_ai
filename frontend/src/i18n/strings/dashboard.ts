import type { Tri } from '../tri'

/**
 * Dashboard copy.
 *
 * Numbers, case ids, evidence ids and hashes are interpolated verbatim; only
 * the surrounding language changes.
 */
const en = {
  refresh: 'Refresh',
  runFullAnalysis: 'Run full analysis',
  loading: 'Assembling command centre…',
  contextCase: (id: string, title: string) =>
    `Case context: ${id} — ${title}. Every figure below links to the analysis that produced it.`,
  contextAll:
    'Aggregated across all cases you are authorized to access. Select a case in the top bar to narrow the context.',

  kpiActiveCases: 'Active cases',
  kpiActiveCasesHint: (n: number) => `${n} authorized`,
  kpiEvidence: 'Evidence items',
  kpiEvidenceHint: 'registered & hashed',
  kpiCandidateRels: 'Candidate relationships',
  kpiCandidateRelsHint: 'awaiting corroboration',
  kpiCrossCase: 'Cross-case links',
  kpiCrossCaseHint: 'candidate associations',
  kpiGaps: 'Information gaps',
  kpiGapsHint: 'missing evidence',
  kpiPending: 'Pending verifications',
  kpiPendingHint: 'human decision required',

  pipelineTitle: 'Evidence → Network → Intelligence',
  pipelineSubtitle: 'The workflow this console follows, end to end.',
  flow: {
    evidence: 'Evidence',
    entities: 'Entities',
    network: 'Network',
    temporal: 'Temporal',
    corroboration: 'Corroboration',
    gaps: 'Gaps',
    nextAction: 'Next action',
    validation: 'Validation',
  },

  networkPreview: 'Network preview',
  networkPreviewSub: (nodes: number, edges: number) =>
    `${nodes} entities · ${edges} evidence-backed relationships`,
  openNetwork: 'Open Network Intelligence',

  findings: 'Analytical findings',
  findingsSub: 'Corroboration across independent methods',
  allFindings: 'All findings',
  findingsNone: 'No analytical lead reaches a supportable threshold in this scope.',
  missing: 'Missing',

  integrity: 'Integrity status',
  integritySub: 'SHA-256 registry + permissioned ledger',
  auditShort: 'Audit',
  objectsVerified: 'Objects verified',
  ledgerBlocks: 'Ledger blocks',
  chainHead: 'Chain head',
  chainIntact: 'Chain intact',
  chainBroken: 'Chain broken',

  timelinePreview: 'Timeline preview',
  timelinePreviewSub: 'Chronological evidence-backed events',
  fullTimeline: 'Full timeline',
  timelineNone: 'No timestamped events available in this scope.',
  noEvidenceRef: 'no evidence ref',

  recentEvidence: 'Recent evidence',
  recentEvidenceSub: 'Latest registry entries',
  evidenceRegistry: 'Evidence registry',
  evidenceNone: 'No evidence registered in this scope.',

  pendingValidation: 'Pending human validation',
  pendingValidationSub: 'Candidate relationships awaiting a decision',
  pendingValidationNone: 'Nothing awaiting verification in this scope.',
  reviewInGraph: 'Review in graph',

  gapsTitle: 'Information gaps',
  gapsSub: 'What is missing, stated explicitly',
  gapsNone: 'No open information gaps in this scope.',
  allGaps: 'All gaps',

  nextAnalysis: 'Recommended next analysis',
  nextAnalysisSub: 'Ranked by expected information value',
  rank1: 'Rank 1',
  infoValue: (pct: number) => `${pct}% info value`,
  nextAnalysisNone: 'No analytical action is currently prioritised for this scope.',
  openDecisionSupport: 'Open decision support',

  recentAudit: 'Recent audit events',
  fullTrail: 'Full trail',
  signedInAs: (name: string, role: string, classification: string) =>
    `Signed in as ${name} (${role}) · ${classification} · No real person, vehicle, account or case is represented.`,
}

type Shape = typeof en

const ta: Shape = {
  refresh: 'புதுப்பி',
  runFullAnalysis: 'முழுப் பகுப்பாய்வை இயக்கு',
  loading: 'கட்டளை மையம் தயாராகிறது…',
  contextCase: (id, title) =>
    `வழக்குச் சூழல்: ${id} — ${title}. கீழே உள்ள ஒவ்வொரு எண்ணும் அதை உருவாக்கிய பகுப்பாய்வுக்கு இணைக்கிறது.`,
  contextAll:
    'நீங்கள் அணுக அங்கீகரிக்கப்பட்ட அனைத்து வழக்குகளிலிருந்தும் தொகுக்கப்பட்டது. சூழலைக் குறுக்க மேல் பட்டியில் ஒரு வழக்கைத் தேர்ந்தெடுக்கவும்.',

  kpiActiveCases: 'செயலில் உள்ள வழக்குகள்',
  kpiActiveCasesHint: (n) => `${n} அங்கீகரிக்கப்பட்டவை`,
  kpiEvidence: 'ஆதாரப் பொருள்கள்',
  kpiEvidenceHint: 'பதிவு செய்யப்பட்டு ஹாஷ் செய்யப்பட்டவை',
  kpiCandidateRels: 'வேட்பாளர் உறவுகள்',
  kpiCandidateRelsHint: 'உறுதிப்படுத்தல் நிலுவையில்',
  kpiCrossCase: 'வழக்குகளுக்கிடையேயான இணைப்புகள்',
  kpiCrossCaseHint: 'வேட்பாளர் தொடர்புகள்',
  kpiGaps: 'தகவல் இடைவெளிகள்',
  kpiGapsHint: 'இல்லாத ஆதாரம்',
  kpiPending: 'நிலுவையில் உள்ள சரிபார்ப்புகள்',
  kpiPendingHint: 'மனித முடிவு தேவை',

  pipelineTitle: 'ஆதாரம் → நெட்வொர்க் → நுண்ணறிவு',
  pipelineSubtitle: 'இந்தக் கட்டுப்பாட்டு அமைப்பு பின்பற்றும் முழுப் பணிப்பாய்வு.',
  flow: {
    evidence: 'ஆதாரம்',
    entities: 'நிறுவனங்கள்',
    network: 'நெட்வொர்க்',
    temporal: 'கால ஆய்வு',
    corroboration: 'உறுதிப்படுத்தல்',
    gaps: 'இடைவெளிகள்',
    nextAction: 'அடுத்த நடவடிக்கை',
    validation: 'சரிபார்ப்பு',
  },

  networkPreview: 'நெட்வொர்க் முன்னோட்டம்',
  networkPreviewSub: (nodes, edges) => `${nodes} நிறுவனங்கள் · ${edges} ஆதாரம் உள்ள உறவுகள்`,
  openNetwork: 'நெட்வொர்க் நுண்ணறிவைத் திற',

  findings: 'பகுப்பாய்வுக் கண்டறிதல்கள்',
  findingsSub: 'சுயாதீன முறைகள் மூலம் உறுதிப்படுத்தல்',
  allFindings: 'அனைத்துக் கண்டறிதல்கள்',
  findingsNone: 'இந்த வரம்பில் எந்தப் பகுப்பாய்வுத் தடயமும் ஆதரிக்கத்தக்க அளவை எட்டவில்லை.',
  missing: 'இல்லாதவை',

  integrity: 'ஒருமைப்பாட்டு நிலை',
  integritySub: 'SHA-256 பதிவேடு + அனுமதி அடிப்படையிலான லெட்ஜர்',
  auditShort: 'தணிக்கை',
  objectsVerified: 'சரிபார்க்கப்பட்ட பொருள்கள்',
  ledgerBlocks: 'லெட்ஜர் தொகுதிகள்',
  chainHead: 'சங்கிலி முனை',
  chainIntact: 'சங்கிலி அப்படியே உள்ளது',
  chainBroken: 'சங்கிலி உடைந்துள்ளது',

  timelinePreview: 'காலவரிசை முன்னோட்டம்',
  timelinePreviewSub: 'ஆதாரம் உள்ள நிகழ்வுகளின் காலவரிசை',
  fullTimeline: 'முழுக் காலவரிசை',
  timelineNone: 'இந்த வரம்பில் நேர முத்திரை கொண்ட நிகழ்வுகள் இல்லை.',
  noEvidenceRef: 'ஆதாரக் குறிப்பு இல்லை',

  recentEvidence: 'சமீபத்திய ஆதாரம்',
  recentEvidenceSub: 'சமீபத்திய பதிவேட்டு உள்ளீடுகள்',
  evidenceRegistry: 'ஆதாரப் பதிவேடு',
  evidenceNone: 'இந்த வரம்பில் ஆதாரம் எதுவும் பதிவு செய்யப்படவில்லை.',

  pendingValidation: 'நிலுவையில் உள்ள மனிதச் சரிபார்ப்பு',
  pendingValidationSub: 'முடிவுக்காகக் காத்திருக்கும் வேட்பாளர் உறவுகள்',
  pendingValidationNone: 'இந்த வரம்பில் சரிபார்ப்புக்கு எதுவும் காத்திருக்கவில்லை.',
  reviewInGraph: 'வரைபடத்தில் பரிசீலி',

  gapsTitle: 'தகவல் இடைவெளிகள்',
  gapsSub: 'என்ன இல்லை என்பது வெளிப்படையாக',
  gapsNone: 'இந்த வரம்பில் திறந்த தகவல் இடைவெளிகள் இல்லை.',
  allGaps: 'அனைத்து இடைவெளிகள்',

  nextAnalysis: 'பரிந்துரைக்கப்பட்ட அடுத்த பகுப்பாய்வு',
  nextAnalysisSub: 'எதிர்பார்க்கப்படும் தகவல் மதிப்பின்படி தரவரிசை',
  rank1: 'தரவரிசை 1',
  infoValue: (pct) => `${pct}% தகவல் மதிப்பு`,
  nextAnalysisNone: 'இந்த வரம்பிற்கு தற்போது எந்தப் பகுப்பாய்வு நடவடிக்கையும் முன்னுரிமை பெறவில்லை.',
  openDecisionSupport: 'முடிவு ஆதரவைத் திற',

  recentAudit: 'சமீபத்திய தணிக்கை நிகழ்வுகள்',
  fullTrail: 'முழுப் பதிவு',
  signedInAs: (name, role, classification) =>
    `${name} (${role}) ஆக உள்நுழைந்துள்ளீர்கள் · ${classification} · உண்மையான நபர், வாகனம், கணக்கு அல்லது வழக்கு எதுவும் இதில் இல்லை.`,
}

const hi: Shape = {
  refresh: 'ताज़ा करें',
  runFullAnalysis: 'पूर्ण विश्लेषण चलाएँ',
  loading: 'कमांड सेंटर तैयार किया जा रहा है…',
  contextCase: (id, title) =>
    `केस संदर्भ: ${id} — ${title}। नीचे दिया गया प्रत्येक आँकड़ा उस विश्लेषण से जुड़ा है जिसने उसे बनाया।`,
  contextAll:
    'उन सभी केसों का समुच्चय जिन तक आपकी पहुँच अनुमत है। संदर्भ सीमित करने हेतु ऊपर की पट्टी में केस चुनें।',

  kpiActiveCases: 'सक्रिय केस',
  kpiActiveCasesHint: (n) => `${n} अधिकृत`,
  kpiEvidence: 'साक्ष्य मदें',
  kpiEvidenceHint: 'पंजीकृत और हैश किए गए',
  kpiCandidateRels: 'अभ्यर्थी संबंध',
  kpiCandidateRelsHint: 'संपुष्टि प्रतीक्षित',
  kpiCrossCase: 'अंतर-केस कड़ियाँ',
  kpiCrossCaseHint: 'अभ्यर्थी संबंध',
  kpiGaps: 'सूचना अंतराल',
  kpiGapsHint: 'अनुपलब्ध साक्ष्य',
  kpiPending: 'लंबित सत्यापन',
  kpiPendingHint: 'मानव निर्णय आवश्यक',

  pipelineTitle: 'साक्ष्य → नेटवर्क → आसूचना',
  pipelineSubtitle: 'यह कंसोल आद्योपांत जिस कार्यप्रवाह का पालन करता है।',
  flow: {
    evidence: 'साक्ष्य',
    entities: 'इकाइयाँ',
    network: 'नेटवर्क',
    temporal: 'कालिक',
    corroboration: 'संपुष्टि',
    gaps: 'अंतराल',
    nextAction: 'अगली कार्रवाई',
    validation: 'सत्यापन',
  },

  networkPreview: 'नेटवर्क पूर्वावलोकन',
  networkPreviewSub: (nodes, edges) => `${nodes} इकाइयाँ · ${edges} साक्ष्य-समर्थित संबंध`,
  openNetwork: 'नेटवर्क आसूचना खोलें',

  findings: 'विश्लेषणात्मक निष्कर्ष',
  findingsSub: 'स्वतंत्र विधियों द्वारा संपुष्टि',
  allFindings: 'सभी निष्कर्ष',
  findingsNone: 'इस दायरे में कोई भी विश्लेषणात्मक सूत्र समर्थनयोग्य सीमा तक नहीं पहुँचता।',
  missing: 'अनुपलब्ध',

  integrity: 'अखंडता स्थिति',
  integritySub: 'SHA-256 रजिस्टर + अनुमति-आधारित लेजर',
  auditShort: 'अंकेक्षण',
  objectsVerified: 'सत्यापित वस्तुएँ',
  ledgerBlocks: 'लेजर ब्लॉक',
  chainHead: 'शृंखला शीर्ष',
  chainIntact: 'शृंखला अक्षुण्ण',
  chainBroken: 'शृंखला भंग',

  timelinePreview: 'समयरेखा पूर्वावलोकन',
  timelinePreviewSub: 'साक्ष्य-समर्थित घटनाओं का कालक्रम',
  fullTimeline: 'पूरी समयरेखा',
  timelineNone: 'इस दायरे में समय-चिह्नित घटनाएँ उपलब्ध नहीं हैं।',
  noEvidenceRef: 'कोई साक्ष्य संदर्भ नहीं',

  recentEvidence: 'हाल का साक्ष्य',
  recentEvidenceSub: 'नवीनतम रजिस्टर प्रविष्टियाँ',
  evidenceRegistry: 'साक्ष्य रजिस्टर',
  evidenceNone: 'इस दायरे में कोई साक्ष्य पंजीकृत नहीं है।',

  pendingValidation: 'लंबित मानव सत्यापन',
  pendingValidationSub: 'निर्णय की प्रतीक्षा में अभ्यर्थी संबंध',
  pendingValidationNone: 'इस दायरे में सत्यापन हेतु कुछ भी लंबित नहीं है।',
  reviewInGraph: 'ग्राफ़ में समीक्षा करें',

  gapsTitle: 'सूचना अंतराल',
  gapsSub: 'क्या अनुपलब्ध है, स्पष्ट रूप से',
  gapsNone: 'इस दायरे में कोई खुला सूचना अंतराल नहीं है।',
  allGaps: 'सभी अंतराल',

  nextAnalysis: 'अनुशंसित अगला विश्लेषण',
  nextAnalysisSub: 'अपेक्षित सूचना-मूल्य के अनुसार क्रमित',
  rank1: 'क्रम 1',
  infoValue: (pct) => `${pct}% सूचना-मूल्य`,
  nextAnalysisNone: 'इस दायरे के लिए फ़िलहाल कोई विश्लेषणात्मक कार्रवाई प्राथमिकता पर नहीं है।',
  openDecisionSupport: 'निर्णय सहायता खोलें',

  recentAudit: 'हाल की अंकेक्षण घटनाएँ',
  fullTrail: 'पूरा पथ',
  signedInAs: (name, role, classification) =>
    `${name} (${role}) के रूप में साइन-इन · ${classification} · कोई वास्तविक व्यक्ति, वाहन, खाता या केस निरूपित नहीं है।`,
}

export const dashboard: Tri<Shape> = { en, ta, hi }
