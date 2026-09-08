<script lang="ts">
  let { size = 36, decorative = true } = $props<{ size?: number; decorative?: boolean }>();
</script>

<svg
  width={size}
  height={size}
  viewBox="0 0 64 64"
  fill="none"
  aria-hidden={decorative}
  role={decorative ? undefined : 'img'}
  aria-label={decorative ? undefined : 'Mind-Nav crown'}
>
  <path
    d="M10 21C6 8 19 6 23 16L32 30L41 16C45 6 58 8 54 21"
    stroke="currentColor"
    stroke-width="4.5"
    stroke-linecap="round"
  />
  <path d="M12 27L18 45C27 49 37 49 46 45L52 27L41 35L32 23L23 35L12 27Z" fill="currentColor" />
  <path
    d="M20 53C28 56 36 56 44 53"
    stroke="currentColor"
    stroke-width="4.5"
    stroke-linecap="round"
  />
  <path d="M32 35L35 39L32 43L29 39L32 35Z" fill="var(--crown-cutout, #233D4D)" />
</svg>
