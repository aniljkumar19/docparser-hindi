// Bulk upload interface for CA firms
import { useState } from "react";

type Batch = {
  batch_id: string;
  batch_name?: string;
  client_id?: string;
  status: string;
  progress: {
    total: number;
    completed: number;
    failed: number;
    processing: number;
  };
  jobs: Array<{
    job_id: string;
    filename: string;
    status: string;
    doc_type?: string;
    result?: any;
  }>;
};

function normalizeBatch(raw: any): Batch {
  const jobs = Array.isArray(raw?.jobs) ? raw.jobs : [];
  const totalFiles = raw?.progress?.total ?? raw?.total_files ?? jobs.length ?? 0;
  const completed = raw?.progress?.completed ?? jobs.filter((j: any) => j.status === "succeeded").length ?? 0;
  const failed = raw?.progress?.failed ?? jobs.filter((j: any) => j.status === "failed").length ?? 0;
  const processing = raw?.progress?.processing ?? jobs.filter((j: any) => !["succeeded", "failed"].includes(j.status)).length ?? 0;

  return {
    batch_id: raw?.batch_id ?? "",
    batch_name: raw?.batch_name ?? raw?.name ?? undefined,
    client_id: raw?.client_id ?? undefined,
    status: raw?.status ?? "queued",
    progress: {
      total: totalFiles,
      completed,
      failed,
      processing,
    },
    jobs,
  };
}

