# Gode

[EN Doc](https://github.com/godothub/gode) &nbsp;&nbsp;&nbsp; [中文文档](https://github.com/godothub/gode/blob/main/README-ZH.md)

Godot 引擎的 JavaScript/TypeScript 脚本支持，运行在所有原生平台！

| 平台 | Windows | Android | macOS | iOS | Linux | OHOS |
| --- | --- | --- | --- | --- | --- | --- |
| 支持情况 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 最低版本 | 10 | 9 | 10.15 | 16 | Ubuntu 22 | 6 |

## 快速入门

### 1. 安装插件

1. 下载最新版本的[Gode插件](https://github.com/godothub/gode/releases/latest)
2. 将压缩包中的 `gode` 目录解压到项目的 `addons` 目录下。没有该目录时，先手动创建。

安装后的目录结构应类似：

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

3. 打开 Godot，进入 `项目 > 项目设置 > 插件`。
4. 找到 `gode`，勾选启用。

启用后，创建 Godot 脚本时选择 `TypeScript`。

### 2. 编写 TypeScript 脚本

创建 `res://scripts/hello.ts`：

```ts
import { Node } from "godot";

export default class Hello extends Node {
	_ready(): void {
		console.log("Hello from Gode");
	}
}
```

然后在 Godot 编辑器中，把这个脚本挂到任意节点上运行。

TypeScript 脚本可以使用 `import { Node } from "godot"` 这类写法引入 Godot 类型。

### 3. 使用 npm 包

示例项目不包含 `npm` 外部依赖，因此可以直接打开运行，不需要系统安装 Node.js。只有项目根目录存在 `package.json` 或 `node_modules` 时，Gode 才会把它视为外部依赖项目，并在导出时要求环境中存在 Node.js/npm 基础工具链。

需要使用外部 npm 包时，在项目根目录自行初始化包管理器。例如：

```bash
npm init -y
```

安装依赖：

```bash
npm install lodash
```

pnpm、yarn 等项目也可以使用对应工具初始化和安装依赖，例如 `pnpm init` / `pnpm add lodash`。Gode 不会自动初始化项目，也不会自动安装依赖；这些步骤由项目本身的开发流程负责。

在 TypeScript 脚本中使用：

```ts
import { Node } from "godot";
import lodash from "lodash";

export default class Demo extends Node {
	_ready(): void {
		console.log(lodash.camelCase("hello gode"));
	}
}
```

Gode 会从项目根目录的 `node_modules`（即 `res://node_modules`）中解析 npm 包。ESM 包按 ESM 加载，CommonJS 包会桥接为 default/named import。项目脚本仍然只允许 TypeScript；`.cjs` 只作为明确的 CommonJS 运行时 sidecar 格式用于互操作。导出项目时，Gode 会根据项目根目录的 `gode.json` 生成运行时依赖快照；外部依赖项目缺少该文件时会自动生成，详见[导出项目](#导出项目)。

### 4. 配置 TypeScript

Gode 的正式插件包会在 `addons/gode/tsc` 内置 TypeScript `6.0.3`，普通 Godot 开发不需要安装或运行 `tsc`。Gode 默认读取项目根目录的 `res://tsconfig.json`；如果项目还没有这个文件，第一次编译时会从 `res://addons/gode/config/tsconfig.json` 复制一份默认配置到项目根目录：

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

这份 `tsconfig.json` 是项目配置，生成后可以按项目需要维护。只有脚本使用 Node 全局对象或 Node 包类型时，才需要安装 Node 类型，并把 `"types"` 改为包含 `"node"`：

```bash
npm install -D @types/node
```

## 进阶用法

### TypeScript 与 GDScript 互相调用

下面是一个完整的节点结构示例：

```text
Main
├── TsPlayer      # 挂 res://scripts/player_logic.ts
└── GdTarget      # 挂 res://scripts/gd_target.gd
```

`res://scripts/player_logic.ts`：

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

`res://scripts/gd_target.gd`：

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

GDScript 调 TypeScript 脚本方法时，可以像调用普通节点脚本一样直接调用：

```gdscript
var result = $"../TsPlayer".say_hello("Godot")
```

TypeScript 调 GDScript 方法时，推荐通过 Godot 的通用 `call()` 调用：

```ts
const target = this.get_node("../GdTarget");
const result = target.call("some_method", "from TypeScript");
```

如果希望降低耦合，推荐使用 Godot 信号。TypeScript 自定义信号的写法见[声明信号](#声明信号)。

### Godot 类型与单例

可以从 `godot` 模块导入 Godot 类、内置 Variant 类型和运行时 singleton：

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

Gode 只通过 `godot` 模块暴露 Godot API。需要什么类和 singleton，就显式 import 什么。生成的 `globals.d.ts` 只声明脚本装饰器辅助函数和导出元数据类型，不会再把 `Node`、`ResourceLoader`、`Engine` 这类 Godot API 自动声明成全局可用的名称。

### TypeScript Autoload

只要脚本的默认导出继承自 Godot 基类，例如 `Node`，TypeScript 脚本就可以作为 Godot autoload 使用：

```ts
import { Node } from "godot";

export default class Settings extends Node {
	_ready(): void {
		this.load_settings();
	}

	load_settings(): void {
		// 在这里初始化全局设置。
	}
}
```

可以在 `project.godot` 或 Project Settings 中注册：

```ini
[autoload]

Settings="*res://menu/settings.ts"
```

其他脚本中通过场景树访问：

```ts
const settings = this.get_node("/root/Settings");
settings.load_settings();
```

### 导出属性与工具脚本

使用静态 `exports` 可以把 TypeScript 字段暴露为 Godot 脚本属性。导出的属性会出现在 Inspector 中，并可以被场景和资源序列化。

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

`type` 字段使用 Godot Variant 类型名，例如 `"String"`、`"int"`、`"float"`、`"bool"`、`"Vector3"`、`"Object"`，以及其他 Godot 脚本属性支持的类型。

如果脚本需要在编辑器中运行，可以设置 `static tool = true`：

```ts
export default class Preview extends Node3D {
	static tool = true;
}
```

### 声明信号

自定义脚本信号可以通过静态 `signals` 对象声明。Gode 会把这些信息暴露给 Godot 的脚本元数据接口，因此 `has_signal()`、`connect()` 以及编辑器/运行时的信号发现都可以正常工作。

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

信号参数使用 `{ name, type }` 描述。`type` 可以是 Godot Variant 类型名，例如 `"String"`、`"int"`、`"float"`、`"bool"`、`"Vector3"` 或 `"Object"`。

也可以直接连接已有的 Godot 信号：

```ts
button.connect("pressed", () => {
	console.log("button pressed");
});
```

### RPC 元数据

需要通过 Godot 多人 RPC 调用的方法，必须使用静态 `rpc_config` 声明 RPC 元数据：

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

声明元数据后，就可以用 Godot 标准 RPC 调用 TypeScript 方法：

```ts
if (target.has_method("hit")) {
	target.rpc("hit");
}
```

`mode` 支持 `"authority"`、`"any_peer"` 和 `"disabled"`。`transfer_mode` 支持 `"reliable"`、`"unreliable"` 和 `"unreliable_ordered"`。未填写的字段会使用 Godot 默认值。

### 加载资源与实例化场景

TypeScript 中加载的资源是普通 Godot 资源，在 JavaScript wrapper 持有期间会保持正确的 Godot 生命周期：

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

如果资源后续还会复用，像 GDScript 中一样保留引用即可：

```ts
import { Node, ResourceLoader } from "godot";

export default class LevelLoader extends Node {
	_ready(): void {
		this.levelScene = ResourceLoader.load("res://level/level.tscn");
		this.add_child(this.levelScene.instantiate());
	}
}
```

### 调试

脚本层调试可以使用 `console.log()` / `console.error()`。输出会显示在 Godot 输出面板和启动 Godot 的终端中。

当 JavaScript 异常穿过 Godot 调用边界时，Gode 会把它报告为 Godot 脚本错误。如果问题只在运行时出现，也建议从终端启动 Godot，这样 Node/V8 警告和原生扩展信息也能看到。

### TypeScript 工作流

Gode 把 TypeScript 作为唯一面向 Godot 的脚本语言。编辑器和运行时会把 `.ts` / `.tsx` 资源在进程内编译为 ESM JavaScript，并写入 Gode 管理的 `user://.gode/typescript/...` 缓存。这个缓存是内部实现，不需要提交，也不要在场景里引用。

脚本元数据写在默认导出的 TypeScript 类上。`signals`、`rpc_config`、`exports`、`tool` 这些静态字段会保留到生成的 ESM 输出中：

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

本地导入使用现代 ESM 写法：

```ts
import { PlayerState } from "./player_state";
```

Gode 使用插件内置的 TypeScript 编译器完成诊断和输出。项目根目录的 `tsconfig.json` 会用于类型检查策略；缺失时 Gode 会生成默认配置。运行产物会被强制为 ESM，保证 Godot 项目只有一种主模块格式。CommonJS 只作为 npm 包和显式 `.cjs` sidecar 模块的兼容路径，不作为 Godot 脚本资源格式。

### 导出项目

导出开始前，Gode 导出插件会编译项目，并把生成的 ESM JavaScript 作为 `res://.gode/build/typescript/...` 虚拟文件注入导出包。debug 导出包含 source map，release 导出只包含运行时 JavaScript。

如果项目根目录没有 `package.json` 或 `node_modules`，Gode 不会要求外部 Node.js/npm 环境，项目可以直接导出。只有项目根目录存在 `package.json` 或 `node_modules` 时，Gode 才会把它视为外部依赖项目：

- 导出前检查 `node` 和 `npm` 是否在 `PATH` 中，用来确认当前环境具备 npm 项目的基础工具链。
- `package.json` 声明依赖但没有 `node_modules` 时导出失败，用户需要先运行对应的 install 命令。
- 默认把根目录的 package manifest/lockfile 和 `node_modules` 文件快照注入导出包。
- Gode 不会扫描或审查 `node_modules` 内部包内容；如果依赖包含原生二进制、wasm 或运行时数据文件，需要用户按目标平台自行保证这些文件可用。

可以在项目根目录的 `gode.json` 中控制导出细节。外部依赖项目导出时，如果根目录没有 `gode.json`，Gode 会从插件内置模板 `res://addons/gode/config/gode.json` 自动生成一份。模板内容如下：

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

| 设置 | 默认值 | 说明 |
| --- | --- | --- |
| `export.npm.exportDependencies` | `true` | 有 npm 项目文件时导出 package manifest 和 `node_modules` 快照。 |
| `export.npm.requireTools` | `true` | 有 npm 项目文件时要求 `node` 和 `npm` 命令存在。 |
| `export.npm.includeManifests` | `true` | 导出 `package.json`、lockfile、`.npmrc` / `.yarnrc` 等根目录 manifest。 |
| `export.npm.includeNodeModules` | `true` | 导出 `res://node_modules` 文件快照。 |
| `export.npm.excludePaths` | `node_modules/.cache`, `node_modules/.bin` | 从 npm 快照中排除的路径前缀。 |
| `export.npm.extraIncludePaths` | 空 | 额外注入导出包的依赖资源路径，例如包外的 wasm 或数据目录。 |

推荐的项目配置方式：

- 无外部依赖项目：不要在项目根目录放 `package.json` 或 `node_modules`，也不需要 `gode.json`，导出不要求系统安装 Node.js/npm。单独存在的 lockfile 不会触发外部依赖模式。
- npm/pnpm/yarn/bun 项目：在项目根目录自行运行 `init` / `install` / `add`，提交 `package.json` 和 lockfile；导出前由用户或 CI 先安装依赖。首次导出会生成项目根目录 `gode.json`，保持 `exportDependencies`、`includeManifests`、`includeNodeModules` 为默认开启即可。
- 自定义依赖流水线：只有当你明确用其他流程注入依赖时，才关闭 `exportDependencies` 或 `includeNodeModules`；只有当上层 CI 已经验证工具链时，才关闭 `requireTools`。
- Gode 不会检查 npm 包内部“有哪些东西”，也不会替用户判断某个包是否该用；导出阶段只检查可复现运行所必需的边界条件，例如根目录是否存在 `package.json` / `node_modules`、声明的依赖是否已经安装。

## 精选案例

- [tps-demo-ts](https://github.com/godothub/gode-tps-demo)：官方 tps-demo 示例的 TypeScript 版本

## 常见问题

**启用插件后看不到 TypeScript 脚本类型**

确认插件目录是 `res://addons/gode`，并且 `res://addons/gode/plugin.cfg` 存在。然后重新启用插件或重启 Godot。

**TypeScript autoload 无法实例化**

确认 autoload 条目指向 `.ts` / `.tsx` 文件，并且脚本的默认导出类继承自 Godot 基类，例如 `Node`。Gode 会通过这份继承元数据创建 autoload 实例。

**TypeScript 脚本没有被编译**

确认已安装的插件包含 `addons/gode/tsc/lib/typescript.js`。编译失败时，Gode 会在 Godot 输出面板报告 TypeScript 诊断信息。

**`rpc()` 无法调用 TypeScript 方法**

请在 TypeScript 类上用 `static rpc_config` 声明该方法。只有脚本报告了 RPC 元数据后，Godot 才会把对应方法暴露给 RPC。

**运行时找不到 npm 包**

确认依赖已经安装在 Godot 项目根目录的 `node_modules` 中。导出时保持 `gode.json` 中的 `export.npm.exportDependencies` 启用，Gode 会注入 `node_modules` 快照；如果包还需要额外的 wasm、数据文件或平台相关二进制，请通过 `export.npm.extraIncludePaths` 或项目自己的导出流水线明确处理。

**导出后插件无法加载**

确认当前导出平台在支持列表中，并且 `addons/gode/binary/gode.gdextension` 中对应平台的二进制文件存在。
