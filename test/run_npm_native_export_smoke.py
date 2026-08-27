#!/usr/bin/env python3
import argparse
import json
import os
import pathlib
import re
import shutil
import stat
import subprocess
import sys
import textwrap
import time
import urllib.error
import urllib.request
import zipfile

from run_godot_smoke import captured_output_text, non_leak_error_lines, resolve_godot
from run_npm_native_smoke import (
	DEFAULT_HELPER_MARKER,
	DEFAULT_MARKER,
	DEFAULT_PACKAGE_VERSION,
	ROOT,
	host_platform,
	install_npm_dependencies,
	prepare_project,
	run_command,
)


TEMPLATE_SENTINELS = {
	"windows": "windows_release_x86_64.exe",
	"linux": "linux_release.x86_64",
	"macos": "macos.zip",
}
DOWNLOAD_ATTEMPTS = 5
DOWNLOAD_TIMEOUT_SECONDS = 60
RETRYABLE_HTTP_STATUS = {408, 425, 429, 500, 502, 503, 504}


def godot_string(value):
	return json.dumps(str(value).replace("\\", "/"))


def version_key_from_tag(version):
	return version.removeprefix("Godot_v").replace("-", ".")


def tag_from_version_text(version_text):
	first_line = version_text.strip().splitlines()[0]
	first_token = first_line.split()[0]
	match = re.match(r"(?P<number>[0-9]+\.[0-9]+(?:\.[0-9]+)?)[.-](?P<channel>stable|dev|beta[0-9]*|rc[0-9]*)", first_token)
	if match:
		return f"{match.group('number')}-{match.group('channel')}"
	return first_token.replace(".stable", "-stable")


def resolve_template_version(godot, explicit_version):
	if explicit_version:
		return explicit_version, version_key_from_tag(explicit_version)
	version_output = run_command([str(godot), "--version"], ROOT, 30)
	tag = tag_from_version_text(version_output)
	return tag, version_key_from_tag(tag)


def export_templates_root():
	override = os.environ.get("GODE_EXPORT_TEMPLATES_DIR")
	if override:
		return pathlib.Path(override).expanduser()
	home = pathlib.Path.home()
	if sys.platform == "darwin":
		return home / "Library/Application Support/Godot/export_templates"
	if os.name == "nt":
		appdata = os.environ.get("APPDATA")
		if appdata:
			return pathlib.Path(appdata) / "Godot/export_templates"
		return home / "AppData/Roaming/Godot/export_templates"
	xdg_data_home = os.environ.get("XDG_DATA_HOME")
	if xdg_data_home:
		return pathlib.Path(xdg_data_home) / "godot/export_templates"
	return home / ".local/share/godot/export_templates"


def should_retry_download_error(exc):
	if isinstance(exc, urllib.error.HTTPError):
		return exc.code in RETRYABLE_HTTP_STATUS
	return isinstance(exc, (TimeoutError, urllib.error.URLError, OSError))


def download_file(url, destination):
	print(f"[gode-npm-native-export-smoke] Downloading {url}")
	destination.parent.mkdir(parents=True, exist_ok=True)
	for attempt in range(1, DOWNLOAD_ATTEMPTS + 1):
		try:
			with urllib.request.urlopen(url, timeout=DOWNLOAD_TIMEOUT_SECONDS) as response, destination.open("wb") as output:
				shutil.copyfileobj(response, output)
			return
		except Exception as exc:
			if destination.exists():
				destination.unlink()
			if attempt == DOWNLOAD_ATTEMPTS or not should_retry_download_error(exc):
				raise
			sleep_seconds = attempt * 2
			print(
				f"[gode-npm-native-export-smoke] Download failed on attempt {attempt}/{DOWNLOAD_ATTEMPTS}: {exc}. "
				f"Retrying in {sleep_seconds} seconds...",
				file=sys.stderr,
			)
			time.sleep(sleep_seconds)


