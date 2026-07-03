@tool
extends EditorExportPlugin

const GODE_CONFIG_PATH := "res://gode.json"
const DEFAULT_GODE_CONFIG_PATH := "res://addons/gode/config/gode.json"

const NPM_MANIFEST_FILES := [
	"package.json",
	"package-lock.json",
	"npm-shrinkwrap.json",
	"pnpm-lock.yaml",
	"yarn.lock",
	"bun.lock",
	"bun.lockb",
	".npmrc",
	".yarnrc",
	".yarnrc.yml",
]

var npm_exported_files := 0
var npm_config: Dictionary = {}
var config_error := ""

func _get_name() -> String:
	return "GodeTypeScriptExport"

func _export_begin(features: PackedStringArray, is_debug: bool, path: String, flags: int) -> void:
	npm_exported_files = 0
	var has_npm_project := _has_npm_project()
	npm_config = _load_npm_config(has_npm_project)
	if not config_error.is_empty():
		push_error(config_error)
		return
	if not _prepare_npm_export():
		return

	var compiler := GodeTypeScriptCompiler.new()
	var result: Dictionary = compiler.compile_project(true)
	if not result.get("ok", false):
		_print_diagnostics(result.get("diagnostics", []))
		push_error("Gode TypeScript export failed. Fix TypeScript diagnostics before exporting.")
		return

	for output: Dictionary in result.get("outputs", []):
		var source_path: String = output.get("path", "")
		var exported_path: String = output.get("exported_path", "")
		_add_compiled_file(exported_path, source_path)
		if is_debug:
			_add_compiled_file(exported_path + ".map", source_path + ".map")

	if _should_export_npm_dependencies() and has_npm_project:
		if not _export_npm_runtime_snapshot():
			return
		if npm_exported_files > 0:
			print("[Gode Export] Added npm runtime snapshot files: %d" % npm_exported_files)

func _add_compiled_file(exported_path: String, source_path: String) -> void:
	if exported_path.is_empty() or source_path.is_empty():
		return
	if not FileAccess.file_exists(source_path):
		push_error("Missing Gode TypeScript output: %s" % source_path)
		return
	add_file(exported_path, FileAccess.get_file_as_bytes(source_path), false)

func _print_diagnostics(diagnostics: Array) -> void:
	for diagnostic: Dictionary in diagnostics:
		var message: String = diagnostic.get("message", "")
		var file: String = diagnostic.get("file", "")
		var line: int = diagnostic.get("line", 0)
		var column: int = diagnostic.get("column", 0)
		if file.is_empty():
			push_error("[Gode TypeScript] %s" % message)
		else:
			push_error("[Gode TypeScript] %s:%d:%d %s" % [file, line, column, message])

func _prepare_npm_export() -> bool:
	if not _has_npm_project():
		return true
	if not _get_npm_bool("requireTools"):
		return _validate_npm_layout()

	if not _command_exists("node"):
		push_error("Gode export found npm project files in the project root, but Node.js was not found in PATH.")
		return false
	if not _command_exists("npm"):
		push_error("Gode export found npm project files in the project root, but npm was not found in PATH.")
		return false
	return _validate_npm_layout()

func _validate_npm_layout() -> bool:
	var package_json := _read_package_json()
	if _package_has_dependencies(package_json) and not _dir_exists("res://node_modules"):
		push_error("Gode export found dependencies in package.json, but res://node_modules is missing. Run your package manager install command before exporting.")
		return false
	return true

func _has_npm_project() -> bool:
	return _file_exists("res://package.json") or _dir_exists("res://node_modules")

func _should_export_npm_dependencies() -> bool:
	return _get_npm_bool("exportDependencies")

func _command_exists(command: String) -> bool:
	var candidates := PackedStringArray([command])
	if OS.get_name() == "Windows":
		candidates.append(command + ".cmd")
		candidates.append(command + ".exe")

	for candidate in candidates:
		var output: Array = []
		var exit_code := OS.execute(candidate, PackedStringArray(["--version"]), output, true, false)
		if exit_code == 0:
			return true
	return false

func _export_npm_runtime_snapshot() -> bool:
	if _get_npm_bool("includeManifests"):
		for manifest: String in NPM_MANIFEST_FILES:
			var manifest_path := "res://" + manifest
			if _file_exists(manifest_path):
				if not _add_export_file(manifest_path):
					return false

	if _get_npm_bool("includeNodeModules") and _dir_exists("res://node_modules"):
		if not _add_export_directory("res://node_modules"):
			return false

	for extra_path: String in _get_npm_string_array("extraIncludePaths"):
		var normalized := _normalize_res_path(extra_path)
		if normalized.is_empty():
			continue
		if _file_exists(normalized):
			if not _add_export_file(normalized):
				return false
		elif _dir_exists(normalized):
			if not _add_export_directory(normalized):
				return false
		else:
			push_warning("Gode export extra npm include path does not exist: %s" % normalized)
	return true

func _add_export_directory(directory_path: String) -> bool:
	if _is_excluded_export_path(directory_path):
		return true

	for file_name in DirAccess.get_files_at(directory_path):
		var file_path := directory_path.path_join(file_name)
		if _is_excluded_export_path(file_path):
			continue
		if not _add_export_file(file_path):
			return false

	for directory_name in DirAccess.get_directories_at(directory_path):
		var child_path := directory_path.path_join(directory_name)
		if not _add_export_directory(child_path):
			return false
	return true

func _add_export_file(source_path: String) -> bool:
	if _is_excluded_export_path(source_path):
		return true

	if not _file_exists(source_path):
		push_error("Gode export expected file does not exist: %s" % source_path)
		return false
	add_file(source_path, FileAccess.get_file_as_bytes(source_path), false)
	npm_exported_files += 1
	return true

