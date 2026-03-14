import { fetchApiKeys, createApiKey, deleteApiKey, fetchOAuthSessions, deleteOAuthSession } from '../api/client.js';

export default {
    name: 'ApiKeysPanel',
    template: `
        <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" @click.self="$emit('close')">
            <div class="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] flex flex-col">
                <!-- Header -->
                <div class="flex items-center justify-between p-4 border-b">
                    <div>
                        <h2 class="text-xl font-bold text-gray-800">MCP API Keys</h2>
                        <p class="text-sm text-gray-500 mt-0.5">Use these keys to authenticate MCP clients without the OAuth flow.</p>
                    </div>
                    <button @click="$emit('close')" class="text-gray-500 hover:text-gray-700">
                        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                        </svg>
                    </button>
                </div>

                <!-- Content -->
                <div class="flex-1 overflow-y-auto p-4 space-y-6">
                    <!-- New key reveal -->
                    <div v-if="newKey" class="bg-green-50 border border-green-200 rounded-lg p-4">
                        <p class="text-sm font-semibold text-green-800 mb-2">Key created — copy it now. It will not be shown again.</p>
                        <div class="flex items-center gap-2">
                            <code class="flex-1 bg-white border border-green-300 rounded px-3 py-2 text-sm font-mono text-green-900 break-all select-all">{{ newKey }}</code>
                            <button @click="copyKey" class="shrink-0 px-3 py-2 bg-green-600 hover:bg-green-700 text-white text-sm rounded font-medium transition-colors">
                                {{ copied ? 'Copied!' : 'Copy' }}
                            </button>
                        </div>
                    </div>

                    <!-- Create form -->
                    <div class="bg-gray-50 rounded-lg p-4">
                        <h3 class="text-sm font-semibold text-gray-700 mb-3">Create New Key</h3>
                        <div class="flex gap-2">
                            <input
                                v-model="newKeyName"
                                type="text"
                                placeholder="Key name (e.g. Claude Desktop)"
                                class="flex-1 px-3 py-2 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
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
                        <p v-if="createError" class="mt-2 text-sm text-red-600">{{ createError }}</p>
                    </div>

                    <!-- Key list -->
                    <div>
                        <h3 class="text-sm font-semibold text-gray-700 mb-3">Existing Keys</h3>
                        <div v-if="loading" class="flex justify-center p-8">
                            <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
                        </div>
                        <div v-else-if="keys.length === 0" class="text-sm text-gray-500 text-center py-6">
                            No API keys yet.
                        </div>
                        <div v-else class="divide-y border rounded-lg overflow-hidden">
                            <div v-for="key in keys" :key="key.id" class="flex items-center justify-between px-4 py-3 bg-white hover:bg-gray-50">
                                <div class="min-w-0">
                                    <p class="text-sm font-medium text-gray-900 truncate">{{ key.name }}</p>
                                    <p class="text-xs text-gray-500 mt-0.5">
                                        Created {{ formatDate(key.created_at * 1000) }}
                                        <span class="mx-1">·</span>
                                        {{ key.last_used_at ? 'Last used ' + formatDate(key.last_used_at * 1000) : 'Never used' }}
                                    </p>
                                </div>
                                <button
                                    @click="handleDelete(key)"
                                    :disabled="deletingId === key.id"
                                    class="ml-4 shrink-0 px-3 py-1.5 text-xs font-medium text-red-600 border border-red-200 bg-red-50 hover:bg-red-100 rounded transition-colors disabled:opacity-50"
                                >
                                    {{ deletingId === key.id ? 'Revoking…' : 'Revoke' }}
                                </button>
                            </div>
                        </div>
                    </div>

                    <!-- Connected OAuth Sessions -->
                    <div>
                        <h3 class="text-sm font-semibold text-gray-700 mb-1">Connected Sessions</h3>
                        <p class="text-xs text-gray-500 mb-3">OAuth clients connected via the browser login flow (e.g. claude.ai). Disconnecting revokes the refresh token — the client will need to re-authenticate.</p>
                        <div v-if="sessionsLoading" class="flex justify-center p-8">
                            <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
                        </div>
                        <div v-else-if="sessions.length === 0" class="text-sm text-gray-500 text-center py-6">
                            No active sessions.
                        </div>
                        <div v-else class="divide-y border rounded-lg overflow-hidden">
                            <div v-for="session in sessions" :key="session.id" class="flex items-center justify-between px-4 py-3 bg-white hover:bg-gray-50">
                                <div class="min-w-0">
                                    <p class="text-sm font-medium text-gray-900 truncate">{{ session.client_name }}</p>
                                    <p class="text-xs text-gray-500 mt-0.5">
                                        Connected {{ formatDate(session.created_at * 1000) }}
                                        <span class="mx-1">·</span>
                                        Expires {{ formatDate(session.expires_at * 1000) }}
                                    </p>
                                </div>
                                <button
                                    @click="handleDisconnect(session)"
                                    :disabled="disconnectingId === session.id"
                                    class="ml-4 shrink-0 px-3 py-1.5 text-xs font-medium text-red-600 border border-red-200 bg-red-50 hover:bg-red-100 rounded transition-colors disabled:opacity-50"
                                >
                                    {{ disconnectingId === session.id ? 'Disconnecting…' : 'Disconnect' }}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Footer -->
                <div class="p-4 border-t bg-gray-50 flex justify-end">
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
                alert('Failed to revoke key: ' + e.message);
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
                alert('Failed to disconnect session: ' + e.message);
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
                alert('Copy failed — please select and copy manually.');
            }
        },
        formatDate(ms) {
            if (!ms) return '—';
            return new Date(ms).toLocaleString();
        }
    }
};
