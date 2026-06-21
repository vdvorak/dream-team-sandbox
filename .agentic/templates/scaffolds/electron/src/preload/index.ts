import { contextBridge, ipcRenderer } from "electron"

// The only renderer ↔ main bridge. With contextIsolation=true the renderer sees only this
// API, not the whole ipcRenderer. Every channel is explicit (no generic passthrough).
const api = {
  getVersion: (): Promise<string> => ipcRenderer.invoke("app:version"),
}

contextBridge.exposeInMainWorld("api", api)

export type Api = typeof api
