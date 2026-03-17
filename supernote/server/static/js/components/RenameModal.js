export default {
    name: 'RenameModal',
    props: ['item'],
    template: `
        <div class="fixed inset-0 z-[110] flex items-center justify-center p-4 bg-black/50" @click.self="$emit('close')">
            <div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-300 dark:border-gray-700 shadow-xl w-full max-w-md p-6">
                <h3 class="text-lg font-bold text-black dark:text-white mb-4">Rename {{ item.isDirectory ? 'Folder' : 'File' }}</h3>
                <input v-model="newName" type="text" placeholder="New name"
                    class="w-full px-4 py-3 bg-white dark:bg-gray-700 dark:text-white dark:placeholder-gray-400 border border-gray-300 dark:border-gray-600 rounded focus:ring-2 focus:ring-black dark:focus:ring-white focus:border-black dark:focus:border-white outline-none transition-all mb-6"
                    @keyup.enter="handleRename" ref="nameInput">
                <div class="flex justify-end gap-3">
                    <button @click="$emit('close')" class="px-4 py-2 bg-white dark:bg-gray-600 border border-gray-300 dark:border-gray-500 rounded text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-500 transition-colors">Cancel</button>
                    <button @click="handleRename" :disabled="!newName || newName === item.name"
                        class="px-6 py-2 bg-black border border-black rounded text-sm font-medium text-white hover:bg-gray-800 disabled:opacity-50 transition-colors">
                        Rename
                    </button>
                </div>
            </div>
        </div>
    `,
    data() {
        return {
            newName: this.item.name
        }
    },
    mounted() {
        this.$nextTick(() => {
            this.$refs.nameInput.focus();
            this.$refs.nameInput.select();
        });
    },
    methods: {
        handleRename() {
            if (this.newName && this.newName !== this.item.name) {
                this.$emit('confirm', this.newName);
            }
        }
    }
}
