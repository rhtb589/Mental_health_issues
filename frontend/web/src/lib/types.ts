export interface User {
  user_id: string
  email: string | null
  role: string
  is_active: boolean
  prefers_de_identified: boolean
  data_residency_region: string
  anonymized: boolean
  created_at: string | null
}

export interface TokenPair {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface Assessment {
  assessment_id: string
  instrument_id: string
  instrument_version: string | null
  status: string
  high_risk: boolean
  high_risk_detail: string | null
  is_de_identified: boolean
  started_at: string
  completed_at: string | null
  score: any | null
  interpretation: string | null
}

export interface ConsentRecord {
  consent_id: string
  purpose: string
  status: string
  consent_text_version: string
  recorded_at: string
  is_active: boolean
  withdrawn_at: string | null
}

export interface AuditLog {
  event_id: string
  seq: number
  event_type: string
  occurred_at: string | null
  actor_user_id: string
  subject_user_id: string
  action: string
  resource_type: string
  resource_id: string
  metadata_json: string
}

export interface Assignment {
  assignment_id: string
  patient_id: string
  provider_id: string
  provider_role: string
  active: boolean
  created_at: string | null
  created_by: string
}

export interface DataRequest {
  request_id: string
  user_id: string
  request_type: string
  reason: string | null
  status: string
  requested_at: string | null
  processed_at: string | null
  processed_by: string | null
}

export interface DashboardStats {
  total_users: number
  active_users: number
  total_assessments: number
  completed_assessments: number
  high_risk_count: number
  total_consents: number
  active_consents: number
  by_instrument: { instrument_id: string; total: number; high_risk: number }[]
}

export interface ScreeningQuestion {
  id: string
  number?: number
  text: string
  prompt?: string
  response_type: 'single_choice' | 'multi_choice'
  safety_relevant?: boolean
  options?: { id: string; label: string; score?: number; code?: number }[]
  items?: string[]
  groups?: { id: string; group: string; items: string[] }[]
}

export interface ChatMessage {
  message_id: string
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

export interface Conversation {
  conversation_id: string
  messages: ChatMessage[]
  is_generating: boolean
  created_at: string
  updated_at: string
}
