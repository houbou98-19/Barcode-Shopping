<script setup>
import { ref } from 'vue'
import Scanner from './components/Scanner.vue'
import ShoppingList from './components/ShoppingList.vue'

const view = ref('scan') // 'scan' | 'list'

const status = ref('idle') // idle | loading | choose | create | added | error
const scannedBarcode = ref(null)
const matches = ref([])
const message = ref('')
const newName = ref('')
const newCategory = ref('')

async function handleScan(barcode) {
  scannedBarcode.value = barcode
  status.value = 'loading'
  message.value = ''
  try {
    const res = await fetch(`/api/products/barcode/${encodeURIComponent(barcode)}`)
    const products = await res.json()
    matches.value = products
    if (products.length === 0) {
      status.value = 'create'
    } else if (products.length === 1) {
      await addToList(products[0].id)
    } else {
      status.value = 'choose'
    }
  } catch {
    status.value = 'error'
    message.value = 'Could not reach the server'
  }
}

async function addToList(productId) {
  status.value = 'loading'
  try {
    const res = await fetch('/api/list', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ product_id: productId }),
    })
    if (!res.ok) throw new Error()
    status.value = 'added'
    message.value = 'Added to list!'
  } catch {
    status.value = 'error'
    message.value = 'Could not add item to the list'
  }
}

async function createAndAdd() {
  if (!newName.value) return
  status.value = 'loading'
  try {
    const res = await fetch('/api/products', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        barcode: scannedBarcode.value,
        name: newName.value,
        category: newCategory.value || null,
      }),
    })
    if (!res.ok) throw new Error()
    const product = await res.json()
    newName.value = ''
    newCategory.value = ''
    await addToList(product.id)
  } catch {
    status.value = 'error'
    message.value = 'Could not create product'
  }
}

function scanAgain() {
  status.value = 'idle'
  scannedBarcode.value = null
  matches.value = []
  message.value = ''
}
</script>

<template>
  <div id="app">
    <h1>Barcode Shopping</h1>

    <nav class="tabs">
      <button :class="{ active: view === 'scan' }" @click="view = 'scan'">Scan</button>
      <button :class="{ active: view === 'list' }" @click="view = 'list'">List</button>
    </nav>

    <section v-if="view === 'scan'">
      <Scanner v-if="status === 'idle'" @scan="handleScan" />

      <p v-if="status === 'loading'">Working...</p>

      <div v-if="status === 'choose'">
        <p>Multiple products found for barcode {{ scannedBarcode }}:</p>
        <ul>
          <li v-for="p in matches" :key="p.id">
            <button @click="addToList(p.id)">
              {{ p.name }} ({{ p.category || 'no category' }})
            </button>
          </li>
        </ul>
      </div>

      <div v-if="status === 'create'">
        <p>No product found for barcode {{ scannedBarcode }}. Add it:</p>
        <input v-model="newName" placeholder="Product name" />
        <input v-model="newCategory" placeholder="Category (optional)" />
        <button @click="createAndAdd">Add product &amp; add to list</button>
      </div>

      <p v-if="status === 'added'">{{ message }}</p>
      <p v-if="status === 'error'" class="error">{{ message }}</p>

      <button v-if="status !== 'idle' && status !== 'loading'" @click="scanAgain">
        Scan again
      </button>
    </section>

    <section v-if="view === 'list'">
      <ShoppingList />
    </section>
  </div>
</template>

<style scoped>
.tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.tabs button.active {
  font-weight: bold;
  text-decoration: underline;
}

.error {
  color: #b00020;
}
</style>
