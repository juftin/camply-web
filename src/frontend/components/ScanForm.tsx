import { useState, useMemo, useEffect, type ReactNode } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Info, Loader2 } from "lucide-react";

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
import { AreaCoveragePicker } from "./AreaCoveragePicker";
import {
  DEFAULT_PROVIDER_FILTER_CAPABILITIES,
  useProviders,
} from "@/hooks/useProviders";
import { useCreateScan, useUpdateScan } from "@/hooks/useScans";
import { useAuth } from "@/hooks/useAuth";
import { getApiErrorMessage, searchCampgrounds } from "@/lib/api";
import type {
  Campground,
  ProviderFilterCapabilities,
  ScanResponse,
  SearchResult,
} from "@/lib/structs";
import { ALL_WEEKDAYS, WEEKDAY_NAMES, hasQualifyingStay } from "@/lib/weekdays";
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
    require_accessible: z.boolean().default(false),
    min_rv_length: z
      .union([
        z.literal(""),
        z.null(),
        z.undefined(),
        z.coerce
          .number()
          .int("Vehicle length must be a whole number of feet")
          .min(1, "Minimum RV length is 1 ft")
          .max(200, "Maximum RV length is 200 ft"),
      ])
      .transform((val): number | null =>
        val === "" || val == null ? null : val,
      )
      .default(null),
    preferred_types: z.array(z.string()).default([]),
    allowed_weekdays: z
      .array(z.number().int().min(0).max(6))
      .min(1, "Select at least one night."),
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
  )
  .refine(
    (data) => {
      if (
        !data.start_date ||
        !data.end_date ||
        data.end_date <= data.start_date ||
        !data.allowed_weekdays.length ||
        data.min_stay_length < 1
      )
        return true;
      return hasQualifyingStay(
        data.start_date,
        data.end_date,
        data.allowed_weekdays,
        data.min_stay_length,
      );
    },
    {
      message:
        "The remaining dates and selected nights cannot contain the requested consecutive stay. Extend the dates, select more nights, or reduce the stay length.",
      path: ["allowed_weekdays"],
    },
  );

type ScanFormValues = z.input<typeof scanFormSchema>;

