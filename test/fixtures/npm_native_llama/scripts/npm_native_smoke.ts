import { GD, Node } from "godot";
import { getLlama } from "node-llama-cpp";

interface GodeRequire {
	(id: string): any;
	resolve(id: string): string;
}

declare const require: GodeRequire;
declare const process: { env: Record<string, string | undefined> };
const fs = require("node:fs") as { appendFileSync: (path: string, data: string) => void };
const path = require("node:path") as { dirname: (path: string) => string; join: (...parts: string[]) => string };
const fork = require("node:child_process").fork as (...args: any[]) => any;

function recordMarker(line: string): void {
	const markerFile = process.env.GODE_NPM_NATIVE_SMOKE_MARKER_FILE;
	if (!markerFile) return;
	try {
		fs.appendFileSync(markerFile, line + "\n");
	} catch (_) {}
}

function runForkProbe(): Promise<string> {
	return new Promise((resolve, reject) => {
		const child = fork("res://scripts/fork_probe_child.cjs", [], {
			stdio: ["ignore", "pipe", "pipe", "ipc"],
		} as any);
		let settled = false;
		let stderr = "";
		let timer: any = null;
		const finish = (callback: () => void): void => {
			if (settled) return;
			settled = true;
			clearTimeout(timer);
			callback();
		};
		timer = setTimeout(() => {
			try { child.kill(); } catch (_) {}
			finish(() => reject(new Error("fork helper probe timed out")));
		}, 15000);
		(child.stderr as any)?.on("data", (chunk: unknown) => { stderr += String(chunk); });
		child.on("message", (message: any) => {
			if (message?.type !== "gode-fork-probe" || typeof message.execPath !== "string") return;
			const normalized = message.execPath.replace(/\\/g, "/");
			if (!/\/gode_node(?:\.exe)?$/i.test(normalized)) {
				finish(() => reject(new Error("fork did not use bundled gode_node helper: " + message.execPath)));
				return;
			}
			finish(() => resolve(message.execPath));
		});
		child.on("error", (error: Error) => finish(() => reject(error)));
		child.on("exit", (code: number | null) => {
			finish(() => reject(new Error("fork helper exited before reporting execPath: " + code + (stderr ? "\n" + stderr : ""))));
		});
	});
}

function runNodeModulesForkProbe(): Promise<string> {
	return new Promise((resolve, reject) => {
		const nodeLlamaMain = require.resolve("node-llama-cpp");
		const probePath = path.join(path.dirname(nodeLlamaMain), "bindings", "utils", "testBindingBinary.js");
		const child = fork(probePath, [], {
			stdio: ["ignore", "pipe", "pipe", "ipc"],
			env: { ...process.env, TEST_BINDING_CP: "true" },
		} as any);
		let settled = false;
		let stderr = "";
		let timer: any = null;
		const finish = (callback: () => void): void => {
			if (settled) return;
			settled = true;
			clearTimeout(timer);
			callback();
		};
		timer = setTimeout(() => {
			try { child.kill(); } catch (_) {}
			finish(() => reject(new Error("node_modules fork dependency probe timed out")));
		}, 15000);
		(child.stderr as any)?.on("data", (chunk: unknown) => { stderr += String(chunk); });
		child.on("message", (message: any) => {
			if (message?.type !== "ready") return;
			try { child.send({ type: "exit" }); } catch (_) {}
			finish(() => resolve(probePath));
		});
		child.on("error", (error: Error) => finish(() => reject(error)));
		child.on("exit", (code: number | null) => {
			finish(() => reject(new Error("node_modules fork dependency probe exited before ready: " + code + (stderr ? "\n" + stderr : ""))));
		});
	});
}

export default class NpmNativeSmoke extends Node {
	public async _ready(): Promise<void> {
		try {
			const forkExecPath = await runForkProbe();
			const forkMarker = "[GodeNpmNativeSmoke] fork helper OK: " + forkExecPath;
			GD.print(forkMarker);
			recordMarker(forkMarker);
			const nodeModulesForkPath = await runNodeModulesForkProbe();
			const nodeModulesForkMarker = "[GodeNpmNativeSmoke] node_modules fork dependency OK: " + nodeModulesForkPath;
			GD.print(nodeModulesForkMarker);
			recordMarker(nodeModulesForkMarker);
			GD.print("[GodeNpmNativeSmoke] before node-llama-cpp dryRun");
			const llama = await getLlama({ dryRun: true } as any);
			const llamaMarker = "[GodeNpmNativeSmoke] node-llama-cpp dryRun OK: " + typeof llama;
			GD.print(llamaMarker);
			recordMarker(llamaMarker);
			this.get_tree().quit(0);
		} catch (error) {
			const message = error instanceof Error ? error.stack || error.message : String(error);
			GD.push_error("[GodeNpmNativeSmoke] " + message);
			this.get_tree().quit(1);
		}
	}
}
