import { useAuth } from "@/hooks/useAuth";
import { Link } from "react-router-dom";
import {
  Search,
  Bell,
  Calendar,
  MapPin,
  Clock,
  Smartphone,
  Mail,
  Zap,
  Shield,
  Settings,
  CheckCircle,
  ArrowRight,
  RefreshCw,
  AlertCircle,
  TentTree,
  Tent,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { communityPagesEnabled } from "@/lib/features";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export function HowItWorks() {
  const { accountPath } = useAuth();
  return (
    <div className="container mx-auto py-12 px-4 max-w-6xl">
      {/* Hero Section */}
      <div className="text-center mb-16">
        <div className="mb-6">
          <Tent className="h-16 w-16 text-primary mx-auto mb-4" />
        </div>
        <h1 className="text-5xl font-bold mb-6">
          How camply
          <span className="text-primary"> Works</span>
        </h1>
        <p className="text-xl text-muted-foreground max-w-4xl mx-auto leading-relaxed">
          {communityPagesEnabled
            ? "From search to reservation, here's exactly how camply monitors campsite availability and gets you notified the moment your perfect spot becomes available."
            : "Search campgrounds, save a scan for the dates and campsite you want, and review matching availability in your dashboard. Complete reservations with the campground's booking provider."}
        </p>
      </div>

      {/* Quick Overview */}
      <section className="mb-16">
        <Card className="border-blue-200 bg-blue-50 dark:bg-blue-950/20 dark:border-blue-800">
          <CardHeader className="text-center">
            <CardTitle className="text-3xl mb-4">The Simple Process</CardTitle>
            <CardDescription className="text-lg">
              {communityPagesEnabled
                ? "Four easy steps to never miss a campsite again"
                : "Four steps from campground search to booking"}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid md:grid-cols-4 gap-6">
              <div className="text-center">
                <div className="bg-primary text-primary-foreground rounded-full w-12 h-12 flex items-center justify-center text-xl font-bold mx-auto mb-4">
                  1
                </div>
                <Search className="h-8 w-8 text-primary mx-auto mb-2" />
                <h3 className="font-semibold mb-2">Search</h3>
                <p className="text-sm text-muted-foreground">
                  Find your desired campground and dates
                </p>
              </div>
              <div className="text-center">
                <div className="bg-primary text-primary-foreground rounded-full w-12 h-12 flex items-center justify-center text-xl font-bold mx-auto mb-4">
                  2
                </div>
                <Settings className="h-8 w-8 text-primary mx-auto mb-2" />
                <h3 className="font-semibold mb-2">Configure</h3>
                <p className="text-sm text-muted-foreground">
                  Set your preferences and notification methods
                </p>
              </div>
              <div className="text-center">
                <div className="bg-primary text-primary-foreground rounded-full w-12 h-12 flex items-center justify-center text-xl font-bold mx-auto mb-4">
                  3
                </div>
                <RefreshCw className="h-8 w-8 text-primary mx-auto mb-2" />
                <h3 className="font-semibold mb-2">
                  {communityPagesEnabled ? "Monitor" : "Check Availability"}
                </h3>
                <p className="text-sm text-muted-foreground">
                  {communityPagesEnabled
                    ? "We check availability every few minutes"
                    : "Checks on the configured schedule"}
                </p>
              </div>
              <div className="text-center">
                <div className="bg-primary text-primary-foreground rounded-full w-12 h-12 flex items-center justify-center text-xl font-bold mx-auto mb-4">
                  4
                </div>
                <Bell className="h-8 w-8 text-primary mx-auto mb-2" />
                <h3 className="font-semibold mb-2">
                  {communityPagesEnabled ? "Get Notified" : "Review Results"}
                </h3>
                <p className="text-sm text-muted-foreground">
                  {communityPagesEnabled
                    ? "Instant alerts when spots open up"
                    : "Review matching availability and booking links"}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </section>

      {/* Detailed Steps */}
      <section className="mb-16">
        <h2 className="text-3xl font-bold text-center mb-12">
          Step-by-Step Guide
        </h2>

        {/* Step 1 */}
        <div className="mb-12">
          <Card>
            <CardContent className="p-8">
              <div className="grid md:grid-cols-2 gap-8 items-center">
                <div>
                  <div className="flex items-center gap-4 mb-4">
                    <div className="bg-primary text-primary-foreground rounded-full w-10 h-10 flex items-center justify-center text-lg font-bold">
                      1
                    </div>
                    <h3 className="text-2xl font-semibold">
                      Find Your Campground
                    </h3>
                  </div>
                  <p className="text-muted-foreground mb-4">
                    {communityPagesEnabled
                      ? "Start by searching for your desired campground using our search tool. You can search by name, location, or browse our supported providers including National Parks, State Parks, and Recreation Areas."
                      : "Search campgrounds by name or location, or browse the providers available in this instance. Choose a campground to view its details and available booking information."}
                  </p>
                  <div className="space-y-3">
                    <div className="flex items-center gap-2">
                      <MapPin className="h-4 w-4 text-primary" />
                      <span className="text-sm">
                        Search by campground name or location
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Calendar className="h-4 w-4 text-primary" />
                      <span className="text-sm">Select your desired dates</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <TentTree className="h-4 w-4 text-primary" />
                      <span className="text-sm">
                        Choose campsite types and preferences
                      </span>
                    </div>
                  </div>
                </div>
                <div className="bg-muted/30 rounded-lg p-6 text-center">
                  <Search className="h-16 w-16 text-primary mx-auto mb-4" />
                  <p className="text-sm text-muted-foreground">
                    Search interface with filters for dates, campsite types, and
                    amenities
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Step 2 */}
        <div className="mb-12">
          <Card>
            <CardContent className="p-8">
              <div className="grid md:grid-cols-2 gap-8 items-center">
                <div className="bg-muted/30 rounded-lg p-6 text-center order-2 md:order-1">
                  <Settings className="h-16 w-16 text-primary mx-auto mb-4" />
                  <p className="text-sm text-muted-foreground">
                    {communityPagesEnabled
                      ? "Notification preferences and monitoring settings"
                      : "Campsite preferences and scan settings"}
                  </p>
                </div>
                <div className="order-1 md:order-2">
                  <div className="flex items-center gap-4 mb-4">
                    <div className="bg-primary text-primary-foreground rounded-full w-10 h-10 flex items-center justify-center text-lg font-bold">
                      2
                    </div>
                    <h3 className="text-2xl font-semibold">
                      Set Your Preferences
                    </h3>
                  </div>
                  <p className="text-muted-foreground mb-4">
                    {communityPagesEnabled
                      ? "Configure how and when you want to be notified. Choose your notification methods, set specific campsite preferences, and customize monitoring frequency to match your needs."
                      : "Choose the dates, site types, and other preferences for the campsite you want. Save them as a scan so you can review its status and matching availability from your dashboard."}
                  </p>
                  <div className="space-y-3">
                    <div className="flex items-center gap-2">
                      <Mail className="h-4 w-4 text-primary" />
                      <span className="text-sm">
                        {communityPagesEnabled
                          ? "Email notifications"
                          : "Review scan status in your dashboard"}
                      </span>
                    </div>
                    {communityPagesEnabled && (
                      <>
                        <div className="flex items-center gap-2">
                          <Smartphone className="h-4 w-4 text-primary" />
                          <span className="text-sm">
                            SMS alerts (coming soon)
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          <Bell className="h-4 w-4 text-primary" />
                          <span className="text-sm">
                            Push notifications (coming soon)
                          </span>
                        </div>
                      </>
                    )}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Step 3 */}
        <div className="mb-12">
          <Card>
            <CardContent className="p-8">
              <div className="grid md:grid-cols-2 gap-8 items-center">
                <div>
                  <div className="flex items-center gap-4 mb-4">
                    <div className="bg-primary text-primary-foreground rounded-full w-10 h-10 flex items-center justify-center text-lg font-bold">
                      3
                    </div>
                    <h3 className="text-2xl font-semibold">
                      {communityPagesEnabled
                        ? "We Monitor 24/7"
                        : "Check Availability"}
                    </h3>
                  </div>
                  <p className="text-muted-foreground mb-4">
                    {communityPagesEnabled
                      ? "Once you've set up your alerts, camply takes over. Our system automatically checks campsite availability every few minutes, around the clock, so you don't have to constantly refresh booking websites."
                      : "The app checks availability for saved scans using the schedule configured for this instance. Check each scan's status and matching results in your dashboard."}
                  </p>
                  <div className="space-y-3">
                    <div className="flex items-center gap-2">
                      <Clock className="h-4 w-4 text-primary" />
                      <span className="text-sm">
                        {communityPagesEnabled
                          ? "Checks every 2-5 minutes"
                          : "Checks on the configured schedule"}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Shield className="h-4 w-4 text-primary" />
                      <span className="text-sm">
                        {communityPagesEnabled
                          ? "Reliable, automated monitoring"
                          : "Scan status and results in your dashboard"}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Zap className="h-4 w-4 text-primary" />
                      <span className="text-sm">
                        {communityPagesEnabled
                          ? "Instant detection of new availability"
                          : "Matching availability from the provider"}
                      </span>
                    </div>
                  </div>
                </div>
                <div className="bg-muted/30 rounded-lg p-6 text-center">
                  <RefreshCw className="h-16 w-16 text-primary mx-auto mb-4" />
                  <p className="text-sm text-muted-foreground">
                    {communityPagesEnabled
                      ? "Continuous monitoring dashboard showing real-time status"
                      : "Scan status and matching campsite availability"}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Step 4 */}
        <div className="mb-12">
          <Card>
            <CardContent className="p-8">
              <div className="grid md:grid-cols-2 gap-8 items-center">
                <div className="bg-muted/30 rounded-lg p-6 text-center order-2 md:order-1">
                  <Bell className="h-16 w-16 text-primary mx-auto mb-4" />
                  <p className="text-sm text-muted-foreground">
                    {communityPagesEnabled
                      ? "Instant notification with booking link and campsite details"
                      : "Matching availability with campsite details and booking link"}
                  </p>
                </div>
                <div className="order-1 md:order-2">
                  <div className="flex items-center gap-4 mb-4">
                    <div className="bg-primary text-primary-foreground rounded-full w-10 h-10 flex items-center justify-center text-lg font-bold">
                      4
                    </div>
                    <h3 className="text-2xl font-semibold">
                      {communityPagesEnabled
                        ? "Get Instant Alerts"
                        : "Review Results"}
                    </h3>
                  </div>
                  <p className="text-muted-foreground mb-4">
                    {communityPagesEnabled
                      ? "The moment a campsite becomes available, you'll receive an instant notification with all the details you need to book quickly. Each alert includes a direct link to the official booking site."
                      : "When a scan finds matching availability, review the campsite details and follow its booking link to the provider's reservation site."}
                  </p>
                  <div className="space-y-3">
                    <div className="flex items-center gap-2">
                      <Zap className="h-4 w-4 text-primary" />
                      <span className="text-sm">
                        {communityPagesEnabled
                          ? "Instant notifications"
                          : "Availability shown in your dashboard"}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <CheckCircle className="h-4 w-4 text-primary" />
                      <span className="text-sm">Direct booking links</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <MapPin className="h-4 w-4 text-primary" />
                      <span className="text-sm">
                        Campsite details and pricing
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* Behind the Scenes */}
      <section className="mb-16">
        <h2 className="text-3xl font-bold text-center mb-12">
          {communityPagesEnabled ? "Behind the Scenes" : "What the App Does"}
        </h2>
        <div className="grid md:grid-cols-3 gap-8">
          <Card>
            <CardHeader className="text-center">
              <RefreshCw className="h-12 w-12 text-primary mx-auto mb-4" />
              <CardTitle>
                {communityPagesEnabled
                  ? "Smart Monitoring"
                  : "Availability Checks"}
              </CardTitle>
            </CardHeader>
            <CardContent className="text-center">
              <p className="text-muted-foreground">
                {communityPagesEnabled
                  ? "Our system intelligently schedules checks based on campground patterns, peak times, and cancellation trends to catch availability the moment it appears."
                  : "The app checks availability for saved scans according to the schedule configured for this instance."}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="text-center">
              <Shield className="h-12 w-12 text-primary mx-auto mb-4" />
              <CardTitle>
                {communityPagesEnabled
                  ? "Reliable Infrastructure"
                  : "Scan Results"}
              </CardTitle>
            </CardHeader>
            <CardContent className="text-center">
              <p className="text-muted-foreground">
                {communityPagesEnabled
                  ? "Built on robust infrastructure with redundancy and failover systems to ensure we never miss an availability opening, even during high-traffic periods."
                  : "Your dashboard shows each scan's status and any matching campsites returned by its booking provider."}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="text-center">
              <Zap className="h-12 w-12 text-primary mx-auto mb-4" />
              <CardTitle>
                {communityPagesEnabled ? "Lightning Fast" : "Booking Links"}
              </CardTitle>
            </CardHeader>
            <CardContent className="text-center">
              <p className="text-muted-foreground">
                {communityPagesEnabled
                  ? "Notifications are sent within seconds of detecting availability. Our optimized delivery system ensures you get notified before anyone manually checking websites."
                  : "When results include availability, use the booking link to open the provider's reservation page and complete your booking there."}
              </p>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* FAQ Section */}
      <section className="mb-16">
        <h2 className="text-3xl font-bold text-center mb-12">
          Common Questions
        </h2>
        <div className="space-y-6 max-w-4xl mx-auto">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <AlertCircle className="h-5 w-5 text-primary" />
                {communityPagesEnabled
                  ? "How often do you check for availability?"
                  : "How often does this instance check for availability?"}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground">
                {communityPagesEnabled
                  ? "We check campsite availability every 2-5 minutes, 24/7. The exact frequency depends on the campground and how close your dates are, with more frequent checks closer to arrival dates."
                  : "Scans run on the schedule configured for this instance. Check your scan dashboard for the latest status and results."}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <AlertCircle className="h-5 w-5 text-primary" />
                Do I book through camply?
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground">
                {communityPagesEnabled
                  ? "No, camply only monitors and notifies. When we find availability, we send you a direct link to the official booking site (like Recreation.gov or ReserveAmerica) where you complete your reservation."
                  : "No. Camply shows scan results and links to the provider's reservation page. Complete your booking on the provider's website."}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <AlertCircle className="h-5 w-5 text-primary" />
                {communityPagesEnabled
                  ? "How fast do I need to book after getting notified?"
                  : "How quickly should I book after availability is found?"}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground">
                {communityPagesEnabled
                  ? "Popular campsites can book up within minutes, so we recommend booking immediately after receiving a notification. Our notifications give you a significant head start over manual checking."
                  : "Availability can change at any time. Camply does not reserve a site, so complete your booking with the provider to secure it."}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <AlertCircle className="h-5 w-5 text-primary" />
                Which campgrounds do you support?
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground">
                We support campgrounds on Recreation.gov (National Parks,
                National Forests, Army Corps of Engineers) and many state park
                systems. Check our{" "}
                <Link to="/providers" className="text-primary hover:underline">
                  providers page
                </Link>{" "}
                for the complete list.
              </p>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* Call to Action */}
      <section className="text-center">
        <Card className="bg-primary/5 border-primary/20">
          <CardContent className="py-12">
            <TentTree className="h-16 w-16 text-primary mx-auto mb-6" />
            <h2 className="text-3xl font-bold mb-6">Ready to Get Started?</h2>
            <p className="text-xl text-muted-foreground max-w-3xl mx-auto mb-8">
              {communityPagesEnabled
                ? "Set up your first campsite alert in minutes and never miss your perfect camping spot again."
                : "Search for a campground, save a scan with your dates and preferences, and review matching availability in your dashboard."}
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Button size="lg" asChild>
                <Link to={accountPath}>
                  {communityPagesEnabled ? "Start Monitoring" : "Create a Scan"}
                  <ArrowRight className="h-4 w-4 ml-2" />
                </Link>
              </Button>
              <Button variant="outline" size="lg" asChild>
                <Link to="/providers">View Supported Campgrounds</Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
