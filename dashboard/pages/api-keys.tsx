import { useState, useEffect } from "react";
import Link from "next/link";

type ApiKey = {
  id: string;
  name: string | null;
  tenant_id: string;
  active: boolean;
  rate_limit_per_minute: number;
  rate_limit_per_hour: number;
  last_used_at: string | null;
  created_at: string;
};

function getApiBase(): string {
  if (typeof window !== "undefined") {
    return window.location.origin;
  }
  return process.env.NEXT_PUBLIC_DOCPARSER_API_BASE || "http://localhost:8000";
}

function getApiKey(): string {
  if (typeof window !== "undefined") {
    const stored = localStorage.getItem("docparser_api_key");
    if (stored) return stored;
  }
  return process.env.NEXT_PUBLIC_DOCPARSER_API_KEY || "dev_123";
}

function getAdminToken(): string | null {
  if (typeof window !== "undefined") {
    return localStorage.getItem("docparser_admin_token");
  }
  return null;
}

export default function ApiKeysPage() {
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newKeyName, setNewKeyName] = useState("");
  const [creating, setCreating] = useState(false);
  const [newKey, setNewKey] = useState<string | null>(null);
  const [showAdminMode, setShowAdminMode] = useState(false);
  const [adminToken, setAdminToken] = useState<string>("");
  const [isAdmin, setIsAdmin] = useState(false);

  useEffect(() => {
    const stored = getAdminToken();
    if (stored) {
      setAdminToken(stored);
      setIsAdmin(true);
    }
    fetchKeys();
  }, []);

  async function fetchKeys() {
    setLoading(true);
    setError(null);
    try {
      const apiBase = getApiBase();
      const endpoint = isAdmin ? "/admin/api-keys" : "/v1/api-keys";
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      };

      if (isAdmin && adminToken) {
        headers["X-Admin-Token"] = adminToken;
      } else {
        headers["Authorization"] = `Bearer ${getApiKey()}`;
      }

      const r = await fetch(`${apiBase}${endpoint}`, { headers });

      if (!r.ok) {
        if (r.status === 401) {
          setError("Authentication failed. Check your API key or admin token.");
        } else {
          setError(`Failed to fetch keys: ${r.status} ${r.statusText}`);
        }
        return;
      }

      const data = await r.json();
      setKeys(Array.isArray(data) ? data : []);
    } catch (e: any) {
      setError(`Error: ${e.message}`);
    } finally {
      setLoading(false);
    }
  }

  async function createKey() {
    if (!newKeyName.trim()) {
      setError("Please enter a name for the key");
      return;
    }

    setCreating(true);
    setError(null);

    try {
      const apiBase = getApiBase();
      const endpoint = isAdmin
        ? `/admin/api-keys?name=${encodeURIComponent(newKeyName)}`
        : "/v1/api-keys/";
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      };

      if (isAdmin && adminToken) {
        headers["X-Admin-Token"] = adminToken;
      } else {
        headers["Authorization"] = `Bearer ${getApiKey()}`;
      }

      const body = isAdmin
        ? undefined
        : JSON.stringify({
            name: newKeyName,
            tenant_id: "tenant_demo", // Default tenant
            rate_limit_per_minute: 100,
            rate_limit_per_hour: 5000,
          });

      const r = await fetch(`${apiBase}${endpoint}`, {
        method: "POST",
        headers,
        body,
      });

      if (!r.ok) {
        const errorText = await r.text();
        setError(`Failed to create key: ${r.status} ${errorText}`);
        return;
      }

      const data = await r.json();
      setNewKey(data.api_key || data.key);
      setNewKeyName("");
      setShowCreateModal(false);
      fetchKeys();
    } catch (e: any) {
      setError(`Error: ${e.message}`);
    } finally {
      setCreating(false);
    }
  }

  async function revokeKey(keyId: string) {
    if (!confirm("Are you sure you want to revoke this API key? It will stop working immediately.")) {
      return;
    }

    try {
      const apiBase = getApiBase();
      const endpoint = isAdmin
        ? `/admin/api-keys/${keyId}/revoke`
        : `/v1/api-keys/${keyId}/revoke`;
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      };

      if (isAdmin && adminToken) {
        headers["X-Admin-Token"] = adminToken;
      } else {
        headers["Authorization"] = `Bearer ${getApiKey()}`;
      }

      const r = await fetch(`${apiBase}${endpoint}`, {
        method: "POST",
        headers,
      });

      if (!r.ok) {
        setError(`Failed to revoke key: ${r.status}`);
        return;
      }

      fetchKeys();
    } catch (e: any) {
      setError(`Error: ${e.message}`);
    }
  }

  async function activateKey(keyId: string) {
    try {
      const apiBase = getApiBase();
      const endpoint = isAdmin
        ? `/admin/api-keys/${keyId}/activate`
        : `/v1/api-keys/${keyId}/reactivate`;
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      };

      if (isAdmin && adminToken) {
        headers["X-Admin-Token"] = adminToken;
      } else {
        headers["Authorization"] = `Bearer ${getApiKey()}`;
      }

      const r = await fetch(`${apiBase}${endpoint}`, {
        method: "POST",
        headers,
      });

      if (!r.ok) {
        setError(`Failed to activate key: ${r.status}`);
        return;
      }

      fetchKeys();
    } catch (e: any) {
      setError(`Error: ${e.message}`);
    }
  }

  function copyToClipboard(text: string) {
    navigator.clipboard.writeText(text).then(() => {
      alert("Copied to clipboard!");
    });
  }

  function enableAdminMode() {
    if (adminToken.trim()) {
      localStorage.setItem("docparser_admin_token", adminToken.trim());
      setIsAdmin(true);
      fetchKeys();
    } else {
      setError("Please enter an admin token");
    }
  }

  function disableAdminMode() {
    localStorage.removeItem("docparser_admin_token");
    setAdminToken("");
    setIsAdmin(false);
    fetchKeys();
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 text-slate-100">
      <div className="max-w-7xl mx-auto p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-slate-50">API Key Management</h1>
            <p className="text-sm text-slate-400 mt-1">
              Create and manage API keys for accessing the DocParser API
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Link
              href="/dashboard"
              className="px-4 py-2 rounded-lg border border-slate-700 bg-slate-900/60 text-slate-300 hover:bg-slate-800 transition"
            >
              ← Back to Dashboard
            </Link>
            <button
              onClick={() => setShowCreateModal(true)}
              className="px-4 py-2 rounded-lg bg-indigo-600 text-white hover:bg-indigo-500 transition"
            >
              + Create Key
            </button>
          </div>
        </div>

        {/* Admin Mode Toggle */}
        <div className="mb-6 p-4 rounded-lg border border-slate-800 bg-slate-900/60">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-slate-200">Admin Mode</h3>
              <p className="text-xs text-slate-400 mt-1">
                {isAdmin
                  ? "Viewing all API keys across all tenants"
                  : "Viewing only your tenant's keys"}
              </p>
            </div>
            {!isAdmin ? (
              <div className="flex items-center gap-2">
                <input
                  type="password"
                  value={adminToken}
                  onChange={(e) => setAdminToken(e.target.value)}
                  placeholder="Enter admin token"
                  className="px-3 py-1.5 rounded border border-slate-700 bg-slate-950 text-sm text-slate-100 placeholder-slate-500"
                />
                <button
                  onClick={enableAdminMode}
                  className="px-3 py-1.5 rounded bg-slate-800 text-slate-300 hover:bg-slate-700 text-sm transition"
                >
                  Enable
                </button>
              </div>
            ) : (
              <button
                onClick={disableAdminMode}
                className="px-3 py-1.5 rounded bg-red-900/50 text-red-300 hover:bg-red-900/70 text-sm transition"
              >
                Disable Admin Mode
              </button>
            )}
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-6 p-4 rounded-lg bg-red-900/20 border border-red-800 text-red-300 text-sm">
            {error}
          </div>
        )}

        {/* New Key Display */}
        {newKey && (
          <div className="mb-6 p-6 rounded-lg bg-emerald-900/20 border border-emerald-800">
            <h3 className="text-lg font-semibold text-emerald-300 mb-2">
              ⚠️ API Key Created - Save This Now!
            </h3>
            <p className="text-sm text-slate-400 mb-3">
              This is the ONLY time the key will be shown. Copy it immediately.
            </p>
            <div className="flex items-center gap-2">
              <code className="flex-1 px-4 py-3 rounded bg-slate-950 border border-slate-700 text-slate-100 font-mono text-sm break-all">
                {newKey}
              </code>
              <button
                onClick={() => copyToClipboard(newKey)}
                className="px-4 py-3 rounded bg-indigo-600 text-white hover:bg-indigo-500 transition"
              >
                Copy
              </button>
            </div>
            <button
              onClick={() => setNewKey(null)}
              className="mt-3 text-sm text-slate-400 hover:text-slate-300"
            >
              I've saved it, dismiss
            </button>
          </div>
        )}

        {/* Keys List */}
        {loading ? (
          <div className="text-center py-12 text-slate-400">Loading API keys...</div>
        ) : keys.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-slate-400 mb-4">No API keys found</p>
            <button
              onClick={() => setShowCreateModal(true)}
              className="px-4 py-2 rounded-lg bg-indigo-600 text-white hover:bg-indigo-500 transition"
            >
              Create Your First Key
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            {keys.map((key) => (
              <div
                key={key.id}
                className="p-4 rounded-lg border border-slate-800 bg-slate-900/60 hover:bg-slate-900/80 transition"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="font-semibold text-slate-100">
                        {key.name || "Unnamed Key"}
                      </h3>
                      <span
                        className={`px-2 py-0.5 rounded text-xs font-medium ${
                          key.active
                            ? "bg-emerald-900/50 text-emerald-300"
                            : "bg-red-900/50 text-red-300"
                        }`}
                      >
                        {key.active ? "Active" : "Revoked"}
                      </span>
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm text-slate-400">
                      <div>
                        <span className="text-slate-500">ID:</span>{" "}
                        <code className="text-slate-300">{key.id}</code>
                      </div>
                      <div>
                        <span className="text-slate-500">Tenant:</span>{" "}
                        <span className="text-slate-300">{key.tenant_id}</span>
                      </div>
                      <div>
                        <span className="text-slate-500">Rate Limit:</span>{" "}
                        <span className="text-slate-300">
                          {key.rate_limit_per_minute}/min, {key.rate_limit_per_hour}/hr
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-500">Last Used:</span>{" "}
                        <span className="text-slate-300">
                          {key.last_used_at
                            ? new Date(key.last_used_at).toLocaleDateString()
                            : "Never"}
                        </span>
                      </div>
                    </div>
                    <div className="mt-2 text-xs text-slate-500">
                      Created: {new Date(key.created_at).toLocaleString()}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 ml-4">
                    {key.active ? (
                      <button
                        onClick={() => revokeKey(key.id)}
                        className="px-3 py-1.5 rounded bg-red-900/50 text-red-300 hover:bg-red-900/70 text-sm transition"
                      >
                        Revoke
                      </button>
                    ) : (
                      <button
                        onClick={() => activateKey(key.id)}
                        className="px-3 py-1.5 rounded bg-emerald-900/50 text-emerald-300 hover:bg-emerald-900/70 text-sm transition"
                      >
                        Activate
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Create Modal */}
        {showCreateModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-slate-900 rounded-lg border border-slate-800 p-6 max-w-md w-full">
              <h2 className="text-xl font-semibold text-slate-100 mb-4">Create New API Key</h2>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Key Name
                  </label>
                  <input
                    type="text"
                    value={newKeyName}
                    onChange={(e) => setNewKeyName(e.target.value)}
                    placeholder="e.g., Production Key, Test Key"
                    className="w-full px-3 py-2 rounded border border-slate-700 bg-slate-950 text-slate-100 placeholder-slate-500"
                    autoFocus
                  />
                </div>
                <div className="flex items-center gap-3">
                  <button
                    onClick={createKey}
                    disabled={creating}
                    className="flex-1 px-4 py-2 rounded bg-indigo-600 text-white hover:bg-indigo-500 transition disabled:opacity-50"
                  >
                    {creating ? "Creating..." : "Create Key"}
                  </button>
                  <button
                    onClick={() => {
                      setShowCreateModal(false);
                      setNewKeyName("");
                    }}
                    className="px-4 py-2 rounded border border-slate-700 bg-slate-800 text-slate-300 hover:bg-slate-700 transition"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

