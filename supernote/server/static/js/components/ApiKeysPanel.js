import { fetchApiKeys, createApiKey, deleteApiKey, fetchOAuthSessions, deleteOAuthSession } from '../api/client.js';
import { useToast } from '../composables/useToast.js';

const { addToast } = useToast();

export default {
    name: 'ApiKeysPanel',
    template: `
        <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4" @click.self="$emit('close')">
            <div class="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-fit min-w-[min(36rem,100%)] max-w-full max-h-[90vh] flex flex-col">
                <!-- Header -->
                <div class="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
                    <div>
                        <h2 class="text-xl font-bold text-gray-800 dark:text-white">MCP Credentials</h2>
                        <p class="text-sm text-gray-500 dark:text-gray-400 mt-0.5">Manage API keys and session tokens for MCP client access.</p>
                    </div>
                    <button @click="$emit('close')" class="text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-white">
                        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                        </svg>
                    </button>
                </div>

                <!-- Content -->
                <div class="flex-1 overflow-y-auto p-4 space-y-6">
                    <!-- New key reveal -->
                    <div v-if="newKey" class="bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-700 rounded-lg p-4">
                        <p class="text-sm font-semibold text-green-800 dark:text-green-300 mb-2">Key created — copy it now. It will not be shown again.</p>
                        <div class="flex items-center gap-2">
                            <code class="flex-1 bg-white dark:bg-gray-700 border border-green-300 dark:border-green-600 rounded px-3 py-2 text-sm font-mono text-green-900 dark:text-green-300 break-all select-all">{{ newKey }}</code>
                            <button @click="copyKey" class="shrink-0 px-3 py-2 bg-green-600 hover:bg-green-700 text-white text-sm rounded font-medium transition-colors">
                                {{ copied ? 'Copied!' : 'Copy' }}
                            </button>
                        </div>
                    </div>

                    <!-- Create form -->
                    <div class="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                        <h3 class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Create New Key</h3>
                        <div class="flex gap-2">
                            <input
                                v-model="newKeyName"
                                type="text"
                                placeholder="Key name (e.g. Claude Desktop)"
                                class="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-600 text-black dark:text-white placeholder-gray-400 dark:placeholder-gray-400 rounded text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                                @keyup.enter="handleCreate"
                                :disabled="creating"
                            />
                            <button
                                @click="handleCreate"
                                :disabled="!newKeyName.trim() || creating"
                                class="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm rounded font-medium transition-colors"
                            >
                                {{ creating ? 'Creating…' : 'Create' }}
                            </button>
                        </div>
                        <p v-if="createError" class="mt-2 text-sm text-red-600 dark:text-red-400">{{ createError }}</p>
                    </div>

                    <!-- Key list -->
                    <div>
                        <h3 class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Existing Keys</h3>
                        <div v-if="loading" class="flex justify-center p-8">
                            <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
                        </div>
                        <div v-else-if="keys.length === 0" class="text-sm text-gray-500 dark:text-gray-400 text-center py-6">
                            No API keys yet.
                        </div>
                        <div v-else class="divide-y divide-gray-200 dark:divide-gray-700 border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
                            <div v-for="key in keys" :key="key.id" class="flex items-center justify-between px-4 py-3 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700">
                                <div class="min-w-0">
                                    <p class="text-sm font-medium text-gray-900 dark:text-white truncate">{{ key.name }}</p>
                                    <p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                                        Created {{ formatDate(key.created_at * 1000) }}
                                        <span class="mx-1">·</span>
                                        {{ key.last_used_at ? 'Last used ' + formatDate(key.last_used_at * 1000) : 'Never used' }}
                                    </p>
                                </div>
                                <button
                                    @click="handleDelete(key)"
                                    :disabled="deletingId === key.id"
                                    class="ml-4 shrink-0 px-3 py-1.5 text-xs font-medium text-red-600 dark:text-red-400 border border-red-200 dark:border-red-700 bg-red-50 dark:bg-red-900/20 hover:bg-red-100 dark:hover:bg-red-900/40 rounded transition-colors disabled:opacity-50"
                                >
                                    {{ deletingId === key.id ? 'Revoking…' : 'Revoke' }}
                                </button>
                            </div>
                        </div>
                    </div>

                    <!-- Connected OAuth Sessions -->
                    <div>
                        <h3 class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1">Connected Sessions</h3>
                        <p class="text-xs text-gray-500 dark:text-gray-400 mb-3">OAuth clients connected via the browser login flow (e.g. claude.ai). Disconnecting revokes the refresh token — the client will need to re-authenticate.</p>
                        <div v-if="sessionsLoading" class="flex justify-center p-8">
                            <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
                        </div>
                        <div v-else-if="sessions.length === 0" class="text-sm text-gray-500 dark:text-gray-400 text-center py-6">
                            No active sessions.
                        </div>
                        <div v-else class="divide-y divide-gray-200 dark:divide-gray-700 border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
                            <div v-for="session in sessions" :key="session.id" class="flex items-center justify-between px-4 py-3 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700">
                                <div class="min-w-0">
                                    <p class="text-sm font-medium text-gray-900 dark:text-white truncate">{{ session.client_name }}</p>
                                    <p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                                        Connected {{ formatDate(session.created_at * 1000) }}
                                        <span class="mx-1">·</span>
                                        Expires {{ formatDate(session.expires_at * 1000) }}
                                    </p>
                                </div>
                                <button
                                    @click="handleDisconnect(session)"
                                    :disabled="disconnectingId === session.id"
                                    class="ml-4 shrink-0 px-3 py-1.5 text-xs font-medium text-red-600 dark:text-red-400 border border-red-200 dark:border-red-700 bg-red-50 dark:bg-red-900/20 hover:bg-red-100 dark:hover:bg-red-900/40 rounded transition-colors disabled:opacity-50"
                                >
                                    {{ disconnectingId === session.id ? 'Disconnecting…' : 'Disconnect' }}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Footer -->
                <div class="p-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-700 flex justify-end">
                    <button @click="$emit('close')" class="px-4 py-2 bg-indigo-600 border border-transparent rounded shadow-sm text-sm font-medium text-white hover:bg-indigo-700">
                        Close
                    </button>
                </div>
            </div>
        </div>
    `,
    data() {
        return {
            loading: true,
            keys: [],
            newKeyName: '',
            creating: false,
            createError: null,
            newKey: null,
            copied: false,
            deletingId: null,
            sessions: [],
            sessionsLoading: true,
            disconnectingId: null,
        };
    },
    async mounted() {
        await Promise.all([this.loadKeys(), this.loadSessions()]);
    },
    methods: {
        async loadKeys() {
            this.loading = true;
            try {
                const data = await fetchApiKeys();
                this.keys = data.keys || [];
            } catch (e) {
                console.error('Failed to load API keys:', e);
            } finally {
                this.loading = false;
            }
        },
        async loadSessions() {
            this.sessionsLoading = true;
            try {
                const data = await fetchOAuthSessions();
                this.sessions = data.sessions || [];
            } catch (e) {
                console.error('Failed to load OAuth sessions:', e);
            } finally {
                this.sessionsLoading = false;
            }
        },
        async handleCreate() {
            const name = this.newKeyName.trim();
            if (!name) return;
            this.creating = true;
            this.createError = null;
            this.newKey = null;
            try {
                const data = await createApiKey(name);
                this.newKey = data.key;
                this.newKeyName = '';
                await this.loadKeys();
            } catch (e) {
                this.createError = e.message;
            } finally {
                this.creating = false;
            }
        },
        async handleDelete(key) {
            if (!confirm(`Revoke key "${key.name}"? Any clients using it will immediately lose access.`)) return;
            this.deletingId = key.id;
            try {
                await deleteApiKey(key.id);
                this.keys = this.keys.filter(k => k.id !== key.id);
                if (this.newKey) this.newKey = null;
            } catch (e) {
                addToast('Failed to revoke key', e.message);
            } finally {
                this.deletingId = null;
            }
        },
        async handleDisconnect(session) {
            if (!confirm(`Disconnect "${session.client_name}"? It will need to re-authenticate.`)) return;
            this.disconnectingId = session.id;
            try {
                await deleteOAuthSession(session.id);
                this.sessions = this.sessions.filter(s => s.id !== session.id);
            } catch (e) {
                addToast('Failed to disconnect session', e.message);
            } finally {
                this.disconnectingId = null;
            }
        },
        async copyKey() {
            try {
                await navigator.clipboard.writeText(this.newKey);
                this.copied = true;
                setTimeout(() => { this.copied = false; }, 2000);
            } catch (e) {
                addToast('Copy failed', 'Please select and copy manually.');
            }
        },
        formatDate(ms) {
            if (!ms) return '—';
            return new Date(ms).toLocaleString();
        }
    }
};
