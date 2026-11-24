import { defineConfig, type DefaultTheme } from "vitepress";

interface CamplyThemeConfig extends DefaultTheme.Config {
  showBackToApp?: boolean;
}

const sidebar = [
  {
    text: "User Documentation",
    collapsed: false,
    items: [
      { text: "Overview", link: "/" },
      { text: "Web App", link: "/using-camply" },
      { text: "Command Line", link: "/cli" },
    ],
  },
  {
    text: "Self-Hosting",
    collapsed: false,
    items: [
      { text: "Overview", link: "/self-hosting/" },
      { text: "Standalone", link: "/self-hosting/standalone" },
      { text: "Docker & Kubernetes", link: "/self-hosting/containers" },
      { text: "Configuration", link: "/self-hosting/configuration" },
      { text: "Maintenance", link: "/self-hosting/maintenance" },
    ],
  },
  {
    text: "Technical & Architectural",
    collapsed: true,
    items: [
      { text: "Overview", link: "/technical/" },
      { text: "Contributing", link: "/CONTRIBUTING" },
      { text: "Developer Guide", link: "/development/DEVELOPER_GUIDE" },
      { text: "Style Guide", link: "/development/STYLE_GUIDE" },
      {
        text: "Architecture",
        collapsed: true,
        items: [
          {
            text: "Polling Engine",
            link: "/architecture/ARCHITECTURE_DEEP_DIVE",
          },
          { text: "Data Model", link: "/architecture/DESIGN_DATA" },
          { text: "Providers", link: "/architecture/DESIGN_PROVIDERS" },
          { text: "Notifications", link: "/architecture/DESIGN_NOTIFICATIONS" },
          { text: "API & Security", link: "/architecture/DESIGN_API" },
          { text: "Frontend", link: "/architecture/DESIGN_FRONTEND" },
        ],
      },
    ],
  },
  {
    text: "Technical Reference",
    collapsed: true,
    items: [
      { text: "Reference Hub", link: "/reference" },
      { text: "Environment Variables", link: "/operations/CONFIGURATION" },
      { text: "Runtime & Packaging", link: "/operations/RUNNING" },
      { text: "Release Operations", link: "/operations/RELEASES" },
      { text: "License", link: "/license" },
      {
        text: "Specs & Planning",
        collapsed: true,
        items: [
          { text: "Specifications Catalog", link: "/specs/" },
          { text: "Roadmap & Plan", link: "/PLAN" },
          { text: "Feature Checklist", link: "/CHECKLIST" },
          { text: "Agentic Tooling", link: "/development/DESIGN_AGENTIC" },
          {
            text: "Agent Troubleshooting",
            link: "/development/AGENT_TROUBLESHOOTING",
          },
        ],
      },
    ],
  },
];

const EXCLUDED_SEARCH_PATHS = [
  "specs/",
  "PLAN.md",
  "CHECKLIST.md",
  "development/DESIGN_AGENTIC.md",
  "development/AGENT_TROUBLESHOOTING.md",
];

function isExcludedFromSearch(relativePath: string): boolean {
  return EXCLUDED_SEARCH_PATHS.some((prefix) =>
    relativePath.startsWith(prefix),
  );
}

function normalizeBase(rawBase: string | undefined): string {
  const value = rawBase || "/docs/";
  return value.endsWith("/") ? value : `${value}/`;
}

const base = normalizeBase(process.env.VITEPRESS_BASE);
const showBackToApp = process.env.CAMPLY_DOCS_EMBEDDED === "1";

export default defineConfig<CamplyThemeConfig>({
  title: "camply docs",
  description: "Find a campsite. Get notified when a stay opens up.",
  base,
  outDir: "../build/docs",
  ignoreDeadLinks: true,
  vite: {
    build: {
      chunkSizeWarningLimit: 2000,
    },
  },
  markdown: {
    config(md) {
      const defaultFence = md.renderer.rules.fence?.bind(md.renderer.rules);
      md.renderer.rules.fence = (tokens, idx, options, env, self) => {
        const token = tokens[idx];
        const lang = token.info.trim().split(/\s+/)[0]?.toLowerCase() ?? "";
        if (lang === "mermaid") {
          return `<MermaidDiagram code="${encodeURIComponent(token.content)}" />`;
        }
        return defaultFence
          ? defaultFence(tokens, idx, options, env, self)
          : self.renderToken(tokens, idx, options);
      };
    },
  },
  head: [
    ["link", { rel: "shortcut icon", href: `${base}favicon.ico` }],
    [
      "link",
      { rel: "icon", type: "image/svg+xml", href: `${base}favicon.svg` },
    ],
  ],
  themeConfig: {
    showBackToApp,
    logo: {
      light: "/branding/camply-horizontal.svg",
      dark: "/branding/camply-horizontal-dark.svg",
      alt: "camply",
    },
    siteTitle: "Docs",
    nav: [
      { text: "User Guide", link: "/using-camply" },
      { text: "CLI", link: "/cli" },
      { text: "Self-Hosting", link: "/self-hosting/" },
      {
        text: "Technical",
        items: [
          { text: "Architecture & Contributing", link: "/technical/" },
          { text: "Technical Reference", link: "/reference" },
        ],
      },
    ],
    sidebar,
    search: {
      provider: "local",
      options: {
        miniSearch: {
          searchOptions: {
            boost: {
              title: 4,
              titles: 2,
              text: 1,
            },
            boostDocument: (documentId: string): number => {
              const route = (documentId.split("#")[0] ?? "").toLowerCase();
              if (route.includes("/self-hosting/")) {
                return 2;
              }
              if (
                route.includes("/operations/") ||
                route.includes("/architecture/")
              ) {
                return 0.5;
              }
              if (
                route.includes("/technical/") ||
                route.includes("/development/") ||
                route.includes("/contributing") ||
                route.includes("/reference") ||
                route.includes("/license")
              ) {
                return 1;
              }
              return 2;
            },
          },
        },
        _render(src, env, md) {
          if (isExcludedFromSearch(env.relativePath)) {
            return "";
          }
          const html = md.render(src, env);
          return env.frontmatter?.search === false ? "" : html;
        },
      },
    },
    socialLinks: [
      { icon: "github", link: "https://github.com/juftin/camply-web" },
    ],
  },
});
