<script setup>
import { onMounted, ref } from 'vue'
import { getServerUrl, setServerUrl } from '../api'

const displayName = ref('')
const serverUrl = ref('')
const saved = ref(false)

function load() {
  displayName.value = localStorage.getItem('displayName') || ''
  serverUrl.value = getServerUrl()
}

function save() {
  if (displayName.value) {
    localStorage.setItem('displayName', displayName.value)
  } else {
    localStorage.removeItem('displayName')
  }
  setServerUrl(serverUrl.value.trim())
  saved.value = true
  setTimeout(() => {
    saved.value = false
  }, 1500)
}

onMounted(load)
</script>

<template>
  <div class="settings">
    <div class="card">
      <label class="field">
        <span class="label">Display name</span>
        <input v-model="displayName" type="text" placeholder="e.g. Alex" />
      </label>

      <label class="field">
        <span class="label">Pin code</span>
        <input type="password" placeholder="Coming soon" disabled />
        <span class="hint">Not implemented yet - will lock the app per person</span>
      </label>

      <label class="field">
        <span class="label">Server URL</span>
        <input v-model="serverUrl" type="url" placeholder="http://192.168.1.10:8080" />
        <span class="hint">
          Set a URL to always route here instead. (Required for the native Android app, optional otherwise).
        </span>
      </label>

      <button class="btn btn-primary" @click="save">Save</button>
      <p v-if="saved" class="saved-msg">Saved!</p>
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

.saved-msg {
  color: var(--accent);
  font-size: 0.85rem;
  margin: 0;
}
</style>
