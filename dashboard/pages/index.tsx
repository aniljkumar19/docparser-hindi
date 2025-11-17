// ...existing imports
import { useState } from "react";

type Job = {
  job_id: string;
  status: string;
  doc_type?: string | null;
  result?: any;
  meta?: {
    detected_doc_type?: string | null;
    doc_type_scores?: Record<string, number> | null;
    doc_type_confidence?: number | null;
    [k: string]: any;
  } | null;
};

function DocTypeBadge({ type, conf }: { type?: string | null; conf?: number | null }) {
  const t = (type || "unknown") as string;
  const c = conf ?? 0;
  const color =
    t === "invoice" ? "bg-violet-100 text-violet-800" :
    t === "receipt" ? "bg-teal-100 text-teal-800" :
    t === "utility_bill" ? "bg-amber-100 text-amber-800" :
    "bg-gray-100 text-gray-700";
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-sm font-medium ${color}`}>
      <span className="capitalize">{t.replace("_", " ")}</span>
      <span className="opacity-70">({c})</span>
    </span>
  );
}

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
};

function StatusPill({ status }: { status: string }) {
  const color =
    status === "matched"
      ? "bg-emerald-100 text-emerald-700"
      : status === "itc_underclaimed"
      ? "bg-amber-100 text-amber-800"
      : status === "itc_overclaimed"
      ? "bg-rose-100 text-rose-800"
      : "bg-gray-100 text-gray-700";
  return (
    <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${color}`}>
      {status.replace(/_/g, " ")}
    </span>
  );
}

