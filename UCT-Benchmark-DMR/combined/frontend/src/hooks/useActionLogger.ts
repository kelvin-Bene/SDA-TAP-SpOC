import { useEffect, useRef, useCallback, useState } from 'react';
import type { UserAction } from '@/types/feedback';

const MAX_ACTIONS = 20;
const MAX_CONSOLE_ERRORS = 5;

export function useActionLogger() {
  const actionsRef = useRef<UserAction[]>([]);
  const consoleErrorsRef = useRef<string[]>([]);
  const [, setTick] = useState(0);

  const addAction = useCallback((type: UserAction['type'], detail: string) => {
    const action: UserAction = {
      timestamp: new Date().toISOString(),
      type,
      detail,
    };
    actionsRef.current = [...actionsRef.current.slice(-(MAX_ACTIONS - 1)), action];
    setTick((t) => t + 1);
  }, []);

  const addConsoleError = useCallback((message: string) => {
    consoleErrorsRef.current = [
      ...consoleErrorsRef.current.slice(-(MAX_CONSOLE_ERRORS - 1)),
      `[${new Date().toISOString()}] ${message}`,
    ];
    setTick((t) => t + 1);
  }, []);

  // Click event listener
  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      const tag = target.tagName.toLowerCase();
      const text = target.textContent?.slice(0, 50) || '';
      const id = target.id ? `#${target.id}` : '';
      const className = target.className && typeof target.className === 'string'
        ? `.${target.className.split(' ')[0]}`
        : '';
      addAction('click', `${tag}${id}${className} "${text}"`);
    };

    document.addEventListener('click', handleClick, { capture: true });
    return () => document.removeEventListener('click', handleClick, { capture: true });
  }, [addAction]);

  // Window error and unhandled rejection listeners
  useEffect(() => {
    const handleError = (event: ErrorEvent) => {
      const msg = `${event.message} at ${event.filename}:${event.lineno}:${event.colno}`;
      addConsoleError(msg);
      addAction('error', msg);
    };

    const handleRejection = (event: PromiseRejectionEvent) => {
      const msg = `Unhandled rejection: ${
        event.reason instanceof Error ? event.reason.message : String(event.reason)
      }`;
      addConsoleError(msg);
      addAction('error', msg);
    };

    window.addEventListener('error', handleError);
    window.addEventListener('unhandledrejection', handleRejection);

    return () => {
      window.removeEventListener('error', handleError);
      window.removeEventListener('unhandledrejection', handleRejection);
    };
  }, [addAction, addConsoleError]);

  // SPA navigation tracking via history.pushState/replaceState interception
  useEffect(() => {
    const originalPushState = history.pushState.bind(history);
    const originalReplaceState = history.replaceState.bind(history);

    history.pushState = function (...args: Parameters<typeof history.pushState>) {
      originalPushState(...args);
      addAction('navigate', `pushState -> ${args[2] ?? window.location.href}`);
    };

    history.replaceState = function (...args: Parameters<typeof history.replaceState>) {
      originalReplaceState(...args);
      addAction('navigate', `replaceState -> ${args[2] ?? window.location.href}`);
    };

    const handlePopState = () => {
      addAction('navigate', `popstate -> ${window.location.href}`);
    };

    window.addEventListener('popstate', handlePopState);

    return () => {
      history.pushState = originalPushState;
      history.replaceState = originalReplaceState;
      window.removeEventListener('popstate', handlePopState);
    };
  }, [addAction]);

  return {
    get actions() {
      return actionsRef.current;
    },
    get consoleErrors() {
      return consoleErrorsRef.current;
    },
    addAction,
  };
}
