const path = require('path');
const HtmlWebpackPlugin = require('html-webpack-plugin');
const CopyWebpackPlugin = require('copy-webpack-plugin');
const webpack = require('webpack');

module.exports = (env, argv) => {
  const isDevelopment = argv.mode === 'development';

  return {
    mode: isDevelopment ? 'development' : 'production',
    devtool: 'source-map', // Always enable for debugging
    experiments: {
      asyncWebAssembly: true,
    },
    entry: {
      popup: './src/popup/index.tsx',
      background: './src/background.ts',
      content: './src/content.ts',
      injected: './src/injected.ts',
    },
    output: {
      path: path.resolve(__dirname, 'dist'),
      filename: '[name].js',
      clean: true,
    },
    resolve: {
      extensions: ['.ts', '.tsx', '.js', '.jsx'],
      alias: {
        '@wallet-engine': path.resolve(__dirname, '../../src'),
        '@noble/ed25519': path.resolve(__dirname, 'node_modules/@noble/ed25519'),
      },
      fallback: {
        "crypto": require.resolve("crypto-browserify"),
        "stream": require.resolve("stream-browserify"),
        "buffer": require.resolve("buffer/"),
        "path": require.resolve("path-browserify"),
        "fs": false,
        "os": false,
        "vm": false,
      },
    },
    module: {
      rules: [
        {
          test: /\.tsx?$/,
          use: {
            loader: 'ts-loader',
            options: {
              transpileOnly: true, // Skip type checking during build
            }
          },
          exclude: /node_modules/,
        },
        {
          test: /\.css$/,
          use: ['style-loader', 'css-loader'],
        },
        {
          test: /\.(png|svg|jpg|jpeg|gif)$/i,
          type: 'asset/resource',
        },
      ],
    },
    plugins: [
      new webpack.DefinePlugin({
        'process.env': JSON.stringify({}),
        'process.version': JSON.stringify(''),
        'process.browser': JSON.stringify(true),
      }),
      new webpack.ProvidePlugin({
        Buffer: ['buffer', 'Buffer'],
      }),
      new HtmlWebpackPlugin({
        template: './public/popup.html',
        filename: 'popup.html',
        chunks: ['popup'],
      }),
      new CopyWebpackPlugin({
        patterns: [
          { from: 'manifest.json', to: 'manifest.json' },
          { from: 'public/assets', to: 'assets', noErrorOnMissing: false },
        ],
      }),
    ],
  };
};
