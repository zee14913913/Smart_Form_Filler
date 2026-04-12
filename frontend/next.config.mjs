/** @type {import('next').NextConfig} */
const nextConfig = {
  // AG Grid uses ESM/CJS dual package — transpile to avoid
  // "Module not found: Can't resolve 'ag-grid-react'" in Next.js 14.
  transpilePackages: ['ag-grid-react', 'ag-grid-community'],
};

export default nextConfig;
