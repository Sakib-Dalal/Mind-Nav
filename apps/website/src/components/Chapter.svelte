<script lang="ts">
  import {
    ArrowUpRight,
    Download,
    Info,
    TriangleAlert,
    ArrowUp,
  } from "@lucide/svelte";
  import { chapters } from "../lib/content";
  import CodeBlock from "./CodeBlock.svelte";
  import Platforms from "./Platforms.svelte";
  import Diagram from "./Diagram.svelte";
  let { id } = $props<{ id: string }>();
  let chapter = $derived(chapters[id]);
</script>

{#if chapter}
  <div class="chapter-layout">
    <article class="chapter-body">
      {#if chapter.lead}<p class="chapter-lead">
          {chapter.lead}
        </p>{/if}{#each chapter.sections as section}<section
          id={section.id}
          class="doc-section"
        >
          <h2>
            <a href={`#/${id}/${section.id}`}
              >{section.title}<span aria-hidden="true">#</span></a
            >
          </h2>
          {#each section.blocks as block}{#if block.type === "paragraph"}<p>
                {block.text}
              </p>{:else if block.type === "list"}{#if block.ordered}<ol
                  class="doc-steps"
                >
                  {#each block.items as item}<li>{item}</li>{/each}
                </ol>{:else}<ul class="doc-list">
                  {#each block.items as item}<li>{item}</li>{/each}
                </ul>{/if}{:else if block.type === "table"}<!-- Keyboard focus lets users scroll overflowing content. -->
              <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
              <div
                class="table-scroll"
                role="region"
                aria-label={`${section.title} table`}
                tabindex="0"
              >
                <table>
                  <thead
                    ><tr
                      >{#each block.headers as header}<th scope="col"
                          >{header}</th
                        >{/each}</tr
                    ></thead
                  ><tbody
                    >{#each block.rows as row}<tr
                        >{#each row as cell, i}{#if i === 0}<th scope="row"
                              >{cell}</th
                            >{:else}<td>{cell}</td>{/if}{/each}</tr
                      >{/each}</tbody
                  >
                </table>
              </div>{:else if block.type === "code"}<CodeBlock
                label={block.label}
                code={block.code}
              />{:else if block.type === "note"}<aside
                class="callout"
                class:warning={block.tone === "warning"}
              >
                {#if block.tone === "warning"}<TriangleAlert
                    size={20}
                  />{:else}<Info size={20} />{/if}
                <div>
                  <strong>{block.title}</strong>
                  <p>{block.text}</p>
                </div>
              </aside>{:else if block.type === "links"}<div
                class="resource-links"
              >
                {#each block.items as item}<a
                    href={item.href}
                    download={item.download ? "" : undefined}
                    target={item.href.startsWith("http") ||
                    (item.href.startsWith("/assets") && !item.download)
                      ? "_blank"
                      : undefined}
                    rel={item.href.startsWith("http")
                      ? "noreferrer"
                      : undefined}
                    >{#if item.download}<Download
                        size={15}
                      />{/if}{item.label}<ArrowUpRight size={14} /></a
                  >{/each}
              </div>{:else if block.type === "diagram"}<Diagram
                variant={block.variant}
              />{:else if block.type === "platforms"}<Platforms
              />{:else if block.type === "image"}<figure class="doc-figure">
                <a
                  href={block.src}
                  target="_blank"
                  rel="noreferrer"
                  aria-label="Open full-size electrode reference"
                  ><img
                    src={block.src}
                    alt={block.alt}
                    loading="lazy"
                    width="1920"
                    height="1080"
                  /></a
                >
                <figcaption>{block.caption}</figcaption>
              </figure>{/if}{/each}
        </section>{/each}
      <div class="chapter-source">
        <span>PROJECT REFERENCE</span>
        <p>{chapter.source}</p>
      </div>
    </article>
    <aside class="toc" aria-label="On this page">
      <div>ON THIS PAGE</div>
      <nav>
        {#each chapter.sections as section}<a href={`#/${id}/${section.id}`}
            >{section.title.replace(/^\d+ \/ /, "")}</a
          >{/each}
      </nav>
      <a class="back-top" href={`#/${id}`}><ArrowUp size={14} />Back to top</a>
      <div class="toc-note">
        <span class="small-dot"></span>Current desktop v0.2.0<br /><small
          >Acquisition protocol v2</small
        >
      </div>
    </aside>
  </div>
{/if}
