import { useAdminLocation } from "@/hooks/useAdminLocation";
import { taskLabel } from "./labels";
import {
  AlertTriangle,
  BarChart2,
  LineChart as LineChartIcon,
  Loader2,
  Table as TableIcon,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAdminTrends } from "@/hooks/useAdmin";
import type { TrendMetric, TrendSeries } from "@/lib/structs";

interface AdminTrendsPanelProps {
  group: "usage" | "api" | "worker" | "provider";
  title?: string;
  description?: string;
  endpoint?: string;
  task_name?: string;
  provider?: string;
}

const SERIES_COLORS = [
  "#2563eb", // blue-600
  "#16a34a", // green-600
  "#d97706", // amber-600
  "#dc2626", // red-600
  "#9333ea", // purple-600
  "#0891b2", // cyan-600
  "#ea580c", // orange-600
  "#4f46e5", // indigo-600
];

const UNIT_LABELS: Record<string, string> = {
  "req/s": "requests / second",
  "errors/s": "errors / second",
  "tasks/min": "tasks / minute",
  "outcomes/min": "outcomes / minute",
  "targets/min": "targets / minute",
  "events/min": "events / minute",
  "checks/min": "checks / minute",
  ms: "milliseconds",
  "%": "percent",
};

function seriesLabel(series: TrendSeries): string {
  const labels = series.labels ?? {};
  if (labels.task_name) return taskLabel(labels.task_name);
  if (labels.provider) {
    const provider =
      labels.provider === "recreation_dot_gov"
        ? "Recreation.gov"
        : labels.provider;
    return labels.status ? `${provider} · ${labels.status}` : provider;
  }
  // Scrape labels identify sources; they are not the metric's meaning.
  const suffix = Object.entries(labels)
    .filter(([key]) => key !== "__name__")
    .map(([key, value]) => `${key}=${value}`)
    .join(", ");
  return suffix && series.name.endsWith(` (${suffix})`)
    ? series.name.slice(0, -suffix.length - 3)
    : series.name;
}

function formatValue(value: number): string {
  return value.toLocaleString(undefined, { maximumFractionDigits: 4 });
}

