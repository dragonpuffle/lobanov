/** Mirrors backend enums / DTOs (see lobanov/app/api/v1). */

export type DocumentationSessionStatus =
  | 'created'
  | 'audio_uploaded'
  | 'transcribed'
  | 'facts_extracted'
  | 'draft_created'
  | 'confirmed'

export type MedicalDocumentStatus = 'pending' | 'confirmed'

export type FieldValueStatusStr = 'auto_filled' | 'user_edited' | 'missing' | 'doubtful' | 'confirmed'

export interface UserResponse {
  id: string
  email: string
  full_name: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface AuthResponse {
  user: UserResponse
  token: { access_token: string; token_type?: string; expires_in: number }
}

export interface SessionResponse {
  id: string
  user_id: string
  template_id: string
  status: DocumentationSessionStatus
  created_at: string
  updated_at: string
}

export interface SessionDetailsResponse extends SessionResponse {
  has_audio: boolean
  has_transcript: boolean
  has_document: boolean
}

export interface SessionListResponse {
  sessions: SessionResponse[]
  total: number
}

export interface TemplateResponse {
  id: string
  name: string
  description: string
  version: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface TemplateFieldDTO {
  id: string
  name: string
  label: string
  is_required: boolean
  default_value: string | null
  options: Record<string, unknown> | null
  order: number
  field_type?: string
}

export interface TemplateDetailsResponse extends TemplateResponse {
  fields: TemplateFieldDTO[]
}

export interface TemplateListResponse {
  templates: TemplateResponse[]
  total: number
}

export interface TranscriptResponse {
  id: string
  session_id: string
  audio_record_id: string
  text: string
  language: string
  confidence_score: number
  created_at: string
}

export interface FieldValueDTO {
  field_id: string
  field_name: string
  field_label: string
  value: string | null
  status: FieldValueStatusStr
  is_required: boolean
  confidence: number | null
  source_text: string | null
  source_start_index: number | null
  source_end_index: number | null
}

export interface MedicalDocumentDetailsResponse {
  id: string
  user_id: string
  session_id: string
  template_id: string
  template_name: string
  transcript_id: string
  transcript_text: string
  status: MedicalDocumentStatus
  created_at: string
  updated_at: string
  field_values: FieldValueDTO[]
  validation_status: Record<string, boolean>
}

export interface ValidateDocumentResponse {
  is_valid: boolean
  missing_fields: string[]
  doubtful_fields: string[]
  required_fields_count: number
  filled_fields_count: number
}
