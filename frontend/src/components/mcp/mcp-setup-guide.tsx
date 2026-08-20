"use client";

import { useEffect, useState } from "react";
import {
  Activity,
  Bot,
  Check,
  Copy,
  FileCode,
  FlaskConical,
  ShieldAlert,
  Sparkles,
} from "lucide-react";
import { apiBaseUrl } from "@/lib/api/client";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { CodeHighlight } from "@/components/ui/code-highlight";
import { Input } from "@/components/ui/input";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import { useToast } from "@/components/ui/toast";

interface ClientConfig {
  command?: string;
  configJson?: string;
  description: string;
  filePath?: string;
  id: string;
  name: string;
  syntax: "json" | "bash";
}

function resolveServerUrl(): string {
  if (typeof window !== "undefined" && window.location?.origin) {
    if (apiBaseUrl.startsWith("http://") || apiBaseUrl.startsWith("https://")) {
      try {
        const parsed = new URL(apiBaseUrl);
        const isApiLocalhost =
          parsed.hostname === "localhost" || parsed.hostname === "127.0.0.1";
        const isWindowLocalhost =
          window.location.hostname === "localhost" ||
          window.location.hostname === "127.0.0.1";
        if (isApiLocalhost && !isWindowLocalhost) {
          return window.location.origin;
        }
        return parsed.origin;
      } catch {
        return window.location.origin;
      }
    }
    return window.location.origin;
  }

  if (apiBaseUrl.startsWith("http://") || apiBaseUrl.startsWith("https://")) {
    try {
      return new URL(apiBaseUrl).origin;
    } catch {
      // fallback
    }
  }

  return "";
}

