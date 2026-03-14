import axios from 'axios';

const API_BASE = 'http://127.0.0.1:8001';

const api = axios.create({
    baseURL: API_BASE,
    timeout: 5000,
    headers: {
        'Content-Type': 'application/json',
    },
});

// INTERCEPTOR: Inject Token
api.interceptors.request.use((config) => {
    // In Electron with nodeIntegration, we can access process.env
    // We try multiple sources for resilience
    const token = window.process?.env?.SENTINEL_TOKEN || localStorage.getItem('sentinel_token');

    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
}, (error) => {
    return Promise.reject(error);
});

export const checkSystemStatus = async () => {
    try {
        const res = await api.get('/heartbeat/');
        return res.data; // { status: "ok", timestamp: ... }
    } catch (err) {
        return { status: "offline", error: err.message };
    }
};

export const getConfig = async () => {
    try {
        const res = await api.get('/config/');
        return res.data;
    } catch (err) {
        console.error("Config Fetch Failed:", err);
        return null;
    }
};

export const updateConfig = async (newConfig) => {
    const res = await api.put('/config/', newConfig);
    return res.data;
};

export const getSignals = async () => {
    try {
        const res = await api.get('/signal/');
        return res.data;
    } catch (err) {
        console.error("Failed to fetch signals:", err);
        return [];
    }
};

export const getLogs = async (lines = 50, level = null, category = null) => {
    try {
        const params = { lines };
        if (level) params.level = level;
        if (category) params.category = category;

        const res = await api.get('/logs/', { params });
        return res.data;
    } catch (err) {
        console.error("Log Fetch Error:", err);
        return [{ level: "ERROR", message: "Failed to fetch logs", timestamp: new Date().toISOString() }];
    }
};

export const getAuthStatus = async () => {
    try {
        const res = await api.get('/auth/status');
        return res.data;
    } catch (err) {
        // Return structured null object to prevent destructuring errors in React
        // This was the source of the crash when backend is offline
        console.error("Auth Status Fetch Failed:", err);
        return null;
    }
};

export const updateToken = async (broker_name, access_token, client_id = null) => {
    const payload = { broker_name, access_token };
    if (client_id) payload.client_id = client_id;

    const res = await api.post('/auth/update-token', payload);
    return res.data;
};

export const triggerKillSwitch = async () => {
    const res = await api.post('/governance/kill');
    return res.data;
};

export const triggerManualPause = async () => {
    const res = await api.post('/governance/pause');
    return res.data;
};

export default api;
