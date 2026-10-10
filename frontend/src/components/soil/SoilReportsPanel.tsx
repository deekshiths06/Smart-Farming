import { useRef, useState } from "react";
import { Download, FileText, Link2, Paperclip, Upload } from "lucide-react";
import { Button } from "../ui/Button";
import { Input } from "../ui/Input";
import { StatusBadge } from "../ui/StatusBadge";
import { formatBytes, formatSoilDate } from "../../lib/soil";
import { soilErrorMessage } from "../../services/soil";
import type { SoilReport } from "../../types/soil";

interface SoilReportsPanelProps {
  reports: SoilReport[];
  onUpload: (file: File, meta: { report_date?: string; report_source?: string }) => Promise<void>;
  onDownload: (report: SoilReport) => Promise<void>;
}

function todayISO(): string {
  return new Date().toISOString().slice(0, 10);
}

export function SoilReportsPanel({ reports, onUpload, onDownload }: SoilReportsPanelProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [reportDate, setReportDate] = useState("");
  const [reportSource, setReportSource] = useState("");
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [downloadingId, setDownloadingId] = useState<number | null>(null);

  const handleUpload = async () => {
    setError(null);
    if (!file) {
      setError("Choose a PDF or scan of the soil report first.");
      return;
    }
    setUploading(true);
    try {
      await onUpload(file, {
        report_date: reportDate || undefined,
        report_source: reportSource.trim() || undefined,
      });
      setFile(null);
      setReportDate("");
      setReportSource("");
      if (inputRef.current) inputRef.current.value = "";
    } catch (err) {
      setError(soilErrorMessage(err, "The report could not be uploaded. Please try again."));
    } finally {
      setUploading(false);
    }
  };

  const handleDownload = async (report: SoilReport) => {
    setDownloadingId(report.id);
    try {
      await onDownload(report);
    } finally {
      setDownloadingId(null);
    }
  };

  return (
    <section className="space-y-4">
      <div className="flex items-center gap-2">
        <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-50 text-brand-700">
          <Paperclip className="h-4.5 w-4.5" />
        </span>
        <div>
          <h2 className="text-lg font-bold tracking-tight text-ink">Uploaded soil reports</h2>
          <p className="text-xs text-ink-muted">
            Keep the original lab sheet or Soil Health Card with the field for reference.
          </p>
        </div>
      </div>

      <div className="rounded-panel border border-border bg-surface p-5 shadow-card">
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="w-full">
            <label htmlFor="soil-report-file" className="mb-1.5 block text-sm font-medium text-ink-soft">
              Report file
            </label>
            <input
              ref={inputRef}
              id="soil-report-file"
              type="file"
              accept=".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png"
              onChange={(event) => setFile(event.target.files?.[0] ?? null)}
              className="block w-full cursor-pointer rounded-lg border border-border-strong bg-surface text-sm text-ink-soft shadow-soft file:mr-3 file:cursor-pointer file:rounded-l-lg file:border-0 file:bg-surface-sunken file:px-3 file:py-2.5 file:text-sm file:font-semibold file:text-ink-soft hover:file:bg-border focus:outline-none focus:ring-2 focus:ring-brand-600/20"
            />
            <p className="mt-1.5 text-xs text-ink-muted">PDF, JPG or PNG · up to 10 MB.</p>
          </div>
          <Input
            id="soil-report-date"
            type="date"
            label="Report date (optional)"
            max={todayISO()}
            value={reportDate}
            onChange={(event) => setReportDate(event.target.value)}
          />
          <Input
            id="soil-report-source"
            label="Issued by (optional)"
            placeholder="e.g. Soil Health Card, KVK lab"
            value={reportSource}
            onChange={(event) => setReportSource(event.target.value)}
          />
          <div className="flex items-end">
            <Button
              leftIcon={<Upload className="h-4 w-4" />}
              onClick={() => void handleUpload()}
              loading={uploading}
              disabled={!file}
              className="w-full"
            >
              Upload report
            </Button>
          </div>
        </div>
        {error && (
          <p role="alert" className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </p>
        )}
        <p className="mt-3 text-xs text-ink-muted">
          Files are stored privately. Uploading a report does not create any soil values — you still
          enter and confirm the numbers you read from it.
        </p>
      </div>

      {reports.length === 0 ? (
        <p className="rounded-card border border-dashed border-border-strong bg-surface p-6 text-center text-sm text-ink-muted">
          No reports uploaded for this field yet.
        </p>
      ) : (
        <div className="space-y-2.5">
          {reports.map((report) => (
            <div
              key={report.id}
              className="flex items-center gap-3 rounded-card border border-border bg-surface p-3 shadow-card"
            >
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-surface-sunken text-ink-soft">
                <FileText className="h-4.5 w-4.5" />
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-ink">{report.original_filename}</p>
                <p className="truncate text-xs text-ink-muted">
                  {formatBytes(report.file_size_bytes)}
                  {report.report_date ? ` · ${formatSoilDate(report.report_date)}` : ""}
                  {report.report_source ? ` · ${report.report_source}` : ""}
                </p>
              </div>
              {report.status === "linked" ? (
                <StatusBadge tone="success" icon={<Link2 className="h-3.5 w-3.5" />}>
                  Linked
                </StatusBadge>
              ) : (
                <StatusBadge tone="neutral">Uploaded</StatusBadge>
              )}
              <Button
                size="sm"
                variant="outline"
                leftIcon={<Download className="h-3.5 w-3.5" />}
                loading={downloadingId === report.id}
                onClick={() => void handleDownload(report)}
              >
                Download
              </Button>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
