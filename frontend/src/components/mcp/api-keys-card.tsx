"use client";

import { useState } from "react";
import {
  AlertTriangle,
  Check,
  Copy,
  Key,
  Plus,
  ShieldAlert,
  Trash2,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
} from "@/components/ui/dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { Notice } from "@/components/ui/notice";
import { Selector } from "@/components/ui/selector";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeaderCell,
  TableRow,
} from "@/components/ui/table";
import { useToast } from "@/components/ui/toast";
import {
  useCreateApiKeyMutation,
  useGetApiKeysQuery,
  useRevokeApiKeyMutation,
} from "@/store/api/gitvaneApi";
import type { ApiKeyCreatedResponse, ApiKeyItem } from "@/types/apiKeys";

const EXPIRATION_OPTIONS = [
  { label: "Never expires", value: "never" },
  { label: "30 days", value: "30" },
  { label: "90 days", value: "90" },
  { label: "1 year (365 days)", value: "365" },
];

function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return "Never";
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return dateStr;
    return d.toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return dateStr;
  }
}

function getKeyStatus(key: ApiKeyItem): { label: string; tone: "success" | "warning" | "danger" } {
  if (key.is_revoked) {
    return { label: "Revoked", tone: "danger" };
  }
  if (key.expires_at) {
    const expiry = new Date(key.expires_at).getTime();
    if (!isNaN(expiry) && expiry < Date.now()) {
      return { label: "Expired", tone: "warning" };
    }
  }
  return { label: "Active", tone: "success" };
}