export function McpSetupGuide() {
  const { notify } = useToast();
  const [serverUrl, setServerUrl] = useState<string>("");
  const [apiKeyInput, setApiKeyInput] = useState("");
  const [copiedTab, setCopiedTab] = useState<string | null>(null);
  const [selectedTab, setSelectedTab] = useState("antigravity");

  useEffect(() => {
    setServerUrl(resolveServerUrl());
  }, []);

  const effectiveKey = apiKeyInput.trim() || "<YOUR_API_KEY>";
  const effectiveUrl = serverUrl.trim() || resolveServerUrl() || "<SERVER_URL>";

  const jsonSnippet = JSON.stringify(
    {
      mcpServers: {
        gitvane: {
          command: "uvx",
          args: [
            "gitvane-mcp",
            "--server-url",
            effectiveUrl,
            "--api-key",
            effectiveKey,
          ],
        },
      },
    },
    null,
    2,
  );

  const clients: ClientConfig[] = [
    {
      id: "antigravity",
      name: "Antigravity",
      description: "Antigravity IDE & Autonomous Agents MCP Configuration",
      filePath: "~/.gemini/antigravity/mcp_config.json or .agent/mcp.json",
      configJson: jsonSnippet,
      syntax: "json",
    },
    {
      id: "codex",
      name: "OpenAI Codex",
      description: "Codex CLI & OpenAI MCP Clients",
      filePath: "~/.codex/config.json or .codex/mcp.json",
      configJson: jsonSnippet,
      syntax: "json",
    },
    {
      id: "claude-desktop",
      name: "Claude Desktop",
      description: "Anthropic Claude Desktop Application Configuration",
      filePath:
        "macOS: ~/Library/Application Support/Claude/claude_desktop_config.json | Windows: %APPDATA%\\Claude\\claude_desktop_config.json",
      configJson: jsonSnippet,
      syntax: "json",
    },
    {
      id: "cursor",
      name: "Cursor IDE",
      description: "Cursor Composer & MCP Settings",
      filePath: ".cursor/mcp.json or Settings > Features > MCP",
      configJson: jsonSnippet,
      syntax: "json",
    },
    {
      id: "claude-code",
      name: "Claude Code",
      description: "Claude Code CLI one-liner registration",
      command: `claude mcp add gitvane -- uvx gitvane-mcp --server-url ${effectiveUrl} --api-key ${effectiveKey}`,
      syntax: "bash",
    },
    {
      id: "windsurf",
      name: "Windsurf / Generic",
      description: "Windsurf Cascade, Roo Code, and standard stdio MCP clients",
      filePath: "~/.codeium/windsurf/mcp_config.json",
      configJson: jsonSnippet,
      command: `# Standalone execution via environment variables:\nexport GITVANE_SERVER_URL="${effectiveUrl}"\nexport GITVANE_API_KEY="${effectiveKey}"\nuvx gitvane-mcp`,
      syntax: "json",
    },
  ];

  const handleCopySnippet = async (textToCopy: string, tabId: string) => {
    try {
      await navigator.clipboard.writeText(textToCopy);
      setCopiedTab(tabId);
      notify({
        title: "Snippet copied",
        description: "MCP configuration copied to clipboard.",
        variant: "info",
      });
      setTimeout(() => setCopiedTab(null), 2500);
    } catch {
      notify({
        title: "Copy failed",
        description: "Please copy the snippet manually.",
        variant: "warning",
      });
    }
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2.5">
            <div className="grid size-9 place-items-center rounded-lg border border-border bg-panel-muted text-primary">
              <Bot className="size-4" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-foreground">
                AI Agent & MCP Setup Guide
              </h2>
              <p className="text-xs text-muted">
                Connect your favorite AI agent or IDE to GitVane using the Model Context Protocol (MCP).
              </p>
            </div>
          </div>
        </CardHeader>

        <CardContent className="space-y-6 p-5">
          {/* Parameter customization bar */}
          <div className="rounded-lg border border-border/80 bg-panel-muted/50 p-4">
            <div className="max-w-xl">
              <label
                className="mb-1.5 block font-mono text-[11px] font-bold uppercase tracking-wider text-muted"
                htmlFor="mcp-api-key"
              >
                Personal API Key (Optional Override)
              </label>
              <Input
                className="font-mono text-xs"
                id="mcp-api-key"
                onChange={(e) => setApiKeyInput(e.target.value)}
                placeholder="gv_live_... (or leave empty to use placeholder)"
                value={apiKeyInput}
              />
              <p className="mt-1 text-[11px] text-muted">
                Paste your secret key above to automatically populate all snippet templates.
              </p>
            </div>
          </div>

          {/* Interactive Client Configuration Tabs */}
          <Tabs onValueChange={setSelectedTab} value={selectedTab}>
            <div className="overflow-x-auto pb-1">
              <TabsList className="flex min-w-max">
                {clients.map((client) => (
                  <TabsTrigger
                    key={client.id}
                    onClick={() => setSelectedTab(client.id)}
                    value={client.id}
                  >
                    {client.name}
                  </TabsTrigger>
                ))}
              </TabsList>
            </div>

            {clients.map((client) => {
              const snippet = client.configJson || client.command || "";
              const isCopied = copiedTab === client.id;

              return (
                <TabsContent
                  className="mt-4 space-y-3"
                  key={client.id}
                  value={client.id}
                >
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                    <div>
                      <h3 className="text-sm font-semibold text-foreground">
                        {client.name} Integration
                      </h3>
                      <p className="text-xs text-muted">{client.description}</p>
                    </div>

                    <Button
                      className="flex items-center gap-1.5 self-start sm:self-auto"
                      onClick={() => handleCopySnippet(snippet, client.id)}
                      size="sm"
                      variant="secondary"
                    >
                      {isCopied ? (
                        <>
                          <Check className="size-3.5 text-success" />
                          <span>Copied!</span>
                        </>
                      ) : (
                        <>
                          <Copy className="size-3.5" />
                          <span>Copy Configuration</span>
                        </>
                      )}
                    </Button>
                  </div>

                  {client.filePath && (
                    <div className="flex items-center gap-2 rounded-md border border-border/70 bg-panel px-3 py-1.5 text-xs text-muted">
                      <FileCode className="size-3.5 shrink-0 text-primary" />
                      <span className="font-mono text-[11px] truncate">
                        File location: <strong className="text-foreground">{client.filePath}</strong>
                      </span>
                    </div>
                  )}

                  <div className="relative">
                    <CodeHighlight
                      code={snippet}
                      language={client.syntax}
                    />
                  </div>

                  {client.id === "windsurf" && client.command && (
                    <div className="mt-3">
                      <p className="mb-1 text-xs font-semibold text-muted">
                        Alternative: CLI / Shell Environment Variables
                      </p>
                      <CodeHighlight code={client.command} language="bash" />
                    </div>
                  )}
                </TabsContent>
              );
            })}
          </Tabs>
        </CardContent>
      </Card>

      {/* MCP Tools & Capabilities Section */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2.5">
            <div className="grid size-9 place-items-center rounded-lg border border-border bg-panel-muted text-primary">
              <Sparkles className="size-4" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-foreground">
                Exposed MCP Tools & Agent Intelligence
              </h2>
              <p className="text-xs text-muted">
                When connected, AI agents gain real-time access to the following GitVane capabilities:
              </p>
            </div>
          </div>
        </CardHeader>

        <CardContent className="grid grid-cols-1 gap-4 p-5 md:grid-cols-3">
          <div className="rounded-lg border border-border/80 bg-panel p-4 shadow-sm transition-all hover:border-primary/40">
            <div className="flex items-center gap-2 text-primary">
              <Activity className="size-4" />
              <h3 className="font-mono text-xs font-bold lowercase">
                gitvane_analyze_impact
              </h3>
            </div>
            <p className="mt-2 text-xs leading-relaxed text-muted">
              Performs change blast radius and graph impact analysis on modified files or staged git diffs, identifying affected downstream consumers and risky call chains.
            </p>
            <div className="mt-3 flex items-center gap-1.5">
              <Badge tone="info">Local Diff Aware</Badge>
              <Badge tone="neutral">Graph Traversal</Badge>
            </div>
          </div>

          <div className="rounded-lg border border-border/80 bg-panel p-4 shadow-sm transition-all hover:border-primary/40">
            <div className="flex items-center gap-2 text-primary">
              <FlaskConical className="size-4" />
              <h3 className="font-mono text-xs font-bold lowercase">
                gitvane_recommend_tests
              </h3>
            </div>
            <p className="mt-2 text-xs leading-relaxed text-muted">
              Selects and recommends the optimal minimal test suites needed to validate code changes before committing, cutting CI feedback loops and test execution times.
            </p>
            <div className="mt-3 flex items-center gap-1.5">
              <Badge tone="success">Smart Selection</Badge>
              <Badge tone="neutral">Confidence Score</Badge>
            </div>
          </div>

          <div className="rounded-lg border border-border/80 bg-panel p-4 shadow-sm transition-all hover:border-primary/40">
            <div className="flex items-center gap-2 text-primary">
              <ShieldAlert className="size-4" />
              <h3 className="font-mono text-xs font-bold lowercase">
                gitvane_get_file_risk
              </h3>
            </div>
            <p className="mt-2 text-xs leading-relaxed text-muted">
              Returns risk scoring, static structural complexity, and historical change churn for repository files so agents can exercise caution on high-risk modules.
            </p>
            <div className="mt-3 flex items-center gap-1.5">
              <Badge tone="warning">Risk Metric</Badge>
              <Badge tone="neutral">Complexity</Badge>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
