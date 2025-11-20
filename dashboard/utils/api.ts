/**
 * Environment-aware API base URL helper
 * Automatically detects local vs production environment
 */

export function getApiBase(): string {
  // 1. Check explicit env var (highest priority)
  if (process.env.NEXT_PUBLIC_DOCPARSER_API_BASE) {
    return process.env.NEXT_PUBLIC_DOCPARSER_API_BASE;
  }
  
  // 2. Check if we're in development mode
  const isDev = process.env.NODE_ENV === 'development';
  
  if (isDev) {
    return "http://localhost:8000"; // Always use localhost in dev
  }
  
  // 3. Check hostname for local development
  if (typeof window !== 'undefined') {
    const hostname = window.location.hostname;
    // If running on localhost or 127.0.0.1, use localhost:8000
    if (hostname === 'localhost' || hostname === '127.0.0.1' || hostname.startsWith('192.168.') || hostname.startsWith('10.')) {
      return "http://localhost:8000";
    }
    // Otherwise, use same origin (for production deployments)
    return window.location.origin;
  }
  
  // 4. SSR fallback
  return "http://localhost:8000";
}

