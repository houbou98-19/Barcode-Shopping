<script setup>
import { ref } from 'vue'
import { apiUrl, getSession } from './api'
import ProductsBrowser from './components/ProductsBrowser.vue'
import ProfileLogin from './components/ProfileLogin.vue'
import Scanner from './components/Scanner.vue'
import Settings from './components/Settings.vue'
import ShoppingList from './components/ShoppingList.vue'

const session = ref(getSession())

function handleLogin() {
  session.value = getSession()
}

function handleLoggedOut() {
  session.value = null
}

const view = ref('scan') // 'scan' | 'list' | 'products' | 'settings'

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
    const res = await fetch(apiUrl(`/api/products/barcode/${encodeURIComponent(barcode)}`))
    const products = await res.json()
    matches.value = products
    if (products.length === 0) {
      status.value = 'create'
    } else if (products.length === 1) {
      await addToList(products[0].id, products[0].name)
    } else {
      status.value = 'choose'
    }
  } catch {
    status.value = 'error'
    message.value = 'Could not reach the server'
  }
}

async function addToList(productId, productName) {
  status.value = 'loading'
  try {
    const res = await fetch(apiUrl('/api/list'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ product_id: productId }),
    })
    if (!res.ok) throw new Error()
    status.value = 'added'
    message.value = `${productName} was added to list`
  } catch {
    status.value = 'error'
    message.value = 'Could not add item to the list'
  }
}

