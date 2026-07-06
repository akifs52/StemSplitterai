import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  base: "/static/",
  plugins: [
    react(),
    VitePWA({
      strategies: "injectManifest",
      injectRegister: false,
      srcDir: "src",
      filename: "sw.ts",
      manifestFilename: "manifest.webmanifest",
      registerType: "autoUpdate",
      injectManifest: {
        globPatterns: ["**/*.{js,css,html,png,svg,ico,webmanifest,ttf,woff2}"],
        modifyURLPrefix: {
          "": "/static/"
        },
        maximumFileSizeToCacheInBytes: 3 * 1024 * 1024
      },
      manifest: {
        name: "StemSplit AI",
        short_name: "StemSplit",
        description: "AI-powered audio stem separation workspace.",
        theme_color: "#101212",
        background_color: "#101212",
        display: "standalone",
        scope: "/",
        start_url: "/",
        icons: [
          {
            src: "/static/pwa-192.png",
            sizes: "192x192",
            type: "image/png"
          },
          {
            src: "/static/pwa-512.png",
            sizes: "512x512",
            type: "image/png"
          },
          {
            src: "/static/pwa-maskable-512.png",
            sizes: "512x512",
            type: "image/png",
            purpose: "maskable"
          }
        ]
      }
    })
  ],
  build: {
    outDir: "../web/static",
    emptyOutDir: true,
    assetsDir: "vite-assets",
    sourcemap: false
  }
});
