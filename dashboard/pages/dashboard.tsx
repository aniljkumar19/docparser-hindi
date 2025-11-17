import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/router";

type Job = {
  job_id: string;
  status: string;
  doc_type?: string | null;
  filename?: string | null;
  result?: any;
  meta?: {
    detected_doc_type?: string | null;
    doc_type_confidence?: number | null;
    reconciliations?: {
      purchase_vs_gstr3b_itc?: PurchaseVsGstr3bRecon;
      sales_vs_gstr1?: SalesVsGstr1Recon;
    };
    [k: string]: any;
  } | null;
  created_at?: string;
};

type PurchaseVsGstr3bRecon = {
  status: string;
  itc_from_purchase_register?: Record<string, number>;
  itc_from_gstr3b?: Record<string, number>;
  totals?: {
    purchase_register?: Record<string, number>;
    gstr3b?: Record<string, number>;
  };
  difference?: Record<string, number>;
  invoice_contributions?: Array<Record<string, any>>;
  warnings?: string[];
  source_purchase_register_job_id?: string;
  source_purchase_register_filename?: string;
};

type SalesVsGstr1Recon = {
  status: string;
  totals?: {
    sales_register?: Record<string, number>;
    gstr1?: Record<string, number>;
  };
  difference?: Record<string, number>;
  missing_in_gstr1?: Array<{
    invoice_number: string;
    invoice_date?: string;
    customer_name?: string;
    customer_gstin?: string;
    taxable_value?: number;
    total_value?: number;
  }>;
  missing_in_sales_register?: Array<{
    invoice_number: string;
    invoice_date?: string;
    customer_name?: string;
    customer_gstin?: string;
    taxable_value?: number;
    total_value?: number;
  }>;
  value_mismatches?: Array<{
    invoice_number: string;
    invoice_date?: string;
    sales_register_value?: number;
    gstr1_value?: number;
    difference?: number;
  }>;
  warnings?: string[];
  source_sales_register_job_id?: string;
  source_sales_register_filename?: string;
  source_gstr1_job_id?: string;
  source_gstr1_filename?: string;
};

function formatTimeAgo(dateString: string | null | undefined): string {
  if (!dateString) return "Unknown";
  try {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    
    if (diffMins < 1) return "Just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  } catch {
    return "Unknown";
  }
}

