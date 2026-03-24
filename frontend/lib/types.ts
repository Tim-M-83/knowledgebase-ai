export type Role = 'admin' | 'editor' | 'viewer';

export type User = {
  id: number;
  email: string;
  role: Role;
  department_id?: number | null;
  email_helper_enabled: boolean;
  license_enabled: boolean;
  license_active: boolean;
  license_status?: string | null;
  license_grace_until?: string | null;
  must_change_credentials: boolean;
};

export type LicenseStatus = {
  license_enabled: boolean;
  license_active: boolean;
  license_status?: string | null;
  workspace_id?: string | null;
  instance_id_configured: boolean;
  license_key_configured: boolean;
  current_period_end?: string | null;
  last_validated_at?: string | null;
  grace_until?: string | null;
  last_error?: string | null;
  license_server_base_url: string;
  remote_active_activation_count?: number | null;
  remote_total_activation_count?: number | null;
  activation_limit?: number | null;
};

export type PersonalNote = {
  id: number;
  user_id: number;
  title: string;
  content: string;
  priority: PersonalNotePriority;
  created_at: string;
  updated_at: string;
};

export type PersonalNotePriority = 'none' | 'low' | 'medium' | 'high';

export type PersonalNotePayload = {
  title: string;
  content: string;
  priority?: PersonalNotePriority;
};

export type SummarizerDocumentStatus = 'uploaded' | 'processing' | 'ready' | 'failed';

export type SummarizerDocument = {
  id: number;
  owner_id: number;
  original_name: string;
  mime_type: string;
  size: number;
  status: SummarizerDocumentStatus;
  error_text?: string | null;
  summary_text?: string | null;
  summary_updated_at?: string | null;
  created_at: string;
};

export type SummarizerMessage = {
  id: number;
  document_id: number;
  role: 'user' | 'assistant' | 'system';
  content: string;
  created_at: string;
};

export type FolderItem = {
  id: number;
  name: string;
  created_at?: string;
};

export type DocumentItem = {
  id: number;
  owner_id: number;
  filename: string;
  original_name: string;
  mime_type: string;
  size: number;
  department_id?: number | null;
  folder_id?: number | null;
  visibility: 'company' | 'department' | 'private';
  status: 'uploaded' | 'processing' | 'ready' | 'failed';
  error_text?: string | null;
  created_at: string;
};

export type DocumentDetail = DocumentItem & {
  chunk_count: number;
  tag_ids: number[];
};

export type ChatSession = {
  id: number;
  user_id: number;
  title: string;
  created_at: string;
};

export type ChatMessage = {
  id: number;
  session_id: number;
  role: 'user' | 'assistant' | 'system';
  content: string;
  created_at: string;
  sources?: SourceRef[];
};

export type SourceRef = {
  id: number;
  document_id: number;
  original_name: string;
  chunk_id: number;
  score: number;
  page_number?: number;
  csv_row_start?: number;
  csv_row_end?: number;
  snippet: string;
};

export type ChatDoneEvent = {
  answer: string;
  session_id: number;
  message_id: number;
  low_confidence: boolean;
  warning?: string | null;
};

export type KPIResponse = {
  docs: number;
  chunks: number;
  users: number;
  chats: number;
  last_ingestion?: string | null;
  failed_ingestions: number;
};

export type LabelValue = { label: string; value: number };
export type TimePoint = { date: string; value: number };

export type ChartsResponse = {
  daily_chats: TimePoint[];
  top_tags: LabelValue[];
  top_departments: LabelValue[];
  unanswered_daily: TimePoint[];
};

export type GapItem = {
  id: number;
  question: string;
  avg_score: number;
  had_sources: boolean;
  created_at: string;
};

export type ProviderRuntime = 'openai' | 'ollama';

export type ProviderSettings = {
  llm_provider: ProviderRuntime;
  embeddings_provider: ProviderRuntime;
  available_providers: ProviderRuntime[];
  openai_chat_model: string;
  openai_embeddings_model: string;
  openai_api_key_configured: boolean;
  openai_api_key_masked?: string | null;
  ollama_base_url: string;
  ollama_chat_model: string;
  ollama_embeddings_model: string;
  warning?: string | null;
};

export type ProviderSettingsUpdate = {
  llm_provider: ProviderRuntime;
  embeddings_provider: ProviderRuntime;
  openai_api_key?: string;
  openai_chat_model?: string;
  ollama_base_url?: string;
  ollama_chat_model?: string;
  ollama_embeddings_model?: string;
};

export type OpenAITestResult = {
  ok: boolean;
  chat_endpoint_ok: boolean;
  embeddings_endpoint_ok: boolean;
  detail: string;
  selected_chat_model?: string | null;
};

export type OllamaTestResult = {
  ok: boolean;
  chat_endpoint_ok: boolean;
  embeddings_endpoint_ok: boolean;
  detail: string;
  embedding_dimension?: number | null;
};

export type Health = {
  provider: {
    llm: string;
    embeddings: string;
    openai_chat_model: string;
    openai_embeddings_model: string;
    openai_api_key_configured: boolean;
    ollama_base_url?: string;
    ollama_chat_model?: string;
    ollama_embeddings_model?: string;
    ollama_reachable?: boolean | null;
  };
  db: boolean;
  redis: boolean;
};

export type ClearSessionsResponse = {
  deleted_sessions: number;
};

export type ClearGapsResponse = {
  deleted_gaps: number;
};
