import { defineConfig } from 'vite';

/**
 * De leeromgeving is een statische build zonder netwerkafhankelijkheid.
 * Content wordt tijdens de build in de bundle opgenomen (zie src/web/content.ts),
 * zodat de app ook werkt wanneer ze rechtstreeks van schijf geopend wordt.
 */
export default defineConfig({
  root: 'src/web',
  base: './',
  build: {
    outDir: '../../dist/web',
    emptyOutDir: true,
    target: 'es2022',
    assetsInlineLimit: 8192,
    rollupOptions: {
      output: {
        manualChunks: undefined,
      },
    },
  },
  server: {
    port: 5173,
    open: false,
  },
});
