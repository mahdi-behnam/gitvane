"use client";

import { Plus } from "lucide-react";
import { FormEvent, useId, useState } from "react";
import { normalizeApiError } from "@/lib/api/errors";
import type { RepositoryCreate } from "@/lib/api/types";
import { useCreateRepositoryMutation } from "@/store/api/repolensApi";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Notice } from "@/components/ui/notice";

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
  const [createRepository, createState] = useCreateRepositoryMutation();
  const formId = useId();

  const updateForm = <Field extends keyof FormState>(
    field: Field,
    value: FormState[Field],
  ) => {
    setForm((current) => ({ ...current, [field]: value }));
    setClientError(null);
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!form.cloneUrl.trim()) {
      setClientError("Provide a clone URL.");
      return;
    }

    const body: RepositoryCreate = {
      branch: form.branch.trim() || null,
      clone_url: form.cloneUrl.trim(),
      index_now: form.indexNow,
      name: form.name.trim(),
      pat: form.pat.trim() || null,
    };

    try {
      await createRepository(body).unwrap();
      setForm(initialState);
      setOpen(false);
    } catch {
      // The rendered mutation state below carries the normalized API message.
    }
  };

  const apiError = createState.error
    ? normalizeApiError(createState.error).message
    : null;
  const error = clientError ?? apiError;

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="primary">
          <Plus aria-hidden="true" className="size-4" />
          Add repository
        </Button>
      </DialogTrigger>
      <DialogContent title="Add repository">
        <form className="space-y-4" onSubmit={handleSubmit}>
          <label className="block text-sm font-medium" htmlFor={`${formId}-name`}>
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
            <label className="block text-sm font-medium" htmlFor={`${formId}-branch`}>
              Branch
            </label>
            <Input
              id={`${formId}-branch`}
              onChange={(event) => updateForm("branch", event.target.value)}
              placeholder="main"
              value={form.branch}
            />
          </div>

          <div className="space-y-2">
            <label className="block text-sm font-medium" htmlFor={`${formId}-pat`}>
              Personal Access Token (PAT) (Optional)
            </label>
            <Input
              id={`${formId}-pat`}
              onChange={(event) => updateForm("pat", event.target.value)}
              placeholder="ghp_..."
              type="password"
              value={form.pat}
            />
            <span className="block text-xs text-muted">Required for private repositories.</span>
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
            <Button onClick={() => setOpen(false)} type="button" variant="ghost">
              Cancel
            </Button>
            <Button disabled={createState.isLoading} type="submit" variant="primary">
              {createState.isLoading ? "Adding" : "Add repository"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
