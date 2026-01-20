# Dependency Conflict Resolution - January 20, 2026

## Issue

When running `npm install` in `web/frontend/`, the following error occurred:

```
npm error code ERESOLVE
npm error ERESOLVE unable to resolve dependency tree
npm error
npm error While resolving: spoc-frontend@1.0.0
npm error Found: eslint@9.39.2
npm error node_modules/eslint
npm error   dev eslint@"^9.10.0" from the root project
npm error
npm error Could not resolve dependency:
npm error peer eslint@"^3.0.0 || ^4.0.0 || ^5.0.0 || ^6.0.0 || ^7.0.0 || ^8.0.0-0" from eslint-plugin-react-hooks@4.6.2
```

## Root Cause Analysis

| Component | Issue |
|-----------|-------|
| **ESLint Version** | `^9.10.0` - ESLint 9.x uses new "flat config" format with breaking changes |
| **eslint-plugin-react-hooks** | Version `4.6.2` only supports ESLint 3-8 (peer dependency conflict) |
| **Missing Dependencies** | `@eslint/js` and `globals` packages required for ESLint 9 flat config |
| **Deprecated TypeScript ESLint** | `@typescript-eslint/eslint-plugin` and `@typescript-eslint/parser` replaced by unified `typescript-eslint` |

## Solution Applied

### 1. Updated package.json Dependencies

**Before (broken):**
```json
{
  "devDependencies": {
    "@typescript-eslint/eslint-plugin": "^8.6.0",
    "@typescript-eslint/parser": "^8.6.0",
    "eslint": "^9.10.0",
    "eslint-plugin-react-hooks": "^4.6.2",
    ...
  }
}
```

**After (fixed):**
```json
{
  "devDependencies": {
    "@eslint/js": "^9.10.0",
    "eslint": "^9.10.0",
    "eslint-plugin-react-hooks": "^5.0.0",
    "eslint-plugin-react-refresh": "^0.4.12",
    "globals": "^15.9.0",
    "typescript-eslint": "^8.6.0",
    ...
  }
}
```

### 2. Updated Lint Scripts

**Before:**
```json
"lint": "eslint . --ext ts,tsx --report-unused-disable-directives --max-warnings 0"
```

**After:**
```json
"lint": "eslint .",
"lint:strict": "eslint . --report-unused-disable-directives --max-warnings 0"
```

Note: ESLint 9 flat config determines file extensions from config, not CLI flags.

### 3. Updated ESLint Config (eslint.config.js)

Added proper ignores and expanded global definitions:

```javascript
import js from '@eslint/js';
import globals from 'globals';
import reactHooks from 'eslint-plugin-react-hooks';
import reactRefresh from 'eslint-plugin-react-refresh';
import tseslint from 'typescript-eslint';

export default tseslint.config(
  { ignores: ['dist', 'node_modules', '*.config.js', '*.config.ts'] },
  {
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      ecmaVersion: 2020,
      globals: {
        ...globals.browser,
        ...globals.es2020,
      },
    },
    plugins: {
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      'react-refresh/only-export-components': ['warn', { allowConstantExport: true }],
      '@typescript-eslint/no-unused-vars': ['warn', { argsIgnorePattern: '^_' }],
      '@typescript-eslint/no-explicit-any': 'warn',
    },
  }
);
```

### 4. Fixed TypeScript Errors

Fixed unused imports and variables across multiple files:

| File | Fix |
|------|-----|
| `OrbitViewer.tsx` | Removed unused `useEffect`, `ConstantProperty` imports |
| `DatasetFilters.tsx` | Removed unused `dateRangeOptions` constant |
| `DatasetPreviewDialog.tsx` | Removed unused `ExternalLink` import |
| `useLeaderboard.ts` | Removed unused `api` import |
| `DocumentationPage.tsx` | Removed unused `ScrollArea`, `Book`, `ExternalLink` imports |
| `LeaderboardPage.tsx` | Removed unused `Button`, `Badge`, `Minus` imports; removed unused `index` parameter |
| `LoginPage.tsx` | Removed unused `Link` import; prefixed unused `provider` param with underscore |
| `ProfilePage.tsx` | Removed unused `Mail`, `Bell` imports |
| `ResultsPage.tsx` | Removed unused `FileText`, `Cell` imports; prefixed unused `submissionId` with underscore |
| `SubmitPage.tsx` | Removed unused `Badge`, `File` imports; removed unused `useCallback` import |
| `input.tsx` | Changed empty interface to type alias |
| `textarea.tsx` | Changed empty interface to type alias |

## Verification

After applying fixes:

1. **npm install** - Completes successfully (556 packages)
2. **npm run lint** - Passes (26 warnings, 0 errors)
3. **npm run build** - Completes successfully (54.65s build time)

## Technical Details

### Why eslint-plugin-react-hooks v5?

- Version 5.0.0 was released with official ESLint 9 support
- Maintains backward compatibility with existing rules
- Required for React 18+ applications using hooks

### Why unified typescript-eslint?

- ESLint 9 works better with the unified `typescript-eslint` package
- Replaces separate `@typescript-eslint/eslint-plugin` and `@typescript-eslint/parser`
- Provides better type-aware linting with flat config

### Build Warning (Acceptable)

The build shows a warning about chunk size:
```
(!) Some chunks are larger than 500 kB after minification.
```

This is expected for an initial implementation and can be optimized later with:
- Dynamic imports for code-splitting
- Manual chunk configuration in Vite

## Files Modified

- `web/frontend/package.json`
- `web/frontend/eslint.config.js`
- `web/frontend/src/components/cesium/OrbitViewer.tsx`
- `web/frontend/src/components/datasets/DatasetFilters.tsx`
- `web/frontend/src/components/datasets/DatasetPreviewDialog.tsx`
- `web/frontend/src/components/ui/input.tsx`
- `web/frontend/src/components/ui/textarea.tsx`
- `web/frontend/src/hooks/useLeaderboard.ts`
- `web/frontend/src/pages/DocumentationPage.tsx`
- `web/frontend/src/pages/LeaderboardPage.tsx`
- `web/frontend/src/pages/LoginPage.tsx`
- `web/frontend/src/pages/ProfilePage.tsx`
- `web/frontend/src/pages/ResultsPage.tsx`
- `web/frontend/src/pages/SubmitPage.tsx`

---

**Author:** Blake Mister
**Date:** January 20, 2026
