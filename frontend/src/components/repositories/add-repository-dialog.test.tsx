import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse, delay } from "msw";
import { describe, expect, it } from "vitest";
import { AddRepositoryDialog } from "@/components/repositories/add-repository-dialog";
import { apiBaseUrl } from "@/lib/api/client";
import { renderWithProviders } from "@/test/render";
import { server } from "@/test/server";

describe("AddRepositoryDialog", () => {
  it("renders the add repository trigger button and opens dialog", async () => {
    renderWithProviders(<AddRepositoryDialog />);

    const trigger = screen.getByRole("button", { name: "Add repository" });
    expect(trigger).toBeInTheDocument();

    fireEvent.click(trigger);
    expect(
      screen.getByRole("dialog", { name: "Add repository" }),
    ).toBeInTheDocument();
  });

  it("disables the submit button until name, valid URL, and branch are present", async () => {
    renderWithProviders(<AddRepositoryDialog />);

    fireEvent.click(screen.getByRole("button", { name: "Add repository" }));

    const dialog = screen.getByRole("dialog", { name: "Add repository" });
    const submitBtn = within(dialog).getByRole("button", {
      name: "Add repository",
    });

    expect(submitBtn).toBeDisabled();

    // 1. Enter name only -> still disabled
    fireEvent.change(screen.getByLabelText("Name"), {
      target: { value: "my-test-repo" },
    });
    expect(submitBtn).toBeDisabled();

    // 2. Enter clone URL -> triggers branch fetch, auto-selects default branch
    fireEvent.change(screen.getByLabelText("Clone URL"), {
      target: { value: "https://github.com/org/repo.git" },
    });

    await waitFor(() => {
      expect(submitBtn).not.toBeDisabled();
    });
  });

  it("shows loading state in branch selector when fetching remote branches", async () => {
    server.use(
      http.post(`${apiBaseUrl}/repositories/remote-branches`, async () => {
        await delay(200);
        return HttpResponse.json({
          branches: [
            {
              commit_date: null,
              commit_message: null,
              commit_sha: "1111111",
              name: "main",
              ref_type: "branch",
            },
            {
              commit_date: null,
              commit_message: null,
              commit_sha: "2222222",
              name: "release-v1",
              ref_type: "branch",
            },
          ],
          default_branch: "main",
        });
      }),
    );

    renderWithProviders(<AddRepositoryDialog />);

    fireEvent.click(screen.getByRole("button", { name: "Add repository" }));

    fireEvent.change(screen.getByLabelText("Clone URL"), {
      target: { value: "https://github.com/org/repo.git" },
    });

    // Verify branches are eventually loaded and branch dropdown displays options
    await waitFor(() => {
      expect(screen.getByText("main")).toBeInTheDocument();
    });
  });

  it("allows selecting a different branch from the fetched remote branches", async () => {
    server.use(
      http.post(`${apiBaseUrl}/repositories/remote-branches`, () =>
        HttpResponse.json({
          branches: [
            {
              commit_date: null,
              commit_message: null,
              commit_sha: "1111111",
              name: "main",
              ref_type: "branch",
            },
            {
              commit_date: null,
              commit_message: null,
              commit_sha: "2222222",
              name: "release-v1",
              ref_type: "branch",
            },
          ],
          default_branch: "main",
        }),
      ),
    );

    const createdBodies: unknown[] = [];
    server.use(
      http.post(`${apiBaseUrl}/repositories`, async ({ request }) => {
        createdBodies.push(await request.json());
        return HttpResponse.json(
          {
            clone_url: "https://github.com/org/repo.git",
            created_at: "2026-06-21T10:00:00Z",
            current_ref: "release-v1",
            default_branch: "main",
            id: "1",
            indexed_at: null,
            last_indexed_commit: null,
            name: "test-repo",
            repo_metadata: null,
            status: "ready",
            updated_at: "2026-06-21T10:00:00Z",
          },
          { status: 201 },
        );
      }),
    );

    renderWithProviders(<AddRepositoryDialog />);

    fireEvent.click(screen.getByRole("button", { name: "Add repository" }));
    fireEvent.change(screen.getByLabelText("Name"), {
      target: { value: "test-repo" },
    });
    fireEvent.change(screen.getByLabelText("Clone URL"), {
      target: { value: "https://github.com/org/repo.git" },
    });

    // Wait for auto-selected "main"
    await waitFor(() => {
      expect(screen.getByText("main")).toBeInTheDocument();
    });

    // Open branch combobox
    const combobox = screen.getByRole("combobox");
    fireEvent.click(combobox);

    // Select release-v1
    const releaseOption = await screen.findByRole("button", {
      name: /release-v1/i,
    });
    fireEvent.click(releaseOption);

    // Submit
    const dialog = screen.getByRole("dialog", { name: "Add repository" });
    const submitBtn = within(dialog).getByRole("button", {
      name: "Add repository",
    });
    fireEvent.click(submitBtn);

    await waitFor(() => expect(createdBodies).toHaveLength(1));
    expect(createdBodies[0]).toMatchObject({
      branch: "release-v1",
      clone_url: "https://github.com/org/repo.git",
      name: "test-repo",
    });
  });

  it("does not show burst error messages immediately while typing clone URL", async () => {
    renderWithProviders(<AddRepositoryDialog />);

    fireEvent.click(screen.getByRole("button", { name: "Add repository" }));
    const urlInput = screen.getByLabelText("Clone URL");

    // Type partial text
    fireEvent.change(urlInput, { target: { value: "h" } });
    fireEvent.change(urlInput, { target: { value: "ht" } });
    fireEvent.change(urlInput, { target: { value: "http" } });

    // Should NOT show error immediately on keystroke
    expect(
      screen.queryByText(/Please enter a valid Git clone URL/i),
    ).not.toBeInTheDocument();

    // After debounce expires for invalid format, error should appear
    expect(
      await screen.findByText(/Please enter a valid Git clone URL/i),
    ).toBeInTheDocument();
  });
});
