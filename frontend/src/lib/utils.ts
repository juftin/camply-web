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
