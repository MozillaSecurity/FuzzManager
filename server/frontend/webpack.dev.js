const { merge } = require('webpack-merge');
const common = require('./webpack.common.js');

module.exports = merge(common, {
    mode: 'development',
    devServer: {
        port: 8080,
        historyApiFallback: true,
        open: true,
        overlay: true,
        hot: true
    },
});