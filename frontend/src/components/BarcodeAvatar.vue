<script setup>
import { computed } from 'vue'
import { barcodeBarsForName } from '../barcodeAvatar'

const props = defineProps({
  name: { type: String, required: true },
})

const PADDING = 2
const BAR_HEIGHT = 60

const barcode = computed(() => barcodeBarsForName(props.name))
const viewWidth = computed(() => barcode.value.totalModules + PADDING * 2)
const viewHeight = BAR_HEIGHT + PADDING * 2
</script>

<template>
  <svg
    class="barcode-avatar"
    :viewBox="`0 0 ${viewWidth} ${viewHeight}`"
    preserveAspectRatio="none"
    role="img"
    :aria-label="`${name}'s avatar`"
  >
    <rect width="100%" height="100%" fill="#ffffff" />
    <g fill="#111111">
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
.barcode-avatar {
  display: block;
  width: 100%;
  height: 100%;
  border-radius: 8px;
}
</style>
