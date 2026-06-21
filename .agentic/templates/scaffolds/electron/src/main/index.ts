import { app, BrowserWindow, ipcMain, shell } from "electron"
import { join } from "node:path"

function createWindow(): void {
  const win = new BrowserWindow({
    width: 1100,
    height: 720,
    show: false,
    autoHideMenuBar: true,
    webPreferences: {
      preload: join(__dirname, "../preload/index.js"),
      sandbox: true, // renderer runs in a sandbox
      contextIsolation: true, // context isolation (security baseline — Heimdall)
      nodeIntegration: false, // renderer has NO direct Node API
    },
  })

  win.once("ready-to-show", () => win.show())

  // External links open in the browser, not in the app window.
  win.webContents.setWindowOpenHandler(({ url }) => {
    void shell.openExternal(url)
    return { action: "deny" }
  })

  // Dev: vite dev server (HMR); prod: the built renderer from a file.
  const devUrl = process.env["ELECTRON_RENDERER_URL"]
  if (devUrl) {
    void win.loadURL(devUrl)
  } else {
    void win.loadFile(join(__dirname, "../renderer/index.html"))
  }
}

// Example IPC handler — the renderer calls it only through the typed preload bridge.
ipcMain.handle("app:version", () => app.getVersion())

app.whenReady().then(() => {
  createWindow()
  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    }
  })
})

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit()
  }
})
