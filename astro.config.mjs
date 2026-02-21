import { defineConfig } from "astro/config";
import starlight from "@astrojs/starlight";
import sitemap from "@astrojs/sitemap";
import robotsTxt from "astro-robots-txt";
import rehypeExternalLinks from "rehype-external-links";

// https://astro.build/config
export default defineConfig({
  site: "https://sigenergy.annable.me",
  integrations: [
    sitemap(),
    robotsTxt(),
    starlight({
      title: "Sigenergy with Home Assistant",
      description:
        "Step-by-step guides for automating a Sigenergy system with Home Assistant using EMHASS or HAEO and Amber Electric in Australia.",
      tableOfContents: false,
      head: [
        {
          tag: "script",
          attrs: {
            async: true,
            src: "https://www.googletagmanager.com/gtag/js?id=G-HNTKBKHJY3",
          },
        },
        {
          tag: "script",
          attrs: {},
          content: `
            window.dataLayer = window.dataLayer || [];
            function gtag() {
              dataLayer.push(arguments);
            }
            gtag("js", new Date());
            gtag("config", "G-HNTKBKHJY3");
          `,
        },
        {
          tag: "script",
          attrs: {},
          content: `
            // Set dark mode as default if no preference is stored
            if (!localStorage.getItem('starlight-theme')) {
              localStorage.setItem('starlight-theme', 'dark');
              document.documentElement.dataset.theme = 'dark';
            }
          `,
        },
      ],
      customCss: ["./src/styles/custom.css"],
      sidebar: [
        { label: "Home", link: "/" },
        {
          label: "HAEO Guide",
          items: [
            { label: "Introduction", link: "/haeo" },
            { label: "Architecture", link: "/haeo/architecture" },
            { label: "Prerequisites", link: "/haeo/prerequisites" },
            { label: "HAEO Setup", link: "/haeo/setup" },
            { label: "Dashboard", link: "/haeo/dashboard" },
            { label: "Battery Automation", link: "/haeo/automation" },
            { label: "Conclusion", link: "/haeo/conclusion" },
            {
              label: "Debugging",
              items: [{ label: "Download Diagnostic", link: "/haeo/diagnostic" }],
            },
          ],
        },
        {
          label: "EMHASS Guide",
          items: [
            { label: "Introduction", link: "/emhass" },
            { label: "Architecture", link: "/emhass/architecture" },
            { label: "Prerequisites", link: "/emhass/prerequisites" },
            { label: "EMHASS Setup", link: "/emhass/setup" },
            { label: "Running EMHASS", link: "/emhass/emhass" },
            { label: "Dashboard", link: "/emhass/dashboard" },
            { label: "Battery Automation", link: "/emhass/automation" },
            { label: "Conclusion", link: "/emhass/conclusion" },
            { label: "Debugging",
              items: [{ label: "Trace Downloading", link: "/emhass/trace" }],
            },
          ],
        },
      ],
    }),
  ],
  compressHTML: false,
  markdown: {
    shikiConfig: {
      theme: "github-dark-default",
    },
    rehypePlugins: [
      [
        rehypeExternalLinks,
        {
          target: "_blank",
          rel: ["noopener", "noreferrer"],
        },
      ],
    ],
  },
  redirects: {
    // Legacy /pages/ redirects
    "/pages/architecture": "/emhass/architecture",
    "/pages/automation": "/emhass/automation",
    "/pages/conclusion": "/emhass/conclusion",
    "/pages/dashboard": "/emhass/dashboard",
    "/pages/emhass": "/emhass/emhass",
    "/pages/prerequisites": "/emhass/prerequisites",
    "/pages/setup": "/emhass/setup",
    // Old root-level redirects to new EMHASS paths
    "/architecture": "/emhass/architecture",
    "/automation": "/emhass/automation",
    "/conclusion": "/emhass/conclusion",
    "/dashboard": "/emhass/dashboard",
    "/prerequisites": "/emhass/prerequisites",
    "/setup": "/emhass/setup",
    "/trace": "/emhass/trace",
  },
});
