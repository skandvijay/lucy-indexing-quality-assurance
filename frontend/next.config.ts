import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Enable standalone output for Docker optimization
  output: 'standalone',
  typescript: {
    ignoreBuildErrors: true,
  },
  
  async rewrites() {
    // Use the correct backend URL for local development
    const backendUrl = process.env.BACKEND_URL || 'http://127.0.0.1:8000';
    
    return [
      {
        source: '/api/:path*',
        destination: `${backendUrl}/:path*`,
      },
    ];
  },
  
  // Optimize for production
  poweredByHeader: false,
  compress: true,
  
  // Configure images for Docker
  images: {
    unoptimized: true, // Disable image optimization for smaller Docker image
  },
};

export default nextConfig;
