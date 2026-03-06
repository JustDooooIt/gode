# Gode

在 Godot 4（GDExtension）里嵌入 Node.js 运行时，并提供：
- JavaScript 作为 ScriptLanguage（.js 脚本资源）
- `require('godot')` 原生绑定（N-API）
- `res://` 路径的 `require()`/模块解析与 `fs` 访问适配
- 自动生成的 Godot API JS 绑定（Node/Resource/UtilityFunctions/Builtin types 等）

本仓库包含多个子模块：`godot-cpp`、`node-addon-api`、`node`（Node.js 源码）、`tree-sitter`、`tree-sitter-javascript`。

## 快速开始（跑 example）

1. 初始化子模块：
```bash
git submodule update --init --recursive
```

2. 构建扩展（见下方“构建”）。

3. 打开示例工程并运行：
- 用 Godot 打开 `example/`
- Project Settings → Plugins 启用 `gode`
- 直接运行工程（F5），主场景是 [node_2d.tscn](file:///d:/Godot/gode/example/scene/node_2d.tscn#L1-L6)，其脚本是 [MyNode.js](file:///d:/Godot/gode/example/script/MyNode.js)

## 版本要求

- Godot：示例扩展配置要求 `compatibility_minimum = "4.6.1"`（见 [.gdextension](file:///d:/Godot/gode/example/addons/gode/bin/.gdextension#L1-L9)）
- CMake：≥ 3.12
- Python：用于代码生成（见 [code_generator/README.md](file:///d:/Godot/gode/code_generator/README.md)）
- Windows：当前 CMakeLists 针对 Windows/libnode 的路径做了特殊处理（见 [CMakeLists.txt](file:///d:/Godot/gode/CMakeLists.txt)）

## 构建（Windows / Visual Studio）

### 1) 准备 libnode（node/out/**）

本项目默认从 `node/` 子模块链接 `libnode`（DLL import lib + DLL）。

你需要先把 Node.js 编译出以下产物（默认路径）：
- `node/out/Debug/libnode.lib` 与 `node/out/Debug/libnode.dll`
- `node/out/Release/libnode.lib` 与 `node/out/Release/libnode.dll`

项目会在构建后自动把 `libnode.dll` 拷贝到 `example/addons/gode/bin/`（见 [CMakeLists.txt](file:///d:/Godot/gode/CMakeLists.txt#L191-L223)）。

### 2) 生成 VS 工程并编译

```bash
cmake -S . -B build -G "Visual Studio 17 2022" -A x64
cmake --build build --config Debug
```

构建完成后会自动把扩展 DLL 拷贝到：
- `example/addons/gode/bin/libgode.Debug.dll` 或 `libgode.Release.dll`（见 [CMakeLists.txt](file:///d:/Godot/gode/CMakeLists.txt#L225-L231)）

## 运行 example（Godot 编辑器）

### 1) 确认 .gdextension 指向正确 DLL

示例工程内的扩展描述文件是 [.gdextension](file:///d:/Godot/gode/example/addons/gode/bin/.gdextension#L1-L9)，其中写死了 Debug/Release 的 DLL 路径：
- `res://addons/gode/bin/libgode.Debug.dll`
- `res://addons/gode/bin/libgode.Release.dll`

只要你按上面的 CMake 构建，POST_BUILD 会自动把产物拷贝到这个目录，一般不需要手动改。

### 2) 安装 JS 依赖（可选）

示例脚本 [MyNode.js](file:///d:/Godot/gode/example/script/MyNode.js#L1-L15) 使用了 `is-odd`：
- 如果 `example/node_modules/` 已存在（仓库可能已带），可跳过
- 如果没有，请在 `example/` 下执行：

```bash
npm install
```

### 3) 启用插件与运行

1. 用 Godot 打开 `example/` 工程（[project.godot](file:///d:/Godot/gode/example/project.godot#L1-L22)）。
2. Project Settings → Plugins 启用 `gode`（[plugin.cfg](file:///d:/Godot/gode/example/addons/gode/plugin.cfg#L1-L7)）。
3. 插件会添加一个 Autoload 单例 `EventLoop`（见 [gode.gd](file:///d:/Godot/gode/example/addons/gode/gode.gd#L1-L22) 与 [event_loop.gd](file:///d:/Godot/gode/example/addons/gode/script/event_loop.gd#L1-L1)）。
4. 运行工程（F5）。主场景为 [node_2d.tscn](file:///d:/Godot/gode/example/scene/node_2d.tscn#L1-L6)，挂载脚本为 `res://script/MyNode.js`。

## JavaScript / res:// 模块加载机制

项目会对 Node 的模块系统做一层注入与兼容，使以下行为成立：
- `require('godot')` 返回原生绑定对象（来自 `process._linkedBinding('godot')`）
- `fs.readFileSync('res://...')` / `fs.existsSync('res://...')` / `fs.statSync('res://...')` 走 Godot 侧文件接口
- `require('./x')`、`require('pkg')` 在 `res://` 场景下具备类似 Node 的解析规则（扩展名、package.json main、index.js、node_modules 向上查找）

对应实现集中在 [node_runtime.cpp](file:///d:/Godot/gode/src/utils/node_runtime.cpp#L148-L427)：
- 注入 `godot` 模块到 `Module._cache`
- 重写 `fs.readFileSync/existsSync/statSync`
- 重写 `path.join/resolve/dirname` 以兼容 `res://`
- 重写 `Module._nodeModulePaths/_findPath/_resolveFilename`
- 提供 `globalThis.__gode_compile(code, filename)` 进行按文件名上下文编译

## 绑定生成（code_generator）

此仓库包含一个 Python + Jinja2 的绑定生成器，用于生成：
- `include/generated/**`
- `src/generated/**`

使用方法见 [code_generator/README.md](file:///d:/Godot/gode/code_generator/README.md)。

常用命令：
```bash
pip install -r code_generator/requirements.txt
python code_generator/generator.py
```

## 对象生命周期与 GC 约定（JS ↔ Godot）（简要）

### 1) Godot 对象销毁后，JS 访问安全

生成的 `*Binding` 现在会保存 `ObjectID`，每次调用前通过 `ObjectDB::get_instance(id)` 校验对象是否仍存在；对象已销毁时抛出 JS 异常，避免悬空指针崩溃。

### 2) JS GC 时，Node 的“是否回收实例”策略

当 JS 侧对象被 GC 触发 `~*Binding()`：
- 若是 `Node`（或其子类）且 **不在 SceneTree**（`!node->is_inside_tree()`），则调用 `queue_free()` 释放 Godot 侧实例
- 若已在 SceneTree，则仅回收 JS 包装对象，Godot 侧由场景树继续管理

### 3) ScriptInstance 释放 JS 强引用

当一个挂载了 JS Script 的 Godot 对象被 `queue_free()`：
- Godot 会销毁其 ScriptInstance
- `JavascriptInstance` 析构中会 `Reset()` 掉 `Napi::ObjectReference`，解除 C++→JS 的强引用，随后 JS 对象可被 GC

相关实现见：
- [javascript_instance.cpp](file:///d:/Godot/gode/src/support/javascript/javascript_instance.cpp)

## 目录结构（简要）

- `src/` / `include/`：扩展主体
- `src/generated/` / `include/generated/`：自动生成的绑定代码
- `code_generator/`：Python 代码生成器
- `example/`：Godot 示例工程（包含插件与 .gdextension 配置）
- `node/`：Node.js 源码子模块（用于构建 libnode）
- `node-addon-api/`：N-API C++ 封装头文件子模块
- `tree-sitter*`：用于 JS 相关解析/语法支持的子模块
