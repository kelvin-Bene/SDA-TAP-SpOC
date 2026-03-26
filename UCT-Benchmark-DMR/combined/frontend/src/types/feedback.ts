export type FeedbackSeverity = 'bug' | 'suggestion' | 'question';

export interface UserAction {
  timestamp: string;
  type: 'click' | 'navigate' | 'error' | 'submit';
  detail: string;
}

export interface FeedbackPayload {
  description: string;
  severity: FeedbackSeverity;
  screenshot_base64?: string;
  page_url?: string;
  user_agent?: string;
  viewport?: string;
  recent_actions?: UserAction[];
  console_errors?: string[];
  sentry_event_id?: string;
}

export interface FeedbackResponse {
  success: boolean;
  feedback_id?: string;
  message: string;
}
