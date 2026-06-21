import tseslint from "typescript-eslint"

// Style-lint (ne formatter — to je prettier). curly = vždy blokové tělo `if (…) { … }`
// (constitution §Standardy). Minimální a cílené; rozšiřuj vědomě.
export default tseslint.config(
  { ignores: ["node_modules", "out", "dist"] },
  {
    files: ["**/*.{ts,tsx}"],
    languageOptions: { parser: tseslint.parser },
    rules: {
      curly: ["error", "all"],
    },
  },
)
