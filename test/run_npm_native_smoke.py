#!/usr/bin/env python3
import argparse
import json
import os
import pathlib
import platform
import shutil
import subprocess
import sys
import textwrap

from run_godot_smoke import captured_output_text, ensure_extension_list, non_leak_error_lines, resolve_godot


ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_MARKER = "[GodeNpmNativeSmoke] node-llama-cpp dryRun OK"
DEFAULT_EXTENSION = "res://addons/gode/binary/gode.gdextension"


def parse_node_major(version_text):
	version = version_text.strip()
	if version.startswith("v"):
		version = version[1:]
	major = version.split(".", 1)[0]
	if not major.isdigit():
		raise RuntimeError(f"Could not parse Node.js version: {version_text.strip()}")
	return int(major)


def host_platform():
	system = platform.system().lower()
	machine = platform.machine().lower()
	if system == "windows":
		gode_platform = "windows"
	elif system == "darwin":
		gode_platform = "macos"
	elif system == "linux":
		gode_platform = "linux"
	else:
		raise RuntimeError(f"Unsupported native smoke platform: {platform.system()}")

	if machine in ("amd64", "x86_64"):
		arch = "x64"
	elif machine in ("arm64", "aarch64"):
		arch = "arm64"
	else:
		raise RuntimeError(f"Unsupported native smoke architecture: {platform.machine()}")
	return gode_platform, arch


def run_command(command, cwd, timeout):
	print("[gode-npm-native-smoke] " + " ".join(str(part) for part in command))
	result = subprocess.run(
		command,
		cwd=cwd,
		stdout=subprocess.PIPE,
		stderr=subprocess.STDOUT,
		text=True,
		errors="replace",
		timeout=timeout,
		check=False,
	)
	if result.stdout:
		print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
	if result.returncode != 0:
		raise RuntimeError(f"Command exited with code {result.returncode}: {command[0]}")
	return result.stdout


def write_text(path, text):
	path.parent.mkdir(parents=True, exist_ok=True)
	path.write_text(textwrap.dedent(text).lstrip(), encoding="utf-8")


def copy_addon(source_addon, project):
	destination = project / "addons/gode"
	if destination.exists():
		shutil.rmtree(destination)
	destination.parent.mkdir(parents=True, exist_ok=True)
	shutil.copytree(source_addon, destination)
	return destination


def ensure_platform_binaries(addon_root):
	gode_platform, arch = host_platform()
	extension_binary = {
		"windows": f"binary/windows/{arch}/libgode.dll",
		"linux": f"binary/linux/{arch}/libgode.so",
		"macos": f"binary/macos/{arch}/libgode.dylib",
	}[gode_platform]
	required = [extension_binary]
	if gode_platform == "windows":
		required.append(f"binary/windows/{arch}/node.dll")

	missing = [path for path in required if not (addon_root / path).is_file()]
	if missing:
		raise FileNotFoundError("Missing built addon binary files: " + ", ".join(missing))


def ensure_typescript_compiler(addon_root, timeout):
	typescript_runtime = addon_root / "tsc/lib/typescript.js"
	if typescript_runtime.is_file():
		return

	output_directory = addon_root / "tsc"
	if os.name == "nt":
		script = ROOT / ".github/shell/prepare-typescript.ps1"
		powershell = shutil.which("pwsh") or shutil.which("powershell")
		if not powershell:
			raise FileNotFoundError("PowerShell was not found in PATH.")
		run_command([powershell, "-NoProfile", "-File", str(script), "-OutputDirectory", str(output_directory)], ROOT, timeout)
	else:
		script = ROOT / ".github/shell/prepare-typescript.sh"
		run_command([str(script), "--output-directory", str(output_directory)], ROOT, timeout)


def write_project(project, package_version):
	write_text(
		project / "project.godot",
		"""
		config_version=5

		[application]
		config/name="gode-npm-native-smoke"
		run/main_scene="res://main.tscn"
		config/features=PackedStringArray("4.7")

		[autoload]
		EventLoop="*res://addons/gode/runtime/event_loop.gd"

		[editor_plugins]
		enabled=PackedStringArray("res://addons/gode/plugin.cfg")

		[native_extensions]
		paths=["res://addons/gode/binary/gode.gdextension"]
		""",
	)
	write_text(
		project / "main.tscn",
		"""
		[gd_scene load_steps=2 format=3]

		[ext_resource type="Script" path="res://scripts/npm_native_smoke.ts" id="1_script"]

		[node name="NpmNativeSmoke" type="Node"]
		script = ExtResource("1_script")
		""",
	)
	write_text(
		project / "tsconfig.json",
		"""
		{
		  "compilerOptions": {
		    "target": "ES2022",
		    "module": "ESNext",
		    "moduleResolution": "Bundler",
		    "strict": true,
		    "isolatedModules": true,
		    "forceConsistentCasingInFileNames": true,
		    "useDefineForClassFields": true,
		    "experimentalDecorators": true,
		    "esModuleInterop": true,
		    "allowSyntheticDefaultImports": true,
		    "skipLibCheck": true,
		    "types": []
		  },
		  "include": ["**/*.ts", "**/*.d.ts"],
		  "exclude": ["node_modules", ".godot", ".gode", "addons/gode/tsc"]
		}
		""",
	)
	package_json = {
		"name": "gode-npm-native-smoke",
		"private": True,
		"type": "module",
		"dependencies": {
			"@types/node": "^24.0.0",
			"node-llama-cpp": package_version,
		},
	}
	write_text(project / "package.json", json.dumps(package_json, indent=2) + "\n")
	write_text(
		project / "scripts/npm_native_smoke.ts",
		"""
		import { GD, Node } from "godot";
		import { getLlama } from "node-llama-cpp";

		export default class NpmNativeSmoke extends Node {
			public async _ready(): Promise<void> {
				try {
					GD.print("[GodeNpmNativeSmoke] before node-llama-cpp dryRun");
					const llama = await getLlama({ dryRun: true } as any);
					GD.print("[GodeNpmNativeSmoke] node-llama-cpp dryRun OK: " + typeof llama);
					this.get_tree().quit(0);
				} catch (error) {
					const message = error instanceof Error ? error.stack || error.message : String(error);
					GD.push_error("[GodeNpmNativeSmoke] " + message);
					this.get_tree().quit(1);
				}
			}
		}
		""",
	)


