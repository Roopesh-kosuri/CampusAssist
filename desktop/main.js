const { app, BrowserWindow, shell, Menu, ipcMain } = require("electron");
const path = require("path");
const http = require("http");

let mainWindow = null;
const DEFAULT_URL = process.env.CAMPUSASSIST_URL || "http://127.0.0.1:8000";

// Remove the native Win32 menu bar entirely
Menu.setApplicationMenu(null);

function checkBackendReady(urlStr, callback) {
  try {
    const parsed = new URL(urlStr);
    const req = http.get(
      {
        host: parsed.hostname,
        port: parsed.port || (parsed.protocol === "https:" ? 443 : 80),
        path: "/health",
        timeout: 2000,
      },
      (res) => {
        callback(res.statusCode === 200);
      }
    );
    req.on("error", () => callback(false));
    req.on("timeout", () => {
      req.destroy();
      callback(false);
    });
  } catch (e) {
    callback(false);
  }
}

function createWindow() {
  const iconPath = path.join(__dirname, "build", "icon.png");

  mainWindow = new BrowserWindow({
    width: 1240,
    height: 840,
    minWidth: 860,
    minHeight: 600,
    title: "CampusAssist - LPU Student AI Assistant",
    icon: iconPath,
    backgroundColor: "#0B0F19",
    // Fully frameless — we draw our own title bar in HTML
    frame: false,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      nodeIntegration: false,
      contextIsolation: true,
      spellcheck: true,
    },
  });

  // Modern Liquid Glass splash loading HTML
  const splashHTML = `
  <!DOCTYPE html>
  <html>
  <head>
    <meta charset="utf-8">
    <title>CampusAssist Loading</title>
    <style>
      * { box-sizing: border-box; margin: 0; }
      body {
        height: 100vh;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        background: #0B0F19;
        color: #EAF0FB;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        overflow: hidden;
        -webkit-user-select: none;
        user-select: none;
      }
      /* Draggable region so user can move window during splash */
      .drag { position: fixed; top: 0; left: 0; right: 0; height: 38px; -webkit-app-region: drag; }
      .loader {
        width: 48px;
        height: 48px;
        border: 4px solid rgba(255, 255, 255, 0.08);
        border-top-color: #D26A45;
        border-radius: 50%;
        animation: spin 1s cubic-bezier(0.4, 0, 0.2, 1) infinite;
        margin-bottom: 22px;
      }
      @keyframes spin { to { transform: rotate(360deg); } }
      h2 { font-weight: 600; font-size: 24px; margin: 0 0 8px 0; letter-spacing: -0.02em; }
      p { color: #8593AB; font-size: 14px; margin: 0; }
    </style>
  </head>
  <body>
    <div class="drag"></div>
    <div class="loader"></div>
    <h2>CampusAssist</h2>
    <p>Connecting to Campus AI Engine...</p>
  </body>
  </html>
  `;

  mainWindow.loadURL("data:text/html;charset=utf-8," + encodeURIComponent(splashHTML));

  // Poll for backend and load main interface
  let attempts = 0;
  const pollInterval = setInterval(() => {
    attempts++;
    checkBackendReady(DEFAULT_URL, (ready) => {
      if (ready || attempts > 15) {
        clearInterval(pollInterval);
        mainWindow.loadURL(DEFAULT_URL).catch((err) => {
          console.error("Failed to load application URL:", err);
        });
      }
    });
  }, 800);

  // Handle external links (open in default browser)
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith("http:") || url.startsWith("https:")) {
      shell.openExternal(url);
      return { action: "deny" };
    }
    return { action: "allow" };
  });

  // Update maximize/restore icon when window state changes
  mainWindow.on("maximize", () => {
    mainWindow.webContents.send("win-state-changed", "maximized");
  });
  mainWindow.on("unmaximize", () => {
    mainWindow.webContents.send("win-state-changed", "normal");
  });

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

// ── IPC: Custom window controls ──────────────────────────────────────────────
ipcMain.on("win-minimize", () => mainWindow?.minimize());
ipcMain.on("win-maximize", () => {
  if (!mainWindow) return;
  mainWindow.isMaximized() ? mainWindow.unmaximize() : mainWindow.maximize();
});
ipcMain.on("win-close", () => mainWindow?.close());

// ── IPC: App utilities ───────────────────────────────────────────────────────
ipcMain.on("app-reload", () => {
  if (mainWindow) mainWindow.reload();
});
ipcMain.on("app-toggle-fullscreen", () => {
  if (mainWindow) {
    mainWindow.setFullScreen(!mainWindow.isFullScreen());
  }
});
ipcMain.on("app-devtools", () => {
  if (mainWindow) mainWindow.webContents.toggleDevTools();
});

app.whenReady().then(() => {
  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});
