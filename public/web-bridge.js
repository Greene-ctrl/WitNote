(function() {
    if (typeof window.fs !== 'undefined') return;

    console.log('🌐 Web Bridge loading...');

    async function apiCall(endpoint, method = 'POST', body = null) {
        const options = {
            method,
            headers: {
                'Content-Type': 'application/json'
            }
        };
        if (body) {
            options.body = JSON.stringify(body);
        }
        const response = await fetch('/api' + endpoint, options);
        if (!response.ok) {
            const err = await response.json().catch(() => ({ detail: response.statusText }));
            throw new Error('API Error: ' + (err.detail || response.statusText));
        }
        return response.json();
    }

    window.fs = {
        getVaultPath: () => fetch('/api/fs/getVaultPath').then(r => r.json()),
        setVaultPath: (path) => Promise.resolve(true),
        selectDirectory: () => window.fs.getVaultPath(), // Match the server's vault path
        disconnectVault: () => Promise.resolve(true),
        readDirectory: (path) => apiCall('/fs/readDirectory', 'POST', { path }),
        readFile: (path) => apiCall('/fs/readFile', 'POST', { path }),
        writeFile: (path, content) => apiCall('/fs/writeFile', 'POST', { path, content }),
        createFile: (path) => apiCall('/fs/createFile', 'POST', { path }),
        createDirectory: (path) => apiCall('/fs/createDirectory', 'POST', { path }),
        deleteFile: (path) => apiCall('/fs/deleteFile', 'POST', { path }),
        renameFile: (oldPath, newPath) => apiCall('/fs/renameFile', 'POST', { oldPath, newPath }),
        readFileBuffer: (path) => fetch('/api/fs/readFileBuffer', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path })
        }).then(r => {
            if (!r.ok) throw new Error('Buffer read failed');
            return r.arrayBuffer();
        }),
        copyExternalFile: (externalPath, targetDir) => Promise.resolve(null),
        saveImage: (relativeDirPath, base64Data, fileName) => apiCall('/fs/saveImage', 'POST', { relativeDirPath, base64Data, fileName }),
        selectAndCopyImage: (relativeDirPath) => Promise.resolve(null),
        downloadAndSaveImage: (imageUrl, relativeDirPath) => apiCall('/fs/downloadAndSaveImage', 'POST', { imageUrl, relativeDirPath }),
        isImageReferenced: (imageRelativePath, excludeFilePath) => apiCall('/fs/isImageReferenced', 'POST', { imageRelativePath, excludeFilePath }),
        deleteUnreferencedImage: (imageRelativePath) => apiCall('/fs/deleteFile', 'POST', { path: imageRelativePath }),
        exportMarkdownToPdf: (htmlContent, outputPath, title) => apiCall('/export-markdown-to-pdf', 'POST', { htmlContent, outputPath, title }),
        watch: (path) => Promise.resolve(true),
        unwatch: () => Promise.resolve(true),
        onFileChange: (callback) => {
            // No real-time file change detection in web version without WebSockets
            return () => {};
        }
    };

    window.chat = {
        load: (filePath) => apiCall('/chat/load', 'POST', { filePath }),
        save: (filePath, messages) => apiCall('/chat/save', 'POST', { filePath, messages }),
        deleteAll: () => apiCall('/chat/deleteAll', 'POST')
    };

    window.platform = {
        os: 'web',
        isMac: false,
        isWindows: false
    };

    window.appWindow = {
        setWidth: (width) => Promise.resolve(true)
    };

    window.app = {
        getVersion: () => apiCall('/app/getVersion', 'GET')
    };

    window.settings = {
        get: () => apiCall('/settings/get', 'GET'),
        set: (key, value) => apiCall('/settings/set', 'POST', { key, value }),
        reset: () => apiCall('/settings/reset', 'POST')
    };

    window.vault = {
        syncSettings: () => apiCall('/vault/syncSettings', 'POST'),
        loadSettings: () => apiCall('/vault/loadSettings', 'GET'),
        saveEngineConfig: (config) => apiCall('/vault/saveEngineConfig', 'POST', { config }),
        loadEngineConfig: () => apiCall('/vault/loadEngineConfig', 'GET')
    };

    window.ollama = {
        listModels: () => apiCall('/ollama/listModels', 'GET'),
        pullModel: (modelName) => Promise.resolve({ success: false, output: 'Not supported in web' }),
        deleteModel: (modelName) => Promise.resolve({ success: false }),
        cancelPull: (modelName) => Promise.resolve({ success: false }),
        onPullProgress: (callback) => {
            return () => {};
        }
    };

    window.shortcuts = {
        onCreateArticle: (callback) => () => {},
        onCreateFolder: (callback) => () => {},
        onOpenSettings: (callback) => () => {},
        onToggleFocusMode: (callback) => () => {},
        onCycleEditorMode: (callback) => () => {},
        onToggleSmartAutocomplete: (callback) => () => {},
        syncSmartAutocomplete: (enabled) => Promise.resolve(true),
        changeMenuLanguage: (lang) => Promise.resolve(true)
    };

    window.externalFile = {
        onOpenExternalFile: (callback) => () => {},
        getExternalFilePath: () => Promise.resolve(null)
    };

    console.log('✅ Web Bridge loaded successfully');
})();
