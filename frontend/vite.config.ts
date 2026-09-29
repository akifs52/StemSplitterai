import react from "@vitejs/plugin-react";
import { defineConfig, Plugin } from "vite";
import { VitePWA } from "vite-plugin-pwa";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

function copyFolderRecursiveSync(source: string, target: string) {
  if (!fs.existsSync(source)) return;
  if (!fs.existsSync(target)) {
    fs.mkdirSync(target, { recursive: true });
  }
  const files = fs.readdirSync(source);
  for (const file of files) {
    const curSource = path.join(source, file);
    const curTarget = path.join(target, file);
    if (fs.lstatSync(curSource).isDirectory()) {
      copyFolderRecursiveSync(curSource, curTarget);
    } else {
      fs.copyFileSync(curSource, curTarget);
    }
  }
}

function universalBuildDistSync(): Plugin {
  return {
    name: "universal-build-dist-sync",
    apply: "build",
    buildStart() {
      // Ensure frontend/public/static exists with fonts & pwa icons for any legacy /static requests
      const publicDir = path.resolve(__dirname, "public");
      const staticDir = path.join(publicDir, "static");
      const fontsDir = path.join(publicDir, "fonts");
      if (fs.existsSync(fontsDir)) {
        copyFolderRecursiveSync(fontsDir, path.join(staticDir, "fonts"));
      }
      if (fs.existsSync(publicDir)) {
        for (const item of fs.readdirSync(publicDir)) {
          if (item.startsWith("pwa-") && item.endsWith(".png")) {
            fs.mkdirSync(staticDir, { recursive: true });
            fs.copyFileSync(path.join(publicDir, item), path.join(staticDir, item));
          }
        }
      }
    },
    closeBundle() {
      const distDir = path.resolve(__dirname, "dist");
      const rootDistDir = path.resolve(__dirname, "../dist");
      const webStaticDir = path.resolve(__dirname, "../web/static");

      // 1. Generate 200.html SPA fallback inside dist
      const distIndex = path.join(distDir, "index.html");
      const dist200 = path.join(distDir, "200.html");
      if (fs.existsSync(distIndex)) {
        fs.copyFileSync(distIndex, dist200);
      }

      // 2. Mirror dist to root ../dist (for root-level Vercel builds)
      copyFolderRecursiveSync(distDir, rootDistDir);

      // 3. Mirror dist to ../web/static (for Docker and local FastAPI server)
      copyFolderRecursiveSync(distDir, webStaticDir);
    }
  };
}

export default defineConfig({
  base: "/",
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
          "": "/"
        },
        maximumFileSizeToCacheInBytes: 5 * 1024 * 1024
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
            src: "/pwa-192.png",
            sizes: "192x192",
            type: "image/png"
          },
          {
            src: "/pwa-512.png",
            sizes: "512x512",
            type: "image/png"
          },
          {
            src: "/pwa-maskable-512.png",
            sizes: "512x512",
            type: "image/png",
            purpose: "maskable"
          }
        ]
      }
    }),
    universalBuildDistSync()
  ],
  build: {
    outDir: "dist",
    emptyOutDir: true,
    assetsDir: "vite-assets",
    sourcemap: false
  }
});
