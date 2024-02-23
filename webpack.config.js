const path = require("path");
const BundleTracker = require('webpack-bundle-tracker');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');

module.exports = {
  mode: process.env.ENV == "production" ? "production" : "development",
  context: __dirname,
  entry: {
    main: [
      './common/static/common/js/application.js',
      './common/static/common/scss/application.scss'
    ]
  },
  output: {
    // Where Webpack will compile assets to
    path: path.resolve('./static/webpack_bundles/'),
    // Where the compiled assets will be accessed through Django
    // (they are picked up by `collectstatic`)
    publicPath: '/assets/webpack_bundles/',
    filename: "[name]-[hash].js"
  },

  plugins: [
    new BundleTracker({ filename: './webpack-stats.json' }),
    new MiniCssExtractPlugin({
      filename: '[name]-[hash].css',
      chunkFilename: '[id]-[hash].css'
    })
  ],

  module: {
    rules: [
      // Use file-loader to handle image assets
      {
        test: /\.(png|jpe?g|gif|woff2?|svg|ico)$/i,
        use: [
          {
            loader: 'file-loader',
            options: {
              // Note: `django-webpack-loader`'s `webpack_static` tag does
              //       not yet pick up versioned assets, so we need to
              //       generate image assets without a hash in the
              //       filename.
              // c.f.: https://github.com/owais/django-webpack-loader/issues/138
              name: '[name].[ext]',
            }
          }
        ]
      },

      // Babel
      {
        test: /\.m?js$/,
        exclude: /node_modules/,
        use: {
          loader: "babel-loader",
          options: {
            presets: ["@babel/preset-env", "@babel/react"]
          }
        }
      },

      // Extract compiled SCSS separately from JS
      {
        test: /\.s[ac]ss$/i,
        use: [
          {
            loader: MiniCssExtractPlugin.loader
          },
          'css-loader',
          {
            loader: 'sass-loader',
            options: {
              sassOptions: {
                includePaths: [
                  'additional_codes/static/additional_codes/scss',
                  'footnotes/static/footnotes/scss',
                  'geo_areas/static/geo_areas/scss',
                  'measures/static/measures/scss',
                  'publishing/static/publishing/scss',
                  'regulations/static/regulations/scss',
                  'workbaskets/static/workbaskets/scss',
                  'reference_documents/static/reference_documents/scss',
                ],
              },
            },
          },
        ]
      }
    ]
  },

  resolve: {
    modules: ['node_modules'],
    extensions: ['.js', '.scss']
  }
}
