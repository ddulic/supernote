import { ref } from 'vue';

// Module-level singleton so any component can import and share state
const toasts = ref([]);
let nextId = 0;

function addToast(title, detail = '', type = 'error', duration = 4000) {
    const id = ++nextId;
    toasts.value.push({ id, title, detail, type });
    setTimeout(() => removeToast(id), duration);
}

function removeToast(id) {
    toasts.value = toasts.value.filter(t => t.id !== id);
}

export function useToast() {
    return { toasts, addToast, removeToast };
}
