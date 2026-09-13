import { ref } from 'vue'
import { apiFetch } from './api'

const ACTIVE_LIST_KEY = 'activeListId'

const stored = Number(localStorage.getItem(ACTIVE_LIST_KEY))
export const activeListId = ref(Number.isInteger(stored) && stored > 0 ? stored : null)

export function setActiveListId(id) {
  activeListId.value = id
  localStorage.setItem(ACTIVE_LIST_KEY, String(id))
}

export function clearActiveListId() {
  activeListId.value = null
  localStorage.removeItem(ACTIVE_LIST_KEY)
}

/**
 * Fetches the current profile's lists, and falls back to their personal
 * list if nothing valid is selected yet - covers first login, and a
 * leftover activeListId from a different profile after switching.
 */
export async function loadLists() {
  const res = await apiFetch('/api/lists')
  if (!res.ok) return []
  const lists = await res.json()

  if (!activeListId.value || !lists.some((l) => l.id === activeListId.value)) {
    const personal = lists.find((l) => l.is_personal) || lists[0]
    if (personal) setActiveListId(personal.id)
  }

  return lists
}
