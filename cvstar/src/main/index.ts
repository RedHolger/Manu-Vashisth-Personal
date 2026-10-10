import { app, BrowserWindow, ipcMain } from 'electron';
import * as path from 'path';
import * as fs from 'fs';

// Handle creating/removing shortcuts on Windows when installing/uninstalling.
if (require('electron-squirrel-startup')) {
  app.quit();
}

const createWindow = () => {
  // Create the browser window.
  const mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  // and load the index.html of the app.
  mainWindow.loadFile(path.join(__dirname, '../../public/index.html'));

  // Open the DevTools.
  mainWindow.webContents.openDevTools();
};

// This method will be called when Electron has finished
// initialization and is ready to create browser windows.
// Some APIs can only be used after this event occurs.
app.on('ready', createWindow);

// Quit when all windows are closed, except on macOS. There, it's common
// for applications and their menu bar to stay active until the user quits
// explicitly with Cmd + Q.
app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  // On OS X it's common to re-create a window in the app when the
  // dock icon is clicked and there are no other windows open.
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});

// IPC handlers for file operations
ipcMain.handle('dialog:openFile', async () => {
  const { dialog } = require('electron');
  const result = await dialog.showOpenDialog({
    properties: ['openFile'],
    filters: [
      { name: 'LaTeX Files', extensions: ['tex'] },
      { name: 'All Files', extensions: ['*'] }
    ]
  });
  
  if (!result.canceled && result.filePaths.length > 0) {
    const filePath = result.filePaths[0];
    const content = await fs.promises.readFile(filePath, 'utf8');
    return { success: true, path: filePath, content };
  }
  
  return { success: false };
});

ipcMain.handle('dialog:saveFile', async (event, { content, defaultPath }) => {
  const { dialog } = require('electron');
  const result = await dialog.showSaveDialog({
    defaultPath: path.basename(defaultPath || 'untitled.tex'),
    filters: [
      { name: 'LaTeX Files', extensions: ['tex'] },
      { name: 'All Files', extensions: ['*'] }
    ]
  });
  
  if (!result.canceled && result.filePath) {
    await fs.promises.writeFile(result.filePath, content, 'utf8');
    return { success: true, path: result.filePath };
  }
  
  return { success: false };
});

// Handle LaTeX compilation requests
ipcMain.handle('compile:latex', async (event, { latexContent, projectDir }) => {
  const { exec } = require('child_process');
  const util = require('util');
  const execAsync = util.promisify(exec);
  
  try {
    // Write LaTeX content to file
    const texFilePath = path.join(projectDir, 'main.tex');
    await fs.promises.writeFile(texFilePath, latexContent, 'utf8');
    
    // Compile with latexmk
    const { stdout, stderr } = await execAsync('latexmk -pdf -interaction=nonstopmode', {
      cwd: projectDir,
      timeout: 30000
    });
    
    // Read generated PDF
    const pdfPath = path.join(projectDir, 'main.pdf');
    const pdfExists = await fs.promises.access(pdfPath).then(() => true).catch(() => false);
    
    let pdfData = null;
    if (pdfExists) {
      pdfData = await fs.promises.readFile(pdfPath);
    }
    
    return {
      success: true,
      stdout,
      stderr,
      pdfData: pdfData ? pdfData.toString('base64') : null,
      log: `${stdout}\n${stderr}`
    };
  } catch (error: any) {
    return {
      success: false,
      error: error.message,
      stdout: error.stdout,
      stderr: error.stderr
    };
  }
});