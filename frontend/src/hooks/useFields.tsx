import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { fieldsApi } from "../services/fields";
import type { Field } from "../types/field";

interface FieldsContextValue {
  fields: Field[];
  loading: boolean;
  error: string | null;
  reload: () => Promise<void>;
  selectedField: Field | null;
  setSelectedFieldId: (id: number | null) => void;
}

const FieldsContext = createContext<FieldsContextValue | undefined>(undefined);

export function FieldsProvider({ children }: { children: ReactNode }) {
  const [fields, setFields] = useState<Field[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedFieldId, setSelectedFieldId] = useState<number | null>(null);

  const reload = useCallback(async () => {
    setError(null);
    setLoading(true);
    try {
      const list = await fieldsApi.list();
      setFields(list);
      setSelectedFieldId((current) =>
        current !== null && list.some((item) => item.id === current)
          ? current
          : (list[0]?.id ?? null)
      );
    } catch {
      setFields([]);
      setError("We could not load your fields. Please try again.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  const selectedField = useMemo(
    () => fields.find((item) => item.id === selectedFieldId) ?? null,
    [fields, selectedFieldId]
  );

  const value = useMemo(
    () => ({ fields, loading, error, reload, selectedField, setSelectedFieldId }),
    [fields, loading, error, reload, selectedField]
  );

  return <FieldsContext.Provider value={value}>{children}</FieldsContext.Provider>;
}

export function useFields(): FieldsContextValue {
  const context = useContext(FieldsContext);
  if (!context) {
    throw new Error("useFields must be used within FieldsProvider");
  }
  return context;
}