"use client";

import { Bot, Sparkles } from "lucide-react";
import { ApiKeysCard } from "@/components/mcp/api-keys-card";
import { McpSetupGuide } from "@/components/mcp/mcp-setup-guide";
import { Badge } from "@/components/ui/badge";

export default function McpPage() {
  return (
    <div className="mx-auto max-w-7xl space-y-8">
      {/* Page Header */}
      <div className="border-b border-border/70 pb-6">
        <div className="flex items-center gap-2">
          <Badge tone="info">Model Context Protocol</Badge>
          <span className="flex items-center gap-1 text-xs text-muted">
            <Sparkles className="size-3 text-primary" />
            Standard stdio & HTTP
          </span>
        </div>
        <h1 className="mt-3 text-3xl font-extrabold tracking-tight md:text-4xl text-balance flex items-center gap-3">
          <Bot className="size-8 text-primary shrink-0" />
          MCP & AI Agent Integration
        </h1>
        <p className="mt-2.5 max-w-3xl text-sm leading-relaxed text-muted font-medium text-balance">
          Connect autonomous AI agents, IDE assistants (Antigravity, Claude Desktop, Cursor, Claude Code, Windsurf), and terminal CLI tools to GitVane using standard Model Context Protocol servers. Generate personal API keys and copy one-click setup snippets below.
        </p>
      </div>

      {/* 1. API Key Management */}
      <section>
        <ApiKeysCard />
      </section>

      {/* 2. MCP Setup Guide & Tool Capabilities */}
      <section>
        <McpSetupGuide />
      </section>
    </div>
  );
}
