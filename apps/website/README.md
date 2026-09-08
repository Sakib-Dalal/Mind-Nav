# Mind-Nav handbook

The project documentation website, built with Svelte 5, TypeScript, and Vite. It covers the current Rust/Tauri desktop application and v2 Arduino acquisition firmware.

## Run locally

Use Node.js 22.12+ or a newer supported LTS.

```sh
cd apps/website
npm ci
npm run dev
```

The development server uses `http://127.0.0.1:1490`.

```sh
npm run check
npm run build
npm run preview
```

`dist/` contains the complete static site. The production preview uses port 1491. Fragment routes such as `#/hardware/pin-map` work on static hosting without rewrite rules. This website has no native EEG runtime or access to recordings.

## Content and assets

- `src/lib/navigation.ts`: the 14 documentation chapters and sidebar groups.
- `src/lib/content.ts`: structured chapter content, source references, tables, and code examples.
- `src/components/Overview.svelte`: handbook introduction and workflow.
- `src/components/Diagram.svelte`: interactive wiring highlights and processing flow.
- `src/assets/wiring-v2.svg`: logical wiring diagram embedded by the site.
- `public/assets/wiring-v2.svg`: identical downloadable copy; keep it synchronized with the embedded source.
- `public/downloads/`: exact copies of current hardware, signal, validation documents, and v2 firmware.

The site preserves the desktop crown, navy/orange identity, locally bundled Manrope font, and existing Svelte dependency versions. Keep the handbook, firmware download, and source-document copies in sync with the root project when those contracts change.

The logical diagram does not provide electrical isolation. The handbook preserves the project’s research status and distinguishes legacy comparison results from live v2 use.

## Hosting

`.openai/hosting.json` identifies the private Sites deployment and its static `dist` output. Do not store credentials in this directory. The website is a separate static deployment; the desktop app is unchanged.
