import { cloudflare } from "@cloudflare/vite-plugin";
import { defineConfig } from "vite";

export default defineConfig({
	publicDir: "../dist",
	server: { port: 8787, host: "127.0.0.1", strictPort: true },
	plugins: [cloudflare()],
});
