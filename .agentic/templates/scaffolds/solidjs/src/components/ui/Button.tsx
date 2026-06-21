import { type JSX, splitProps } from "solid-js"

import styles from "./Button.module.css"

interface ButtonProps extends JSX.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary"
}

export default function Button(props: ButtonProps) {
  const [local, rest] = splitProps(props, ["variant", "class", "children"])
  const variantClass = local.variant === "secondary" ? styles.secondary : styles.primary
  return (
    <button class={`${styles.button} ${variantClass} ${local.class ?? ""}`} {...rest}>
      {local.children}
    </button>
  )
}
