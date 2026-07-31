import { RepositoryManagementPage } from "@/components/repositories/repository-management-page";

/**
 * Repositories page component.
 * Uses DeleteRepoModal (via RepositoryManagementPage) for repository deletion confirmation.
 */
export default function RepositoriesPage() {
  return <RepositoryManagementPage />;
}
