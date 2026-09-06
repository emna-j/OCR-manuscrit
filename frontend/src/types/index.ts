export type UserRole = "ADMIN" | "ANALYST" | "REVIEWER" | "USER";

export type DocumentStatus =
  | "UPLOADED"
  | "VALIDATING"
  | "PREPROCESSING"
  | "OCR_PROCESSING"
  | "TEXT_EXTRACTED"
  | "ANALYZING"
  | "ANALYZED"
  | "COMPLETED"
  | "REQUIRES_REVIEW"
  | "REVIEWED"
  | "FAILED";

export type Sentiment = "positive" | "negative" | "neutral";
export type ReviewDecision = "VALIDATED" | "REJECTED";

export type PIIType =
  | "PERSON"
  | "EMAIL"
  | "PHONE"
  | "ADDRESS"
  | "DATE_OF_BIRTH"
  | "ID_NUMBER"
  | "ORGANIZATION"
  | "LOCATION";

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  role: UserRole;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface PiiDetection {
  id: string;
  pii_type: PIIType;
  value: string;
  start: number | null;
  end: number | null;
  confidence: number | null;
}

export interface Emotion {
  label: string;
  confidence: number;
}

export interface Analysis {
  id: string;
  document_id: string;
  extracted_text: string | null;
  ocr_confidence: number | null;
  sentiment: Sentiment | null;
  sentiment_confidence: number | null;
  emotions: Emotion[];
  category: string | null;
  keywords: string[];
  summary: string | null;
  analysis_confidence: number | null;
  created_at: string;
  pii_detections: PiiDetection[];
}

export interface HumanReview {
  id: string;
  document_id: string;
  reviewer_id: string | null;
  corrected_text: string | null;
  corrected_sentiment: Sentiment | null;
  corrected_category: string | null;
  comment: string | null;
  decision: ReviewDecision;
  created_at: string;
}

export interface DocumentItem {
  id: string;
  owner_id: string;
  original_filename: string;
  content_type: string;
  file_size_bytes: number;
  language: string | null;
  status: DocumentStatus;
  error_reason: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentDetail extends DocumentItem {
  analysis: Analysis | null;
  latest_review: HumanReview | null;
}

export interface DocumentListResponse {
  items: DocumentItem[];
  total: number;
}

export interface RecentDocument {
  id: string;
  original_filename: string;
  status: DocumentStatus;
  sentiment: Sentiment | null;
  ocr_confidence: number | null;
  analysis_confidence: number | null;
  created_at: string;
}

export interface DashboardStatistics {
  total_documents: number;
  positive_count: number;
  negative_count: number;
  neutral_count: number;
  unknown_sentiment_count: number;
  average_ocr_confidence: number | null;
  average_analysis_confidence: number | null;
  requires_review_count: number;
  recent_documents: RecentDocument[];
}

export interface ReviewRequest {
  corrected_text?: string;
  corrected_sentiment?: Sentiment;
  corrected_category?: string;
  comment?: string;
  decision: ReviewDecision;
}