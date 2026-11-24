import { Button } from "@/components/ui/button";

/** Navigate server-side pages without hiding records beyond the first response. */
export function AdminPagination({
  page,
  pageSize,
  total,
  onPage,
}: {
  page: number;
  pageSize: number;
  total: number;
  onPage: (page: number) => void;
}) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 p-3 text-xs text-muted-foreground border-t">
      <span>
        {total === 0
          ? "No records"
          : `Showing ${Math.min(page * pageSize + 1, total)}–${Math.min((page + 1) * pageSize, total)} of ${total}`}
      </span>
      <div className="flex gap-2">
        <Button
          variant="outline"
          size="sm"
          disabled={page === 0}
          onClick={() => onPage(page - 1)}
        >
          Previous
        </Button>
        <Button
          variant="outline"
          size="sm"
          disabled={(page + 1) * pageSize >= total}
          onClick={() => onPage(page + 1)}
        >
          Next
        </Button>
      </div>
    </div>
  );
}
