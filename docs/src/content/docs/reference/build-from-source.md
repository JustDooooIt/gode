---
title: Build from Source
description: Build Gode locally and understand the repository build outputs.
---

Most users should install a release package. Build from source when you are developing Gode itself, testing a patch, or producing internal binaries for a controlled platform matrix.

## Prerequisites

Initialize submodules:

```bash
git submodule update --init --recursive
```

Install generator dependencies:

```bash
python -m pip install -r generator/requirements.txt
```

Prepare `libnode` in the expected layout:

```text
libnode/
  include/
  windows/x64/libnode.lib
  linux/x64/libnode.a
  macos/arm64/libnode.a
  macos/x64/libnode.a
  ios/arm64/libnode.a
  android/arm64/libnode.a
```

## Fast path

Windows:

```powershell
./shell/build-windows.ps1
```

Linux:

```bash
./shell/build-linux.sh
```

These commands default to `Debug`, use incremental builds, choose an available CMake generator automatically, and output binaries into the example addon. Runtime libraries are written under `binary/<platform>/<arch>/`; desktop builds also produce the `gode_node` helper in the same runtime directory for native npm package probes, plus the editor-only library under `binary/editor/<platform>/<arch>/`.

## Common options

| Option | Purpose |
| --- | --- |
| `--config Release` / `-Configuration Release` | Build a release binary. |
| `--jobs 8` / `-Jobs 8` | Control build parallelism. |
| `--fresh` / `-Fresh` | Reconfigure while preserving build outputs where possible. |
| `--clean` / `-Clean` | Delete the current platform, architecture, and config build directory. |
| `--skip-codegen` / `-SkipCodegen` | Skip code generation when only native source changed. |

## Build output

Build directories are separated by platform, architecture, and configuration:

```text
build/<platform>/<arch>/<config>/
```

Runtime plugin binaries are written to:

```text
example/addons/gode/binary/<platform>/<arch>/
```

Desktop builds also place the `gode_node` helper in this directory. It is used by exported games when npm native packages need an isolated Node-compatible probe process.

Desktop builds also write the development-only editor extension to:

```text
example/addons/gode/binary/editor/<platform>/<arch>/
```

Debug and Release builds for the same platform and architecture overwrite the same example addon binaries. This makes the sample project load the most recent build.

## CI behavior

The repository CI builds `Release`, passes fresh reconfiguration flags, packages generated bindings, and uploads platform artifacts. Local development defaults to incremental builds for faster iteration.
