import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { cn } from '@/lib/utils';

interface LlmMarkdownProps {
  children: string;
  className?: string;
}

/**
 * Renders LLM-generated markdown text with sensible Tailwind defaults.
 *
 * Used by all four Phase 2 LLM features (SqlQueryPage, ExplainResultsButton,
 * LeaderboardChatPage, SuggestFixCard) so they share consistent styling.
 *
 * Deliberately minimal — no syntax highlighting, no math, no custom block
 * components. If we need fancier rendering later, swap the underlying
 * react-markdown call here without touching feature code.
 */
export function LlmMarkdown({ children, className }: LlmMarkdownProps) {
  return (
    <div
      className={cn(
        'prose prose-sm prose-invert max-w-none',
        'prose-headings:font-semibold prose-headings:text-foreground',
        'prose-p:text-foreground prose-p:leading-relaxed',
        'prose-strong:text-foreground prose-em:text-foreground',
        'prose-code:rounded prose-code:bg-white/10 prose-code:px-1 prose-code:py-0.5',
        'prose-code:text-cosmic-cyan prose-code:before:content-none prose-code:after:content-none',
        'prose-pre:rounded-md prose-pre:bg-black/40 prose-pre:border prose-pre:border-white/10',
        'prose-a:text-cosmic-cyan prose-a:no-underline hover:prose-a:underline',
        'prose-li:text-foreground prose-ul:text-foreground prose-ol:text-foreground',
        className,
      )}
    >
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{children}</ReactMarkdown>
    </div>
  );
}
