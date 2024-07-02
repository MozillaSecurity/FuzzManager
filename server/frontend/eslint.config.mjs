import globals from "globals";
import pluginJs from "@eslint/js";
import pluginVue from "eslint-plugin-vue";
import pluginPrettier from "eslint-plugin-prettier/recommended";

export default [
  { files: ["**/*.{js,mjs,cjs,vue}"] },
  { ignores: ["**/dist/**"] },
  {
    languageOptions: {
      globals: {
        ...globals.browser,
        ...globals.jest,
        ...globals.node,
      },
    },
  },
  pluginJs.configs.recommended,
  ...pluginVue.configs["flat/vue2-strongly-recommended"],
  pluginPrettier,
  {
    rules: {
      "vue/html-self-closing": [
        1,
        {
          html: {
            normal: "never",
            void: "always",
          },
        },
      ],
      "vue/max-attributes-per-line": 0,
      "vue/multi-word-component-names": 0,
      "vue/singleline-html-element-content-newline": 0,
      "vue/v-on-style": [2, "longform"],
    },
  },
];
