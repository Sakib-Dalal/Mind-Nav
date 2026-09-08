<script lang="ts">
  import { onMount, tick } from "svelte";
  import {
    ArrowUpRight,
    ArrowRight,
    ChevronRight,
    Menu,
    X,
    Code2,
    BookOpen,
  } from "@lucide/svelte";
  import { groups, pages, repository } from "./lib/navigation";
  import Overview from "./components/Overview.svelte";
  import Chapter from "./components/Chapter.svelte";
  let pageId = $state("overview");
  let menuOpen = $state(false);
  let sectionId = $state("");
  let page = $derived(pages.find((p) => p.id === pageId));
  let nextPage = $derived(
    page ? pages[pages.findIndex((p) => p.id === pageId) + 1] : undefined,
  );
  onMount(() => {
    async function readRoute() {
      const [id, section] = window.location.hash
        .replace(/^#\/?/, "")
        .split("/");
      const changed = pageId !== (id || "overview");
      pageId = id || "overview";
      sectionId = section || "";
      menuOpen = false;
      await tick();
      if (sectionId)
        document
          .getElementById(sectionId)
          ?.scrollIntoView({ behavior: "instant", block: "start" });
      else {
        window.scrollTo(0, 0);
        if (changed)
          document
            .getElementById("main-content")
            ?.focus({ preventScroll: true });
      }
    }
    readRoute();
    window.addEventListener("hashchange", readRoute);
    return () => window.removeEventListener("hashchange", readRoute);
  });
</script>

<svelte:head
  ><title>{page?.title ?? "Page not found"} · Mind-Nav Handbook</title
  ></svelte:head
>
<svelte:window
  onkeydown={(event) => {
    if (event.key === "Escape") menuOpen = false;
  }}
/>
<a
  href="#main-content"
  class="skip-link"
  onclick={(e) => {
    e.preventDefault();
    document.getElementById("main-content")?.focus();
  }}>Skip to content</a
>
<header class="topbar">
  <a class="brand" href="#/overview" aria-label="Mind-Nav home"
    ><img src="/assets/crown.svg" alt="" width="34" height="34" /><strong
      >Mind-Nav<span class="brand-period">.</span></strong
    ><span class="brand-divider"></span><span class="brand-docs">Handbook</span
    ></a
  >
  <nav aria-label="Top navigation">
    <a class="top-active" href="#/overview">Documentation</a><a
      href={repository}
      target="_blank"
      rel="noreferrer"
      ><Code2 size={16} /><span>View project</span><ArrowUpRight size={14} /></a
    ><span class="version">v0.2.0</span>
  </nav>
  <button
    class="menu-button"
    aria-label={menuOpen ? "Close navigation" : "Open navigation"}
    aria-expanded={menuOpen}
    aria-controls="side-navigation"
    onclick={() => (menuOpen = !menuOpen)}
    >{#if menuOpen}<X />{:else}<Menu />{/if}</button
  >
</header>
{#if menuOpen}<button
    class="nav-backdrop"
    aria-label="Close navigation"
    onclick={() => (menuOpen = false)}
  ></button>{/if}
<aside class:open={menuOpen} class="sidebar" id="side-navigation">
  <div class="sidebar-label">
    <BookOpen size={15} /><span>PROJECT DOCUMENTATION</span>
  </div>
  <nav aria-label="Documentation sections">
    {#each groups as group}<div class="nav-group">
        <div class="nav-group-title">{group.title}</div>
        {#each group.items as item}<a
            class:active={pageId === item.id}
            aria-current={pageId === item.id ? "page" : undefined}
            href={`#/${item.id}`}
            onclick={() => (menuOpen = false)}
            ><item.icon size={17} strokeWidth={1.7} /><span>{item.title}</span
            >{#if item.id === "hardware"}<span class="nav-new">v2</span>{/if}</a
          >{/each}
      </div>{/each}
  </nav>
  <div class="sidebar-bottom">
    <span class="small-dot"></span>
    <div>
      <strong>Built on possibility.</strong><span
        >Rust + Tauri 2 + Svelte 5</span
      >
    </div>
  </div>
</aside>
<main id="main-content" tabindex="-1">
  <div class="content-wrap">
    <div class="breadcrumb">
      <span>Documentation</span><ChevronRight size={13} /><span
        >{page?.title ?? "Page not found"}</span
      ><span class="breadcrumb-right">THE COMPLETE PROJECT GUIDE</span>
    </div>
    {#if pageId === "overview"}<Overview />{:else if page}<div
        class="doc-heading"
      >
        <div class="eyebrow">{page.group}</div>
        <h1>{page.title}</h1>
        <p>{page.description}</p>
      </div>
      <Chapter id={pageId} />{:else}<div class="doc-heading">
        <h1>That page isn’t here.</h1>
        <p>Find your next step in the handbook.</p>
        <a href="#/overview" class="button primary"
          >Back to introduction <ArrowRight size={16} /></a
        >
      </div>{/if}
    {#if nextPage}<a class="next-page" href={`#/${nextPage.id}`}
        ><span><small>UP NEXT</small><strong>{nextPage.title}</strong></span
        ><ArrowRight size={22} /></a
      >{/if}
    <footer>
      <span
        >Mind-Nav <span class="footer-dot">·</span> A little thought. A world of possibility.</span
      ><a href={repository} target="_blank" rel="noreferrer"
        >Explore the source <ArrowUpRight size={14} /></a
      >
    </footer>
  </div>
</main>
