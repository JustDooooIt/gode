# Gode

[EN Doc](https://github.com/godothub/gode) &nbsp;&nbsp;&nbsp; [中文文档](https://github.com/godothub/gode/blob/main/README-ZH.md)

JavaScript/TypeScript scripting support for the Godot engine, running on all native platforms.

| Platform | Windows | Android | macOS | iOS | Linux |
| --- | --- | --- | --- | --- | --- |
| Supported | ✅ | ✅ | ✅ | ✅ | ✅ |
| Minimum Version | 10 | 9 | 10.15 | 16 | Ubuntu 22 |

## Quick Start

### 1. Install the Plugin

1. Download the latest [Gode plugin](https://github.com/godothub/gode/releases/latest).
2. Extract the `gode` directory from the archive into your project's `addons` directory. Create the directory first if it does not exist.

The installed directory structure should look like this:

```bash
my_project
├── addons
│   └── gode
│       ├── binary
│       ├── gode.gd
│       ├── gode.gd.uid
│       ├── plugin.cfg
│       ├── runtime
│       ├── tsc
│       └── types
```

3. Open Godot and go to `Project > Project Settings > Plugins`.
4. Find `gode` and enable it.

After enabling the plugin, choose `TypeScript` when creating Godot scripts.

### 2. Write a TypeScript Script

Create `res://scripts/hello.ts`:

```ts
import { Node } from "godot";

export default class Hello extends Node {
	_ready(): void {
		console.log("Hello from Gode");
	}
}
```

Attach this script to any node in the Godot editor and run the scene.

TypeScript scripts import Godot types with syntax like `import { Node } from "godot"`.

### 3. Use npm Packages

The example project does not include `package.json` or `node_modules`, so users can open and run it directly without installing Node.js or npm. Gode treats a project as an external-dependency project only when the project root contains `package.json` or `node_modules`; export then requires the basic Node.js/npm toolchain to be available.

To use external npm packages, initialize your package manager in the project root. For npm:

```bash
npm init -y
```

Install a dependency:

```bash
npm install lodash
```

pnpm, Yarn, and Bun projects can use their own commands, such as `pnpm init` / `pnpm add lodash`. Gode does not initialize projects or install dependencies automatically; that stays in your own development workflow.

Use it in a TypeScript script:

```ts
import { Node } from "godot";
import lodash from "lodash";

export default class Demo extends Node {
	_ready(): void {
		console.log(lodash.camelCase("hello gode"));
	}
}
```

Gode resolves npm packages from the project root `node_modules` (`res://node_modules`). ESM packages are loaded as ESM, and CommonJS packages are bridged for default and named imports. Project scripts are still TypeScript-only; `.cjs` is supported as an explicit runtime sidecar format for CommonJS interop. During export, Gode can generate a runtime dependency snapshot from the project-root `gode.json`; external-dependency projects get that file automatically when it is missing. See [Exporting Projects](#exporting-projects).

### 4. Configure TypeScript

Release builds of the Gode plugin include TypeScript `6.0.3` under `addons/gode/tsc`, so users do not install or run `tsc` for normal Godot development. Gode reads `res://tsconfig.json` from the project root by default. If the project does not have one yet, the first compilation copies the default template from `res://addons/gode/config/tsconfig.json` into the project root:

```json
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
	"include": [
		"**/*.ts",
		"**/*.tsx",
		"**/*.d.ts"
	],
	"exclude": ["node_modules", ".godot", ".gode", "addons/gode/tsc"]
}
```

Treat the generated `tsconfig.json` as project configuration and adjust it as needed. Installing Node types is optional and only needed when your scripts use Node globals or Node package types; when you do, include `"node"` in `"types"`:

```bash
npm install -D @types/node
```

## Advanced Usage

### Calling Between TypeScript and GDScript

Here is a complete node setup:

```text
Main
├── TsPlayer      # attached to res://scripts/player_logic.ts
└── GdTarget      # attached to res://scripts/gd_target.gd
```

`res://scripts/player_logic.ts`:

```ts
import { Node } from "godot";

export default class PlayerLogic extends Node {
	say_hello(name: string): string {
		return `hi ${name}`;
	}

	call_gd_target(): unknown {
		const target = this.get_node("../GdTarget");
		return target.call("some_method", "from TypeScript");
	}
}
```

`res://scripts/gd_target.gd`:

```gdscript
extends Node

func _ready() -> void:
	var ts_result = $"../TsPlayer".say_hello("Godot")
	print(ts_result) # hi Godot

	var gd_result = $"../TsPlayer".call_gd_target()
	print(gd_result) # gd received from TypeScript

func some_method(message: String) -> String:
	return "gd received " + message
```

GDScript can call TypeScript script methods directly, just like methods on regular node scripts:

```gdscript
var result = $"../TsPlayer".say_hello("Godot")
```

When TypeScript calls a GDScript method, use Godot's generic `call()`:

```ts
const target = this.get_node("../GdTarget");
const result = target.call("some_method", "from TypeScript");
```

For loose coupling, prefer Godot signals. See [Declaring Signals](#declaring-signals) for TypeScript-defined signals.

### Godot Types and Singletons

Import Godot classes, built-in Variant types, and runtime singletons from the `godot` module:

```ts
import { DisplayServer, Node3D, ResourceLoader, Vector3 } from "godot";

export default class Demo extends Node3D {
	_ready(): void {
		console.log(DisplayServer.get_name());

		const scene = ResourceLoader.load("res://scenes/marker.tscn");
		const marker = scene.instantiate();
		marker.position = new Vector3(0, 1, 0);
		this.add_child(marker);
	}
}
```

Gode only exposes Godot APIs through the `godot` module. Import the classes and singletons you use explicitly. The generated `globals.d.ts` file only declares script decorator helpers and export metadata types; it no longer declares Godot APIs such as `Node`, `ResourceLoader`, and `Engine` as globally available names.

### TypeScript Autoloads

TypeScript scripts can be used as Godot autoloads when the script's default export extends a Godot base class such as `Node`:

```ts
import { Node } from "godot";

export default class Settings extends Node {
	_ready(): void {
		this.load_settings();
	}

	load_settings(): void {
		// Initialize global settings here.
	}
}
```

Register the script in `project.godot` or through Project Settings:

```ini
[autoload]

Settings="*res://menu/settings.ts"
```

Then access it from other scripts through the scene tree:

```ts
const settings = this.get_node("/root/Settings");
settings.load_settings();
```

### Exported Properties and Tool Scripts

Use static `exports` to expose TypeScript fields as Godot script properties. Exported properties appear in the Inspector and can be serialized in scenes and resources.

```ts
import { Node3D, Vector3 } from "godot";

export default class Spawner extends Node3D {
	static exports = {
		spawn_count: { type: "int" },
		spawn_offset: { type: "Vector3" },
		enabled: { type: "bool" },
	};

	spawn_count = 3;
	spawn_offset = new Vector3(0, 1, 0);
	enabled = true;
}
```

The `type` field uses Godot Variant type names such as `"String"`, `"int"`, `"float"`, `"bool"`, `"Vector3"`, `"Object"`, and other types supported by Godot script properties.

Set `static tool = true` when the script should run in the editor:

```ts
export default class Preview extends Node3D {
	static tool = true;
}
```

### Declaring Signals

Declare custom script signals with a static `signals` object. Gode exposes these to Godot through the script metadata APIs, so `has_signal()`, `connect()`, and editor/runtime signal discovery work as expected.

```ts
import { Node } from "godot";

export default class Menu extends Node {
	static signals = {
		replace_main_scene: [{ name: "resource", type: "Object" }],
		quit: [],
	};

	_on_start_pressed(): void {
		this.emit_signal("replace_main_scene", this.next_scene);
	}
}
```

Signal arguments are described with `{ name, type }` entries. The `type` value may be a Godot Variant type name such as `"String"`, `"int"`, `"float"`, `"bool"`, `"Vector3"`, or `"Object"`.

You can also connect to existing Godot signals directly:

```ts
button.connect("pressed", () => {
	console.log("button pressed");
});
```

### RPC Metadata

Methods that should be callable through Godot multiplayer RPC must be declared with static `rpc_config` metadata:

```ts
import { CharacterBody3D } from "godot";

export default class Robot extends CharacterBody3D {
	static rpc_config = {
		hit: { mode: "authority", call_local: true },
		play_effect: { mode: "any_peer", call_local: true, transfer_mode: "reliable", channel: 0 },
	};

	hit(): void {
		this.health -= 1;
	}

	play_effect(): void {
		this.effect.restart();
	}
}
```

After the metadata is declared, regular Godot RPC calls can target the TypeScript method:

```ts
if (target.has_method("hit")) {
	target.rpc("hit");
}
```

Supported `mode` values are `"authority"`, `"any_peer"`, and `"disabled"`. Supported `transfer_mode` values are `"reliable"`, `"unreliable"`, and `"unreliable_ordered"`. Omitted fields use Godot's defaults.

### Resource Loading and Scene Instantiation

Resources loaded from TypeScript are normal Godot resources and keep their Godot lifetime while wrapped by JavaScript:

```ts
import { Node, ResourceLoader } from "godot";

export default class SceneSpawner extends Node {
	_ready(): void {
		const menuScene = ResourceLoader.load("res://menu/menu.tscn");
		const menu = menuScene.instantiate();
		this.add_child(menu);
	}
}
```

Keep a reference to resources that you plan to reuse, just as you would in GDScript:

```ts
import { Node, ResourceLoader } from "godot";

export default class LevelLoader extends Node {
	_ready(): void {
		this.levelScene = ResourceLoader.load("res://level/level.tscn");
		this.add_child(this.levelScene.instantiate());
	}
}
```

### Debugging

Use `console.log()` / `console.error()` for script-level debugging. Output appears in the Godot output panel and in the terminal that launched Godot.

When a JavaScript exception crosses into Godot, Gode reports it as a Godot script error. For runtime-only issues, also run Godot from a terminal so Node/V8 warnings and native extension messages are visible.

### TypeScript Workflow

Gode treats TypeScript as the only Godot-facing script language. At edit time and runtime, `.ts` / `.tsx` resources are compiled in-process to ESM JavaScript under Gode's `user://.gode/typescript/...` cache. That cache is private implementation detail; do not commit it and do not reference it from scenes.

Keep script metadata on the exported TypeScript class. Static fields such as `signals`, `rpc_config`, `exports`, and `tool` are preserved in the generated ESM output:

```ts
import { Node } from "godot";

export default class Player extends Node {
	static signals = {
		died: [],
	};

	static rpc_config = {
		hit: { mode: "authority", call_local: true },
	}
}
```

For local imports, use modern ESM specifiers:

```ts
import { PlayerState } from "./player_state";
```

Gode uses the bundled TypeScript compiler for diagnostics and emit. It respects the project-root `tsconfig.json` for type-checking policy and creates the default config when it is missing. Runtime output is forced to ESM so Godot projects have one primary module format. CommonJS remains a compatibility path for npm packages and explicit `.cjs` sidecar modules, not for Godot script resources.

### Exporting Projects

Before export, the Gode export plugin compiles the project and injects the generated ESM JavaScript into `res://.gode/build/typescript/...` inside the exported package. Debug exports include source maps; release exports include only the runtime JavaScript.

If the project root has no `package.json` or `node_modules`, Gode does not require an external Node.js/npm environment and the project can be exported directly. Only root `package.json` or `node_modules` makes Gode treat the project as an external-dependency project:

- It checks that `node` and `npm` are available in `PATH`, which confirms the basic npm project toolchain exists.
- Export fails when `package.json` declares dependencies but `node_modules` is missing; run the matching install command first.
- Root package manifests/lockfiles and a `node_modules` file snapshot are injected into the exported package by default.
- Gode does not scan or audit package contents inside `node_modules`; if a dependency contains native binaries, wasm, or runtime data files, the project is responsible for making those files valid for the target platform.

Export behavior is controlled from `gode.json` in the project root. When an external-dependency project is exported without a root `gode.json`, Gode creates one from the bundled template at `res://addons/gode/config/gode.json`. The template is:

```json
{
  "export": {
    "npm": {
      "exportDependencies": true,
      "requireTools": true,
      "includeManifests": true,
      "includeNodeModules": true,
      "excludePaths": [
        "node_modules/.cache",
        "node_modules/.bin"
      ],
      "extraIncludePaths": []
    }
  }
}
```

| Setting | Default | Meaning |
| --- | --- | --- |
| `export.npm.exportDependencies` | `true` | Export package manifests and a `node_modules` snapshot when npm project files exist. |
| `export.npm.requireTools` | `true` | Require `node` and `npm` for npm projects. |
| `export.npm.includeManifests` | `true` | Export root `package.json`, lockfiles, `.npmrc` / `.yarnrc`, and related manifests. |
| `export.npm.includeNodeModules` | `true` | Export a `res://node_modules` file snapshot. |
| `export.npm.excludePaths` | `node_modules/.cache`, `node_modules/.bin` | Path prefixes excluded from the npm snapshot. |
| `export.npm.extraIncludePaths` | empty | Extra dependency resources to inject, such as external wasm or data directories. |

Recommended project setup:

- Projects without external dependencies: do not place `package.json` or `node_modules` in the project root, and do not need `gode.json`. Export does not require a system Node.js/npm installation. A lockfile by itself does not trigger external-dependency mode.
- npm/pnpm/Yarn/Bun projects: run `init` / `install` / `add` yourself in the project root and commit `package.json` plus the lockfile. Install dependencies before export, either locally or in CI. The first export creates root `gode.json`; keep `exportDependencies`, `includeManifests`, and `includeNodeModules` enabled unless you have a custom pipeline.
- Custom dependency pipelines: disable `exportDependencies` or `includeNodeModules` only when another pipeline injects dependencies. Disable `requireTools` only when an outer CI step already validates the toolchain.
- Gode does not inspect package internals or decide which packages users should use. Export checks are limited to reproducible runtime boundaries: whether root `package.json` / `node_modules` exists and whether declared dependencies are installed.

## Featured Demos

- [tps-demo-ts](https://github.com/godothub/gode-tps-demo): TypeScript version of the official tps-demo sample

## FAQ

**The TypeScript script type does not appear after enabling the plugin**

Make sure the plugin directory is `res://addons/gode` and that `res://addons/gode/plugin.cfg` exists. Then enable the plugin again or restart Godot.

**A TypeScript autoload fails to instantiate**

Make sure the autoload entry points to a `.ts` / `.tsx` file and the script's default export class extends a Godot base class such as `Node`. Gode uses that inheritance metadata to create the autoload instance.

**TypeScript scripts are not compiled**

Make sure the installed plugin contains `addons/gode/tsc/lib/typescript.js`. Gode reports TypeScript diagnostics in the Godot output panel when compilation fails.

**`rpc()` cannot call a TypeScript method**

Declare the method in `static rpc_config` on the TypeScript class. Godot only exposes methods to RPC after the script reports that RPC metadata.

**npm packages cannot be found at runtime**

Make sure dependencies are installed in the Godot project root under `node_modules`. Keep `export.npm.exportDependencies` enabled in `gode.json` so Gode injects the `node_modules` snapshot; packages that need extra wasm, data files, or platform-specific binaries should be handled with `export.npm.extraIncludePaths` or your own export pipeline.

**The plugin fails to load after export**

Make sure the export platform is listed as supported, and that the matching binary exists in `addons/gode/binary/gode.gdextension`.
