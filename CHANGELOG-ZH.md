## 2.1.0

- 将 TypeScript 作为唯一面向 Godot 的脚本语言，兼容 JavaScript 的同时、防止混用两种语言带来的混乱。
- 为正式发布包加入内置 TypeScript 打包流程。打包时会把编译器解压到插件的 `tsc/` 目录，且不保留 npm 压缩包中的外层 `package/` 目录。
- 依赖更新：嵌入式 Node.js 升级到 `24.18.0`，`third/node-addon-api` 升级到 `8.9.0`。
- 在 `addons/gode/config/` 内置默认 `tsconfig.json` 模板；项目根目录没有 `res://tsconfig.json` 时，Gode 会自动生成一份项目配置。
- 增加基于嵌入式 Node/V8 的进程内 TypeScript 项目编译，将 ESM JavaScript 输出到 Gode 管理的 `user://` 缓存，供编辑器和运行时使用。
- 增加 Godot 导出插件：导出前编译 TypeScript，并把生成的 ESM JavaScript 作为 `res://.gode/build/typescript/...` 注入导出包。
- 增加由项目根目录 `gode.json` 控制的商业化 npm 导出处理；需要该配置的外部依赖项目会从 `addons/gode/config/gode.json` 自动生成默认文件。
- 将 Node 虚拟文件系统和模块解析从 `res://` 扩展到 `user://`，使 TypeScript 编译缓存中的模块可以可靠导入项目模块和 npm 包。
- 保留 CommonJS 作为 npm 包和显式 `.cjs` sidecar 模块的互操作路径，项目生成产物只输出 ESM。
- 移除旧 JavaScript 资源 loader/saver 实现和未使用的 JavaScript 脚本图标，避免 `.js` 通过残留代码路径重新作为 Godot 脚本资源出现。
- 移除示例项目根目录的 `package.json`，保证内置示例无需安装外部依赖即可直接运行。
- 修复 TypeScript 导出属性的 revert 默认值：通过 `static exports` 声明属性时，会读取同名 class field initializer 作为默认值。
- 为运行时已暴露的内置类型运算符方法生成 TypeScript 声明，例如 `Vector2i.add()`；同时保留 `GD.typeof()` 这类运行时保留字名称。

## 2.0.0

- 为 TypeScript 增加静态 `signals` 和 `rpc_config` 元数据解析，使其与 JavaScript 脚本元数据工作流一致。
- 扩展 TypeScript 元数据中的 Variant 类型解析，支持 `Object`、`Vector4` 和 boxed primitive 名称等写法。
- 更新生成的 TypeScript 声明，将 Godot 类枚举值暴露到构造器上，对齐 `Window.MODE_FULLSCREEN`、`Viewport.MSAA_DISABLED` 等运行时用法。
- 修正生成的 TypeScript 声明中 `Object.set()` 和 `Object.get()` 的方法名，使其与 JavaScript 运行时 API 一致。
- 通过 GDExtension utility-function 表暴露 godot-cpp 省略的 `GD.is_instance_valid()`，用于验证 JavaScript 包装的 Godot 对象和 singleton。
- 将生成的 class vararg MethodBind 调用错误转换成 JavaScript 异常，避免 `emit_signal()`、`Object.call()` 等低层调用在参数错误时静默返回默认值。
- 为 NodeRuntime 的公开 V8 入口统一补充 locker/isolate scope，降低 TypeScript 编译、默认值求值和事件循环在嵌入式运行时中的 isolate 进入风险。
- 加固扩展关闭流程：用模块级 `Ref` 持有资源 loader/saver 单例，在 NodeRuntime 关闭前清理脚本 loader 缓存，并对 runtime 关闭后的 N-API 引用析构启用 suppress 保护。
- 在 NodeRuntime 关闭期间重置生成的静态 N-API constructor 引用，并去重 Godot class registry，使同进程 runtime 重新初始化更安全。
- 修正生成的 RefCounted wrapper 析构逻辑，使用 `unreference()` 返回值决定是否删除对象，避免递减引用计数后再查询同一对象。
- 允许生成绑定的 `Array`、`TypedArray<T>` 和 `Packed*Array` 输入直接接收普通 JavaScript 数组，覆盖 packed array 构造器、方法、运算符和 TypeScript 声明。
- 修复 `String`、`StringName` 和 `NodePath` wrapper 对象的模板转换，避免生成绑定把 wrapper 参数错误转换为空值。
- 移除旧式 `globalThis` Godot API 注入和默认 `godot` 命名空间导出。Gode 2.0 要求从 `godot` 模块显式具名导入所需 API。
- 从 `globals.d.ts` 移除 ambient Godot API 声明；该文件现在只声明脚本装饰器辅助函数和导出元数据类型。

## 1.6.3

- 修复 Godot 回调 JavaScript 脚本实例时的参数转换：先复制传入的 Variant 指针数组再调用 JS 方法，避免高频回调中出现不稳定的 native 崩溃。
- 在 Gode 事件循环和 JavaScript 信号 Callable 中推进 V8 microtask，使 `await obj.to_signal(...)` 在运行时能可靠恢复。
- 修复生成类继承方法在子类 wrapper 上的派发：先通过共享 Godot 对象句柄取回真实对象再转换类型，避免 `SceneMultiplayer` 调用继承的 `MultiplayerAPI` 方法这类崩溃。
- 调整 Godot 对象 wrapper 缓存，在保留 JavaScript 脚本实例身份的同时，不再依赖可能在 V8 GC finalizer 阶段崩溃的弱引用缓存。
- 为 JavaScript 脚本方法和 notification 增加异步 Promise rejection 处理，使 `await` 之后发生的错误会打印到 Godot 日志，而不是作为 Node 未处理 rejection 终止游戏进程。

