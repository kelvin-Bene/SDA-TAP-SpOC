import { test as base, expect, type ConsoleMessage, type Page } from '@playwright/test';

/**
 * ConsoleWatcher — shared fixture that captures console + pageerror events on every test
 * and fails the test if any denylisted (e.g. CSP, WebGL, chunk-load, uncaught) messages appear.
 *
 * Import `test` from this file instead of `@playwright/test` so every spec inherits the guard.
 */

const ALLOWLIST: RegExp[] = [
  /Cesium ion default access token is missing/i,
  /ResizeObserver loop/i,
  /favicon\.ico.*404/i,
  /\[vite\].*hmr/i,
  /Download the React DevTools/i,
  /React Router Future Flag Warning/i,
  /Failed to load resource: the server responded with a status of 401/i, // Ion tile without token OK
];

const DENYLIST: RegExp[] = [
  /Content Security Policy/i,
  /Refused to (load|connect|execute|evaluate|apply|frame)/i,
  /WebGL.*(error|failed|lost)/i,
  /Uncaught \(in promise\)/i,
  /Uncaught (Type|Reference|Range)Error/i,
  /ChunkLoadError|Failed to fetch dynamically imported module/i,
  /Cesium.*destroyed/i,
  /An error occurred in the <\w+> component/i,
  /Warning: Cannot update a component.*while rendering/i,
];

export type CapturedEntry = {
  kind: 'console' | 'pageerror';
  type?: string;
  text: string;
  url: string;
  ts: number;
};

export class ConsoleWatcher {
  readonly entries: CapturedEntry[] = [];
  private extraAllow: RegExp[] = [];

  constructor(private page: Page) {
    page.on('console', (msg: ConsoleMessage) => {
      if (msg.type() === 'error' || msg.type() === 'warning') {
        this.entries.push({
          kind: 'console',
          type: msg.type(),
          text: msg.text(),
          url: page.url(),
          ts: Date.now(),
        });
      }
    });
    page.on('pageerror', (err) => {
      this.entries.push({
        kind: 'pageerror',
        text: `${err.name}: ${err.message}`,
        url: page.url(),
        ts: Date.now(),
      });
    });
  }

  /** Add extra allowed patterns for a single test (e.g. 404s on bad IDs). */
  allow(...patterns: RegExp[]): void {
    this.extraAllow.push(...patterns);
  }

  /** Remove all captured entries (useful to reset after a known-noisy navigation). */
  drain(): void {
    this.entries.length = 0;
  }

  /** Returns entries that match the denylist and are not allowlisted. */
  violations(): CapturedEntry[] {
    const allow = [...ALLOWLIST, ...this.extraAllow];
    return this.entries.filter((e) => {
      // pageerror entries always fail (no allowlist bypass)
      if (e.kind === 'pageerror') return true;
      // Allowlist wins — skip benign expected errors
      if (allow.some((re) => re.test(e.text))) return false;
      // Deny-listed patterns fail
      return DENYLIST.some((re) => re.test(e.text));
    });
  }

  /** Throw if any violations are present. */
  assertClean(): void {
    const v = this.violations();
    if (v.length === 0) return;
    const msg = [
      `Console regression detected (${v.length} entries):`,
      ...v.map((e) => `  [${e.kind}${e.type ? `:${e.type}` : ''} @ ${e.url}] ${e.text}`),
    ].join('\n');
    expect.soft(v, msg).toEqual([]);
    throw new Error(msg);
  }
}

export const test = base.extend<{ consoleWatcher: ConsoleWatcher }>({
  consoleWatcher: async ({ page }, use) => {
    const watcher = new ConsoleWatcher(page);
    await use(watcher);
    watcher.assertClean();
  },
});

export { expect };
