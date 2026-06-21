import type { Field } from "@/components/createFormStore"

import styles from "./TextField.module.css"

// Connected field wrapper over createFormStore. Knows only the Field abstraction
// (value/set/blur/error), not the store mechanics. Pattern for further *Field wrappers.
interface TextFieldProps {
  field: Field<string>
  label: string
  type?: string
  disabled?: boolean
}

export default function TextField(props: TextFieldProps) {
  return (
    <label class={styles.field}>
      <span class={styles.label}>{props.label}</span>
      <input
        class={styles.input}
        type={props.type ?? "text"}
        value={props.field.value}
        disabled={props.disabled}
        aria-invalid={props.field.error ? "true" : undefined}
        onInput={(e) => props.field.set(e.currentTarget.value)}
        onBlur={() => props.field.blur()}
      />
      {props.field.error && <span class={styles.error}>{props.field.error}</span>}
    </label>
  )
}
