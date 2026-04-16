import * as React from 'react';
import { cn } from '@/lib/utils';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Card } from '@/components/ui/card';

/**
 * Column descriptor for ResponsiveTable.
 * API shape mirrors @tanstack/react-table's ColumnDef so consumers can migrate
 * internals later without breaking callers.
 */
export type ResponsiveColumn<T> = {
  /** Unique column identifier (used as React key and for data-col attributes). */
  key: string;
  /** Header text rendered above the column on desktop and as the label in card body on mobile. */
  header: string;
  /** Renders the cell content for a given row. */
  cell: (row: T) => React.ReactNode;
  /**
   * If true, this column's value is rendered as the card title on mobile
   * (instead of inside the <dl> body). Only one column should be marked primary.
   */
  primary?: boolean;
  /** Drop this column entirely below `md:` (useful for low-priority meta fields). */
  hideOnMobile?: boolean;
  /** Override the card-mode label for this column. Falls back to `header`. */
  mobileLabel?: string;
  /** Extra className applied to the <td> (desktop) and the <dd> (mobile). */
  cellClassName?: string;
  /** Extra className applied to the <th> (desktop only). */
  headerClassName?: string;
};

export interface ResponsiveTableProps<T> {
  data: T[];
  columns: ResponsiveColumn<T>[];
  /** Returns a stable unique key for each row. */
  keyField: (row: T) => string | number;
  /** Make rows clickable. Whole row on desktop, whole card on mobile. */
  onRowClick?: (row: T) => void;
  /**
   * Renders an actions slot inside each row / card (typically a kebab menu).
   * On desktop: rendered in the rightmost cell. On mobile: rendered top-right of card header.
   */
  renderActions?: (row: T) => React.ReactNode;
  emptyState?: React.ReactNode;
  className?: string;
  cardClassName?: string;
}

/**
 * Responsive data table primitive.
 *
 * - `md:+` (≥ 768px): renders a standard shadcn `Table` with all columns.
 * - `<md:` (< 768px): renders a stacked list of `Card`s. The column marked
 *   `primary` becomes the card title; remaining visible columns render as a
 *   definition list inside the card body.
 *
 * Designed to back the Leaderboard, MySubmissions, MyDatasets, and
 * DatasetBrowser tables uniformly.
 */
export function ResponsiveTable<T>({
  data,
  columns,
  keyField,
  onRowClick,
  renderActions,
  emptyState,
  className,
  cardClassName,
}: ResponsiveTableProps<T>) {
  if (data.length === 0 && emptyState) {
    return <div className={cn('py-12 text-center', className)}>{emptyState}</div>;
  }

  const primaryCol = columns.find((c) => c.primary);
  const bodyCols = columns.filter((c) => !c.primary && !c.hideOnMobile);

  return (
    <>
      {/* Desktop: full table */}
      <div className={cn('hidden md:block', className)}>
        <Table>
          <TableHeader>
            <TableRow>
              {columns.map((col) => (
                <TableHead key={col.key} className={col.headerClassName}>
                  {col.header}
                </TableHead>
              ))}
              {renderActions && <TableHead className="w-[1%]" />}
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.map((row) => (
              <TableRow
                key={keyField(row)}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
                className={onRowClick ? 'cursor-pointer' : undefined}
              >
                {columns.map((col) => (
                  <TableCell key={col.key} className={col.cellClassName}>
                    {col.cell(row)}
                  </TableCell>
                ))}
                {renderActions && (
                  <TableCell
                    className="text-right"
                    onClick={(e) => e.stopPropagation()}
                  >
                    {renderActions(row)}
                  </TableCell>
                )}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {/* Mobile: stacked cards */}
      <ul className={cn('md:hidden space-y-3', className)} role="list">
        {data.map((row) => {
          const key = keyField(row);
          const clickable = Boolean(onRowClick);
          return (
            <li key={key}>
              <Card
                className={cn(
                  'p-4',
                  clickable &&
                    'cursor-pointer transition-colors hover:bg-accent/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                  cardClassName,
                )}
                {...(clickable
                  ? {
                      role: 'button',
                      tabIndex: 0,
                      onClick: () => onRowClick?.(row),
                      onKeyDown: (e: React.KeyboardEvent) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault();
                          onRowClick?.(row);
                        }
                      },
                    }
                  : {})}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0 flex-1 text-base font-medium">
                    {primaryCol ? primaryCol.cell(row) : null}
                  </div>
                  {renderActions && (
                    <div
                      className="shrink-0"
                      onClick={(e) => e.stopPropagation()}
                      onKeyDown={(e) => e.stopPropagation()}
                    >
                      {renderActions(row)}
                    </div>
                  )}
                </div>
                {bodyCols.length > 0 && (
                  <dl className="mt-3 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1.5 text-sm">
                    {bodyCols.map((col) => (
                      <React.Fragment key={col.key}>
                        <dt className="text-xs font-medium text-muted-foreground self-center">
                          {col.mobileLabel ?? col.header}
                        </dt>
                        <dd className={cn('text-right break-words', col.cellClassName)}>
                          {col.cell(row)}
                        </dd>
                      </React.Fragment>
                    ))}
                  </dl>
                )}
              </Card>
            </li>
          );
        })}
      </ul>
    </>
  );
}
