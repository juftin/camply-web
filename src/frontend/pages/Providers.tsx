import {
  ExternalLink,
  MapPin,
  Users,
  Calendar,
  Star,
  Caravan,
} from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Link } from "react-router-dom";
import { SearchBar } from "@/components/SearchBar.tsx";

interface Provider {
  name: string;
  description: string;
  website: string;
  logo?: string;
  features: string[];
  campgroundCount?: number;
  coverage: string[];
  popular?: boolean;
}

const providers: Provider[] = [
  {
    name: "Recreation.gov",
    description:
      "The official federal recreation portal for reserving campsites at National Parks, National Forests, and other federal recreation areas.",
    website: "https://www.recreation.gov",
    logo: `${import.meta.env.BASE_URL}branding/recreation-gov.png`,
    features: [
      "National Parks",
      "National Forests",
      "National Wildlife Refuges",
      "Campsites & Tickets",
      "Timed Entries",
    ],
    campgroundCount: 3000,
    coverage: ["Federal Lands", "National Parks"],
    popular: true,
  },
  {
    name: "ReserveCalifornia",
    description:
      "Official reservation system for California State Parks offering diverse camping from beaches to deserts to mountains.",
    website: "https://www.reservecalifornia.com",
    features: [
      "Beach Camping",
      "Desert Camping",
      "Mountain Camping",
      "Historic Sites",
    ],
    campgroundCount: 280,
    coverage: ["California State Parks"],
    popular: true,
  },
  {
    name: "ReserveAmerica",
    description:
      "Campsite reservations at state parks and other campgrounds across the United States.",
    website: "https://www.reserveamerica.com",
    features: ["Tent Camping", "RV Sites", "Cabins & Lodging", "Group Camping"],
    campgroundCount: 1000,
    coverage: ["State Parks", "United States"],
    popular: true,
  },
  {
    name: "Arizona State Parks",
    description:
      "Official booking platform for Arizona's desert state parks and recreation areas.",
    website: "https://azstateparks.com/reserve",
    features: [
      "Desert Camping",
      "Hiking Trails",
      "Lake Recreation",
      "Historic Sites",
    ],
    coverage: ["Arizona State Parks"],
  },
  {
    name: "Florida State Parks",
    description:
      "Reservation system for Florida's diverse state parks from beaches to springs to wetlands.",
    website: "https://reserve.floridastateparks.org/Web",
    features: [
      "Beach Camping",
      "Spring Sites",
      "Wetland Parks",
      "Cabins & Lodges",
    ],
    coverage: ["Florida State Parks"],
  },
  {
    name: "Minnesota State Parks",
    description:
      "Booking platform for Minnesota's state parks and recreation areas with lakes and forests.",
    website: "https://reservemn.usedirect.com/MinnesotaWeb",
    features: ["Lake Camping", "Forest Sites", "Cabins", "Group Camps"],
    coverage: ["Minnesota State Parks"],
  },
  {
    name: "Missouri State Parks",
    description:
      "Reservation system for Missouri's state parks and historic sites.",
    website: "https://icampmo.usedirect.com/MSPWeb",
    features: ["Ozark Camping", "Lake Sites", "Historic Parks", "Cabins"],
    coverage: ["Missouri State Parks"],
  },
  {
    name: "Ohio State Parks",
    description:
      "Official booking system for Ohio's state parks and recreation facilities.",
    website: "https://reserveohio.com/OhioCampWeb",
    features: [
      "Lake Camping",
      "Forest Sites",
      "Cabins & Lodges",
      "Group Facilities",
    ],
    coverage: ["Ohio State Parks"],
  },
  {
    name: "Virginia State Parks",
    description:
      "Reservation platform for Virginia's state parks from mountains to coast.",
    website: "https://reservevaparks.com/Web",
    features: ["Mountain Camping", "Coastal Sites", "Historic Parks", "Cabins"],
    coverage: ["Virginia State Parks"],
  },
  {
    name: "Fairfax County Parks",
    description:
      "Local parks and recreation booking system for Fairfax County, Virginia.",
    website: "https://fairfax.usedirect.com/FairfaxFCPAWeb",
    features: [
      "Local Parks",
      "Recreation Centers",
      "Group Sites",
      "Special Events",
    ],
    coverage: ["Fairfax County, VA"],
  },
  {
    name: "Oregon Metro",
    description:
      "Regional parks and natural areas in the Portland metropolitan region.",
    website: "https://reservemetro.usedirect.com/MetroWeb",
    features: [
      "Regional Parks",
      "Natural Areas",
      "Trail Access",
      "Environmental Programs",
    ],
    coverage: ["Portland Metro Area, OR"],
  },
  {
    name: "Northern Territory",
    description:
      "Australian park booking system for Northern Territory's unique landscapes and wildlife areas.",
    website: "https://parkbookings.nt.gov.au/Web",
    features: [
      "Outback Camping",
      "Wildlife Parks",
      "Cultural Sites",
      "Adventure Tourism",
    ],
    coverage: ["Northern Territory, Australia"],
  },
  {
    name: "Washington State Parks",
    description:
      "Reservation system for Washington State Parks campgrounds, cabins, and yurts.",
    website: "https://washington.goingtocamp.com",
    features: ["Coastal Camping", "Mountain Sites", "Cabins & Yurts"],
    coverage: ["Washington State Parks"],
  },
  {
    name: "Wisconsin State Parks",
    description:
      "Reservation portal for Wisconsin State Parks, forests, and trails.",
    website: "https://wisconsin.goingtocamp.com",
    features: ["Lake Camping", "Forest Sites", "Group Camps"],
    coverage: ["Wisconsin State Parks"],
  },
  {
    name: "Michigan State Parks",
    description:
      "Michigan Department of Natural Resources reservation portal for state parks and campgrounds.",
    website: "https://midnrreservations.com",
    features: ["Great Lakes Camping", "State Forests", "Cabins & Lodges"],
    coverage: ["Michigan State Parks"],
  },
  {
    name: "Tacoma Power Parks",
    description:
      "Camping and recreation reservations along Tacoma Power hydroelectric reservoirs.",
    website: "https://tacomapower.goingtocamp.com",
    features: ["Lake Camping", "RV Sites", "Tent Sites"],
    coverage: ["Washington"],
  },
  {
    name: "Parks Canada",
    description:
      "Federal reservation portal for Canadian National Parks, National Marine Conservation Areas, and historic sites.",
    website: "https://reservation.pc.gc.ca",
    features: ["National Parks", "Backcountry", "oTENTiks & Cabins"],
    coverage: ["Canada"],
  },
  {
    name: "BC Parks",
    description:
      "British Columbia provincial parks reservation portal for frontcountry and backcountry camping.",
    website: "https://camping.bcparks.ca",
    features: ["Mountain Camping", "Coastal Sites", "Backcountry"],
    coverage: ["British Columbia, Canada"],
  },
  {
    name: "Ontario Parks",
    description:
      "Ontario provincial parks reservation system for campsites, backcountry, and roofed accommodations.",
    website: "https://reservations.ontarioparks.ca",
    features: ["Lake Camping", "Backcountry", "Cabins & Yurts"],
    coverage: ["Ontario, Canada"],
  },
  {
    name: "Nova Scotia Parks",
    description:
      "Provincial park campground and yurt reservations across Nova Scotia.",
    website: "https://novascotia.goingtocamp.com",
    features: ["Coastal Camping", "Yurts", "Tent & RV Sites"],
    coverage: ["Nova Scotia, Canada"],
  },
  {
    name: "Manitoba Parks",
    description:
      "Manitoba provincial park campground, yurt, and cabin reservations.",
    website: "https://manitoba.goingtocamp.com",
    features: ["Lake Camping", "Yurts & Cabins", "Group Sites"],
    coverage: ["Manitoba, Canada"],
  },
  {
    name: "Newfoundland & Labrador Provincial Parks",
    description:
      "Camping reservations for Newfoundland and Labrador provincial parks.",
    website: "https://www.nlcamping.ca",
    features: ["Coastal Camping", "RV & Tent Sites", "Group Camping"],
    coverage: ["Newfoundland & Labrador, Canada"],
  },
  {
    name: "Gatineau Park",
    description:
      "National Capital Commission campsite and cabin reservations in Gatineau Park.",
    website: "https://reservations.ncc-ccn.gc.ca",
    features: ["Forest Camping", "Cabins & Yurts", "Backcountry"],
    coverage: ["Quebec, Canada"],
  },
  {
    name: "Long Point Region",
    description:
      "Long Point Region Conservation Authority campground reservations along Lake Erie.",
    website: "https://longpoint.goingtocamp.com",
    features: ["Lake Erie Camping", "Conservation Areas", "RV & Tent Sites"],
    coverage: ["Ontario, Canada"],
  },
  {
    name: "Maitland Valley",
    description:
      "Maitland Valley Conservation Authority campground reservations at Falls Reserve.",
    website: "https://maitlandvalley.goingtocamp.com",
    features: ["Conservation Areas", "Family Camping", "RV & Tent Sites"],
    coverage: ["Ontario, Canada"],
  },
  {
    name: "St. Clair Region",
    description:
      "St. Clair Region Conservation Authority campground reservations in southwestern Ontario.",
    website: "https://stclair.goingtocamp.com",
    features: ["Conservation Areas", "Riverfront Camping", "RV & Tent Sites"],
    coverage: ["Ontario, Canada"],
  },
];

