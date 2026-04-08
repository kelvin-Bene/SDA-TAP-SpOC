import { useEffect, useRef } from 'react';
import { Sparkles, User, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { LlmMarkdown } from './LlmMarkdown';
import { ResultsTable } from './ResultsTable';

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  /** Optional: SQL the assistant ran via the tool-use loop. Renders below the message. */
  sql?: string | null;
  /** Optional: result rows from the SQL execution. Renders as a small inline table. */
  rows?: Record<string, unknown>[] | null;
  columns?: string[] | null;
}

interface ChatTranscriptProps {
  messages: ChatMessage[];
  loading: boolean;
  className?: string;
}

/**
 * Stateless message-list component for the A3 Leaderboard Chat page.
 *
 * Renders user messages right-aligned (no markdown — they're plain text)
 * and assistant messages left-aligned via LlmMarkdown. If an assistant
 * message includes SQL + rows from the tool-use loop, those render inline
 * below the prose.
 *
 * Auto-scrolls to the bottom when new messages or the loading state
 * change. The parent component owns the messages array.
 */
export function ChatTranscript({ messages, loading, className }: ChatTranscriptProps) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  if (messages.length === 0 && !loading) {
    return (
      <div className={cn('flex flex-col items-center justify-center text-center py-16 text-muted-foreground', className)}>
        <Sparkles className="h-12 w-12 text-cosmic-cyan/40 mb-4" />
        <p className="text-lg font-medium text-foreground">Ask the catalog anything</p>
        <p className="text-sm mt-2 max-w-md">
          The local LLM has read-only access to the satellites, observations, datasets,
          submissions, and leaderboard. Ask in plain English and it will look up the answer.
        </p>
      </div>
    );
  }

  return (
    <div className={cn('flex flex-col gap-4 py-4', className)}>
      {messages.map((msg, i) => (
        <ChatBubble key={i} message={msg} />
      ))}
      {loading && (
        <div className="flex items-start gap-3">
          <div className="rounded-full bg-cosmic-cyan/10 border border-cosmic-cyan/30 p-2 shrink-0">
            <Sparkles className="h-4 w-4 text-cosmic-cyan" />
          </div>
          <div className="rounded-2xl rounded-tl-sm border border-white/10 bg-white/5 px-4 py-3 max-w-[85%]">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Thinking...
            </div>
          </div>
        </div>
      )}
      <div ref={endRef} />
    </div>
  );
}

function ChatBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user';

  if (isUser) {
    return (
      <div className="flex items-start gap-3 justify-end">
        <div className="rounded-2xl rounded-tr-sm bg-cosmic-cyan/15 border border-cosmic-cyan/30 px-4 py-3 max-w-[85%] text-foreground">
          <p className="whitespace-pre-wrap">{message.content}</p>
        </div>
        <div className="rounded-full bg-white/5 border border-white/10 p-2 shrink-0">
          <User className="h-4 w-4 text-foreground" />
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-start gap-3">
      <div className="rounded-full bg-cosmic-cyan/10 border border-cosmic-cyan/30 p-2 shrink-0">
        <Sparkles className="h-4 w-4 text-cosmic-cyan" />
      </div>
      <div className="rounded-2xl rounded-tl-sm border border-white/10 bg-white/5 px-4 py-3 max-w-[85%] space-y-3">
        <LlmMarkdown>{message.content}</LlmMarkdown>
        {message.sql && (
          <details className="rounded border border-white/10 bg-black/20 text-xs">
            <summary className="px-2 py-1 cursor-pointer text-muted-foreground hover:text-foreground">
              View generated SQL
            </summary>
            <pre className="px-3 py-2 font-mono text-cosmic-cyan overflow-x-auto whitespace-pre-wrap break-all">
              {message.sql}
            </pre>
          </details>
        )}
        {message.rows && message.rows.length > 0 && message.columns && (
          <ResultsTable
            columns={message.columns}
            rows={message.rows}
            className="text-xs"
          />
        )}
      </div>
    </div>
  );
}
