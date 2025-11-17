module.exports = {
  reactStrictMode: true,
  output: 'export', // Static export for serving from FastAPI
  trailingSlash: true,
  images: {
    unoptimized: true, // Required for static export
  },
};

