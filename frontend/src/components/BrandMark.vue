<template>
  <div class="brand-mark" aria-hidden="true"><span /><span /><span /></div>
</template>

<style scoped>
.brand-mark { display: grid; grid-template-columns: repeat(3, 5px); align-items: end; gap: 3px; width: 28px; height: 28px; padding: 5px; border-radius: 8px; background: var(--ink-900); }
.brand-mark span { display: block; border-radius: 1px; background: var(--teal-400); }
.brand-mark span:nth-child(1) { height: 8px; }
.brand-mark span:nth-child(2) { height: 17px; }
.brand-mark span:nth-child(3) { height: 12px; }
</style>
