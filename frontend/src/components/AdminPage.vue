<script setup>
import { ref } from 'vue'
import { apiUrl } from '../api'
import AppLogo from './AppLogo.vue'

// Kept in memory only (not localStorage) - re-entering the password on
// every page load is an acceptable cost for not leaving an admin secret
// sitting in persistent browser storage.
const password = ref('')
const authed = ref(false)
const authError = ref('')
const busy = ref(false)

const profiles = ref([])
const products = ref([])

function adminFetch(path, options = {}) {
  return fetch(apiUrl(path), {
    ...options,
    headers: { ...options.headers, 'X-Admin-Password': password.value },
  })
}

async function loadAll() {
  const [profilesRes, productsRes] = await Promise.all([
    adminFetch('/api/admin/profiles'),
    adminFetch('/api/admin/products'),
  ])
  profiles.value = await profilesRes.json()
  products.value = await productsRes.json()
}

async function login() {
  busy.value = true
  authError.value = ''
  try {
    const res = await adminFetch('/api/admin/profiles')
    if (res.status === 401) {
      authError.value = 'Incorrect password'
      return
    }
    if (res.status === 404) {
      authError.value = 'Admin access is not configured on this server'
      return
    }
    if (!res.ok) {
      authError.value = 'Could not reach server'
      return
    }
    await loadAll()
    authed.value = true
  } catch {
    authError.value = 'Could not reach server'
  } finally {
    busy.value = false
  }
}

async function resetPin(profile) {
  const pin = window.prompt(`New 4-digit PIN for ${profile.name}:`)
  if (pin === null) return
  if (!/^\d{4}$/.test(pin)) {
    window.alert('PIN must be exactly 4 digits')
    return
  }
  const res = await adminFetch(`/api/admin/profiles/${profile.id}/reset-pin`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ pin }),
  })
  if (res.ok) await loadAll()
  else window.alert('Could not reset PIN')
}

async function clearLockout(profile) {
  const res = await adminFetch(`/api/admin/profiles/${profile.id}/clear-lockout`, {
    method: 'POST',
  })
  if (res.ok) await loadAll()
  else window.alert('Could not clear lockout')
}

async function deleteProfile(profile) {
  if (!window.confirm(`Delete profile "${profile.name}"? This also deletes their shopping list. This cannot be undone.`)) return
  const res = await adminFetch(`/api/admin/profiles/${profile.id}`, { method: 'DELETE' })
  if (res.ok) await loadAll()
  else window.alert('Could not delete profile')
}

async function editProduct(product) {
  const name = window.prompt('Product name:', product.name)
  if (name === null) return
  const category = window.prompt('Category (blank for none):', product.category || '')
  if (category === null) return
  const res = await adminFetch(`/api/admin/products/${product.id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, category }),
  })
  if (res.ok) await loadAll()
  else window.alert('Could not update product')
}

async function deleteProduct(product) {
  if (!window.confirm(`Delete product "${product.name}"? This removes it from everyone's list. This cannot be undone.`)) return
  const res = await adminFetch(`/api/admin/products/${product.id}`, { method: 'DELETE' })
  if (res.ok) await loadAll()
  else window.alert('Could not delete product')
}
</script>

<template>
  <div class="admin-page">
    <div class="admin-header">
      <AppLogo :width="28" :height="28" />
      <h1>Admin</h1>
    </div>

    <div v-if="!authed" class="card login-card">
      <label class="field">
        <span class="label">Admin password</span>
        <input v-model="password" type="password" @keyup.enter="login" />
      </label>
      <p v-if="authError" class="hint error">{{ authError }}</p>
      <button class="btn btn-primary" :disabled="busy" @click="login">
        {{ busy ? 'Checking...' : 'Log in' }}
      </button>
    </div>

    <template v-else>
      <section class="card">
        <h2>Profiles</h2>
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="p in profiles" :key="p.id">
              <td>{{ p.name }}</td>
              <td>
                <span v-if="p.is_locked" class="chip chip-danger">Locked</span>
                <span v-else class="chip">OK</span>
              </td>
              <td class="actions">
                <button class="btn btn-secondary" @click="resetPin(p)">Reset PIN</button>
                <button class="btn btn-secondary" :disabled="!p.is_locked" @click="clearLockout(p)">
                  Clear lockout
                </button>
                <button class="btn btn-danger" @click="deleteProfile(p)">Delete</button>
              </td>
            </tr>
          </tbody>
        </table>
      </section>

      <section class="card">
        <h2>Products</h2>
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Category</th>
              <th>Barcode</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="p in products" :key="p.id">
              <td>{{ p.name }}</td>
              <td>{{ p.category || '-' }}</td>
              <td class="barcode">{{ p.barcode }}</td>
              <td class="actions">
                <button class="btn btn-secondary" @click="editProduct(p)">Edit</button>
                <button class="btn btn-danger" @click="deleteProduct(p)">Delete</button>
              </td>
            </tr>
          </tbody>
        </table>
      </section>
    </template>
  </div>
</template>

<style scoped>
.admin-page {
  max-width: 720px;
  margin: 0 auto;
  padding: 24px 16px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.admin-header {
  display: flex;
  align-items: center;
  gap: 10px;
}

.admin-header h1 {
  font-size: 1.3rem;
  margin: 0;
}

.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 20px;
  box-shadow: var(--shadow);
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.login-card {
  max-width: 320px;
}

.card h2 {
  margin: 0;
  font-size: 1.05rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.label {
  font-size: 0.85rem;
  font-weight: 600;
}

.field input {
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--bg);
  color: var(--text);
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}

th, td {
  text-align: left;
  padding: 8px 6px;
  border-bottom: 1px solid var(--border);
}

.barcode {
  font-family: ui-monospace, Consolas, monospace;
  font-size: 0.85rem;
}

.actions {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.chip {
  font-size: 0.75rem;
  color: var(--text-muted);
  background: var(--bg);
  border-radius: 999px;
  padding: 2px 8px;
}

.chip-danger {
  color: var(--danger);
  background: var(--danger-bg);
}

.btn {
  border: none;
  border-radius: 999px;
  padding: 6px 12px;
  cursor: pointer;
  font-weight: 600;
  font-size: 0.82rem;
}

.btn-primary {
  background: var(--accent);
  color: var(--accent-contrast);
  padding: 10px 18px;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  background: transparent;
  border: 1px solid var(--border);
  color: var(--text);
}

.btn-secondary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-danger {
  background: transparent;
  border: 1px solid var(--danger);
  color: var(--danger);
}

.hint.error {
  color: var(--danger);
  margin: 0;
  font-size: 0.85rem;
}
</style>
