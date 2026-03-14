// Saves options to chrome.storage
function saveOptions() {
    var token = document.getElementById('token').value;
    chrome.storage.local.set({
        sentinel_token: token
    }, function () {
        // Update status to let user know options were saved.
        var status = document.getElementById('status');
        status.textContent = 'Token Saved Successfully.';
        status.style.color = '#4ade80';
        setTimeout(function () {
            status.textContent = '';
        }, 2000);
    });
}

// Restores select box and checkbox state using the preferences
// stored in chrome.storage.
function restoreOptions() {
    chrome.storage.local.get({
        sentinel_token: ''
    }, function (items) {
        document.getElementById('token').value = items.sentinel_token;
    });
}

document.addEventListener('DOMContentLoaded', restoreOptions);
document.getElementById('save').addEventListener('click', saveOptions);
