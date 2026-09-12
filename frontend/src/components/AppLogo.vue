<script setup>
import { computed } from 'vue'
import { barcodeBarsForName } from '../barcodeAvatar'

defineProps({
  width: { type: Number, default: 22 },
  height: { type: Number, default: 22 },
})

const PADDING = 2
const BAR_HEIGHT = 60

const barcode = computed(() => barcodeBarsForName('HBCS'))
const viewWidth = computed(() => barcode.value.totalModules + PADDING * 2)
const viewHeight = BAR_HEIGHT + PADDING * 2
</script>

<template>
  <svg
    class="app-logo"
    :viewBox="`0 0 ${viewWidth} ${viewHeight}`"
    preserveAspectRatio="none"
    aria-hidden="true"
    :style="{ width: `${width}px`, height: `${height}px` }"
  >
    <g fill="currentColor">
      <rect
        v-for="(bar, i) in barcode.bars"
        :key="i"
        :x="bar.x + PADDING"
        :y="PADDING"
        :width="bar.width"
        :height="BAR_HEIGHT"
      />
    </g>
  </svg>
</template>

<style scoped>
.app-logo {
  flex-shrink: 0;
}
</style>
