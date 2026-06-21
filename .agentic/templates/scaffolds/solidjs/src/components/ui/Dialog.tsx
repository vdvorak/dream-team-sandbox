import { Dialog as KDialog } from "@kobalte/core/dialog"
import type { JSX } from "solid-js"

import styles from "./Dialog.module.css"

interface DialogProps {
  triggerLabel: string
  title: string
  children: JSX.Element
}

// Wrapper over the Kobalte Dialog: behavior + a11y (focus trap, escape, ARIA) come
// from Kobalte; the visual is driven by tokens via Dialog.module.css. No hand-written a11y.
export default function Dialog(props: DialogProps) {
  return (
    <KDialog>
      <KDialog.Trigger class={styles.trigger}>{props.triggerLabel}</KDialog.Trigger>
      <KDialog.Portal>
        <KDialog.Overlay class={styles.overlay} />
        <div class={styles.positioner}>
          <KDialog.Content class={styles.content}>
            <KDialog.Title class={styles.title}>{props.title}</KDialog.Title>
            <div class={styles.body}>{props.children}</div>
            <KDialog.CloseButton class={styles.close}>Close</KDialog.CloseButton>
          </KDialog.Content>
        </div>
      </KDialog.Portal>
    </KDialog>
  )
}
