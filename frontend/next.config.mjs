/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Image de prod plus legere/fiable : ne copie que le sous-ensemble de
  // node_modules reellement utilise par le build, voir Dockerfile.
  output: "standalone",
  images: {
    remotePatterns: [
      { protocol: "http", hostname: "localhost" },
      { protocol: "http", hostname: "minio" },
    ],
  },
  // Docker Desktop sur Windows ne propage pas toujours fiablement les
  // evenements filesystem natifs (inotify) a travers le bind-mount vers le
  // conteneur : le watcher par defaut de webpack manque alors des
  // modifications de fichiers (observe en pratique -- il fallait redemarrer
  // le conteneur pour qu'un edit soit pris en compte). Le polling est plus
  // lent mais fiable partout.
  webpack: (config, { dev }) => {
    if (dev) {
      config.watchOptions = {
        poll: 800,
        aggregateTimeout: 300,
      };
    }
    return config;
  },
};

export default nextConfig;
