import FieldWizard from "../components/FieldWizard";

export default function CreateField() {
  return (
    <>
      <div className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight text-gray-900">Add a Field</h1>
        <p className="mt-1 text-sm text-gray-500">
          Build the trusted foundation ANNADATA uses to know your field.
        </p>
      </div>
      <FieldWizard />
    </>
  );
}