/**
 * API Client for Supernote Backend
 */

let authToken = localStorage.getItem('supernote_token');

export function setToken(token) {
    authToken = token;
    localStorage.setItem('supernote_token', token);
}

export function getToken() {
    return authToken;
}

export function logout() {
    authToken = null;
    localStorage.removeItem('supernote_token');
    window.location.reload();
}

/**
 * Secure Login Flow
 */
export async function login(email, password) {
    // 1. Wakeup / Get Token (Using query/token endpoint as a pre-check/wakeup)
    // This step in the CLI client ensures a clean session/CSRF token if needed,
    // although for the Web API we primarily rely on the random code flow.
    await fetch('/api/user/query/token', { method: 'POST', body: '{}' });

    // 2. Get Random Code (Challenge)
    const randomCodeResp = await fetch('/api/official/user/query/random/code', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ account: email })
    });

    if (!randomCodeResp.ok) throw new Error("Failed to get login challenge");
    const { randomCode, timestamp } = await randomCodeResp.json();

    // 3. Hash Password
    // Schema: SHA256(MD5(password) + randomCode)

    // Step 3a: MD5(password)
    // Using SparkMD5 global from CDN
    const md5Password = SparkMD5.hash(password);

    // Step 3b: SHA256(md5Password + randomCode)
    const contentToHash = md5Password + randomCode;
    const sha256Hash = await sha256(contentToHash);

    // 4. Authenticate
    const loginResp = await fetch('/api/official/user/account/login/new', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            account: email,
            password: sha256Hash,
            timestamp: timestamp,
            loginMethod: "2", // Email
            equipment: 1 // WEB
        })
    });

    if (!loginResp.ok) {
        if (loginResp.status === 401) throw new Error("Invalid credentials");
        throw new Error("Login failed");
    }

    const loginData = await loginResp.json();
    setToken(loginData.token);
    return loginData;
}

// Helper: SHA-256 using Web Crypto API
async function sha256(message) {
    const msgBuffer = new TextEncoder().encode(message);
    const hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}

/**
 * Fetch files for a given directory.
 */
export async function fetchFiles(directoryId = "0", pageNo = 1, pageSize = 50) {
    const headers = {
        'Content-Type': 'application/json'
    };
    if (authToken) {
        headers['x-access-token'] = authToken;
    }

    const response = await fetch('/api/file/list/query', {
        method: 'POST',
        headers,
        body: JSON.stringify({
            directoryId: directoryId, // Pass as string/raw to preserve precision
            pageNo,
            pageSize,
            order: "filename",
            sequence: "asc"
        })
    });

    if (!response.ok) {
        if (response.status === 401) {
            // If the token is invalid, clear it
            if (authToken) {
                logout();
                throw new Error("Unauthorized");
            }
            throw new Error("Unauthorized");
        }
        throw new Error(`Failed to fetch files: ${response.status}`);
    }

    const data = await response.json();

    // Map backend VO to frontend interface
    return (data.userFileVOList || []).map(file => ({
        id: file.id,
        name: file.fileName,
        isDirectory: file.isFolder === "Y" || file.isFolder === true || file.isFolder === 1,
        size: file.size,
        updatedAt: file.updateTime,
        extension: file.isFolder === "Y" ? null : getExtension(file.fileName)
    }));
}

function getExtension(filename) {
    if (!filename) return null;
    const parts = filename.split('.');
    return parts.length > 1 ? parts.pop().toLowerCase() : null;
}

/**
 * Convert Note to PNG
 * @param {string} fileId
 * @returns {Promise<Array<{pageNo: number, url: string}>>}
 */
export async function convertNoteToPng(fileId) {
    // 1. Get Token
    const currentToken = getToken();
    if (!currentToken) throw new Error("Unauthorized");

    // 2. Call API
    const response = await fetch('/api/file/note/to/png', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'x-access-token': currentToken
        },
        body: JSON.stringify({ id: fileId }) // Pass as string to preserve 64-bit precision
    });

    if (!response.ok) {
        if (response.status === 401) {
            logout();
            throw new Error("Unauthorized");
        }
        throw new Error(`Conversion failed: ${response.status}`);
    }

    const data = await response.json();
    return data.pngPageVOList || [];
}

/**
 * Fetch summaries for a file
 * @param {string} fileId
 * @returns {Promise<Array<Object>>}
 */