func _read_package_json() -> Dictionary:
	if not _file_exists("res://package.json"):
		return {}
	var parsed := JSON.parse_string(FileAccess.get_file_as_string("res://package.json"))
	if typeof(parsed) == TYPE_DICTIONARY:
		return parsed
	push_warning("Gode export could not parse res://package.json.")
	return {}

func _package_has_dependencies(package_json: Dictionary) -> bool:
	for key in ["dependencies", "devDependencies", "optionalDependencies", "peerDependencies"]:
		if package_json.has(key) and typeof(package_json[key]) == TYPE_DICTIONARY and not package_json[key].is_empty():
			return true
	return false

func _is_excluded_export_path(path: String) -> bool:
	var rel_path := _to_resource_relative(path)
	for raw_pattern in _get_npm_string_array("excludePaths"):
		var pattern := _to_resource_relative(_normalize_res_path(raw_pattern))
		if pattern.is_empty():
			continue
		if rel_path == pattern or rel_path.begins_with(pattern.trim_suffix("/") + "/"):
			return true
	return false

func _load_npm_config(should_create_project_config: bool) -> Dictionary:
	config_error = ""
	var config := _default_npm_config()
	if not _file_exists(GODE_CONFIG_PATH):
		if not should_create_project_config:
			return config
		if not _create_project_gode_config():
			return config

	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(GODE_CONFIG_PATH))
	if typeof(parsed) != TYPE_DICTIONARY:
		config_error = "Gode config must be a JSON object: %s" % GODE_CONFIG_PATH
		return config

	var root: Dictionary = parsed
	var export_value: Variant = root.get("export", {})
	if typeof(export_value) != TYPE_DICTIONARY:
		config_error = "Gode config field export must be an object: %s" % GODE_CONFIG_PATH
		return config

	var export_config: Dictionary = export_value
	var npm_value: Variant = export_config.get("npm", {})
	if typeof(npm_value) != TYPE_DICTIONARY:
		config_error = "Gode config field export.npm must be an object: %s" % GODE_CONFIG_PATH
		return config

	var user_config: Dictionary = npm_value
	for key_value in user_config.keys():
		var key := String(key_value)
		if not config.has(key):
			push_warning("Unknown Gode npm export config key ignored: export.npm.%s" % key)
			continue
		_merge_npm_config_value(config, key, user_config[key_value])
	return config

func _create_project_gode_config() -> bool:
	if not _file_exists(DEFAULT_GODE_CONFIG_PATH):
		config_error = "Gode default config template is missing: %s" % DEFAULT_GODE_CONFIG_PATH
		return false

	var default_config := FileAccess.get_file_as_string(DEFAULT_GODE_CONFIG_PATH)
	if typeof(JSON.parse_string(default_config)) != TYPE_DICTIONARY:
		config_error = "Gode default config template must be a JSON object: %s" % DEFAULT_GODE_CONFIG_PATH
		return false

	var project_config := FileAccess.open(GODE_CONFIG_PATH, FileAccess.WRITE)
	if project_config == null:
		config_error = "Gode could not create project config: %s" % GODE_CONFIG_PATH
		return false

	project_config.store_string(default_config)
	project_config.close()
	print("[Gode Export] Created project config from template: %s" % GODE_CONFIG_PATH)
	return true

func _default_npm_config() -> Dictionary:
	return {
		"exportDependencies": true,
		"requireTools": true,
		"includeManifests": true,
		"includeNodeModules": true,
		"excludePaths": PackedStringArray(["node_modules/.cache", "node_modules/.bin"]),
		"extraIncludePaths": PackedStringArray(),
	}

func _merge_npm_config_value(config: Dictionary, key: String, value: Variant) -> void:
	if key in ["exportDependencies", "requireTools", "includeManifests", "includeNodeModules"]:
		if typeof(value) != TYPE_BOOL:
			config_error = "Gode config field export.npm.%s must be a boolean." % key
			return
		config[key] = value
		return

	if key in ["excludePaths", "extraIncludePaths"]:
		config[key] = _read_string_array_config(value, "export.npm.%s" % key)

func _read_string_array_config(value: Variant, field_name: String) -> PackedStringArray:
	var out := PackedStringArray()
	var values: Array = []
	if value is PackedStringArray:
		for item in value:
			out.append(String(item))
		return out
	if typeof(value) != TYPE_ARRAY:
		config_error = "Gode config field %s must be an array of strings." % field_name
		return out

	values = value
	for item in values:
		if typeof(item) != TYPE_STRING:
			config_error = "Gode config field %s must contain only strings." % field_name
			return PackedStringArray()
		out.append(String(item))
	return out

func _get_npm_bool(name: String) -> bool:
	return bool(npm_config.get(name, _default_npm_config().get(name, false)))

func _get_npm_string(name: String) -> String:
	return String(npm_config.get(name, _default_npm_config().get(name, "")))

func _get_npm_string_array(name: String) -> PackedStringArray:
	var value: Variant = npm_config.get(name, _default_npm_config().get(name, PackedStringArray()))
	if value is PackedStringArray:
		return value
	if value is Array:
		var out := PackedStringArray()
		for item in value:
			out.append(String(item))
		return out
	return PackedStringArray()

func _normalize_res_path(path: String) -> String:
	var normalized := path.strip_edges().replace("\\", "/")
	if normalized.is_empty():
		return ""
	if normalized.begins_with("res://"):
		return normalized
	return "res://" + normalized.trim_prefix("/")

func _to_resource_relative(path: String) -> String:
	return _normalize_res_path(path).trim_prefix("res://").trim_suffix("/")

func _file_exists(path: String) -> bool:
	return FileAccess.file_exists(path)

func _dir_exists(path: String) -> bool:
	return DirAccess.open(path) != null
