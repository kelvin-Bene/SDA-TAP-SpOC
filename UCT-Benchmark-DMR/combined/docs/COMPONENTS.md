> **Note:** This documentation has moved to `generated-docs/docs/`.
> Please see [generated-docs/docs/technical/FRONTEND.md](../../../generated-docs/docs/technical/FRONTEND.md) for the latest version.

# SpOC Component Library

## Overview

The SpOC frontend uses shadcn/ui as the base component library, built on Radix UI primitives with Tailwind CSS styling. This document catalogs all available components.

## UI Components (shadcn/ui)

### Form Components

#### Button
```tsx
import { Button } from '@/components/ui/button';

<Button variant="default">Primary</Button>
<Button variant="outline">Outline</Button>
<Button variant="ghost">Ghost</Button>
<Button variant="destructive">Destructive</Button>
<Button size="sm">Small</Button>
<Button size="lg">Large</Button>
<Button size="icon"><Icon /></Button>
```

#### Input
```tsx
import { Input } from '@/components/ui/input';

<Input type="text" placeholder="Enter text..." />
<Input type="email" />
<Input type="password" />
<Input disabled />
```

#### Textarea
```tsx
import { Textarea } from '@/components/ui/textarea';

<Textarea placeholder="Enter description..." rows={4} />
```

#### Select
```tsx
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select';

<Select value={value} onValueChange={setValue}>
  <SelectTrigger>
    <SelectValue placeholder="Select..." />
  </SelectTrigger>
  <SelectContent>
    <SelectItem value="option1">Option 1</SelectItem>
    <SelectItem value="option2">Option 2</SelectItem>
  </SelectContent>
</Select>
```

#### Radio Group
```tsx
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';

<RadioGroup value={value} onValueChange={setValue}>
  <RadioGroupItem value="option1" id="r1" />
  <Label htmlFor="r1">Option 1</Label>
</RadioGroup>
```

#### Switch
```tsx
import { Switch } from '@/components/ui/switch';

<Switch checked={enabled} onCheckedChange={setEnabled} />
```

#### Slider
```tsx
import { Slider } from '@/components/ui/slider';

<Slider
  value={[value]}
  onValueChange={([v]) => setValue(v)}
  min={0}
  max={100}
  step={1}
/>
```

### Display Components

#### Card
```tsx
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/card';

<Card>
  <CardHeader>
    <CardTitle>Title</CardTitle>
    <CardDescription>Description text</CardDescription>
  </CardHeader>
  <CardContent>
    Content goes here
  </CardContent>
  <CardFooter>
    <Button>Action</Button>
  </CardFooter>
</Card>
```

#### Badge
```tsx
import { Badge } from '@/components/ui/badge';

<Badge>Default</Badge>
<Badge variant="secondary">Secondary</Badge>
<Badge variant="success">Success</Badge>
<Badge variant="destructive">Error</Badge>

// Orbital regime badges
<Badge variant="leo">LEO</Badge>
<Badge variant="meo">MEO</Badge>
<Badge variant="geo">GEO</Badge>
<Badge variant="heo">HEO</Badge>

// Tier badges
<Badge variant="tier1">T1</Badge>
<Badge variant="tier2">T2</Badge>
<Badge variant="tier3">T3</Badge>
<Badge variant="tier4">T4</Badge>
```

#### Progress
```tsx
import { Progress } from '@/components/ui/progress';

<Progress value={75} />
```

#### Table
```tsx
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table';

<Table>
  <TableHeader>
    <TableRow>
      <TableHead>Column 1</TableHead>
      <TableHead>Column 2</TableHead>
    </TableRow>
  </TableHeader>
  <TableBody>
    <TableRow>
      <TableCell>Data 1</TableCell>
      <TableCell>Data 2</TableCell>
    </TableRow>
  </TableBody>
</Table>
```

#### Skeleton
```tsx
import { Skeleton } from '@/components/ui/skeleton';

<Skeleton className="h-4 w-full" />
<Skeleton className="h-12 w-12 rounded-full" />
```

### Overlay Components

#### Dialog
```tsx
import { Dialog, DialogTrigger, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';

<Dialog>
  <DialogTrigger asChild>
    <Button>Open Dialog</Button>
  </DialogTrigger>
  <DialogContent>
    <DialogHeader>
      <DialogTitle>Dialog Title</DialogTitle>
      <DialogDescription>Dialog description</DialogDescription>
    </DialogHeader>
    {/* Content */}
  </DialogContent>
</Dialog>
```

#### Dropdown Menu
```tsx
import { DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem } from '@/components/ui/dropdown-menu';

<DropdownMenu>
  <DropdownMenuTrigger asChild>
    <Button variant="ghost">Menu</Button>
  </DropdownMenuTrigger>
  <DropdownMenuContent>
    <DropdownMenuItem>Item 1</DropdownMenuItem>
    <DropdownMenuItem>Item 2</DropdownMenuItem>
  </DropdownMenuContent>
</DropdownMenu>
```

#### Tooltip
```tsx
import { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider } from '@/components/ui/tooltip';

<TooltipProvider>
  <Tooltip>
    <TooltipTrigger>Hover me</TooltipTrigger>
    <TooltipContent>Tooltip text</TooltipContent>
  </Tooltip>
</TooltipProvider>
```

