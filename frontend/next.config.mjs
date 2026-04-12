import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

/** @type {import('next').NextConfig} */
const nextConfig = {
  // AG Grid uses ESM/CJS dual package — transpile to avoid
  // "Module not found: Can't resolve 'ag-grid-react'" in Next.js 14/15.
  transpilePackages: ['ag-grid-react', 'ag-grid-community'],
  // Next.js 15: outputFileTracingRoot moved from experimental to top-level.
  // Suppresses spurious workspace-root warning from multiple lockfiles.
  outputFileTracingRoot: path.join(__dirname, '../../'),
};

export default nextConfig;