async function createAndAdd() {
  if (!newName.value) return
  status.value = 'loading'
  try {
    const res = await fetch(apiUrl('/api/products'), {
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
    const name = newName.value
    newName.value = ''
    newCategory.value = ''
    await addToList(product.id, name)
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

function selectView(next) {
  view.value = next
  if (next === 'scan') scanAgain()
}
</script>

<template>
  <ProfileLogin v-if="!session" @login="handleLogin" />

  <div v-else class="app">
    <header class="app-header">
      <button class="title-btn" @click="view = 'products'">
        <svg class="logo" viewBox="0 0 24 24" aria-hidden="true">
          <rect x="1" y="2" width="2.5" height="20" fill="currentColor" />
          <rect x="5.5" y="2" width="1.2" height="20" fill="currentColor" />
          <rect x="8" y="2" width="3" height="20" fill="currentColor" />
          <rect x="12.5" y="2" width="1.2" height="20" fill="currentColor" />
          <rect x="15" y="2" width="2" height="20" fill="currentColor" />
          <rect x="18.5" y="2" width="1.2" height="20" fill="currentColor" />
          <rect x="21" y="2" width="2" height="20" fill="currentColor" />
        </svg>
        <h1>Barcode Shopping</h1>
      </button>
    </header>

    <main class="app-main">
      <section v-if="view === 'scan'" class="scan-view">
        <Scanner v-if="status === 'idle'" @scan="handleScan" />

        <p v-if="status === 'loading'" class="hint">Working...</p>

        <div v-if="status === 'choose'" class="card">
          <p>Multiple products found for barcode <code>{{ scannedBarcode }}</code>:</p>
          <ul class="choice-list">
            <li v-for="p in matches" :key="p.id">
              <button class="btn btn-secondary" @click="addToList(p.id, p.name)">
                {{ p.name }} <span class="muted">({{ p.category || 'no category' }})</span>
              </button>
            </li>
          </ul>
        </div>

        <div v-if="status === 'create'" class="card">
          <p>No product found for barcode <code>{{ scannedBarcode }}</code>. Add it:</p>
          <div class="form-row">
            <input v-model="newName" placeholder="Product name" />
            <input v-model="newCategory" placeholder="Category (optional)" />
          </div>
          <button class="btn btn-primary" @click="createAndAdd">Add &amp; add to list</button>
        </div>

        <template v-if="status === 'added'">
          <p class="hint success">{{ message }}</p>
          <button class="scan-again-panel" @click="scanAgain">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path
                fill="none"
                stroke="currentColor"
                stroke-width="1.6"
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M4 8V6a2 2 0 0 1 2-2h2M4 16v2a2 2 0 0 0 2 2h2M20 8V6a2 2 0 0 0-2-2h-2M20 16v2a2 2 0 0 1-2 2h-2M4 12h16"
              />
            </svg>
            Scan again
          </button>
        </template>

        <p v-if="status === 'error'" class="hint error">{{ message }}</p>

        <button
          v-if="status === 'choose' || status === 'create' || status === 'error'"
          class="btn btn-secondary"
          @click="scanAgain"
        >
          Scan again
        </button>
      </section>

      <section v-if="view === 'list'">
        <ShoppingList />
      </section>

      <section v-if="view === 'products'">
        <ProductsBrowser />
      </section>

      <section v-if="view === 'settings'">
        <Settings :session="session" @logged-out="handleLoggedOut" />
      </section>
    </main>

    <nav class="tab-bar">
      <button :class="{ active: view === 'scan' }" @click="selectView('scan')">
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path
            fill="none"
            stroke="currentColor"
            stroke-width="1.8"
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M4 8V6a2 2 0 0 1 2-2h2M4 16v2a2 2 0 0 0 2 2h2M20 8V6a2 2 0 0 0-2-2h-2M20 16v2a2 2 0 0 1-2 2h-2M4 12h16"
          />
        </svg>
        Scan
      </button>
      <button :class="{ active: view === 'list' }" @click="selectView('list')">
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path
            fill="none"
            stroke="currentColor"
            stroke-width="1.8"
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M9 6h11M9 12h11M9 18h11M4 6h.01M4 12h.01M4 18h.01"
          />
        </svg>
        List
      </button>
      <button :class="{ active: view === 'settings' }" @click="selectView('settings')">
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path
            fill="none"
            stroke="currentColor"
            stroke-width="1.8"
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z"
          />
          <path
            fill="none"
            stroke="currentColor"
            stroke-width="1.8"
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.6a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1Z"
          />
        </svg>
        Settings
      </button>
    </nav>
  </div>
</template>

<style scoped>
.app {
  display: flex;
  flex-direction: column;
  min-height: 100svh;
  max-width: 480px;
  margin: 0 auto;
}

.app-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px;
}

.title-btn {
  display: flex;
  align-items: center;
  gap: 10px;
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
  color: inherit;
  text-align: left;
}

.logo {
  width: 22px;
  height: 22px;
  color: var(--text);
  flex-shrink: 0;
}

.app-header h1 {
  font-size: 1.15rem;
  margin: 0;
}

.app-main {
  flex: 1;
  padding: 0 16px 16px;
}

.scan-view {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* While native scanning is active, let the scan view grow to fill the
   whole screen height so Scanner.vue's frame can center the target in
   the real camera viewport instead of a small boxed area. */
body.barcode-scanner-active .app-main {
  display: flex;
  flex-direction: column;
}

body.barcode-scanner-active .scan-view {
  flex: 1;
}

.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 16px;
  box-shadow: var(--shadow);
}

.card code {
  background: var(--bg);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.9em;
}

.form-row {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin: 12px 0;
}

.form-row input {
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--bg);
  color: var(--text);
}

.choice-list {
  list-style: none;
  padding: 0;
  margin: 12px 0 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.btn {
  border: none;
  border-radius: 999px;
  padding: 10px 18px;
  cursor: pointer;
  font-weight: 600;
}

.btn-primary {
  background: var(--accent);
  color: var(--accent-contrast);
}

.btn-secondary {
  background: var(--surface);
  border: 1px solid var(--border);
  color: var(--text);
  width: 100%;
  text-align: left;
}

.scan-again-panel {
  width: 100%;
  aspect-ratio: 4 / 3;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  background: var(--surface);
  border: 2px dashed var(--border);
  border-radius: 16px;
  color: var(--text);
  font-size: 1.2rem;
  font-weight: 600;
  cursor: pointer;
}

.scan-again-panel svg {
  width: 40px;
  height: 40px;
  color: var(--accent);
}

.muted {
  color: var(--text-muted);
  font-weight: 400;
}

.hint {
  text-align: center;
  color: var(--text-muted);
}

.hint.success {
  color: var(--accent);
}

.hint.error {
  color: var(--danger);
}

.tab-bar {
  display: flex;
  border-top: 1px solid var(--border);
  background: var(--surface);
}

/* Native barcode scanning hides the whole body so the camera preview
   (rendered behind the WebView) shows through - the tab bar must stay
   visible and tappable regardless, or there's no way out of the scanner. */
body.barcode-scanner-active .tab-bar {
  visibility: visible;
}

.tab-bar button {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 10px 0 max(10px, env(safe-area-inset-bottom));
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  font-size: 0.8rem;
}

.tab-bar button svg {
  width: 22px;
  height: 22px;
}

.tab-bar button.active {
  color: var(--accent);
}
</style>
