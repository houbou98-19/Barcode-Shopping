<script setup>
import { onMounted, ref } from 'vue'
import { apiUrl, clearSession, getServerUrl, setServerUrl } from '../api'

const props = defineProps({ session: Object })
const emit = defineEmits(['logged-out'])

const serverUrl = ref('')
const saved = ref(false)
const testResult = ref(null)
const testing = ref(false)

function load() {
  serverUrl.value = getServerUrl()
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
    const res = await fetch(apiUrl('/api/list'))
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
