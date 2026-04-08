import { cn } from '@/lib/utils';

interface ResultsTableProps {
  columns: string[];
  rows: Record<string, unknown>[];
  truncated?: boolean;
  className?: string;
}

/**
 * Generic table renderer for LLM-generated SQL query results.
 *
 * Used by SqlQueryPage (A1) and inline by LeaderboardChatPage (A3) when the
 * chat agent's tool-use loop returns rows.
 *
 * No sorting, no paging, no virtualization in v1 — the LLM endpoint already
 * caps result_count at 500 server-side, which is small enough to render
 * directly. Add @tanstack/react-table integration in v2 if needed.
 */
export function ResultsTable({ columns, rows, truncated, className }: ResultsTableProps) {
  if (rows.length === 0) {
    return (
      <div className={cn('rounded border border-white/10 p-4 text-sm text-muted-foreground', className)}>
        Empty result set.
      </div>
    );
  }

  return (
    <div className={cn('rounded border border-white/10 overflow-hidden', className)}>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-white/5 text-left">
            <tr>
              {columns.map((col) => (
                <th
                  key={col}
                  className="px-3 py-2 font-medium text-muted-foreground border-b border-white/10 whitespace-nowrap"
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i} className="border-b border-white/5 hover:bg-white/5 transition-colors">
                {columns.map((col) => (
                  <td key={col} className="px-3 py-2 text-foreground/90 whitespace-nowrap">
                    {formatCell(row[col])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {truncated && (
        <div className="bg-white/5 border-t border-white/10 px-3 py-2 text-xs text-muted-foreground">
          Result set was truncated to 500 rows. Refine your query for narrower results.
        </div>
      )}
    </div>
  );
}

function formatCell(value: unknown): string {
  if (value === null || value === undefined) return '—';
  if (typeof value === 'number') {
    // Pretty-print floats with 4 decimals; integers as-is
    return Number.isInteger(value) ? String(value) : value.toFixed(4);
  }
  if (typeof value === 'boolean') return value ? 'true' : 'false';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}
