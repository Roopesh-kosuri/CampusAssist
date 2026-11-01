// CampusAssist Electron Preload Script
const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("electronAPI", {
  isElectron: true,
  platform: process.platform,
  version: "1.0.0",

  // Window controls (frameless mode)
  winMinimize: () => ipcRenderer.send("win-minimize"),
  winMaximize: () => ipcRenderer.send("win-maximize"),
  winClose:    () => ipcRenderer.send("win-close"),

  // Listen for window state changes (maximize/restore)
  onWinStateChange: (cb) => {
    ipcRenderer.on("win-state-changed", (_event, state) => cb(state));
  },

  // App utilities
  reload:          () => ipcRenderer.send("app-reload"),
  toggleFullscreen:() => ipcRenderer.send("app-toggle-fullscreen"),
  openDevTools:    () => ipcRenderer.send("app-devtools"),
});