def prepare_project(args):
	project = (ROOT / args.work_dir).resolve()
	if args.fresh and project.exists():
		shutil.rmtree(project)
	project.mkdir(parents=True, exist_ok=True)

	source_addon = (ROOT / args.addon).resolve()
	if not source_addon.exists():
		raise FileNotFoundError(f"Addon directory was not found: {source_addon}")

	addon_root = copy_addon(source_addon, project)
	ensure_platform_binaries(addon_root)
	ensure_typescript_compiler(addon_root, args.prepare_typescript_timeout)
	write_project(project, args.package_version)
	ensure_extension_list(project, DEFAULT_EXTENSION)
	return project


def run_smoke(args):
	godot = resolve_godot(args.godot)
	project = prepare_project(args)

	if not args.skip_npm_install:
		node = shutil.which("node")
		if not node:
			raise FileNotFoundError("node was not found in PATH.")
		node_version = run_command([node, "--version"], ROOT, args.npm_install_timeout)
		if parse_node_major(node_version) < 20:
			raise RuntimeError(
				"node-llama-cpp smoke requires Node.js 20 or newer; "
				f"found {node_version.strip()} at {node}."
			)
		npm = shutil.which("npm")
		if not npm:
			raise FileNotFoundError("npm was not found in PATH.")
		run_command([npm, "install", "--foreground-scripts"], project, args.npm_install_timeout)

	command = [str(godot), "--headless", "--path", str(project), "res://main.tscn"]
	output = run_command(command, ROOT, args.timeout)

	failures = []
	if args.marker not in output:
		failures.append(f"Expected marker was not found: {args.marker}")

	errors = non_leak_error_lines(output)
	if errors:
		failures.append("Godot emitted non-leak ERROR lines:\n" + "\n".join(errors[:20]))

	if failures:
		for failure in failures:
			print(f"[gode-npm-native-smoke] FAIL: {failure}", file=sys.stderr)
		return 1

	print("[gode-npm-native-smoke] PASS")
	return 0


def build_parser():
	parser = argparse.ArgumentParser(description="Run a Godot smoke test for npm native packages.")
	parser.add_argument("--godot", help="Path to the Godot executable. Defaults to GODOT_BIN or common install locations.")
	parser.add_argument("--addon", default="example/addons/gode", help="Addon directory to copy into the temporary project.")
	parser.add_argument("--work-dir", default="build/npm-native-smoke/node-llama-cpp", help="Temporary Godot project directory.")
	parser.add_argument("--package-version", default="3.19.1", help="node-llama-cpp version to install.")
	parser.add_argument("--marker", default=DEFAULT_MARKER, help="Output marker that proves the native package completed.")
	parser.add_argument("--timeout", type=int, default=120, help="Seconds before the Godot process is terminated.")
	parser.add_argument("--npm-install-timeout", type=int, default=420, help="Seconds before npm install is terminated.")
	parser.add_argument("--prepare-typescript-timeout", type=int, default=120, help="Seconds before TypeScript preparation is terminated.")
	parser.add_argument("--skip-npm-install", action="store_true", help="Reuse an existing node_modules directory in the work directory.")
	parser.add_argument("--reuse", dest="fresh", action="store_false", help="Reuse the existing work directory instead of recreating it.")
	parser.set_defaults(fresh=True)
	return parser


def main():
	parser = build_parser()
	args = parser.parse_args()
	try:
		return run_smoke(args)
	except subprocess.TimeoutExpired as exc:
		print(f"[gode-npm-native-smoke] FAIL: command timed out after {exc.timeout} seconds", file=sys.stderr)
		output = captured_output_text(exc.stdout)
		if output:
			print(output, end="" if output.endswith("\n") else "\n")
		return 1
	except Exception as exc:
		print(f"[gode-npm-native-smoke] FAIL: {exc}", file=sys.stderr)
		return 1


if __name__ == "__main__":
	sys.exit(main())
