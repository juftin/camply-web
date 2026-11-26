import { useState } from "react";
import { Link } from "react-router-dom";
import {
  Search,
  Loader2,
  Mail,
  ExternalLink,
  Check,
  X,
  Ban,
} from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { AdminNav } from "@/components/AdminNav";
import { useCompactAdminList } from "@/hooks/useCompactAdminList";
import { useAdminLocation } from "@/hooks/useAdminLocation";
import { AdminPagination } from "@/components/admin/AdminPagination";
import { AdminFeedback } from "@/components/admin/AdminFeedback";
import { getApiErrorMessage } from "@/lib/api";
import {
  useAdminAccessRequests,
  useUpdateAdminAccessRequest,
} from "@/hooks/useAdmin";
import type { AdminAccessRequestItem } from "@/lib/structs";

type StatusFilter = "all" | "pending" | "approved" | "rejected";

const STATUS_BADGE_VARIANT: Record<
  AdminAccessRequestItem["status"],
  "warning" | "success" | "destructive"
> = {
  pending: "warning",
  approved: "success",
  rejected: "destructive",
};

const STATUS_FILTERS: { value: StatusFilter; label: string }[] = [
  { value: "all", label: "All" },
  { value: "pending", label: "Pending" },
  { value: "approved", label: "Approved" },
  { value: "rejected", label: "Rejected" },
];

