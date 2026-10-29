import { bindings, defineConfig, exports } from "cf/config";
import * as entrypoint from "./src/index.ts" with { type: "cf-worker" };

export default defineConfig(({ mode }) => ({
	accountId: "87b9bb14c33d5cf43f13b7cb7d776014",
	worker: {
		name: "valorai-prototype",
		compatibilityDate: "2026-10-28",
		entrypoint,
		workersDev: true,
		observability: { enabled: true, headSamplingRate: 0.1, redactQueryString: true },
		exports: { AuthCoordinator: exports.durableObject({ storage: "sqlite" }) },
		assets: { runWorkerFirst: ["/api/*"], notFoundHandling: "single-page-application" },
		env: {
			ASSETS: bindings.assets(),
			DB: bindings.d1({ id: "9186a9b0-dce5-442b-96ee-a3e67b4fe2b0", name: "valorai-prototype" }),
			AUTH: bindings.durableObject({ worker: "valorai-prototype", exportName: "AuthCoordinator" }),
			ENVIRONMENT: bindings.text(mode === "development" ? "development" : "production"),
			EMAIL_MODE: bindings.text("demo"),
			TURNSTILE_SITE_KEY: bindings.text(mode === "development" ? "" : "0x4AAAAAAFrPCsARbdASrFUU"),
			TURNSTILE_SECRET_KEY: mode === "development" ? undefined : bindings.secret(),
		},
	},
}));