def ensure_export_templates(godot, args):
	gode_platform, _ = host_platform()
	tag, version_key = resolve_template_version(godot, args.godot_version)
	template_dir = export_templates_root() / version_key
	sentinel = template_dir / TEMPLATE_SENTINELS[gode_platform]
	if sentinel.is_file():
		print(f"[gode-npm-native-export-smoke] Export templates ready: {template_dir}")
		return template_dir
	if not args.install_export_templates:
		raise FileNotFoundError(
			f"Godot export template is missing: {sentinel}. "
			"Install export templates or pass --install-export-templates."
		)

	archive_name = f"Godot_v{tag}_export_templates.tpz"
	download_root = pathlib.Path(args.template_download_dir).resolve()
	archive_path = download_root / archive_name
	extract_dir = download_root / "extract"
	if extract_dir.exists():
		shutil.rmtree(extract_dir)
	extract_dir.mkdir(parents=True, exist_ok=True)
	if not archive_path.is_file():
		download_file(f"https://github.com/godotengine/godot/releases/download/{tag}/{archive_name}", archive_path)

	with zipfile.ZipFile(archive_path) as zip_file:
		zip_file.extractall(extract_dir)

	source_dir = extract_dir / "templates"
	if not source_dir.is_dir():
		raise FileNotFoundError(f"Godot export template archive has no templates directory: {archive_path}")

	template_dir.mkdir(parents=True, exist_ok=True)
	for source in source_dir.iterdir():
		if source.is_file():
			shutil.copy2(source, template_dir / source.name)

	if not sentinel.is_file():
		raise FileNotFoundError(f"Godot export template was not installed: {sentinel}")
	print(f"[gode-npm-native-export-smoke] Export templates installed: {template_dir}")
	return template_dir


def common_preset(name, platform_name, export_path):
	return textwrap.dedent(
		f"""
		[preset.0]

		name={godot_string(name)}
		platform={godot_string(platform_name)}
		runnable=true
		dedicated_server=false
		custom_features=""
		export_filter="all_resources"
		include_filter="scripts/fork_probe_child.cjs"
		exclude_filter=""
		export_path={godot_string(export_path)}
		patches=PackedStringArray()
		patch_delta_encoding=false
		patch_delta_compression_level_zstd=19
		patch_delta_min_reduction=0.1
		patch_delta_include_filters="*"
		patch_delta_exclude_filters=""
		encryption_include_filters=""
		encryption_exclude_filters=""
		seed=0
		encrypt_pck=false
		encrypt_directory=false
		script_export_mode=2

		[preset.0.options]
		"""
	).lstrip()


def write_macos_entitlements(export_dir):
	entitlements_path = export_dir / "gode-npm-native-smoke.entitlements"
	entitlements_path.write_text(
		textwrap.dedent(
			"""
			<?xml version="1.0" encoding="UTF-8"?>
			<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "https://www.apple.com/DTDs/PropertyList-1.0.dtd">
			<plist version="1.0">
			<dict>
				<key>com.apple.security.cs.allow-jit</key>
				<true/>
				<key>com.apple.security.cs.allow-unsigned-executable-memory</key>
				<true/>
				<key>com.apple.security.cs.disable-library-validation</key>
				<true/>
			</dict>
			</plist>
			"""
		).lstrip(),
		encoding="utf-8",
	)
	return entitlements_path


