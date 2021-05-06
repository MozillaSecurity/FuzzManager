const path = require('path')
const { VueLoaderPlugin } = require('vue-loader')

module.exports = {
    mode: 'development',
    entry: path.join(__dirname, 'src', 'main.js'),

    output: {
        filename: '[name].js',
        path: path.resolve(__dirname, 'dist'),
        publicPath: '',
    },

    plugins: [
        new VueLoaderPlugin(),
    ],

    module: {
        rules: [
            {
                test: /\.vue$/,
                loader: "vue-loader",
            }
        ]
    },

    resolve: {
        alias: {
           vue: 'vue/dist/vue.js'
        }
    }
}