#### Toast
```tsx
import { useToast } from '@/hooks/use-toast';

const { toast } = useToast();

toast({
  title: "Success",
  description: "Operation completed",
});

toast({
  variant: "destructive",
  title: "Error",
  description: "Something went wrong",
});
```

### Navigation Components

#### Tabs
```tsx
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';

<Tabs defaultValue="tab1">
  <TabsList>
    <TabsTrigger value="tab1">Tab 1</TabsTrigger>
    <TabsTrigger value="tab2">Tab 2</TabsTrigger>
  </TabsList>
  <TabsContent value="tab1">Content 1</TabsContent>
  <TabsContent value="tab2">Content 2</TabsContent>
</Tabs>
```

#### Scroll Area
```tsx
import { ScrollArea } from '@/components/ui/scroll-area';

<ScrollArea className="h-72">
  {/* Long content */}
</ScrollArea>
```

### Utility Components

#### Separator
```tsx
import { Separator } from '@/components/ui/separator';

<Separator />
<Separator orientation="vertical" />
```

#### Label
```tsx
import { Label } from '@/components/ui/label';

<Label htmlFor="input">Label Text</Label>
```

---

## Custom Application Components

### Dashboard Components

#### StatCard
```tsx
import { StatCard } from '@/components/dashboard/StatCard';

<StatCard
  title="Your Rank"
  value="#3"
  change={2}
  changeLabel="this week"
  icon={<Trophy className="h-5 w-5" />}
/>
```

**Props:**
| Prop | Type | Description |
|------|------|-------------|
| title | string | Card title |
| value | string \| number | Main value display |
| subtitle | string | Optional subtitle |
| change | number | Trend indicator |
| changeLabel | string | Change description |
| icon | ReactNode | Optional icon |

#### RecentSubmissions
```tsx
import { RecentSubmissions } from '@/components/dashboard/RecentSubmissions';

<RecentSubmissions />
```
Displays recent submission activity with status badges and metrics.

#### LeaderboardSnapshot
```tsx
import { LeaderboardSnapshot } from '@/components/dashboard/LeaderboardSnapshot';

<LeaderboardSnapshot />
```
Shows top 5 leaderboard entries with medal indicators.

#### QuickActions
```tsx
import { QuickActions } from '@/components/dashboard/QuickActions';

<QuickActions />
```
Primary action buttons for common tasks.

### Dataset Components

#### DatasetCard
```tsx
import { DatasetCard } from '@/components/datasets/DatasetCard';

<DatasetCard
  dataset={dataset}
  onPreview={(d) => handlePreview(d)}
  onDownload={(d) => handleDownload(d)}
/>
```

**Props:**
| Prop | Type | Description |
|------|------|-------------|
| dataset | Dataset | Dataset object |
| onPreview | (dataset) => void | Preview callback |
| onDownload | (dataset) => void | Download callback |

#### DatasetFilters
```tsx
import { DatasetFilters } from '@/components/datasets/DatasetFilters';

<DatasetFilters
  filters={filters}
  onFiltersChange={setFilters}
  onClear={clearFilters}
/>
```

**Props:**
| Prop | Type | Description |
|------|------|-------------|
| filters | DatasetFilters | Current filter state |
| onFiltersChange | (filters) => void | Filter change handler |
| onClear | () => void | Clear all filters |

#### DatasetPreviewDialog
```tsx
import { DatasetPreviewDialog } from '@/components/datasets/DatasetPreviewDialog';

<DatasetPreviewDialog
  dataset={selectedDataset}
  open={isOpen}
  onOpenChange={setIsOpen}
  onDownload={handleDownload}
/>
```

### Layout Components

#### MainLayout
```tsx
import { MainLayout } from '@/components/layout/MainLayout';

// Used as route wrapper in App.tsx
<Route path="/" element={<MainLayout />}>
  {/* Child routes */}
</Route>
```
Provides app shell with header, sidebar, and content area.

#### Header
```tsx
import { Header } from '@/components/layout/Header';

<Header onMenuClick={() => setSidebarOpen(!open)} />
```
Top navigation bar with logo, nav links, notifications, user menu.

#### Sidebar
```tsx
import { Sidebar } from '@/components/layout/Sidebar';

<Sidebar
  isOpen={sidebarOpen}
  onClose={() => setSidebarOpen(false)}
/>
```
Collapsible navigation with expandable menu items.

### Visualization Components

#### OrbitViewer
```tsx
import { OrbitViewer } from '@/components/cesium/OrbitViewer';

<OrbitViewer
  satellites={satelliteData}
  startTime={new Date()}
  endTime={new Date(Date.now() + 7200000)}
  showGroundTracks={true}
/>
```

**Props:**
| Prop | Type | Description |
|------|------|-------------|
| satellites | Satellite[] | Array of satellite data |
| startTime | Date | Animation start time |
| endTime | Date | Animation end time |
| showGroundTracks | boolean | Show orbit paths |
| className | string | Additional CSS classes |

---

## Icon Usage

Using Lucide React icons throughout:

```tsx
import {
  Trophy, Medal, Award, Star,           // Ranking icons
  Database, Satellite, Upload, Download, // Data icons
  CheckCircle, XCircle, AlertCircle,     // Status icons
  ArrowUp, ArrowDown, TrendingUp,        // Trend icons
  Play, Pause, RotateCcw, ZoomIn,        // Control icons
  Moon, Sun, Monitor,                    // Theme icons
} from 'lucide-react';
```
