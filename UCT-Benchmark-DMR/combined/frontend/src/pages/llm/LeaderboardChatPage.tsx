import { useEffect, useRef, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Sparkles, Send, RotateCcw, Cpu } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { useToast } from '@/hooks/use-toast';
import { api } from '@/api/client';
import { ChatTranscript, type ChatMessage } from '@/components/llm/ChatTranscript';

interface ChatResponse {
  text: string;
  sql?: string | null;
  rows?: Record<string, unknown>[] | null;
  columns?: string[] | null;
}

const STARTER_QUESTIONS = [
  'Which algorithms have the best F1 score?',
  'How many submissions have been made?',
  'What datasets are available for LEO?',
  'Which sensor has the most observations?',
];

/**
 * A3 — Leaderboard Chat page.
 *
 * Multi-turn conversational interface. The LLM has read-only access to the
 * catalog via the same sqlglot-validated SQL pipeline as A1. When it needs
 * data, it emits a <sql>...</sql> tool tag in its first response; the
 * backend extracts and executes, then makes a second LLM call with the
 * result included in <result>...</result> tags so the model can summarize.
 *
 * State management: the conversation lives in React state. Page refresh =
 * new chat. The server is stateless — full message history is sent in
 * every request. This is intentional for v1 (avoids a chat_sessions DB
 * table). Persistence is a v2 follow-up.
 */
export function LeaderboardChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { toast } = useToast();

  const mutation = useMutation({
    mutationFn: async (newMessages: ChatMessage[]) => {
      // Strip SQL/rows/columns from the messages we send back — the backend
      // doesn't need them, only the role+content for the conversation history.
      const wireMessages = newMessages.map((m) => ({ role: m.role, content: m.content }));
      const response = await api.chatWithLeaderboard(wireMessages);
      return response.data as ChatResponse;
    },
    onSuccess: (data) => {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: data.text,
          sql: data.sql ?? null,
          rows: data.rows ?? null,
          columns: data.columns ?? null,
        },
      ]);
    },
    onError: (err: unknown) => {
      const axiosErr = err as { response?: { status?: number }; message?: string };
      const status = axiosErr?.response?.status;
      let description = 'The local LLM call failed. Try again or rephrase your question.';
      if (status === 503) {
        description = 'Ollama service is not running. Start the GPU compose profile.';
      } else if (status === 502) {
        description = 'The LLM server returned an error. Check the Ollama container logs.';
      }
      toast({
        title: 'Chat failed',
        description,
        variant: 'destructive',
      });
    },
  });

  // Focus the textarea on mount
  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

  // Cmd/Ctrl+Enter to submit
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        if (input.trim() && !mutation.isPending) {
          handleSend();
        }
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [input, mutation.isPending]);

  const handleSend = () => {
    if (!input.trim() || mutation.isPending) return;
    const userMessage: ChatMessage = { role: 'user', content: input.trim() };
    const next = [...messages, userMessage];
    setMessages(next);
    setInput('');
    mutation.mutate(next);
  };

  const handleStarter = (q: string) => {
    setInput(q);
    textareaRef.current?.focus();
  };

  const handleNewChat = () => {
    setMessages([]);
    setInput('');
    mutation.reset();
    textareaRef.current?.focus();
  };

  return (
    <div className="container mx-auto py-8 max-w-4xl flex flex-col h-[calc(100vh-8rem)]">
      <div className="flex items-start justify-between gap-4 mb-4">
        <div>
          <h1 className="text-3xl font-display font-bold tracking-tight flex items-center gap-2">
            <Sparkles className="h-7 w-7 text-cosmic-cyan" />
            Chat Assistant
          </h1>
          <p className="text-muted-foreground mt-1">
            Ask the local LLM anything about the catalog. It can run SQL queries and explain
            the leaderboard, datasets, submissions, and observations.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="border-cosmic-cyan/40 bg-cosmic-cyan/10 text-cosmic-cyan font-mono text-xs gap-1.5">
            <Cpu className="h-3 w-3" />
            Local LLM
          </Badge>
          {messages.length > 0 && (
            <Button variant="outline" size="sm" onClick={handleNewChat} className="gap-1.5">
              <RotateCcw className="h-3 w-3" />
              New chat
            </Button>
          )}
        </div>
      </div>

      <Card className="flex-1 flex flex-col overflow-hidden">
        <CardHeader className="pb-2 shrink-0">
          <CardTitle className="text-base flex items-center gap-2">
            <Sparkles className="h-4 w-4" />
            Conversation
          </CardTitle>
          <CardDescription>
            Press <kbd className="px-1.5 py-0.5 bg-white/10 rounded border border-white/10 text-xs font-mono">
              {navigator.platform.includes('Mac') ? '⌘' : 'Ctrl'}+Enter
            </kbd> to send. Conversation lives in this browser tab — refresh = new chat.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex-1 overflow-y-auto px-6">
          <ChatTranscript messages={messages} loading={mutation.isPending} />
        </CardContent>
        <div className="border-t border-white/10 p-4 space-y-3 shrink-0">
          {messages.length === 0 && (
            <div className="flex flex-wrap gap-2">
              <span className="text-xs text-muted-foreground">Try:</span>
              {STARTER_QUESTIONS.map((q) => (
                <button
                  key={q}
                  type="button"
                  onClick={() => handleStarter(q)}
                  className="text-xs text-muted-foreground hover:text-cosmic-cyan transition-colors underline underline-offset-2"
                  disabled={mutation.isPending}
                >
                  "{q}"
                </button>
              ))}
            </div>
          )}
          <div className="flex items-end gap-2">
            <Textarea
              ref={textareaRef}
              placeholder="Ask about the catalog..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              className="min-h-[60px] max-h-[160px] resize-y"
              disabled={mutation.isPending}
            />
            <Button
              onClick={handleSend}
              disabled={mutation.isPending || !input.trim()}
              className="gap-1.5 h-[60px]"
            >
              <Send className="h-4 w-4" />
              Send
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
}