## 1.6.2

- 为从 Godot 对象属性返回的生成内置类型增加实时写回，使 `velocity.x`、`global_transform.origin` 这类成员赋值会更新所属属性。
- 修复 JavaScript GC 后弱对象包装缓存被复用的问题，避免 `get_multiplayer()` 等重复调用返回失效 wrapper。
- 生成内置类型构造器时改为按参数类型解析重载，而不是只按参数数量匹配，覆盖 `Basis(Quaternion)` 和 `Transform3D(Quaternion, Vector3)` 这类流程。
- 增加嵌套内置类型父级写回，使 `global_transform.basis.x = ...` 这类链式赋值能继续回写到所属属性。
- 通过 Godot `Variant` 执行生成的内置类型运算符，支持 API 声明的跨类型运算，例如 `Basis.multiply(Vector3)` 和 `Transform3D.multiply(Vector3)`。
- 当生成绑定期望 `Basis` 时允许传入 `Quaternion`，对齐 root motion 和 transform 构造中常见的 Godot 用法。
- 修正生成的 `Basis.x/y/z` 成员访问，改用 Godot 轴列而不是 godot-cpp 内部行存储，修复相机相对方向计算。

## 1.6.1

- 将生成的内置类型静态方法暴露到构造器上，包括 `Basis.looking_at()` 这类 API。
- 保留生成的内置类型方法绑定中的默认参数。
- 生成类属性时，将 `_set_size` 这类下划线属性访问器解析到公开 setter。
- 根据只有 getter 的 Godot API 元数据生成只读类属性，包括 `World3D.direct_space_state` 这类属性。

## 1.6.0

- 将 Godot 类枚举值暴露到类构造器和 singleton 实例上，使运行时代码可以使用 `ResourceLoader.THREAD_LOAD_LOADED` 这类写法。
- 将内置类型常量暴露到 JavaScript 构造器和实例上，包括 `Vector3.UP`、`Vector3.ZERO` 和 `Color.WHITE` 等值。
- 保留生成的 JavaScript 类绑定中的 Godot API 默认参数，使 `Node3D.look_at(target)` 等调用会使用 Godot 文档中的默认值，而不是零值/空值。
- 扩展生成绑定的默认参数支持，覆盖 `RID` 和 typed array 参数。
- 为 Godot array 和 packed array 增加 JavaScript 迭代支持，使 `Array`、`PackedInt32Array` 等返回值可以直接用于 `for...of`。
- 增加 JavaScript 和 TypeScript 脚本方法元数据，包括方法列表和参数数量。
- 改进被包装 Godot 对象的 Object wrapper fallback 和所有权跟踪。

## 1.5.0

- 新增 JavaScript autoload 支持：默认导出类只要继承自 Godot 基类即可实例化，也支持 `godot.Node` 这类导入写法。
- 新增 JavaScript 脚本元数据解析：支持静态 `signals` 声明，使 JavaScript 自定义信号可以被 Godot 元数据接口发现并正常连接。
- 新增 JavaScript RPC 元数据支持：通过静态 `rpc_config` 配置 RPC 方法，使 Godot RPC 可以调用 JavaScript 方法，并支持 mode、transfer mode、channel 和 call local 等选项。
- 将 Godot 运行时 singleton 导出到 `godot` 模块和 `globalThis`，并改为懒加载 singleton，同时为 `EditorInterface` 增加仅编辑器环境可用的保护。
- 改进 Object wrapper 生命周期处理：更新被包装对象的实例 ID，保留 `RefCounted` 实例引用，并在被包装的 Godot 对象已释放时报告更清晰的类名/方法名错误。
- 修复从 JavaScript 返回被包装 Godot 对象的场景/资源实例化路径，包括 headless/runtime 流程中的 `PackedScene.instantiate()` 用法。
- 扩充英文和中文高级用法文档，补充 autoload、信号、RPC 元数据、导出属性/tool 脚本、资源加载、调试、TypeScript 工作流和导出说明。

## 1.4.2

- 修复启用插件时 Godot 编辑器 PopupMenu 报错的问题：JavaScript 和 TypeScript 脚本图标改为通过 GDExtension manifest 注册，不再在运行时修改编辑器主题。
- 移除插件自动启动 `tsc --watch` 的行为。TypeScript 编译现在完全由项目自行控制，用户可以使用自己的编译器、监听器、打包器或包管理器工作流。
- 更新 TypeScript 脚本加载逻辑，使 `.ts` 和 `.tsx` 脚本从 `res://dist` 解析对应的运行时 JavaScript 输出。
- 保持 JavaScript 脚本直接加载，不再回退到 `res://dist`。
- 修复 JavaScript 资源的脚本源码检测。
- 修复关闭时的 ObjectDB 泄漏警告：GDExtension 退出时会释放已注册的 JavaScript 和 TypeScript 语言 singleton。
- 更新导出文档，推荐导出预设包含运行时 JavaScript/JSON 文件、`dist`、`node_modules` 和 `package.json`。

## 1.4.1

- 重构。
