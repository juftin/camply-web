/**
 * Component and visual state preview catalog for Camply.
 *
 * Provides an isolated environment displaying design system primitives,
 * compound components, and varied data states for visual snapshot testing
 * and reviewer inspection.
 */

import React, { useState } from "react";
import { Activity, Bell, Calendar, MapPin, Sparkles, Zap } from "lucide-react";
import { ScanCard } from "@/components/ScanCard";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { ThemeToggle } from "@/components/theme-toggle";
import type { ScanResponse } from "@/lib/structs";

/**
 * Mock scan records covering various states.
 */
const mockScans: ScanResponse[] = [
  {
    id: "scan-mock-1",
    provider_id: 1,
    campground_id: "232447",
    campground_name: "Upper Pines Campground",
    recreation_area_name: "Yosemite National Park",
    start_date: "2026-07-15",
    end_date: "2026-07-19",
    is_active: true,
    min_stay_length: 2,
    preferred_types: ["STANDARD NONELECTRIC", "TENT ONLY"],
    require_electric: false,
    last_checked_at: "2026-07-01T12:00:00Z",
    found_count: 4,
    created_at: "2026-06-15T08:00:00Z",
  },
  {
    id: "scan-mock-2",
    provider_id: 1,
    campground_id: "232450",
    campground_name: "Camp 4",
    recreation_area_name: "Yosemite National Park",
    start_date: "2026-08-01",
    end_date: "2026-08-03",
    is_active: false,
    min_stay_length: 1,
    preferred_types: ["TENT ONLY"],
    require_electric: false,
    last_checked_at: "2026-07-01T11:45:00Z",
    found_count: 0,
    created_at: "2026-06-20T10:00:00Z",
  },
  {
    id: "scan-mock-3",
    provider_id: 1,
    campground_id: "232449",
    campground_name: "Lower Pines",
    recreation_area_name: "Yosemite National Park",
    start_date: "2026-09-10",
    end_date: "2026-09-14",
    is_active: true,
    min_stay_length: 3,
    preferred_types: ["RV NONELECTRIC"],
    require_electric: true,
    last_checked_at: "2026-07-01T12:05:00Z",
    found_count: 1,
    created_at: "2026-06-25T14:30:00Z",
  },
];

/**
 * DevPreview page component rendering all design system variations.
 *
 * Returns
 * -------
 * React.ReactElement
 *     Rendered component showcase page.
 */
export function DevPreview(): React.ReactElement {
  const [scans, setScans] = useState<ScanResponse[]>(mockScans);
  const [switchState, setSwitchState] = useState<boolean>(true);

  const handleToggleActive = (scanId: string, isActive: boolean): void => {
    setScans((prev) =>
      prev.map((scan) =>
        scan.id === scanId ? { ...scan, is_active: isActive } : scan,
      ),
    );
  };

  const handleDelete = (scanId: string): void => {
    setScans((prev) => prev.filter((scan) => scan.id !== scanId));
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-6xl space-y-10">
      {/* Header and Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b pb-6">
        <div>
          <div className="flex items-center gap-2">
            <Sparkles className="h-6 w-6 text-primary" />
            <h1 className="text-3xl font-bold tracking-tight">
              Design System & Snapshot Catalog
            </h1>
          </div>
          <p className="text-muted-foreground mt-1 text-sm">
            Visual fixture harness for human reviewers and automated visual
            regression agents.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <ThemeToggle />
        </div>
      </div>

      {/* Section 1: Dashboard Stat Cards */}
      <section className="space-y-4">
        <h2 className="text-xl font-semibold tracking-tight">Summary Stats</h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Total Monitored Scans</CardDescription>
              <CardTitle className="text-2xl font-bold">12</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-muted-foreground flex items-center gap-1">
                <Activity className="h-3.5 w-3.5 text-primary" />
                Across 4 recreation areas
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Active Checkers</CardDescription>
              <CardTitle className="text-2xl font-bold text-green-600 dark:text-green-400">
                8
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-muted-foreground flex items-center gap-1">
                <Zap className="h-3.5 w-3.5 text-yellow-500" />
                Polling every 30 seconds
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Campsites Available</CardDescription>
              <CardTitle className="text-2xl font-bold text-primary">
                5
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-muted-foreground flex items-center gap-1">
                <Bell className="h-3.5 w-3.5 text-primary" />
                Alerts dispatched to Pushover
              </p>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* Section 2: Scan Cards Variations */}
      <section className="space-y-4">
        <h2 className="text-xl font-semibold tracking-tight">
          Scan Cards (Active, Paused, Found)
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {scans.map((scan) => (
            <ScanCard
              key={scan.id}
              scan={scan}
              onToggleActive={handleToggleActive}
              onDelete={handleDelete}
            />
          ))}
        </div>
      </section>

      {/* Section 3: Badges & Status Indicators */}
      <section className="space-y-4">
        <h2 className="text-xl font-semibold tracking-tight">
          Badges & Status Elements
        </h2>
        <div className="flex flex-wrap items-center gap-3 p-4 border rounded-lg bg-card">
          <Badge variant="default">Active</Badge>
          <Badge variant="secondary">Paused</Badge>
          <Badge variant="outline">Recreation.gov</Badge>
          <Badge variant="destructive">Failed</Badge>
          <Badge className="bg-emerald-600 hover:bg-emerald-700 text-white">
            4 Found
          </Badge>
          <Badge className="bg-amber-600 hover:bg-amber-700 text-white">
            Electric Required
          </Badge>
        </div>
      </section>

      {/* Section 4: Interactive Primitives */}
      <section className="space-y-4">
        <h2 className="text-xl font-semibold tracking-tight">
          Form Controls & Buttons
        </h2>
        <Card>
          <CardContent className="pt-6 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-6">
            <div className="space-y-2">
              <Label htmlFor="preview-email">Input Field</Label>
              <Input
                id="preview-email"
                placeholder="camper@example.com"
                defaultValue="camper@example.com"
              />
            </div>
            <div className="space-y-2">
              <Label>Switch Toggle</Label>
              <div className="flex items-center space-x-2 pt-2">
                <Switch
                  id="preview-switch"
                  checked={switchState}
                  onCheckedChange={setSwitchState}
                />
                <Label htmlFor="preview-switch" className="cursor-pointer">
                  {switchState ? "Notification Active" : "Notification Paused"}
                </Label>
              </div>
            </div>
            <div className="space-y-2">
              <Label>Button Variants</Label>
              <div className="flex flex-wrap gap-2 pt-1">
                <Button size="sm">Primary</Button>
                <Button size="sm" variant="outline">
                  Outline
                </Button>
                <Button size="sm" variant="ghost">
                  Ghost
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </section>

      {/* Section 5: Empty State */}
      <section className="space-y-4">
        <h2 className="text-xl font-semibold tracking-tight">Empty State</h2>
        <Card className="text-center py-10">
          <CardContent className="space-y-3">
            <Calendar className="h-10 w-10 text-muted-foreground mx-auto" />
            <h3 className="text-lg font-medium">No active campsite scans</h3>
            <p className="text-sm text-muted-foreground max-w-sm mx-auto">
              Start by searching for a national park or campground above to
              track openings.
            </p>
            <Button size="sm" className="mt-2">
              <MapPin className="h-4 w-4 mr-1.5" />
              Explore Campgrounds
            </Button>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
