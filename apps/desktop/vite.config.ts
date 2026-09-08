import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';
export default defineConfig({
  plugins: [svelte()],
  clearScreen: false,
  server: { port: 1487, strictPort: true, watch: { ignored: ['**/src-tauri/**', '**/target/**'] } },
});
