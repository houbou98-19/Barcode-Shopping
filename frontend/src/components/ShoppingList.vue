<script setup>
import { onMounted, ref } from 'vue'

const items = ref([])
const loading = ref(false)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await fetch('/api/list')
    if (!res.ok) throw new Error()
    items.value = await res.json()
  } catch {
    error.value = 'Could not load the shopping list'
  } finally {
    loading.value = false
  }
}

async function toggleChecked(item) {
  const checked = item.checked ? 0 : 1
  const previous = item.checked
  item.checked = checked
  try {
    const res = await fetch(`/api/list/${item.id}`, {
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
    const res = await fetch(`/api/list/${item.id}`, {
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
    const res = await fetch(`/api/list/${item.id}`, { method: 'DELETE' })
    if (!res.ok) throw new Error()
    items.value = items.value.filter((i) => i.id !== item.id)
  } catch {
    error.value = 'Could not remove item'
  }
}

onMounted(load)
</script>

<template>
  <div class="shopping-list">
    <p v-if="loading">Loading...</p>
    <p v-if="error" class="error">{{ error }}</p>
    <p v-if="!loading && items.length === 0">Your shopping list is empty.</p>

    <ul>
      <li v-for="item in items" :key="item.id" :class="{ checked: item.checked }">
        <label>
          <input type="checkbox" :checked="!!item.checked" @change="toggleChecked(item)" />
          <span class="name">{{ item.name }}</span>
          <span v-if="item.category" class="category">({{ item.category }})</span>
        </label>
        <span class="quantity">
          <button :disabled="item.quantity <= 1" @click="changeQuantity(item, -1)">-</button>
          {{ item.quantity }}
          <button @click="changeQuantity(item, 1)">+</button>
        </span>
        <button class="remove" @click="removeItem(item)">Remove</button>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.shopping-list ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.shopping-list li {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 0;
  border-bottom: 1px solid #e5e4e7;
}

.shopping-list li.checked .name {
  text-decoration: line-through;
  opacity: 0.5;
}

.category {
  opacity: 0.6;
  font-size: 0.9em;
}

.quantity {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-left: auto;
}

.error {
  color: #b00020;
}
</style>