def export_config(export_dir, macos_entitlements_path=None):
	gode_platform, _ = host_platform()
	if gode_platform == "windows":
		export_path = export_dir / "gode_npm_native_export_smoke.exe"
		preset = common_preset("Windows", "Windows Desktop", export_path) + textwrap.dedent(
			"""
			custom_template/debug=""
			custom_template/release=""
			binary_format/architecture="x86_64"
			binary_format/embed_pck=true
			codesign/enable=false
			application/modify_resources=false
			application/company_name="GodotHub"
			application/product_name="Gode Npm Native Smoke"
			application/file_description="Gode npm native export smoke"
			application/copyright=""
			application/trademarks=""
			"""
		)
		return "Windows", export_path, preset
	if gode_platform == "macos":
		if macos_entitlements_path is None:
			macos_entitlements_path = write_macos_entitlements(export_dir)
		export_path = export_dir / "gode_npm_native_export_smoke.zip"
		preset = common_preset("macOS", "macOS", export_path) + textwrap.dedent(
			f"""
			custom_template/debug=""
			custom_template/release=""
			binary_format/architecture="universal"
			application/name="Gode Npm Native Smoke"
			application/info="Gode npm native export smoke"
			application/icon=""
			application/bundle_identifier="com.godothub.gode.npmnativeexportsmoke"
			application/signature=""
			application/app_category="public.app-category.games"
			application/short_version="1.0"
			application/version="1.0"
			application/copyright=""
			display/high_res=true
			codesign/codesign=3
			codesign/identity=""
			codesign/certificate_file=""
			codesign/certificate_password=""
			codesign/entitlements/custom_file=""
			codesign/entitlements/allow_jit_code_execution=false
			codesign/entitlements/allow_unsigned_executable_memory=false
			codesign/entitlements/allow_dyld_environment_variables=false
			codesign/entitlements/disable_library_validation=false
			codesign/entitlements/audio_input=false
			codesign/entitlements/camera=false
			codesign/entitlements/location=false
			codesign/entitlements/address_book=false
			codesign/entitlements/calendars=false
			codesign/entitlements/photos_library=false
			codesign/entitlements/apple_events=false
			codesign/entitlements/debugging=false
			codesign/entitlements/app_sandbox/enabled=false
			codesign/entitlements/app_sandbox/network_server=false
			codesign/entitlements/app_sandbox/network_client=false
			codesign/entitlements/app_sandbox/device_usb=false
			codesign/entitlements/app_sandbox/device_bluetooth=false
			codesign/entitlements/app_sandbox/helper_executables=[]
			codesign/custom_options=PackedStringArray("--options", "runtime", "--entitlements", {godot_string(macos_entitlements_path)})
			notarization/notarization=0
			notarization/apple_id_name=""
			notarization/apple_id_password=""
			notarization/api_uuid=""
			notarization/api_key=""
			notarization/api_key_id=""
			"""
		)
		return "macOS", export_path, preset
	if gode_platform == "linux":
		export_path = export_dir / "gode_npm_native_export_smoke.x86_64"
		preset = common_preset("Linux", "Linux/X11", export_path) + textwrap.dedent(
			"""
			custom_template/debug=""
			custom_template/release=""
			binary_format/architecture="x86_64"
			binary_format/embed_pck=true
			texture_format/bptc=true
			texture_format/s3tc=true
			texture_format/etc=false
			texture_format/etc2=false
			ssh_remote_deploy/enabled=false
			ssh_remote_deploy/host="user@host_ip"
			ssh_remote_deploy/port="22"
			ssh_remote_deploy/extra_args_ssh=""
			ssh_remote_deploy/extra_args_scp=""
			ssh_remote_deploy/run_script="#!/usr/bin/env bash"
			ssh_remote_deploy/cleanup_script="#!/usr/bin/env bash"
			"""
		)
		return "Linux", export_path, preset
	raise RuntimeError(f"Unsupported export smoke platform: {gode_platform}")


def write_export_preset(project, export_dir):
	export_dir.mkdir(parents=True, exist_ok=True)
	macos_entitlements_path = write_macos_entitlements(export_dir) if host_platform()[0] == "macos" else None
	preset_name, export_path, preset_text = export_config(export_dir, macos_entitlements_path)
	(project / "export_presets.cfg").write_text(preset_text, encoding="utf-8")
	return preset_name, export_path


def make_executable(path):
	if os.name == "nt":
		return
	mode = path.stat().st_mode
	path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def exported_executable(export_path):
	gode_platform, _ = host_platform()
	if gode_platform == "macos":
		extract_dir = export_path.parent / "macos-run"
		if extract_dir.exists():
			shutil.rmtree(extract_dir)
		extract_dir.mkdir(parents=True, exist_ok=True)
		with zipfile.ZipFile(export_path) as zip_file:
			zip_file.extractall(extract_dir)
		apps = sorted(extract_dir.glob("*.app"))
		if not apps:
			raise FileNotFoundError(f"Exported macOS app bundle was not found in {extract_dir}")
		macos_dir = apps[0] / "Contents/MacOS"
		executables = [path for path in sorted(macos_dir.iterdir()) if path.is_file()]
		if not executables:
			raise FileNotFoundError(f"Exported macOS app executable was not found in {macos_dir}")
		make_executable(executables[0])
		return executables[0]
	if not export_path.is_file():
		raise FileNotFoundError(f"Exported executable was not found: {export_path}")
	make_executable(export_path)
	return export_path


def run_process(command, cwd, timeout, env=None):
	print("[gode-npm-native-export-smoke] " + " ".join(str(part) for part in command))
	result = subprocess.run(
		command,
		cwd=cwd,
		stdout=subprocess.PIPE,
		stderr=subprocess.STDOUT,
		text=True,
		errors="replace",
		timeout=timeout,
		check=False,
		env=env,
	)
	if result.stdout:
		print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
	return result.returncode, result.stdout


