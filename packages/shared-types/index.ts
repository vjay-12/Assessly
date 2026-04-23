export interface User {
  id: string;
  email: string;
  name: string;
  role: 'candidate' | 'employer';
  status: string;
  created_at: string;
}

export interface Application {
  id: string;
  candidate_id: string;
  status: 'applied' | 'attempted' | 'submitted' | 'evaluated';
  started_at: string | null;
  submitted_at: string | null;
  created_at: string;
}

export interface MCQQuestion {
  id: string;
  question_text: string;
  options: string[];
  difficulty: number;
}

export interface Response {
  id: string;
  application_id: string;
  question_id: string;
  selected_option: number;
  is_correct: boolean;
}

export interface Score {
  id: string;
  application_id: string;
  total_questions: number;
  correct_count: number;
  percentage: number;
  evaluated_at: string;
  worker_id: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface CrossAppTokenRequest {
  application_id: string;
}

export interface CrossAppTokenResponse {
  token: string;
  expires_at: string;
  expires_in: number;
}

export interface SubmissionRequest {
  application_id: string;
  answers: { question_id: string; selected_option: number }[];
}

export interface FunnelData {
  applied: number;
  attempted: number;
  submitted: number;
  evaluated: number;
}

export interface SSEEvent {
  type: 'EVALUATION_COMPLETED' | 'CANDIDATE_UPDATED';
  payload: Record<string, unknown>;
}
