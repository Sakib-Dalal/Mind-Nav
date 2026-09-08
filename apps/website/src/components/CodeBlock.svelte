<script lang="ts">
  import { Copy, Check } from "@lucide/svelte";
  import { onDestroy } from "svelte";
  let { label, code } = $props<{ label: string; code: string }>();
  let status = $state<"idle" | "copied" | "failed">("idle");
  let timer: ReturnType<typeof setTimeout>;
  async function copy() {
    clearTimeout(timer);
    try {
      await navigator.clipboard.writeText(code);
      status = "copied";
    } catch {
      status = "failed";
    }
    timer = setTimeout(() => (status = "idle"), 3000);
  }
  onDestroy(() => clearTimeout(timer));
</script>

<div class="code-block">
  <div class="code-label">
    <span>{label}</span><button onclick={copy} aria-label={`Copy ${label} code`}
      >{#if status === "copied"}<Check size={15} />{:else}<Copy
          size={15}
        />{/if}<span aria-live="polite"
        >{status === "copied"
          ? "Copied"
          : status === "failed"
            ? "Select text to copy"
            : "Copy"}</span
      ></button
    >
  </div>
  <!-- Keyboard focus lets users scroll overflowing content. -->
  <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
  <pre tabindex="0" aria-label={label}><code>{code}</code></pre>
</div>
