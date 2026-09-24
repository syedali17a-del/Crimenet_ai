export type Role = 'INVESTIGATOR' | 'ANALYST' | 'SUPERVISOR' | 'ADMIN'

export interface UserProfile {
  user_id: string
  display_name: string
  role: Role
  unit: string
  badge: string
  case_access: string[]
  permissions: string[]
}

export interface LoginResponse {
  access_token: string
  token_type: string
  expires_at: string
  expires_in: number
  user: UserProfile
  classification: string
}

export interface CaseOut {
  case_id: string
  title: string
  case_type: string
  priority: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
  description: string
  investigator: string
  created_date: string
  status: string
  classification: string
  evidence_count: number
  entity_count: number
  relationship_count: number
  open_gaps: number
}

export interface EvidenceItem {
  evidence_id: string
  case_id: string
  evidence_type: string
  source: string
  timestamp: string
  uploaded_by: string
  sha256: string
  integrity_status: string
  verification_status: string
  processing_status: string
  text_origin: string
  ocr_applied: boolean
  provenance: Array<Record<string, unknown>>
  notes: string
  classification: string
  size_bytes: number
}

export interface GraphNode {
  data: {
    id: string
    label: string
    entity_type: string
    cases: string[]
    support_level: string
    verification_status: string
    evidence_ids: string[]
    degree: number
    lat?: number | null
    lon?: number | null
  }
}

export interface GraphEdge {
  data: {
    id: string
    source: string
    target: string
    relationship_type: string
    timestamp: string
    evidence_id: string
    case_id: string
    support_level: string
    verification_status: string
    source_document: string
  }
}

export interface GraphPayload {
  case_ids: string[] | string
  nodes: GraphNode[]
  edges: GraphEdge[]
  counts: { nodes: number; edges: number }
  sufficient: boolean
  message: string
  classification: string
}

export interface Signal {
  signal: string
  value: string
  supports: boolean
  detail: string
}

export interface CrossCaseAssociation {
  link_id: string
  case_a: string
  case_a_title: string
  case_b: string
  case_b_title: string
  status: string
  support_level: string
  strength: number
  signals: Signal[]
  why_connected: string[]
  evidence_ids: string[]
  entity_pairs: Array<{ left: string; right: string; type: string; basis: string }>
  verification_status: string
  disclaimer: string
}

export interface CandidateMatch {
  match_id?: string
  left: { entity_id: string; label: string; cases: string[] }
  right: { entity_id: string; label: string; cases: string[] }
  score: number
  support_level: string
  name_similarity: number
  fuzzy: Record<string, number>
  tokens: { tokens_a: string[]; tokens_b: string[]; shared_tokens: string[]; initial_compatible: boolean; surname_match: boolean }
  signals: Signal[]
  shared: { vehicles: string[]; phones: string[]; locations: string[]; accounts: string[] }
  contradictions: string[]
  temporal_gap_days: number | null
  decision: string
  auto_merged: boolean
  verification_status?: string
}

export interface Lead {
  lead_id: string
  title: string
  subject_ids: string[]
  case_ids: string[]
  status: string
  support_level: string
  methods: Array<{ method: string; finding: string; agrees: boolean }>
  independent_sources: number
  supporting_evidence: Array<Record<string, string>>
  contradicting_evidence: Array<Record<string, unknown>>
  missing_evidence: string[]
  why: string[]
  verification_status: string
  disclaimer: string
}

export interface Hypothesis {
  hypothesis_id: string
  statement: string
  supporting_evidence: string[]
  supporting_signals?: string[]
  contradicting_evidence: (string | null)[]
  missing_information: string[]
  support_score: number
  support_level: string
  rank: number
}

export interface HypothesisSet {
  hypothesis_set_id: string
  observation: string
  case_ids: string[]
  subject_ids?: string[]
  hypotheses: Hypothesis[]
  status: string
  ranking_method?: string
  note: string
}

export interface InformationGap {
  gap_id: string
  lead_id: string
  case_ids: string[]
  question: string
  hypothesis: string
  known: string[]
  unknown: string[]
  gap_types: string[]
  severity: string
  status: string
  statement: string
  recommended_analysis: string
  recommended_action: NextAction | null
}

export interface NextAction {
  action_id: string
  title: string
  endpoint: string
  method: string
  addresses: string[]
  open_gaps_addressed?: number
  information_value: number
  rationale: string
  authorization?: string
  rank?: number
  case_ids?: string[]
}

export interface TimelineEvent {
  event_id: string
  case_id: string
  title: string
  timestamp: string
  location_id: string | null
  entity_ids: string[]
  evidence_id: string | null
  event_type: string
  description: string
  location_label?: string
  entity_labels?: string[]
}

export interface ConvergenceEvent {
  location_id: string
  window_start: string
  window_end: string
  entities: string[]
  events: Array<{ event_id: string; timestamp: string; title: string; evidence_id: string; entity_ids: string[] }>
  evidence_ids: string[]
  signals: Array<{ signal: string; present: boolean; detail: string }>
  status: string
  requires_review: boolean
  disclaimer: string
}

export interface AuditRecord {
  audit_id: string
  timestamp: string
  user_id: string
  role: string
  action: string
  case_id: string | null
  object_id: string | null
  status: string
  detail: string
  hash: string
}

export interface AgentTask {
  task_id: string
  plan_id: string
  name: string
  agent: string
  status: 'PENDING' | 'RUNNING' | 'COMPLETE' | 'SKIPPED' | 'FAILED'
  depends_on: string[]
  started_at: string | null
  finished_at: string | null
  summary: string
  result: Record<string, any>
}

export interface ManagerRun {
  plan_id: string
  objective: string
  title: string
  case_ids: string[]
  requested_by: string
  role: string
  started_at: string
  finished_at: string
  tasks: AgentTask[]
  results: Record<string, any>
  manager_constraints: Record<string, unknown>
  conclusion: {
    headline: string
    status: string
    why?: string[]
    missing_evidence?: string[]
    corroboration_summary: string
    open_gaps: number
    recommended_next_analysis: string | null
    human_decision_required: boolean
    principle: string
  }
}

export interface DashboardPayload {
  product: { name: string; tagline: string; description: string; principle: string; classification: string }
  scope: string[]
  kpis: Record<string, number>
  pipeline: Array<{ stage: string; value: number; detail: string }>
  network_preview: GraphPayload
  timeline_preview: TimelineEvent[]
  recent_evidence: EvidenceItem[]
  findings: Lead[]
  pending_validation: Array<Record<string, any>>
  information_gaps: InformationGap[]
  next_best_action: NextAction | null
  next_best_actions: NextAction[]
  integrity: { ledger_intact: boolean; ledger_blocks: number; head_hash: string; mismatches: string[]; verified: number; total: number }
  recent_audit: AuditRecord[]
}
