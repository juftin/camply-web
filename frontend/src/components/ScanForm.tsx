import { useState, useMemo, useEffect, type ReactNode } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { DatePicker } from "@/components/ui/date-picker";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { useCreateScan, useUpdateScan } from "@/hooks/useScans";
import { useAuth } from "@/hooks/useAuth";
import { getApiErrorMessage, searchCampgrounds } from "@/lib/api";
import type { Campground, ScanResponse, SearchResult } from "@/lib/structs";
import {
  addDays,
  daysBetween,
  formatDisplayDate,
  getTodayString,
} from "@/lib/utils";

// ---------------------------------------------------------------------------
// Validation schema
// ---------------------------------------------------------------------------

const scanFormSchema = z
  .object({
    start_date: z.string().min(1, "Check-in date is required"),
    end_date: z.string().min(1, "Check-out date is required"),
    min_stay_length: z.coerce.number().int().min(1).default(1),
    require_electric: z.boolean().default(false),
    preferred_types: z.array(z.string()).default([]),
  })
  .refine(
    (data) => {
      if (!data.start_date || !data.end_date) return true;
      return new Date(data.end_date) > new Date(data.start_date);
    },
    {
      message: "Check-out must be after check-in",
      path: ["end_date"],
    },
  );

type ScanFormValues = z.input<typeof scanFormSchema>;

interface ScanFormProps {
  /** Saved scan to edit; omitted when creating a scan. */
  scan?: ScanResponse;
  /** If a ParkSearch result was selected, pre-fill campground details. */
  preselectedCampground?: Campground;
  preselectedProviderId?: number;
  /** Otherwise, allow searching from within the dialog. */
  /** Called after successfully saving. */
  onSuccess?: () => void;
  /** Trigger element (defaults to a "New Scan" button). */
  trigger?: ReactNode;
}

// ---------------------------------------------------------------------------
// Campsite type options
// ---------------------------------------------------------------------------

