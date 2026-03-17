import { ref, onMounted, watch } from 'vue';
import { fetchSummaries, fetchOcrPages } from '../api/client.js';

export default {
    props: {
        fileId: {
            required: true
        }
    },
    setup(props) {
        // AI tab state
        const summaries = ref([]);
        const isLoading = ref(false);
        const error = ref(null);

        // OCR tab state
        const activeTab = ref('ai');
        const ocrPages = ref([]);
        const isOcrLoading = ref(false);
        const ocrError = ref(null);
        const ocrLoaded = ref(false);

        const loadSummaries = async () => {
            if (!props.fileId) return;

            isLoading.value = true;
            error.value = null;
            summaries.value = [];

            try {
                const result = await fetchSummaries(props.fileId);
                // Sort by creation time desc
                summaries.value = result.sort((a, b) => (b.creationTime || 0) - (a.creationTime || 0));
            } catch (e) {
                console.error(e);
                error.value = "Failed to load summaries.";
            } finally {
                isLoading.value = false;
            }
        };

        const loadOcr = async () => {
            if (!props.fileId || ocrLoaded.value) return;

            isOcrLoading.value = true;
            ocrError.value = null;

            try {
                ocrPages.value = await fetchOcrPages(props.fileId);
                ocrLoaded.value = true;
            } catch (e) {
                console.error(e);
                ocrError.value = "Failed to load OCR text.";
            } finally {
                isOcrLoading.value = false;
            }
        };

        const selectTab = (tab) => {
            activeTab.value = tab;
            if (tab === 'ocr') loadOcr();
        };

        onMounted(loadSummaries);
        watch(() => props.fileId, () => {
            // Reset all state when the viewed file changes
            activeTab.value = 'ai';
            ocrPages.value = [];
            ocrLoaded.value = false;
            ocrError.value = null;
            loadSummaries();
        });

        // Helper to format text (simple line breaks)
        const formatContent = (text) => {
            if (!text) return "";
            return text.replace(/\n/g, '<br/>');
        };

        const formatDate = (ts) => {
            if (!ts) return "";
            return new Date(ts).toLocaleString();
        };

        return {
            summaries,
            isLoading,
            error,
            activeTab,
            ocrPages,
            isOcrLoading,
            ocrError,
            selectTab,
            formatContent,
            formatDate
        };
    },
    template: `
    <div class="h-full flex flex-col bg-white dark:bg-gray-800 border-l border-gray-200 dark:border-gray-700 w-full md:w-96">
        <!-- Header -->
        <div class="border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-700">
            <div class="px-4 flex items-center justify-between">
                <h3 class="font-semibold text-black dark:text-white flex items-center gap-2 shrink-0">
                    <svg class="w-5 h-5 text-gray-600 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
                    AI Insights
                </h3>
                <!-- Tabs inline with header -->
                <div class="flex gap-1 mx-2">
                    <button
                        @click="selectTab('ai')"
                        :class="[
                            'px-3 py-3 text-sm font-medium transition-colors border-b-2',
                            activeTab === 'ai'
                                ? 'border-black dark:border-white text-black dark:text-white'
                                : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-black dark:hover:text-white'
                        ]"
                    >AI</button>
                    <button
                        @click="selectTab('ocr')"
                        :class="[
                            'px-3 py-3 text-sm font-medium transition-colors border-b-2',
                            activeTab === 'ocr'
                                ? 'border-black dark:border-white text-black dark:text-white'
                                : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-black dark:hover:text-white'
                        ]"
                    >OCR</button>
                </div>
                <button @click="$emit('close')" class="text-gray-400 hover:text-black dark:hover:text-white transition-colors shrink-0">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
                </button>
            </div>
        </div>

        <!-- AI Tab Content -->
        <div v-if="activeTab === 'ai'" class="flex-1 overflow-y-auto p-4 space-y-4">
            <!-- Loading -->
            <div v-if="isLoading" class="flex flex-col items-center justify-center py-12">
                <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-black dark:border-white mb-3"></div>
                <p class="text-sm text-gray-500 dark:text-gray-400">Thinking...</p>
            </div>

            <!-- Error -->
            <div v-if="error" class="bg-gray-100 dark:bg-gray-700 text-black dark:text-white border border-gray-300 dark:border-gray-600 p-4 rounded text-sm">
                {{ error }}
            </div>

            <!-- Empty State -->
            <div v-if="!isLoading && !error && summaries.length === 0" class="text-center py-12">
                <p class="text-gray-400 mb-2">No insights yet.</p>
                <p class="text-xs text-gray-400">Summaries and transcripts will appear here once processed.</p>
            </div>

            <!-- List -->
            <div v-for="item in summaries" :key="item.id" class="bg-gray-50 dark:bg-gray-700 rounded p-4 border border-gray-200 dark:border-gray-600">
                <div class="flex items-center justify-between mb-2">
                    <span class="text-xs font-semibold px-2 py-1 rounded bg-white dark:bg-gray-600 text-gray-600 dark:text-gray-300 border border-gray-200 dark:border-gray-500 capitalize">
                        {{ item.dataSource || 'Unknown' }}
                    </span>
                    <span class="text-xs text-gray-400">{{ formatDate(item.creationTime) }}</span>
                </div>
                <div class="prose prose-sm max-w-none text-gray-700 dark:text-gray-300" v-html="formatContent(item.content)"></div>
            </div>
        </div>

        <!-- OCR Tab Content -->
        <div v-if="activeTab === 'ocr'" class="flex-1 overflow-y-auto p-4 space-y-4">
            <!-- Loading -->
            <div v-if="isOcrLoading" class="flex flex-col items-center justify-center py-12">
                <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-black dark:border-white mb-3"></div>
                <p class="text-sm text-gray-500 dark:text-gray-400">Loading OCR text...</p>
            </div>

            <!-- Error -->
            <div v-if="ocrError" class="bg-gray-100 dark:bg-gray-700 text-black dark:text-white border border-gray-300 dark:border-gray-600 p-4 rounded text-sm">
                {{ ocrError }}
            </div>

            <!-- Empty State -->
            <div v-if="!isOcrLoading && !ocrError && ocrPages.length === 0" class="text-center py-12">
                <p class="text-gray-400 mb-2">No OCR text available.</p>
                <p class="text-xs text-gray-400">Text will appear here once the note has been processed.</p>
            </div>

            <!-- Pages -->
            <div v-for="page in ocrPages" :key="page.pageIndex" class="bg-gray-50 dark:bg-gray-700 rounded p-4 border border-gray-200 dark:border-gray-600">
                <div class="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-2 font-mono">
                    Page {{ page.pageIndex + 1 }}
                </div>
                <div class="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">{{ page.textContent }}</div>
            </div>
        </div>
    </div>
    `
};
