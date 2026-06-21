import { render } from "solid-js/web"
import { Route, Router } from "@solidjs/router"

import BackendStatusBanner from "@/components/BackendStatusBanner"
import AppShell from "@/components/layout/AppShell"
import ExamplePage from "@/pages/example/ExamplePage"
import "@/i18n" // initializes i18next (i18n from the first line)
import "./index.css"

const App = () => (
  <>
    <BackendStatusBanner />
    <Router root={(props) => <AppShell>{props.children}</AppShell>}>
      <Route path="/" component={ExamplePage} />
    </Router>
  </>
)

render(() => <App />, document.getElementById("root")!)
