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
    <video ref="videoRef" playsinline muted></video>
    <p v-if="error" class="error">{{ error }}</p>
  </div>
</template>

<style scoped>
.scanner video {
  width: 100%;
  max-width: 480px;
  background: #000;
}

.error {
  color: #b00020;
}
</style>
