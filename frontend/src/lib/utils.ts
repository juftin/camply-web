import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import DOMPurify from "dompurify";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function toTitleCase(str: string): string {
  if (!str) return str;

  // If the string has mixed casing, return it unchanged — it's already
  // properly formatted (e.g. "McKinney Lake", "Yosemite National Park").
  // Only normalize strings that are ALL UPPERCASE or all lowercase.
  const isAllUpper = str === str.toUpperCase();
  const isAllLower = str === str.toLowerCase();

  if (!isAllUpper && !isAllLower) {
    return str;
  }

  const exceptions = new Set([
    "of",
    "the",
    "and",
    "in",
    "on",
    "at",
    "to",
    "for",
    "with",
    "by",
  ]);

  const words = str.toLowerCase().split(" ");

  return words
    .map((word, index) => {
      if (!word) return word; // preserve empty strings from consecutive spaces
      // Always capitalize the first word
      if (index === 0) {
        return word.charAt(0).toUpperCase() + word.slice(1);
      }
      // Lowercase exception words
      if (exceptions.has(word)) {
        return word;
      }
      // Capitalize everything else
      return word.charAt(0).toUpperCase() + word.slice(1);
    })
    .join(" ");
}

export function sanitizeAndRenderHTML(html: string | null | undefined): {
  __html: string;
} {
  if (!html) return { __html: "" };

  // Check if the content contains HTML tags
  const hasHTML = /<[a-z][\s\S]*>/i.test(html);

  if (hasHTML) {
    // Sanitize HTML content
    const clean = DOMPurify.sanitize(html, {
      ALLOWED_TAGS: [
        "p",
        "br",
        "strong",
        "em",
        "u",
        "a",
        "ul",
        "ol",
        "li",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
      ],
      ALLOWED_ATTR: ["href", "target", "rel"],
    });
    return { __html: clean };
  } else {
    // Plain text - convert to title case and return
    return { __html: toTitleCase(html) };
  }
}

export function isHTMLContent(content: string | null | undefined): boolean {
  if (!content) return false;
  return /<[a-z][\s\S]*>/i.test(content);
}

export function formatDate(iso: string): string {
  const d = new Date(iso + "T00:00:00");
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

export function daysBetween(start: string, end: string): number {
  const s = new Date(start + "T00:00:00");
  const e = new Date(end + "T00:00:00");
  return Math.max(0, Math.round((e.getTime() - s.getTime()) / 86400000));
}

export function formatRelativeTime(iso: string): string {
  const now = Date.now();
  const then = new Date(iso).getTime();
  const diffSec = Math.floor((now - then) / 1000);
  if (diffSec < 0) {
    const abs = Math.abs(diffSec);
    if (abs < 60) return "just now";
    if (abs < 3600) return `in ${Math.floor(abs / 60)}m`;
    if (abs < 86400) return `in ${Math.floor(abs / 3600)}h`;
    return `in ${Math.floor(abs / 86400)}d`;
  }
  if (diffSec < 60) return `${diffSec}s ago`;
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`;
  return `${Math.floor(diffSec / 86400)}d ago`;
}
