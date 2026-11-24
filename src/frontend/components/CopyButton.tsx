import { useEffect, useState } from "react";
import { Check, Copy } from "lucide-react";
import { Button } from "@/components/ui/button";

export const CopyButton = ({
  value,
  label,
}: {
  value: string;
  label: string;
}) => {
  const [result, setResult] = useState<{
    value: string;
    copied: boolean;
  } | null>(null);
  const [copying, setCopying] = useState(false);
  const current = result?.value === value ? result : null;

  useEffect(() => {
    if (!result?.copied) return;
    const timer = window.setTimeout(() => setResult(null), 2500);
    return () => window.clearTimeout(timer);
  }, [result]);

  const copy = async () => {
    setCopying(true);
    try {
      await navigator.clipboard.writeText(value);
      setResult({ value, copied: true });
    } catch {
      setResult({ value, copied: false });
    } finally {
      setCopying(false);
    }
  };

  return (
    <div className="shrink-0">
      <Button
        type="button"
        variant="outline"
        size="sm"
        aria-label={label}
        title={current?.copied ? "Copied" : label}
        disabled={!value || copying}
        onClick={copy}
      >
        {current?.copied ? (
          <Check className="mr-1 h-4 w-4" aria-hidden="true" />
        ) : (
          <Copy className="mr-1 h-4 w-4" aria-hidden="true" />
        )}
        {current?.copied ? "Copied" : "Copy"}
      </Button>
      {current?.copied && (
        <span role="status" className="sr-only">
          {label.replace(/^Copy /, "")} copied
        </span>
      )}
      {current && !current.copied && (
        <p role="alert" className="mt-1 max-w-40 text-xs text-destructive">
          Copy failed. Try again or copy manually.
        </p>
      )}
    </div>
  );
};
