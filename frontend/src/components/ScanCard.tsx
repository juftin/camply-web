import {
  Clock,
  Calendar,
  Activity,
  Zap,
  Trash2,
} from "lucide-react";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { toTitleCase } from "@/lib/utils";
import type { ScanResponse } from "@/lib/structs";

interface ScanCardProps {
  scan: ScanResponse;
  onToggleActive: (scanId: string, isActive: boolean) => void;
  onDelete: (scanId: string) => void;
  toggling?: boolean;
}

export function ScanCard({
  scan,
  onToggleActive,
  onDelete,
  toggling = false,
}: ScanCardProps) {
  const lastChecked = scan.last_checked_at
    ? formatRelativeTime(scan.last_checked_at)
    : "Never";

  const daysDiff = daysBetween(scan.start_date, scan.end_date);
  const isPastEnd = new Date(scan.end_date) < new Date();

  return (
    <Card
      className={`transition-all ${!scan.is_active ? "opacity-60" : ""} ${isPastEnd ? "ring-1 ring-yellow-400/30" : ""}`}
    >
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="min-w-0 flex-1 pr-2">
            <CardTitle className="text-base truncate">
              {toTitleCase(scan.campground_name || scan.recreation_area_name || "Unknown Campground")}
            </CardTitle>
            {scan.recreation_area_name && scan.campground_name && (
              <p className="text-xs text-muted-foreground truncate mt-0.5">
                {toTitleCase(scan.recreation_area_name)}
              </p>
            )}
          </div>
          <div className="flex items-center gap-1.5 shrink-0">
            {isPastEnd && (
              <Badge variant="warning" className="text-[10px] px-1.5 py-0">
                Ended
              </Badge>
            )}
            <Badge
              variant={scan.is_active ? "success" : "secondary"}
              className="text-[10px] px-1.5 py-0"
            >
              {scan.is_active ? "Active" : "Paused"}
            </Badge>
          </div>
        </div>
      </CardHeader>

      <CardContent className="pb-3 space-y-2">
        {/* Dates */}
        <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
          <Calendar className="h-3.5 w-3.5 shrink-0" />
          <span>
            {formatDate(scan.start_date)} – {formatDate(scan.end_date)}
            <span className="ml-1">({daysDiff} night{daysDiff !== 1 ? "s" : ""})</span>
          </span>
        </div>

        {/* Found count */}
        <div className="flex items-center gap-1.5 text-sm">
          <Activity className="h-3.5 w-3.5 shrink-0 text-primary" />
          <span>
            <strong className="text-foreground">{scan.found_count}</strong>{" "}
            <span className="text-muted-foreground">
              campsite{scan.found_count !== 1 ? "s" : ""} found
            </span>
          </span>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-1.5">
          {scan.require_electric && (
            <Badge variant="secondary" className="text-[10px] gap-0.5">
              <Zap className="h-3 w-3" /> Electric
            </Badge>
          )}
          {scan.min_stay_length > 1 && (
            <Badge variant="secondary" className="text-[10px]">
              Min {scan.min_stay_length} nights
            </Badge>
          )}
          {(scan.preferred_types ?? []).length > 0 && (
            <Badge variant="secondary" className="text-[10px]">
              {(scan.preferred_types ?? []).join(", ")}
            </Badge>
          )}
        </div>

        {/* Last checked */}
        <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <Clock className="h-3 w-3 shrink-0" />
          <span>Last checked: {lastChecked}</span>
        </div>
      </CardContent>

      <CardFooter className="border-t pt-3 flex justify-between">
        <div className="flex items-center gap-2">
          <Switch
            id={`active-${scan.id}`}
            checked={scan.is_active}
            onCheckedChange={(checked) => onToggleActive(scan.id, checked)}
            disabled={toggling}
          />
          <Label
            htmlFor={`active-${scan.id}`}
            className="text-xs text-muted-foreground cursor-pointer"
          >
            {scan.is_active ? "Active" : "Paused"}
          </Label>
        </div>
        <Button
          variant="ghost"
          size="sm"
          className="text-destructive hover:text-destructive hover:bg-destructive/10"
          onClick={() => onDelete(scan.id)}
        >
          <Trash2 className="h-3.5 w-3.5" />
        </Button>
      </CardFooter>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatDate(iso: string): string {
  const d = new Date(iso + "T00:00:00");
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function daysBetween(start: string, end: string): number {
  const s = new Date(start + "T00:00:00");
  const e = new Date(end + "T00:00:00");
  return Math.max(0, Math.round((e.getTime() - s.getTime()) / 86400000));
}

function formatRelativeTime(iso: string): string {
  const now = Date.now();
  const then = new Date(iso).getTime();
  const diffSec = Math.floor((now - then) / 1000);
  if (diffSec < 60) return `${diffSec}s ago`;
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`;
  return `${Math.floor(diffSec / 86400)}d ago`;
}