interface ScanFormProps {
  /** Saved scan to edit; omitted when creating a scan. */
  scan?: ScanResponse;
  /** If a ParkSearch result was selected, pre-fill campground details. */
  preselectedCampground?: Campground;
  preselectedArea?: { id: string; name: string; provider_id: number };
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

const PROVIDER_FILTER_METADATA: ReadonlyArray<{
  key: keyof ProviderFilterCapabilities;
  label: string;
}> = [
  { key: "preferred_types", label: "Preferred Campsite Types" },
  { key: "require_electric", label: "Electric Hookup" },
  { key: "require_accessible", label: "ADA Accessible" },
  { key: "min_rv_length", label: "Minimum RV / Trailer Length" },
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function ScanForm({
  scan,
  preselectedCampground,
  preselectedArea,
  preselectedProviderId,
  onSuccess,
  trigger,
}: ScanFormProps) {
  const [open, setOpen] = useState(false);
  const initialCampground = scan
    ? {
        id: scan.recreation_area_id ?? scan.campground_id ?? "",
        name:
          scan.destination_name ??
          scan.campground_name ??
          scan.recreation_area_name,
      }
    : (preselectedArea ?? preselectedCampground ?? null);
  const [campground, setCampground] = useState<Pick<
    Campground,
    "id" | "name"
  > | null>(initialCampground);
  const [providerId, setProviderId] = useState<number>(
    scan?.provider_id ??
      preselectedArea?.provider_id ??
      preselectedProviderId ??
      0,
  );

  const initialKind =
    scan?.destination_type ??
    (preselectedArea ? "recreation_area" : "campground");
  const [destinationType, setDestinationType] = useState<
    "campground" | "recreation_area"
  >(initialKind);
  const [coverageMode, setCoverageMode] = useState<"all" | "selected">(
    scan?.coverage_mode ?? "all",
  );
  const savedChoices = Object.fromEntries(
    scan?.selected_campgrounds?.length
      ? scan.selected_campgrounds.map((item) => [item.id, item.name])
      : (scan?.campground_ids ?? []).map((id) => [
          id,
          (
            scan as import("@/lib/structs").ScanDetailResponse
          )?.campgrounds?.find((member) => member.campground_id === id)
            ?.campground_name ?? id,
        ]),
  );
  const [selectedChoices, setSelectedChoices] =
    useState<Record<string, string>>(savedChoices);
  useEffect(() => {
    if (preselectedArea) {
      setDestinationType("recreation_area");
      setCampground(preselectedArea);
      setProviderId(preselectedArea.provider_id);
      return;
    }
    if (preselectedCampground) {
      setDestinationType("campground");
      setCampground(preselectedCampground);
      setProviderId(preselectedProviderId ?? preselectedCampground.provider_id);
    }
  }, [preselectedArea, preselectedCampground, preselectedProviderId, open]);
  const [searchTerm, setSearchTerm] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [clearedFilters, setClearedFilters] = useState<string[]>([]);

  const { user } = useAuth();
  const { data: providers = [] } = useProviders(open);
  const createScan = useCreateScan();
  const updateScan = useUpdateScan();
  const isPending = createScan.isPending || updateScan.isPending;
  const defaultValues = {
    start_date: scan?.start_date ?? "",
    end_date: scan?.end_date ?? "",
    min_stay_length: scan?.min_stay_length ?? 1,
    require_electric: scan?.require_electric ?? false,
    require_accessible: scan?.require_accessible ?? false,
    min_rv_length: scan?.min_rv_length ?? ("" as unknown as number | null),
    preferred_types: scan?.preferred_types ?? [],
    allowed_weekdays: scan?.allowed_weekdays ?? ALL_WEEKDAYS,
  };
  const {
    register,
    handleSubmit,
    watch,
    getValues,
    setValue,
    reset,
    formState: { errors },
  } = useForm<ScanFormValues>({
    resolver: zodResolver(scanFormSchema) as never,
    defaultValues,
  });

  const hasCampground = campground !== null;
  const selectedProvider = useMemo(
    () => providers.find((p) => p.id === providerId),
    [providers, providerId],
  );
  const filterCaps = useMemo(
    () =>
      hasCampground
        ? (selectedProvider?.filter_capabilities ??
          DEFAULT_PROVIDER_FILTER_CAPABILITIES)
        : DEFAULT_PROVIDER_FILTER_CAPABILITIES,
    [hasCampground, selectedProvider],
  );
  const unsupportedFilterLabels = useMemo(
    () =>
      hasCampground
        ? PROVIDER_FILTER_METADATA.filter(({ key }) => !filterCaps[key]).map(
            ({ label }) => label,
          )
        : [],
    [hasCampground, filterCaps],
  );

  useEffect(() => {
    if (!open || !hasCampground || !selectedProvider?.filter_capabilities) {
      return;
    }
    const caps = selectedProvider.filter_capabilities;
    const cleared: string[] = [];
    if (
      !caps.preferred_types &&
      (getValues("preferred_types")?.length ?? 0) > 0
    ) {
      setValue("preferred_types", []);
      cleared.push("Preferred Campsite Types");
    }
    if (!caps.require_electric && getValues("require_electric")) {
      setValue("require_electric", false);
      cleared.push("Electric Hookup");
    }
    if (!caps.require_accessible && getValues("require_accessible")) {
      setValue("require_accessible", false);
      cleared.push("ADA Accessible");
    }
    const rvVal = getValues("min_rv_length");
    if (!caps.min_rv_length && rvVal != null && String(rvVal).trim() !== "") {
      setValue("min_rv_length", "" as unknown as number | null, {
        shouldValidate: true,
      });
      cleared.push("Minimum RV / Trailer Length");
    }
    if (cleared.length > 0) {
      setClearedFilters(cleared);
    }
  }, [open, hasCampground, selectedProvider, getValues, setValue]);

  useEffect(() => {
    register("start_date");
    register("end_date");
  }, [register]);

  const startDate = watch("start_date");
  const endDate = watch("end_date");
  const minStayLength = watch("min_stay_length") ?? 1;
  const preferredTypes = watch("preferred_types");
  const requireElectric = watch("require_electric");
  const requireAccessible = watch("require_accessible");
  const allowedWeekdays = watch("allowed_weekdays") ?? ALL_WEEKDAYS;

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
    setClearedFilters([]);
    setDestinationType(
      result.entity_type === "Campground" ? "campground" : "recreation_area",
    );
    setCoverageMode("all");
    setSelectedChoices({});
    setCampground({
      id: result.campground_id ?? result.recreation_area_id ?? "",
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

  const applyWeekendPreset = (weeksAhead: number = 0) => {
    const now = new Date();
    const dayOfWeek = now.getDay();
    let daysUntilFriday = (5 - dayOfWeek + 7) % 7;
    if (daysUntilFriday === 0 && weeksAhead === 0) {
      daysUntilFriday = 7;
    }
    const friday = new Date(now);
    friday.setDate(now.getDate() + daysUntilFriday + weeksAhead * 7);
    const sunday = new Date(friday);
    sunday.setDate(friday.getDate() + 2);

    const fmt = (d: Date) => d.toISOString().split("T")[0];
    setValue("start_date", fmt(friday), { shouldValidate: true });
    setValue("end_date", fmt(sunday), { shouldValidate: true });
  };

  // ---- Submit ----
  const onSubmit = async (data: ScanFormValues) => {
    if (isPending) return;
    if (!campground) {
      setError("Please select a campground first");
      return;
    }
    if (
      destinationType === "recreation_area" &&
      coverageMode === "selected" &&
      !Object.keys(selectedChoices).length
    ) {
      setError("Select at least one campground");
      return;
    }
    setError(null);
    try {
      const payload = {
        provider_id: providerId,
        ...(destinationType === "recreation_area"
          ? {
              destination_type: "recreation_area" as const,
              recreation_area_id: campground.id,
              coverage_mode: coverageMode,
              ...(coverageMode === "selected"
                ? { campground_ids: Object.keys(selectedChoices) }
                : {}),
            }
          : scan?.destination_type === "recreation_area"
            ? {
                destination_type: "campground" as const,
                campground_id: campground.id,
              }
            : { campground_id: campground.id }),
        start_date: data.start_date,
        end_date: data.end_date,
        min_stay_length: Number(data.min_stay_length),
        preferred_types: filterCaps.preferred_types ? data.preferred_types : [],
        require_electric: filterCaps.require_electric
          ? data.require_electric
          : false,
        require_accessible: filterCaps.require_accessible
          ? data.require_accessible
          : false,
        min_rv_length:
          !filterCaps.min_rv_length || data.min_rv_length == null
            ? null
            : Number(data.min_rv_length),
        allowed_weekdays: data.allowed_weekdays,
      };
      if (scan) {
        await updateScan.mutateAsync({
          scanId: scan.id,
          payload: {
            ...payload,
            ...(scan.row_version ? { row_version: scan.row_version } : {}),
          },
        });
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
      setDestinationType(initialKind);
      setCoverageMode(scan?.coverage_mode ?? "all");
      setSelectedChoices(savedChoices);
      setProviderId(
        scan?.provider_id ??
          preselectedArea?.provider_id ??
          preselectedProviderId ??
          0,
      );
      setClearedFilters([]);
      setSearchTerm("");
      setSearchResults([]);
    }
    setOpen(newOpen);
    if (!newOpen) {
      setClearedFilters([]);
      setError(null);
      setSearchError(null);
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        {trigger ?? <Button>{scan ? "Edit Scan" : "New Scan"}</Button>}
      </DialogTrigger>
      <DialogContent className="max-h-[calc(100dvh-2rem)] overflow-y-auto sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>{scan ? "Edit Scan" : "Create a New Scan"}</DialogTitle>
          <DialogDescription>
            {scan
              ? "Update your campground, dates, and campsite preferences."
              : "Monitor a campground or recreation area for cancellations."}
          </DialogDescription>
        </DialogHeader>

        <form
          onSubmit={handleSubmit(onSubmit)}
          noValidate
          className="space-y-4"
        >
          {/* ---- Campground selection ---- */}
          <div className="space-y-2">
            <Label htmlFor="campground-search">Destination</Label>
            {hasCampground ? (
              <div className="flex items-center justify-between rounded-md border p-3">
                <div>
                  <p className="font-medium">{campground.name}</p>
                  <p className="text-xs text-muted-foreground">
                    ID: {campground.id} &middot; Provider:{" "}
                    {selectedProvider?.name ?? providerId}
                  </p>
                </div>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setCampground(null);
                    setClearedFilters([]);
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
                          (r.entity_type === "Campground" && r.campground_id) ||
                          (r.entity_type === "RecreationArea" &&
                            r.recreation_area_id),
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
                            {r.campground_name ?? r.recreation_area_name}
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

          {destinationType === "recreation_area" && campground && (
            <AreaCoveragePicker
              key={`${providerId}:${campground.id}`}
              providerId={providerId}
              areaId={campground.id}
              mode={coverageMode}
              onModeChange={(mode) => {
                setCoverageMode(mode);
                if (mode === "all") setSelectedChoices({});
              }}
              selected={selectedChoices}
              onSelectedChange={setSelectedChoices}
            />
          )}
          {/* ---- Quick Presets ---- */}
          <div className="flex items-center gap-2 pt-1">
            <span className="text-xs text-muted-foreground font-medium">
              Quick Dates:
            </span>
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="h-7 text-xs px-2.5"
              onClick={() => applyWeekendPreset(0)}
            >
              Next Weekend
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="h-7 text-xs px-2.5"
              onClick={() => applyWeekendPreset(1)}
            >
              In 2 Weeks
            </Button>
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

          <fieldset
            className="space-y-2"
            aria-describedby="night-selection-help"
          >
            <legend className="text-sm font-medium">Nights of the week</legend>
            <div className="flex gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() =>
                  setValue("allowed_weekdays", [4, 5], { shouldValidate: true })
                }
              >
                Weekends
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() =>
                  setValue("allowed_weekdays", [...ALL_WEEKDAYS], {
                    shouldValidate: true,
                  })
                }
              >
                Any night
              </Button>
            </div>
            <div className="grid grid-cols-7 gap-1">
              {WEEKDAY_NAMES.map((name, day) => (
                <Button
                  key={name}
                  type="button"
                  variant={
                    allowedWeekdays.includes(day) ? "default" : "outline"
                  }
                  className="min-h-11 px-0 text-xs"
                  aria-label={name}
                  aria-pressed={allowedWeekdays.includes(day)}
                  onClick={() =>
                    setValue(
                      "allowed_weekdays",
                      allowedWeekdays.includes(day)
                        ? allowedWeekdays.filter((value) => value !== day)
                        : [...allowedWeekdays, day].sort((a, b) => a - b),
                      { shouldValidate: true },
                    )
                  }
                >
                  {name.slice(0, 3)}
                </Button>
              ))}
            </div>
            <p
              id="night-selection-help"
              className="text-xs text-muted-foreground"
            >
              Choose the nights you will stay. Friday and Saturday nights check
              out Sunday. Set a two-night minimum for a full weekend.
            </p>
            {errors.allowed_weekdays && (
              <p role="alert" className="text-xs text-destructive">
                {errors.allowed_weekdays.message}
              </p>
            )}
          </fieldset>

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
          {filterCaps.preferred_types && (
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
          )}

          {/* ---- Electric hookup ---- */}
          {filterCaps.require_electric && (
            <div className="flex items-center justify-between rounded-lg border p-3">
              <div>
                <Label htmlFor="require_electric">
                  Electric Hookup Required
                </Label>
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
          )}

          {/* ---- ADA Accessible ---- */}
          {filterCaps.require_accessible && (
            <div className="flex items-center justify-between rounded-lg border p-3">
              <div>
                <Label htmlFor="require_accessible">
                  ADA Accessible Required
                </Label>
                <p className="text-xs text-muted-foreground">
                  Only alert on ADA-accessible campsites
                </p>
              </div>
              <Switch
                id="require_accessible"
                checked={requireAccessible}
                onCheckedChange={(v) => setValue("require_accessible", v)}
              />
            </div>
          )}

          {/* ---- Minimum RV / Trailer length ---- */}
          {filterCaps.min_rv_length && (
            <div className="space-y-2">
              <Label htmlFor="min_rv_length">
                Minimum RV / Trailer Length (ft)
              </Label>
              <Input
                id="min_rv_length"
                type="number"
                min={1}
                max={200}
                step={1}
                placeholder="Any length"
                {...register("min_rv_length")}
              />
              {errors.min_rv_length?.message && (
                <p className="text-xs text-destructive">
                  {String(errors.min_rv_length.message)}
                </p>
              )}
            </div>
          )}

          {/* ---- Unsupported provider filters notice ---- */}
          {unsupportedFilterLabels.length > 0 && (
            <div
              role="status"
              className="flex items-start gap-2 rounded-md border bg-muted/50 p-3 text-xs text-muted-foreground"
            >
              <Info className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
              <div className="space-y-1">
                <p className="font-medium text-foreground">
                  Some filters aren&apos;t available for{" "}
                  {selectedProvider?.name ?? "this provider"}
                </p>
                <p>
                  Hidden because this provider doesn&apos;t report that site
                  metadata: {unsupportedFilterLabels.join(", ")}.
                </p>
                {clearedFilters.length > 0 && (
                  <p>
                    Cleared unsupported selection(s):{" "}
                    {clearedFilters.join(", ")}.
                  </p>
                )}
              </div>
            </div>
          )}

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
