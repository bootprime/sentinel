// Config
const API_URL = "http://127.0.0.1:8001";
const HEARTBEAT_INTERVAL = 5000;

// State
let backendAlive = false;
let authToken = null;

// Load Token on Start and Listen for Changes
function loadToken() {
    chrome.storage.local.get(['sentinel_token', 'lastActivity'], function (result) {
        authToken = result.sentinel_token;
        lastActivity = result.lastActivity || 0;
        console.log("Auth Token Loaded:", authToken ? "YES" : "NO");
    });
}
loadToken();

chrome.storage.onChanged.addListener(function (changes, namespace) {
    if (changes.sentinel_token) {
        authToken = changes.sentinel_token.newValue;
        console.log("Auth Token Updated");
    }
});

// Helper for Auth Headers
function getHeaders() {
    const headers = { "Content-Type": "application/json" };
    if (authToken) {
        headers["Authorization"] = `Bearer ${authToken}`;
    }
    return headers;
}

// Connectivity Check (Updates Extension Badge)
async function checkConnectivity() {
    try {
        const res = await fetch(`${API_URL}/heartbeat/`);
        if (res.ok) {
            const data = await res.json();
            backendAlive = true;
            chrome.action.setBadgeText({ text: "ON" });
            chrome.action.setBadgeBackgroundColor({ color: "#00FF00" });

            chrome.storage.local.set({
                status: "connected",
                details: data,
                lastCheck: new Date().toLocaleTimeString()
            });
        }
    } catch (e) {
        backendAlive = false;
        chrome.action.setBadgeText({ text: "OFF" });
        chrome.action.setBadgeBackgroundColor({ color: "#FF0000" });

        chrome.storage.local.set({
            status: "disconnected",
            error: e.message,
            lastCheck: new Date().toLocaleTimeString()
        });
    }
}

// Connection Registry
let lastActivity = 0; // Last time a TradingView tab pinged us

// Source Pulse (Informs Sentinel UI that Source is Active)
async function sendSourcePulse() {
    if (!backendAlive || !authToken) return;

    // SMART PULSE: Only notify backend if a TradingView tab is actually open/active
    const now = Date.now();
    if (now - lastActivity > 10000) { // Reduced to 10s for snappy UI
        console.log("No active TradingView sessions. Skipping pulse.");
        return;
    }

    try {
        await fetch(`${API_URL}/heartbeat/source/heartbeat`, {
            method: "POST",
            headers: getHeaders()
        });
        console.log("Institutional Pulse Sent");
    } catch (e) {
        console.warn("Pulse delivery failed", e);
    }
}

// Run Loops
checkConnectivity();
sendSourcePulse();
setInterval(checkConnectivity, 5000); // 5s for UI responsiveness
setInterval(sendSourcePulse, 10000);  // Match 10s window for real-time status

// Listen for Signals from Content Script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.type === "SESSION_ACTIVE") {
        lastActivity = Date.now();
        chrome.storage.local.set({ lastActivity: lastActivity });
    } else if (request.type === "SIGNAL") {
        console.log("Received signal from content script:", request.payload);

        if (!backendAlive) {
            console.error("Backend dead, dropping signal.");
            return;
        }

        // Forward to Backend
        fetch(`${API_URL}/signal/`, {
            method: "POST",
            headers: getHeaders(), // Secured Signal
            body: JSON.stringify(request.payload)
        })
            .then(res => res.json())
            .then(data => {
                console.log("Signal forwarded successfully:", data);
                // Save last success to storage for Popup UI
                chrome.storage.local.set({
                    lastSignal: {
                        time: new Date().toLocaleTimeString(),
                        id: request.payload.signal_id,
                        symbol: request.payload.symbol,
                        direction: request.payload.direction,
                        result: data
                    }
                });
            })
            .catch(err => {
                console.error("Failed to forward signal:", err);
            });
    }
});