const CAMPSITE_TYPES = [
  { value: "TENT", label: "Tent" },
  { value: "RV", label: "RV" },
  { value: "CABIN", label: "Cabin" },
  { value: "OTHER", label: "Other" },
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function ScanForm({
  scan,
  preselectedCampground,
  preselectedProviderId,
  onSuccess,
  trigger,
}: ScanFormProps) {
  const [open, setOpen] = useState(false);
  const initialCampground = scan
    ? { id: scan.campground_id, name: scan.campground_name }
    : (preselectedCampground ?? null);
  const [campground, setCampground] = useState<Pick<
    Campground,
    "id" | "name"
  > | null>(initialCampground);
  const [providerId, setProviderId] = useState<number>(
    scan?.provider_id ?? preselectedProviderId ?? 0,
  );
  const [searchTerm, setSearchTerm] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const { user } = useAuth();
  const createScan = useCreateScan();
  const updateScan = useUpdateScan();
  const isPending = createScan.isPending || updateScan.isPending;
  const defaultValues = {
    start_date: scan?.start_date ?? "",
    end_date: scan?.end_date ?? "",
    min_stay_length: scan?.min_stay_length ?? 1,
    require_electric: scan?.require_electric ?? false,
    preferred_types: scan?.preferred_types ?? [],
  };
  const {
    register,
    handleSubmit,
    watch,
    setValue,
    reset,
    formState: { errors },
  } = useForm<ScanFormValues>({
    resolver: zodResolver(scanFormSchema) as never,
    defaultValues,
  });

  useEffect(() => {
    register("start_date");
    register("end_date");
  }, [register]);

  const startDate = watch("start_date");
  const endDate = watch("end_date");
  const minStayLength = watch("min_stay_length") ?? 1;
  const preferredTypes = watch("preferred_types");
  const requireElectric = watch("require_electric");

  const todayStr = useMemo(() => getTodayString(), []);
  const minEndDate = useMemo(() => {
    if (!startDate) return todayStr;
    return addDays(startDate, 1);
  }, [startDate, todayStr]);

  const handleStartDateChange = (newStartDate: string) => {
    setValue("start_date", newStartDate, { shouldValidate: true });
    if (!newStartDate) return;

    // Use start date as input: if end date is empty or on/before the start date,
    // advance end date to start date + min stay length (or 1 night).
    if (!endDate || endDate <= newStartDate) {
      const stay = Math.max(1, Number(minStayLength) || 1);
      setValue("end_date", addDays(newStartDate, stay), {
        shouldValidate: true,
      });
    }
  };

  const handleEndDateChange = (newEndDate: string) => {
    setValue("end_date", newEndDate, { shouldValidate: true });
  };

  const hasValidRange = Boolean(startDate && endDate && endDate > startDate);
  const nights = hasValidRange ? daysBetween(startDate, endDate) : 0;

  // ---- Campground search ----
  const handleSearch = async (term: string) => {
    setSearchTerm(term);
    if (term.length < 2) {
      setSearchResults([]);
      setSearchError(null);
      return;
    }
    setSearching(true);
    setSearchError(null);
    try {
      const results = await searchCampgrounds(term);
      setSearchResults(results);
    } catch (err) {
      setSearchError(getApiErrorMessage(err));
    } finally {
      setSearching(false);
    }
  };

  const selectCampground = (result: SearchResult) => {
    setCampground({
      id: result.campground_id ?? "",
      name: result.campground_name ?? result.recreation_area_name ?? "",
    });
    setProviderId(result.provider_id);
    setSearchTerm(result.campground_name ?? result.recreation_area_name ?? "");
    setSearchResults([]);
  };

  const toggleType = (type: string) => {
    const current = preferredTypes ?? [];
    if (current.includes(type)) {
      setValue(
        "preferred_types",
        current.filter((t) => t !== type),
      );
    } else {
      setValue("preferred_types", [...current, type]);
    }
  };

  // ---- Submit ----
  const onSubmit = async (data: ScanFormValues) => {
    if (isPending) return;
    if (!campground) {
      setError("Please select a campground first");
      return;
    }
    setError(null);
    try {
      const payload = {
        provider_id: providerId,
        campground_id: campground.id,
        start_date: data.start_date,
        end_date: data.end_date,
        min_stay_length: Number(data.min_stay_length),
        preferred_types: data.preferred_types,
        require_electric: data.require_electric,
      };
      if (scan) {
        await updateScan.mutateAsync({ scanId: scan.id, payload });
      } else {
        await createScan.mutateAsync(payload);
      }
      reset();
      setCampground(null);
      setSearchTerm("");
      setOpen(false);
      onSuccess?.();
    } catch (err) {
      setError(getApiErrorMessage(err));
    }
  };

  const handleOpenChange = (newOpen: boolean) => {
    if (isPending) return;
    if (newOpen) {
      reset(defaultValues);
      setCampground(initialCampground);
      setProviderId(scan?.provider_id ?? preselectedProviderId ?? 0);
      setSearchTerm("");
      setSearchResults([]);
    }
    setOpen(newOpen);
    if (!newOpen) {
      setError(null);
      setSearchError(null);
    }
  };

  // ---- Derived ----
  const hasCampground = campground !== null;

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        {trigger ?? <Button>{scan ? "Edit Scan" : "New Scan"}</Button>}
      </DialogTrigger>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>{scan ? "Edit Scan" : "Create a New Scan"}</DialogTitle>
          <DialogDescription>
            {scan
              ? "Update your campground, dates, and campsite preferences."
              : "Monitor a campground for cancellations."}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {/* ---- Campground selection ---- */}
          <div className="space-y-2">
            <Label htmlFor="campground-search">Campground</Label>
            {hasCampground ? (
              <div className="flex items-center justify-between rounded-md border p-3">
                <div>
                  <p className="font-medium">{campground.name}</p>
                  <p className="text-xs text-muted-foreground">
                    ID: {campground.id} &middot; Provider: {providerId}
                  </p>
                </div>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setCampground(null);
                    setSearchTerm("");
                  }}
                >
                  Change
                </Button>
              </div>
            ) : (
              <div className="space-y-2">
                <Input
                  id="campground-search"
                  placeholder="Search for a campground..."
                  value={searchTerm}
                  onChange={(e) => handleSearch(e.target.value)}
                />
                {searching && (
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Loader2 className="h-3 w-3 animate-spin" />
                    Searching...
                  </div>
                )}
                {searchError && (
                  <p className="text-sm text-destructive">{searchError}</p>
                )}
                {searchResults.length > 0 && (
                  <div className="max-h-40 overflow-y-auto rounded-md border">
                    {searchResults
                      .filter(
                        (r) =>
                          r.entity_type === "Campground" && r.campground_id,
                      )
                      .slice(0, 10)
                      .map((r) => (
                        <button
                          key={r.id}
                          type="button"
                          className="w-full px-3 py-2 text-left text-sm hover:bg-muted border-b last:border-b-0"
                          onClick={() => selectCampground(r)}
                        >
                          <span className="font-medium">
                            {r.campground_name}
                          </span>
                          {r.recreation_area_name && (
                            <span className="ml-1 text-muted-foreground">
                              &mdash; {r.recreation_area_name}
                            </span>
                          )}
                        </button>
                      ))}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* ---- Date range ---- */}
          <div className="space-y-2">
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label htmlFor="start_date">Check-in</Label>
                <DatePicker
                  id="start_date"
                  name="start_date"
                  value={startDate}
                  onChange={handleStartDateChange}
                  minDate={todayStr}
                  placeholder="Select check-in"
                  error={!!errors.start_date}
                />
                {errors.start_date && (
                  <p className="text-xs text-destructive">
                    {errors.start_date.message}
                  </p>
                )}
              </div>
              <div className="space-y-1">
                <Label htmlFor="end_date">Check-out</Label>
                <DatePicker
                  id="end_date"
                  name="end_date"
                  value={endDate}
                  onChange={handleEndDateChange}
                  minDate={minEndDate}
                  defaultMonth={startDate || todayStr}
                  startDate={startDate}
                  placeholder="Select check-out"
                  error={!!errors.end_date}
                  align="right"
                />
                {errors.end_date && (
                  <p className="text-xs text-destructive">
                    {errors.end_date.message}
                  </p>
                )}
              </div>
            </div>

            {/* Stay duration preview */}
            {hasValidRange && (
              <div className="flex items-center justify-between rounded-md bg-muted/60 px-3 py-1.5 text-xs text-muted-foreground">
                <span className="font-medium text-foreground">
                  {nights} {nights === 1 ? "night" : "nights"}
                </span>
                <span>
                  {formatDisplayDate(startDate, false)} &ndash;{" "}
                  {formatDisplayDate(endDate, false)}
                </span>
              </div>
            )}
          </div>

          {/* ---- Min stay ---- */}
          <div className="space-y-1">
            <Label htmlFor="min_stay_length">Minimum Stay (nights)</Label>
            <Input
              id="min_stay_length"
              type="number"
              min={1}
              {...register("min_stay_length", {
                onChange: (e) => {
                  const val = Number(e.target.value);
                  if (startDate && val > 0) {
                    const currentNights = endDate
                      ? daysBetween(startDate, endDate)
                      : 0;
                    if (currentNights < val) {
                      setValue("end_date", addDays(startDate, val), {
                        shouldValidate: true,
                      });
                    }
                  }
                },
              })}
            />
          </div>

          {/* ---- Preferred types ---- */}
          <div className="space-y-2">
            <Label>Preferred Campsite Types</Label>
            <div className="flex flex-wrap gap-2">
              {CAMPSITE_TYPES.map((t) => (
                <Badge
                  key={t.value}
                  variant={
                    preferredTypes?.includes(t.value) ? "default" : "outline"
                  }
                  className="cursor-pointer"
                  onClick={() => toggleType(t.value)}
                >
                  {t.label}
                </Badge>
              ))}
            </div>
          </div>

          {/* ---- Electric hookup ---- */}
          <div className="flex items-center justify-between rounded-lg border p-3">
            <div>
              <Label htmlFor="require_electric">Electric Hookup Required</Label>
              <p className="text-xs text-muted-foreground">
                Only alert if the site has electric hookup
              </p>
            </div>
            <Switch
              id="require_electric"
              checked={requireElectric}
              onCheckedChange={(v) => setValue("require_electric", v)}
            />
          </div>

          {/* ---- Error ---- */}
          {error && (
            <div
              role="alert"
              className="rounded-md bg-destructive/10 p-3 text-sm text-destructive"
            >
              {error}
            </div>
          )}

          {/* ---- Suspension Alert ---- */}
          {user?.scanning_enabled === false && (
            <div className="rounded-md bg-amber-500/10 border border-amber-500/30 p-3 text-sm text-amber-800 dark:text-amber-200">
              Scanning is currently disabled for your account. Please contact an
              administrator to re-enable scanning.
            </div>
          )}

          {/* ---- Footer ---- */}
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              disabled={isPending}
              onClick={() => handleOpenChange(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={
                isPending ||
                !hasCampground ||
                (!scan && user?.scanning_enabled === false)
              }
            >
              {isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  {scan ? "Saving..." : "Creating..."}
                </>
              ) : scan ? (
                "Save Changes"
              ) : (
                "Create Scan"
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
