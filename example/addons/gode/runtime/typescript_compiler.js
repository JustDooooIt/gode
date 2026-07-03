"use strict";

(function() {
	const fs = require("fs");
	const path = require("path");

	let ts = null;

	function getTypescript() {
		if (ts) {
			return ts;
		}
		ts = require("res://addons/gode/tsc/lib/typescript.js");
		return ts;
	}

	function normalizePath(filePath) {
		return String(filePath || "").replace(/\\/g, "/");
	}

	function isRelativeModuleName(moduleName) {
		return moduleName.startsWith("./") || moduleName.startsWith("../");
	}

	function resourceDirname(filePath) {
		const normalized = normalizePath(filePath);
		const slash = normalized.lastIndexOf("/");
		return slash >= 0 ? normalized.slice(0, slash) : "";
	}

	function normalizeResourcePath(filePath) {
		const normalized = normalizePath(filePath);
		const hasResourcePrefix = normalized.startsWith("res://");
		const prefix = hasResourcePrefix ? "res://" : "";
		const body = hasResourcePrefix ? normalized.slice("res://".length) : normalized;
		const segments = [];
		for (const part of body.split("/")) {
			if (!part || part === ".") {
				continue;
			}
			if (part === "..") {
				if (segments.length > 0) {
					segments.pop();
				}
				continue;
			}
			segments.push(part);
		}
		return prefix + segments.join("/");
	}

	function sourceModuleBasePath(moduleName, containingFile) {
		if (moduleName.startsWith("res://")) {
			return normalizeResourcePath(moduleName);
		}
		if (!isRelativeModuleName(moduleName)) {
			return "";
		}
		return normalizeResourcePath(`${resourceDirname(containingFile)}/${moduleName}`);
	}

	function pushUnique(array, value) {
		if (!array.includes(value)) {
			array.push(value);
		}
	}

	function sourceModuleCandidates(moduleName, containingFile) {
		const base = sourceModuleBasePath(moduleName, containingFile);
		if (!base) {
			return [];
		}

		const candidates = [];
		const lower = base.toLowerCase();
		const runtimeExtensions = [".js", ".jsx", ".mjs", ".cjs"];
		for (const extension of runtimeExtensions) {
			if (lower.endsWith(extension)) {
				const stem = base.slice(0, -extension.length);
				if (extension === ".jsx") {
					pushUnique(candidates, `${stem}.tsx`);
					pushUnique(candidates, `${stem}.ts`);
				} else {
					pushUnique(candidates, `${stem}.ts`);
					pushUnique(candidates, `${stem}.tsx`);
				}
				pushUnique(candidates, `${stem}.d.ts`);
				pushUnique(candidates, base);
				return candidates;
			}
		}

		if (lower.endsWith(".ts") || lower.endsWith(".tsx") || lower.endsWith(".d.ts")) {
			pushUnique(candidates, base);
			return candidates;
		}

		pushUnique(candidates, `${base}.ts`);
		pushUnique(candidates, `${base}.tsx`);
		pushUnique(candidates, `${base}.d.ts`);
		pushUnique(candidates, `${base}/index.ts`);
		pushUnique(candidates, `${base}/index.tsx`);
		pushUnique(candidates, `${base}/index.d.ts`);
		return candidates;
	}

	function sourceFileExtension(tsApi, filePath) {
		const lower = normalizePath(filePath).toLowerCase();
		if (lower.endsWith(".d.ts")) {
			return tsApi.Extension.Dts;
		}
		if (lower.endsWith(".tsx")) {
			return tsApi.Extension.Tsx;
		}
		if (lower.endsWith(".ts")) {
			return tsApi.Extension.Ts;
		}
		if (lower.endsWith(".jsx")) {
			return tsApi.Extension.Jsx;
		}
		return tsApi.Extension.Js;
	}

	function resolveSourceModule(tsApi, baseHost, moduleName, containingFile) {
		for (const candidate of sourceModuleCandidates(moduleName, containingFile)) {
			if (!baseHost.fileExists(candidate)) {
				continue;
			}
			return {
				resolvedFileName: candidate,
				extension: sourceFileExtension(tsApi, candidate),
				isExternalLibraryImport: candidate.includes("/node_modules/")
			};
		}
		return undefined;
	}

	function parentDirs(filePath) {
		const dirs = [];
		let dir = path.dirname(filePath);
		while (dir && dir !== "." && !dirs.includes(dir)) {
			dirs.push(dir);
			const parent = path.dirname(dir);
			if (parent === dir) {
				break;
			}
			dir = parent;
		}
		return dirs;
	}

	function createSourceContext(sources) {
		const sourceMap = new Map();
		const directories = new Set(["res://"]);

		for (const source of sources) {
			const filePath = normalizePath(source.path);
			sourceMap.set(filePath, String(source.source || ""));
			for (const dir of parentDirs(filePath)) {
				directories.add(dir);
			}
		}

		return {
			sourceMap,
			sourceFiles: Array.from(sourceMap.keys()).sort(),
			directories
		};
	}

	function normalizeDirectoryPath(directoryName) {
		let normalized = normalizePath(directoryName);
		while (normalized.length > "res://".length && normalized.endsWith("/")) {
			normalized = normalized.slice(0, -1);
		}
		return normalized;
	}

	function isUnderDirectory(filePath, directoryName) {
		const normalizedDirectory = normalizeDirectoryPath(directoryName);
		if (normalizedDirectory === "res://") {
			return filePath.startsWith("res://");
		}
		return filePath === normalizedDirectory || filePath.startsWith(`${normalizedDirectory}/`);
	}

	function matchesExtension(filePath, extensions) {
		if (!Array.isArray(extensions) || extensions.length === 0) {
			return true;
		}
		const lower = filePath.toLowerCase();
		return extensions.some((extension) => lower.endsWith(String(extension).toLowerCase()));
	}

	function categoryName(tsApi, category) {
		switch (category) {
			case tsApi.DiagnosticCategory.Warning:
				return "warning";
			case tsApi.DiagnosticCategory.Message:
				return "message";
			case tsApi.DiagnosticCategory.Suggestion:
				return "suggestion";
			default:
				return "error";
		}
	}

	function diagnosticToObject(tsApi, diagnostic) {
		const file = diagnostic.file;
		const position = file && typeof diagnostic.start === "number"
			? file.getLineAndCharacterOfPosition(diagnostic.start)
			: null;
		return {
			category: categoryName(tsApi, diagnostic.category),
			code: diagnostic.code || 0,
			message: tsApi.flattenDiagnosticMessageText(diagnostic.messageText, "\n"),
			file: file ? normalizePath(file.fileName) : "",
			line: position ? position.line + 1 : 0,
			column: position ? position.character + 1 : 0
		};
	}

	function readTsConfig(tsApi, host) {
		const configPath = "res://tsconfig.json";
		if (!fs.existsSync(configPath)) {
			return { options: {}, diagnostics: [] };
		}

		const config = tsApi.readConfigFile(configPath, host.readFile);
		if (config.error) {
			return { options: {}, diagnostics: [config.error] };
		}

		const parsed = tsApi.parseJsonConfigFileContent(
			config.config,
			{
					useCaseSensitiveFileNames: true,
					fileExists: host.fileExists,
					readFile: host.readFile,
					readDirectory: host.readDirectory,
					getCurrentDirectory: () => "res://",
					onUnRecoverableConfigFileDiagnostic: () => {}
				},
			"res://"
		);

		return {
			options: parsed.options || {},
			diagnostics: parsed.errors || []
		};
	}

	function createBaseHost(context) {
		const readFile = (fileName) => {
			const normalized = normalizePath(fileName);
			if (context.sourceMap.has(normalized)) {
				return context.sourceMap.get(normalized);
			}
			if (!fs.existsSync(normalized)) {
				return undefined;
			}
			return fs.readFileSync(normalized, "utf8");
		};

		const fileExists = (fileName) => {
			const normalized = normalizePath(fileName);
			return context.sourceMap.has(normalized) || fs.existsSync(normalized);
		};

		const directoryExists = (directoryName) => {
			const normalized = normalizeDirectoryPath(directoryName);
			if (context.directories.has(normalized)) {
				return true;
			}
			return fs.existsSync(normalized) && fs.statSync(normalized).isDirectory();
		};

		const readDirectory = (directoryName, extensions) => context.sourceFiles.filter((filePath) => {
			return isUnderDirectory(filePath, directoryName) && matchesExtension(filePath, extensions);
		});

		return {
			fileExists,
			readFile,
			directoryExists,
			readDirectory
		};
	}

	function createHost(tsApi, context, options) {
		const baseHost = createBaseHost(context);
		const host = tsApi.createCompilerHost(options, true);
		host.useCaseSensitiveFileNames = () => true;
		host.getCurrentDirectory = () => "res://";
		host.getCanonicalFileName = (fileName) => normalizePath(fileName);
		host.getNewLine = () => "\n";
		host.fileExists = baseHost.fileExists;
		host.readFile = baseHost.readFile;
		host.directoryExists = baseHost.directoryExists;
		host.readDirectory = baseHost.readDirectory;
		host.getDirectories = () => [];
		host.writeFile = () => {};
		host.getSourceFile = (fileName, languageVersion) => {
			const source = baseHost.readFile(fileName);
			if (source === undefined) {
				return undefined;
			}
			return tsApi.createSourceFile(normalizePath(fileName), source, languageVersion, true);
		};
			host.resolveModuleNames = (moduleNames, containingFile) => moduleNames.map((moduleName) => {
				if (moduleName === "godot") {
					return {
						resolvedFileName: "res://addons/gode/types/godot.d.ts",
						extension: tsApi.Extension.Dts,
						isExternalLibraryImport: false
					};
				}
				const sourceResolved = resolveSourceModule(tsApi, baseHost, moduleName, normalizePath(containingFile));
				if (sourceResolved) {
					return sourceResolved;
				}
				const resolved = tsApi.resolveModuleName(
					moduleName,
					normalizePath(containingFile),
					options,
				host
			).resolvedModule;
			return resolved || undefined;
		});

		return host;
	}

	function defaultCompilerOptions(tsApi) {
		return {
			target: tsApi.ScriptTarget.ES2022,
			module: tsApi.ModuleKind.ESNext,
			moduleResolution: tsApi.ModuleResolutionKind.Bundler || tsApi.ModuleResolutionKind.Node10,
			strict: true,
			isolatedModules: true,
			forceConsistentCasingInFileNames: true,
			useDefineForClassFields: true,
			esModuleInterop: true,
			allowSyntheticDefaultImports: true,
			experimentalDecorators: true,
			skipLibCheck: true,
			types: [],
			sourceMap: true,
			inlineSources: true,
			declaration: false,
			noEmit: true
		};
	}

	function isEmittableSource(filePath) {
		const normalized = normalizePath(filePath).toLowerCase();
		return (normalized.endsWith(".ts") || normalized.endsWith(".tsx")) && !normalized.endsWith(".d.ts");
	}

	globalThis.__gode_compile_typescript_project = function(files) {
			try {
				const tsApi = getTypescript();
				const sources = Array.isArray(files) ? files : [];
				const context = createSourceContext(sources);
				const baseHost = createBaseHost(context);
				const config = readTsConfig(tsApi, baseHost);
				const compilerOptions = {
					...defaultCompilerOptions(tsApi),
				...config.options,
				module: tsApi.ModuleKind.ESNext,
				moduleResolution: tsApi.ModuleResolutionKind.Bundler || tsApi.ModuleResolutionKind.Node10,
				noEmit: true,
				sourceMap: true,
				inlineSources: true,
					declaration: false,
					allowImportingTsExtensions: false
				};
				const host = createHost(tsApi, context, compilerOptions);
			const rootNames = sources.map((source) => normalizePath(source.path));
			for (const internalType of ["res://addons/gode/types/globals.d.ts"]) {
				if (fs.existsSync(internalType) && !rootNames.includes(internalType)) {
					rootNames.push(internalType);
				}
			}

			const program = tsApi.createProgram(rootNames, compilerOptions, host);
			const diagnostics = [...config.diagnostics, ...tsApi.getPreEmitDiagnostics(program)];
			const emitOptions = {
				...compilerOptions,
				noEmit: false,
				noEmitOnError: false
			};
			const outputs = [];

			for (const source of sources) {
				const sourcePath = normalizePath(source.path);
				if (!isEmittableSource(sourcePath)) {
					continue;
				}
				const result = tsApi.transpileModule(String(source.source || ""), {
					compilerOptions: emitOptions,
					fileName: sourcePath,
					reportDiagnostics: true
				});
				outputs.push({
					source: sourcePath,
					code: result.outputText || "",
					sourceMap: result.sourceMapText || ""
				});
				if (result.diagnostics) {
					diagnostics.push(...result.diagnostics);
				}
			}

			const diagnosticsOut = diagnostics.map((diagnostic) => diagnosticToObject(tsApi, diagnostic));
			const hasErrors = diagnostics.some((diagnostic) => diagnostic.category === tsApi.DiagnosticCategory.Error);
			return {
				ok: !hasErrors,
				outputs,
				diagnostics: diagnosticsOut
			};
		} catch (error) {
			return {
				ok: false,
				outputs: [],
				diagnostics: [{
					category: "error",
					code: 0,
					message: error && (error.stack || error.message) || String(error),
					file: "",
					line: 0,
					column: 0
				}]
			};
		}
	};
})();
