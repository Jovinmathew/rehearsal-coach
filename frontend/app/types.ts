export type FeedbackCategory = "clarity" | "structure" | "pacing" | "coverage";

export interface FeedbackItem {
  category: FeedbackCategory;
  quote: string;
  issue: string;
  suggestion: string;
}

export interface ReviewStats {
  word_count: number;
  duration_sec: number;
  wpm: number;
  filler_count: number;
  filler_examples: string[];
}

export interface ReviewResponse {
  transcript: string;
  stats: ReviewStats;
  feedback: FeedbackItem[];
}

export interface ReviewError {
  error: string;
}