export function Providers() {
  return (
    <div className="container mx-auto py-12 px-4 max-w-6xl">
      {/* Hero Section */}
      <div className="text-center mb-16">
        <div className="mb-6">
          <Caravan className="h-16 w-16 text-primary mx-auto mb-4" />
        </div>
        <h1 className="text-4xl font-bold mb-6 sm:text-5xl">
          Supported <span className="text-primary">Providers</span>
        </h1>
        <p className="text-xl text-muted-foreground mb-8 max-w-4xl mx-auto leading-relaxed">
          camply monitors availability across major booking platforms and
          recreation systems. Find campsites from thousands of campgrounds
          nationwide.
        </p>

        <div className="flex flex-wrap justify-center gap-6 text-sm text-muted-foreground">
          <span className="flex items-center gap-2">
            <MapPin className="h-4 w-4" />
            26 Booking Platforms
          </span>
          <span className="flex items-center gap-2">
            <Users className="h-4 w-4" />
            Federal, State & Provincial Parks
          </span>
          <span className="flex items-center gap-2">
            <Calendar className="h-4 w-4" />
            Real-time Availability
          </span>
        </div>
      </div>

      <div className="mb-8">
        <SearchBar
          placeholder="Search campgrounds..."
          className="max-w-3xl mx-auto"
        />
      </div>

      {/* Popular Providers */}
      <section className="mb-16">
        <h2 className="text-3xl font-bold text-center mb-4">
          Most Popular Providers
        </h2>
        <p className="text-muted-foreground text-center mb-12 max-w-2xl mx-auto">
          These platforms offer the largest selection of campgrounds and are
          monitored most frequently by camply.
        </p>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 mb-12">
          {providers
            .filter((p) => p.popular)
            .map((provider) => (
              <Card key={provider.name} className="relative">
                {provider.popular && (
                  <div className="absolute -top-3 left-4">
                    <span className="bg-primary text-primary-foreground px-3 py-1 rounded-full text-xs font-medium flex items-center gap-1">
                      <Star className="h-3 w-3" />
                      Popular
                    </span>
                  </div>
                )}
                <CardHeader>
                  {provider.logo && (
                    <img
                      src={provider.logo}
                      alt={`${provider.name} logo`}
                      width={185}
                      height={24}
                      className="max-w-full object-contain self-start rounded bg-white p-2 box-content"
                    />
                  )}
                  <CardTitle className="flex items-center justify-between max-sm:flex-wrap max-sm:gap-2">
                    {provider.name}
                    <a
                      href={provider.website}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-muted-foreground hover:text-foreground transition-colors"
                    >
                      <ExternalLink className="h-4 w-4" />
                    </a>
                  </CardTitle>
                  <CardDescription>{provider.description}</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div>
                      <h4 className="font-semibold text-sm mb-2">Coverage:</h4>
                      <div className="flex flex-wrap gap-1">
                        {provider.coverage.map((area) => (
                          <span
                            key={area}
                            className="bg-secondary text-secondary-foreground px-2 py-1 rounded-md text-xs"
                          >
                            {area}
                          </span>
                        ))}
                      </div>
                    </div>

                    <div>
                      <h4 className="font-semibold text-sm mb-2">Features:</h4>
                      <ul className="text-sm text-muted-foreground space-y-1">
                        {provider.features.slice(0, 3).map((feature) => (
                          <li key={feature} className="flex items-center gap-2">
                            <div className="w-1 h-1 bg-primary rounded-full"></div>
                            {feature}
                          </li>
                        ))}
                      </ul>
                    </div>

                    {provider.campgroundCount && (
                      <div className="text-sm">
                        <span className="font-semibold">
                          {provider.campgroundCount.toLocaleString()}+
                        </span>
                        <span className="text-muted-foreground">
                          {" "}
                          campgrounds
                        </span>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
        </div>
      </section>

      {/* All Providers */}
      <section className="mb-16">
        <h2 className="text-3xl font-bold text-center mb-4">
          All Supported Providers
        </h2>
        <p className="text-muted-foreground text-center mb-12 max-w-2xl mx-auto">
          Complete list of booking platforms and reservation systems that camply
          monitors for availability.
        </p>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {providers.map((provider) => (
            <Card key={provider.name}>
              <CardHeader>
                {provider.logo && (
                  <img
                    src={provider.logo}
                    alt={`${provider.name} logo`}
                    width={185}
                    height={24}
                    className="max-w-full object-contain self-start rounded bg-white p-2 box-content"
                  />
                )}
                <CardTitle className="flex items-center justify-between max-sm:flex-wrap max-sm:gap-2">
                  {provider.name}
                  <a
                    href={provider.website}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-muted-foreground hover:text-foreground transition-colors"
                  >
                    <ExternalLink className="h-4 w-4" />
                  </a>
                </CardTitle>
                <CardDescription>{provider.description}</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div>
                    <div className="flex flex-wrap gap-1">
                      {provider.coverage.map((area) => (
                        <span
                          key={area}
                          className="bg-secondary text-secondary-foreground px-2 py-1 rounded-md text-xs"
                        >
                          {area}
                        </span>
                      ))}
                    </div>
                  </div>

                  {provider.campgroundCount && (
                    <div className="text-sm">
                      <span className="font-semibold">
                        {provider.campgroundCount.toLocaleString()}+
                      </span>
                      <span className="text-muted-foreground">
                        {" "}
                        campgrounds
                      </span>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      {/* Coming Soon */}
      <section className="text-center">
        <h2 className="text-3xl font-bold mb-4">More Providers Coming Soon</h2>
        <p className="text-xl text-muted-foreground mb-8 max-w-2xl mx-auto">
          We're constantly adding support for new booking platforms and
          recreation systems. Have a specific provider you'd like us to support?
        </p>
        <div className="flex flex-col sm:flex-row gap-4 justify-center [&_a]:min-h-11 sm:[&_a]:min-h-0">
          <Button size="lg" asChild>
            <a
              href="https://github.com/juftin/camply-web/issues/new?template=feature_request.md"
              target="_blank"
              rel="noopener noreferrer"
            >
              Request a Provider
            </a>
          </Button>
          <Button size="lg" variant="outline" asChild>
            <Link to="/faq">View FAQ</Link>
          </Button>
        </div>
      </section>
    </div>
  );
}
