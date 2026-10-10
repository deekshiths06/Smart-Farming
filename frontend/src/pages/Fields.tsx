import { useState } from "react";
import { Link } from "react-router-dom";
import { MapPinned, Plus, Search, Sprout } from "lucide-react";
import { PageHeader } from "../components/ui/PageHeader";
import { FieldCard } from "../components/ui/FieldCard";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorAlert } from "../components/ui/ErrorAlert";
import { Skeleton } from "../components/ui/Skeleton";
import { Button } from "../components/ui/Button";
import { useFields } from "../hooks/useFields";
import { fieldsApi } from "../services/fields";
import type { Field } from "../types/field";

export default function Fields() {
  const { fields, loading, error, reload } = useFields();
  const [query, setQuery] = useState("");
  const [pendingDelete, setPendingDelete] = useState<Field | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const filtered = fields.filter((field) =>
    field.field_name.toLowerCase().includes(query.trim().toLowerCase())
  );

  const handleDelete = async () => {
    if (!pendingDelete) return;
    setDeleting(true);
    setDeleteError(null);
    try {
      await fieldsApi.remove(pendingDelete.id);
      setPendingDelete(null);
      await reload();
    } catch {
      setDeleteError("We could not delete this field. Please try again.");
      setDeleting(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="My Fields"
        description="Every decision starts with a field you can trust. Search, review and add to your record."
        icon={<MapPinned className="h-5 w-5" />}
        actions={
          <Link to="/fields/create">
            <Button rightIcon={<Plus className="h-4 w-4" />}>Add a field</Button>
          </Link>
        }
      />

      {error && <ErrorAlert title="Fields could not be loaded" message={error} onRetry={() => void reload()} />}

      {loading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {[...Array(6)].map((_, index) => (
            <Skeleton key={index} className="h-72 rounded-card" />
          ))}
        </div>
      ) : fields.length === 0 ? (
        <EmptyState
          icon={<Sprout className="h-8 w-8" />}
          title="Know your first field"
          description="Add your field with GPS and a map — where it is, how big it is, and its water and soil story. This is the foundation every ANNADATA decision will build on."
          action={
            <Link to="/fields/create">
              <Button rightIcon={<Plus className="h-4 w-4" />}>Create your first field</Button>
            </Link>
          }
        />
      ) : (
        <>
          <div className="flex items-center gap-2 rounded-card border border-border bg-surface px-3.5 py-2.5 shadow-card">
            <Search className="h-4 w-4 shrink-0 text-ink-muted" />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search your fields by name…"
              aria-label="Search fields"
              className="w-full bg-transparent text-sm text-ink placeholder:text-ink-muted focus:outline-none"
            />
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {filtered.map((field) => (
              <FieldCard key={field.id} field={field} onDelete={setPendingDelete} />
            ))}
          </div>

          {filtered.length === 0 && (
            <p className="mt-6 rounded-card border border-dashed border-border-strong bg-surface p-8 text-center text-sm text-ink-muted">
              No fields match “{query}”.
            </p>
          )}
        </>
      )}

      <ConfirmDialog
        open={pendingDelete !== null}
        title={`Delete “${pendingDelete?.field_name ?? ""}”?`}
        description={
          <>
            This removes the field and its record from ANNADATA. It cannot be undone.
            {deleteError && <span className="mt-2 block text-sm font-medium text-red-700">{deleteError}</span>}
          </>
        }
        confirmLabel="Delete field"
        loading={deleting}
        onConfirm={() => void handleDelete()}
        onCancel={() => {
          setPendingDelete(null);
          setDeleteError(null);
        }}
      />
    </div>
  );
}