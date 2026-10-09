import { useState } from "react";
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
import type { TrendMetric } from "@/lib/structs";

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

export function AdminTrendsPanel({
  group,
  title,
  description,
  endpoint,
  task_name,
  provider,
}: AdminTrendsPanelProps) {
  const [range, setRange] = useState<"24h" | "7d" | "30d">("24h");
  const [viewMode, setViewMode] = useState<"charts" | "table">("charts");

  const { data, isLoading, error } = useAdminTrends({
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
    const dataMap: Record<string, Record<string, number | string>> = {};

    metric.series.forEach((s) => {
      s.points.forEach((p) => {
        const timeKey = p.timestamp;
        if (!dataMap[timeKey]) {
          dataMap[timeKey] = {
            timestamp: timeKey,
            formattedTime: formatTimestamp(timeKey),
          };
        }
        dataMap[timeKey][s.name] = p.value;
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
            {title || `${group.toUpperCase()} Historical Trends`}
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
                onClick={() => setRange(r)}
              >
                {r}
              </Button>
            ))}
          </div>

          {/* Accessible Table vs Chart Toggle */}
          <div className="flex items-center space-x-1 border rounded-md p-0.5 bg-background">
            <Button
              size="sm"
              variant={viewMode === "charts" ? "default" : "ghost"}
              className="h-7 text-xs px-2"
              onClick={() => setViewMode("charts")}
              title="Chart visualization"
            >
              <BarChart2 className="h-3.5 w-3.5" />
            </Button>
            <Button
              size="sm"
              variant={viewMode === "table" ? "default" : "ghost"}
              className="h-7 text-xs px-2"
              onClick={() => setViewMode("table")}
              title="Accessible table view"
            >
              <TableIcon className="h-3.5 w-3.5" />
            </Button>
          </div>
        </div>
      </div>

      {/* Outage or Unavailable Notice */}
      {data && !data.available && (
        <div className="p-4 rounded-md bg-amber-500/10 border border-amber-500/30 text-amber-900 dark:text-amber-200 text-xs flex items-start gap-2">
          <AlertTriangle className="h-4 w-4 text-amber-600 shrink-0 mt-0.5" />
          <div>
            <span className="font-semibold">
              Prometheus monitoring unavailable:{" "}
            </span>
            <span>
              {data.error_message ||
                "Unable to reach Prometheus server. Historical trends are currently offline."}
            </span>
          </div>
        </div>
      )}

      {error && (
        <div className="p-4 rounded-md bg-destructive/10 border border-destructive/20 text-destructive text-xs">
          Failed to load historical trends.
        </div>
      )}

      {isLoading ? (
        <div className="flex flex-col items-center justify-center p-12 text-muted-foreground border rounded-lg bg-card">
          <Loader2 className="h-8 w-8 animate-spin mb-2" />
          <span className="text-xs">Querying Prometheus time series...</span>
        </div>
      ) : data?.metrics && data.metrics.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {data.metrics.map((metric) => {
            const chartData = transformChartData(metric);

            return (
              <Card key={metric.metric_id} className="overflow-hidden">
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-sm font-semibold">
                      {metric.title}
                    </CardTitle>
                    <Badge variant="outline" className="text-[11px] font-mono">
                      {metric.unit}
                    </Badge>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {metric.description}
                  </p>
                </CardHeader>
                <CardContent className="pt-2">
                  {chartData.length === 0 ? (
                    <div className="h-48 flex items-center justify-center text-xs text-muted-foreground border rounded-md border-dashed">
                      No data recorded for this time range.
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
                              dataKey="formattedTime"
                              tick={{ fontSize: 10 }}
                              stroke="#888888"
                            />
                            <YAxis tick={{ fontSize: 10 }} stroke="#888888" />
                            <Tooltip
                              formatter={(value: unknown) => [
                                `${value} ${metric.unit}`,
                              ]}
                              labelFormatter={(label) => `Time: ${label}`}
                              contentStyle={{
                                fontSize: "12px",
                                borderRadius: "6px",
                                backgroundColor: "rgba(255, 255, 255, 0.95)",
                                color: "#000",
                              }}
                            />
                            {metric.series.map((s, idx) => (
                              <Bar
                                key={s.name}
                                dataKey={s.name}
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
                              dataKey="formattedTime"
                              tick={{ fontSize: 10 }}
                              stroke="#888888"
                            />
                            <YAxis tick={{ fontSize: 10 }} stroke="#888888" />
                            <Tooltip
                              formatter={(value: unknown) => [
                                `${value} ${metric.unit}`,
                              ]}
                              labelFormatter={(label) => `Time: ${label}`}
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
                            {metric.series.map((s, idx) => (
                              <Line
                                key={s.name}
                                type="monotone"
                                dataKey={s.name}
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
                            <th className="p-1.5 font-medium">Time</th>
                            {metric.series.map((s) => (
                              <th
                                key={s.name}
                                className="p-1.5 font-medium text-right"
                              >
                                {s.name}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody className="divide-y">
                          {chartData.map((row, idx) => (
                            <tr key={idx} className="hover:bg-muted/20">
                              <td className="p-1.5 text-muted-foreground whitespace-nowrap">
                                {row.formattedTime}
                              </td>
                              {metric.series.map((s) => (
                                <td
                                  key={s.name}
                                  className="p-1.5 text-right font-mono"
                                >
                                  {row[s.name] ?? "-"}
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
          No metrics returned for this group.
        </div>
      )}
    </div>
  );
}
