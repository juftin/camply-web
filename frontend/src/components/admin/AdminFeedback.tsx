/** Announce the outcome of an administrator action. */
export function AdminFeedback({
  message,
  error = false,
}: {
  message: string | null;
  error?: boolean;
}) {
  if (!message) return null;
  return (
    <div
      role={error ? "alert" : "status"}
      className={`mb-4 rounded-md border p-3 text-sm ${error ? "bg-destructive/10 text-destructive border-destructive/30" : "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300"}`}
    >
      {message}
    </div>
  );
}
