import React, { useEffect, useState } from "react";
import { getApiBase } from "../utils/api";

type DocType = "sales_register" | "gstr2b" | "gstr3b";

type ValidationIssue = {
  code: string;
  level: "warning" | "error";
  message: string;
  meta: Record<string, any>;
};

type ValidationResponse = {
  job_id: string;
  doc_type: DocType;
  valid?: boolean;
  issues: ValidationIssue[];
  issue_count?: number;
};

interface ValidationPanelProps {
  docType: DocType;
  jobId: string;
}

export const ValidationPanel: React.FC<ValidationPanelProps> = ({
  docType,
  jobId,
}) => {
  const [data, setData] = useState<ValidationResponse | null>(null);
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
    if (!jobId) return;

    const fetchValidation = async () => {
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
          `${apiBase}/v1/validate/${docType}/${jobId}`,
          { headers }
        );
        
        if (!res.ok) {
          const errorText = await res.text();
          throw new Error(`HTTP ${res.status}: ${errorText}`);
        }
        
        const json = (await res.json()) as ValidationResponse;
        setData(json);
      } catch (err: any) {
        console.error("Validation fetch error", err);
        setError(err.message || "Failed to load validation");
      } finally {
        setLoading(false);
      }
    };

    fetchValidation();
  }, [docType, jobId]);

  if (!jobId) {
    return <div className="text-sm text-gray-500">No job selected.</div>;
  }

  if (loading) {
    return <div className="text-sm text-gray-500">Running validation…</div>;
  }

  if (error) {
    return (
      <div className="text-sm text-red-600">
        Validation failed: {error}
      </div>
    );
  }

  const issues = data?.issues ?? [];
  const hasErrors = issues.some((i) => i.level === "error");
  const hasWarnings = issues.some((i) => i.level === "warning");

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="font-medium">
          Validation ({docType})
        </div>
        <div className="text-xs text-gray-500">
          Job: {jobId}
        </div>
      </div>

      {issues.length === 0 && (
        <div className="rounded-md border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-700">
          ✅ No issues found – validation passed.
        </div>
      )}

      {issues.length > 0 && (
        <div className="rounded-md border border-yellow-200 bg-yellow-50 px-3 py-2 text-sm text-yellow-800">
          {hasErrors && "❌ Errors detected. "}
          {hasWarnings && "⚠️ Warnings detected. "}
          Total issues: {issues.length}
        </div>
      )}

      {issues.length > 0 && (
        <ul className="space-y-2">
          {issues.map((issue, idx) => (
            <li
              key={`${issue.code}-${idx}`}
              className="rounded-md border border-gray-200 bg-white px-3 py-2 text-sm"
            >
              <div className="flex items-center justify-between">
                <span
                  className={
                    issue.level === "error"
                      ? "text-xs font-semibold text-red-600"
                      : "text-xs font-semibold text-yellow-600"
                  }
                >
                  {issue.level.toUpperCase()}
                </span>
                <span className="text-xs font-mono text-gray-500">
                  {issue.code}
                </span>
              </div>
              <div className="mt-1 text-gray-800">{issue.message}</div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

