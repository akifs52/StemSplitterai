import react from "@vitejs/plugin-react";
import { defineConfig, Plugin } from "vite";
import { VitePWA } from "vite-plugin-pwa";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const isVercel = Boolean(process.env.VERCEL || process.env.NOW_BUILDER);
const base = isVercel ? "/" : "/static/";
const outDir = isVercel ? "dist" : "../web/static";

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

function vercelBuildEnhancer(): Plugin {
  return {
    name: "vercel-build-enhancer",
    apply: "build",
    buildStart() {
      // Ensure frontend/public/static exists with fonts & pwa icons for universal path resolution
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
      // Sync build output so both dist and ../web/static are always present
      if (isVercel) {
        const distIndex = path.resolve(__dirname, "dist/index.html");
        const dist200 = path.resolve(__dirname, "dist/200.html");
        if (fs.existsSync(distIndex) && !fs.existsSync(dist200)) {
          fs.copyFileSync(distIndex, dist200);
        }
      } else {
        const webStatic = path.resolve(__dirname, "../web/static");
        const distDir = path.resolve(__dirname, "dist");
        if (fs.existsSync(webStatic)) {
          copyFolderRecursiveSync(webStatic, distDir);
        }
      }
    }
  };
}

export default defineConfig({
  base,
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
          "": base
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
            src: `${base}pwa-192.png`.replace(/\/\//g, "/"),
            sizes: "192x192",
            type: "image/png"
          },
          {
            src: `${base}pwa-512.png`.replace(/\/\//g, "/"),
            sizes: "512x512",
            type: "image/png"
          },
          {
            src: `${base}pwa-maskable-512.png`.replace(/\/\//g, "/"),
            sizes: "512x512",
            type: "image/png",
            purpose: "maskable"
          }
        ]
      }
    }),
    vercelBuildEnhancer()
  ],
  build: {
    outDir,
    emptyOutDir: true,
    assetsDir: "vite-assets",
    sourcemap: false
  }
});
