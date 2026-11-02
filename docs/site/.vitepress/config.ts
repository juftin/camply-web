import { defineConfig } from "vitepress";

export default defineConfig({
  title: "camply docs",
  description: "Find a campsite. Get notified when a stay opens up.",
  base: process.env.VITEPRESS_BASE || "/docs/",
  outDir: "../../build/docs",
  ignoreDeadLinks: [/^https?:\/\/localhost/, /^https?:\/\/127\.0\.0\.1/],
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
      { text: "Home", link: "/" },
      { text: "Using camply", link: "/using-camply" },
      {
        text: "Self-hosting",
        items: [
          { text: "Standalone", link: "/self-hosting/standalone" },
          { text: "Docker & Kubernetes", link: "/self-hosting/containers" },
        ],
      },
      { text: "Configuration", link: "/configuration" },
      { text: "Development", link: "/development" },
      { text: "Reference", link: "/reference" },
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
        items: [
          { text: "Standalone", link: "/self-hosting/standalone" },
          { text: "Docker and Kubernetes", link: "/self-hosting/containers" },
        ],
      },
      {
        text: "Operations & Contributing",
        items: [
          { text: "Configuration", link: "/configuration" },
          { text: "Development", link: "/development" },
          { text: "Reference", link: "/reference" },
        ],
      },
    ],
    search: {
      provider: "local",
    },
    socialLinks: [
      { icon: "github", link: "https://github.com/juftin/camply-web" },
    ],
    editLink: {
      pattern: "https://github.com/juftin/camply-web/edit/main/docs/site/:path",
      text: "Edit this page on GitHub",
    },
  },
});
