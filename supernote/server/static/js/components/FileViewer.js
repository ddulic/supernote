import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'https://unpkg.com/vue@3/dist/vue.esm-browser.js';
import { convertNoteToPng, fetchStaleness, reprocessFile, reprocessPage } from '../api/client.js';
import SummaryPanel from './SummaryPanel.js';

export default {
    components: {
        SummaryPanel
    },
    props: {
        file: {
            type: Object,
            required: true
        },
        breadcrumbs: {
            type: Array,
            default: () => []
        }
    },
    emits: ['close'],
    setup(props) {
        const pages = ref([]);
        const isLoading = ref(false);
        const error = ref(null);
        const showDetails = ref(false);
        const activePage = ref(1);
        const scrollContainerRef = ref(null);

        // Staleness state
        const stalenessData = ref(null);      // full response from /staleness
        const reprocessingAll = ref(false);
        const reprocessingPages = ref({});    // pageId -> boolean

        const staleCount = computed(() => stalenessData.value?.staleCount ?? 0);

        // Map pageIndex (0-based) -> PageStalenessDTO
        const stalenessByIndex = computed(() => {
            if (!stalenessData.value) return {};
            const map = {};
            for (const p of stalenessData.value.pages) {
                map[p.pageIndex] = p;
            }
            return map;
        });

        function isPageStale(page) {
            const info = stalenessByIndex.value[page.pageNo - 1];
            return info ? info.isStale : false;
        }

        function pageId(page) {
            const info = stalenessByIndex.value[page.pageNo - 1];
            return info ? info.pageId : null;
        }

        const loadPages = async () => {
            if (!props.file) return;

            if (!props.file.name.endsWith('.note')) {
                error.value = "Preview not available for this file type.";
                return;
            }

            isLoading.value = true;
            error.value = null;
            pages.value = [];
            stalenessData.value = null;

            try {
                const result = await convertNoteToPng(props.file.id);
                if (result && result.length > 0) {
                    pages.value = result.sort((a, b) => a.pageNo - b.pageNo);
                } else {
                    error.value = "No pages found. The note might still be processing.";
                }
            } catch (e) {
                console.error(e);
                error.value = "Failed to load note preview.";
            } finally {
                isLoading.value = false;
            }

            // Load staleness in background
            loadStaleness();
        };

        async function loadStaleness() {
            try {
                const data = await fetchStaleness(props.file.id);
                stalenessData.value = data;
            } catch (e) {
                // Staleness is non-critical; fail silently
                console.warn('Staleness fetch failed:', e.message);
            }
        }

        async function handleReprocessAll() {
            reprocessingAll.value = true;
            try {
                await reprocessFile(props.file.id, null);
                // Poll: reload staleness after a delay
                setTimeout(loadStaleness, 3000);
            } catch (e) {
                console.error('Reprocess all failed:', e.message);
            } finally {
                reprocessingAll.value = false;
            }
        }

        async function handleReprocessPage(page) {
            const pid = pageId(page);
            if (!pid) return;
            reprocessingPages.value = { ...reprocessingPages.value, [pid]: true };
            try {
                await reprocessPage(props.file.id, pid);
                setTimeout(loadStaleness, 3000);
            } catch (e) {
                console.error('Reprocess page failed:', e.message);
            } finally {
                reprocessingPages.value = { ...reprocessingPages.value, [pid]: false };
            }
        }

        // IntersectionObserver: track which page is most visible in the scroll area
        let pageObserver = null;
        const pageVisibility = new Map(); // pageNo -> intersectionRatio

        function setupPageObserver() {
            if (pageObserver) { pageObserver.disconnect(); pageObserver = null; }
            if (!scrollContainerRef.value || !pages.value.length) return;

            pageObserver = new IntersectionObserver((records) => {
                for (const record of records) {
                    const pageNo = parseInt(record.target.dataset.pageNo);
                    pageVisibility.set(pageNo, record.intersectionRatio);
                }
                let best = activePage.value, bestRatio = -1;
                for (const [pageNo, ratio] of pageVisibility) {
                    if (ratio > bestRatio) { bestRatio = ratio; best = pageNo; }
                }
                if (bestRatio > 0) activePage.value = best;
            }, { root: scrollContainerRef.value, threshold: [0, 0.25, 0.5, 0.75, 1.0] });

            for (const page of pages.value) {
                const el = scrollContainerRef.value.querySelector(`[data-page-no="${page.pageNo}"]`);
                if (el) pageObserver.observe(el);
            }
        }

        watch(pages, async () => {
            pageVisibility.clear();
            await nextTick();
            setupPageObserver();
        }, { flush: 'post' });

        onUnmounted(() => { if (pageObserver) pageObserver.disconnect(); });

        onMounted(loadPages);
        watch(() => props.file, loadPages);

        return {
            pages,
            isLoading,
            error,
            showDetails,
            activePage,
            scrollContainerRef,
            stalenessData,
            staleCount,
            reprocessingAll,
            reprocessingPages,
            isPageStale,
            pageId,
            handleReprocessAll,
            handleReprocessPage,
        };
    },
    template: `
    <div class="bg-gray-50 dark:bg-gray-900 h-full flex flex-col overflow-hidden relative">
        <!-- Header (Fixed) -->
        <div class="flex-none bg-white dark:bg-gray-800 p-4 border-b border-gray-200 dark:border-gray-700 z-10 flex items-center justify-between px-8">
            <div class="flex items-center gap-3">
                <div class="bg-gray-100 dark:bg-gray-700 p-2 rounded border border-gray-200 dark:border-gray-600 text-black dark:text-white">
                    <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
                </div>
                <div>
                    <h2 class="text-lg font-bold text-black dark:text-white">{{ file.name }}</h2>
                    <p class="text-xs text-gray-500 dark:text-gray-400">
                        <span v-if="breadcrumbs.length > 0">{{ breadcrumbs.map(c => c.name).join(' / ') }} &middot; </span>{{ pages.length }} Pages
                    </p>
                </div>
            </div>
            <div class="flex items-center gap-2">
                <button v-if="staleCount > 0"
                    @click="handleReprocessAll"
                    :disabled="reprocessingAll"
                    class="p-2 text-amber-600 dark:text-amber-400 hover:bg-amber-50 dark:hover:bg-amber-900/30 disabled:opacity-50 rounded transition-colors border border-amber-300 dark:border-amber-600"
                    :title="staleCount + ' page' + (staleCount === 1 ? '' : 's') + ' processed with outdated prompts — click to reprocess'">
                    <svg v-if="reprocessingAll" class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                    <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg>
                </button>
                <button @click="showDetails = !showDetails"
                    :class="{'bg-black text-white border-black': showDetails, 'bg-white dark:bg-gray-600 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-500 border-gray-300 dark:border-gray-500': !showDetails}"
                    class="px-4 py-2 text-sm font-medium rounded transition-colors border flex items-center gap-2">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
                    Insights
                </button>
                <button @click="$emit('close')"
                    class="px-4 py-2 bg-white dark:bg-gray-600 border border-gray-300 dark:border-gray-500 rounded text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-500 transition-colors">
                    Close
                </button>
            </div>
        </div>

        <!-- Main Content Area -->
        <div class="flex-1 overflow-hidden relative flex">
            <!-- Pages (Scrollable) -->
            <div ref="scrollContainerRef" class="flex-1 overflow-y-auto p-4 sm:p-8 snap-y snap-proximity scroll-pt-6">
                <div class="max-w-4xl mx-auto">
                    <!-- Error State -->
                    <div v-if="error" class="bg-white dark:bg-gray-800 p-12 rounded border border-gray-200 dark:border-gray-700 text-center">
                        <div class="text-gray-400 mb-2">
                            <svg class="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                        </div>
                        <h3 class="text-lg font-medium text-black dark:text-white">Unable to load preview</h3>
                        <p class="text-gray-500 dark:text-gray-400 mt-1">{{ error }}</p>
                    </div>

                    <!-- Loading State -->
                    <div v-if="isLoading" class="flex flex-col items-center justify-center p-20 bg-white dark:bg-gray-800 rounded border border-gray-200 dark:border-gray-700">
                        <div class="animate-spin rounded-full h-10 w-10 border-b-2 border-black dark:border-white mb-4"></div>
                        <p class="text-gray-500 dark:text-gray-400">Converting note...</p>
                    </div>

                    <!-- Pages List -->
                    <div v-if="!isLoading && !error && pages.length > 0" class="space-y-6">
                        <div v-for="page in pages" :key="page.pageNo" :data-page-no="page.pageNo" class="bg-white dark:bg-gray-800 rounded border border-gray-200 dark:border-gray-700 overflow-hidden snap-start scroll-mt-6">
                            <div class="border-b border-gray-200 dark:border-gray-700 p-3 bg-gray-50 dark:bg-gray-700 flex justify-between items-center text-xs text-gray-400 font-mono">
                                <div class="flex items-center gap-2">
                                    <span>Page {{ page.pageNo }}</span>
                                    <span v-if="isPageStale(page)" class="bg-amber-100 dark:bg-amber-900/50 text-amber-700 dark:text-amber-300 px-2 py-0.5 rounded-full text-xs font-sans">stale</span>
                                </div>
                                <button
                                    v-if="isPageStale(page) && pageId(page)"
                                    @click="handleReprocessPage(page)"
                                    :disabled="reprocessingPages[pageId(page)]"
                                    class="px-2 py-1 text-xs font-medium font-sans bg-amber-600 hover:bg-amber-700 disabled:opacity-50 text-white rounded transition-colors flex items-center gap-1"
                                >
                                    <svg v-if="reprocessingPages[pageId(page)]" class="animate-spin w-3 h-3" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                                    {{ reprocessingPages[pageId(page)] ? 'Queuing…' : 'Reprocess' }}
                                </button>
                            </div>
                            <img :src="page.url" loading="lazy" class="w-full h-auto block" alt="Note Page" />
                        </div>
                    </div>
                </div>
            </div>

            <!-- Sidebar (Animated) -->
            <transition
                enter-active-class="transform transition ease-out duration-300"
                enter-from-class="translate-x-full"
                enter-to-class="translate-x-0"
                leave-active-class="transform transition ease-in duration-300"
                leave-from-class="translate-x-0"
                leave-to-class="translate-x-full"
            >
                <div v-show="showDetails" class="w-96 border-l border-gray-200 dark:border-gray-700 z-20 absolute right-0 top-0 bottom-0 bg-white dark:bg-gray-800 md:relative md:flex md:flex-col min-h-0">
                    <summary-panel :file-id="file.id" :active-page="activePage" @close="showDetails = false" @has-insights="showDetails = true"></summary-panel>
                </div>
            </transition>
        </div>
    </div>
    `
}
