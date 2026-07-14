/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: "standalone",
  allowedDevOrigins: ["*.trycloudflare.com", "*.loca.lt"],
  experimental: {
    middlewareClientMaxBodySize: "200mb"
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: process.env.BACKEND_URL
          ? `${process.env.BACKEND_URL}/api/:path*`
          : "http://backend:8000/api/:path*"
      }
    ];
  }
};

export default nextConfig;
