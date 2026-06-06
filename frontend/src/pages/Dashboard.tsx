import { useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { Plus, Loader2, Frown, LogOut, Settings } from "lucide-react";
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
import { ScanCard } from "@/components/ScanCard";
import { ScanForm } from "@/components/ScanForm";
import { useAuth } from "@/hooks/useAuth";
import { useScans, useUpdateScan, useDeleteScan, getApiErrorMessage } from "@/hooks/useScans";

export function Dashboard() {
  const {
    user,
    isEarlyAccess,
    isReady,
    isLoading: authLoading,
    updatePushoverToken,
    signOut,
  } = useAuth();
  const navigate = useNavigate();

  const {
    data: scanList,
    isLoading: scansLoading,
    error: scansError,
    refetch: refetchScans,
  } = useScans();

  const updateScan = useUpdateScan();
  const deleteScan = useDeleteScan();

  const [showSettings, setShowSettings] = useState(false);
  const [pushoverToken, setPushoverToken] = useState(user?.pushover_token ?? "");
  const [pushoverSaving, setPushoverSaving] = useState(false);
  const [pushoverError, setPushoverError] = useState<string | null>(null);
  const [pushoverSuccess, setPushoverSuccess] = useState(false);

  // ---- Handlers (must be before early returns) ----
  const handleToggleActive = useCallback(
    async (scanId: string, isActive: boolean) => {
      try {
        await updateScan.mutateAsync({ scanId, payload: { is_active: isActive } });
      } catch {
        // error is surfaced via the mutation state
      }
    },
    [updateScan],
  );

  const handleDelete = useCallback(
    async (scanId: string) => {
      try {
        await deleteScan.mutateAsync(scanId);
      } catch {
        // error is surfaced via the mutation state
      }
    },
    [deleteScan],
  );

  // ---- Navigation guard: not ready yet ----
  if (authLoading || !isReady) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  // ---- Early access gate ----
  if (!isEarlyAccess) {
    navigate("/early-access", { replace: true });
    return null;
  }

  const handleSavePushover = async () => {
    setPushoverSaving(true);
    setPushoverError(null);
    setPushoverSuccess(false);
    try {
      await updatePushoverToken(pushoverToken || null);
      setPushoverSuccess(true);
      setTimeout(() => setPushoverSuccess(false), 3000);
    } catch (err) {
      setPushoverError(getApiErrorMessage(err));
    } finally {
      setPushoverSaving(false);
    }
  };

  const scans = scanList?.scans ?? [];
  const activeScans = scans.filter((s) => s.is_active);
  const foundCount = scans.reduce((acc, s) => acc + s.found_count, 0);

  return (
    <div className="container mx-auto px-4 py-8 max-w-5xl">
      {/* ---- Header ---- */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-bold">Dashboard</h1>
          <p className="text-muted-foreground mt-1">
            Welcome back, {user?.email ? user.email.split("@")[0] : "camper"} 🏕️
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowSettings(!showSettings)}
          >
            <Settings className="h-4 w-4 mr-1" />
            Settings
          </Button>
          <Button variant="ghost" size="sm" onClick={signOut}>
            <LogOut className="h-4 w-4 mr-1" />
            Sign Out
          </Button>
        </div>
      </div>

      {/* ---- Stats ---- */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 mb-8">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-2xl">{scans.length}</CardTitle>
            <CardDescription>Total Scans</CardDescription>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-2xl">{activeScans.length}</CardTitle>
            <CardDescription>Active</CardDescription>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-2xl">{foundCount}</CardTitle>
            <CardDescription>Sites Found</CardDescription>
          </CardHeader>
        </Card>
      </div>

      {/* ---- Settings panel ---- */}
      {showSettings && (
        <Card className="mb-8">
          <CardHeader>
            <CardTitle className="text-lg">Notification Settings</CardTitle>
            <CardDescription>
              Configure your Pushover integration for real-time alerts.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="space-y-1">
              <Label htmlFor="pushover_token">Pushover User Key</Label>
              <div className="flex gap-2">
                <Input
                  id="pushover_token"
                  placeholder="Enter your Pushover user key"
                  value={pushoverToken}
                  onChange={(e) => setPushoverToken(e.target.value)}
                />
                <Button
                  onClick={handleSavePushover}
                  disabled={pushoverSaving}
                >
                  {pushoverSaving ? "Saving..." : "Save"}
                </Button>
              </div>
            </div>
            {pushoverError && (
              <p className="text-sm text-destructive">{pushoverError}</p>
            )}
            {pushoverSuccess && (
              <p className="text-sm text-green-600">Pushover token saved!</p>
            )}
            <p className="text-xs text-muted-foreground">
              Don't have a Pushover key?{" "}
              <a
                href="https://pushover.net/"
                target="_blank"
                rel="noopener noreferrer"
                className="underline hover:text-foreground"
              >
                Sign up at pushover.net
              </a>
            </p>
          </CardContent>
        </Card>
      )}

      {/* ---- Scans list ---- */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold">Your Scans</h2>
        <ScanForm onSuccess={() => refetchScans()} />
      </div>

      {scansLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      ) : scansError ? (
        <div className="rounded-md bg-destructive/10 p-6 text-center">
          <p className="text-destructive font-medium">
            Failed to load scans
          </p>
          <Button
            variant="outline"
            size="sm"
            className="mt-2"
            onClick={() => refetchScans()}
          >
            Retry
          </Button>
        </div>
      ) : scans.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12 text-center">
            <Frown className="h-12 w-12 text-muted-foreground mb-3" />
            <h3 className="text-lg font-medium mb-1">No scans yet</h3>
            <p className="text-muted-foreground mb-4 max-w-sm">
              Create your first scan to start monitoring campsite availability.
            </p>
            <ScanForm
              onSuccess={() => refetchScans()}
              trigger={<Button><Plus className="h-4 w-4 mr-1" />Create Scan</Button>}
            />
          </CardContent>
        </Card>
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {scans.map((scan) => (
            <ScanCard
              key={scan.id}
              scan={scan}
              onToggleActive={handleToggleActive}
              onDelete={handleDelete}
              toggling={
                updateScan.isPending &&
                updateScan.variables?.scanId === scan.id
              }
            />
          ))}
        </div>
      )}
    </div>
  );
}
