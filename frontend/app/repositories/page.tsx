import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeaderCell,
  TableRow,
} from "@/components/ui/table";

export default function RepositoriesPage() {
  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <div className="flex flex-col gap-4 border-b border-border pb-6 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-3xl font-semibold md:text-4xl">Repositories</h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-muted">
            Registered repositories will be listed here after the API layer is
            connected.
          </p>
        </div>
        <Button variant="primary">
          <Plus aria-hidden="true" className="size-4" />
          Add repository
        </Button>
      </div>

      <Card>
        <CardHeader>
          <h2 className="text-sm font-semibold">Repository inventory</h2>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHead>
              <TableRow>
                <TableHeaderCell>Name</TableHeaderCell>
                <TableHeaderCell>Status</TableHeaderCell>
                <TableHeaderCell>Branch</TableHeaderCell>
                <TableHeaderCell>Last indexed</TableHeaderCell>
              </TableRow>
            </TableHead>
            <TableBody>
              <TableRow>
                <TableCell colSpan={4}>
                  <EmptyState
                    className="m-4 border-0 bg-panel-muted"
                    description="Add a repository once the creation workflow is connected to the backend."
                    title="No repository records"
                  />
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
