import tseslint from "typescript-eslint"

// Style-lint (ne formatter — to je prettier). Vynucuje pravidla, co prettier neumí:
// curly = vždy blokové tělo `if (…) { … }` (constitution §Standardy). Drž minimální
// a cílené; rozšiřuj vědomě.
export default tseslint.config(
  { ignores: ["node_modules", "dist", "src/api/schema.ts"] },
  {
    files: ["**/*.{ts,tsx}"],
    languageOptions: { parser: tseslint.parser },
    rules: {
      curly: ["error", "all"],
    },
  },
)
