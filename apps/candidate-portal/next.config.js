/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    let apiUrl = process.env.NEXT_PUBLIC_API_GATEWAY_URL || '';
    apiUrl = apiUrl.trim().replace(/^["']|["']$/g, '');
    if (!apiUrl || !apiUrl.startsWith('http')) return [];
    return [
      {
        source: '/api/:path*',
        destination: `${apiUrl}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
