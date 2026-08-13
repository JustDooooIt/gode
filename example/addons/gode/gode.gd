@tool
extends EditorPlugin

const RUNTIME_EXTENSION_PATH := "res://addons/gode/binary/gode.gdextension"
const EDITOR_EXTENSION_TEMPLATE_PATH := "res://addons/gode/binary/gode_editor.gdextension.template"
const EDITOR_EXTENSION_PATH := "res://.godot/gode/gode_editor.gdextension"
const LEGACY_EDITOR_EXTENSION_PATH := "res://addons/gode/binary/gode_editor.gdextension"
const LEGACY_EDITOR_EXTENSION_UID_PATH := "res://addons/gode/binary/gode_editor.gdextension.uid"
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
	_remove_legacy_editor_extension_resources()
	var editor_manifest_ready := _ensure_editor_extension_manifest()
	_ensure_native_extension_registered(RUNTIME_EXTENSION_PATH)
	if not command_line_export and editor_manifest_ready:
		_ensure_local_native_extension_registered(EDITOR_EXTENSION_PATH)
	_ensure_native_extension_loaded(RUNTIME_EXTENSION_PATH)
	if editor_manifest_ready:
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
		if _is_editor_extension_path(normalized_path):
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

	var filtered := PackedStringArray()
	var changed := false
	for line: String in lines:
		var normalized_path := line.strip_edges()
		if _is_editor_extension_path(normalized_path):
			if normalized_path == path and not filtered.has(path):
				filtered.append(path)
			else:
				changed = true
			continue
		if normalized_path.is_empty() or filtered.has(normalized_path):
			changed = true
			continue
		filtered.append(normalized_path)
	if filtered.has(path) and not changed:
		return
	var extension_list_directory := ProjectSettings.globalize_path(LOCAL_EXTENSION_LIST_PATH.get_base_dir())
	if DirAccess.make_dir_recursive_absolute(extension_list_directory) != OK:
		push_error("Failed to create local GDExtension directory: %s" % LOCAL_EXTENSION_LIST_PATH.get_base_dir())
		return
	if not filtered.has(path):
		filtered.append(path)
	var file := FileAccess.open(LOCAL_EXTENSION_LIST_PATH, FileAccess.WRITE)
	if file == null:
		push_error("Failed to write local GDExtension list: %s" % LOCAL_EXTENSION_LIST_PATH)
		return
	file.store_string("\n".join(filtered) + "\n")

func _ensure_editor_extension_manifest() -> bool:
	if not FileAccess.file_exists(EDITOR_EXTENSION_TEMPLATE_PATH):
		push_error("Gode editor extension template is missing: %s" % EDITOR_EXTENSION_TEMPLATE_PATH)
		return false

	var template := FileAccess.get_file_as_string(EDITOR_EXTENSION_TEMPLATE_PATH)
	if FileAccess.get_open_error() != OK:
		push_error("Failed to read Gode editor extension template: %s" % EDITOR_EXTENSION_TEMPLATE_PATH)
		return false

	if FileAccess.file_exists(EDITOR_EXTENSION_PATH):
		var current := FileAccess.get_file_as_string(EDITOR_EXTENSION_PATH)
		if FileAccess.get_open_error() == OK and current == template:
			return true

	var directory := ProjectSettings.globalize_path(EDITOR_EXTENSION_PATH.get_base_dir())
	if DirAccess.make_dir_recursive_absolute(directory) != OK:
		push_error("Failed to create local Gode editor extension directory: %s" % EDITOR_EXTENSION_PATH.get_base_dir())
		return false

	var file := FileAccess.open(EDITOR_EXTENSION_PATH, FileAccess.WRITE)
	if file == null:
		push_error("Failed to write local Gode editor extension manifest: %s" % EDITOR_EXTENSION_PATH)
		return false
	file.store_string(template)
	return true

func _remove_legacy_editor_extension_resources() -> void:
	for path in [LEGACY_EDITOR_EXTENSION_PATH, LEGACY_EDITOR_EXTENSION_UID_PATH]:
		if not FileAccess.file_exists(path):
			continue
		var remove_error := DirAccess.remove_absolute(ProjectSettings.globalize_path(path))
		if remove_error != OK:
			push_warning("Gode could not remove stale editor extension resource: %s" % path)

func _is_editor_extension_path(path: String) -> bool:
	return path == EDITOR_EXTENSION_PATH or path == LEGACY_EDITOR_EXTENSION_PATH

func _is_command_line_export() -> bool:
	for argument: String in OS.get_cmdline_args():
		if argument in ["--export-release", "--export-debug", "--export-pack", "--export-patch"]:
			return true
	return false
