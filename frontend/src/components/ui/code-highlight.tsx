"use client";

import DOMPurify from "dompurify";
import hljs from "highlight.js";
import "highlight.js/styles/atom-one-dark.css";
import { cn } from "@/lib/utils";

interface CodeHighlightProps {
  className?: string;
  code: string;
  inline?: boolean;
  language?: string | null;
}

export function CodeHighlight({
  className,
  code,
  inline = false,
  language,
}: CodeHighlightProps) {
  const normalizedLang = language?.trim().toLowerCase();
  const validLanguage =
    normalizedLang && hljs.getLanguage(normalizedLang)
      ? normalizedLang
      : undefined;

  let highlightedHtml: string;
  try {
    if (validLanguage) {
      highlightedHtml = hljs.highlight(code, {
        ignoreIllegals: true,
        language: validLanguage,
      }).value;
    } else {
      highlightedHtml = hljs.highlightAuto(code).value;
    }
  } catch {
    highlightedHtml = escapeHtml(code);
  }

  const safeHtml = DOMPurify.sanitize(highlightedHtml, {
    ALLOWED_ATTR: ["class"],
    ALLOWED_TAGS: ["span", "mark", "b", "i"],
  });

  if (inline) {
    return (
      <code
        className={cn(
          "hljs rounded border border-border bg-panel-muted px-2 py-1 font-mono text-xs text-foreground",
          validLanguage ? `language-${validLanguage}` : "",
          className,
        )}
        dangerouslySetInnerHTML={{ __html: safeHtml }}
      />
    );
  }

  return (
    <pre
      className={cn(
        "overflow-x-auto rounded-md border border-border bg-panel-muted p-4 font-mono text-xs leading-6 text-foreground",
        className,
      )}
    >
      <code
        className={`hljs ${validLanguage ? `language-${validLanguage}` : ""}`}
        dangerouslySetInnerHTML={{ __html: safeHtml }}
      />
    </pre>
  );
}

function escapeHtml(str: string): string {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