export function AdminTrendsPanel({
  group,
  title,
  description,
  endpoint,
  task_name,
  provider,
}: AdminTrendsPanelProps) {
  const { params, update } = useAdminLocation();
  const rangeParam = params.get(`${group}_range`);
  const range =
    rangeParam === "7d" || rangeParam === "30d" ? rangeParam : "24h";
  const viewMode = params.get(`${group}_view`) === "table" ? "table" : "charts";
  const timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone;

  const { data, isLoading, error, refetch, isFetching } = useAdminTrends({
    group,
    range,
    endpoint,
    task_name,
    provider,
  });

  const formatTimestamp = (iso: string) => {
    try {
      const d = new Date(iso);
      if (range === "24h") {
        return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
      }
      return d.toLocaleDateString([], { month: "short", day: "numeric" });
    } catch {
      return iso;
    }
  };

  const transformChartData = (metric: TrendMetric) => {
    if (!metric.series || metric.series.length === 0) return [];

    // Map timestamps to objects containing values for each series
    const dataMap: Record<string, Record<string, number | string | null>> = {};

    (metric.series ?? []).forEach((s, index) => {
      (s.points ?? []).forEach((p) => {
        const timeKey = p.timestamp;
        if (!dataMap[timeKey]) {
          dataMap[timeKey] = {
            timestamp: timeKey,
          };
        }
        dataMap[timeKey][`series_${index}`] = p.value;
      });
    });

    return Object.values(dataMap).sort(
      (a, b) =>
        new Date(a.timestamp as string).getTime() -
        new Date(b.timestamp as string).getTime(),
    );
  };

  return (
    <div className="space-y-4 my-6">
      {/* Control header: Range and Table/Chart toggle */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 p-3 bg-muted/40 rounded-lg border">
        <div>
          <div className="font-semibold text-sm flex items-center gap-2">
            <LineChartIcon className="h-4 w-4 text-primary" />
            {title ||
              `${{ usage: "Usage", api: "API", worker: "Worker", provider: "Booking provider" }[group]} trends`}
          </div>
          {description && (
            <p className="text-xs text-muted-foreground mt-0.5">
              {description}
            </p>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Range selection */}
          <div className="flex items-center space-x-1 border rounded-md p-0.5 bg-background">
            {(["24h", "7d", "30d"] as const).map((r) => (
              <Button
                key={r}
                size="sm"
                variant={range === r ? "default" : "ghost"}
                className="h-7 text-xs px-2.5"
                onClick={() => update({ [`${group}_range`]: r }, false)}
                aria-pressed={range === r}
              >
                {
                  {
                    "24h": "Last 24 hours",
                    "7d": "Last 7 days",
                    "30d": "Last 30 days",
                  }[r]
                }
              </Button>
            ))}
          </div>

          {/* Accessible Table vs Chart Toggle */}
          <div className="flex items-center space-x-1 border rounded-md p-0.5 bg-background">
            <Button
              size="sm"
              variant={viewMode === "charts" ? "default" : "ghost"}
              className="h-7 text-xs px-2"
              onClick={() => update({ [`${group}_view`]: "charts" }, false)}
              title="Chart visualization"
              aria-pressed={viewMode === "charts"}
            >
              <BarChart2 className="h-3.5 w-3.5 mr-1" /> Charts
            </Button>
            <Button
              size="sm"
              variant={viewMode === "table" ? "default" : "ghost"}
              className="h-7 text-xs px-2"
              onClick={() => update({ [`${group}_view`]: "table" }, false)}
              title="Accessible table view"
              aria-pressed={viewMode === "table"}
            >
              <TableIcon className="h-3.5 w-3.5 mr-1" /> Table
            </Button>
          </div>
        </div>
      </div>

      <div className="flex flex-wrap justify-between gap-2 text-xs text-muted-foreground">
        <span>
          Last updated:{" "}
          {data?.last_successful_at
            ? new Date(data.last_successful_at).toLocaleString()
            : "Not yet available"}
          {isFetching ? " • Updating" : ""}
          {error || data?.available === false ? " • Update unavailable" : ""}
        </span>
        <Button
          size="sm"
          variant="outline"
          disabled={isFetching}
          onClick={() => refetch()}
        >
          Refresh trends
        </Button>
      </div>
      <p className="text-xs text-muted-foreground">
        Times shown in {timeZone}.
        {data &&
          ` One data point every ${data.step_seconds >= 3600 ? `${data.step_seconds / 3600} ${data.step_seconds === 3600 ? "hour" : "hours"}` : `${data.step_seconds / 60} minutes`}.`}{" "}
        Rates are averages; gaps mean no measurements are available.
      </p>
      {/* Outage or Unavailable Notice */}
      {data && !data.available && (
        <div className="p-4 rounded-md bg-amber-500/10 border border-amber-500/30 text-amber-900 dark:text-amber-200 text-xs flex items-start gap-2">
          <AlertTriangle className="h-4 w-4 text-amber-600 shrink-0 mt-0.5" />
          <div>
            <span className="font-semibold">
              Prometheus monitoring unavailable:{" "}
            </span>
            <span>
              {data.metrics?.length
                ? "Showing the last successful snapshot. "
                : ""}
              {data.error_message ||
                "Unable to reach Prometheus server. Historical trends are currently offline."}
            </span>
          </div>
        </div>
      )}

      {error && (
        <div className="p-4 rounded-md bg-destructive/10 border border-destructive/20 text-destructive text-xs">
          Failed to load historical trends. Any displayed values are from the
          last successful response.{" "}
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            Retry
          </Button>
        </div>
      )}

      {isLoading ? (
        <div className="flex flex-col items-center justify-center p-12 text-muted-foreground border rounded-lg bg-card">
          <Loader2 className="h-8 w-8 animate-spin mb-2" />
          <span className="text-xs">Loading trend data...</span>
        </div>
      ) : data?.metrics && data.metrics.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {data.metrics.map((metric) => {
            const chartData = transformChartData(metric);
            const unit = UNIT_LABELS[metric.unit] ?? metric.unit;
            const labels = (metric.series ?? []).map(seriesLabel);
            const displayLabels = labels.map((label, index) => {
              const matchingIndices = labels
                .map((l, i) => (l === label ? i : -1))
                .filter((i) => i !== -1);
              if (matchingIndices.length <= 1) return label;

              const instances = matchingIndices.map(
                (i) => (metric.series ?? [])[i].labels?.instance,
              );
              const uniqueInstances = new Set(instances.filter(Boolean));
              const currentInstance = (metric.series ?? [])[index].labels
                ?.instance;

              if (
                uniqueInstances.size === matchingIndices.length &&
                currentInstance
              ) {
                return `${label} · ${currentInstance}`;
              }

              const workerOrPid =
                (metric.series ?? [])[index].labels?.worker ??
                (metric.series ?? [])[index].labels?.pid;
              if (workerOrPid) {
                return `${label} · worker ${workerOrPid}`;
              }

              const rank = matchingIndices.indexOf(index) + 1;
              return `${label} · source ${rank}`;
            });

            return (
              <Card key={metric.metric_id} className="overflow-hidden">
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-sm font-semibold">
                      {metric.title}
                    </CardTitle>
                    <Badge variant="outline" className="text-[11px] font-mono">
                      {unit}
                    </Badge>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {metric.description}
                  </p>
                </CardHeader>
                <CardContent className="pt-2">
                  {chartData.length === 0 ||
                  (viewMode === "charts" &&
                    !(metric.series ?? []).some((series) =>
                      (series.points ?? []).some(
                        (point) => point.value !== null,
                      ),
                    )) ? (
                    <div className="h-48 flex items-center justify-center text-xs text-muted-foreground border rounded-md border-dashed">
                      No measurements available for this time range.
                    </div>
                  ) : viewMode === "charts" ? (
                    <div className="h-56 w-full">
                      <ResponsiveContainer width="100%" height="100%">
                        {metric.chart_type === "bar" ? (
                          <BarChart data={chartData}>
                            <CartesianGrid
                              strokeDasharray="3 3"
                              opacity={0.3}
                            />
                            <XAxis
                              dataKey="timestamp"
                              tickFormatter={formatTimestamp}
                              tick={{ fontSize: 10 }}
                              stroke="#888888"
                            />
                            <YAxis
                              tick={{ fontSize: 10 }}
                              stroke="#888888"
                              tickFormatter={(value: number) =>
                                value.toLocaleString(undefined, {
                                  notation: "compact",
                                })
                              }
                            />
                            <Tooltip
                              formatter={(value, name) => [
                                value == null
                                  ? "No measurement"
                                  : `${formatValue(Number(value))} ${unit}`,
                                name,
                              ]}
                              labelFormatter={(label) =>
                                `${new Date(String(label)).toLocaleString()} (${timeZone})`
                              }
                              contentStyle={{
                                fontSize: "12px",
                                borderRadius: "6px",
                                backgroundColor: "rgba(255, 255, 255, 0.95)",
                                color: "#000",
                              }}
                            />
                            <Legend
                              wrapperStyle={{
                                fontSize: "11px",
                                paddingTop: "6px",
                              }}
                            />
                            {(metric.series ?? []).map((s, idx) => (
                              <Bar
                                key={s.name}
                                dataKey={`series_${idx}`}
                                name={displayLabels[idx]}
                                fill={SERIES_COLORS[idx % SERIES_COLORS.length]}
                              />
                            ))}
                          </BarChart>
                        ) : (
                          <LineChart data={chartData}>
                            <CartesianGrid
                              strokeDasharray="3 3"
                              opacity={0.3}
                            />
                            <XAxis
                              dataKey="timestamp"
                              tickFormatter={formatTimestamp}
                              tick={{ fontSize: 10 }}
                              stroke="#888888"
                            />
                            <YAxis
                              tick={{ fontSize: 10 }}
                              stroke="#888888"
                              tickFormatter={(value: number) =>
                                value.toLocaleString(undefined, {
                                  notation: "compact",
                                })
                              }
                            />
                            <Tooltip
                              formatter={(value, name) => [
                                value == null
                                  ? "No measurement"
                                  : `${formatValue(Number(value))} ${unit}`,
                                name,
                              ]}
                              labelFormatter={(label) =>
                                `${new Date(String(label)).toLocaleString()} (${timeZone})`
                              }
                              contentStyle={{
                                fontSize: "12px",
                                borderRadius: "6px",
                                backgroundColor: "rgba(255, 255, 255, 0.95)",
                                color: "#000",
                              }}
                            />
                            <Legend
                              wrapperStyle={{
                                fontSize: "11px",
                                paddingTop: "6px",
                              }}
                            />
                            {(metric.series ?? []).map((s, idx) => (
                              <Line
                                key={s.name}
                                type="linear"
                                connectNulls={false}
                                dataKey={`series_${idx}`}
                                name={displayLabels[idx]}
                                stroke={
                                  SERIES_COLORS[idx % SERIES_COLORS.length]
                                }
                                strokeWidth={2}
                                dot={false}
                              />
                            ))}
                          </LineChart>
                        )}
                      </ResponsiveContainer>
                    </div>
                  ) : (
                    /* Accessible Table Alternative */
                    <div className="overflow-x-auto max-h-56">
                      <table className="w-full text-xs text-left">
                        <thead className="bg-muted/50 sticky top-0">
                          <tr>
                            <th className="p-1.5 font-medium">
                              Time ({timeZone})
                            </th>
                            {(metric.series ?? []).map((s, seriesIndex) => (
                              <th
                                key={s.name}
                                className="p-1.5 font-medium text-right"
                              >
                                {displayLabels[seriesIndex]} ({unit})
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody className="divide-y">
                          {chartData.map((row, idx) => (
                            <tr key={idx} className="hover:bg-muted/20">
                              <td className="p-1.5 text-muted-foreground whitespace-nowrap">
                                {new Date(
                                  String(row.timestamp),
                                ).toLocaleString()}
                              </td>
                              {(metric.series ?? []).map((s, seriesIndex) => (
                                <td
                                  key={s.name}
                                  className="p-1.5 text-right font-mono"
                                >
                                  {row[`series_${seriesIndex}`] == null
                                    ? "No measurement"
                                    : formatValue(
                                        Number(row[`series_${seriesIndex}`]),
                                      )}
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      ) : (
        <div className="p-6 text-center text-xs text-muted-foreground border rounded-lg bg-card">
          No trend data is available for this category yet.
        </div>
      )}
    </div>
  );
}
