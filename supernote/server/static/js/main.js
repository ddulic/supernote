import { createApp, ref, onMounted, computed } from 'https://unpkg.com/vue@3/dist/vue.esm-browser.js';
import { useFileSystem } from './composables/useFileSystem.js';
import { useToast } from './composables/useToast.js';
import { setToken, getToken, login, logout, fetchProcessingStatus } from './api/client.js';
import FileCard from './components/FileCard.js';
import LoginCard from './components/LoginCard.js';
import FileViewer from './components/FileViewer.js';
import SystemPanel from './components/SystemPanel.js';
import ApiKeysPanel from './components/ApiKeysPanel.js';
import MoveModal from './components/MoveModal.js';
import RenameModal from './components/RenameModal.js';
import ToastContainer from './components/ToastContainer.js';

createApp({
    components: {
        FileCard,
        LoginCard,
        FileViewer,
        SystemPanel,
        ApiKeysPanel,
        MoveModal,
        RenameModal,
        ToastContainer
    },
    setup() {
        // Toast
        const { addToast } = useToast();

        // Theme
        const isDarkMode = ref(localStorage.getItem('theme') === 'dark');
        function applyTheme(dark) {
            document.documentElement.classList.toggle('dark', dark);
        }
        function toggleTheme() {
            isDarkMode.value = !isDarkMode.value;
            localStorage.setItem('theme', isDarkMode.value ? 'dark' : 'light');
            applyTheme(isDarkMode.value);
        }
        applyTheme(isDarkMode.value);

        // Auth State — initialize synchronously to avoid flashing the login form
        const isLoggedIn = ref(!!getToken());
        const loginError = ref(null);
        const showSystemPanel = ref(false);
        const showApiKeysPanel = ref(false);

        // UI State
        const showNewFolderModal = ref(false);
        const newFolderName = ref('');
        const showMoveModal = ref(false);
        const showRenameModal = ref(false);
        const itemToRename = ref(null);
        const selectedIds = ref([]);
        const processingStatuses = ref({}); // fileId -> status string

        // File System
        const {
            files,
            currentDirectoryId,
            isLoading,
            error,
            loadDirectory,
            createNewFolder,
            deleteSelectedItems,
            moveSelectedItems,
            uploadFiles,
            renameSelectedItem
        } = useFileSystem();

        const view = ref('grid');
        const selectedFile = ref(null);
        const breadcrumbs = ref([{ id: "0", name: "Cloud" }]);

        function saveNavToUrl() {
            const segments = breadcrumbs.value.slice(1).map(c => encodeURIComponent(c.name));
            if (view.value === 'viewer' && selectedFile.value) {
                segments.push(encodeURIComponent(selectedFile.value.name));
            }
            const path = segments.length > 0 ? '/' + segments.join('/') : '/';
            history.replaceState(null, '', path);
        }
        async function restoreNavFromUrl() {
            const segments = window.location.pathname.slice(1).split('/').filter(Boolean).map(decodeURIComponent);
            if (segments.length === 0) return false;

            let currentId = "0";
            const crumbs = [{ id: "0", name: "Cloud" }];

            for (const segment of segments) {
                await loadDirectory(currentId);
                const match = files.value.find(f => f.name === segment);
                if (!match) break;
                if (match.isDirectory) {
                    currentId = match.id;
                    crumbs.push({ id: match.id, name: match.name });
                } else {
                    breadcrumbs.value = crumbs;
                    currentDirectoryId.value = currentId;
                    selectedFile.value = match;
                    view.value = 'viewer';
                    return true;
                }
            }

            breadcrumbs.value = crumbs;
            currentDirectoryId.value = currentId;
            await loadDirectory(currentId);
            return true;
        }

        const folders = computed(() => files.value.filter(f => f.isDirectory));
        const regularFiles = computed(() => files.value.filter(f => !f.isDirectory));

        // Methods
        async function openItem(item) {
            if (item.isDirectory) {
                currentDirectoryId.value = item.id;
                breadcrumbs.value.push({ id: item.id, name: item.name });
                saveNavToUrl();
                selectedIds.value = [];
                await loadDirectory(item.id);
            } else {
                selectedFile.value = item;
                view.value = 'viewer';
                saveNavToUrl();
            }
        }

        async function navigateTo(index) {
            const crumbs = breadcrumbs.value.slice(0, index + 1);
            breadcrumbs.value = crumbs;
            view.value = 'grid';
            selectedFile.value = null;
            selectedIds.value = [];
            saveNavToUrl();
            const target = crumbs[crumbs.length - 1];
            await loadDirectory(target.id);
        }

        function closeViewer() {
            view.value = 'grid';
            selectedFile.value = null;
            saveNavToUrl();
        }

        // Selection
        function toggleSelection(id) {
            const index = selectedIds.value.indexOf(id);
            if (index > -1) {
                selectedIds.value.splice(index, 1);
            } else {
                selectedIds.value.push(id);
            }
        }

        // Actions
        async function handleCreateFolder() {
            if (!newFolderName.value) return;
            try {
                await createNewFolder(newFolderName.value);
                showNewFolderModal.value = false;
                newFolderName.value = '';
            } catch (e) {
                addToast('Failed to create folder', e.message);
            }
        }

        const fileInput = ref(null);
        function triggerUpload() {
            fileInput.value.click();
        }

        async function handleFileUpload(event) {
            const selectedFiles = event.target.files;
            if (selectedFiles.length === 0) return;
            try {
                await uploadFiles(selectedFiles);
            } catch (e) {
                addToast('Upload failed', e.message);
            } finally {
                event.target.value = ''; // Reset input
            }
        }

        async function handleDeleteSelected() {
            if (!confirm(`Are you sure you want to delete ${selectedIds.value.length} items?`)) return;
            try {
                await deleteSelectedItems(selectedIds.value);
                selectedIds.value = [];
            } catch (e) {
                addToast('Delete failed', e.message);
            }
        }

        function handleMoveSelected() {
            showMoveModal.value = true;
        }

        async function onConfirmMove(targetDirId) {
            try {
                await moveSelectedItems(selectedIds.value, targetDirId);
                selectedIds.value = [];
                showMoveModal.value = false;
            } catch (e) {
                addToast('Move failed', e.message);
            }
        }

        function triggerRename(item) {
            itemToRename.value = item;
            showRenameModal.value = true;
        }

        async function onConfirmRename(newName) {
            try {
                await renameSelectedItem(itemToRename.value.id, newName);
                showRenameModal.value = false;
                itemToRename.value = null;
            } catch (e) {
                addToast('Rename failed', e.message);
            }
        }

        async function resumeSession() {
            const token = getToken();
            if (!token) {
                return false;
            }

            const params = new URLSearchParams(window.location.hash.split('?')[1]);
            const returnTo = params.get('return_to');

            // Handle OAuth Bridge exchange strictly
            if (returnTo?.includes('/login-bridge')) {
                try {
                    const resp = await fetch(returnTo, {
                        method: 'POST',
                        headers: { 'x-access-token': token, 'Accept': 'application/json' }
                    });
                    const data = resp.ok ? await resp.json() : null;
                    if (data?.redirect_url) {
                        window.location.href = data.redirect_url;
                        return true;
                    }
                } catch (e) {
                    console.error("Bridge exchange failed", e);
                }
            }

            // Normal app session
            isLoggedIn.value = true;
            if (!await restoreNavFromUrl()) {
                await loadDirectory();
            }
            return true;
        }

        async function handleLogin({ email, password }) {
            loginError.value = null;
            try {
                await login(email, password);
                await resumeSession();
            } catch (e) {
                loginError.value = e.message;
                addToast('Login failed', e.message);
            }
        }

        function handleLogout() {
            logout();
        }

        onMounted(async () => {
            await resumeSession();

            // Polling for processing status
            setInterval(async () => {
                if (!isLoggedIn.value || isLoading.value || files.value.length === 0) return;

                const noteFileIds = files.value
                    .filter(f => f.extension === 'note')
                    .map(f => parseInt(f.id));

                if (noteFileIds.length === 0) return;

                try {
                    const result = await fetchProcessingStatus(noteFileIds);
                    if (result.success) {
                        processingStatuses.value = {
                            ...processingStatuses.value,
                            ...result.statusMap
                        };
                    }
                } catch (e) {
                    console.error("Failed to poll status:", e);
                }
            }, 3000); // Every 3 seconds
        });

        return {
            isDarkMode,
            toggleTheme,
            isLoggedIn,
            handleLogin,
            handleLogout,
            view,
            files,
            folders,
            regularFiles,
            currentDirectoryId,
            isLoading,
            error,
            breadcrumbs,
            openItem,
            navigateTo,
            closeViewer,
            selectedFile,
            showSystemPanel,
            showApiKeysPanel,

            // New States
            showNewFolderModal,
            newFolderName,
            showMoveModal,
            showRenameModal,
            itemToRename,
            selectedIds,
            fileInput,

            // New Methods
            toggleSelection,
            handleCreateFolder,
            triggerUpload,
            handleFileUpload,
            handleDeleteSelected,
            handleMoveSelected,
            onConfirmMove,
            triggerRename,
            onConfirmRename,
            processingStatuses
        };
    }
}).mount('#app');
