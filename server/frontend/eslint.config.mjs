import pluginJs from "@eslint/js";
import prettier from "eslint-config-prettier";
import pluginJest from "eslint-plugin-jest";
import pluginPrettierRec from "eslint-plugin-prettier";
import pluginVue from "eslint-plugin-vue";
import globals from "globals";

export default [
  ...pluginVue.configs["flat/recommended"],
  { files: ["**/*.{js,mjs,cjs,vue}"] },
  { ignores: ["**/dist/**", "**/coverage/**", "**/node_modules/**"] },
  {
    languageOptions: {
      sourceType: "module",
      globals: {
        ...Object.fromEntries(
          Object.entries(globals.browser).map(([key, value]) => [
            key.trim(),
            value,
          ]),
        ),
        ...globals.jest,
        ...globals.node,
      },
      parserOptions: {
        ecmaVersion: "latest",
        sourceType: "module",
      },
      ecmaVersion: 2022,
    },
  },
  {
    rules: {
      ...pluginJs.configs.recommended.rules,
    },
  },
  {
    plugins: {
      vue: pluginVue,
    },
    rules: {
      ...pluginVue.configs["vue3-strongly-recommended"].rules,
    },
  },
  {
    rules: {
      ...prettier.rules,
    },
  },
  {
    plugins: {
      prettier: pluginPrettierRec,
    },
    rules: {
      "prettier/prettier": "error",
    },
  },
  {
    plugins: {
      jest: pluginJest,
    },
    rules: {
      "vue/max-attributes-per-line": "off",
      "vue/multi-word-component-names": "off",
      "vue/singleline-html-element-content-newline": "off",
      "vue/v-on-style": ["error", "shorthand"],
      "vue/no-unused-components": "off",
      "vue/valid-v-on": "off",
      "vue/v-on-handler-style": "off",
      "vue/v-on-event-hyphenation": "off",
      "vue/require-explicit-emits": "off",
    },
  },
  {
    files: ["**/__tests__/*.{j,t}s?(x)", "**/tests/unit/**/*.spec.{j,t}s?(x)"],
    rules: {
      "jest/no-disabled-tests": "warn",
      "jest/no-focused-tests": "error",
      "jest/no-identical-title": "error",
      "jest/prefer-to-have-length": "warn",
      "jest/valid-expect": "error",
    },
  },
];
