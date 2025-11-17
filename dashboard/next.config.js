module.exports = {
  reactStrictMode: true,
  async rewrites() {
    return [{
      source: '/backend/:path*',
      destination: 'http://localhost:8000/:path*'
    }];
  },
};

