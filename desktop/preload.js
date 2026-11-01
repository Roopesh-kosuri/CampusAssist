// CampusAssist Electron Preload Script
const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("electronAPI", {
  isElectron: true,
  platform: process.platform,
  version: "1.0.0",
  reload: () => ipcRenderer.send("app-reload"),
  toggleFullscreen: () => ipcRenderer.send("app-toggle-fullscreen"),
  openDevTools: () => ipcRenderer.send("app-devtools")
});