export async function fetchSummaries(fileId) {
    const currentToken = getToken();
    if (!currentToken) throw new Error("Unauthorized");

    const response = await fetch('/api/extended/file/summary/list', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'x-access-token': currentToken
        },
        // Extension endpoint expects { fileId: ... }
        body: JSON.stringify({ fileId: fileId })
    });

    if (!response.ok) {
        if (response.status === 401) {
            logout();
            throw new Error("Unauthorized");
        }
        throw new Error(`Summary fetch failed: ${response.status}`);
    }

    const data = await response.json();
    return data.summaryDOList || [];
}

/**
 * Fetch system tasks (Extended API).
 * @returns {Promise<Object>} The system task list response.
 */
export async function fetchSystemTasks() {
    const currentToken = getToken();
    if (!currentToken) throw new Error("Unauthorized");

    const response = await fetch('/api/extended/system/tasks', {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'x-access-token': currentToken
        }
    });

    if (response.status === 401) {
        logout();
        throw new Error("Unauthorized");
    }

    if (!response.ok) {
        throw new Error(`Failed to fetch system tasks: ${response.status}`);
    }

    return await response.json();
}

/**
 * Fetch storage capacity/quota.
 * @returns {Promise<{usedCapacity: number, totalCapacity: number}>}
 */
export async function fetchCapacity() {
    const currentToken = getToken();
    if (!currentToken) throw new Error("Unauthorized");

    const response = await fetch('/api/file/capacity/query', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'x-access-token': currentToken
        },
        body: JSON.stringify({})
    });

    if (response.status === 401) {
        logout();
        throw new Error("Unauthorized");
    }

    if (!response.ok) {
        throw new Error(`Failed to fetch capacity: ${response.status}`);
    }

    return await response.json();
}

/**
 * Create a new folder.
 */
export async function createFolder(directoryId, folderName) {
    const currentToken = getToken();
    if (!currentToken) throw new Error("Unauthorized");

    const response = await fetch('/api/file/folder/add', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'x-access-token': currentToken
        },
        body: JSON.stringify({
            directoryId: directoryId,
            fileName: folderName
        })
    });

    if (!response.ok) {
        throw new Error(`Failed to create folder: ${response.status}`);
    }

    return await response.json();
}

/**
 * Delete items (files or folders).
 */
export async function deleteItems(directoryId, idList) {
    const currentToken = getToken();
    if (!currentToken) throw new Error("Unauthorized");

    const response = await fetch('/api/file/delete', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'x-access-token': currentToken
        },
        body: JSON.stringify({
            directoryId: directoryId,
            idList: idList
        })
    });

    if (!response.ok) {
        throw new Error(`Failed to delete items: ${response.status}`);
    }

    return await response.json();
}

/**
 * Move items to a new directory.
 */
export async function moveItems(idList, targetDirectoryId) {
    const currentToken = getToken();
    if (!currentToken) throw new Error("Unauthorized");

    const response = await fetch('/api/file/move', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'x-access-token': currentToken
        },
        body: JSON.stringify({
            idList: idList,
            directoryId: "0", // Not strictly required for move but good for DTO compliance if needed
            goDirectoryId: targetDirectoryId
        })
    });

    if (!response.ok) {
        throw new Error(`Failed to move items: ${response.status}`);
    }

    return await response.json();
}

/**
 * Rename an item.
 */
export async function renameItem(id, newName) {
    const currentToken = getToken();
    if (!currentToken) throw new Error("Unauthorized");

    const response = await fetch('/api/file/rename', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'x-access-token': currentToken
        },
        body: JSON.stringify({
            id: id,
            newName: newName
        })
    });

    if (!response.ok) {
        throw new Error(`Failed to rename item: ${response.status}`);
    }

    return await response.json();
}

/**
 * File Upload: Step 1 - Apply
 */
async function uploadApply(directoryId, fileName, size, md5) {
    const currentToken = getToken();
    if (!currentToken) throw new Error("Unauthorized");

    const response = await fetch('/api/file/upload/apply', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'x-access-token': currentToken
        },
        body: JSON.stringify({
            directoryId: directoryId,
            fileName: fileName,
            size: size,
            md5: md5
        })
    });

    if (!response.ok) {
        throw new Error(`Upload apply failed: ${response.status}`);
    }

    return await response.json();
}

/**
 * File Upload: Step 2 - Finish
 */
async function uploadFinish(directoryId, fileName, size, md5, innerName) {
    const currentToken = getToken();
    if (!currentToken) throw new Error("Unauthorized");

    const response = await fetch('/api/file/upload/finish', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'x-access-token': currentToken
        },
        body: JSON.stringify({
            directoryId: directoryId,
            fileName: fileName,
            fileSize: size,
            md5: md5,
            innerName: innerName,
            type: "2" // CLOUD
        })
    });

    if (!response.ok) {
        throw new Error(`Upload finish failed: ${response.status}`);
    }

    return await response.json();
}

