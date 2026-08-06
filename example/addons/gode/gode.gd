@tool
extends EditorPlugin

const RUNTIME_EXTENSION_PATH := "res://addons/gode/binary/gode.gdextension"
const EDITOR_EXTENSION_PATH := "res://addons/gode/binary/gode_editor.gdextension"
const LOCAL_EXTENSION_LIST_PATH := "res://.godot/extension_list.cfg"

var export_plugin: EditorExportPlugin

func _enter_tree() -> void:
	_setup_plugin()

func _exit_tree() -> void:
	_teardown_editor_session()

func _enable_plugin() -> void:
	_setup_plugin()

func _disable_plugin() -> void:
	_teardown_editor_session()
	if ProjectSettings.has_setting("autoload/EventLoop"):
		remove_autoload_singleton("EventLoop")

func _setup_plugin() -> void:
	var command_line_export := _is_command_line_export()
	_ensure_native_extension_registered(RUNTIME_EXTENSION_PATH)
	if not command_line_export:
		_ensure_local_native_extension_registered(EDITOR_EXTENSION_PATH)
	_ensure_native_extension_loaded(RUNTIME_EXTENSION_PATH)
	_ensure_native_extension_loaded(EDITOR_EXTENSION_PATH)
	if not ProjectSettings.has_setting("autoload/EventLoop"):
		add_autoload_singleton("EventLoop", "res://addons/gode/runtime/event_loop.gd")
	if export_plugin == null:
		export_plugin = preload("res://addons/gode/runtime/export_plugin.gd").new()
		add_export_plugin(export_plugin)

func _teardown_editor_session() -> void:
	if export_plugin != null:
		remove_export_plugin(export_plugin)
		export_plugin = null

func _ensure_native_extension_loaded(path: String) -> void:
	if not FileAccess.file_exists(path):
		push_error("Gode native extension manifest is missing: %s" % path)
		return
	if GDExtensionManager.is_extension_loaded(path):
		return
	var status := GDExtensionManager.load_extension(path)
	if status != GDExtensionManager.LOAD_STATUS_OK and status != GDExtensionManager.LOAD_STATUS_ALREADY_LOADED:
		push_error("Failed to load Gode native extension %s, status %d" % [path, status])

func _ensure_native_extension_registered(path: String) -> void:
	var value: Variant = ProjectSettings.get_setting("native_extensions/paths", PackedStringArray())
	var paths := PackedStringArray()
	if typeof(value) == TYPE_PACKED_STRING_ARRAY:
		paths = value
	elif typeof(value) == TYPE_ARRAY:
		var array: Array = value
		for item in array:
			paths.append(String(item))
	var normalized_paths := PackedStringArray()
	var changed := false
	for existing_path: String in paths:
		var normalized_path := existing_path.strip_edges()
		if normalized_path == EDITOR_EXTENSION_PATH:
			changed = true
			continue
		if normalized_path.is_empty() or normalized_paths.has(normalized_path):
			changed = true
			continue
		normalized_paths.append(normalized_path)
	if normalized_paths.has(path) and not changed:
		return
	if not normalized_paths.has(path):
		normalized_paths.append(path)
		changed = true
	ProjectSettings.set_setting("native_extensions/paths", normalized_paths)
	ProjectSettings.save()

func _ensure_local_native_extension_registered(path: String) -> void:
	if not FileAccess.file_exists(path):
		push_error("Gode native extension manifest is missing: %s" % path)
		return
	var lines := PackedStringArray()
	if FileAccess.file_exists(LOCAL_EXTENSION_LIST_PATH):
		var content := FileAccess.get_file_as_string(LOCAL_EXTENSION_LIST_PATH)
		if FileAccess.get_open_error() != OK:
			push_error("Failed to read local GDExtension list: %s" % LOCAL_EXTENSION_LIST_PATH)
			return
		lines = content.replace("\r\n", "\n").replace("\r", "\n").split("\n", false)
	for line: String in lines:
		if line.strip_edges() == path:
			return
	var extension_list_directory := ProjectSettings.globalize_path(LOCAL_EXTENSION_LIST_PATH.get_base_dir())
	if DirAccess.make_dir_recursive_absolute(extension_list_directory) != OK:
		push_error("Failed to create local GDExtension directory: %s" % LOCAL_EXTENSION_LIST_PATH.get_base_dir())
		return
	lines.append(path)
	var file := FileAccess.open(LOCAL_EXTENSION_LIST_PATH, FileAccess.WRITE)
	if file == null:
		push_error("Failed to write local GDExtension list: %s" % LOCAL_EXTENSION_LIST_PATH)
		return
	file.store_string("\n".join(lines) + "\n")

func _is_command_line_export() -> bool:
	for argument: String in OS.get_cmdline_args():
		if argument in ["--export-release", "--export-debug", "--export-pack", "--export-patch"]:
			return true
	return false
