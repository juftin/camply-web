import { defineConfig } from "vitepress";

const defaultSidebar = [
  {
    text: "User Documentation",
    items: [
      { text: "Overview", link: "/" },
      { text: "Web App", link: "/using-camply" },
      { text: "Command Line", link: "/cli" },
    ],
  },
  {
    text: "Self-Hosting",
    items: [
      { text: "Overview", link: "/self-hosting/" },
      { text: "Standalone", link: "/self-hosting/standalone" },
      { text: "Docker & Kubernetes", link: "/self-hosting/containers" },
      { text: "Configuration", link: "/self-hosting/configuration" },
      { text: "Maintenance", link: "/self-hosting/maintenance" },
    ],
  },
];

const technicalSidebar = [
  {
    text: "Technical & Architectural",
    items: [
      { text: "Overview", link: "/technical/" },
      { text: "Contributing", link: "/CONTRIBUTING" },
      { text: "Developer Guide", link: "/development/DEVELOPER_GUIDE" },
      { text: "Style Guide", link: "/development/STYLE_GUIDE" },
    ],
  },
  {
    text: "Architecture",
    items: [
      { text: "Polling Engine", link: "/architecture/ARCHITECTURE_DEEP_DIVE" },
      { text: "Data Model", link: "/architecture/DESIGN_DATA" },
      { text: "Providers", link: "/architecture/DESIGN_PROVIDERS" },
      { text: "Notifications", link: "/architecture/DESIGN_NOTIFICATIONS" },
      { text: "API & Security", link: "/architecture/DESIGN_API" },
      { text: "Frontend", link: "/architecture/DESIGN_FRONTEND" },
    ],
  },
];

const referenceSidebar = [
  {
    text: "Technical Reference",
    items: [
      { text: "Reference Hub", link: "/reference" },
      { text: "Environment Variables", link: "/operations/CONFIGURATION" },
      { text: "Runtime & Packaging", link: "/operations/RUNNING" },
      { text: "Release Operations", link: "/operations/RELEASES" },
    ],
  },
  {
    text: "Specs & Planning",
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

export default defineConfig({
  title: "camply docs",
  description: "Find a campsite. Get notified when a stay opens up.",
  base: process.env.VITEPRESS_BASE || "/docs/",
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
        if (token.info.trim() === "mermaid") {
          return `<MermaidDiagram code="${encodeURIComponent(token.content)}" />`;
        }
        return defaultFence
          ? defaultFence(tokens, idx, options, env, self)
          : self.renderToken(tokens, idx, options);
      };
    },
  },
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
    sidebar: {
      "/technical/": technicalSidebar,
      "/CONTRIBUTING": technicalSidebar,
      "/development/DEVELOPER_GUIDE": technicalSidebar,
      "/development/STYLE_GUIDE": technicalSidebar,
      "/architecture/": technicalSidebar,
      "/reference": referenceSidebar,
      "/operations/": referenceSidebar,
      "/specs/": referenceSidebar,
      "/PLAN": referenceSidebar,
      "/CHECKLIST": referenceSidebar,
      "/development/DESIGN_AGENTIC": referenceSidebar,
      "/development/AGENT_TROUBLESHOOTING": referenceSidebar,
      "/": defaultSidebar,
    },
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
