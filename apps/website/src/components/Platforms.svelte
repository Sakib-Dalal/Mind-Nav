<script lang="ts">
  import { Monitor, Apple, Terminal } from "@lucide/svelte";
  import CodeBlock from "./CodeBlock.svelte";
  let platform = $state("macos");
  const platforms = [
    {
      id: "macos",
      name: "macOS",
      icon: Apple,
      text: "Install Xcode Command Line Tools, stable Rust, and Node.js. The project has produced a macOS application bundle; native device and speech flows still need validation.",
      code: "xcode-select --install",
      note: "The native speech implementation uses macOS speech. App distribution still requires signing and notarization configuration.",
    },
    {
      id: "windows",
      name: "Windows",
      icon: Monitor,
      text: "Install Microsoft C++ Build Tools with the Desktop development with C++ workload, the Windows SDK, and WebView2. Use the stable MSVC Rust toolchain and Node.js.",
      code: "rustup default stable-msvc",
      note: "The project uses Windows speech integration. Windows installer packaging and hardware behavior have not been validated in the current project record.",
    },
    {
      id: "linux",
      name: "Linux",
      icon: Terminal,
      text: "Install your distribution’s Tauri dependencies, including WebKitGTK 4.1, plus libudev development packages for serial access and spd-say for speech. The command below is for Debian/Ubuntu.",
      code: "sudo apt update\nsudo apt install libwebkit2gtk-4.1-dev build-essential curl wget file \\\n  libxdo-dev libssl-dev libayatana-appindicator3-dev librsvg2-dev \\\n  libudev-dev speech-dispatcher",
      note: "For other distributions, use the matching packages in the official Tauri guide. Linux installer packaging and native hardware behavior still need validation.",
    },
  ];
  const selected = $derived(platforms.find((p) => p.id === platform)!);
</script>

<div class="platforms">
  <div class="platform-tabs" role="group" aria-label="Choose operating system">
    {#each platforms as item}<button
        aria-pressed={platform === item.id}
        class:selected={platform === item.id}
        onclick={() => (platform = item.id)}
        ><item.icon size={17} />{item.name}</button
      >{/each}
  </div>
  <div class="platform-content">
    <h3>{selected.name} setup</h3>
    <p>{selected.text}</p>
    <CodeBlock
      label={`${selected.name} · setup command`}
      code={selected.code}
    />
    <p class="platform-note">{selected.note}</p>
  </div>
</div>
