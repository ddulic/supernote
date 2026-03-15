import { useToast } from '../composables/useToast.js';

const icons = {
    error: `<svg class="w-5 h-5 shrink-0 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>`,
    success: `<svg class="w-5 h-5 shrink-0 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>`,
    info: `<svg class="w-5 h-5 shrink-0 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>`,
};

export default {
    setup() {
        const { toasts, removeToast } = useToast();
        return { toasts, removeToast, icons };
    },
    template: `
    <div class="fixed top-20 inset-x-0 z-[300] pointer-events-none">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col gap-2 items-end">
        <transition-group name="toast">
            <div
                v-for="toast in toasts"
                :key="toast.id"
                class="pointer-events-auto flex items-start gap-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg p-4 w-80 max-w-[calc(100vw-2rem)]"
            >
                <span v-html="icons[toast.type] || icons.info"></span>
                <div class="flex-1 min-w-0">
                    <p class="text-sm font-semibold text-black dark:text-white">{{ toast.title }}</p>
                    <p v-if="toast.detail" class="text-xs text-gray-500 dark:text-gray-400 mt-0.5 break-words">{{ toast.detail }}</p>
                </div>
                <button @click="removeToast(toast.id)" class="shrink-0 text-gray-400 hover:text-black dark:hover:text-white transition-colors">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
                </button>
            </div>
        </transition-group>
        </div>
    </div>
    `
};
