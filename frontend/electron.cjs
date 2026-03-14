const { app, BrowserWindow, Tray, Menu } = require('electron');
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');

let mainWindow;
let tray;
let pythonBackend = null;
let isQuitting = false;

// SECURITY: Load Sentinel Token
const SECRETS_PATH = path.join(__dirname, '../data/secrets.json');
function loadToken() {
    try {
        if (fs.existsSync(SECRETS_PATH)) {
            const data = JSON.parse(fs.readFileSync(SECRETS_PATH, 'utf8'));
            process.env.SENTINEL_TOKEN = data.api_token;
            console.log("Sentinel Token Loaded into Environment");
        }
    } catch (e) { console.error("Token load failed:", e); }
}

function startBackend() {
    const isDev = !app.isPackaged;
    const pythonExecutable = "python"; // Assume python in path
    const mainScript = path.join(__dirname, '../main.py');

    console.log("Starting Python Backend:", mainScript);

    pythonBackend = spawn(pythonExecutable, [mainScript], {
        cwd: path.join(__dirname, '..'),
        env: { ...process.env, PYTHONUNBUFFERED: "1" }
    });

    pythonBackend.stdout.on('data', (data) => console.log(`[Backend]: ${data}`));
    pythonBackend.stderr.on('data', (data) => console.error(`[Backend-Error]: ${data}`));

    pythonBackend.on('close', (code) => {
        console.log(`Backend process exited with code ${code}`);
        if (!isQuitting) {
            console.log("Backend died unexpectedly. Restarting in 3s...");
            setTimeout(startBackend, 3000);
        }
    });
}

function stopBackend() {
    if (pythonBackend) {
        isQuitting = true;
        console.log("Killing Python Backend...");
        pythonBackend.kill('SIGTERM');
    }
}

const { nativeImage } = require('electron');

function createTray() {
    try {
        const iconPath = path.join(__dirname, 'public/vite.svg');
        // SVG might fail on some Windows versions in Tray, so we use nativeImage with fallback
        let icon = nativeImage.createFromPath(iconPath);

        if (icon.isEmpty()) {
            // Fallback: Create a tiny blue square if icon fails to load
            icon = nativeImage.createFromBuffer(Buffer.from(
                'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAMklEQVR42mP8/58BH2BkYIAR6BgaGf+jY7A5IAZgGPyB4YMBDAzD4A8MHwxghGMAAFAvCxcR8X9AAAAAAElFTkSuQmCC', 'base64'
            ));
        }

        tray = new Tray(icon);
        const contextMenu = Menu.buildFromTemplate([
            { label: 'Open Sentinel', click: () => mainWindow.show() },
            { label: 'Restart Backend', click: () => { stopBackend(); isQuitting = false; startBackend(); } },
            { type: 'separator' },
            { label: 'Quit Sentinel', click: () => { isQuitting = true; app.quit(); } }
        ]);
        tray.setToolTip('Sentinel Execution Authority');
        tray.setContextMenu(contextMenu);
        tray.on('double-click', () => mainWindow.show());
    } catch (e) {
        console.error("Failed to create tray:", e);
    }
}

function createWindow() {
    const isDev = !app.isPackaged;
    loadToken();

    mainWindow = new BrowserWindow({
        width: 1280,
        height: 800,
        title: "Sentinel Prime - Execution Authority",
        backgroundColor: '#020617',
        show: false,
        webPreferences: {
            nodeIntegration: true,
            contextIsolation: false,
        },
        icon: path.join(__dirname, 'public/vite.svg')
    });

    mainWindow.setMenuBarVisibility(false);

    const startUrl = isDev
        ? 'http://127.0.0.1:5173'
        : `file://${path.join(__dirname, 'dist/index.html')}`;

    mainWindow.loadURL(startUrl);

    mainWindow.once('ready-to-show', () => {
        mainWindow.maximize();
        mainWindow.show();
    });

    mainWindow.on('close', (event) => {
        if (!isQuitting) {
            event.preventDefault();
            mainWindow.hide();
        }
        return false;
    });

    mainWindow.on('closed', () => {
        mainWindow = null;
    });
}

const gotTheLock = app.requestSingleInstanceLock();
if (!gotTheLock) {
    app.quit();
} else {
    app.on('second-instance', () => {
        if (mainWindow) {
            if (mainWindow.isMinimized()) mainWindow.restore();
            mainWindow.show();
            mainWindow.focus();
        }
    });

    app.whenReady().then(() => {
        startBackend();
        setTimeout(createTray, 1000); // Small delay for backend to log
        createWindow();
    });
}

app.on('before-quit', () => {
    isQuitting = true;
    stopBackend();
});

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin' && isQuitting) {
        app.quit();
    }
});
