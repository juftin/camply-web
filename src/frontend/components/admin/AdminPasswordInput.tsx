import { useState } from "react";
import { Check, Copy, KeyRound } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface AdminPasswordInputProps {
  id: string;
  label: string;
  value: string;
  onChange: (password: string) => void;
  disabled?: boolean;
}

/** Generate 144 bits of randomness with unbiased selection from 64 characters. */
function generatePassword(): string {
  const alphabet =
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";
  const bytes = crypto.getRandomValues(new Uint8Array(24));
  return Array.from(bytes, (byte) => alphabet[byte & 63]).join("");
}

/** Reveal generated credentials only while their create/reset dialog is open. */
export function AdminPasswordInput({
  id,
  label,
  value,
  onChange,
  disabled = false,
}: AdminPasswordInputProps) {
  const [generated, setGenerated] = useState(false);
  const [copied, setCopied] = useState(false);
  const [copying, setCopying] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleGenerate = () => {
    setCopied(false);
    setError(null);
    try {
      onChange(generatePassword());
      setGenerated(true);
    } catch {
      setError(
        "Could not generate a secure password. Try again or enter one manually.",
      );
    }
  };

  const handleCopy = async () => {
    setError(null);
    setCopying(true);
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
    } catch {
      setError("Could not copy the password. Select it and copy it manually.");
    } finally {
      setCopying(false);
    }
  };

  return (
    <div className="space-y-2">
      <Label htmlFor={id}>{label}</Label>
      <Input
        id={id}
        type={generated ? "text" : "password"}
        autoComplete="new-password"
        spellCheck={false}
        className={generated ? "font-mono" : undefined}
        value={value}
        onChange={(event) => {
          onChange(event.target.value);
          setGenerated(false);
          setCopied(false);
          setError(null);
        }}
        required
        disabled={disabled || copying}
      />
      <div className="flex flex-wrap gap-2">
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={handleGenerate}
          disabled={disabled || copying}
        >
          <KeyRound className="mr-1.5 h-4 w-4" /> Generate Password
        </Button>
        {generated && (
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={handleCopy}
            disabled={disabled || copying}
            aria-label={copied ? "Copied" : "Copy password"}
          >
            {copied ? (
              <Check className="mr-1.5 h-4 w-4" />
            ) : (
              <Copy className="mr-1.5 h-4 w-4" />
            )}
            {copied ? "Copied" : "Copy"}
          </Button>
        )}
      </div>
      {generated && (
        <p className="text-xs text-muted-foreground">
          Copy this password before saving. It will not be shown again.
        </p>
      )}
      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}
    </div>
  );
}
