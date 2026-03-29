import { Badge } from '@/components/ui/badge';

interface SectionLabelProps {
  children: React.ReactNode;
}

export function SectionLabel({ children }: SectionLabelProps) {
  return (
    <Badge
      variant="outline"
      className="border-white/20 bg-white/5 text-muted-foreground font-mono text-xs tracking-widest uppercase px-4 py-1.5"
    >
      {children}
    </Badge>
  );
}
