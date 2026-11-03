import { defineConfig } from "vitepress";

export default defineConfig({
  title: "camply docs",
  description: "Find a campsite. Get notified when a stay opens up.",
  base: process.env.VITEPRESS_BASE || "/docs/",
  outDir: "../build/docs",
  ignoreDeadLinks: true,
  head: [
    ["link", { rel: "shortcut icon", href: "/docs/favicon.ico" }],
    ["link", { rel: "icon", type: "image/svg+xml", href: "/docs/favicon.svg" }],
  ],
  themeConfig: {
    logo: {
      light: "/branding/camply-horizontal.svg",
      dark: "/branding/camply-horizontal-dark.svg",
      alt: "camply",
    },
    siteTitle: "Docs",
    nav: [
      { text: "Overview", link: "/" },
      { text: "Using camply", link: "/using-camply" },
      {
        text: "Self-hosting",
        items: [
          { text: "Standalone", link: "/self-hosting/standalone" },
          { text: "Docker & Kubernetes", link: "/self-hosting/containers" },
          { text: "Configuration Guide", link: "/configuration" },
        ],
      },
      {
        text: "Operations",
        items: [
          {
            text: "Configuration Reference",
            link: "/operations/CONFIGURATION",
          },
          { text: "Running & Packaging", link: "/operations/RUNNING" },
          { text: "Release Operations", link: "/operations/RELEASES" },
        ],
      },
      {
        text: "Architecture",
        items: [
          {
            text: "Polling Deep Dive",
            link: "/architecture/ARCHITECTURE_DEEP_DIVE",
          },
          { text: "Data Models", link: "/architecture/DESIGN_DATA" },
          { text: "API Contract & Security", link: "/architecture/DESIGN_API" },
          { text: "Frontend Journey", link: "/architecture/DESIGN_FRONTEND" },
          { text: "Notifications", link: "/architecture/DESIGN_NOTIFICATIONS" },
          { text: "Providers", link: "/architecture/DESIGN_PROVIDERS" },
        ],
      },
      {
        text: "Development",
        items: [
          { text: "Developer Guide", link: "/development/DEVELOPER_GUIDE" },
          { text: "Style Guide", link: "/development/STYLE_GUIDE" },
          {
            text: "Troubleshooting",
            link: "/development/AGENT_TROUBLESHOOTING",
          },
          { text: "Agentic Tooling", link: "/development/DESIGN_AGENTIC" },
          { text: "Roadmap & Plan", link: "/PLAN" },
          { text: "Feature Checklist", link: "/CHECKLIST" },
        ],
      },
      {
        text: "Reference",
        items: [
          { text: "Reference Hub", link: "/reference" },
          { text: "Specifications Catalog", link: "/specs/" },
        ],
      },
    ],
    sidebar: [
      {
        text: "Guide",
        items: [
          { text: "Overview", link: "/" },
          { text: "Using camply", link: "/using-camply" },
        ],
      },
      {
        text: "Self-hosting",
        collapsed: false,
        items: [
          { text: "Standalone", link: "/self-hosting/standalone" },
          { text: "Docker and Kubernetes", link: "/self-hosting/containers" },
          { text: "Configuration Guide", link: "/configuration" },
        ],
      },
      {
        text: "Operations",
        collapsed: false,
        items: [
          {
            text: "Configuration Reference",
            link: "/operations/CONFIGURATION",
          },
          { text: "Running & Packaging", link: "/operations/RUNNING" },
          { text: "Release Operations", link: "/operations/RELEASES" },
        ],
      },
      {
        text: "Architecture",
        collapsed: false,
        items: [
          {
            text: "Polling Deep Dive",
            link: "/architecture/ARCHITECTURE_DEEP_DIVE",
          },
          { text: "Data Models", link: "/architecture/DESIGN_DATA" },
          { text: "API Contract & Security", link: "/architecture/DESIGN_API" },
          { text: "Frontend Journey", link: "/architecture/DESIGN_FRONTEND" },
          { text: "Notifications", link: "/architecture/DESIGN_NOTIFICATIONS" },
          { text: "Providers", link: "/architecture/DESIGN_PROVIDERS" },
        ],
      },
      {
        text: "Development & Planning",
        collapsed: false,
        items: [
          { text: "Developer Quickstart", link: "/development" },
          { text: "Developer Guide", link: "/development/DEVELOPER_GUIDE" },
          { text: "Style Guide", link: "/development/STYLE_GUIDE" },
          {
            text: "Troubleshooting",
            link: "/development/AGENT_TROUBLESHOOTING",
          },
          { text: "Agentic Tooling", link: "/development/DESIGN_AGENTIC" },
          { text: "Roadmap & Plan", link: "/PLAN" },
          { text: "Feature Checklist", link: "/CHECKLIST" },
        ],
      },
      {
        text: "Reference",
        collapsed: false,
        items: [
          { text: "Reference Hub", link: "/reference" },
          { text: "Specifications Catalog", link: "/specs/" },
        ],
      },
    ],
    search: {
      provider: "local",
    },
    socialLinks: [
      { icon: "github", link: "https://github.com/juftin/camply-web" },
    ],
  },
});
