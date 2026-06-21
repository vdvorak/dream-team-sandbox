import { createSignal } from "solid-js"
import { createStore, reconcile } from "solid-js/store"

// createFormStore — canonical write binding (rules/frontend.md §Form model).
// ONE central store = single source of truth for data/errors/touched/submitting/dirty.
// Validation = dry-run of the same persistence operation (rules §Write-flow); the UI binds
// to a field via a thin Field abstraction that does not know the internal storage.
//
// This skeleton supports top-level field keys (readability). Deep paths =
// an extension when a feature needs it.

export interface Field<T> {
  readonly value: T
  set: (value: T) => void
  blur: () => void
  readonly error: string | undefined
}

// Result of the persistence operation. fieldErrors = field-level; error = global/throw.
export interface SaveResult {
  fieldErrors?: Record<string, string>
  error?: unknown
}

export interface FormConfig<TData extends object> {
  defaultData: TData // baseline for create
  // validate=true → dry-run (server ONLY validates, no side effects); false → commit.
  save: (data: TData, validate: boolean) => Promise<SaveResult>
  load?: () => Promise<TData> // optional loader for the edit flow (returns the editable subtree)
  onSuccess?: (data: TData) => void
  debounceMs?: number // live validation (default 400)
}

export function createFormStore<TData extends object>(config: FormConfig<TData>) {
  const [state, setState] = createStore({
    data: structuredClone(config.defaultData) as TData,
    errors: {} as Record<string, string>,
    touched: {} as Record<string, true>,
  })
  const [submitting, setSubmitting] = createSignal(false)
  const [loading, setLoading] = createSignal(false)
  const [globalError, setGlobalError] = createSignal<string | null>(null)

  let baseline = JSON.stringify(config.defaultData)
  let timer: ReturnType<typeof setTimeout> | undefined

  const applyErrors = (r: SaveResult) => setState("errors", reconcile(r.fieldErrors ?? {}))

  // Dry-run validation — no side effects on the server (rules §Write-flow).
  async function validate(): Promise<boolean> {
    const r = await config.save(state.data, true)
    applyErrors(r)
    return Object.keys(r.fieldErrors ?? {}).length === 0
  }

  function scheduleValidate() {
    clearTimeout(timer)
    timer = setTimeout(() => void validate(), config.debounceMs ?? 400)
  }

  function field<K extends keyof TData & string>(key: K): Field<TData[K]> {
    return {
      get value() {
        return state.data[key]
      },
      set: (value) => {
        setState("data", key as never, value as never)
        scheduleValidate()
      },
      blur: () => {
        clearTimeout(timer)
        setState("touched", key, true)
        void validate()
      },
      get error() {
        return state.touched[key] ? state.errors[key] : undefined
      },
    }
  }

  async function submit(): Promise<void> {
    clearTimeout(timer)
    setGlobalError(null)
    setSubmitting(true)
    try {
      // 1) validation-only dry-run; stop on errors (the server re-validates anyway)
      if (!(await validate())) {
        return
      }
      // 2) commit
      const r = await config.save(state.data, false)
      if (r.fieldErrors && Object.keys(r.fieldErrors).length > 0) {
        applyErrors(r)
        return
      }
      if (r.error) {
        setGlobalError("common.error")
        return
      }
      baseline = JSON.stringify(state.data)
      config.onSuccess?.(state.data)
    } finally {
      setSubmitting(false)
    }
  }

  async function loadInitial(): Promise<void> {
    if (!config.load) {
      return
    }
    setLoading(true)
    try {
      const data = await config.load()
      setState("data", reconcile(data))
      baseline = JSON.stringify(data)
    } finally {
      setLoading(false)
    }
  }

  return {
    field,
    submit,
    loadInitial,
    submitting,
    loading,
    globalError,
    isDirty: () => JSON.stringify(state.data) !== baseline,
  }
}
