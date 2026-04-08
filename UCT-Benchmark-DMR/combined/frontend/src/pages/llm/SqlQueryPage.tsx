import { useEffect, useRef, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Sparkles, Loader2, AlertCircle, Database, Cpu } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { useToast } from '@/hooks/use-toast';
import { api } from '@/api/client';
import { ResultsTable } from '@/components/llm/ResultsTable';
import { LlmMarkdown } from '@/components/llm/LlmMarkdown';

interface SqlQueryResponse {
  sql: string;
  columns: string[];
  rows: Record<string, unknown>[];
  row_count: number;
  truncated: boolean;
}

const EXAMPLE_QUESTIONS = [
  'How many satellites are in each orbital regime?',
  'Show me the top 10 sensors by observation count',
  'What is the average F1 score across all submissions?',
  'List the 5 most recent observations',
];

export function SqlQueryPage() {
  const [question, setQuestion] = useState('');
  const [result, setResult] = useState<SqlQueryResponse | null>(null);
  const [errorDetail, setErrorDetail] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { toast } = useToast();

  const mutation = useMutation({
    mutationFn: async (q: string) => {
      const response = await api.queryDatabase(q);
      return response.data as SqlQueryResponse;
    },
    onSuccess: (data) => {
      setResult(data);
      setErrorDetail(null);
    },
    onError: (err: unknown) => {
      setResult(null);
      const axiosErr = err as {
        response?: { status?: number; data?: { detail?: { error?: string; reason?: string; raw_sql?: string } | string } };
      };
      const status = axiosErr?.response?.status;
      const detail = axiosErr?.response?.data?.detail;

      if (status === 503) {
        setErrorDetail(
          'AI features unavailable — the Ollama service is not running. ' +
            'On a DGX Spark, ensure the GPU compose profile is up: `docker compose --profile gpu up -d`.',
        );
        return;
      }

      if (status === 400 && detail && typeof detail === 'object') {
        // sqlglot safety rejection
        const reason = detail.reason || detail.error || 'Query rejected';
        const rawSql = detail.raw_sql ? `\n\nGenerated SQL:\n\`\`\`sql\n${detail.raw_sql}\n\`\`\`` : '';
        setErrorDetail(`The safety validator rejected the LLM's query.\n\n**Reason:** ${reason}${rawSql}`);
        return;
      }

      if (status === 504) {
        setErrorDetail('The query exceeded the 5-second execution limit. Try a more specific question.');
        return;
      }

      const reason = typeof detail === 'string' ? detail : detail?.reason || 'Unknown error';
      setErrorDetail(`The LLM call failed: ${reason}`);
      toast({
        title: 'Query failed',
        description: typeof reason === 'string' ? reason : 'See the error panel for details.',
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
        if (question.trim() && !mutation.isPending) {
          mutation.mutate(question);
        }
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [question, mutation]);

  const handleSubmit = () => {
    if (!question.trim() || mutation.isPending) return;
    mutation.mutate(question);
  };

  const handleExample = (example: string) => {
    setQuestion(example);
    textareaRef.current?.focus();
  };

  return (
    <div className="container mx-auto py-8 max-w-5xl space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-display font-bold tracking-tight flex items-center gap-2">
            <Sparkles className="h-7 w-7 text-cosmic-cyan" />
            Query Database
          </h1>
          <p className="text-muted-foreground mt-1">
            Ask a question in plain English. The local LLM will translate it to SQL, validate it,
            and run it against the read-only catalog.
          </p>
        </div>
        <Badge variant="outline" className="border-cosmic-cyan/40 bg-cosmic-cyan/10 text-cosmic-cyan font-mono text-xs gap-1.5">
          <Cpu className="h-3 w-3" />
          Local LLM
        </Badge>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Database className="h-5 w-5" />
            Your question
          </CardTitle>
          <CardDescription>
            Press <kbd className="px-1.5 py-0.5 bg-white/10 rounded border border-white/10 text-xs font-mono">
              {navigator.platform.includes('Mac') ? '⌘' : 'Ctrl'}+Enter
            </kbd> to submit.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Textarea
            ref={textareaRef}
            placeholder="e.g. How many UCTs are near GEO with high declination drift?"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            className="min-h-[100px] font-mono text-sm resize-y"
            disabled={mutation.isPending}
          />

          <div className="flex flex-wrap items-center gap-2">
            <Button
              onClick={handleSubmit}
              disabled={mutation.isPending || !question.trim()}
              className="gap-2"
            >
              {mutation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Generating SQL...
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4" />
                  Ask
                </>
              )}
            </Button>

            <span className="text-xs text-muted-foreground ml-2">Try:</span>
            {EXAMPLE_QUESTIONS.map((ex) => (
              <button
                key={ex}
                type="button"
                onClick={() => handleExample(ex)}
                className="text-xs text-muted-foreground hover:text-cosmic-cyan transition-colors underline underline-offset-2"
                disabled={mutation.isPending}
              >
                "{ex}"
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Error panel */}
      {errorDetail && !mutation.isPending && (
        <Card className="border-destructive/40 bg-destructive/5">
          <CardHeader className="pb-3">
            <CardTitle className="text-base text-destructive flex items-center gap-2">
              <AlertCircle className="h-4 w-4" />
              Query failed
            </CardTitle>
          </CardHeader>
          <CardContent>
            <LlmMarkdown>{errorDetail}</LlmMarkdown>
          </CardContent>
        </Card>
      )}

      {/* Results */}
      {result && !mutation.isPending && (
        <>
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <Database className="h-4 w-4" />
                Generated SQL
              </CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="rounded-md bg-black/40 border border-white/10 p-3 text-xs font-mono text-cosmic-cyan overflow-x-auto whitespace-pre-wrap break-all">
                {result.sql}
              </pre>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">
                Results
                <span className="ml-2 text-sm font-normal text-muted-foreground">
                  ({result.row_count} {result.row_count === 1 ? 'row' : 'rows'}
                  {result.truncated && ', truncated'})
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ResultsTable
                columns={result.columns}
                rows={result.rows}
                truncated={result.truncated}
              />
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
