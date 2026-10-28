import React from "react";
import { Sparkles, ArrowRight, Eye, ShieldCheck } from "lucide-react";
import { Link } from "react-router-dom";
import { PaletteStudio } from "@/components/PaletteStudio";
import { ScanCard } from "@/components/ScanCard";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import type { ScanResponse } from "@/lib/structs";

const sampleScan: ScanResponse = {
  id: "preview-scan-1",
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
};

export const PalettePage: React.FC = () => {
  return (
    <div className="container mx-auto px-4 py-8 max-w-5xl space-y-8 animate-in fade-in duration-300">
      {/* Header */}
      <div className="border-b pb-6">
        <div className="flex items-center gap-2">
          <Sparkles className="h-6 w-6 text-primary" />
          <h1 className="text-3xl font-bold tracking-tight">
            Theme Palette Studio
          </h1>
        </div>
        <p className="text-muted-foreground mt-1.5 text-sm max-w-2xl">
          Interact with sliders and presets to find your ideal campsite theme
          color. Any changes apply live across the whole application and persist
          during your browsing session.
        </p>
      </div>

      {/* Main Studio Tool */}
      <section>
        <PaletteStudio />
      </section>

      {/* Real-World Context Previews */}
      <section className="space-y-4 pt-4 border-t">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold tracking-tight flex items-center gap-2">
              <Eye className="h-5 w-5 text-primary" /> Real-World Application
              Preview
            </h2>
            <p className="text-xs text-muted-foreground">
              See how your active palette looks on live production components.
            </p>
          </div>
          <Link to="/dashboard">
            <Button size="sm" variant="outline" className="text-xs">
              Go to Dashboard <ArrowRight className="h-3.5 w-3.5 ml-1" />
            </Button>
          </Link>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Card 1: Sample Scan Card */}
          <div className="space-y-2">
            <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Campsite Scan Card
            </span>
            <ScanCard
              scan={sampleScan}
              onToggleActive={() => {}}
              onDelete={() => {}}
            />
          </div>

          {/* Card 2: Interactive Stats */}
          <div className="space-y-2">
            <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Dashboard Metric Card
            </span>
            <Card className="h-full flex flex-col justify-between">
              <CardHeader>
                <CardDescription>Campsites Available</CardDescription>
                <CardTitle className="text-4xl font-extrabold text-primary">
                  14
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <p className="text-xs text-muted-foreground">
                  Immediate alerts dispatched across 3 monitored recreation
                  areas in Yosemite and Joshua Tree.
                </p>
                <div className="flex gap-2">
                  <Button size="sm" className="w-full">
                    View Available Sites
                  </Button>
                  <Button size="sm" variant="outline">
                    Scan Filters
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      {/* Accessibility & Design System Guidelines */}
      <section className="p-4 rounded-xl border bg-muted/30 space-y-2 text-xs text-muted-foreground">
        <div className="flex items-center gap-2 font-semibold text-foreground">
          <ShieldCheck className="h-4 w-4 text-primary" />
          Color Design Tips for Camply
        </div>
        <p>
          When choosing a blue or cyan for dark mode, keeping saturation between{" "}
          <strong>40% and 55%</strong> prevents the eye from experiencing{" "}
          <em>chromostereopsis</em> (chromatic aberration and optical haloing).
          All default presets are pre-calibrated to exceed WCAG AA 4.5:1
          contrast.
        </p>
      </section>
    </div>
  );
};
