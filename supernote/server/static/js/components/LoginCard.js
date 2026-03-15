import { ref } from 'vue';

export default {
    emits: ['login'],
    setup(props, { emit }) {
        const email = ref('');
        const password = ref('');
        const isLoading = ref(false);

        const handleSubmit = async () => {
            if (!email.value || !password.value) return;
            isLoading.value = true;
            try {
                await emit('login', { email: email.value, password: password.value });
            } finally {
                isLoading.value = false;
            }
        };

        return {
            email,
            password,
            isLoading,
            handleSubmit
        };
    },
    template: `
    <div class="max-w-md mx-auto bg-white dark:bg-gray-800 rounded-lg border border-gray-300 dark:border-gray-700 shadow-lg overflow-hidden mt-20">
        <div class="p-8 sm:p-12">
            <div class="text-center mb-8">
                <div class="w-16 h-16 bg-black rounded-lg flex items-center justify-center text-white text-2xl font-bold mx-auto mb-4">S</div>
                <h2 class="text-2xl font-bold text-black dark:text-white">Welcome Back</h2>
                <p class="text-gray-500 dark:text-gray-400 mt-2">Sign in to access your Supernote Cloud</p>
            </div>

            <form @submit.prevent="handleSubmit" class="space-y-6">
                <div>
                    <label class="block text-sm font-medium text-black dark:text-white mb-2">Email Address</label>
                    <input type="email" v-model="email" required
                        class="w-full px-4 py-3 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-black dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:border-black dark:focus:border-white focus:ring-2 focus:ring-gray-200 dark:focus:ring-gray-600 outline-none transition-all"
                        placeholder="you@example.com">
                </div>

                <div>
                    <label class="block text-sm font-medium text-black dark:text-white mb-2">Password</label>
                    <input type="password" v-model="password" required
                        class="w-full px-4 py-3 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-black dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:border-black dark:focus:border-white focus:ring-2 focus:ring-gray-200 dark:focus:ring-gray-600 outline-none transition-all"
                        placeholder="••••••••">
                </div>

                <button type="submit"
                    :disabled="isLoading"
                    class="w-full bg-black hover:bg-gray-800 text-white font-medium py-3 px-4 rounded transition-all disabled:opacity-50 disabled:cursor-not-allowed flex justify-center items-center">
                    <span v-if="isLoading" class="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></span>
                    {{ isLoading ? 'Signing in...' : 'Sign In' }}
                </button>
            </form>
        </div>
        <div class="bg-gray-50 dark:bg-gray-700 p-4 text-center text-xs text-gray-400 border-t border-gray-200 dark:border-gray-600">
            Supernote Private Cloud Server
        </div>
    </div>
    `
}
