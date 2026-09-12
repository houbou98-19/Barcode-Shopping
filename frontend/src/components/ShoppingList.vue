<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { apiFetch, apiUrl } from '../api'
import ProductCard from './ProductCard.vue'

const items = ref([])
const loading = ref(false)
const error = ref('')
const search = ref('')
const selectedProduct = ref(null)
const sortKey = ref('added') // 'added' | 'category' | 'name'
const sortDir = ref(1) // 1 = ascending, -1 = descending

function setSort(key) {
  if (sortKey.value === key) {
    sortDir.value *= -1
  } else {
    sortKey.value = key
    sortDir.value = 1
  }
}

const filteredItems = computed(() => {
  const q = search.value.trim().toLowerCase()
  if (!q) return items.value
  return items.value.filter(
    (item) =>
      item.name.toLowerCase().includes(q) || (item.category || '').toLowerCase().includes(q)
  )
})

const sortedItems = computed(() => {
  const list = [...filteredItems.value]
  const dir = sortDir.value
  list.sort((a, b) => {
    let cmp
    if (sortKey.value === 'added') {
      cmp = a.added_at < b.added_at ? -1 : a.added_at > b.added_at ? 1 : 0
    } else if (sortKey.value === 'category') {
      cmp = (a.category || '').toLowerCase().localeCompare((b.category || '').toLowerCase())
    } else {
      cmp = a.name.toLowerCase().localeCompare(b.name.toLowerCase())
    }
    return cmp * dir
  })
  return list
})

async function load({ silent = false } = {}) {
  if (!silent) loading.value = true
  error.value = ''
  try {
    const res = await apiFetch('/api/list')
    if (!res.ok) throw new Error()
    items.value = await res.json()
  } catch {
    error.value = 'Could not load the shopping list'
  } finally {
    if (!silent) loading.value = false
  }
}

async function toggleChecked(item) {
  const checked = item.checked ? 0 : 1
  const previous = item.checked
  item.checked = checked
  try {
    const res = await apiFetch(`/api/list/${item.id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ checked: !!checked }),
    })
    if (!res.ok) throw new Error()
  } catch {
    item.checked = previous
    error.value = 'Could not update item'
  }
}

async function changeQuantity(item, delta) {
  const newQuantity = item.quantity + delta
  if (newQuantity < 1) return
  const previous = item.quantity
  item.quantity = newQuantity
  try {
    const res = await apiFetch(`/api/list/${item.id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ quantity: newQuantity }),
    })
    if (!res.ok) throw new Error()
  } catch {
    item.quantity = previous
    error.value = 'Could not update quantity'
  }
}

async function removeItem(item) {
  try {
    const res = await apiFetch(`/api/list/${item.id}`, { method: 'DELETE' })
    if (!res.ok) throw new Error()
    items.value = items.value.filter((i) => i.id !== item.id)
  } catch {
    error.value = 'Could not remove item'
  }
}

function openDetail(item) {
  selectedProduct.value = {
    id: item.product_id,
    name: item.name,
    category: item.category,
    barcode: item.barcode,
  }
}

let eventSource = null

function connectLiveUpdates() {
  eventSource = new EventSource(apiUrl('/api/events'))
  eventSource.onmessage = () => load({ silent: true })
}

onMounted(() => {
  load()
  connectLiveUpdates()
})

onUnmounted(() => {
  eventSource?.close()
})
</script>