/**
 * Upload a file (orchestrates apply, put, and finish).
 */
export async function uploadFile(directoryId, file, onProgress) {
    // 1. Calculate MD5 (optional but good for finish)
    const md5 = await calculateFileMd5(file);

    // 2. Apply
    const applyData = await uploadApply(directoryId, file.name, file.size, md5);
    const { fullUploadUrl, innerName } = applyData;

    // 3. POST/PUT file to blob storage as multipart
    // We use FormData to ensure the server receives a multipart request.
    const formData = new FormData();
    formData.append('file', file);

    const uploadResp = await fetch(fullUploadUrl, {
        method: 'POST', // Both POST and PUT are supported by our oss.py handle_oss_upload
        body: formData,
        // Note: Do NOT set Content-Type header; fetch will set it with the correct boundary
    });

    if (!uploadResp.ok) {
        throw new Error(`File binary upload failed: ${uploadResp.status}`);
    }

    // 4. Finish
    return await uploadFinish(directoryId, file.name, file.size, md5, innerName);
}

/**
 * Helper to calculate file MD5.
 */
function calculateFileMd5(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = (e) => {
            const hash = SparkMD5.ArrayBuffer.hash(e.target.result);
            resolve(hash);
        };
        reader.onerror = reject;
        reader.readAsArrayBuffer(file);
    });
}
/**
 * MCP API Key management
 */
export async function fetchApiKeys() {
    const currentToken = getToken();
    if (!currentToken) throw new Error("Unauthorized");

    const response = await fetch('/api/mcp/api-keys', {
        method: 'GET',
        headers: { 'x-access-token': currentToken }
    });

    if (response.status === 401) { logout(); throw new Error("Unauthorized"); }
    if (!response.ok) throw new Error(`Failed to fetch API keys: ${response.status}`);
    return await response.json();
}

export async function createApiKey(name) {
    const currentToken = getToken();
    if (!currentToken) throw new Error("Unauthorized");

    const response = await fetch('/api/mcp/api-keys', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'x-access-token': currentToken },
        body: JSON.stringify({ name })
    });

    if (response.status === 401) { logout(); throw new Error("Unauthorized"); }
    if (!response.ok) throw new Error(`Failed to create API key: ${response.status}`);
    return await response.json();
}

export async function deleteApiKey(keyId) {
    const currentToken = getToken();
    if (!currentToken) throw new Error("Unauthorized");

    const response = await fetch(`/api/mcp/api-keys/${keyId}`, {
        method: 'DELETE',
        headers: { 'x-access-token': currentToken }
    });

    if (response.status === 401) { logout(); throw new Error("Unauthorized"); }
    if (!response.ok) throw new Error(`Failed to delete API key: ${response.status}`);
}

/**
 * MCP OAuth session management
 */
export async function fetchOAuthSessions() {
    const currentToken = getToken();
    if (!currentToken) throw new Error("Unauthorized");

    const response = await fetch('/api/mcp/oauth-sessions', {
        method: 'GET',
        headers: { 'x-access-token': currentToken }
    });

    if (response.status === 401) { logout(); throw new Error("Unauthorized"); }
    if (!response.ok) throw new Error(`Failed to fetch sessions: ${response.status}`);
    return await response.json();
}

export async function deleteOAuthSession(sessionId) {
    const currentToken = getToken();
    if (!currentToken) throw new Error("Unauthorized");

    const response = await fetch(`/api/mcp/oauth-sessions/${sessionId}`, {
        method: 'DELETE',
        headers: { 'x-access-token': currentToken }
    });

    if (response.status === 401) { logout(); throw new Error("Unauthorized"); }
    if (!response.ok) throw new Error(`Failed to revoke session: ${response.status}`);
}

/**
 * Fetch processing status for a list of files.
 * @param {Array<number>} fileIds
 * @returns {Promise<{success: boolean, statusMap: Object}>}
 */
export async function fetchProcessingStatus(fileIds) {
    const currentToken = getToken();
    if (!currentToken) throw new Error("Unauthorized");

    const response = await fetch('/api/extended/file/processing/status', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'x-access-token': currentToken
        },
        body: JSON.stringify({ fileIds: fileIds })
    });

    if (response.status === 401) {
        logout();
        throw new Error("Unauthorized");
    }

    if (!response.ok) {
        throw new Error(`Failed to fetch processing status: ${response.status}`);
    }

    const data = await response.json();
    return {
        success: true,
        statusMap: data.statusMap
    };
}