def run_export_smoke(args):
	godot = resolve_godot(args.godot)
	project = prepare_project(args)
	install_npm_dependencies(project, args.skip_npm_install, args.npm_install_timeout)
	ensure_export_templates(godot, args)

	export_dir = (ROOT / args.export_dir).resolve()
	if args.fresh_export and export_dir.exists():
		shutil.rmtree(export_dir)
	preset_name, export_path = write_export_preset(project, export_dir)

	export_output = run_command(
		[str(godot), "--headless", "--quiet", "--path", str(project), "--export-release", preset_name, str(export_path)],
		ROOT,
		args.export_timeout,
	)
	executable = exported_executable(export_path)
	marker_file = export_dir / "runtime-marker.log"
	if marker_file.exists():
		marker_file.unlink()

	env = os.environ.copy()
	env["GODE_NPM_NATIVE_SMOKE_MARKER_FILE"] = str(marker_file)
	returncode, run_output = run_process([str(executable), "--headless", "--quiet"], export_path.parent, args.timeout, env=env)
	marker_output = marker_file.read_text(encoding="utf-8") if marker_file.is_file() else ""
	if marker_output:
		print(marker_output, end="" if marker_output.endswith("\n") else "\n")

	combined_output = "\n".join([export_output, run_output, marker_output])
	failures = []
	if returncode != 0:
		failures.append(f"Exported game exited with code {returncode}")
	if DEFAULT_MARKER not in combined_output:
		failures.append(f"Expected marker was not found: {DEFAULT_MARKER}")
	if DEFAULT_HELPER_MARKER not in combined_output:
		failures.append(f"Expected marker was not found: {DEFAULT_HELPER_MARKER}")

	errors = non_leak_error_lines(combined_output)
	if errors:
		failures.append("Godot emitted non-leak ERROR lines:\n" + "\n".join(errors[:20]))

	if failures:
		for failure in failures:
			print(f"[gode-npm-native-export-smoke] FAIL: {failure}", file=sys.stderr)
		return 1

	print("[gode-npm-native-export-smoke] PASS")
	return 0


def build_parser():
	default_template_download = pathlib.Path(os.environ.get("RUNNER_TEMP", ROOT / "build")) / "godot-export-templates"
	parser = argparse.ArgumentParser(description="Export and run the npm native package Godot smoke project.")
	parser.add_argument("--godot", help="Path to the Godot executable. Defaults to GODOT_BIN or common install locations.")
	parser.add_argument("--godot-version", default=os.environ.get("GODOT_VERSION", ""), help="Godot release tag used to download export templates.")
	parser.add_argument("--addon", default="example/addons/gode", help="Addon directory to copy into the temporary project.")
	parser.add_argument("--work-dir", default="build/npm-native-export-smoke/node-llama-cpp", help="Temporary Godot project directory.")
	parser.add_argument("--export-dir", default="build/npm-native-export-smoke/exported", help="Directory for exported game artifacts.")
	parser.add_argument("--package-version", default=DEFAULT_PACKAGE_VERSION, help="node-llama-cpp version to install.")
	parser.add_argument("--timeout", type=int, default=180, help="Seconds before the exported game process is terminated.")
	parser.add_argument("--export-timeout", type=int, default=300, help="Seconds before the Godot export process is terminated.")
	parser.add_argument("--npm-install-timeout", type=int, default=420, help="Seconds before npm install is terminated.")
	parser.add_argument("--prepare-typescript-timeout", type=int, default=120, help="Seconds before TypeScript preparation is terminated.")
	parser.add_argument("--template-download-dir", default=str(default_template_download), help="Directory for downloaded export templates.")
	parser.add_argument("--install-export-templates", action="store_true", help="Download and install missing Godot export templates.")
	parser.add_argument("--skip-npm-install", action="store_true", help="Reuse an existing node_modules directory in the work directory.")
	parser.add_argument("--reuse", dest="fresh", action="store_false", help="Reuse the existing work directory instead of recreating it.")
	parser.add_argument("--reuse-export", dest="fresh_export", action="store_false", help="Reuse the existing export directory.")
	parser.set_defaults(fresh=True, fresh_export=True)
	return parser


def main():
	parser = build_parser()
	args = parser.parse_args()
	try:
		return run_export_smoke(args)
	except subprocess.TimeoutExpired as exc:
		print(f"[gode-npm-native-export-smoke] FAIL: command timed out after {exc.timeout} seconds", file=sys.stderr)
		output = captured_output_text(exc.stdout)
		if output:
			print(output, end="" if output.endswith("\n") else "\n")
		return 1
	except Exception as exc:
		print(f"[gode-npm-native-export-smoke] FAIL: {exc}", file=sys.stderr)
		return 1


if __name__ == "__main__":
	sys.exit(main())
