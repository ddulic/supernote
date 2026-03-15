import { fetchSystemTasks, fetchCapacity } from '../api/client.js';

export default {
    name: 'SystemPanel',
    template: `
        <div class="fixed inset-0 bg-black/50 flex items-center justify-center z-50" @click.self="$emit('close')">
            <div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-300 dark:border-gray-700 shadow-xl w-fit max-w-[90vw] max-h-[75vh] flex flex-col overflow-hidden">
                <!-- Header -->
                <div class="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
                    <h2 class="text-xl font-bold text-black dark:text-white">System Status</h2>
                    <button @click="$emit('close')" class="text-gray-400 hover:text-black dark:hover:text-white">
                        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                        </svg>
                    </button>
                </div>

                <!-- Content -->
                <div class="flex-1 overflow-y-auto p-4 space-y-6">
                    <!-- Storage Quota -->
                    <div class="bg-gray-50 dark:bg-gray-700 p-4 rounded border border-gray-200 dark:border-gray-600">
                        <h3 class="text-lg font-medium text-black dark:text-white mb-2">Storage Usage</h3>
                        <div v-if="capacity" class="space-y-2">
                            <div class="flex justify-between text-sm text-gray-600 dark:text-gray-400">
                                <span>{{ formatSize(capacity.usedCapacity) }} used</span>
                                <span>{{ formatSize(capacity.totalCapacity) }} total</span>
                            </div>
                            <div class="w-full bg-gray-200 dark:bg-gray-600 rounded-full h-2.5">
                                <div class="bg-black dark:bg-white h-2.5 rounded-full transition-all duration-500" :style="{ width: usagePercent + '%' }"></div>
                            </div>
                        </div>
                        <div v-else class="animate-pulse bg-gray-200 dark:bg-gray-600 h-10 rounded"></div>
                    </div>

                    <!-- Tasks -->
                    <div>
                        <div class="flex items-center justify-between mb-4">
                            <h3 class="text-lg font-medium text-black dark:text-white">Processing Queue</h3>
                            <div class="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                                <label class="text-xs">Rows per page:</label>
                                <select v-model="pageSize" @change="currentPage = 1" class="text-xs border border-gray-300 dark:border-gray-600 rounded px-1 py-0.5 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300">
                                    <option v-for="n in [10, 25, 50, 100]" :key="n" :value="n">{{ n }}</option>
                                </select>
                            </div>
                        </div>
                        <div v-if="loading" class="flex justify-center p-8">
                            <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-black dark:border-white"></div>
                        </div>

                        <div v-else-if="error" class="p-4 bg-gray-100 dark:bg-gray-700 text-black dark:text-white border border-gray-300 dark:border-gray-600 rounded">
                            {{ error }}
                        </div>

                        <div v-else class="overflow-x-auto border border-gray-200 dark:border-gray-700 rounded">
                            <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                                <thead class="bg-gray-50 dark:bg-gray-700">
                                    <tr>
                                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">File ID</th>
                                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Type</th>
                                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Key</th>
                                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Status</th>
                                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Retries</th>
                                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Updated</th>
                                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Details</th>
                                    </tr>
                                </thead>
                                <tbody class="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                                    <tr v-for="task in paginatedTasks" :key="task.id">
                                        <td class="px-6 py-4 whitespace-nowrap text-sm text-black dark:text-white">{{ task.fileId }}</td>
                                        <td class="px-6 py-4 whitespace-nowrap text-sm text-black dark:text-white">{{ task.taskType }}</td>
                                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">{{ task.key }}</td>
                                        <td class="px-6 py-4 whitespace-nowrap">
                                            <span :class="statusClass(task.status)" class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full">
                                                {{ task.status }}
                                            </span>
                                        </td>
                                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">{{ task.retryCount }}</td>
                                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">{{ formatDate(task.updateTime) }}</td>
                                        <td class="px-6 py-4 text-sm text-gray-500 dark:text-gray-400 max-w-xs truncate" :title="task.lastError">
                                            {{ task.lastError }}
                                        </td>
                                    </tr>
                                    <tr v-if="tasks.length === 0">
                                        <td colspan="7" class="px-6 py-4 text-center text-sm text-gray-500 dark:text-gray-400">No active tasks</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                        <div v-if="totalPages > 1" class="flex items-center justify-end mt-3 text-sm text-gray-600 dark:text-gray-400">
                            <div class="flex items-center gap-2">
                                <span>Page {{ currentPage }} of {{ totalPages }}</span>
                                <div class="flex gap-1">
                                    <button @click="currentPage = 1" :disabled="currentPage === 1" class="px-2 py-1 rounded border border-gray-300 dark:border-gray-600 disabled:opacity-40 hover:bg-gray-100 dark:hover:bg-gray-700">&laquo;</button>
                                    <button @click="currentPage--" :disabled="currentPage === 1" class="px-2 py-1 rounded border border-gray-300 dark:border-gray-600 disabled:opacity-40 hover:bg-gray-100 dark:hover:bg-gray-700">&lsaquo;</button>
                                    <button @click="currentPage++" :disabled="currentPage === totalPages" class="px-2 py-1 rounded border border-gray-300 dark:border-gray-600 disabled:opacity-40 hover:bg-gray-100 dark:hover:bg-gray-700">&rsaquo;</button>
                                    <button @click="currentPage = totalPages" :disabled="currentPage === totalPages" class="px-2 py-1 rounded border border-gray-300 dark:border-gray-600 disabled:opacity-40 hover:bg-gray-100 dark:hover:bg-gray-700">&raquo;</button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Footer -->
                <div class="p-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-700 flex justify-end">
                    <button @click="loadData" class="mr-2 px-4 py-2 bg-white dark:bg-gray-600 border border-gray-300 dark:border-gray-500 rounded text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-500 transition-colors">
                        Refresh
                    </button>
                    <button @click="$emit('close')" class="px-4 py-2 bg-black border border-black rounded text-sm font-medium text-white hover:bg-gray-800 transition-colors">
                        Close
                    </button>
                </div>
            </div>
        </div>
    `,
    data() {
        return {
            loading: true,
            error: null,
            tasks: [],
            capacity: null,
            currentPage: 1,
            pageSize: 10
        }
    },
    computed: {
        usagePercent() {
            if (!this.capacity || this.capacity.totalCapacity === 0) return 0;
            return Math.min(100, (this.capacity.usedCapacity / this.capacity.totalCapacity) * 100);
        },
        totalPages() {
            return Math.max(1, Math.ceil(this.tasks.length / this.pageSize));
        },
        paginatedTasks() {
            const start = (this.currentPage - 1) * this.pageSize;
            return this.tasks.slice(start, start + this.pageSize);
        }
    },
    async mounted() {
        await this.loadData();
    },
    methods: {
        async loadData() {
            this.loading = true;
            this.error = null;
            this.currentPage = 1;
            try {
                const [tasksResult, capacityResult] = await Promise.all([
                    fetchSystemTasks(),
                    fetchCapacity()
                ]);

                if (tasksResult.success) {
                    this.tasks = tasksResult.tasks;
                } else {
                    this.error = "Failed to load tasks";
                }

                // Capacity result is the VO directly, typically
                this.capacity = capacityResult;
            } catch (e) {
                this.error = e.message;
            } finally {
                this.loading = false;
            }
        },
        statusClass(status) {
            const classes = {
                'PENDING': 'bg-gray-100 text-gray-700 border border-gray-300',
                'PROCESSING': 'bg-gray-200 text-black border border-gray-400',
                'COMPLETED': 'bg-black text-white',
                'FAILED': 'bg-gray-800 text-white'
            };
            return classes[status] || 'bg-gray-100 text-gray-700';
        },
        formatDate(timestamp) {
            if (!timestamp) return '-';
            return new Date(timestamp).toLocaleString();
        },
        formatSize(bytes) {
            if (!bytes) return '0 B';
            const k = 1024;
            const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }
    }
}
