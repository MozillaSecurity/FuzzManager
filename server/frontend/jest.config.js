module.exports = {
  testEnvironment: "jsdom",
  moduleFileExtensions: ["vue", "js", "json", "node"],
  collectCoverageFrom: [
    "**/*.{js,jsx}",
    "**/*.vue",
    "!**/tests/**",
    "!**/coverage/**",
    "!**/dist/**",
    "!**/webpack.*.js",
  ],
  moduleNameMapper: {
    "^@/(.*)$": "<rootDir>/src/$1",
    d3: "<rootDir>/node_modules/d3/dist/d3.min.js",
    "\\.(css|less|scss|sass)$": "jest-transform-stub",
  },
  transformIgnorePatterns: [
    "/node_modules/(?!floating-vue|vue-loading-overlay)",
  ],
  transform: {
    "^.+\\.vue$": "@vue/vue3-jest",
    "^.+\\.(js)$": "babel-jest",
    ".+\\.(css|styl|less|sass|scss|png|jpg|ttf|woff|woff2)$":
      "jest-transform-stub",
  },
  testMatch: ["**/tests/**/*.[jt]s", "**/?(*.)+(spec|test).[jt]s"],
  testPathIgnorePatterns: [
    "<rootDir>/tests/setup.js",
    "<rootDir>/tests/fixtures.js",
  ],
  setupFiles: ["<rootDir>/tests/setup.js"],
  testEnvironmentOptions: {
    customExportConditions: ["node", "node-addons"],
  },
};
