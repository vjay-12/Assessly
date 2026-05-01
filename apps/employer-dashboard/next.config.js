/** @type {import('next').NextConfig} */
const nextConfig = {
  eslint: { ignoreDuringBuilds: true },
  // output: 'standalone', // enable only for Docker production builds
};

module.exports = nextConfig;
