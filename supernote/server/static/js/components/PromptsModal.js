import { ref, onMounted, computed } from 'https://unpkg.com/vue@3/dist/vue.esm-browser.js';
import { fetchPrompts, savePrompt, deletePrompt, reprocessAllNotes } from '../api/client.js';
import { useToast } from '../composables/useToast.js';

const { addToast } = useToast();

export default {
    name: 'PromptsModal',
    emits: ['close'],
    template: `
        <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4" @click.self="$emit('close')">
            <div class="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-3xl max-h-[90vh] flex flex-col">
                <!-- Header -->
                <div class="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
                    <div>
                        <h2 class="text-xl font-bold text-gray-800 dark:text-white">Prompt Configuration</h2>
                        <p class="text-sm text-gray-500 dark:text-gray-400 mt-0.5">Customise OCR and summary prompts per note type.</p>
                    </div>
                    <button @click="$emit('close')" class="text-gray-400 hover:text-black dark:hover:text-white transition-colors">
                        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                        </svg>
                    </button>
                </div>

                <!-- Tab Bar -->
                <div class="flex items-center border-b border-gray-200 dark:border-gray-700 px-4 pt-2">
                    <button
                        v-for="tab in ['ocr', 'summary']"
                        :key="tab"
                        @click="activeTab = tab"
                        :class="['px-4 py-2 text-sm font-medium border-b-2 transition-colors mr-2',
                            activeTab === tab
                                ? 'border-black dark:border-white text-black dark:text-white'
                                : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200']"
                    >{{ tabLabels[tab] }}</button>
                    <div class="ml-auto pb-2 flex items-center gap-2">
                        <!-- Confirmation prompt -->
                        <template v-if="confirmingReprocessAll">
                            <span class="text-xs text-amber-700 dark:text-amber-300 max-w-xs">This will reprocess all notes and may incur substantial AI costs. Continue?</span>
                            <button
                                @click="confirmReprocessAllNotes"
                                :disabled="reprocessingAllNotes"
                                class="px-3 py-1.5 bg-black border border-black rounded text-sm font-medium text-white hover:bg-gray-800 disabled:opacity-50 transition-colors flex items-center gap-1"
                            >
                                <svg v-if="reprocessingAllNotes" class="animate-spin w-3 h-3" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                                {{ reprocessingAllNotes ? 'Queuing…' : 'Yes, reprocess' }}
                            </button>
                            <button
                                @click="confirmingReprocessAll = false"
                                :disabled="reprocessingAllNotes"
                                class="px-3 py-1.5 bg-white dark:bg-gray-600 border border-gray-300 dark:border-gray-500 rounded text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-500 disabled:opacity-50 transition-colors"
                            >Cancel</button>
                        </template>
                        <!-- Trigger button -->
                        <button
                            v-else
                            @click="confirmingReprocessAll = true"
                            class="px-3 py-1.5 bg-white dark:bg-gray-600 border border-gray-300 dark:border-gray-500 rounded text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-500 transition-colors flex items-center gap-1.5"
                            title="Reprocess all notes with current prompts"
                        >
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg>
                            Reprocess All Notes
                        </button>
                    </div>
                </div>

                <!-- Content -->
                <div class="flex-1 overflow-y-auto p-4">
                    <div v-if="loading" class="flex justify-center py-8">
                        <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-black dark:border-white"></div>
                    </div>

                    <div v-else>
                        <!-- Existing layers -->
                        <div v-for="prompt in tabPrompts" :key="prompt.category + '/' + prompt.layer" class="mb-4 border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
                            <div class="flex items-center justify-between px-3 py-2 bg-gray-50 dark:bg-gray-700">
                                <div class="flex items-center gap-2">
                                    <span class="text-sm font-medium text-gray-700 dark:text-gray-200 capitalize">{{ prompt.layer }}</span>
                                    <span v-if="prompt.isOverride" class="text-xs bg-gray-200 dark:bg-gray-600 text-gray-600 dark:text-gray-300 px-2 py-0.5 rounded-full">customised</span>
                                </div>
                                <button
                                    v-if="prompt.isOverride && !isProtected(prompt)"
                                    @click="handleRemove(prompt)"
                                    :disabled="saving[prompt.category + '/' + prompt.layer]"
                                    class="px-3 py-1.5 text-xs font-medium text-red-600 dark:text-red-400 border border-red-200 dark:border-red-700 bg-red-50 dark:bg-red-900/20 hover:bg-red-100 dark:hover:bg-red-900/40 rounded transition-colors disabled:opacity-50"
                                    title="Remove this prompt override"
                                >Remove</button>
                            </div>
                            <div class="p-3">
                                <textarea
                                    v-model="editContents[prompt.category + '/' + prompt.layer]"
                                    rows="5"
                                    class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-600 text-gray-900 dark:text-white rounded text-sm font-mono focus:outline-none focus:ring-2 focus:ring-black dark:focus:ring-white resize-y"
                                    :placeholder="'Enter ' + prompt.layer + ' prompt…'"
                                ></textarea>
                                <div class="flex justify-end mt-2">
                                    <button
                                        @click="handleSave(prompt)"
                                        :disabled="saving[prompt.category + '/' + prompt.layer] || !editContents[prompt.category + '/' + prompt.layer]"
                                        class="shrink-0 px-3 py-1.5 bg-black border border-black rounded text-sm font-medium text-white hover:bg-gray-800 disabled:opacity-50 transition-colors"
                                    >{{ saving[prompt.category + '/' + prompt.layer] ? 'Saving…' : 'Save' }}</button>
                                </div>
                            </div>
                        </div>

                        <!-- Add custom type -->
                        <div class="mt-6 border border-dashed border-gray-300 dark:border-gray-600 rounded-lg p-4">
                            <h3 class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Add Custom Note Type</h3>
                            <div class="flex gap-2 mb-3">
                                <input
                                    v-model="newLayerName"
                                    type="text"
                                    placeholder="Type name (e.g. project, work)"
                                    class="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-600 text-gray-900 dark:text-white rounded text-sm focus:outline-none focus:ring-2 focus:ring-black dark:focus:ring-white"
                                    @keyup.enter="focusNewContent"
                                />
                            </div>
                            <textarea
                                ref="newContentRef"
                                v-model="newLayerContent"
                                rows="4"
                                :placeholder="'Enter prompt for ' + (newLayerName || 'custom type') + '…'"
                                class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-600 text-gray-900 dark:text-white rounded text-sm font-mono focus:outline-none focus:ring-2 focus:ring-black dark:focus:ring-white resize-y mb-3"
                            ></textarea>
                            <button
                                @click="handleAddCustom"
                                :disabled="!newLayerName.trim() || !newLayerContent.trim() || addingCustom"
                                class="px-4 py-2 bg-black border border-black rounded text-sm font-medium text-white hover:bg-gray-800 disabled:opacity-50 transition-colors"
                            >{{ addingCustom ? 'Adding…' : 'Add Custom Type' }}</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `,
    setup(props, { emit }) {
        const loading = ref(true);
        const prompts = ref([]);
        const activeTab = ref('ocr');
        const editContents = ref({});
        const saving = ref({});
        const newLayerName = ref('');
        const newLayerContent = ref('');
        const addingCustom = ref(false);
        const newContentRef = ref(null);
        const reprocessingAllNotes = ref(false);
        const confirmingReprocessAll = ref(false);

        const tabLabels = { ocr: 'OCR', summary: 'Summary' };

        const tabPrompts = computed(() =>
            prompts.value.filter(p => p.category === activeTab.value)
        );

        async function load() {
            loading.value = true;
            try {
                const data = await fetchPrompts();
                prompts.value = data.prompts || [];
                // Populate edit buffers
                const contents = {};
                for (const p of prompts.value) {
                    contents[p.category + '/' + p.layer] = p.content;
                }
                editContents.value = contents;
            } catch (e) {
                addToast('Failed to load prompts: ' + e.message, 'error');
            } finally {
                loading.value = false;
            }
        }

        async function handleSave(prompt) {
            const key = prompt.category + '/' + prompt.layer;
            const content = editContents.value[key];
            if (!content || !content.trim()) return;
            saving.value = { ...saving.value, [key]: true };
            try {
                await savePrompt(prompt.category, prompt.layer, content.trim());
                addToast('Prompt saved.', 'success');
                await load();
            } catch (e) {
                addToast('Save failed: ' + e.message, 'error');
            } finally {
                saving.value = { ...saving.value, [key]: false };
            }
        }

        const PROTECTED = new Set(['ocr/default', 'summary/default', 'summary/common']);
        function isProtected(prompt) {
            return PROTECTED.has(prompt.category + '/' + prompt.layer);
        }

        async function handleRemove(prompt) {
            const key = prompt.category + '/' + prompt.layer;
            saving.value = { ...saving.value, [key]: true };
            try {
                await deletePrompt(prompt.category, prompt.layer);
                addToast('Prompt removed.', 'success');
                await load();
            } catch (e) {
                addToast('Remove failed: ' + e.message, 'error');
            } finally {
                saving.value = { ...saving.value, [key]: false };
            }
        }

        async function handleAddCustom() {
            const layer = newLayerName.value.trim();
            const content = newLayerContent.value.trim();
            if (!layer || !content) return;
            addingCustom.value = true;
            try {
                await savePrompt(activeTab.value, layer, content);
                addToast('Custom type added.', 'success');
                newLayerName.value = '';
                newLayerContent.value = '';
                await load();
            } catch (e) {
                addToast('Failed to add custom type: ' + e.message, 'error');
            } finally {
                addingCustom.value = false;
            }
        }

        function focusNewContent() {
            if (newContentRef.value) newContentRef.value.focus();
        }

        async function confirmReprocessAllNotes() {
            reprocessingAllNotes.value = true;
            try {
                const result = await reprocessAllNotes();
                addToast(`Queued ${result.queuedPageCount ?? 0} file(s) for reprocessing.`, 'success');
                confirmingReprocessAll.value = false;
            } catch (e) {
                addToast('Reprocess all failed: ' + e.message, 'error');
            } finally {
                reprocessingAllNotes.value = false;
            }
        }

        onMounted(load);

        return {
            loading,
            prompts,
            activeTab,
            tabLabels,
            tabPrompts,
            editContents,
            saving,
            newLayerName,
            newLayerContent,
            newContentRef,
            addingCustom,
            reprocessingAllNotes,
            confirmingReprocessAll,
            isProtected,
            handleSave,
            handleRemove,
            handleAddCustom,
            focusNewContent,
            confirmReprocessAllNotes,
        };
    }
};
