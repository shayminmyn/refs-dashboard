/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  async rewrites() {
    // BACKEND_URL là server-side only (không NEXT_PUBLIC_) — chỉ Next.js server
    // dùng để forward request đến backend Docker nội bộ.
    // Browser luôn gọi relative /api/* → Next.js proxy.
    const backendUrl = process.env.BACKEND_URL ?? 'http://localhost:4000';
    return [
      {
        source: '/api/:path*',
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
