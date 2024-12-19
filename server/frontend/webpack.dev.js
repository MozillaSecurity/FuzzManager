const { merge } = require("webpack-merge");
const { DefinePlugin } = require("webpack");
const common = require("./webpack.common.js");

module.exports = merge(common, {
  mode: "development",
  plugins: [
    // ... other plugins ...
    new DefinePlugin({
      __VUE_OPTIONS_API__: true,
      __VUE_PROD_DEVTOOLS__: true, // Enable devtools in development
      __VUE_PROD_HYDRATION_MISMATCH_DETAILS__: true, // Enable hydration warnings in development
    }),
  ],
});
