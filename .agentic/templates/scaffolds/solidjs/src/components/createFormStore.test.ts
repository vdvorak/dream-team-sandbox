import { createRoot } from "solid-js"
import { describe, expect, it, vi } from "vitest"

import { createFormStore, type SaveResult } from "./createFormStore"

interface Data {
  label: string
}

describe("createFormStore", () => {
  it("submit: dry-run validate → commit when clean", async () => {
    await createRoot(async (dispose) => {
      const save = vi
        .fn<(d: Data, validate: boolean) => Promise<SaveResult>>()
        .mockResolvedValue({})
      const onSuccess = vi.fn()
      const form = createFormStore<Data>({
        defaultData: { label: "" },
        save,
        onSuccess,
      })

      form.field("label").set("ahoj")
      await form.submit()

      // 1st call = validation-only (true), 2nd = commit (false)
      expect(save).toHaveBeenNthCalledWith(1, { label: "ahoj" }, true)
      expect(save).toHaveBeenNthCalledWith(2, { label: "ahoj" }, false)
      expect(onSuccess).toHaveBeenCalledOnce()
      dispose()
    })
  })

  it("submit: field error from dry-run stops commit", async () => {
    await createRoot(async (dispose) => {
      const save = vi
        .fn<(d: Data, validate: boolean) => Promise<SaveResult>>()
        .mockResolvedValue({ fieldErrors: { label: "required" } })
      const form = createFormStore<Data>({ defaultData: { label: "" }, save })

      await form.submit()

      // only validation-only ran; no commit
      expect(save).toHaveBeenCalledTimes(1)
      expect(save).toHaveBeenCalledWith({ label: "" }, true)
      dispose()
    })
  })
})
