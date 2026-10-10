// Preload script for Electron renderer process
// Exposes safe IPC methods to the renderer

const { contextBridge, ipcRenderer } = require('electron');

// Expose protected methods that allow the renderer to use IPC
contextBridge.exposeInMainWorld('electronAPI', {
  // File operations
  openFile: () => ipcRenderer.invoke('dialog:openFile'),
  saveFile: (content, defaultPath) => ipcRenderer.invoke('dialog:saveFile', { content, defaultPath }),
  
  // LaTeX compilation
  compileLaTeX: (latexContent, projectDir) => ipcRenderer.invoke('compile:latex', { latexContent, projectDir }),
  
  // Add more IPC methods as needed
});