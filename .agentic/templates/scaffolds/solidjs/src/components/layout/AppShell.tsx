import { A } from "@solidjs/router"
import type { ParentComponent } from "solid-js"

import { t } from "@/i18n"

import styles from "./AppShell.module.css"

const AppShell: ParentComponent = (props) => (
  <div class={styles.shell}>
    <nav class={styles.sidebar}>
      <A href="/" class={styles.navLink}>
        {t("nav.examples")}
      </A>
    </nav>
    <main class={styles.main}>{props.children}</main>
  </div>
)

export default AppShell