/**
 * Fetch all prompt configurations for the current user.
 * @returns {Promise<{success: boolean, prompts: Array}>}
 */
export async function fetchPrompts() {
    const currentToken = getToken();
    if (!currentToken) throw new Error("Unauthorized");

    const response = await fetch('/api/extended/prompts', {
        headers: { 'x-access-token': currentToken }
    });

    if (response.status === 401) { logout(); throw new Error("Unauthorized"); }
    if (!response.ok) throw new Error(`Failed to fetch prompts: ${response.status}`);
    return await response.json();
}

/**
 * Save or update a prompt layer override.
 * @param {string} category - 'ocr' or 'summary'
 * @param {string} layer - layer name
 * @param {string} content - prompt text
 * @returns {Promise<{success: boolean}>}
 */
export async function savePrompt(category, layer, content) {
    const currentToken = getToken();
    if (!currentToken) throw new Error("Unauthorized");

    const response = await fetch('/api/extended/prompts', {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
            'x-access-token': currentToken
        },
        body: JSON.stringify({ category, layer, content })
    });

    if (response.status === 401) { logout(); throw new Error("Unauthorized"); }
    if (!response.ok) throw new Error(`Failed to save prompt: ${response.status}`);
    return await response.json();
}

/**
 * Delete a prompt override, reverting to server default.
 * @param {string} category
 * @param {string} layer
 * @returns {Promise<{success: boolean}>}
 */
export async function deletePrompt(category, layer) {
    const currentToken = getToken();
    if (!currentToken) throw new Error("Unauthorized");

    const response = await fetch(`/api/extended/prompts/${category}/${layer}`, {
        method: 'DELETE',
        headers: { 'x-access-token': currentToken }
    });

    if (response.status === 401) { logout(); throw new Error("Unauthorized"); }
    if (!response.ok) throw new Error(`Failed to delete prompt: ${response.status}`);
    return await response.json();
}

/**
 * Fetch staleness data for a file.
 * @param {number} fileId
 * @returns {Promise<{success: boolean, currentPromptHash: string, staleCount: number, totalCount: number, pages: Array}>}
 */
export async function fetchStaleness(fileId) {
    const currentToken = getToken();
    if (!currentToken) throw new Error("Unauthorized");

    const response = await fetch(`/api/extended/files/${fileId}/staleness`, {
        headers: { 'x-access-token': currentToken }
    });

    if (response.status === 401) { logout(); throw new Error("Unauthorized"); }
    if (!response.ok) throw new Error(`Failed to fetch staleness: ${response.status}`);
    return await response.json();
}

/**
 * Reprocess stale pages for a file.
 * @param {number} fileId
 * @param {Array<string>|null} pageIds - specific page IDs, or null for all stale
 * @returns {Promise<{success: boolean, queuedPageCount: number}>}
 */
export async function reprocessFile(fileId, pageIds = null) {
    const currentToken = getToken();
    if (!currentToken) throw new Error("Unauthorized");

    const body = pageIds !== null ? JSON.stringify({ pageIds }) : '{}';

    const response = await fetch(`/api/extended/files/${fileId}/reprocess`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'x-access-token': currentToken
        },
        body
    });

    if (response.status === 401) { logout(); throw new Error("Unauthorized"); }
    if (!response.ok) throw new Error(`Failed to reprocess file: ${response.status}`);
    return await response.json();
}

/**
 * Reprocess a single page.
 * @param {number} fileId
 * @param {string} pageId
 * @returns {Promise<{success: boolean, queuedPageCount: number}>}
 */
export async function reprocessPage(fileId, pageId) {
    const currentToken = getToken();
    if (!currentToken) throw new Error("Unauthorized");

    const response = await fetch(`/api/extended/files/${fileId}/pages/${pageId}/reprocess`, {
        method: 'POST',
        headers: { 'x-access-token': currentToken }
    });

    if (response.status === 401) { logout(); throw new Error("Unauthorized"); }
    if (!response.ok) throw new Error(`Failed to reprocess page: ${response.status}`);
    return await response.json();
}

/**
 * Reprocess all note files for the current user.
 * @returns {Promise<{success: boolean, queuedPageCount: number}>}
 */
export async function reprocessAllNotes() {
    const currentToken = getToken();
    if (!currentToken) throw new Error("Unauthorized");

    const response = await fetch('/api/extended/reprocess-all', {
        method: 'POST',
        headers: { 'x-access-token': currentToken }
    });

    if (response.status === 401) { logout(); throw new Error("Unauthorized"); }
    if (!response.ok) throw new Error(`Failed to reprocess all notes: ${response.status}`);
    return await response.json();
}
