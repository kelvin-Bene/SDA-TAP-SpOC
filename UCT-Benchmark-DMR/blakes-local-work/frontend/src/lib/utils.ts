import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatNumber(value: number, decimals: number = 2): string {
  return value.toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

export function formatPercentage(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

export function formatDate(date: Date | string): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  return d.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

export function formatDateTime(date: Date | string): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  return d.toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function getOrbitalRegimeColor(regime: string): string {
  const colors: Record<string, string> = {
    LEO: '#3B82F6',
    MEO: '#10B981',
    GEO: '#F59E0B',
    HEO: '#EF4444',
  };
  return colors[regime.toUpperCase()] || '#6B7280';
}

export function getTierColor(tier: number | string): string {
  const colors: Record<string, string> = {
    '1': '#22C55E',
    '2': '#3B82F6',
    '3': '#F59E0B',
    '4': '#EF4444',
    T1: '#22C55E',
    T2: '#3B82F6',
    T3: '#F59E0B',
    T4: '#EF4444',
  };
  return colors[tier.toString()] || '#6B7280';
}

export function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    completed: '#22C55E',
    success: '#22C55E',
    processing: '#3B82F6',
    pending: '#3B82F6',
    queued: '#3B82F6',
    warning: '#EAB308',
    error: '#EF4444',
    failed: '#EF4444',
  };
  return colors[status.toLowerCase()] || '#6B7280';
}

export function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength - 3) + '...';
}

export function debounce<T extends (...args: Parameters<T>) => void>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: ReturnType<typeof setTimeout> | null = null;
  return (...args: Parameters<T>) => {
    if (timeout) clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
}

export function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
