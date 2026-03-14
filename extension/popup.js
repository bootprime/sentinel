function updateUI() {
    chrome.storage.local.get(['status', 'details', 'error', 'lastSignal', 'lastCheck', 'sentinel_token', 'lastActivity'], (result) => {
        const dot = document.getElementById('status-dot');
        const text = document.getElementById('status-text');
        const mode = document.getElementById('mode-val');
        const state = document.getElementById('state-val');
        const pulse = document.getElementById('pulse-val');
        const log = document.getElementById('last-signal');
        const footer = document.getElementById('hb-time');

        // Always show last check time if available
        if (result.lastCheck) {
            footer.innerText = 'Last Check: ' + result.lastCheck;
        }

        // Pulse Diagnostic
        const now = Date.now();
        const activityAge = now - (result.lastActivity || 0);

        if (!result.sentinel_token) {
            pulse.innerText = "NO AUTHENTICATION";
            pulse.style.color = "#666";
        } else if (activityAge > 10000) {
            pulse.innerText = "CHART INACTIVE";
            pulse.style.color = "#FF8C00";
        } else if (result.status === 'connected') {
            const secs = Math.floor(activityAge / 1000);
            pulse.innerText = secs < 3 ? "ACTIVE" : `ACTIVE (${secs}s ago)`;
            pulse.style.color = "#818cf8";
        } else {
            pulse.innerText = "PULSE WAITING";
            pulse.style.color = "#666";
        }

        // Connection Status
        if (result.status === 'connected') {
            dot.className = 'dot connected';
            text.innerText = 'ONLINE';
            text.style.color = '#00FF00';

            if (result.details) {
                mode.innerText = result.details.mode || 'UNK';
                state.innerText = result.details.system_state || 'UNK';
                state.style.color = result.details.system_state === 'READY' ? '#4ec9b0' : '#FF0000';
            }
        } else {
            dot.className = 'dot disconnected';
            text.innerText = 'OFFLINE';
            text.style.color = '#FF0000';
            mode.innerText = '--';
            state.innerText = 'DISCONNECTED';
            state.style.color = '#666';
        }

        // Last Signal Display
        if (result.lastSignal) {
            const s = result.lastSignal;
            log.innerHTML = `
                <div class="log-entry">
                    <span class="highlight">[${s.time}]</span> 
                    Signal <span class="val">${s.id}</span><br>
                    ${s.symbol} <span style="color:${s.direction === 'CALL' ? '#00FF00' : '#FF0000'}">${s.direction}</span> 
                    Sent <span style="color:#28a745">✔</span>
                </div>
            `;
        }
    });
}

// Run on load
document.addEventListener('DOMContentLoaded', () => {
    updateUI();
    setInterval(updateUI, 1000);

    const popBtn = document.getElementById('popout-btn');
    if (popBtn) {
        popBtn.addEventListener('click', () => {
            chrome.windows.create({
                url: chrome.runtime.getURL("popup.html"),
                type: "popup",
                width: 360,
                height: 500
            });
        });
    }
});
