"use client";

import type { FetchBaseQueryError } from "@reduxjs/toolkit/query";
import type { SerializedError } from "@reduxjs/toolkit";
import { Plus } from "lucide-react";
import { FormEvent, useEffect, useId, useState } from "react";
import { normalizeApiError } from "@/lib/api/errors";
import type { RepositoryCreate } from "@/lib/api/types";
import {
  useCreateRepositoryMutation,
  useListRemoteBranchesMutation,
} from "@/store/api/gitvaneApi";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Notice } from "@/components/ui/notice";
import { RefSelector } from "@/components/ui/ref-selector";
import type { SelectorOption } from "@/components/ui/selector";

type FormState = {
  branch: string;
  cloneUrl: string;
  indexNow: boolean;
  name: string;
  pat: string;
};

const initialState: FormState = {
  branch: "",
  cloneUrl: "",
  indexNow: false,
  name: "",
  pat: "",
};

export function AddRepositoryDialog() {
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState<FormState>(initialState);
  const [clientError, setClientError] = useState<string | null>(null);
  const [urlError, setUrlError] = useState<string | null>(null);
  const [branchOptions, setBranchOptions] = useState<SelectorOption[]>([]);

  const [createRepository, createState] = useCreateRepositoryMutation();
  const [listRemoteBranches, { isLoading: isFetchingBranches }] =
    useListRemoteBranchesMutation();
  const formId = useId();

  const handleOpenChange = (nextOpen: boolean) => {
    setOpen(nextOpen);
    if (!nextOpen) {
      setForm(initialState);
      setClientError(null);
      setUrlError(null);
      setBranchOptions([]);
    }
  };

  const updateForm = <Field extends keyof FormState>(
    field: Field,
    value: FormState[Field],
  ) => {
    setForm((current) => ({ ...current, [field]: value }));
    setClientError(null);
    if (field === "cloneUrl" || field === "pat") {
      // Clear URL error immediately while typing to avoid burst errors
      setUrlError(null);
    }
  };

  // Debounced remote branch fetching and URL validation
  useEffect(() => {
    const trimmedUrl = form.cloneUrl.trim();
    const trimmedPat = form.pat.trim();

    if (!trimmedUrl) {
      setBranchOptions([]);
      setUrlError(null);
      return;
    }

    const timer = setTimeout(async () => {
      // Basic sanity check before making API call
      const isLikelyValidUrl =
        trimmedUrl.startsWith("http://") ||
        trimmedUrl.startsWith("https://") ||
        trimmedUrl.startsWith("git@") ||
        trimmedUrl.startsWith("ssh://") ||
        /^[a-zA-Z0-9_-]+@[a-zA-Z0-9.-]+:/.test(trimmedUrl);

      if (!isLikelyValidUrl) {
        setUrlError(
          "Please enter a valid Git clone URL (e.g. https://github.com/org/repo.git).",
        );
        setBranchOptions([]);
        return;
      }

      try {
        const res = await listRemoteBranches({
          clone_url: trimmedUrl,
          pat: trimmedPat || null,
        }).unwrap();

        const options: SelectorOption[] = res.branches.map((b) => ({
          badge: b.name === res.default_branch ? "default" : undefined,
          badgeTone: b.name === res.default_branch ? "info" : undefined,
          description: b.commit_sha ? `Commit ${b.commit_sha}` : undefined,
          label: b.name,
          value: b.name,
        }));

        setBranchOptions(options);
        setUrlError(null);

        // Auto-select default branch if not already chosen or not in the returned list
        setForm((current) => {
          if (
            !current.branch ||
            !options.some((opt) => opt.value === current.branch)
          ) {
            const autoBranch =
              res.default_branch ||
              (options.length > 0 ? options[0].value : "");
            return { ...current, branch: autoBranch };
          }
          return current;
        });
      } catch (err: unknown) {
        const normalized = normalizeApiError(
          err as FetchBaseQueryError | SerializedError,
        );
        setUrlError(
          normalized.message ||
            "Unable to access repository or list branches. Please check the URL and access token.",
        );
        setBranchOptions([]);
      }
    }, 500);

    return () => clearTimeout(timer);
  }, [form.cloneUrl, form.pat, listRemoteBranches]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!form.name.trim()) {
      setClientError("Repository name is required.");
      return;
    }

    if (!form.cloneUrl.trim()) {
      setClientError("Provide a clone URL.");
      return;
    }

    if (!form.branch.trim()) {
      setClientError("Branch is required. Please select or enter a branch.");
      return;
    }

    if (urlError) {
      setClientError(urlError);
      return;
    }

    const body: RepositoryCreate = {
      branch: form.branch.trim(),
      clone_url: form.cloneUrl.trim(),
      index_now: form.indexNow,
      name: form.name.trim(),
      pat: form.pat.trim() || null,
    };

    try {
      await createRepository(body).unwrap();
      setForm(initialState);
      setBranchOptions([]);
      setUrlError(null);
      setOpen(false);
    } catch {
      // The rendered mutation state below carries the normalized API message.
    }
  };

  const apiError = createState.error
    ? normalizeApiError(createState.error).message
    : null;
  const error = clientError ?? urlError ?? apiError;

  const isSubmitDisabled =
    createState.isLoading ||
    isFetchingBranches ||
    !form.name.trim() ||
    !form.cloneUrl.trim() ||
    !form.branch.trim() ||
    Boolean(urlError);

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button variant="primary">
          <Plus aria-hidden="true" className="size-4" />
          Add repository
        </Button>
      </DialogTrigger>
      <DialogContent title="Add repository">
        <form className="space-y-4" onSubmit={handleSubmit}>
          <label
            className="block text-sm font-medium"
            htmlFor={`${formId}-name`}
          >
            Name
          </label>
          <Input
            id={`${formId}-name`}
            onChange={(event) => updateForm("name", event.target.value)}
            required
            value={form.name}
          />

          <div className="space-y-2">
            <label
              className="block text-sm font-medium"
              htmlFor={`${formId}-clone-url`}
            >
              Clone URL
            </label>
            <Input
              id={`${formId}-clone-url`}
              onChange={(event) => updateForm("cloneUrl", event.target.value)}
              placeholder="https://github.com/org/repo.git"
              required
              value={form.cloneUrl}
            />
          </div>

          <div className="space-y-2">
            <label
              className="block text-sm font-medium"
              htmlFor={`${formId}-branch`}
            >
              Branch
            </label>
            <RefSelector
              disabled={isFetchingBranches || !form.cloneUrl.trim()}
              id={`${formId}-branch`}
              loading={isFetchingBranches}
              onChange={(val) => updateForm("branch", String(val || ""))}
              options={branchOptions}
              placeholder={
                isFetchingBranches
                  ? "Loading available branches..."
                  : !form.cloneUrl.trim()
                    ? "Enter clone URL to load branches"
                    : branchOptions.length === 0
                      ? "No branches available"
                      : "Select branch..."
              }
              value={form.branch}
            />
          </div>

          <div className="space-y-2">
            <label
              className="block text-sm font-medium"
              htmlFor={`${formId}-pat`}
            >
              Personal Access Token (PAT) (Optional)
            </label>
            <Input
              id={`${formId}-pat`}
              onChange={(event) => updateForm("pat", event.target.value)}
              placeholder="ghp_..."
              type="password"
              value={form.pat}
            />
            <span className="block text-xs text-muted">
              Required for private repositories.
            </span>
          </div>

          <label className="flex items-start gap-3 text-sm text-muted">
            <input
              checked={form.indexNow}
              className="mt-1 rounded border-border text-primary focus:ring-primary"
              onChange={(event) => updateForm("indexNow", event.target.checked)}
              type="checkbox"
            />
            <span>Index after registration</span>
          </label>

          {error ? <Notice tone="danger">{error}</Notice> : null}

          <div className="flex justify-end gap-2">
            <Button
              onClick={() => handleOpenChange(false)}
              type="button"
              variant="ghost"
            >
              Cancel
            </Button>
            <Button disabled={isSubmitDisabled} type="submit" variant="primary">
              {createState.isLoading ? "Adding" : "Add repository"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
