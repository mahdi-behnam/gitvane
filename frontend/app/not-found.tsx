import { HelpCircle } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";

export default function NotFound() {
  return (
    <div className="flex min-h-[50vh] items-center justify-center p-4 md:p-8">
      <Card className="w-full max-w-md">
        <CardHeader className="flex flex-col items-center border-b-0 pb-2 text-center">
          <div className="mb-4 grid size-12 place-items-center rounded-lg border border-border bg-panel-muted text-primary">
            <HelpCircle className="size-6" />
          </div>
          <h2 className="text-xl font-semibold tracking-tight text-foreground">
            404 - Page Not Found
          </h2>
          <p className="mt-2 text-sm text-muted">
            We couldn&apos;t find the page you&apos;re looking for.
          </p>
        </CardHeader>
        <CardContent className="flex justify-center pt-4">
          <Button asChild className="w-full" variant="primary">
            <Link href="/repositories">Go to Repositories</Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
