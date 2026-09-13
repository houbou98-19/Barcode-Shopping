<script setup>
import { computed, ref, watch } from 'vue'
import { apiFetch, apiUrl } from '../api'
import { activeListId } from '../listStore'

const props = defineProps({
  product: { type: Object, required: true },
  showAddButton: { type: Boolean, default: true },
})
const emit = defineEmits(['close', 'added'])

const status = ref('idle') // idle | adding | added | error
const imageFailed = ref(false)
const imageExpanded = ref(false)
const imageUrl = computed(() => apiUrl(`/api/products/${props.product.id}/image`))

// This component instance is reused across products (a single v-if, not a
// v-for), so a failed load for one product must not hide a real image for
// the next one shown.
watch(
  () => props.product.id,
  () => {
    imageFailed.value = false
    imageExpanded.value = false
  }
)

// added_at is stored as a UTC "YYYY-MM-DD HH:MM:SS" string (SQLite
// datetime('now'), no timezone suffix) - Date would otherwise parse it
// as local time, which is wrong.
const addedAtDisplay = computed(() => {
  if (!props.product.addedAt) return ''
  const date = new Date(props.product.addedAt.replace(' ', 'T') + 'Z')
  return date.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
})

async function addToList() {
  status.value = 'adding'
  try {
    const res = await apiFetch(`/api/lists/${activeListId.value}/items`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ product_id: props.product.id }),
    })
    if (!res.ok) throw new Error()
    status.value = 'added'
    emit('added')
    setTimeout(() => emit('close'), 700)
  } catch {
    status.value = 'error'
  }
}
</script>

<template>
  <div class="overlay" @click.self="emit('close')">
    <div class="detail-card">
      <button class="close-btn" aria-label="Close" @click="emit('close')">
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path
            fill="none"
            stroke="currentColor"
            stroke-width="1.8"
            stroke-linecap="round"
            d="m6 6 12 12M18 6 6 18"
          />
        </svg>
      </button>

      <img
        v-if="!imageFailed"
        :src="imageUrl"
        alt=""
        class="product-image"
        @error="imageFailed = true"
        @click="imageExpanded = true"
      />
      <div v-else class="image-placeholder"></div>

      <h2>{{ product.name }}</h2>
      <p v-if="product.category" class="chip">{{ product.category }}</p>
      <p class="barcode">{{ product.barcode }}</p>
      <p v-if="product.addedByName" class="added-by">
        Added by {{ product.addedByName }} · {{ addedAtDisplay }}
      </p>

      <button
        v-if="showAddButton"
        class="add-btn"
        :class="{ added: status === 'added' }"
        :disabled="status === 'adding' || status === 'added'"
        @click="addToList"
      >
        <template v-if="status === 'added'">Added ✓</template>
        <template v-else-if="status === 'error'">Could not add - try again</template>
        <template v-else>
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              d="M12 5v14M5 12h14"
            />
          </svg>
          Add to list
        </template>
      </button>
    </div>

    <div v-if="imageExpanded" class="lightbox" @click="imageExpanded = false">
      <img :src="imageUrl" alt="" class="lightbox-image" />
    </div>
  </div>
</template>

<style scoped>
.overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  z-index: 100;
}

.detail-card {
  position: relative;
  width: 100%;
  max-width: 320px;
  background: var(--surface);
  border-radius: 16px;
  padding: 24px;
  box-shadow: var(--shadow);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  text-align: center;
}

.close-btn {
  position: absolute;
  top: 10px;
  right: 10px;
  width: 30px;
  height: 30px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: none;
  color: var(--text-muted);
  cursor: pointer;
  border-radius: 8px;
}

.close-btn svg {
  width: 18px;
  height: 18px;
}

.image-placeholder,
.product-image {
  width: 96px;
  height: 96px;
  border-radius: 12px;
}

.image-placeholder {
  background: var(--bg);
  border: 1px dashed var(--border);
}

.product-image {
  object-fit: cover;
  border: 1px solid var(--border);
  cursor: zoom-in;
}

.lightbox {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.75);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  z-index: 200;
  cursor: zoom-out;
}

.lightbox-image {
  max-width: min(80vw, 400px);
  max-height: 80vh;
  border-radius: 12px;
}

.detail-card h2 {
  margin: 4px 0 0;
  font-size: 1.1rem;
}

.chip {
  font-size: 0.8rem;
  color: var(--text-muted);
  background: var(--bg);
  border-radius: 999px;
  padding: 3px 10px;
  margin: 0;
}

.barcode {
  font-family: ui-monospace, Consolas, monospace;
  font-size: 0.85rem;
  color: var(--text-muted);
  margin: 0;
}

.added-by {
  font-size: 0.78rem;
  color: var(--text-muted);
  margin: 0;
}

.add-btn {
  margin-top: 10px;
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border: none;
  border-radius: 999px;
  padding: 12px 18px;
  background: var(--accent);
  color: var(--accent-contrast);
  font-weight: 600;
  cursor: pointer;
}

.add-btn:disabled {
  cursor: default;
  opacity: 0.85;
}

.add-btn svg {
  width: 18px;
  height: 18px;
}
</style>
