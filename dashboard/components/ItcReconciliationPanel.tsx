import React, { useEffect, useState } from "react";
import { getApiBase } from "../utils/api";

type HeadStatus = "match" | "over_claimed" | "under_claimed";

type ItcHeadResult = {
  available_2b: number;
  claimed_3b: number;
  difference: number;
  status: HeadStatus;
};

type ItcReconciliationResult = {
  gstin: string | null;
  period: string | null;
  itc_available_2b: Record<"igst" | "cgst" | "sgst" | "cess", number>;
  itc_claimed_3b: Record<"igst" | "cgst" | "sgst" | "cess", number>;
  by_head: Record<"igst" | "cgst" | "sgst" | "cess", ItcHeadResult>;
  overall: {
    total_available_2b: number;
    total_claimed_3b: number;
    difference: number;
    status: HeadStatus;
  };
  issues: {
    code: string;
    level: "warning" | "error";
    message: string;
  }[];
};

type ItcReconciliationResponse = {
  job2b_id: string;
  job3b_id: string;
  result: ItcReconciliationResult;
};

interface ItcReconciliationPanelProps {
  job2bId: string | null;
  job3bId: string | null;
}

export const ItcReconciliationPanel: React.FC<ItcReconciliationPanelProps> = ({
  job2bId,
  job3bId,
}) => {
  const [data, setData] = useState<ItcReconciliationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Helper to get API key from localStorage
  const getApiKey = (): string => {
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem("docparser_api_key");
      if (stored) return stored;
    }
    return process.env.NEXT_PUBLIC_DOCPARSER_API_KEY || "dev_123";
  };

  useEffect(() => {
    if (!job2bId || !job3bId) return;

    const fetchRec = async () => {
      try {
        setLoading(true);
        setError(null);
        
        const apiBase = getApiBase();
        const apiKey = getApiKey();
        const headers: HeadersInit = {
          "Content-Type": "application/json",
          "x-api-key": apiKey,
        };
        
        const res = await fetch(
          `${apiBase}/v1/reconcile/itc/2b-3b?job2b_id=${encodeURIComponent(
            job2bId
          )}&job3b_id=${encodeURIComponent(job3bId)}`,
          { headers }
        );
        
        if (!res.ok) {
          const errorText = await res.text();
          throw new Error(`HTTP ${res.status}: ${errorText}`);
        }
        
        const json = (await res.json()) as ItcReconciliationResponse;
        setData(json.result);
      } catch (err: any) {
        console.error("ITC reconciliation error", err);
        setError(err.message || "Failed to load reconciliation");
      } finally {
        setLoading(false);
      }
    };

    fetchRec();
  }, [job2bId, job3bId]);

  if (!job2bId || !job3bId) {
    return (
      <div className="text-sm text-gray-500">
        Select both a GSTR-2B job and a GSTR-3B job to reconcile ITC.
      </div>
    );
  }

  if (loading) {
    return <div className="text-sm text-gray-500">Reconciling ITC…</div>;
  }

  if (error) {
    return (
      <div className="text-sm text-red-600">
        Reconciliation failed: {error}
      </div>
    );
  }

  if (!data) {
    return null;
  }

  const { gstin, period, overall, by_head, issues } = data;

  const statusBadge = (status: HeadStatus) => {
    if (status === "match") {
      return (
        <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">
          Match
        </span>
      );
    }
    if (status === "over_claimed") {
      return (
        <span className="rounded-full bg-yellow-100 px-2 py-0.5 text-xs font-medium text-yellow-800">
          Over-claimed
        </span>
      );
    }
    return (
      <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">
        Under-claimed
      </span>
    );
  };

  const formatMoney = (n: number) =>
    `₹${n.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

  const heads: ("igst" | "cgst" | "sgst" | "cess")[] = [
    "igst",
    "cgst",
    "sgst",
    "cess",
  ];

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-1">
        <div className="text-sm text-gray-500">
          GSTIN: <span className="font-mono">{gstin || "N/A"}</span>
        </div>
        <div className="text-sm text-gray-500">
          Period: <span className="font-mono">{period || "N/A"}</span>
        </div>
      </div>

      <div className="rounded-md border border-gray-200 bg-gray-50 px-3 py-2 text-sm">
        <div className="flex items-center justify-between">
          <div className="font-medium">Overall ITC status</div>
          {statusBadge(overall.status)}
        </div>
        <div className="mt-1 grid grid-cols-3 gap-4 text-xs text-gray-700">
          <div>
            <div className="text-gray-500">Available (2B)</div>
            <div className="font-mono">
              {formatMoney(overall.total_available_2b)}
            </div>
          </div>
          <div>
            <div className="text-gray-500">Claimed (3B)</div>
            <div className="font-mono">
              {formatMoney(overall.total_claimed_3b)}
            </div>
          </div>
          <div>
            <div className="text-gray-500">Difference</div>
            <div className="font-mono">
              {formatMoney(overall.difference)}
            </div>
          </div>
        </div>
      </div>

      <div>
        <div className="mb-2 text-sm font-medium">
          By tax head (2B vs 3B)
        </div>
        <div className="overflow-hidden rounded-md border border-gray-200">
          <table className="min-w-full text-left text-xs">
            <thead className="bg-gray-50 text-gray-600">
              <tr>
                <th className="px-3 py-2">Head</th>
                <th className="px-3 py-2">Available (2B)</th>
                <th className="px-3 py-2">Claimed (3B)</th>
                <th className="px-3 py-2">Difference</th>
                <th className="px-3 py-2">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {heads.map((h) => {
                const row = by_head[h];
                if (!row) return null;
                return (
                  <tr key={h}>
                    <td className="px-3 py-2 font-mono uppercase">{h}</td>
                    <td className="px-3 py-2 font-mono">
                      {formatMoney(row.available_2b)}
                    </td>
                    <td className="px-3 py-2 font-mono">
                      {formatMoney(row.claimed_3b)}
                    </td>
                    <td className="px-3 py-2 font-mono">
                      {formatMoney(row.difference)}
                    </td>
                    <td className="px-3 py-2">
                      {statusBadge(row.status)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {issues.length > 0 && (
        <div>
          <div className="mb-1 text-sm font-medium">Issues</div>
          <ul className="space-y-1 text-xs text-gray-700">
            {issues.map((iss, idx) => (
              <li key={`${iss.code}-${idx}`}>
                {iss.level === "error" ? "❌" : "⚠️"} [{iss.level}]{" "}
                {iss.message}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