export function AdminInvites() {
  const compact = useCompactAdminList();
  const { params, page, update, setPage } = useAdminLocation();
  const search = params.get("search") ?? "";
  const rawStatus = params.get("status") ?? "all";
  const filter: StatusFilter =
    rawStatus === "pending" ||
    rawStatus === "approved" ||
    rawStatus === "rejected"
      ? rawStatus
      : "all";

  const [message, setMessage] = useState<string | null>(null);
  const [actionError, setActionError] = useState(false);
  const [updatingRequestId, setUpdatingRequestId] = useState<string | null>(
    null,
  );
  const pageSize = 50;

  const { data, isLoading, error, refetch } = useAdminAccessRequests({
    status: filter === "all" ? undefined : filter,
    search: search.trim() || undefined,
    limit: pageSize,
    offset: page * pageSize,
  });

  const updateMutation = useUpdateAdminAccessRequest();

  const handleUpdateStatus = async (
    item: AdminAccessRequestItem,
    nextStatus: "approved" | "rejected",
    actionVerb: "approved" | "rejected" | "revoked",
  ) => {
    setMessage(null);
    setActionError(false);
    try {
      setUpdatingRequestId(item.id);
      await updateMutation.mutateAsync({
        requestId: item.id,
        payload: { status: nextStatus },
      });
      if (actionVerb === "approved") {
        setMessage(`Approved invitation request for ${item.email}.`);
      } else if (actionVerb === "revoked") {
        setMessage(`Revoked invitation for ${item.email}.`);
      } else {
        setMessage(`Rejected invitation request for ${item.email}.`);
      }
    } catch (err) {
      setActionError(true);
      setMessage(getApiErrorMessage(err));
    } finally {
      setUpdatingRequestId(null);
    }
  };

  const renderRow = (item: AdminAccessRequestItem) => {
    const isUpdating = updatingRequestId === item.id;
    const disabled = isUpdating || updateMutation.isPending;

    const email = (
      <div className="break-words font-medium text-foreground">
        {item.email}
      </div>
    );
    const name = item.name || "—";
    const status = (
      <Badge variant={STATUS_BADGE_VARIANT[item.status]} className="capitalize">
        {item.status}
      </Badge>
    );
    const requested = new Date(item.created_at).toLocaleString();
    const reviewed = item.reviewed_at
      ? new Date(item.reviewed_at).toLocaleString()
      : "—";
    const user = item.user_id ? (
      <Link
        to={`/admin/users/${item.user_id}`}
        className="inline-flex items-center gap-1 text-primary hover:underline font-medium"
      >
        View User <ExternalLink className="h-3 w-3" />
      </Link>
    ) : (
      <span className="text-muted-foreground">—</span>
    );
    const actions = (
      <div className="flex flex-wrap items-center md:justify-end gap-2">
        {item.status === "pending" && (
          <>
            <Button
              size="sm"
              variant="default"
              className="gap-1"
              disabled={disabled}
              onClick={() => handleUpdateStatus(item, "approved", "approved")}
            >
              <Check className="h-3.5 w-3.5" />
              Approve
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="gap-1"
              disabled={disabled}
              onClick={() => handleUpdateStatus(item, "rejected", "rejected")}
            >
              <X className="h-3.5 w-3.5" />
              Reject
            </Button>
          </>
        )}
        {item.status === "approved" && (
          <Button
            size="sm"
            variant="outline"
            className="gap-1 text-destructive hover:text-destructive"
            disabled={disabled}
            onClick={() => handleUpdateStatus(item, "rejected", "revoked")}
          >
            <Ban className="h-3.5 w-3.5" />
            Revoke
          </Button>
        )}
        {item.status === "rejected" && (
          <Button
            size="sm"
            variant="outline"
            className="gap-1"
            disabled={disabled}
            onClick={() => handleUpdateStatus(item, "approved", "approved")}
          >
            <Check className="h-3.5 w-3.5" />
            Approve
          </Button>
        )}
      </div>
    );
    if (compact) {
      return (
        <li
          key={item.id}
          className="min-w-0 break-words space-y-2 p-4 [&_a]:min-h-11 [&_button]:min-h-11"
        >
          <div className="flex flex-wrap items-start justify-between gap-2">
            {email}
            {status}
          </div>
          <p className="text-sm text-muted-foreground">{name}</p>
          <p className="text-xs text-muted-foreground">Requested {requested}</p>
          {item.reviewed_at && (
            <p className="text-xs text-muted-foreground">Reviewed {reviewed}</p>
          )}
          {item.user_id && user}
          {actions}
        </li>
      );
    }
    return (
      <tr key={item.id} className="hover:bg-muted/30 transition-colors">
        <td className="py-3 px-4">{email}</td>
        <td className="py-3 px-4 text-muted-foreground">{name}</td>
        <td className="py-3 px-4">{status}</td>
        <td className="py-3 px-4 text-xs text-muted-foreground whitespace-nowrap">
          {requested}
        </td>
        <td className="py-3 px-4 text-xs text-muted-foreground whitespace-nowrap">
          {reviewed}
        </td>
        <td className="py-3 px-4 text-xs">{user}</td>
        <td className="py-3 px-4 text-right">{actions}</td>
      </tr>
    );
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-6xl">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-2">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Mail className="h-7 w-7 text-primary" /> Invitation Requests
          </h1>
          <p className="text-muted-foreground mt-1">
            Review access requests, approve invitations, or revoke previously
            approved access.
          </p>
        </div>
      </div>

      <AdminNav />
      <AdminFeedback message={message} error={actionError} />

      {/* Filters and Search */}
      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search by email or name..."
            value={search}
            onChange={(e) => update({ search: e.target.value })}
            className="pl-9"
          />
        </div>
        <div className="flex flex-wrap gap-2 [&>button]:min-h-11 sm:[&>button]:min-h-0">
          {STATUS_FILTERS.map((opt) => (
            <Button
              key={opt.value}
              variant={filter === opt.value ? "default" : "outline"}
              size="sm"
              onClick={() => update({ status: opt.value })}
            >
              {opt.label}
            </Button>
          ))}
        </div>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : error || !data ? (
        <div className="rounded-md bg-destructive/10 p-6 text-center">
          <p className="text-destructive font-medium">
            Failed to load invitation requests
          </p>
          <Button
            variant="outline"
            size="sm"
            className="mt-2"
            onClick={() => refetch()}
          >
            Retry
          </Button>
        </div>
      ) : data.access_requests.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            No invitation requests found matching your criteria.
          </CardContent>
          <AdminPagination
            page={page}
            pageSize={pageSize}
            total={data.total}
            onPage={setPage}
          />
        </Card>
      ) : (
        <div className="min-w-0 rounded-md border bg-card overflow-hidden">
          {compact ? (
            <ul aria-label="Invitations" className="divide-y md:hidden">
              {data.access_requests.map(renderRow)}
            </ul>
          ) : (
            <div className="hidden overflow-x-auto md:block">
              <table className="w-full text-sm">
                <thead className="bg-muted/50 border-b">
                  <tr>
                    <th className="py-3 px-4 text-left font-medium">Email</th>
                    <th className="py-3 px-4 text-left font-medium">Name</th>
                    <th className="py-3 px-4 text-left font-medium">Status</th>
                    <th className="py-3 px-4 text-left font-medium">
                      Requested
                    </th>
                    <th className="py-3 px-4 text-left font-medium">
                      Reviewed
                    </th>
                    <th className="py-3 px-4 text-left font-medium">
                      Linked User
                    </th>
                    <th className="py-3 px-4 text-right font-medium">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {data.access_requests.map(renderRow)}
                </tbody>
              </table>
            </div>
          )}
          <AdminPagination
            page={page}
            pageSize={pageSize}
            total={data.total}
            onPage={setPage}
          />
        </div>
      )}
    </div>
  );
}
