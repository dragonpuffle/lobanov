/**
 * OpenAPI `paths` subset for `/api/v1` — regenerate with `npm run gen:api` when backend changes.
 * @see openapi-typescript
 */
import type {
  AuthResponse,
  MedicalDocumentDetailsResponse,
  SessionDetailsResponse,
  SessionListResponse,
  SessionResponse,
  TemplateDetailsResponse,
  TemplateListResponse,
  TranscriptResponse,
  ValidateDocumentResponse,
} from '@/shared/api/types'

export type Json = Record<string, unknown>

export interface paths {
  '/api/v1/auth/register': {
    post: {
      requestBody: { content: { 'application/json': { email: string; password: string; full_name: string } } }
      responses: { 201: { content: { 'application/json': AuthResponse } } }
    }
  }
  '/api/v1/auth/login': {
    post: {
      requestBody: { content: { 'application/json': { email: string; password: string } } }
      responses: { 200: { content: { 'application/json': AuthResponse } } }
    }
  }
  '/api/v1/sessions': {
    get: {
      parameters: { query: { status?: string; limit?: number; offset?: number } }
      responses: { 200: { content: { 'application/json': SessionListResponse } } }
    }
    post: {
      requestBody: { content: { 'application/json': { template_id: string } } }
      responses: { 201: { content: { 'application/json': SessionResponse } } }
    }
  }
  '/api/v1/sessions/{session_id}': {
    get: {
      parameters: { path: { session_id: string } }
      responses: { 200: { content: { 'application/json': SessionDetailsResponse } } }
    }
  }
  '/api/v1/sessions/{session_id}/audio': {
    post: {
      parameters: { path: { session_id: string } }
      requestBody: { content: { 'multipart/form-data': { '': string } } }
      responses: { 201: { content: { 'application/json': Json } } }
    }
  }
  '/api/v1/sessions/{session_id}/transcribe': {
    post: {
      parameters: { path: { session_id: string } }
      requestBody: { content: { 'application/json': { language?: string } } }
      responses: { 202: { content: { 'application/json': { task_id: string; message: string } } } }
    }
  }
  '/api/v1/sessions/{session_id}/transcript': {
    get: {
      parameters: { path: { session_id: string } }
      responses: { 200: { content: { 'application/json': TranscriptResponse } } }
    }
  }
  '/api/v1/sessions/{session_id}/document/generate': {
    post: {
      parameters: { path: { session_id: string } }
      requestBody: { content: { 'application/json': { template_id: string } } }
      responses: { 202: { content: { 'application/json': { task_id: string; message: string } } } }
    }
  }
  '/api/v1/sessions/{session_id}/document': {
    get: {
      parameters: { path: { session_id: string } }
      responses: { 200: { content: { 'application/json': MedicalDocumentDetailsResponse } } }
    }
  }
  '/api/v1/sessions/{session_id}/document/fields/{field_id}': {
    put: {
      parameters: { path: { session_id: string; field_id: string } }
      requestBody: { content: { 'application/json': { value: string } } }
      responses: { 200: { content: { 'application/json': { field_id: string; value: string; status: string } } } }
    }
  }
  '/api/v1/sessions/{session_id}/document/validate': {
    get: {
      parameters: { path: { session_id: string } }
      responses: { 200: { content: { 'application/json': ValidateDocumentResponse } } }
    }
  }
  '/api/v1/sessions/{session_id}/document/confirm': {
    post: {
      parameters: { path: { session_id: string } }
      responses: { 200: { content: { 'application/json': { id: string; status: string; message: string } } } }
    }
  }
  '/api/v1/sessions/{session_id}/document/export': {
    post: {
      parameters: { path: { session_id: string } }
      requestBody: { content: { 'application/json': { format?: string } } }
      responses: {
        200: {
          content: {
            'application/json': Blob
            'application/pdf': Blob
          }
        }
      }
    }
  }
  '/api/v1/templates': {
    get: {
      parameters: { query: { active_only?: boolean; limit?: number; offset?: number } }
      responses: { 200: { content: { 'application/json': TemplateListResponse } } }
    }
  }
  '/api/v1/templates/{template_id}': {
    get: {
      parameters: { path: { template_id: string } }
      responses: { 200: { content: { 'application/json': TemplateDetailsResponse } } }
    }
  }
}

export type PathsWithMethod = {
  [K in keyof paths]: keyof paths[K]
}[keyof paths]