<template>
  <div class="shopping-list">
    <div v-if="!loading && items.length > 0" class="toolbar">
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
        <input v-model="search" type="text" placeholder="Search items or groups" />
      </div>

      <div class="sort-row">
        <button
          class="sort-chip"
          :class="{ active: sortKey === 'added' }"
          @click="setSort('added')"
        >
          Time added
          <span v-if="sortKey === 'added'" class="arrow">{{ sortDir === 1 ? '↑' : '↓' }}</span>
        </button>
        <button
          class="sort-chip"
          :class="{ active: sortKey === 'category' }"
          @click="setSort('category')"
        >
          Group name
          <span v-if="sortKey === 'category'" class="arrow">{{ sortDir === 1 ? '↑' : '↓' }}</span>
        </button>
        <button
          class="sort-chip"
          :class="{ active: sortKey === 'name' }"
          @click="setSort('name')"
        >
          Item name
          <span v-if="sortKey === 'name'" class="arrow">{{ sortDir === 1 ? '↑' : '↓' }}</span>
        </button>
      </div>
    </div>

    <p v-if="loading" class="hint">Loading...</p>
    <p v-if="error" class="hint error">{{ error }}</p>

    <div v-if="!loading && items.length === 0" class="empty">
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path
          fill="none"
          stroke="currentColor"
          stroke-width="1.5"
          stroke-linecap="round"
          stroke-linejoin="round"
          d="M6 6h15l-1.5 9h-12L6 3H3M9 20a1 1 0 1 0 0-2 1 1 0 0 0 0 2M18 20a1 1 0 1 0 0-2 1 1 0 0 0 0 2"
        />
      </svg>
      <p>Your shopping list is empty</p>
    </div>

    <p v-if="!loading && items.length > 0 && sortedItems.length === 0" class="hint">
      No items match "{{ search }}"
    </p>

    <ul>
      <li
        v-for="item in sortedItems"
        :key="item.id"
        class="card"
        :class="{ checked: item.checked }"
        tabindex="0"
        @click="openDetail(item)"
        @keydown.enter="openDetail(item)"
        @keydown.space.prevent="openDetail(item)"
      >
        <span
          class="checkmark"
          role="checkbox"
          :aria-checked="!!item.checked"
          tabindex="0"
          @click.stop="toggleChecked(item)"
          @keydown.enter.stop="toggleChecked(item)"
          @keydown.space.stop.prevent="toggleChecked(item)"
        ></span>

        <div class="info">
          <span class="name">{{ item.name }}</span>
          <span v-if="item.category" class="chip">{{ item.category }}</span>
        </div>

        <div class="stepper" @click.stop>
          <button :disabled="item.quantity <= 1" @click="changeQuantity(item, -1)">-</button>
          <span>{{ item.quantity }}</span>
          <button @click="changeQuantity(item, 1)">+</button>
        </div>

        <button class="icon-btn" aria-label="Remove item" @click.stop="removeItem(item)">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path
              fill="none"
              stroke="currentColor"
              stroke-width="1.6"
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M4 7h16M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2m2 0-.8 12.2a1 1 0 0 1-1 .8H8.8a1 1 0 0 1-1-.8L7 7"
            />
          </svg>
        </button>
      </li>
    </ul>

    <ProductCard
      v-if="selectedProduct"
      :product="selectedProduct"
      :show-add-button="false"
      @close="selectedProduct = null"
    />
  </div>
</template>

<style scoped>
.toolbar {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 14px;
}

.search-box {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 8px 14px;
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

.sort-row {
  display: flex;
  gap: 8px;
  overflow-x: auto;
}

.sort-chip {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 4px;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text-muted);
  border-radius: 999px;
  padding: 6px 12px;
  font-size: 0.85rem;
  cursor: pointer;
}

.sort-chip.active {
  color: var(--accent-contrast);
  background: var(--accent);
  border-color: var(--accent);
}

.arrow {
  font-weight: bold;
}

.shopping-list ul {
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
  user-select: none;
}

.card:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}

.checkmark {
  width: 22px;
  height: 22px;
  flex-shrink: 0;
  border: 2px solid var(--border);
  border-radius: 6px;
  display: inline-block;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
}

.checkmark:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}

.card.checked .checkmark {
  background: var(--accent);
  border-color: var(--accent);
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

.checked .name {
  text-decoration: line-through;
  color: var(--text-muted);
}

.chip {
  font-size: 0.75rem;
  color: var(--text-muted);
  background: var(--bg);
  border-radius: 999px;
  padding: 2px 8px;
}

.stepper {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.stepper button {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  border: 1px solid var(--border);
  background: var(--bg);
  color: var(--text);
  cursor: pointer;
  line-height: 1;
}

.stepper button:disabled {
  opacity: 0.4;
  cursor: default;
}

.stepper span {
  min-width: 1.2em;
  text-align: center;
}

.icon-btn {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: none;
  color: var(--text-muted);
  cursor: pointer;
  border-radius: 8px;
}

.icon-btn:hover {
  color: var(--danger);
  background: var(--danger-bg);
}

.icon-btn svg {
  width: 18px;
  height: 18px;
}

.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  color: var(--text-muted);
  padding: 48px 0;
}

.empty svg {
  width: 40px;
  height: 40px;
}

.hint {
  text-align: center;
  color: var(--text-muted);
}

.hint.error {
  color: var(--danger);
}
</style>
