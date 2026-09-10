<script setup>
import { computed, onMounted, ref } from 'vue'
import ProductCard from './ProductCard.vue'

const products = ref([])
const loading = ref(false)
const error = ref('')
const search = ref('')
const selectedProduct = ref(null)

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await fetch('/api/products')
    if (!res.ok) throw new Error()
    products.value = await res.json()
  } catch {
    error.value = 'Could not load products'
  } finally {
    loading.value = false
  }
}

const filteredProducts = computed(() => {
  const q = search.value.trim().toLowerCase()
  if (!q) return products.value
  return products.value.filter(
    (p) => p.name.toLowerCase().includes(q) || (p.category || '').toLowerCase().includes(q)
  )
})

onMounted(load)
</script>

<template>
  <div class="products-browser">
    <div class="search-box">
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path
          fill="none"
          stroke="currentColor"
          stroke-width="1.6"
          stroke-linecap="round"
          stroke-linejoin="round"
          d="m21 21-4.35-4.35M19 11a8 8 0 1 1-16 0 8 8 0 0 1 16 0"
        />
      </svg>
      <input v-model="search" type="text" placeholder="Search products or groups" />
    </div>

    <p v-if="loading" class="hint">Loading...</p>
    <p v-if="error" class="hint error">{{ error }}</p>

    <p v-if="!loading && products.length === 0" class="hint">No products yet</p>
    <p v-if="!loading && products.length > 0 && filteredProducts.length === 0" class="hint">
      No products match "{{ search }}"
    </p>

    <ul>
      <li
        v-for="p in filteredProducts"
        :key="p.id"
        class="card"
        tabindex="0"
        @click="selectedProduct = p"
        @keydown.enter="selectedProduct = p"
        @keydown.space.prevent="selectedProduct = p"
      >
        <div class="info">
          <span class="name">{{ p.name }}</span>
          <span v-if="p.category" class="chip">{{ p.category }}</span>
        </div>
        <span class="barcode">{{ p.barcode }}</span>
      </li>
    </ul>

    <ProductCard v-if="selectedProduct" :product="selectedProduct" @close="selectedProduct = null" />
  </div>
</template>

<style scoped>
.search-box {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 8px 14px;
  margin-bottom: 14px;
}

.search-box svg {
  width: 18px;
  height: 18px;
  color: var(--text-muted);
  flex-shrink: 0;
}

.search-box input {
  flex: 1;
  border: none;
  background: none;
  color: var(--text);
  outline: none;
  min-width: 0;
}

ul {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.card {
  display: flex;
  align-items: center;
  gap: 12px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 12px;
  box-shadow: var(--shadow);
  cursor: pointer;
}

.card:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}

.info {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.name {
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chip {
  font-size: 0.75rem;
  color: var(--text-muted);
  background: var(--bg);
  border-radius: 999px;
  padding: 2px 8px;
}

.barcode {
  flex-shrink: 0;
  font-family: ui-monospace, Consolas, monospace;
  font-size: 0.8rem;
  color: var(--text-muted);
}

.hint {
  text-align: center;
  color: var(--text-muted);
}

.hint.error {
  color: var(--danger);
}
</style>
