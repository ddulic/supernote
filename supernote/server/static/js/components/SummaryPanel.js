import { ref, computed, onMounted, watch, nextTick } from 'vue';
import { fetchSummaries, fetchOcrPages } from '../api/client.js';

export default {
    props: {
        fileId: {
            required: true
        },
        activePage: {
            type: Number,
            default: 1
        }
    },
    emits: ['close', 'has-insights'],
    setup(props, { emit }) {
        const ocrContainerRef = ref(null);
        const aiContainerRef = ref(null);

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
                summaries.value = result
                    .filter(s => (s.dataSource || '').toUpperCase() !== 'OCR')
                    .sort((a, b) => (b.creationTime || 0) - (a.creationTime || 0));
                if (summaries.value.length > 0) emit('has-insights');
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

        function parseSegments(item) {
            if (!item.metadata) return null;
            try {
                const meta = JSON.parse(item.metadata);
                const segs = meta.segments;
                if (Array.isArray(segs) && segs.length > 0) return segs;
            } catch (_) {}
            return null;
        }

        const aiRows = computed(() => {
            const rows = [];
            for (const item of summaries.value) {
                const segments = parseSegments(item);
                if (segments) {
                    segments.forEach((seg, idx) => {
                        rows.push({
                            key: `${item.id}-seg-${idx}`,
                            dataSource: item.dataSource,
                            creationTime: item.creationTime,
                            dateRange: seg.date_range,
                            content: seg.summary,
                            pageRefs: seg.page_refs || [],
                        });
                    });
                } else {
                    rows.push({
                        key: `${item.id}-full`,
                        dataSource: item.dataSource,
                        creationTime: item.creationTime,
                        dateRange: null,
                        content: item.content,
                        pageRefs: [],
                    });
                }
            }
            return rows;
        });

        function segmentIndexForPage(pageNo) {
            if (!pageNo || aiRows.value.length === 0) return -1;
            let best = -1;
            for (let i = 0; i < aiRows.value.length; i++) {
                const refs = aiRows.value[i].pageRefs;
                if (refs.length > 0 && Math.min(...refs) <= pageNo) {
                    best = i;
                }
            }
            return best >= 0 ? best : 0;
        }

        const SCROLL_PADDING = 16; // matches space-y-4 between panel cards

        function scrollAiToPage(pageNo) {
            const container = aiContainerRef.value;
            if (!container) return;
            const idx = segmentIndexForPage(pageNo);
            if (idx < 0) return;
            const el = container.querySelector(`[data-ai-segment="${idx}"]`);
            if (!el) return;
            const top = el.getBoundingClientRect().top - container.getBoundingClientRect().top + container.scrollTop - SCROLL_PADDING;
            container.scrollTo({ top: Math.max(0, top), behavior: 'smooth' });
        }

        function scrollOcrToPage(pageNo) {
            const container = ocrContainerRef.value;
            if (!container || !pageNo) return;
            const el = container.querySelector(`[data-ocr-page="${pageNo}"]`);
            if (!el) return;
            const top = el.getBoundingClientRect().top - container.getBoundingClientRect().top + container.scrollTop - SCROLL_PADDING;
            container.scrollTo({ top: Math.max(0, top), behavior: 'smooth' });
        }

        watch([() => props.activePage, activeTab], ([newPage, tab]) => {
            if (tab === 'ocr') {
                nextTick(() => scrollOcrToPage(newPage));
            } else if (tab === 'ai') {
                nextTick(() => scrollAiToPage(newPage));
            }
        });

        onMounted(loadSummaries);
        watch(() => props.fileId, () => {
            activeTab.value = 'ai';
            ocrPages.value = [];
            ocrLoaded.value = false;
            ocrError.value = null;
            loadSummaries();
        });

        const formatDate = (ts) => {
            if (!ts) return "";
            return new Date(ts).toLocaleString();
        };

        return {
            isLoading,
            error,
            activeTab,
            aiRows,
            aiContainerRef,
            ocrPages,
            isOcrLoading,
            ocrError,
            ocrContainerRef,
            selectTab,
            formatDate
        };
    },
    template: `
    <div class="flex-1 min-h-0 flex flex-col bg-white dark:bg-gray-800 border-l border-gray-200 dark:border-gray-700 w-full md:w-96">
        <!-- Header -->
        <div class="border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-700">
            <div class="px-4 flex items-center justify-between">
                <h3 class="font-semibold text-black dark:text-white flex items-center gap-2 shrink-0">
                    <svg class="w-5 h-5 text-gray-600 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
                    AI Insights
                </h3>
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
        <div v-if="activeTab === 'ai'" ref="aiContainerRef" class="flex-1 min-h-0 overflow-y-auto p-4 space-y-4">
            <div v-if="isLoading" class="flex flex-col items-center justify-center py-12">
                <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-black dark:border-white mb-3"></div>
                <p class="text-sm text-gray-500 dark:text-gray-400">Thinking...</p>
            </div>
            <div v-if="error" class="bg-gray-100 dark:bg-gray-700 text-black dark:text-white border border-gray-300 dark:border-gray-600 p-4 rounded text-sm">
                {{ error }}
            </div>
            <div v-if="!isLoading && !error && aiRows.length === 0" class="text-center py-12">
                <p class="text-gray-400 mb-2">No insights yet.</p>
                <p class="text-xs text-gray-400">Summaries and transcripts will appear here once processed.</p>
            </div>
            <div v-for="(row, idx) in aiRows" :key="row.key" :data-ai-segment="idx" class="bg-gray-50 dark:bg-gray-700 rounded p-4 border border-gray-200 dark:border-gray-600">
                <div v-if="row.dateRange || row.pageRefs.length > 0" class="flex items-center justify-between mb-2">
                    <span v-if="row.dateRange" class="text-xs font-medium text-black dark:text-white truncate">{{ row.dateRange }}</span>
                    <span v-if="row.pageRefs.length > 0" class="text-xs text-gray-400 font-mono shrink-0 ml-auto">p.{{ row.pageRefs.join(', ') }}</span>
                </div>
                <div class="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">{{ row.content }}</div>
            </div>
        </div>

        <!-- OCR Tab Content -->
        <div v-if="activeTab === 'ocr'" ref="ocrContainerRef" class="flex-1 min-h-0 overflow-y-auto p-4 space-y-4">
            <div v-if="isOcrLoading" class="flex flex-col items-center justify-center py-12">
                <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-black dark:border-white mb-3"></div>
                <p class="text-sm text-gray-500 dark:text-gray-400">Loading OCR text...</p>
            </div>
            <div v-if="ocrError" class="bg-gray-100 dark:bg-gray-700 text-black dark:text-white border border-gray-300 dark:border-gray-600 p-4 rounded text-sm">
                {{ ocrError }}
            </div>
            <div v-if="!isOcrLoading && !ocrError && ocrPages.length === 0" class="text-center py-12">
                <p class="text-gray-400 mb-2">No OCR text available.</p>
                <p class="text-xs text-gray-400">Text will appear here once the note has been processed.</p>
            </div>
            <div v-for="page in ocrPages" :key="page.pageIndex" :data-ocr-page="page.pageIndex + 1" class="bg-gray-50 dark:bg-gray-700 rounded p-4 border border-gray-200 dark:border-gray-600">
                <div class="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-2 font-mono">
                    Page {{ page.pageIndex + 1 }}
                </div>
                <div class="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">{{ page.textContent }}</div>
            </div>
        </div>
    </div>
    `
};
