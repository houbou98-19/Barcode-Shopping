<script setup>
import { onMounted, ref } from 'vue'
import { apiUrl, setSession } from '../api'
import Settings from './Settings.vue'

const emit = defineEmits(['login'])

const profiles = ref([])
const loadError = ref('')
const selected = ref(null) // profile object being logged into, or null
const pin = ref('')
const error = ref('')
const busy = ref(false)

const creating = ref(false)
const newName = ref('')
const newPin = ref('')
const createError = ref('')

// The native Android app has no real origin to resolve a relative
// /api/... path against - Server URL must be set before this screen's
// own fetch to /api/profiles can ever succeed. Gating the whole app
// behind login (see App.vue) means this is the only place a first-run
// native user could reach that setting, so it has to be reachable from
// here too, not just from the post-login Settings tab.
const showServerSettings = ref(false)

function closeServerSettings() {
  showServerSettings.value = false
  loadProfiles()
}

async function loadProfiles() {
  loadError.value = ''
  try {
    const res = await fetch(apiUrl('/api/profiles'))
    if (!res.ok) throw new Error()
    profiles.value = await res.json()
  } catch {
    loadError.value = 'Could not reach the server'
  }
}

function choose(profile) {
  selected.value = profile
  pin.value = ''
  error.value = ''
}

function cancel() {
  selected.value = null
  pin.value = ''
  error.value = ''
}

async function submitPin() {
  if (pin.value.length !== 4) return
  busy.value = true
  error.value = ''
  try {
    const res = await fetch(apiUrl(`/api/profiles/${selected.value.id}/verify-pin`), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pin: pin.value }),
    })
    const data = await res.json()
    if (!res.ok) {
      error.value = 'Incorrect PIN'
      pin.value = ''
      return
    }
    setSession({ token: data.token, profileId: selected.value.id, profileName: selected.value.name })
    emit('login')
  } catch {
    error.value = 'Could not reach the server'
  } finally {
    busy.value = false
  }
}

async function submitCreate() {
  if (!newName.value || newPin.value.length !== 4) return
  busy.value = true
  createError.value = ''
  try {
    const res = await fetch(apiUrl('/api/profiles'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: newName.value, pin: newPin.value }),
    })
    const data = await res.json()
    if (!res.ok) {
      createError.value = data.error || 'Could not create profile'
      return
    }
    profiles.value.push(data)
    creating.value = false
    newName.value = ''
    newPin.value = ''
  } catch {
    createError.value = 'Could not reach the server'
  } finally {
    busy.value = false
  }
}

onMounted(loadProfiles)
</script>

<template>
  <div v-if="showServerSettings" class="login-screen">
    <h1>Server settings</h1>
    <Settings />
    <button class="btn btn-secondary" @click="closeServerSettings">Back</button>
  </div>

  <div v-else class="login-screen">
    <h1>Who's shopping?</h1>

    <p v-if="loadError" class="hint error">{{ loadError }}</p>
    <button v-if="loadError" class="btn btn-secondary" @click="showServerSettings = true">
      Server settings
    </button>

    <div v-if="!selected && !creating" class="profile-grid">
      <button v-for="p in profiles" :key="p.id" class="profile-btn" @click="choose(p)">
        {{ p.name }}
      </button>
      <button class="profile-btn profile-btn-new" @click="creating = true">+ New profile</button>
    </div>

    <div v-if="selected" class="card">
      <p>Enter PIN for <strong>{{ selected.name }}</strong></p>
      <input
        v-model="pin"
        type="password"
        inputmode="numeric"
        maxlength="4"
        placeholder="****"
        autofocus
        @keyup.enter="submitPin"
      />
      <p v-if="error" class="hint error">{{ error }}</p>
      <div class="actions">
        <button class="btn btn-secondary" @click="cancel">Back</button>
        <button class="btn btn-primary" :disabled="busy || pin.length !== 4" @click="submitPin">
          {{ busy ? 'Checking...' : 'Log in' }}
        </button>
      </div>
    </div>

    <div v-if="creating" class="card">
      <p>Create a profile</p>
      <input v-model="newName" type="text" placeholder="Name" />
      <input v-model="newPin" type="password" inputmode="numeric" maxlength="4" placeholder="4-digit PIN" />
      <p v-if="createError" class="hint error">{{ createError }}</p>
      <div class="actions">
        <button class="btn btn-secondary" @click="creating = false">Back</button>
        <button class="btn btn-primary" :disabled="busy || !newName || newPin.length !== 4" @click="submitCreate">
          {{ busy ? 'Creating...' : 'Create' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-screen {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 20px;
  min-height: 100svh;
  padding: 24px;
  text-align: center;
}

.profile-grid {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 12px;
}

.profile-btn {
  padding: 16px 20px;
  border-radius: 12px;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text);
  font-weight: 600;
  cursor: pointer;
  box-shadow: var(--shadow);
}

.profile-btn-new {
  background: none;
  border-style: dashed;
  color: var(--text-muted);
  font-weight: 500;
}

.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 20px;
  box-shadow: var(--shadow);
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 100%;
  max-width: 320px;
}

.card input {
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--bg);
  color: var(--text);
  text-align: center;
  letter-spacing: 0.3em;
}

.actions {
  display: flex;
  gap: 10px;
  justify-content: center;
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

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  background: transparent;
  border: 1px solid var(--border);
  color: var(--text);
}

.hint {
  margin: 0;
}

.hint.error {
  color: var(--danger);
}
</style>
