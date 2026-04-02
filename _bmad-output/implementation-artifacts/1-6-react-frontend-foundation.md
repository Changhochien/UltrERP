# Story 1.6: React Frontend Foundation

Status: completed

## Story

As a developer,
I want a working React frontend with Vite dev server,
So that I can see the UI and verify the frontend infrastructure.

## Context

Based on architecture:
- **Frontend:** React 19 (NOT "latest" - specific version due to Tauri webview dropdown bug)
- **Build:** Vite 6+
- **TypeScript:** Strict mode
- **Desktop:** Tauri 2.x

## Acceptance Criteria

**Given** the frontend is set up
**When** I run `pnpm dev`
**Then** Vite starts on port 5173
**And** loading localhost:5173 shows the app
**And** the app can make API calls to localhost:8000 through the proxy

## Technical Requirements

### package.json (repo root)

```json
{
  "name": "@ultr-erp/frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "lint": "eslint .",
    "test": "vitest run"
  },
  "dependencies": {
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "@tauri-apps/api": "^2.0.0"
  },
  "devDependencies": {
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "@vitejs/plugin-react": "^4.6.0",
    "typescript": "^5.0.0",
    "vite": "^6.0.0",
    "vitest": "^2.0.0",
    "eslint": "^9.0.0",
    "@eslint/js": "^9.0.0",
    "typescript-eslint": "^8.0.0",
    "eslint-config-prettier": "^9.0.0"
  }
}
```

### vite.config.ts

```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  clearScreen: false,
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  envPrefix: ["VITE_", "TAURI_"],
  build: {
    target:
      process.env.TAURI_PLATFORM === "windows" ? "chrome105" : "safari13",
    minify: !process.env.TAURI_DEBUG ? "esbuild" : false,
    sourcemap: !!process.env.TAURI_DEBUG,
  },
});
```

### tsconfig.json

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src"]
}
```

### tsconfig.node.json

```json
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true
  },
  "include": ["vite.config.ts"]
}
```

### eslint.config.js

```javascript
import tseslint from 'typescript-eslint';
import eslintConfigPrettier from 'eslint-config-prettier';

export default tseslint.config(
  { ignores: ['**/dist/', '**/node_modules/', '**/src-tauri/'] },
  ...tseslint.configs.recommended,
  {
    files: ['**/*.ts', '**/*.tsx'],
    languageOptions: {
      parserOptions: {
        project: './tsconfig.json',
      },
    },
    rules: {
      '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
    },
  },
  eslintConfigPrettier
);
```

### index.html

```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>UltrERP</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

### src/main.tsx

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

### src/App.tsx

```tsx
function App() {
  return (
    <div>
      <h1>UltrERP</h1>
      <p>AI-native ERP for Taiwan SMBs</p>
    </div>
  );
}

export default App;
```

### src/index.css

```css
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
    "Helvetica Neue", Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
```

### src/vite-env.d.ts

```typescript
/// <reference types="vite/client" />
```

## Tasks

- [x] Task 1: Create frontend package configuration
  - [x] Subtask: Create root package.json with React 19 and dependencies
  - [x] Subtask: Create vite.config.ts with proxy configuration
  - [x] Subtask: Create tsconfig.json with strict mode
  - [x] Subtask: Create tsconfig.node.json for Vite config type-checking
  - [x] Subtask: Create eslint.config.js with flat config
- [x] Task 2: Create HTML entry point
  - [x] Subtask: Create index.html
- [x] Task 3: Create React app structure
  - [x] Subtask: Create src/main.tsx
  - [x] Subtask: Create src/App.tsx
  - [x] Subtask: Create src/index.css
  - [x] Subtask: Create src/vite-env.d.ts
- [x] Task 4: Test development server
  - [x] Subtask: Run `pnpm dev`
  - [x] Subtask: Verify localhost:5173 loads
  - [x] Subtask: Test API proxy to localhost:8000

## Dev Notes

### Critical Implementation Details

1. **React 19** - NOT "latest". Per architecture: "React 19" required due to Tauri webview dropdown bug
2. **vite.config.ts proxy** - `/api` routes proxy to FastAPI backend
3. **Strict TypeScript** - noUnusedLocals, noUnusedParameters enabled
4. **moduleResolution: bundler** - For Vite compatibility
5. **noEmit: true** - TypeScript only for type checking, Vite handles transpilation

### Architecture References

- Section 3.1: React 19 requirement
- Section 3.1: Vite + React stack
- Best practices: Vite proxy configuration

### Source References

- Architecture: Section 3.1 - Technology Stack Table
- PRD: Technology decisions

## File List

- package.json
- vite.config.ts
- tsconfig.json
- tsconfig.node.json
- eslint.config.js
- index.html
- src/main.tsx
- src/App.tsx
- src/index.css
- src/vite-env.d.ts
- src/tests/test_health.test.tsx

## Validation Evidence

- Frontend validation passes with `pnpm test`, `pnpm lint`, and `pnpm build`.
- The dev server and `/api` proxy path were validated locally during Epic 1 execution.

## Review Outcome

- The proxy target now remains configurable via `VITE_API_PROXY_TARGET` while defaulting to `http://localhost:8000`.
- Frontend testing was upgraded from server-render-only assertions to a real `jsdom` client render smoke test.