function PurchaseVsGstr3bCard({ data }: { data: PurchaseVsGstr3bRecon }) {
  const totals = data.totals ?? {
    purchase_register: data.itc_from_purchase_register,
    gstr3b: data.itc_from_gstr3b,
  };
  const pr = totals?.purchase_register ?? {};
  const g3b = totals?.gstr3b ?? {};
  const diff = data.difference ?? {};
  const contributions = data.invoice_contributions ?? [];

  return (
    <div className="border rounded-xl p-4 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-base font-semibold">Purchase Register vs GSTR-3B ITC</h3>
          <p className="text-sm text-gray-500">Compare input tax credit totals</p>
        </div>
        <StatusPill status={data.status ?? "unknown"} />
      </div>

      <div className="overflow-x-auto text-sm">
        <table className="min-w-[320px] w-full text-left">
          <thead className="text-gray-500">
            <tr>
              <th className="py-1 pr-4">Source</th>
              <th className="py-1 pr-4">IGST</th>
              <th className="py-1 pr-4">CGST</th>
              <th className="py-1 pr-4">SGST</th>
              <th className="py-1 pr-4">Total</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="py-1 pr-4 text-gray-600">Purchase Register</td>
              <td className="py-1 pr-4">{(pr.igst ?? 0).toLocaleString()}</td>
              <td className="py-1 pr-4">{(pr.cgst ?? 0).toLocaleString()}</td>
              <td className="py-1 pr-4">{(pr.sgst ?? 0).toLocaleString()}</td>
              <td className="py-1 pr-4">{(pr.total ?? 0).toLocaleString()}</td>
            </tr>
            <tr>
              <td className="py-1 pr-4 text-gray-600">GSTR-3B</td>
              <td className="py-1 pr-4">{(g3b.igst ?? 0).toLocaleString()}</td>
              <td className="py-1 pr-4">{(g3b.cgst ?? 0).toLocaleString()}</td>
              <td className="py-1 pr-4">{(g3b.sgst ?? 0).toLocaleString()}</td>
              <td className="py-1 pr-4">{(g3b.total ?? 0).toLocaleString()}</td>
            </tr>
            <tr className="border-t">
              <td className="py-1 pr-4 font-medium">Difference</td>
              <td className="py-1 pr-4">{(diff.igst ?? 0).toLocaleString()}</td>
              <td className="py-1 pr-4">{(diff.cgst ?? 0).toLocaleString()}</td>
              <td className="py-1 pr-4">{(diff.sgst ?? 0).toLocaleString()}</td>
              <td className="py-1 pr-4">{(diff.total ?? 0).toLocaleString()}</td>
            </tr>
          </tbody>
        </table>
      </div>

      {contributions.length > 0 && (
        <div className="space-y-2">
          <div className="text-sm font-medium text-gray-600">Invoices contributing ITC</div>
          <div className="overflow-x-auto text-xs">
            <table className="min-w-[360px] text-left">
              <thead className="text-gray-500">
                <tr>
                  <th className="py-1 pr-3">Invoice</th>
                  <th className="py-1 pr-3">Supplier</th>
                  <th className="py-1 pr-3">IGST</th>
                  <th className="py-1 pr-3">CGST</th>
                  <th className="py-1 pr-3">SGST</th>
                </tr>
              </thead>
              <tbody>
                {contributions.slice(0, 5).map((entry, idx) => (
                  <tr key={`${entry.invoice_number || idx}-${idx}`}>
                    <td className="py-1 pr-3">
                      <div className="font-medium">{entry.invoice_number || "—"}</div>
                      <div className="text-[11px] text-gray-500">{entry.invoice_date}</div>
                    </td>
                    <td className="py-1 pr-3">
                      <div>{entry.supplier_name || "—"}</div>
                      <div className="text-[11px] text-gray-500">{entry.supplier_gstin}</div>
                    </td>
                    <td className="py-1 pr-3">{(entry.igst ?? 0).toLocaleString()}</td>
                    <td className="py-1 pr-3">{(entry.cgst ?? 0).toLocaleString()}</td>
                    <td className="py-1 pr-3">{(entry.sgst ?? 0).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {data.warnings && data.warnings.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs text-amber-900 space-y-1">
          <div className="font-medium">Warnings</div>
          <ul className="list-disc list-inside space-y-0.5">
            {data.warnings.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [polling, setPolling] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [docType, setDocType] = useState("");

  async function uploadAndParse() {
    setError(null);
    if (!file) return;
    const fd = new FormData();
    fd.append("file", file);
    if (docType) {
      fd.append("doc_type", docType);
    }
    try {
      // Call API directly (bypass Next.js proxy for POST with FormData)
      const apiBase = process.env.NEXT_PUBLIC_DOCPARSER_API_BASE || "http://localhost:8000";
      const r = await fetch(`${apiBase}/v1/parse`, {
        method: "POST",
        headers: { 
          "Authorization": `Bearer ${process.env.NEXT_PUBLIC_DOCPARSER_API_KEY || "dev_123"}`
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
      setJob(j);
      // start polling for full result
      pollJob(j.job_id);
    } catch (e: any) {
      setError(e?.message || "Failed to upload file");
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
          const apiBase = process.env.NEXT_PUBLIC_DOCPARSER_API_BASE || "http://localhost:8000";
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
        setJob(j);
        if (j.status === "succeeded" || j.status === "failed" || j.status === "needs_review") break;
        await new Promise(res => setTimeout(res, 1000));
      }
    } catch (e:any) {
      setError(e?.message || "Failed to fetch job");
    } finally {
      setPolling(false);
    }
  }

  const detected = job?.meta?.detected_doc_type ?? job?.doc_type ?? null;
  const conf = job?.meta?.doc_type_confidence ?? null;
  const scores = job?.meta?.doc_type_scores ?? null;

  async function downloadExport(kind: "json" | "sales-csv" | "purchase-csv" | "sales-zoho") {
    if (!job) return;
    const apiBase = process.env.NEXT_PUBLIC_DOCPARSER_API_BASE || "http://localhost:8000";
    let path = "";
    if (kind === "json") path = `/v1/export/json/${job.job_id}`;
    if (kind === "sales-csv") path = `/v1/export/sales-csv/${job.job_id}`;
    if (kind === "purchase-csv") path = `/v1/export/purchase-csv/${job.job_id}`;
    if (kind === "sales-zoho") path = `/v1/export/sales-zoho/${job.job_id}`;
    try {
      const r = await fetch(`${apiBase}${path}`, {
        headers: {
          "Authorization": `Bearer ${process.env.NEXT_PUBLIC_DOCPARSER_API_KEY || "dev_123"}`
        },
      });
      if (!r.ok) {
        console.error("Export failed", r.status, await r.text());
        return;
      }
      const data = await r.json();
      const filename = data.filename || `${job.job_id}.txt`;
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

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      {/* Top nav */}
      <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-500/20 text-blue-400 ring-1 ring-inset ring-blue-500/40">
              <span className="text-xs font-semibold">DP</span>
            </div>
            <div>
              <div className="text-sm font-semibold tracking-tight">DocParser</div>
              <div className="text-xs text-slate-400">AI document parsing for CAs &amp; SMEs</div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <a
              href="/bulk-upload"
              className="rounded-md border border-slate-700 px-3 py-1.5 text-xs font-medium text-slate-100 hover:border-slate-500 hover:bg-slate-900"
            >
              Bulk upload workspace
            </a>
          </div>
        </div>
      </header>

      <main className="mx-auto flex max-w-5xl flex-col gap-8 px-6 py-10 md:flex-row">
        {/* Left column – hero & marketing */}
        <section className="flex-1 space-y-6">
          <div>
            <h1 className="text-balance text-3xl font-semibold tracking-tight text-slate-50 md:text-4xl">
              Turn messy GST &amp; finance PDFs into clean, exportable data.
            </h1>
            <p className="mt-3 max-w-xl text-sm leading-relaxed text-slate-300">
              Upload your bank statements, invoices and GST returns and get ready‑to‑use JSON, CSV, Tally XML and
              reconciliation reports in a few clicks – purpose‑built for Indian CAs and finance teams.
            </p>
          </div>

          {/* Product overview / marketing copy */}
          <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 space-y-3 shadow-sm shadow-slate-950/40">
            <h2 className="text-sm font-semibold text-slate-100">What DocParser can handle</h2>
            <p className="text-xs text-slate-300">
              Built for high‑volume compliance workloads – not generic OCR demos.
            </p>
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <h3 className="text-xs font-semibold text-slate-200">Understands your documents</h3>
                <ul className="mt-1 list-disc list-inside text-xs text-slate-300 space-y-0.5">
                  <li>Bank statements</li>
                  <li>GST invoices</li>
                  <li>GSTR-1 &amp; GSTR-3B returns</li>
                  <li>Purchase &amp; sales registers (PDF / CSV)</li>
                </ul>
              </div>
              <div>
                <h3 className="text-xs font-semibold text-slate-200">Exports &amp; reconciliations</h3>
                <ul className="mt-1 list-disc list-inside text-xs text-slate-300 space-y-0.5">
                  <li>Tally XML for sales &amp; purchase vouchers</li>
                  <li>Standardized CSV for registers</li>
                  <li>Zoho Books-ready JSON (sales invoices)</li>
                  <li>GSTR-3B ITC &amp; GSTR-1 / Sales reconciliation</li>
                </ul>
              </div>
            </div>
            <div className="grid gap-4 pt-3 border-t border-slate-800 md:grid-cols-2">
              <div>
                <h3 className="text-xs font-semibold text-slate-200">Why firms use DocParser</h3>
                <ul className="mt-1 list-disc list-inside text-xs text-slate-300 space-y-0.5">
                  <li>Save 5–15 hours per client every month</li>
                  <li>Eliminate manual data entry &amp; reduce errors</li>
                  <li>Works with any ERP (Tally, Zoho, custom)</li>
                </ul>
              </div>
              <div className="flex items-center">
                <p className="text-xs text-slate-300">
                  Start by uploading a file on the right, then download JSON / CSV / XML or push data into your
                  accounting tools.
                </p>
              </div>
            </div>
          </section>
        </section>

        {/* Right column – upload & results */}
        <section className="flex-1">
          <div className="relative overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/60 p-4 shadow-lg shadow-slate-950/40 backdrop-blur">
            <div className="pointer-events-none absolute inset-x-0 top-0 h-40 bg-gradient-to-b from-blue-500/15 via-slate-900/0 to-transparent" />
            <div className="relative space-y-4">
              <div>
                <h2 className="text-sm font-semibold text-slate-100">Try it with a file</h2>
                <p className="text-xs text-slate-400">
                  Choose a document and optionally specify its type. We&apos;ll auto‑detect and parse if you leave it on
                  auto.
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-3">
                <input
                  type="file"
                  onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                  className="block text-xs text-slate-200 file:mr-3 file:rounded-md file:border-0 file:bg-blue-600 file:px-3 file:py-1.5 file:text-xs file:font-medium file:text-white hover:file:bg-blue-500"
                />
                <select
                  value={docType}
                  onChange={(e) => setDocType(e.target.value)}
                  className="text-xs rounded-md border border-slate-700 bg-slate-900 px-2 py-1 text-slate-100"
                >
                  <option value="">Auto-detect</option>
                  <option value="bank_statement">Bank statement</option>
                  <option value="gstr">GST return</option>
                  <option value="gstr1">GSTR-1</option>
                  <option value="gstr3b">GSTR-3B</option>
                  <option value="purchase_register">Purchase register</option>
                  <option value="sales_register">Sales register</option>
                  <option value="gst_invoice">GST invoice</option>
                  <option value="utility_bill">Utility bill</option>
                </select>
                <button
                  onClick={uploadAndParse}
                  disabled={!file}
                  className="inline-flex items-center rounded-md bg-blue-600 px-3 py-1.5 text-xs font-medium text-white shadow-sm transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  Upload &amp; parse
                </button>
              </div>

              {error && <p className="text-xs text-rose-400">{error}</p>}

              {job && (
                <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-4 space-y-3">
                  <div className="flex items-center justify-between gap-4">
                    <div className="space-y-0.5">
                      <div className="text-[11px] uppercase tracking-wide text-slate-500">Job</div>
                      <div className="truncate font-mono text-xs text-slate-100">{job.job_id}</div>
                    </div>
                    <div className="rounded-full bg-slate-900 px-3 py-1 text-[11px] text-slate-200">
                      <span className="mr-1 text-slate-400">Status:</span>
                      <span className="font-medium">{job.status}</span>
                    </div>
                  </div>

                  {/* Doc type + confidence */}
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-xs text-slate-400">Detected doc type:</span>
                    <DocTypeBadge type={detected} conf={conf ?? undefined} />
                  </div>

                  {/* Export buttons */}
                  <div className="flex flex-wrap items-center gap-2 text-[11px]">
                    <button
                      onClick={() => downloadExport("json")}
                      className="rounded border border-slate-700 px-2 py-1 text-slate-100 hover:border-slate-500 hover:bg-slate-900"
                    >
                      Download JSON
                    </button>
                    {job.doc_type === "sales_register" && (
                      <>
                        <button
                          onClick={() => downloadExport("sales-csv")}
                          className="rounded border border-blue-500/50 px-2 py-1 text-blue-100 hover:border-blue-400 hover:bg-blue-950/40"
                        >
                          Export CSV
                        </button>
                        <button
                          onClick={() => downloadExport("sales-zoho")}
                          className="rounded border border-emerald-500/50 px-2 py-1 text-emerald-100 hover:border-emerald-400 hover:bg-emerald-950/40"
                        >
                          Zoho JSON
                        </button>
                      </>
                    )}
                    {job.doc_type === "purchase_register" && (
                      <button
                        onClick={() => downloadExport("purchase-csv")}
                        className="rounded border border-blue-500/50 px-2 py-1 text-blue-100 hover:border-blue-400 hover:bg-blue-950/40"
                      >
                        Export CSV
                      </button>
                    )}
                  </div>

                  {/* Optional: score breakdown */}
                  {scores && (
                    <div className="overflow-x-auto">
                      <table className="min-w-[320px] text-xs">
                        <thead>
                          <tr className="text-slate-500">
                            <th className="text-left pr-4 py-1">Class</th>
                            <th className="text-left py-1">Score</th>
                          </tr>
                        </thead>
                        <tbody>
                          {Object.entries(scores).map(([k, v]) => (
                            <tr key={k}>
                              <td className="pr-4 py-1 capitalize text-slate-100">{k.replace("_", " ")}</td>
                              <td className="py-1 text-slate-100">{v}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}

                  {/* Reconciliation cards */}
                  {job?.meta?.reconciliations?.purchase_vs_gstr3b_itc && (
                    <PurchaseVsGstr3bCard
                      data={job.meta.reconciliations.purchase_vs_gstr3b_itc as PurchaseVsGstr3bRecon}
                    />
                  )}

                  {/* Render the parsed JSON */}
                  <div className="rounded-lg bg-slate-950/60 p-3">
                    <div className="mb-1 flex items-center justify-between">
                      <span className="text-[11px] font-medium text-slate-400">Parsed output</span>
                      {polling && <span className="text-[11px] text-slate-500">Polling…</span>}
                    </div>
                    <pre className="max-h-64 overflow-auto whitespace-pre-wrap break-all rounded bg-slate-950 p-2 text-[11px] text-slate-100">
                      {JSON.stringify(job.result ?? {}, null, 2)}
                    </pre>
                  </div>
                </div>
              )}

              {!job && (
                <p className="text-[11px] text-slate-500">
                  No job yet. Upload a sample bank statement, GST invoice or register to see the structured output here.
                </p>
              )}
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
