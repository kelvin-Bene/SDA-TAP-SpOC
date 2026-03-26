import React, { createContext, useContext, useCallback } from 'react';
import { FeedbackWidget } from './FeedbackWidget';
import { useActionLogger } from '@/hooks/useActionLogger';
import { apiClient } from '@/api/client';
import type { FeedbackPayload, FeedbackResponse } from '@/types/feedback';

interface FeedbackContextValue {
  submitFeedback: (payload: FeedbackPayload) => Promise<FeedbackResponse>;
}

const FeedbackContext = createContext<FeedbackContextValue | null>(null);

export function useFeedback() {
  const ctx = useContext(FeedbackContext);
  if (!ctx) throw new Error('useFeedback must be used within FeedbackProvider');
  return ctx;
}

export function FeedbackProvider({ children }: { children: React.ReactNode }) {
  const { actions, consoleErrors } = useActionLogger();

  const submitFeedback = useCallback(
    async (payload: FeedbackPayload): Promise<FeedbackResponse> => {
      const response = await apiClient.post('/feedback', {
        ...payload,
        page_url: window.location.href,
        user_agent: navigator.userAgent,
        viewport: `${window.innerWidth}x${window.innerHeight}`,
        recent_actions: actions,
        console_errors: consoleErrors,
      });
      return response.data;
    },
    [actions, consoleErrors]
  );

  return (
    <FeedbackContext.Provider value={{ submitFeedback }}>
      {children}
      <FeedbackWidget />
    </FeedbackContext.Provider>
  );
}
