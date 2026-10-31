const { app, BrowserWindow, shell, Menu } = require("electron");
const path = require("path");
const http = require("http");

let mainWindow = null;
const DEFAULT_URL = process.env.CAMPUSASSIST_URL || "http://127.0.0.1:8000";

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
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      nodeIntegration: false,
      contextIsolation: true,
      spellcheck: true,
    },
  });

  // Splash loading HTML
  const splashHTML = `
  <!DOCTYPE html>
  <html>
  <head>
    <meta charset="utf-8">
    <title>CampusAssist Loading</title>
    <style>
      body {
        margin: 0;
        height: 100vh;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        background: #0B0F19;
        color: #EAF0FB;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      }
      .loader {
        width: 50px;
        height: 50px;
        border: 4px solid rgba(255, 255, 255, 0.1);
        border-top-color: #2563EB;
        border-radius: 50%;
        animation: spin 1s linear infinite;
        margin-bottom: 20px;
      }
      @keyframes spin { to { transform: rotate(360deg); } }
      h2 { font-weight: 500; margin: 0 0 8px 0; }
      p { color: #8593AB; font-size: 14px; margin: 0; }
    </style>
  </head>
  <body>
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

  // Build native application menu
  const menuTemplate = [
    {
      label: "CampusAssist",
      submenu: [
        {
          label: "About CampusAssist",
          click: () => {
            shell.openExternal("https://www.lpu.in");
          },
        },
        { type: "separator" },
        { role: "quit" },
      ],
    },
    {
      label: "Edit",
      submenu: [
        { role: "undo" },
        { role: "redo" },
        { type: "separator" },
        { role: "cut" },
        { role: "copy" },
        { role: "paste" },
        { role: "selectAll" },
      ],
    },
    {
      label: "View",
      submenu: [
        { role: "reload" },
        { role: "forceReload" },
        { role: "toggleDevTools" },
        { type: "separator" },
        { role: "resetZoom" },
        { role: "zoomIn" },
        { role: "zoomOut" },
        { type: "separator" },
        { role: "togglefullscreen" },
      ],
    },
  ];

  const menu = Menu.buildFromTemplate(menuTemplate);
  Menu.setApplicationMenu(menu);

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

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
