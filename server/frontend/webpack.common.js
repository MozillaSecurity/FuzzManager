const path = require("path");
const MiniCssExtractPlugin = require("mini-css-extract-plugin");
const { VueLoaderPlugin } = require("vue-loader");

module.exports = {
  mode: "development",
  entry: path.join(__dirname, "src", "main.js"),

  output: {
    filename: "[name].js",
    path: path.resolve(__dirname, "dist"),
    publicPath: "",
  },

  plugins: [new MiniCssExtractPlugin(), new VueLoaderPlugin()],

  module: {
    rules: [
      {
        test: /\.vue$/,
        loader: "vue-loader",
      },
      {
        test: /\.css$/,
        use: [MiniCssExtractPlugin.loader, "css-loader"],
      },
    ],
  },

  resolve: {
    alias: {
      handlebars: "handlebars/dist/handlebars.min.js",
      vue: "vue/dist/vue.js",
    },
  },
};
