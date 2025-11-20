import React from "react";
import { getApiBase } from "../utils/api";

interface ExportSalesRegisterButtonProps {
  jobId: string;
  variant?: "canonical" | "legacy";
}

export const ExportSalesRegisterButton: React.FC<ExportSalesRegisterButtonProps> = ({
  jobId,
  variant = "canonical",
}) => {
  // Helper to get API key from localStorage
  const getApiKey = (): string => {
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem("docparser_api_key");
      if (stored) return stored;
    }
    return process.env.NEXT_PUBLIC_DOCPARSER_API_KEY || "dev_123";
  };

  const handleClick = async () => {
    if (!jobId) return;

    try {
      const apiBase = getApiBase();
      const apiKey = getApiKey();
      const headers: HeadersInit = {
        "Content-Type": "application/json",
        "x-api-key": apiKey,
      };

      // Use canonical CSV export endpoint
      const endpoint = variant === "canonical" 
        ? `${apiBase}/v1/export/sales-csv-canonical/${jobId}`
        : `${apiBase}/v1/export/sales-csv/${jobId}`;

      const response = await fetch(endpoint, { headers });
      
      if (!response.ok) {
        throw new Error(`Export failed: ${response.statusText}`);
      }

      const data = await response.json();
      
      // Create download link
      const blob = new Blob([data.content], { type: "text/csv" });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = data.filename || `sales_register_${jobId}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (error: any) {
      console.error("Export error:", error);
      alert(`Failed to export: ${error.message}`);
    }
  };

  return (
    <button
      onClick={handleClick}
      className="inline-flex items-center rounded-md border border-gray-300 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 shadow-sm hover:bg-gray-50"
    >
      ⬇ Export Sales Register (CSV{variant === "canonical" ? " - Canonical" : ""})
    </button>
  );
};

