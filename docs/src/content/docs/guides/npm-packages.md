---
title: Using NPM
description: Use npm dependencies from a Godot project root while keeping export behavior explicit and reproducible.
---

Gode can resolve npm packages from the Godot project root. This capability is enabled explicitly: a project is treated as an external-dependency project only when the root contains `package.json` or `node_modules`.

## When to add dependencies

Add npm packages only when they provide real value: data formats, networking helpers, deterministic simulation tools, validation logic, libraries shared with a backend, or runtime content pipelines.

Do not add a package for a very small gameplay helper. Every runtime dependency enters the export pipeline and should be reviewed for platform assumptions, file layout, size, and licensing.

## Initialize the project

Use the package manager your project already standardizes on. For npm:

```bash
npm init -y
npm install lodash
```

For pnpm:

```bash
pnpm init
pnpm add lodash
```

When using pnpm, configure the project to use a hoisted `node_modules` layout:

```ini title=".npmrc"
node-linker=hoisted
```

pnpm's default isolated layout stores packages behind symlinks under `node_modules/.pnpm`. Node.js can resolve that layout directly, but Godot's `res://` filesystem and native side-asset loading do not fully match Node's symlink resolver. A hoisted layout keeps package entry points, transitive dependencies, and native `.node` side libraries visible under `res://node_modules`, which is the layout Gode packages and resolves most reliably.

For native packages on pnpm 10 or newer, approve only the audited packages that need install scripts:

```yaml title="pnpm-workspace.yaml"
onlyBuiltDependencies:
  - node-llama-cpp
```

You can also run `pnpm approve-builds` and commit the generated approval file. Without this step, pnpm may print an `Ignored build scripts` warning and skip native setup work that some packages require.

Gode does not initialize package managers or install dependencies for you. These steps belong to the project's own development workflow.

## Import packages

Use standard ESM imports from TypeScript scripts:

```ts
import { Node } from "godot";
import lodash from "lodash";

export default class PackageDemo extends Node {
  _ready(): void {
    console.log(lodash.camelCase("hello gode"));
  }
}
```

ESM packages are loaded as ESM. CommonJS packages are bridged for default and named imports. Project scripts remain TypeScript-only; `.cjs` is supported as an explicit runtime sidecar format for CommonJS interoperability.

## Export implications

When root npm project files exist, Gode's export path validates and packages dependency files according to `gode.json`:

- `node` and `npm` are required by default.
- Export fails when `package.json` declares dependencies but `node_modules` is missing.
- Root package manifests and lockfiles are included by default.
- A `res://node_modules` snapshot is included by default.

When an exported game loads packages that need real filesystem paths, Gode materializes only the needed package directories from the exported dependency snapshot to `user://.gode/npm/node_modules` on demand. This gives native `.node` binaries, sibling DLLs/shared libraries, ESM `import.meta.url` path lookups, and package probe scripts real paths while keeping the export package reproducible.

Gode does not audit package internals. If a dependency contains native binaries, wasm files, large data sets, or platform-specific runtime assets, the game project is responsible for making those assets valid for the target export.

## Production checklist

| Check | Reason |
| --- | --- |
| Commit `package.json` and the lockfile | CI and teammates install the same dependency graph. |
| Install dependencies before export | Gode packages the installed snapshot; it does not run package installs during export. |
| Use `node-linker=hoisted` with pnpm | Godot and exported builds need a regular `node_modules` tree rather than pnpm's default symlink graph. |
| Approve required pnpm build scripts | Native packages may need postinstall work before Godot can load their `.node` binaries and side libraries. |
| Run an exported build once with native packages | First native load may populate package directories under the `user://.gode/npm` cache and should be measured on target hardware. |
| Review dependency size | Native game exports are sensitive to unexpected package weight. |
| Test each target platform | Node packages may assume desktop-only APIs or filesystem layouts. |
| Keep `gode.json` explicit | Export policy should be visible in code review. |