export default function BulkUpload() {
  const [files, setFiles] = useState<FileList | null>(null);
  const [clientId, setClientId] = useState("");
  const [batchName, setBatchName] = useState("");
  const [docType, setDocType] = useState("");
  const [batch, setBatch] = useState<Batch | null>(null);
  const [polling, setPolling] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function uploadBulkFiles() {
    if (!files || files.length === 0) return;
    
    setError(null);
    const formData = new FormData();
    
    // Add all files
    Array.from(files).forEach(file => {
      formData.append("files", file);
    });
    
    // Add metadata
    if (clientId) formData.append("client_id", clientId);
    if (batchName) formData.append("batch_name", batchName);
    if (docType) formData.append("doc_type", docType);

    try {
      const apiBase = process.env.NEXT_PUBLIC_DOCPARSER_API_BASE || "http://localhost:8000";
      const response = await fetch(`${apiBase}/v1/bulk-parse`, {
        method: "POST",
        headers: { "Authorization": `Bearer ${process.env.NEXT_PUBLIC_DOCPARSER_API_KEY || "dev_123"}` },
        body: formData
      });

      if (!response.ok) {
        throw new Error(`Upload failed: ${response.statusText}`);
      }

      const result = await response.json();
      setBatch(normalizeBatch(result));
      
      // Start polling for updates
      if (result.batch_id) {
        pollBatchStatus(result.batch_id);
      }
    } catch (err: any) {
      setError(err.message);
    }
  }

  async function pollBatchStatus(batchId: string) {
    setPolling(true);
    try {
      let tries = 0;
      while (tries++ < 60) { // Poll for up to 1 minute
        const apiBase = process.env.NEXT_PUBLIC_DOCPARSER_API_BASE || "http://localhost:8000";
        const response = await fetch(`${apiBase}/v1/batches/${batchId}`, {
          headers: { "x-api-key": process.env.NEXT_PUBLIC_DOCPARSER_API_KEY || "dev_123" }
        });
        
        if (!response.ok) break;
        
        const batchDataRaw = await response.json();
        setBatch(normalizeBatch(batchDataRaw));
        
        if (batchDataRaw.status === "completed" || batchDataRaw.status === "failed") {
          break;
        }
        
        await new Promise(res => setTimeout(res, 2000)); // Poll every 2 seconds
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setPolling(false);
    }
  }

  async function exportResults(format: string) {
    if (!batch) return;
    
    try {
      const apiBase = process.env.NEXT_PUBLIC_DOCPARSER_API_BASE || "http://localhost:8000";
      const response = await fetch(`${apiBase}/v1/batches/${batch.batch_id}/export?format=${format}`, {
        headers: { "x-api-key": process.env.NEXT_PUBLIC_DOCPARSER_API_KEY || "dev_123" }
      });
      
      if (!response.ok) {
        throw new Error(`Export failed: ${response.statusText}`);
      }
      
      const data = await response.json();
      
      // Download the file
      const blob = new Blob([data.csv_data || JSON.stringify(data, null, 2)], {
        type: format === "csv" ? "text/csv" : "application/json"
      });
      
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `batch_${batch.batch_id}_export.${format === "csv" ? "csv" : "json"}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err: any) {
      setError(err.message);
    }
  }

  const progressStats = batch?.progress;
  const completionPercent = progressStats && progressStats.total > 0
    ? Math.min(100, Math.max(0, (progressStats.completed / progressStats.total) * 100))
    : 0;

  return (
    <main className="max-w-6xl mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Bulk Document Processing</h1>
        <a 
          href="/"
          className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 text-sm font-medium"
        >
          ← Single Upload
        </a>
      </div>
      
      {/* Upload Section */}
      <div className="bg-white rounded-lg border p-6 space-y-4">
        <h2 className="text-xl font-semibold">Upload Documents</h2>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-2">Select Files (Max 100)</label>
            <input
              type="file"
              multiple
              onChange={(e) => setFiles(e.target.files)}
              className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
            />
            {files && (
              <p className="text-sm text-gray-600 mt-2">
                {files.length} files selected
              </p>
            )}
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-2">Client ID (Optional)</label>
              <input
                type="text"
                value={clientId}
                onChange={(e) => setClientId(e.target.value)}
                placeholder="client_123"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-2">Batch Name (Optional)</label>
              <input
                type="text"
                value={batchName}
                onChange={(e) => setBatchName(e.target.value)}
                placeholder="January 2024 Invoices"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Doc Type Override</label>
              <select
                value={docType}
                onChange={(e) => setDocType(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Auto-detect</option>
                <option value="bank_statement">Bank statement</option>
                <option value="gstr">GST return</option>
                <option value="gstr1">GSTR-1</option>
                <option value="gstr3b">GSTR-3B</option>
                <option value="gst_invoice">GST invoice</option>
                <option value="utility_bill">Utility bill</option>
              </select>
            </div>
          </div>
          
          <button
            onClick={uploadBulkFiles}
            disabled={!files || files.length === 0}
            className="px-6 py-3 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Upload & Process {files ? `(${files.length} files)` : ""}
          </button>
        </div>
      </div>

      {/* Batch Status */}
      {batch && (
        <div className="bg-white rounded-lg border p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold">Batch Status</h2>
            <div className="flex gap-2">
              <button
                onClick={() => exportResults("json")}
                className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700"
              >
                Export JSON
              </button>
              <button
                onClick={() => exportResults("csv")}
                className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700"
              >
                Export CSV
              </button>
              <button
                onClick={() => exportResults("tally_csv")}
                className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700"
              >
                Export Tally CSV
              </button>
            </div>
          </div>
          
          <div className="grid grid-cols-4 gap-4">
            <div className="text-center p-4 bg-blue-50 rounded-lg">
              <div className="text-2xl font-bold text-blue-600">{progressStats?.total ?? 0}</div>
              <div className="text-sm text-gray-600">Total Files</div>
            </div>
            <div className="text-center p-4 bg-green-50 rounded-lg">
              <div className="text-2xl font-bold text-green-600">{progressStats?.completed ?? 0}</div>
              <div className="text-sm text-gray-600">Completed</div>
            </div>
            <div className="text-center p-4 bg-yellow-50 rounded-lg">
              <div className="text-2xl font-bold text-yellow-600">{progressStats?.processing ?? 0}</div>
              <div className="text-sm text-gray-600">Processing</div>
            </div>
            <div className="text-center p-4 bg-red-50 rounded-lg">
              <div className="text-2xl font-bold text-red-600">{progressStats?.failed ?? 0}</div>
              <div className="text-sm text-gray-600">Failed</div>
            </div>
          </div>
          
          {/* Progress Bar */}
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all duration-300"
              style={{
                width: `${completionPercent}%`
              }}
            />
          </div>
          
          {/* Job List */}
          <div className="space-y-2">
            <h3 className="font-semibold">Individual Files</h3>
            <div className="max-h-60 overflow-y-auto space-y-1">
              {batch.jobs.map((job) => (
                <div
                  key={job.job_id}
                  className="flex items-center justify-between p-3 bg-gray-50 rounded-md"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-mono">{job.filename}</span>
                    {job.doc_type && (
                      <span className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded">
                        {job.doc_type}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <span
                      className={`px-2 py-1 text-xs rounded ${
                        job.status === "succeeded"
                          ? "bg-green-100 text-green-800"
                          : job.status === "failed"
                          ? "bg-red-100 text-red-800"
                          : "bg-yellow-100 text-yellow-800"
                      }`}
                    >
                      {job.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <p className="text-red-600">{error}</p>
        </div>
      )}

      {polling && (
        <div className="text-center text-gray-600">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600 mx-auto mb-2"></div>
          Processing documents...
        </div>
      )}
    </main>
  );
}

