import { useState } from "react";
import { Link } from "react-router-dom";
import { Loader2, Target, ExternalLink } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Card, CardContent } from "@/components/ui/card";
import { AdminNav } from "@/components/AdminNav";
import { useCompactAdminList } from "@/hooks/useCompactAdminList";
import { useAdminLocation } from "@/hooks/useAdminLocation";
import { AdminPagination } from "@/components/admin/AdminPagination";
import { AdminFeedback } from "@/components/admin/AdminFeedback";
import { getApiErrorMessage } from "@/lib/api";
import { parseDateTime } from "@/lib/utils";
import { useAdminScans, useUpdateAdminScan } from "@/hooks/useAdmin";

import type { AdminScanItem } from "@/lib/structs";

export function AdminScans() {
  const compact = useCompactAdminList();
  const { params, page, update, setPage } = useAdminLocation();
  const activeFilter = params.get("status") ?? "all";
  const eligibleFilter = params.get("eligibility") ?? "all";
  const targetStatus = params.get("target_status");
  const pageSize = 50;
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [updatingScanId, setUpdatingScanId] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const isActiveParam =
    activeFilter === "all" ? undefined : activeFilter === "active";
  const isEligibleParam =
    eligibleFilter === "all" ? undefined : eligibleFilter === "eligible";

  const { data, isLoading, error, refetch } = useAdminScans({
    is_active: isActiveParam,
    is_eligible: isEligibleParam,
    limit: pageSize,
    offset: page * pageSize,
    target_status:
      targetStatus === "overdue" ||
      targetStatus === "active" ||
      targetStatus === "dormant"
        ? targetStatus
        : undefined,
  });

  const updateScanMutation = useUpdateAdminScan();

  const handleToggleScan = async (
    scanId: string,
    current: boolean,
    userScanningEnabled: boolean,
  ) => {
    if (!current && !userScanningEnabled) {
      setErrorMessage(
        "Cannot resume this scan while the owner’s scanning access is suspended.",
      );
      return;
    }
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      setUpdatingScanId(scanId);
      await updateScanMutation.mutateAsync({
        scanId,
        payload: { is_active: !current },
      });
      setSuccessMessage(
        current ? "Scan paused." : "Scan resumed and eligible for checks.",
      );
    } catch (err: unknown) {
      setErrorMessage(getApiErrorMessage(err));
    } finally {
      setUpdatingScanId(null);
    }
  };

  const renderRow = (s: AdminScanItem) => {
    const isUpdating = updatingScanId === s.id;
    const destination =
      s.destination_name || s.campground_name || "Unknown Destination";

    const owner = (
      <>
        <Link
          to={`/admin/users/${s.user_id}`}
          className="font-medium hover:underline text-foreground block"
        >
          {s.user_email}
        </Link>
        {!s.user_scanning_enabled && (
          <Badge variant="warning" className="text-[10px] mt-0.5">
            Scanning suspended
          </Badge>
        )}
      </>
    );
    const place = (
      <>
        <div className="font-medium">{destination}</div>
        <div className="text-xs text-muted-foreground">
          {s.provider_id === 1 ? "Recreation.gov" : `Provider ${s.provider_id}`}
          {s.destination_type === "recreation_area" && (
            <>
              {" · "}
              {s.coverage_mode === "all"
                ? "All campgrounds"
                : "Selected campgrounds"}
            </>
          )}
        </div>
      </>
    );
    const dates = `${s.start_date} → ${s.end_date}`;
    const setting = (
      <div className="flex items-center gap-2">
        <Switch
          aria-label={`Saved active scan for ${s.user_email} at ${destination}`}
          checked={s.is_active}
          disabled={isUpdating || updateScanMutation.isPending}
          onCheckedChange={() =>
            handleToggleScan(s.id, s.is_active, s.user_scanning_enabled)
          }
        />
        <span className="text-xs">{s.is_active ? "Active" : "Paused"}</span>
      </div>
    );
    const eligibility = s.is_eligible ? (
      <Badge variant="success" className="text-xs">
        Eligible
      </Badge>
    ) : (
      <Badge variant="secondary" className="text-xs">
        {s.user_scanning_enabled ? "Scan paused" : "Owner scanning suspended"}
      </Badge>
    );
    const lastChecked = s.last_checked_at ? (
      <>
        <time dateTime={s.last_checked_at}>
          {parseDateTime(s.last_checked_at).toLocaleString()}
        </time>
        <p className="text-muted-foreground">
          {Math.max(
            0,
            Math.floor(
              (Date.now() - parseDateTime(s.last_checked_at).getTime()) / 1000,
            ),
          )}
          s ago
        </p>
      </>
    ) : (
      "Never"
    );
    const target = (
      <Button asChild variant="ghost" size="sm" className="h-7 text-xs">
        <Link
          to={
            s.target_id
              ? `/admin/targets/${s.target_id}`
              : `/admin/scans/${s.id}`
          }
          className="gap-1"
        >
          <Target className="h-3 w-3 text-primary" /> Target
        </Link>
      </Button>
    );
    const actions = (
      <Button asChild variant="ghost" size="sm">
        <Link
          to={`/admin/scans/${s.id}`}
          className="inline-flex items-center gap-1"
        >
          Details <ExternalLink className="h-3 w-3" />
        </Link>
      </Button>
    );
    if (compact) {
      return (
        <li
          key={s.id}
          className="min-w-0 break-words space-y-2 p-4 [&_a]:min-h-11 [&_button:not([role=switch])]:min-h-11 [&_button[role=switch]]:relative [&_button[role=switch]]:before:absolute [&_button[role=switch]]:before:-inset-y-3 [&_button[role=switch]]:before:inset-x-0"
        >
          {place}
          {owner}
          <p className="text-sm">{dates}</p>
          <div className="flex flex-wrap items-center justify-between gap-3">
            {setting}
            {eligibility}
          </div>
          <div className="text-xs text-muted-foreground">
            Last checked {lastChecked}
          </div>
          <div className="flex items-center gap-2">
            {target}
            {actions}
          </div>
        </li>
      );
    }
    return (
      <tr key={s.id} className="hover:bg-muted/30 transition-colors">
        <td className="py-3 px-4">{owner}</td>
        <td className="py-3 px-4">{place}</td>
        <td className="py-3 px-4 text-xs whitespace-nowrap">{dates}</td>
        <td className="py-3 px-4">{setting}</td>
        <td className="py-3 px-4">{eligibility}</td>
        <td className="py-3 px-4 text-xs">{lastChecked}</td>
        <td className="py-3 px-4">{target}</td>
        <td className="py-3 px-4 text-right">{actions}</td>
      </tr>
    );
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-6xl">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-2">
        <div>
          <h1 className="text-3xl font-bold">Scan Management</h1>
          <p className="text-muted-foreground mt-1">
            Review all users’ scans, pause or resume them, and inspect shared
            targets.
          </p>
        </div>
      </div>

      <AdminNav />
      <AdminFeedback message={successMessage} />
      <p className="text-sm text-muted-foreground mb-4">
        Active is the saved scan setting. A scan is eligible for checks only
        when it is active and its owner has scanning access. Matching scans
        share a target.
      </p>
      <div className="mb-4 flex flex-wrap gap-2">
        {(["all", "overdue", "active", "dormant"] as const).map((value) => (
          <Button
            key={value}
            size="sm"
            variant={(targetStatus ?? "all") === value ? "default" : "outline"}
            onClick={() => update({ target_status: value })}
          >
            {value === "all"
              ? "All targets"
              : {
                  overdue: "Overdue for check",
                  active: "Eligible, not overdue",
                  dormant: "Dormant (no eligible scans)",
                }[value]}
          </Button>
        ))}
      </div>

      {errorMessage && (
        <div
          role="alert"
          className="mb-4 rounded-md bg-destructive/10 border border-destructive/30 p-3 text-destructive text-sm flex items-center justify-between"
        >
          <span>{errorMessage}</span>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setErrorMessage(null)}
          >
            Dismiss
          </Button>
        </div>
      )}

      {/* Filter Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <span>Scan setting:</span>
            <Button
              variant={activeFilter === "all" ? "default" : "outline"}
              size="sm"
              onClick={() => update({ status: "all" })}
            >
              All
            </Button>
            <Button
              variant={activeFilter === "active" ? "default" : "outline"}
              size="sm"
              onClick={() => update({ status: "active" })}
            >
              Active
            </Button>
            <Button
              variant={activeFilter === "paused" ? "default" : "outline"}
              size="sm"
              onClick={() => update({ status: "paused" })}
            >
              Paused
            </Button>
          </div>

          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <span>Eligible for checks:</span>
            <Button
              variant={eligibleFilter === "all" ? "default" : "outline"}
              size="sm"
              onClick={() => update({ eligibility: "all" })}
            >
              All
            </Button>
            <Button
              variant={eligibleFilter === "eligible" ? "default" : "outline"}
              size="sm"
              onClick={() => update({ eligibility: "eligible" })}
            >
              Eligible
            </Button>
            <Button
              variant={eligibleFilter === "ineligible" ? "default" : "outline"}
              size="sm"
              onClick={() => update({ eligibility: "ineligible" })}
            >
              Ineligible
            </Button>
          </div>
        </div>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : error || !data ? (
        <div className="rounded-md bg-destructive/10 p-6 text-center">
          <p className="text-destructive font-medium">Failed to load scans</p>
          <Button
            variant="outline"
            size="sm"
            className="mt-2"
            onClick={() => refetch()}
          >
            Retry
          </Button>
        </div>
      ) : data.scans.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            No scans found matching current filters.
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
            <ul aria-label="Scans" className="divide-y md:hidden">
              {data.scans.map(renderRow)}
            </ul>
          ) : (
            <div className="hidden overflow-x-auto md:block">
              <table className="w-full text-sm">
                <thead className="bg-muted/50 border-b">
                  <tr>
                    <th className="py-3 px-4 text-left font-medium">Owner</th>
                    <th className="py-3 px-4 text-left font-medium">
                      Campground
                    </th>
                    <th className="py-3 px-4 text-left font-medium">Dates</th>
                    <th className="py-3 px-4 text-left font-medium">
                      Scan setting
                    </th>
                    <th className="py-3 px-4 text-left font-medium">
                      Eligibility
                    </th>
                    <th className="py-3 px-4 text-left font-medium">
                      Last Checked
                    </th>
                    <th className="py-3 px-4 text-left font-medium">Target</th>
                    <th className="py-3 px-4 text-right font-medium">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y">{data.scans.map(renderRow)}</tbody>
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