export default function Dashboard() {
  const router = useRouter();
  const { job_id } = router.query;
  
  const [file, setFile] = useState<File | null>(null);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [polling, setPolling] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [docType, setDocType] = useState("");
  const [showRawJson, setShowRawJson] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [loadingJobs, setLoadingJobs] = useState(true);
  const [activeTab, setActiveTab] = useState<"parsed" | "reconciliation" | "exports">("parsed");
  const [loadingJob, setLoadingJob] = useState(false);
  const [salesReconTab, setSalesReconTab] = useState<"missing_gstr1" | "missing_sales" | "mismatches">("missing_gstr1");
  const [samples, setSamples] = useState<Array<{filename: string; name: string; type: string; description: string; size: number}>>([]);
  const [loadingSamples, setLoadingSamples] = useState(false);
  const [apiKey, setApiKey] = useState<string>("");
  const [showApiKeyScreen, setShowApiKeyScreen] = useState(false);

  // Helper to get API base URL (relative in production, absolute in dev)
  function getApiBase(): string {
    if (process.env.NEXT_PUBLIC_DOCPARSER_API_BASE) {
      return process.env.NEXT_PUBLIC_DOCPARSER_API_BASE;
    }
    if (typeof window !== 'undefined') {
      return window.location.origin; // Use same origin in production
    }
    return "http://localhost:8000"; // Fallback for SSR
  }

  // Helper to get API key
  function getApiKey(): string {
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem("docparser_api_key");
      if (stored) return stored;
    }
    return process.env.NEXT_PUBLIC_DOCPARSER_API_KEY || "dev_123";
  }

  // Fetch recent jobs on mount
  async function fetchJobs() {
    try {
      const apiBase = getApiBase();
      const r = await fetch(`${apiBase}/v1/jobs?limit=10`, {
        headers: {
          "Authorization": `Bearer ${getApiKey()}`
        },
      });
      
      if (r.ok) {
        const jobsList = await r.json();
        console.log("Fetched jobs:", jobsList.length, jobsList);
        setJobs(jobsList);
        // Save to sessionStorage for persistence
        if (typeof window !== "undefined") {
          try {
            sessionStorage.setItem("docparser_jobs_list", JSON.stringify(jobsList));
          } catch (e) {
            console.warn("Failed to save jobs to sessionStorage", e);
          }
        }
      } else {
        console.error("Failed to fetch jobs:", r.status, r.statusText);
        const errorText = await r.text().catch(() => "");
        console.error("Error response:", errorText);
      }
    } catch (e) {
      console.error("Failed to fetch jobs", e);
      // On error, try to load from sessionStorage as fallback
      if (typeof window !== "undefined") {
        try {
          const cached = sessionStorage.getItem("docparser_jobs_list");
          if (cached) {
            const jobsList = JSON.parse(cached);
            setJobs(jobsList);
          }
        } catch (e) {
          console.warn("Failed to load jobs from sessionStorage", e);
        }
      }
    } finally {
      setLoadingJobs(false);
    }
  }

  // Load job by ID
  async function loadJobById(jobId: string) {
    setLoadingJob(true);
    try {
      // Try to load from sessionStorage first for instant display
      if (typeof window !== "undefined") {
        try {
          const cachedJob = sessionStorage.getItem(`docparser_job_${jobId}`);
          if (cachedJob) {
            const job: Job = JSON.parse(cachedJob);
            setSelectedJob(job);
            // Still fetch fresh data, but show cached version immediately
          }
        } catch (e) {
          console.warn("Failed to load job from sessionStorage", e);
        }
      }

      const apiBase = getApiBase();
      const r = await fetch(`${apiBase}/v1/jobs/${jobId}`, {
        headers: {
          "Authorization": `Bearer ${getApiKey()}`
        },
      });
      
      if (r.ok) {
        const job: Job = await r.json();
        setSelectedJob(job);
        // Save to sessionStorage for persistence
        if (typeof window !== "undefined") {
          try {
            sessionStorage.setItem("lastViewedJobId", jobId);
            sessionStorage.setItem(`docparser_job_${jobId}`, JSON.stringify(job));
          } catch (e) {
            console.warn("Failed to save job to sessionStorage", e);
          }
        }
        // If job is still processing, start polling
        if (job.status === "queued" || job.status === "processing") {
          pollJob(jobId);
        }
      } else if (r.status === 404) {
        // Job not found in API - might be from local dev or deleted
        console.warn(`Job ${jobId} not found in API (404). Using cached data if available.`);
        // Keep the cached job if it exists, but show a warning
        if (selectedJob && selectedJob.job_id === jobId) {
          // Already showing cached version, that's fine
          setError("Job not found in server. Showing cached data.");
        } else {
          setError("Job not found. It may have been deleted or created in a different environment.");
          setSelectedJob(null);
        }
      } else {
        console.error("Failed to load job:", r.status, r.statusText);
        const errorText = await r.text().catch(() => "");
        console.error("Error response:", errorText);
        setError(`Failed to load job: ${r.status} ${r.statusText}`);
      }
    } catch (e) {
      console.error("Failed to load job", e);
      setError("Failed to load job");
    } finally {
      setLoadingJob(false);
    }
  }

  useEffect(() => {
    // Load jobs from sessionStorage immediately for instant display
    if (typeof window !== "undefined") {
      try {
        const cached = sessionStorage.getItem("docparser_jobs_list");
        if (cached) {
          const jobsList = JSON.parse(cached);
          setJobs(jobsList);
          setLoadingJobs(false);
        }
      } catch (e) {
        console.warn("Failed to load jobs from sessionStorage", e);
      }
    }
    // Then fetch fresh data from API
    fetchJobs();
  }, []);

  // Clear sessionStorage if we detect environment mismatch (jobs in cache but API returns empty)
  useEffect(() => {
    if (typeof window !== "undefined" && jobs.length === 0 && !loadingJobs) {
      // Check if we have cached jobs but API returned empty - likely environment mismatch
      const cached = sessionStorage.getItem("docparser_jobs_list");
      if (cached) {
        try {
          const cachedJobs = JSON.parse(cached);
          if (cachedJobs.length > 0) {
            console.warn("Detected environment mismatch: cached jobs exist but API returned empty. Clearing cache.");
            // Clear all cached data
            sessionStorage.removeItem("docparser_jobs_list");
            sessionStorage.removeItem("lastViewedJobId");
            // Clear all job caches
            Object.keys(sessionStorage).forEach(key => {
              if (key.startsWith("docparser_job_")) {
                sessionStorage.removeItem(key);
              }
            });
            setSelectedJob(null);
            setError("Switched environments. Please upload new documents.");
          }
        } catch (e) {
          // Ignore parse errors
        }
      }
    }
  }, [jobs.length, loadingJobs]);

  // STEP 8: Session persistence - load last viewed job if no job_id in URL
  useEffect(() => {
    if (typeof window !== "undefined" && !job_id && jobs.length === 0) {
      const lastJobId = sessionStorage.getItem("lastViewedJobId");
      if (lastJobId) {
        // Only load if we don't have a job_id in URL and jobs are loaded
        setTimeout(() => {
          router.push(`/dashboard?job_id=${lastJobId}`, undefined, { shallow: true });
        }, 100);
      }
    }
  }, [jobs.length, job_id]);

  // Handle job_id query parameter
  useEffect(() => {
    if (job_id && typeof job_id === "string") {
      loadJobById(job_id);
    }
  }, [job_id]);

  async function uploadAndParse() {
    setError(null);
    if (!file) return;
    
    setUploading(true);
    const fd = new FormData();
    fd.append("file", file);
    if (docType) {
      fd.append("doc_type", docType);
    }
    
    try {
      const apiBase = getApiBase();
      const r = await fetch(`${apiBase}/v1/parse`, {
        method: "POST",
        headers: { 
          "Authorization": `Bearer ${getApiKey()}`
        },
        body: fd
      });
      
      if (!r.ok) {
        const errorData = await r.json().catch(() => ({ detail: r.statusText }));
        throw new Error(errorData.detail || `Upload failed: ${r.status} ${r.statusText}`);
      }
      
      const j = await r.json();
      if (!j.job_id) {
        throw new Error("API response missing job_id");
      }
      
      const newJob: Job = {
        job_id: j.job_id,
        status: j.status,
        doc_type: j.doc_type,
        filename: file.name,
        result: j.result,
        meta: j.meta,
      };
      
      setSelectedJob(newJob);
      setFile(null);
      
      // Save new job to sessionStorage
      if (typeof window !== "undefined") {
        try {
          sessionStorage.setItem("lastViewedJobId", j.job_id);
          sessionStorage.setItem(`docparser_job_${j.job_id}`, JSON.stringify(newJob));
        } catch (e) {
          console.warn("Failed to save job to sessionStorage", e);
        }
      }
      
      // Update URL with job_id
      router.push(`/dashboard?job_id=${j.job_id}`, undefined, { shallow: true });
      
      // Refresh jobs list
      await fetchJobs();
      
      // Start polling for full result
      pollJob(j.job_id);
    } catch (e: any) {
      setError(e?.message || "Failed to upload file");
    } finally {
      setUploading(false);
    }
  }

  async function pollJob(id: string) {
    if (!id || id === "undefined") {
      setError("Invalid job ID");
      return;
    }
    
    setPolling(true);
    try {
      let tries = 0;
      while (tries++ < 30) {
        const apiBase = getApiBase();
        const r = await fetch(`${apiBase}/v1/jobs/${id}`, {
          headers: { "Authorization": `Bearer ${process.env.NEXT_PUBLIC_DOCPARSER_API_KEY || "dev_123"}` }
        });
        
        if (!r.ok) {
          if (r.status === 404) {
            setError("Job not found");
            break;
          }
          const errorData = await r.json().catch(() => ({ detail: r.statusText }));
          setError(errorData.detail || `Failed to fetch job: ${r.status}`);
          break;
        }
        
        const j: Job = await r.json();
        setSelectedJob(j);
        // Save updated job to sessionStorage
        if (typeof window !== "undefined") {
          try {
            sessionStorage.setItem(`docparser_job_${j.job_id}`, JSON.stringify(j));
          } catch (e) {
            console.warn("Failed to save job to sessionStorage", e);
          }
        }
        // Update jobs list with latest status
        setJobs(prev => {
          const updated = prev.map(job => job.job_id === j.job_id ? { ...job, status: j.status, doc_type: j.doc_type } : job);
          // Save updated jobs list to sessionStorage
          if (typeof window !== "undefined") {
            try {
              sessionStorage.setItem("docparser_jobs_list", JSON.stringify(updated));
            } catch (e) {
              console.warn("Failed to save jobs list to sessionStorage", e);
            }
          }
          return updated;
        });
        
        if (j.status === "succeeded" || j.status === "failed" || j.status === "needs_review") break;
        await new Promise(res => setTimeout(res, 1000));
      }
    } catch (e: any) {
      setError(e?.message || "Failed to fetch job");
    } finally {
      setPolling(false);
    }
  }

  async function downloadExport(kind: "json" | "sales-csv" | "purchase-csv" | "sales-zoho" | "tally-xml") {
    if (!selectedJob) return;
    
    const apiBase = getApiBase();
    let path = "";
    
    if (kind === "json") path = `/v1/export/json/${selectedJob.job_id}`;
    else if (kind === "sales-csv") path = `/v1/export/sales-csv/${selectedJob.job_id}`;
    else if (kind === "purchase-csv") path = `/v1/export/purchase-csv/${selectedJob.job_id}`;
    else if (kind === "sales-zoho") path = `/v1/export/sales-zoho/${selectedJob.job_id}`;
    else if (kind === "tally-xml") path = `/v1/export/tally-xml/${selectedJob.job_id}`;
    
    try {
      const r = await fetch(`${apiBase}${path}`, {
        headers: {
          "Authorization": `Bearer ${getApiKey()}`
        },
      });
      
      if (!r.ok) {
        console.error("Export failed", r.status, await r.text());
        return;
      }
      
      const data = await r.json();
      const filename = data.filename || `${selectedJob.job_id}.txt`;
      const content = data.content || "";
      const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error("Export error", e);
    }
  }

  async function downloadReconciliationExport(
    kind: "missing-invoices-gstr1" | "missing-invoices-sales" | "value-mismatches" | "itc-summary"
  ) {
    if (!selectedJob) return;
    
    const apiBase = getApiBase();
    let path = "";
    
    if (kind === "missing-invoices-gstr1") {
      path = `/v1/export/reconciliation/missing-invoices/${selectedJob.job_id}?type=gstr1`;
    } else if (kind === "missing-invoices-sales") {
      path = `/v1/export/reconciliation/missing-invoices/${selectedJob.job_id}?type=sales_register`;
    } else if (kind === "value-mismatches") {
      path = `/v1/export/reconciliation/value-mismatches/${selectedJob.job_id}`;
    } else if (kind === "itc-summary") {
      path = `/v1/export/reconciliation/itc-summary/${selectedJob.job_id}`;
    }
    
    try {
      const r = await fetch(`${apiBase}${path}`, {
        headers: {
          "Authorization": `Bearer ${getApiKey()}`
        },
      });
      
      if (!r.ok) {
        const errorText = await r.text();
        console.error("Reconciliation export failed", r.status, errorText);
        alert(`Export failed: ${r.status === 404 ? "No data found" : "Server error"}`);
        return;
      }
      
      const data = await r.json();
      const filename = data.filename || `${kind}_${selectedJob.job_id}.csv`;
      const content = data.content || "";
      const blob = new Blob([content], { type: "text/csv;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error("Reconciliation export error", e);
      alert("Failed to download export");
    }
  }

  function copyShareUrl() {
    if (!selectedJob) return;
    const shareUrl = `${window.location.origin}/dashboard?job_id=${selectedJob.job_id}`;
    navigator.clipboard.writeText(shareUrl).then(() => {
      alert("Share URL copied to clipboard!");
    }).catch(() => {
      // Fallback for older browsers
      const textarea = document.createElement("textarea");
      textarea.value = shareUrl;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
      alert("Share URL copied to clipboard!");
    });
  }

  async function fetchSamples() {
    setLoadingSamples(true);
    try {
      const apiBase = getApiBase();
      const r = await fetch(`${apiBase}/v1/samples`);
      if (r.ok) {
        const data = await r.json();
        setSamples(data.samples || []);
      }
    } catch (e) {
      console.error("Failed to fetch samples", e);
    } finally {
      setLoadingSamples(false);
    }
  }

  function downloadSample(filename: string) {
    const apiBase = getApiBase();
    const url = `${apiBase}/v1/samples/${filename}`;
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
  }

  function handleApiKeySubmit() {
    if (apiKey.trim()) {
      localStorage.setItem("docparser_api_key", apiKey.trim());
      setShowApiKeyScreen(false);
      // Reload to apply API key
      window.location.reload();
    }
  }

  useEffect(() => {
    // Check for API key on mount
    if (typeof window !== "undefined") {
      const storedKey = localStorage.getItem("docparser_api_key");
      if (!storedKey && !process.env.NEXT_PUBLIC_DOCPARSER_API_KEY) {
        setShowApiKeyScreen(true);
      } else if (storedKey) {
        setApiKey(storedKey);
      }
    }
    fetchSamples();
  }, []);

  const recon = selectedJob?.meta?.reconciliations?.purchase_vs_gstr3b_itc as PurchaseVsGstr3bRecon | undefined;
  const salesRecon = selectedJob?.meta?.reconciliations?.sales_vs_gstr1 as SalesVsGstr1Recon | undefined;
  const detected = selectedJob?.meta?.detected_doc_type ?? selectedJob?.doc_type ?? null;

  // Debug: Log reconciliation data
  if (selectedJob) {
    console.log("Selected job:", selectedJob.job_id);
    console.log("Job meta:", selectedJob.meta);
    console.log("Reconciliations:", selectedJob.meta?.reconciliations);
    console.log("Purchase recon:", recon);
    console.log("Sales recon:", salesRecon);
    console.log("Has reconciliation tab:", !!(recon || salesRecon));
  }

  // API Key login screen
  if (showApiKeyScreen) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 text-slate-100 flex items-center justify-center p-4">
        <div className="max-w-md w-full rounded-2xl border border-slate-800 bg-slate-900/90 p-6 shadow-lg shadow-black/40">
          <div className="flex items-center gap-3 mb-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-slate-900 text-xs font-bold text-slate-100 shadow-lg shadow-slate-900/50">
              DP
            </div>
            <div>
              <h1 className="text-base font-semibold text-slate-50">DocParser Dashboard</h1>
              <p className="text-[11px] text-slate-400">Enter your API key to continue</p>
            </div>
          </div>
          
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleApiKeySubmit();
            }}
            className="space-y-4"
          >
            <div>
              <label htmlFor="api_key" className="block text-[11px] font-medium text-slate-300 mb-2">
                API Key
              </label>
              <input
                id="api_key"
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="Enter your API key"
                className="w-full rounded-lg border border-slate-700 bg-slate-950/90 px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
                required
              />
              <p className="mt-1.5 text-[10px] text-slate-500">
                Your API key is stored locally and never shared
              </p>
            </div>
            
            <button
              type="submit"
              className="w-full rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-medium text-white shadow-md shadow-indigo-500/40 hover:bg-indigo-500 focus:outline-none"
            >
              Continue
            </button>
          </form>
          
          <div className="mt-4 pt-4 border-t border-slate-800">
            <p className="text-[10px] text-slate-500 text-center">
              Don't have an API key? Contact your administrator or use the default key for testing.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 text-slate-100">
      {/* Header */}
      <header className="border-b border-slate-800/70 bg-slate-950/70 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-2xl bg-slate-900 text-xs font-bold text-slate-100 shadow-lg shadow-slate-900/50">
              DP
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-sm font-semibold text-slate-50">DocParser Dashboard</h1>
                <span className="inline-flex items-center rounded-full bg-emerald-500/10 px-2.5 py-0.5 text-[10px] font-medium text-emerald-300 border border-emerald-500/20">
                  • Beta
                </span>
              </div>
              <p className="text-[11px] text-slate-400">
                Upload GST & finance PDFs → parse, reconcile & export (Tally, CSV, JSON).
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Link href="/" className="text-[11px] text-slate-400 hover:text-slate-200">
              API home
            </Link>
            <button
              onClick={() => {
                localStorage.removeItem("docparser_api_key");
                setShowApiKeyScreen(true);
              }}
              className="text-[11px] text-slate-400 hover:text-slate-200"
              title="Change API key"
            >
              🔑 API Key
            </button>
            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2.5 py-0.5 text-[10px] font-medium text-emerald-300 border border-emerald-500/20">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400"></span>
              API online
            </span>
          </div>
        </div>
      </header>

      {/* Main */}
      <main className="mx-auto max-w-7xl px-4 py-6 space-y-5">
        {/* Top layout: left = upload & jobs, right = active job */}
        <div className="grid gap-5 grid-cols-1 md:grid-cols-[400px_1fr]">
          {/* LEFT COLUMN */}
          <div className="space-y-5">
            {/* Upload card */}
            <section className="rounded-2xl border border-slate-800 bg-slate-900/90 p-4 shadow-lg shadow-black/40">
              <h2 className="text-xs font-semibold text-slate-200 uppercase tracking-wide">
                Upload document
              </h2>
              <p className="mt-1 text-[11px] text-slate-400">
                Bank statements, GST invoices, GSTR-1 / 3B, purchase & sales registers (PDF / CSV).
              </p>
              {/* STEP 6: Helpful hint */}
              <div className="mt-2 rounded-lg bg-blue-500/10 border border-blue-500/30 px-2 py-1.5 text-[10px] text-blue-300">
                💡 We auto-detect document type. Leave it on "Auto-detect" for best results.
              </div>

              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  uploadAndParse();
                }}
                className="mt-4 space-y-3"
              >
                <label className="flex cursor-pointer flex-col items-center justify-center rounded-xl border border-dashed border-slate-700 bg-slate-900/60 px-4 py-6 text-center hover:border-indigo-500 hover:bg-slate-900/80 transition">
                  <span className="mb-2 inline-flex h-9 w-9 items-center justify-center rounded-full bg-indigo-500/20 text-indigo-400">
                    ⬆
                  </span>
                  <span className="text-xs font-medium text-slate-100">
                    {file ? file.name : "Drop file here or click to browse"}
                  </span>
                  <span className="mt-1 text-[11px] text-slate-400">
                    Max ~15 MB. We auto-detect document type.
                  </span>
                  <input
                    type="file"
                    onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                    className="hidden"
                    required
                  />
                </label>

                <div className="flex flex-wrap items-center gap-3">
                  <div className="flex items-center gap-2">
                    <label htmlFor="doc_type" className="text-[11px] text-slate-300">
                      Doc type
                    </label>
                    <select
                      id="doc_type"
                      value={docType}
                      onChange={(e) => setDocType(e.target.value)}
                      className="rounded-lg border border-slate-700 bg-slate-900/70 px-2 py-1 text-[11px] text-slate-100 focus:border-indigo-500 focus:outline-none"
                    >
                      <option value="">Auto-detect</option>
                      <option value="bank_statement">Bank statement</option>
                      <option value="gst_invoice">GST invoice</option>
                      <option value="gstr3b">GSTR-3B</option>
                      <option value="gstr1">GSTR-1</option>
                      <option value="purchase_register">Purchase register</option>
                      <option value="sales_register">Sales register</option>
                    </select>
                  </div>
                  <button
                    type="submit"
                    disabled={!file || uploading}
                    className="inline-flex items-center rounded-xl bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white shadow-md shadow-indigo-500/40 hover:bg-indigo-500 focus:outline-none disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    {uploading ? "Uploading..." : "Upload & parse"}
                  </button>
                </div>
              </form>

              {error && (
                <div className="mt-3 rounded-lg bg-rose-500/10 border border-rose-500/30 px-3 py-2 text-[11px] text-rose-300">
                  {error}
                </div>
              )}
            </section>

            {/* Sample Documents section */}
            <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4 shadow-lg shadow-black/40">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-200">
                  Sample Documents
                </h2>
                <span className="text-[10px] text-slate-500">
                  Test instantly
                </span>
              </div>
              
              {loadingSamples ? (
                <div className="text-[11px] text-slate-400">Loading samples...</div>
              ) : samples.length === 0 ? (
                <div className="text-[11px] text-slate-400">No sample documents available</div>
              ) : (
                <div className="space-y-2">
                  {samples.map((sample) => (
                    <button
                      key={sample.filename}
                      onClick={() => downloadSample(sample.filename)}
                      className="w-full flex items-center justify-between rounded-lg border border-slate-700 bg-slate-900/80 px-3 py-2 text-left hover:border-indigo-500 hover:bg-slate-900 transition"
                    >
                      <div className="flex-1 min-w-0">
                        <p className="text-[11px] font-medium text-slate-100 truncate">
                          {sample.name}
                        </p>
                        <p className="text-[10px] text-slate-500 mt-0.5">
                          {sample.description}
                        </p>
                      </div>
                      <span className="ml-2 text-[10px] text-indigo-400">⬇</span>
                    </button>
                  ))}
                </div>
              )}
            </section>

            {/* Recent jobs card */}
            <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4 shadow-lg shadow-black/40">
              <div className="flex items-center justify-between">
                <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-200">
                  Recent jobs
                </h2>
                <span className="text-[10px] text-slate-500">
                  Latest {jobs.length} uploads
                </span>
              </div>

              {loadingJobs ? (
                <div className="mt-3 rounded-xl border border-dashed border-slate-700 bg-slate-950/60 px-3 py-3 text-[11px] text-slate-400">
                  Loading jobs...
                </div>
              ) : jobs.length === 0 ? (
                <div className="mt-3 rounded-xl border border-dashed border-slate-700 bg-slate-950/60 px-3 py-3 text-[11px] text-slate-400">
                  No jobs yet. Upload a sample bank statement, GST invoice or register to see parsed
                  data and reconciliations here.
                </div>
              ) : (
                <ul className="mt-3 divide-y divide-slate-800 text-[11px]">
                  {jobs.map((job) => (
                    <li key={job.job_id} className="flex items-center justify-between py-2">
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-slate-100 truncate">
                          {job.filename || "Untitled"}
                        </p>
                        <p className="text-[10px] text-slate-500">
                          {job.doc_type || "unknown"} · {job.status} · {formatTimeAgo(job.created_at)}
                        </p>
                      </div>
                      <button
                        onClick={() => {
                          router.push(`/dashboard?job_id=${job.job_id}`, undefined, { shallow: true });
                          loadJobById(job.job_id);
                        }}
                        className="ml-2 rounded-lg bg-slate-800 px-2 py-1 text-[10px] text-slate-100 hover:bg-slate-700"
                      >
                        View
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>

          {/* RIGHT COLUMN: Active job details */}
          <div className="space-y-5">
            {loadingJob ? (
              /* STEP 5: Skeleton loader */
              <section className="rounded-2xl border border-slate-800 bg-slate-900/90 p-6 shadow-lg shadow-black/40 animate-pulse">
                <div className="h-6 bg-slate-800 rounded w-1/3 mb-4"></div>
                <div className="h-4 bg-slate-800 rounded w-1/2 mb-2"></div>
                <div className="h-4 bg-slate-800 rounded w-2/3"></div>
              </section>
            ) : !selectedJob ? (
              <section className="rounded-2xl border border-slate-800 bg-slate-900/90 p-6 shadow-lg shadow-black/40">
                <p className="text-sm font-semibold text-slate-200">
                  No job selected
                </p>
                <p className="mt-1 text-[11px] text-slate-400">
                  Upload a document on the left to view parsed results, reconciliations, and exports here.
                </p>
                {/* STEP 6: Helpful hints */}
                <div className="mt-4 rounded-lg bg-blue-500/10 border border-blue-500/30 px-3 py-2 text-[11px] text-blue-300">
                  <p className="font-medium mb-1">💡 Tip:</p>
                  <p>We auto-detect document type. Upload a GSTR-3B sample if you want to test reconciliation.</p>
                </div>
              </section>
            ) : (
              <div className="space-y-5">
                {/* STEP 2: Header with parsed doc type, date, legal name, GSTIN, Job ID */}
                <section className="rounded-2xl border border-slate-800 bg-slate-900/90 p-5 shadow-lg shadow-black/40">
                  <div className="space-y-3">
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap mb-2">
                          <h2 className="text-base font-semibold text-slate-50 capitalize">
                            {detected?.replace("_", " ") || "Document"}
                          </h2>
                          <span
                            className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-[10px] font-medium ${
                              selectedJob.status === "succeeded"
                                ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                                : selectedJob.status === "failed"
                                ? "border-rose-500/30 bg-rose-500/10 text-rose-300"
                                : "border-amber-500/30 bg-amber-500/10 text-amber-300"
                            }`}
                          >
                            {selectedJob.status === "succeeded" ? "✔ Parsed successfully" : selectedJob.status}
                          </span>
                        </div>
                        
                        {/* Extract real data from parsed result */}
                        {selectedJob.result && (
                          <div className="space-y-1.5 text-[11px]">
                            {selectedJob.result.legal_name && (
                              <p className="text-slate-200">
                                <span className="text-slate-400">Legal name:</span>{" "}
                                <span className="font-medium">{selectedJob.result.legal_name}</span>
                              </p>
                            )}
                            {selectedJob.result.gstin && (
                              <p className="text-slate-200">
                                <span className="text-slate-400">GSTIN:</span>{" "}
                                <span className="font-mono font-medium">{selectedJob.result.gstin}</span>
                              </p>
                            )}
                            {(selectedJob.result.period || selectedJob.result.date) && (
                              <p className="text-slate-200">
                                <span className="text-slate-400">Period:</span>{" "}
                                <span className="font-medium">
                                  {selectedJob.result.period?.label || 
                                   selectedJob.result.period || 
                                   selectedJob.result.date || 
                                   "N/A"}
                                </span>
                              </p>
                            )}
                          </div>
                        )}
                        
                        <div className="mt-2 pt-2 border-t border-slate-800 flex items-center justify-between">
                          <p className="text-[10px] text-slate-500">
                            Job ID: <span className="font-mono text-slate-300">{selectedJob.job_id}</span>
                            {selectedJob.filename && (
                              <>
                                {" · "}File: <span className="text-slate-400">{selectedJob.filename}</span>
                              </>
                            )}
                          </p>
                          <button
                            onClick={copyShareUrl}
                            className="flex items-center gap-1.5 rounded-lg bg-indigo-500/20 hover:bg-indigo-500/30 border border-indigo-500/40 px-2.5 py-1 text-[10px] text-indigo-300 transition"
                            title="Copy shareable link"
                          >
                            <span>🔗</span>
                            <span>Share</span>
                          </button>
                        </div>
                      </div>
                    </div>

                    {/* STEP 2: Tabs */}
                    <div className="flex gap-1 border-b border-slate-800">
                      <button
                        onClick={() => setActiveTab("parsed")}
                        className={`px-4 py-2 text-[11px] font-medium transition ${
                          activeTab === "parsed"
                            ? "text-slate-100 border-b-2 border-indigo-500"
                            : "text-slate-400 hover:text-slate-200"
                        }`}
                      >
                        Parsed JSON
                      </button>
                      {(recon || salesRecon) && (
                        <button
                          onClick={() => setActiveTab("reconciliation")}
                          className={`px-4 py-2 text-[11px] font-medium transition ${
                            activeTab === "reconciliation"
                              ? "text-slate-100 border-b-2 border-indigo-500"
                              : "text-slate-400 hover:text-slate-200"
                          }`}
                        >
                          Reconciliation
                        </button>
                      )}
                      <button
                        onClick={() => setActiveTab("exports")}
                        className={`px-4 py-2 text-[11px] font-medium transition ${
                          activeTab === "exports"
                            ? "text-slate-100 border-b-2 border-indigo-500"
                            : "text-slate-400 hover:text-slate-200"
                        }`}
                      >
                        Exports
                      </button>
                    </div>
                  </div>
                </section>

                {/* Tab content */}
                {activeTab === "parsed" && (
                  <section className="rounded-2xl border border-slate-800 bg-slate-900/90 p-5 shadow-lg shadow-black/40">
                    <div className="mb-3 flex items-center justify-between">
                      <h3 className="text-xs font-semibold text-slate-200">Parsed Output</h3>
                      {polling && (
                        <span className="text-[10px] text-slate-400 animate-pulse">Processing...</span>
                      )}
                    </div>
                    {/* STEP 7: Enhanced JSON beautifier */}
                    <div className="rounded-xl bg-slate-950/90 border border-slate-800 overflow-hidden">
                      <pre className="max-h-[600px] overflow-auto p-4 text-[11px] text-slate-100 font-mono leading-relaxed">
                        {JSON.stringify(selectedJob.result || {}, null, 2)}
                      </pre>
                    </div>
                  </section>
                )}

                {activeTab === "reconciliation" && recon && (
                  <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5 shadow-lg shadow-black/40">
                    <div className="flex items-center justify-between gap-4 flex-wrap mb-4">
                      <div>
                        <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-200">
                          Purchase Register vs GSTR-3B – ITC
                        </h3>
                        <p className="mt-1 text-[11px] text-slate-400">
                          {selectedJob.result?.period?.label && (
                            <>Period: {selectedJob.result.period.label} – </>
                          )}
                          Compare input tax credit eligible from purchase register vs ITC claimed in GSTR-3B.
                        </p>
                        {/* Show source purchase register job if available */}
                        {recon.source_purchase_register_job_id && (
                          <p className="mt-1.5 text-[10px] text-slate-500">
                            Source purchase register:{" "}
                            <span className="font-mono text-slate-400">
                              {recon.source_purchase_register_filename || "purchase_register"} ({recon.source_purchase_register_job_id})
                            </span>
                          </p>
                        )}
                      </div>
                      <div className="text-right text-[11px]">
                        <span
                          className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[10px] font-medium border ${
                            recon.status === "itc_overclaimed"
                              ? "bg-rose-500/10 text-rose-300 border-rose-500/30"
                              : recon.status === "itc_underclaimed"
                              ? "bg-emerald-500/10 text-emerald-300 border-emerald-500/30"
                              : "bg-emerald-500/10 text-emerald-300 border-emerald-500/30"
                          }`}
                          title={
                            recon.status === "itc_overclaimed"
                              ? "GSTR-3B ITC > Purchase register ITC"
                              : recon.status === "itc_underclaimed"
                              ? "GSTR-3B ITC < Purchase register ITC"
                              : "GSTR-3B ITC = Purchase register ITC"
                          }
                        >
                          {recon.status === "itc_overclaimed"
                            ? "ITC overclaimed"
                            : recon.status === "itc_underclaimed"
                            ? "ITC underclaimed"
                            : "Matched"}
                        </span>
                        {recon.difference && (
                          <p className="mt-1 text-slate-400">
                            Net difference:{" "}
                            <span
                              className={`font-semibold ${
                                recon.status === "itc_overclaimed"
                                  ? "text-rose-300"
                                  : recon.status === "itc_underclaimed"
                                  ? "text-emerald-300"
                                  : "text-emerald-300"
                              }`}
                            >
                              ₹{((recon.difference.total || 0)).toLocaleString()}
                            </span>
                          </p>
                        )}
                      </div>
                    </div>

                    {/* STEP 3: Reconciliation table */}
                    <div className="overflow-hidden rounded-xl border border-slate-800 bg-slate-950/60">
                      <table className="min-w-full divide-y divide-slate-800 text-[11px]">
                        <thead className="bg-slate-900">
                          <tr>
                            <th className="px-4 py-2 text-left font-semibold text-slate-400">Source</th>
                            <th className="px-4 py-2 text-right font-semibold text-slate-400">IGST</th>
                            <th className="px-4 py-2 text-right font-semibold text-slate-400">CGST</th>
                            <th className="px-4 py-2 text-right font-semibold text-slate-400">SGST</th>
                            <th className="px-4 py-2 text-right font-semibold text-slate-400">Total ITC</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800">
                          <tr>
                            <td className="px-4 py-2 text-slate-200">Purchase register</td>
                            <td className="px-4 py-2 text-right font-mono text-slate-100">
                              {((recon.totals?.purchase_register?.igst || recon.itc_from_purchase_register?.igst || 0)).toLocaleString()}
                            </td>
                            <td className="px-4 py-2 text-right font-mono text-slate-100">
                              {((recon.totals?.purchase_register?.cgst || recon.itc_from_purchase_register?.cgst || 0)).toLocaleString()}
                            </td>
                            <td className="px-4 py-2 text-right font-mono text-slate-100">
                              {((recon.totals?.purchase_register?.sgst || recon.itc_from_purchase_register?.sgst || 0)).toLocaleString()}
                            </td>
                            <td className="px-4 py-2 text-right font-mono font-semibold text-slate-50">
                              {((recon.totals?.purchase_register?.total || recon.itc_from_purchase_register?.total || 0)).toLocaleString()}
                            </td>
                          </tr>
                          <tr>
                            <td className="px-4 py-2 text-slate-200">GSTR-3B</td>
                            <td className="px-4 py-2 text-right font-mono text-slate-100">
                              {((recon.totals?.gstr3b?.igst || recon.itc_from_gstr3b?.igst || 0)).toLocaleString()}
                            </td>
                            <td className="px-4 py-2 text-right font-mono text-slate-100">
                              {((recon.totals?.gstr3b?.cgst || recon.itc_from_gstr3b?.cgst || 0)).toLocaleString()}
                            </td>
                            <td className="px-4 py-2 text-right font-mono text-slate-100">
                              {((recon.totals?.gstr3b?.sgst || recon.itc_from_gstr3b?.sgst || 0)).toLocaleString()}
                            </td>
                            <td className="px-4 py-2 text-right font-mono font-semibold text-slate-50">
                              {((recon.totals?.gstr3b?.total || recon.itc_from_gstr3b?.total || 0)).toLocaleString()}
                            </td>
                          </tr>
                          {recon.difference && (
                            <tr className={recon.status === "itc_overclaimed" ? "bg-rose-950/40" : recon.status === "itc_underclaimed" ? "bg-emerald-950/40" : ""}>
                              <td className={`px-4 py-2 font-semibold ${recon.status === "itc_overclaimed" ? "text-rose-200" : recon.status === "itc_underclaimed" ? "text-emerald-200" : "text-slate-200"}`}>
                                Difference
                              </td>
                              <td className={`px-4 py-2 text-right font-mono font-semibold ${recon.status === "itc_overclaimed" ? "text-rose-300" : recon.status === "itc_underclaimed" ? "text-emerald-300" : "text-slate-300"}`}>
                                {((recon.difference.igst || 0)).toLocaleString()}
                              </td>
                              <td className={`px-4 py-2 text-right font-mono font-semibold ${recon.status === "itc_overclaimed" ? "text-rose-300" : recon.status === "itc_underclaimed" ? "text-emerald-300" : "text-slate-300"}`}>
                                {((recon.difference.cgst || 0)).toLocaleString()}
                              </td>
                              <td className={`px-4 py-2 text-right font-mono font-semibold ${recon.status === "itc_overclaimed" ? "text-rose-300" : recon.status === "itc_underclaimed" ? "text-emerald-300" : "text-slate-300"}`}>
                                {((recon.difference.sgst || 0)).toLocaleString()}
                              </td>
                              <td className={`px-4 py-2 text-right font-mono font-semibold ${recon.status === "itc_overclaimed" ? "text-rose-200" : recon.status === "itc_underclaimed" ? "text-emerald-200" : "text-slate-200"}`}>
                                {((recon.difference.total || 0)).toLocaleString()}
                              </td>
                            </tr>
                          )}
                        </tbody>
                      </table>
                    </div>

                    {/* STEP 3: Warnings */}
                    {recon.warnings && recon.warnings.length > 0 && (
                      <div className="mt-4 rounded-lg bg-amber-500/10 border border-amber-500/30 px-3 py-2 text-[11px] text-amber-300">
                        <div className="font-medium mb-1">⚠️ Warnings:</div>
                        <ul className="list-disc list-inside space-y-0.5">
                          {recon.warnings.map((w, idx) => (
                            <li key={idx}>{w}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {recon.status === "itc_overclaimed" && (
                      <div className="mt-3 rounded-lg bg-rose-500/10 border border-rose-500/30 px-3 py-2 text-[11px] text-rose-300">
                        <div className="font-medium mb-1">🟥 ITC Overclaimed</div>
                        <p>You've claimed more ITC in GSTR-3B than eligible from your purchase register. Review and adjust before filing.</p>
                      </div>
                    )}

                    {recon.status === "itc_underclaimed" && (
                      <div className="mt-3 rounded-lg bg-emerald-500/10 border border-emerald-500/30 px-3 py-2 text-[11px] text-emerald-300">
                        <div className="font-medium mb-1">🟢 ITC Underclaimed</div>
                        <p>You've claimed less ITC than eligible. You may increase ITC claim after verification.</p>
                      </div>
                    )}

                    <p className="mt-3 text-[11px] text-slate-400">
                      Adjust ITC claimed in GSTR-3B or correct the purchase register before filing.
                    </p>
                    
                    <button
                      onClick={() => downloadReconciliationExport("itc-summary")}
                      className="mt-4 w-full rounded-lg bg-indigo-500/20 hover:bg-indigo-500/30 border border-indigo-500/40 px-3 py-2 text-[10px] font-medium text-indigo-300 transition"
                    >
                      📥 Export ITC Mismatch Summary → CSV
                    </button>
                  </section>
                )}

                {/* Sales Register vs GSTR-1 Reconciliation */}
                {activeTab === "reconciliation" && (
                  <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5 shadow-lg shadow-black/40">
                    <div className="mb-4">
                      <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-200">
                        Invoice matching – Sales Register vs GSTR-1
                      </h3>
                      <p className="mt-1 text-[11px] text-slate-400">
                        {selectedJob?.result?.period?.label && (
                          <>Period: {selectedJob.result.period.label} – </>
                        )}
                        Compare invoices in sales register with GSTR-1 return to identify discrepancies.
                      </p>
                      {/* Show source jobs if available */}
                      {salesRecon && (salesRecon.source_sales_register_job_id || salesRecon.source_gstr1_job_id) && (
                        <div className="mt-1.5 space-y-0.5 text-[10px] text-slate-500">
                          {salesRecon.source_sales_register_job_id && (
                            <p>
                              Source sales register:{" "}
                              <span className="font-mono text-slate-400">
                                {salesRecon.source_sales_register_filename || "sales_register"} ({salesRecon.source_sales_register_job_id})
                              </span>
                            </p>
                          )}
                          {salesRecon.source_gstr1_job_id && (
                            <p>
                              Source GSTR-1:{" "}
                              <span className="font-mono text-slate-400">
                                {salesRecon.source_gstr1_filename || "gstr1"} ({salesRecon.source_gstr1_job_id})
                              </span>
                            </p>
                          )}
                        </div>
                      )}
                    </div>

                    {/* Tabs */}
                    <div className="flex gap-1 border-b border-slate-800 mb-4">
                      <button
                        onClick={() => setSalesReconTab("missing_gstr1")}
                        className={`px-3 py-1.5 text-[10px] font-medium transition ${
                          salesReconTab === "missing_gstr1"
                            ? "text-slate-100 border-b-2 border-indigo-500"
                            : "text-slate-400 hover:text-slate-200"
                        }`}
                      >
                        Missing in GSTR-1
                        {salesRecon?.missing_in_gstr1 && (
                          <span className="ml-1.5 inline-flex items-center justify-center rounded-full bg-rose-500/20 text-rose-300 px-1.5 py-0.5 text-[9px]">
                            {salesRecon.missing_in_gstr1.length}
                          </span>
                        )}
                      </button>
                      <button
                        onClick={() => setSalesReconTab("missing_sales")}
                        className={`px-3 py-1.5 text-[10px] font-medium transition ${
                          salesReconTab === "missing_sales"
                            ? "text-slate-100 border-b-2 border-indigo-500"
                            : "text-slate-400 hover:text-slate-200"
                        }`}
                      >
                        Missing in Sales Register
                        {salesRecon?.missing_in_sales_register && (
                          <span className="ml-1.5 inline-flex items-center justify-center rounded-full bg-amber-500/20 text-amber-300 px-1.5 py-0.5 text-[9px]">
                            {salesRecon.missing_in_sales_register.length}
                          </span>
                        )}
                      </button>
                      <button
                        onClick={() => setSalesReconTab("mismatches")}
                        className={`px-3 py-1.5 text-[10px] font-medium transition ${
                          salesReconTab === "mismatches"
                            ? "text-slate-100 border-b-2 border-indigo-500"
                            : "text-slate-400 hover:text-slate-200"
                        }`}
                      >
                        Value Mismatches
                        {salesRecon?.value_mismatches && (
                          <span className="ml-1.5 inline-flex items-center justify-center rounded-full bg-blue-500/20 text-blue-300 px-1.5 py-0.5 text-[9px]">
                            {salesRecon.value_mismatches.length}
                          </span>
                        )}
                      </button>
                    </div>

                    {/* Tab content */}
                    {salesReconTab === "missing_gstr1" && (
                      <div>
                        {!salesRecon ? (
                          <div className="rounded-lg bg-slate-800/50 border border-slate-700 px-3 py-4 text-center">
                            <p className="text-[11px] text-slate-400">No reconciliation data available.</p>
                            <p className="text-[10px] text-slate-500 mt-1">Upload a sales register and GSTR-1 to see invoice matching results.</p>
                          </div>
                        ) : salesRecon.missing_in_gstr1 && salesRecon.missing_in_gstr1.length > 0 ? (
                          <>
                            <p className="text-[11px] text-slate-300 mb-3">
                              <span className="font-semibold text-rose-300">{salesRecon.missing_in_gstr1.length}</span> invoices found in sales register but not reported in GSTR-1.
                            </p>
                            <div className="overflow-hidden rounded-xl border border-slate-800 bg-slate-950/60">
                              <table className="min-w-full divide-y divide-slate-800 text-[10px]">
                                <thead className="bg-slate-900">
                                  <tr>
                                    <th className="px-3 py-2 text-left font-semibold text-slate-400">Invoice #</th>
                                    <th className="px-3 py-2 text-left font-semibold text-slate-400">Date</th>
                                    <th className="px-3 py-2 text-left font-semibold text-slate-400">Customer</th>
                                    <th className="px-3 py-2 text-right font-semibold text-slate-400">Taxable Value</th>
                                    <th className="px-3 py-2 text-right font-semibold text-slate-400">Total Value</th>
                                  </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-800">
                                  {salesRecon.missing_in_gstr1.slice(0, 5).map((inv, idx) => (
                                    <tr key={idx} className="bg-rose-950/20">
                                      <td className="px-3 py-2 font-mono text-slate-200">{inv.invoice_number || "—"}</td>
                                      <td className="px-3 py-2 text-slate-300">{inv.invoice_date || "—"}</td>
                                      <td className="px-3 py-2 text-slate-300">
                                        <div>{inv.customer_name || "—"}</div>
                                        {inv.customer_gstin && (
                                          <div className="text-[9px] text-slate-500 font-mono">{inv.customer_gstin}</div>
                                        )}
                                      </td>
                                      <td className="px-3 py-2 text-right font-mono text-slate-200">
                                        {((inv.taxable_value || 0)).toLocaleString()}
                                      </td>
                                      <td className="px-3 py-2 text-right font-mono font-semibold text-rose-300">
                                        {((inv.total_value || 0)).toLocaleString()}
                                      </td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                            {salesRecon.missing_in_gstr1.length > 5 && (
                              <p className="mt-2 text-[10px] text-slate-500">
                                Showing first 5 of {salesRecon.missing_in_gstr1.length} invoices. Review all invoices in your sales register.
                              </p>
                            )}
                            <button
                              onClick={() => downloadReconciliationExport("missing-invoices-gstr1")}
                              className="mt-3 w-full rounded-lg bg-rose-500/20 hover:bg-rose-500/30 border border-rose-500/40 px-3 py-2 text-[10px] font-medium text-rose-300 transition"
                            >
                              📥 Export Missing in GSTR-1 → CSV
                            </button>
                          </>
                        ) : (
                          <div className="rounded-lg bg-emerald-500/10 border border-emerald-500/30 px-3 py-4 text-center">
                            <p className="text-[11px] text-emerald-300">✓ All sales register invoices are reported in GSTR-1</p>
                          </div>
                        )}
                      </div>
                    )}

                    {salesReconTab === "missing_sales" && (
                      <div>
                        {!salesRecon ? (
                          <div className="rounded-lg bg-slate-800/50 border border-slate-700 px-3 py-4 text-center">
                            <p className="text-[11px] text-slate-400">No reconciliation data available.</p>
                            <p className="text-[10px] text-slate-500 mt-1">Upload a sales register and GSTR-1 to see invoice matching results.</p>
                          </div>
                        ) : salesRecon.missing_in_sales_register && salesRecon.missing_in_sales_register.length > 0 ? (
                          <>
                            <p className="text-[11px] text-slate-300 mb-3">
                              <span className="font-semibold text-amber-300">{salesRecon.missing_in_sales_register.length}</span> invoices found in GSTR-1 but not in sales register.
                            </p>
                            <div className="overflow-hidden rounded-xl border border-slate-800 bg-slate-950/60">
                              <table className="min-w-full divide-y divide-slate-800 text-[10px]">
                                <thead className="bg-slate-900">
                                  <tr>
                                    <th className="px-3 py-2 text-left font-semibold text-slate-400">Invoice #</th>
                                    <th className="px-3 py-2 text-left font-semibold text-slate-400">Date</th>
                                    <th className="px-3 py-2 text-left font-semibold text-slate-400">Customer</th>
                                    <th className="px-3 py-2 text-right font-semibold text-slate-400">Taxable Value</th>
                                    <th className="px-3 py-2 text-right font-semibold text-slate-400">Total Value</th>
                                  </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-800">
                                  {salesRecon.missing_in_sales_register.slice(0, 5).map((inv, idx) => (
                                    <tr key={idx} className="bg-amber-950/20">
                                      <td className="px-3 py-2 font-mono text-slate-200">{inv.invoice_number || "—"}</td>
                                      <td className="px-3 py-2 text-slate-300">{inv.invoice_date || "—"}</td>
                                      <td className="px-3 py-2 text-slate-300">
                                        <div>{inv.customer_name || "—"}</div>
                                        {inv.customer_gstin && (
                                          <div className="text-[9px] text-slate-500 font-mono">{inv.customer_gstin}</div>
                                        )}
                                      </td>
                                      <td className="px-3 py-2 text-right font-mono text-slate-200">
                                        {((inv.taxable_value || 0)).toLocaleString()}
                                      </td>
                                      <td className="px-3 py-2 text-right font-mono font-semibold text-amber-300">
                                        {((inv.total_value || 0)).toLocaleString()}
                                      </td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                            {salesRecon.missing_in_sales_register.length > 5 && (
                              <p className="mt-2 text-[10px] text-slate-500">
                                Showing first 5 of {salesRecon.missing_in_sales_register.length} invoices. Add missing invoices to your sales register.
                              </p>
                            )}
                            <button
                              onClick={() => downloadReconciliationExport("missing-invoices-sales")}
                              className="mt-3 w-full rounded-lg bg-amber-500/20 hover:bg-amber-500/30 border border-amber-500/40 px-3 py-2 text-[10px] font-medium text-amber-300 transition"
                            >
                              📥 Export Missing in Sales Register → CSV
                            </button>
                          </>
                        ) : (
                          <div className="rounded-lg bg-emerald-500/10 border border-emerald-500/30 px-3 py-4 text-center">
                            <p className="text-[11px] text-emerald-300">✓ All GSTR-1 invoices are present in sales register</p>
                          </div>
                        )}
                      </div>
                    )}

                    {salesReconTab === "mismatches" && (
                      <div>
                        {!salesRecon ? (
                          <div className="rounded-lg bg-slate-800/50 border border-slate-700 px-3 py-4 text-center">
                            <p className="text-[11px] text-slate-400">No reconciliation data available.</p>
                            <p className="text-[10px] text-slate-500 mt-1">Upload a sales register and GSTR-1 to see invoice matching results.</p>
                          </div>
                        ) : salesRecon.value_mismatches && salesRecon.value_mismatches.length > 0 ? (
                          <>
                            <p className="text-[11px] text-slate-300 mb-3">
                              <span className="font-semibold text-blue-300">{salesRecon.value_mismatches.length}</span> invoices have value differences between sales register and GSTR-1.
                            </p>
                            <div className="overflow-hidden rounded-xl border border-slate-800 bg-slate-950/60">
                              <table className="min-w-full divide-y divide-slate-800 text-[10px]">
                                <thead className="bg-slate-900">
                                  <tr>
                                    <th className="px-3 py-2 text-left font-semibold text-slate-400">Invoice #</th>
                                    <th className="px-3 py-2 text-left font-semibold text-slate-400">Date</th>
                                    <th className="px-3 py-2 text-right font-semibold text-slate-400">Sales Reg. Value</th>
                                    <th className="px-3 py-2 text-right font-semibold text-slate-400">GSTR-1 Value</th>
                                    <th className="px-3 py-2 text-right font-semibold text-slate-400">Difference</th>
                                  </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-800">
                                  {salesRecon.value_mismatches.slice(0, 5).map((inv, idx) => (
                                    <tr key={idx} className="bg-blue-950/20">
                                      <td className="px-3 py-2 font-mono text-slate-200">{inv.invoice_number || "—"}</td>
                                      <td className="px-3 py-2 text-slate-300">{inv.invoice_date || "—"}</td>
                                      <td className="px-3 py-2 text-right font-mono text-slate-200">
                                        {((inv.sales_register_value || 0)).toLocaleString()}
                                      </td>
                                      <td className="px-3 py-2 text-right font-mono text-slate-200">
                                        {((inv.gstr1_value || 0)).toLocaleString()}
                                      </td>
                                      <td className="px-3 py-2 text-right font-mono font-semibold text-blue-300">
                                        {((inv.difference || 0)).toLocaleString()}
                                      </td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                            {salesRecon.value_mismatches.length > 5 && (
                              <p className="mt-2 text-[10px] text-slate-500">
                                Showing first 5 of {salesRecon.value_mismatches.length} mismatches. Review and correct values.
                              </p>
                            )}
                            <button
                              onClick={() => downloadReconciliationExport("value-mismatches")}
                              className="mt-3 w-full rounded-lg bg-blue-500/20 hover:bg-blue-500/30 border border-blue-500/40 px-3 py-2 text-[10px] font-medium text-blue-300 transition"
                            >
                              📥 Export Value Mismatches → CSV
                            </button>
                          </>
                        ) : (
                          <div className="rounded-lg bg-emerald-500/10 border border-emerald-500/30 px-3 py-4 text-center">
                            <p className="text-[11px] text-emerald-300">✓ No value mismatches found</p>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Summary totals */}
                    {salesRecon?.totals && (
                      <div className="mt-4 pt-4 border-t border-slate-800">
                        <div className="grid grid-cols-2 gap-4 text-[11px]">
                          <div>
                            <p className="text-slate-400 mb-1">Sales Register Total</p>
                            <p className="font-mono font-semibold text-slate-100">
                              ₹{((salesRecon.totals.sales_register?.total || 0)).toLocaleString()}
                            </p>
                          </div>
                          <div>
                            <p className="text-slate-400 mb-1">GSTR-1 Total</p>
                            <p className="font-mono font-semibold text-slate-100">
                              ₹{((salesRecon.totals.gstr1?.total || 0)).toLocaleString()}
                            </p>
                          </div>
                        </div>
                        {salesRecon.difference && (
                          <div className="mt-3 pt-3 border-t border-slate-800">
                            <p className="text-[10px] text-slate-400 mb-1">Net Difference</p>
                            <p className={`font-mono font-semibold ${
                              Math.abs(salesRecon.difference.total || 0) > 1 
                                ? "text-rose-300" 
                                : "text-emerald-300"
                            }`}>
                              ₹{((salesRecon.difference.total || 0)).toLocaleString()}
                            </p>
                          </div>
                        )}
                      </div>
                    )}

                    {salesRecon?.warnings && salesRecon.warnings.length > 0 && (
                      <div className="mt-4 rounded-lg bg-amber-500/10 border border-amber-500/30 px-3 py-2 text-[11px] text-amber-300">
                        <div className="font-medium mb-1">⚠️ Warnings:</div>
                        <ul className="list-disc list-inside space-y-0.5">
                          {salesRecon.warnings.map((w, idx) => (
                            <li key={idx}>{w}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </section>
                )}

                {/* STEP 4: Exports tab */}
                {activeTab === "exports" && (
                  <section className="rounded-2xl border border-slate-800 bg-slate-900/90 p-5 shadow-lg shadow-black/40">
                    <h3 className="text-xs font-semibold text-slate-200 mb-4">Download Exports</h3>
                    <div className="grid grid-cols-2 gap-3">
                      <button
                        onClick={() => downloadExport("json")}
                        className="flex flex-col items-center justify-center rounded-xl border border-slate-700 bg-slate-900/80 px-4 py-4 text-center hover:bg-slate-800 transition"
                      >
                        <span className="text-lg mb-1">📄</span>
                        <span className="text-[11px] font-medium text-slate-100">JSON</span>
                        <span className="text-[10px] text-slate-400 mt-1">Raw parsed data</span>
                      </button>
                      
                      {selectedJob.doc_type === "sales_register" && (
                        <>
                          <button
                            onClick={() => downloadExport("sales-csv")}
                            className="flex flex-col items-center justify-center rounded-xl border border-emerald-500/40 bg-emerald-500/10 px-4 py-4 text-center hover:bg-emerald-500/20 transition"
                          >
                            <span className="text-lg mb-1">📊</span>
                            <span className="text-[11px] font-medium text-emerald-200">Sales CSV</span>
                            <span className="text-[10px] text-emerald-300/70 mt-1">Standardized format</span>
                          </button>
                          <button
                            onClick={() => downloadExport("sales-zoho")}
                            className="flex flex-col items-center justify-center rounded-xl border border-indigo-500/40 bg-indigo-500/10 px-4 py-4 text-center hover:bg-indigo-500/20 transition"
                          >
                            <span className="text-lg mb-1">🔗</span>
                            <span className="text-[11px] font-medium text-indigo-200">Zoho JSON</span>
                            <span className="text-[10px] text-indigo-300/70 mt-1">Zoho Books ready</span>
                          </button>
                        </>
                      )}
                      
                      {selectedJob.doc_type === "purchase_register" && (
                        <button
                          onClick={() => downloadExport("purchase-csv")}
                          className="flex flex-col items-center justify-center rounded-xl border border-emerald-500/40 bg-emerald-500/10 px-4 py-4 text-center hover:bg-emerald-500/20 transition"
                        >
                          <span className="text-lg mb-1">📊</span>
                          <span className="text-[11px] font-medium text-emerald-200">Purchase CSV</span>
                          <span className="text-[10px] text-emerald-300/70 mt-1">Standardized format</span>
                        </button>
                      )}
                      
                      {(selectedJob.doc_type === "gst_invoice" || selectedJob.doc_type === "invoice") && (
                        <button
                          onClick={() => downloadExport("tally-xml")}
                          className="flex flex-col items-center justify-center rounded-xl border border-orange-500/40 bg-orange-500/10 px-4 py-4 text-center hover:bg-orange-500/20 transition"
                        >
                          <span className="text-lg mb-1">📋</span>
                          <span className="text-[11px] font-medium text-orange-200">Tally XML</span>
                          <span className="text-[10px] text-orange-300/70 mt-1">Import to Tally</span>
                        </button>
                      )}
                    </div>
                    
                    {/* STEP 6: Export hints */}
                    <div className="mt-4 rounded-lg bg-blue-500/10 border border-blue-500/30 px-3 py-2 text-[11px] text-blue-300">
                      <p className="font-medium mb-1">💡 Export Tips:</p>
                      <ul className="list-disc list-inside space-y-0.5 text-[10px]">
                        <li>JSON contains the full parsed structure</li>
                        <li>CSV files are formatted for easy import into Excel</li>
                        <li>Tally XML can be directly imported into Tally Prime</li>
                      </ul>
                    </div>
                  </section>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <footer className="mt-4 border-t border-slate-800/70 pt-3">
          <p className="text-[10px] text-slate-500">
            © 2025 DocParser. Internal beta – not for production filings without review.
          </p>
        </footer>
      </main>
    </div>
  );
}