export function ApiKeysCard() {
  const { data: apiKeys, isLoading, isError, refetch } = useGetApiKeysQuery();
  const [createApiKey, { isLoading: isCreating }] = useCreateApiKeyMutation();
  const [revokeApiKey, { isLoading: isRevoking }] = useRevokeApiKeyMutation();
  const { notify } = useToast();

  // Create Modal State
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [keyName, setKeyName] = useState("");
  const [expirationChoice, setExpirationChoice] = useState("never");
  const [createError, setCreateError] = useState<string | null>(null);

  // Raw Key Created Modal State
  const [newlyCreatedKey, setNewlyCreatedKey] = useState<ApiKeyCreatedResponse | null>(null);
  const [hasCopiedKey, setHasCopiedKey] = useState(false);

  // Revoke Dialog State
  const [keyToRevoke, setKeyToRevoke] = useState<ApiKeyItem | null>(null);

  const handleOpenCreate = () => {
    setKeyName("");
    setExpirationChoice("never");
    setCreateError(null);
    setIsCreateOpen(true);
  };

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmedName = keyName.trim();
    if (!trimmedName) {
      setCreateError("Key name is required.");
      return;
    }

    setCreateError(null);
    const expiresInDays =
      expirationChoice === "never" ? undefined : parseInt(expirationChoice, 10);

    try {
      const result = await createApiKey({
        name: trimmedName,
        expires_in_days: expiresInDays,
      }).unwrap();

      setIsCreateOpen(false);
      setNewlyCreatedKey(result);
      setHasCopiedKey(false);
      notify({
        title: "API key generated",
        description: `API key "${result.name}" has been created successfully.`,
        variant: "success",
      });
    } catch (err: unknown) {
      const errorMsg =
        typeof err === "object" && err && "data" in err
          ? JSON.stringify((err as { data: unknown }).data)
          : "Failed to create API key. Please try again.";
      setCreateError(errorMsg);
      notify({
        title: "Failed to create API key",
        description: errorMsg,
        variant: "destructive",
      });
    }
  };

  const handleCopyRawKey = async () => {
    if (!newlyCreatedKey) return;
    try {
      await navigator.clipboard.writeText(newlyCreatedKey.raw_key);
      setHasCopiedKey(true);
      notify({
        title: "Copied to clipboard",
        description: "API key copied securely.",
        variant: "info",
      });
      setTimeout(() => setHasCopiedKey(false), 2500);
    } catch {
      notify({
        title: "Failed to copy",
        description: "Please manually copy the key from the box.",
        variant: "warning",
      });
    }
  };

  const handleRevokeConfirm = async () => {
    if (!keyToRevoke) return;
    try {
      await revokeApiKey(keyToRevoke.id).unwrap();
      notify({
        title: "API key revoked",
        description: `Key "${keyToRevoke.name}" has been revoked.`,
        variant: "success",
      });
      setKeyToRevoke(null);
    } catch {
      notify({
        title: "Failed to revoke key",
        description: "Could not revoke API key. Please try again.",
        variant: "destructive",
      });
    }
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="flex items-center gap-2.5">
              <div className="grid size-9 place-items-center rounded-lg border border-border bg-panel-muted text-primary">
                <Key className="size-4" />
              </div>
              <div>
                <h2 className="text-base font-semibold text-foreground">
                  Personal API Keys
                </h2>
                <p className="text-xs text-muted">
                  Authenticate your AI coding agents, IDE extensions, and the GitVane MCP server.
                </p>
              </div>
            </div>
          </div>

          <Button
            className="flex items-center gap-2"
            onClick={handleOpenCreate}
            size="sm"
          >
            <Plus className="size-4" />
            Create New Key
          </Button>
        </CardHeader>

        <CardContent className="p-0">
          {isLoading ? (
            <div className="space-y-3 p-5">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </div>
          ) : isError ? (
            <div className="p-5">
              <Notice tone="danger">
                Failed to load API keys.{" "}
                <button
                  className="font-medium underline hover:text-foreground"
                  onClick={() => refetch()}
                  type="button"
                >
                  Click here to retry
                </button>
              </Notice>
            </div>
          ) : !apiKeys || apiKeys.length === 0 ? (
            <div className="p-5">
              <EmptyState
                action={
                  <Button onClick={handleOpenCreate} size="sm">
                    <Plus className="size-4" />
                    Create First Key
                  </Button>
                }
                description="No API keys found. Create a personal API key to configure Claude Desktop, Cursor, Antigravity, or other MCP clients."
                icon={<Key className="size-5" />}
                title="No API Keys Generated"
              />
            </div>
          ) : (
            <Table>
              <TableHead>
                <TableRow>
                  <TableHeaderCell>Name</TableHeaderCell>
                  <TableHeaderCell>Key Prefix</TableHeaderCell>
                  <TableHeaderCell>Created</TableHeaderCell>
                  <TableHeaderCell>Expires</TableHeaderCell>
                  <TableHeaderCell>Last Used</TableHeaderCell>
                  <TableHeaderCell>Status</TableHeaderCell>
                  <TableHeaderCell className="text-right">Actions</TableHeaderCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {apiKeys.map((key) => {
                  const status = getKeyStatus(key);
                  return (
                    <TableRow key={key.id}>
                      <TableCell className="font-medium text-foreground">
                        {key.name}
                      </TableCell>
                      <TableCell>
                        <code className="rounded bg-panel-muted px-2 py-0.5 font-mono text-xs text-foreground">
                          {key.key_prefix}••••••••
                        </code>
                      </TableCell>
                      <TableCell className="text-xs text-muted">
                        {formatDate(key.created_at)}
                      </TableCell>
                      <TableCell className="text-xs text-muted">
                        {formatDate(key.expires_at)}
                      </TableCell>
                      <TableCell className="text-xs text-muted">
                        {formatDate(key.last_used_at)}
                      </TableCell>
                      <TableCell>
                        <Badge tone={status.tone}>{status.label}</Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        {!key.is_revoked ? (
                          <Button
                            aria-label={`Revoke key ${key.name}`}
                            className="h-8 text-xs text-danger hover:bg-danger/10 hover:text-danger"
                            disabled={isRevoking}
                            onClick={() => setKeyToRevoke(key)}
                            size="sm"
                            variant="ghost"
                          >
                            <Trash2 className="size-3.5" />
                            Revoke
                          </Button>
                        ) : (
                          <span className="text-xs text-muted">Revoked</span>
                        )}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Create Key Dialog */}
      <Dialog onOpenChange={setIsCreateOpen} open={isCreateOpen}>
        <DialogContent title="Create New Personal API Key">
          <form className="space-y-4" onSubmit={handleCreateSubmit}>
            {createError ? <Notice tone="danger">{createError}</Notice> : null}

            <div>
              <label
                className="mb-1.5 block font-mono text-xs font-semibold uppercase tracking-wider text-muted"
                htmlFor="api-key-name"
              >
                Key Name / Description
              </label>
              <Input
                id="api-key-name"
                onChange={(e) => setKeyName(e.target.value)}
                placeholder="e.g. Cursor IDE, MacBook Claude Code, Antigravity Agent"
                required
                value={keyName}
              />
              <p className="mt-1 text-[11px] text-muted">
                Give your token a distinctive name so you can identify which AI agent is using it.
              </p>
            </div>

            <div>
              <label
                className="mb-1.5 block font-mono text-xs font-semibold uppercase tracking-wider text-muted"
                htmlFor="api-key-expiration"
              >
                Expiration
              </label>
              <Selector
                id="api-key-expiration"
                onChange={(val) => {
                  const selected = Array.isArray(val) ? val[0] : val;
                  setExpirationChoice(selected || "never");
                }}
                options={EXPIRATION_OPTIONS}
                value={expirationChoice}
              />
            </div>

            <div className="mt-6 flex justify-end gap-2.5 pt-2">
              <Button
                disabled={isCreating}
                onClick={() => setIsCreateOpen(false)}
                type="button"
                variant="secondary"
              >
                Cancel
              </Button>
              <Button disabled={isCreating || !keyName.trim()} type="submit">
                {isCreating ? "Generating..." : "Generate Key"}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      {/* Save Secret Raw Key Dialog */}
      <Dialog
        onOpenChange={(open) => {
          if (!open) {
            setNewlyCreatedKey(null);
          }
        }}
        open={Boolean(newlyCreatedKey)}
      >
        <DialogContent title="Save Your Personal API Key">
          {newlyCreatedKey && (
            <div className="space-y-4">
              <Notice className="flex items-start gap-2.5 text-xs" tone="warning">
                <AlertTriangle className="mt-0.5 size-4 shrink-0 text-warning" />
                <div>
                  <strong className="font-semibold">Store this secret key securely:</strong>
                  <p className="mt-0.5">
                    This token will <span className="font-bold underline">never</span> be displayed again. If you lose it, you will need to revoke this key and create a new one.
                  </p>
                </div>
              </Notice>

              <div>
                <label
                  className="mb-1.5 block font-mono text-xs font-semibold uppercase tracking-wider text-muted"
                  htmlFor="raw-api-key-display"
                >
                  Key: {newlyCreatedKey.name}
                </label>
                <div className="flex items-center gap-2">
                  <Input
                    className="font-mono text-xs bg-panel-muted selection:bg-primary selection:text-white"
                    id="raw-api-key-display"
                    readOnly
                    value={newlyCreatedKey.raw_key}
                  />
                  <Button
                    className="shrink-0 flex items-center gap-1.5"
                    onClick={handleCopyRawKey}
                    type="button"
                    variant="secondary"
                  >
                    {hasCopiedKey ? (
                      <>
                        <Check className="size-4 text-success" />
                        <span>Copied!</span>
                      </>
                    ) : (
                      <>
                        <Copy className="size-4" />
                        <span>Copy</span>
                      </>
                    )}
                  </Button>
                </div>
              </div>

              <div className="mt-6 flex justify-end pt-2">
                <Button
                  onClick={() => setNewlyCreatedKey(null)}
                  type="button"
                >
                  I have copied my key
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Revoke Key Confirmation Dialog */}
      <Dialog
        onOpenChange={(open) => {
          if (!open) {
            setKeyToRevoke(null);
          }
        }}
        open={Boolean(keyToRevoke)}
      >
        <DialogContent title="Revoke Personal API Key">
          {keyToRevoke && (
            <div className="space-y-4">
              <div className="flex items-start gap-3 rounded-lg border border-danger/20 bg-danger/5 p-3.5 text-danger">
                <ShieldAlert className="size-5 shrink-0" />
                <div className="text-xs leading-relaxed text-foreground">
                  <p className="font-semibold text-danger">
                    Are you sure you want to revoke &quot;{keyToRevoke.name}&quot;?
                  </p>
                  <p className="mt-1 text-muted">
                    Any MCP servers, IDE extensions, or scripts currently using prefix{" "}
                    <code className="font-mono font-bold text-foreground">
                      {keyToRevoke.key_prefix}••••
                    </code>{" "}
                    will immediately be denied access to the GitVane API. This action cannot be undone.
                  </p>
                </div>
              </div>

              <div className="flex justify-end gap-2.5 pt-2">
                <Button
                  disabled={isRevoking}
                  onClick={() => setKeyToRevoke(null)}
                  type="button"
                  variant="secondary"
                >
                  Cancel
                </Button>
                <Button
                  className="bg-danger text-white hover:bg-danger/90"
                  disabled={isRevoking}
                  onClick={handleRevokeConfirm}
                  type="button"
                >
                  {isRevoking ? "Revoking..." : "Revoke Key"}
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
