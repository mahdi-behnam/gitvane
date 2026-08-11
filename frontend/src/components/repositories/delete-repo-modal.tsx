"use client";

import { useEffect, useState } from "react";
import { Copy, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Notice } from "@/components/ui/notice";

interface DeleteRepoModalProps {
  error?: string | null;
  isLoading?: boolean;
  onConfirm: () => void | Promise<void>;
  onOpenChange: (open: boolean) => void;
  open: boolean;
  repositoryName: string;
}

export function DeleteRepoModal({
  error = null,
  isLoading = false,
  onConfirm,
  onOpenChange,
  open,
  repositoryName,
}: DeleteRepoModalProps) {
  const [confirmName, setConfirmName] = useState("");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!open) {
      setConfirmName("");
      setCopied(false);
    }
  }, [open]);

  const isConfirmed = confirmName.trim() === repositoryName;

  const handleCopyName = () => {
    navigator.clipboard.writeText(repositoryName);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isConfirmed && !isLoading) {
      await onConfirm();
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent title="Delete repository">
        <form className="space-y-4" onSubmit={handleSubmit}>
          <p className="text-sm leading-6 text-muted">
            Delete <strong className="text-foreground">{repositoryName}</strong> from
            GitVane and remove its local cloned files.
          </p>
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label
                className="block text-xs font-medium text-muted"
                htmlFor="confirm-repository-name"
              >
                Please type <span className="font-mono font-semibold text-foreground">{repositoryName}</span> to confirm:
              </label>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="h-6 px-1.5 text-[11px] gap-1 text-muted hover:text-foreground"
                onClick={handleCopyName}
                title="Copy repository name"
              >
                {copied ? (
                  <>
                    <Check className="size-3 text-emerald-500" />
                    <span className="text-emerald-500">Copied</span>
                  </>
                ) : (
                  <>
                    <Copy className="size-3" />
                    <span>Copy</span>
                  </>
                )}
              </Button>
            </div>
            <Input
              autoComplete="off"
              id="confirm-repository-name"
              onChange={(e) => setConfirmName(e.target.value)}
              placeholder={repositoryName}
              type="text"
              value={confirmName}
            />
          </div>
          {error ? <Notice tone="danger">{error}</Notice> : null}
          <div className="flex justify-end gap-2">
            <Button
              disabled={isLoading}
              onClick={() => onOpenChange(false)}
              type="button"
              variant="ghost"
            >
              Cancel
            </Button>
            <Button
              disabled={!isConfirmed || isLoading}
              type="submit"
              variant="danger"
            >
              Delete repository
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
