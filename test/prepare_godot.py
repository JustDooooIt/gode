#!/usr/bin/env python3
import argparse
import os
import pathlib
import platform
import shutil
import stat
import sys
import time
import urllib.error
import urllib.request
import zipfile


ROOT = pathlib.Path(__file__).resolve().parents[1]
DOWNLOAD_ATTEMPTS = 5
DOWNLOAD_TIMEOUT_SECONDS = 60
RETRYABLE_HTTP_STATUS = {408, 425, 429, 500, 502, 503, 504}


def host_platform():
	system = platform.system().lower()
	if system == "windows":
		return "windows"
	if system == "darwin":
		return "macos"
	if system == "linux":
		return "linux"
	raise RuntimeError(f"Unsupported Godot download platform: {platform.system()}")


def archive_name(version, gode_platform):
	if gode_platform == "windows":
		return f"Godot_v{version}_win64.exe.zip"
	if gode_platform == "macos":
		return f"Godot_v{version}_macos.universal.zip"
	if gode_platform == "linux":
		return f"Godot_v{version}_linux.x86_64.zip"
	raise RuntimeError(f"Unsupported Godot platform: {gode_platform}")


def should_retry_download_error(exc):
	if isinstance(exc, urllib.error.HTTPError):
		return exc.code in RETRYABLE_HTTP_STATUS
	return isinstance(exc, (TimeoutError, urllib.error.URLError, OSError))


def download_file(url, destination):
	print(f"[gode-prepare-godot] Downloading {url}")
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
				f"[gode-prepare-godot] Download failed on attempt {attempt}/{DOWNLOAD_ATTEMPTS}: {exc}. "
				f"Retrying in {sleep_seconds} seconds...",
				file=sys.stderr,
			)
			time.sleep(sleep_seconds)


def find_godot_executable(root, gode_platform):
	if gode_platform == "windows":
		patterns = ["**/*console*.exe", "**/Godot*.exe"]
	elif gode_platform == "macos":
		patterns = ["**/Godot.app/Contents/MacOS/Godot"]
	else:
		patterns = ["**/Godot*linux*.x86_64", "**/Godot*.x86_64"]

	for pattern in patterns:
		for candidate in sorted(root.glob(pattern)):
			if candidate.is_file():
				return candidate
	raise FileNotFoundError(f"Godot executable was not found under {root}")


def make_executable(path):
	if os.name == "nt":
		return
	mode = path.stat().st_mode
	path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def append_github_env(name, value):
	github_env = os.environ.get("GITHUB_ENV")
	if not github_env:
		return
	with open(github_env, "a", encoding="utf-8") as env_file:
		env_file.write(f"{name}={value}\n")


def prepare_godot(args):
	gode_platform = host_platform()
	output_dir = pathlib.Path(args.output_dir).resolve()
	archive = archive_name(args.version, gode_platform)
	archive_path = output_dir / archive
	extract_dir = output_dir / "editor"

	if args.fresh and extract_dir.exists():
		shutil.rmtree(extract_dir)
	extract_dir.mkdir(parents=True, exist_ok=True)

	if args.fresh or not archive_path.is_file():
		url = f"https://github.com/godotengine/godot/releases/download/{args.version}/{archive}"
		download_file(url, archive_path)

	with zipfile.ZipFile(archive_path) as zip_file:
		zip_file.extractall(extract_dir)

	godot = find_godot_executable(extract_dir, gode_platform)
	make_executable(godot)
	append_github_env("GODOT_BIN", godot.as_posix())
	print(f"[gode-prepare-godot] GODOT_BIN={godot}")
	return 0


def build_parser():
	default_output = pathlib.Path(os.environ.get("RUNNER_TEMP", ROOT / "build")) / "godot"
	parser = argparse.ArgumentParser(description="Download the Godot editor used by CI smoke tests.")
	parser.add_argument("--version", required=True, help="Godot release tag, for example 4.7-stable.")
	parser.add_argument("--output-dir", default=str(default_output), help="Directory for the downloaded editor archive.")
	parser.add_argument("--reuse", dest="fresh", action="store_false", help="Reuse an existing extracted editor directory.")
	parser.set_defaults(fresh=True)
	return parser


def main():
	parser = build_parser()
	args = parser.parse_args()
	try:
		return prepare_godot(args)
	except Exception as exc:
		print(f"[gode-prepare-godot] FAIL: {exc}", file=sys.stderr)
		return 1


if __name__ == "__main__":
	sys.exit(main())
