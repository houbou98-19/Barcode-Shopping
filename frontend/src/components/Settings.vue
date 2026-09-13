<script setup>
import { onMounted, ref } from 'vue'
import { apiFetch, apiUrl, clearSession, getServerUrl, setServerUrl } from '../api'
import { activeListId, loadLists, setActiveListId } from '../listStore'

const props = defineProps({ session: Object })
const emit = defineEmits(['logged-out'])

const serverUrl = ref('')
const saved = ref(false)
const testResult = ref(null)
const testing = ref(false)

const lists = ref([])
const newListName = ref('')
const joinCode = ref('')
const listError = ref('')
const listBusy = ref(false)

async function refreshLists() {
  lists.value = await loadLists()
}

async function createList() {
  if (!newListName.value.trim()) return
  listBusy.value = true
  listError.value = ''
  try {
    const res = await apiFetch('/api/lists', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: newListName.value.trim() }),
    })
    const data = await res.json()
    if (!res.ok) {
      listError.value = data.error || 'Could not create list'
      return
    }
    newListName.value = ''
    setActiveListId(data.id)
    await refreshLists()
  } catch {
    listError.value = 'Could not reach server'
  } finally {
    listBusy.value = false
  }
}

async function joinList() {
  if (!joinCode.value.trim()) return
  listBusy.value = true
  listError.value = ''
  try {
    const res = await apiFetch('/api/lists/join', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ join_code: joinCode.value.trim() }),
    })
    const data = await res.json()
    if (!res.ok) {
      listError.value = data.error || 'Could not join list'
      return
    }
    joinCode.value = ''
    setActiveListId(data.id)
    await refreshLists()
  } catch {
    listError.value = 'Could not reach server'
  } finally {
    listBusy.value = false
  }
}

async function leaveList(list) {
  if (!window.confirm(`Leave "${list.name}"?`)) return
  const res = await apiFetch(`/api/lists/${list.id}/leave`, { method: 'POST' })
  if (res.ok) await refreshLists()
  else listError.value = 'Could not leave list'
}

async function deleteList(list) {
  if (!window.confirm(`Delete "${list.name}" for everyone in it? This cannot be undone.`)) return
  const res = await apiFetch(`/api/lists/${list.id}`, { method: 'DELETE' })
  if (res.ok) await refreshLists()
  else listError.value = 'Could not delete list'
}

function load() {
  serverUrl.value = getServerUrl()
  if (props.session) refreshLists()
}

function save() {
  setServerUrl(serverUrl.value.trim())
  saved.value = true
  testResult.value = null
  setTimeout(() => {
    saved.value = false
  }, 1500)
}

function switchProfile() {
  clearSession()
  emit('logged-out')
}

async function testConnection() {
  testing.value = true
  testResult.value = null
  try {
    // /api/profiles rather than /api/list - the latter now requires a
    // session (see #29), but this check also runs from the login screen's
    // Server settings escape hatch, before any session exists.
    const res = await fetch(apiUrl('/api/profiles'))
    testResult.value = res.ok
      ? { ok: true, message: `Connected (status ${res.status})` }
      : { ok: false, message: `Server responded with status ${res.status}` }
  } catch (err) {
    // fetch() gives no way to tell a CORS block apart from a genuine
    // network failure (DNS, unreachable host, refused connection) - both
    // surface as the same generic TypeError.
    testResult.value = { ok: false, message: 'Could not reach server (network error, blocked, or unreachable)' }
  } finally {
    testing.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="settings">
    <div class="card">
      <div class="field" v-if="props.session">
        <span class="label">Profile</span>
        <div class="profile-row">
          <span>{{ props.session.profileName }}</span>
          <button class="btn btn-secondary" @click="switchProfile">Switch profile</button>
        </div>
      </div>

      <label class="field">
        <span class="label">Server URL</span>
        <input v-model="serverUrl" type="url" placeholder="http://192.168.1.10:8080" />
        <span class="hint">
          Set a URL to always route here instead. (Required for the native Android app, optional otherwise).
        </span>
      </label>

      <div class="actions">
        <button class="btn btn-primary" @click="save">Save</button>
        <button class="btn btn-secondary" :disabled="testing" @click="testConnection">
          {{ testing ? 'Testing...' : 'Test connection' }}
        </button>
      </div>
      <p v-if="saved" class="saved-msg">Saved!</p>
      <p v-if="testResult" :class="testResult.ok ? 'test-ok' : 'test-error'">{{ testResult.message }}</p>
    </div>

    <div class="card" v-if="props.session">
      <span class="label">Lists</span>

      <ul class="list-list">
        <li v-for="l in lists" :key="l.id" class="list-row">
          <div class="list-info">
            <span class="list-name" :class="{ active: l.id === activeListId }">{{ l.name }}</span>
            <span v-if="l.join_code" class="hint">Code: {{ l.join_code }}</span>
          </div>
          <div v-if="!l.is_personal" class="list-actions">
            <button class="btn btn-secondary" @click="leaveList(l)">Leave</button>
            <button
              v-if="l.created_by_profile_id === props.session.profileId"
              class="btn btn-danger"
              @click="deleteList(l)"
            >
              Delete
            </button>
          </div>
        </li>
      </ul>

      <div class="field">
        <span class="label">Create a shared list</span>
        <div class="inline-form">
          <input v-model="newListName" type="text" placeholder="List name" @keyup.enter="createList" />
          <button class="btn btn-primary" :disabled="listBusy || !newListName.trim()" @click="createList">
            Create
          </button>
        </div>
      </div>

      <div class="field">
        <span class="label">Join a shared list</span>
        <div class="inline-form">
          <input v-model="joinCode" type="text" placeholder="3-digit code" maxlength="3" @keyup.enter="joinList" />
          <button class="btn btn-primary" :disabled="listBusy || !joinCode.trim()" @click="joinList">Join</button>
        </div>
      </div>

      <p v-if="listError" class="test-error">{{ listError }}</p>
    </div>
  </div>
</template>

<style scoped>
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 20px;
  box-shadow: var(--shadow);
  display: flex;
  flex-direction: column;
  gap: 18px;
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

.field input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.hint {
  font-size: 0.78rem;
  color: var(--text-muted);
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
  background: transparent;
  color: var(--text);
  border: 1px solid var(--border);
}

.btn-secondary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-danger {
  background: transparent;
  border: 1px solid var(--danger);
  color: var(--danger);
}

.list-actions {
  display: flex;
  gap: 6px;
}

.actions {
  display: flex;
  gap: 10px;
}

.profile-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.list-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.list-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.list-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.list-name {
  font-weight: 600;
}

.list-name.active {
  color: var(--accent);
}

.inline-form {
  display: flex;
  gap: 8px;
}

.inline-form input {
  flex: 1;
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--bg);
  color: var(--text);
}

.saved-msg {
  color: var(--accent);
  font-size: 0.85rem;
  margin: 0;
}

.test-ok {
  color: var(--accent);
  font-size: 0.85rem;
  margin: 0;
}

.test-error {
  color: #f87171;
  font-size: 0.85rem;
  margin: 0;
}
</style>
