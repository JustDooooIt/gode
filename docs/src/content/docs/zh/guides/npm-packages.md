---
title: 使用 npm 包
description: 在 Godot 项目根目录使用 npm 依赖，并保持导出行为明确、可复现。
---

Gode 可以从 Godot 项目根目录解析 npm 包。这个能力是显式启用的：只有根目录存在 `package.json` 或 `node_modules` 时，项目才会被视为外部依赖项目。

## 何时引入依赖

当 npm 包能提供真实价值时再引入：数据格式、网络辅助、确定性模拟工具、校验逻辑、与后端共享的库，或运行时内容管线。

不要为了很小的 gameplay helper 引入包。每个运行时依赖都会进入导出链路，应审查平台假设、文件结构、体积和许可证。

## 初始化项目

使用项目已经标准化的包管理器。npm 示例：

```bash
npm init -y
npm install lodash
```

pnpm 示例：

```bash
pnpm init
pnpm add lodash
```

使用 pnpm 时，应在项目中配置 hoisted 的 `node_modules` 布局：

```ini title=".npmrc"
node-linker=hoisted
```

pnpm 默认 isolated 布局会把包放在 `node_modules/.pnpm` 下，并通过 symlink 暴露入口。Node.js 自身可以直接解析这种布局，但 Godot 的 `res://` 文件系统和原生 side asset 加载无法完全等价模拟 Node 的 symlink resolver。hoisted 布局会让包入口、间接依赖和原生 `.node` 旁边的动态库都直接出现在 `res://node_modules` 下，这是 Gode 当前最可靠的打包和解析形态。

pnpm 10 或更新版本使用原生包时，只批准已经审计过且确实需要安装脚本的包：

```yaml title="pnpm-workspace.yaml"
onlyBuiltDependencies:
  - node-llama-cpp
```

也可以运行 `pnpm approve-builds`，并提交它生成的批准文件。如果缺少这一步，pnpm 可能输出 `Ignored build scripts` 警告，并跳过某些原生包需要的安装阶段。

Gode 不会替你初始化包管理器，也不会自动安装依赖。这些步骤属于项目自身开发流程。

## 导入包

在 TypeScript 脚本中使用标准 ESM 导入：

```ts
import { Node } from "godot";
import lodash from "lodash";

export default class PackageDemo extends Node {
  _ready(): void {
    console.log(lodash.camelCase("hello gode"));
  }
}
```

ESM 包按 ESM 加载。CommonJS 包会桥接为 default 和 named import。项目脚本仍然只允许 TypeScript；`.cjs` 作为明确的 CommonJS 运行时 sidecar 格式用于互操作。

## 导出影响

当根目录存在 npm 项目文件时，Gode 的导出流程会根据 `gode.json` 校验并打包依赖：

- 默认要求 `node` 和 `npm` 在 `PATH` 中可用。
- `package.json` 声明依赖但缺少 `node_modules` 时，导出会失败。
- 默认包含根目录 package manifest 和 lockfile。
- 默认包含 `res://node_modules` 快照。

导出游戏加载需要真实文件系统路径的包时，Gode 只会按需把导出依赖快照中的相关包目录物化到 `user://.gode/npm/node_modules`。这样原生 `.node` 二进制、旁路 DLL/共享库、ESM `import.meta.url` 路径推导和包探测脚本都有真实路径，同时导出包本身仍然可复现。

Gode 不审计包内部内容。如果依赖包含原生二进制、wasm、大型数据文件或平台相关运行时资源，项目需要自行保证这些资源适用于目标平台。

## 生产检查表

| 检查项 | 原因 |
| --- | --- |
| 提交 `package.json` 和 lockfile | CI 与团队成员安装同一份依赖图。 |
| 导出前安装依赖 | Gode 打包已安装快照，不在导出时执行 install。 |
| pnpm 使用 `node-linker=hoisted` | Godot 和导出构建需要常规 `node_modules` 树，而不是 pnpm 默认 symlink 图。 |
| 批准必要的 pnpm 构建脚本 | 原生包可能需要 postinstall 才能让 Godot 加载 `.node` 二进制和旁边的动态库。 |
| 带原生包跑一次导出包 | 第一次原生加载可能会在 `user://.gode/npm` 下填充包目录缓存，应在目标机器上测量。 |
| 审查依赖体积 | 原生游戏导出对意外包体积很敏感。 |
| 测试每个目标平台 | npm 包可能假设桌面 API 或特定文件系统结构。 |
| 保持 `gode.json` 明确 | 导出策略应能在 code review 中被看见。 |
