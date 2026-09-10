<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { BarcodeDetector } from 'barcode-detector/pure'

const emit = defineEmits(['scan'])

const videoRef = ref(null)
const error = ref(null)

let stream = null
let detector = null
let intervalId = null

async function start() {
  error.value = null
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: 'environment' },
    })
    videoRef.value.srcObject = stream
    await videoRef.value.play()

    detector = new BarcodeDetector({
      formats: ['ean_13', 'ean_8', 'upc_a', 'upc_e', 'code_128'],
    })

    intervalId = setInterval(scanFrame, 400)
  } catch (e) {
    error.value = e.message || 'Could not access the camera'
  }
}

async function scanFrame() {
  if (!videoRef.value || videoRef.value.readyState < 2) return
  try {
    const barcodes = await detector.detect(videoRef.value)
    if (barcodes.length > 0) {
      stop()
      emit('scan', barcodes[0].rawValue)
    }
  } catch {
    // transient decode error on this frame - keep scanning
  }
}

function stop() {
  if (intervalId) {
    clearInterval(intervalId)
    intervalId = null
  }
  if (stream) {
    stream.getTracks().forEach((track) => track.stop())
    stream = null
  }
}

onMounted(start)
onBeforeUnmount(stop)
</script>

<template>
  <div class="scanner">
    <div class="frame">
      <video ref="videoRef" playsinline muted></video>
      <div v-if="!error" class="target">
        <span class="corner tl"></span>
        <span class="corner tr"></span>
        <span class="corner bl"></span>
        <span class="corner br"></span>
      </div>
    </div>
    <p v-if="!error" class="instructions">Point the camera at a barcode</p>
    <p v-if="error" class="error">{{ error }}</p>
  </div>
</template>

<style scoped>
.scanner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.frame {
  position: relative;
  width: 100%;
  aspect-ratio: 4 / 3;
  background: #000;
  border-radius: 16px;
  overflow: hidden;
}

.frame video {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.target {
  position: absolute;
  inset: 22% 10%;
  pointer-events: none;
}

.corner {
  position: absolute;
  width: 24px;
  height: 24px;
  border: 3px solid #fff;
  opacity: 0.85;
}

.corner.tl {
  top: 0;
  left: 0;
  border-right: none;
  border-bottom: none;
  border-radius: 6px 0 0 0;
}

.corner.tr {
  top: 0;
  right: 0;
  border-left: none;
  border-bottom: none;
  border-radius: 0 6px 0 0;
}

.corner.bl {
  bottom: 0;
  left: 0;
  border-right: none;
  border-top: none;
  border-radius: 0 0 0 6px;
}

.corner.br {
  bottom: 0;
  right: 0;
  border-left: none;
  border-top: none;
  border-radius: 0 0 6px 0;
}

.instructions {
  color: var(--text-muted);
  font-size: 0.9rem;
  margin: 0;
}

.error {
  color: var(--danger);
  text-align: center;
}
</style>
