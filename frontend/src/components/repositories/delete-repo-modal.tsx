"use client";

import { useEffect, useState } from "react";
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

  useEffect(() => {
    if (!open) {
      setConfirmName("");
    }
  }, [open]);

  const isConfirmed = confirmName.trim() === repositoryName;

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
            RepoLens and ask the backend to remove its local clone.
          </p>
          <div className="space-y-2">
            <label
              className="block text-xs font-medium text-muted"
              htmlFor="confirm-repository-name"
            >
              Please type <span className="font-mono font-semibold text-foreground">{repositoryName}</span> to confirm:
            </label>
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
