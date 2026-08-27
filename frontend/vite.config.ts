import {defineConfig} from 'vite'; import react from '@vitejs/plugin-react';
const commit=(globalThis as any).process?.env?.CF_PAGES_COMMIT_SHA || (globalThis as any).process?.env?.GITHUB_SHA || 'local';
export default defineConfig({plugins:[react()],define:{'import.meta.env.VITE_COMMIT':JSON.stringify(commit)}});
