@tool
extends EditorPlugin

var _init_button: Button


func _enable_plugin() -> void:
	add_autoload_singleton("EventLoop", "res://addons/gode/script/event_loop.gd")


func _disable_plugin() -> void:
	remove_autoload_singleton("EventLoop")


func _enter_tree() -> void:
	add_autoload_singleton("EventLoop", "res://addons/gode/script/event_loop.gd")

	_init_button = Button.new()
	_init_button.text = "Init TS Project"
	_init_button.tooltip_text = "Initialize TypeScript / gode project (tsconfig, package.json, npm install)"
	_init_button.pressed.connect(_on_init_pressed)
	add_control_to_container(EditorPlugin.CONTAINER_TOOLBAR, _init_button)


func _exit_tree() -> void:
	remove_autoload_singleton("EventLoop")

	if _init_button:
		remove_control_from_container(EditorPlugin.CONTAINER_TOOLBAR, _init_button)
		_init_button.queue_free()
		_init_button = null


func _on_init_pressed() -> void:
	var project_dir := ProjectSettings.globalize_path("res://")
	var plugin_path := (get_script() as GDScript).resource_path
	var addon_dir   := ProjectSettings.globalize_path(plugin_path.get_base_dir())

	var is_windows  := OS.get_name() == "Windows"
	var script_name := "init.bat" if is_windows else "init.sh"
	var init_script := addon_dir + "/" + script_name

	if not FileAccess.file_exists(init_script):
		OS.alert("%s not found in:\n%s" % [script_name, addon_dir], "gode: Init Failed")
		return

	var output    := []
	var exit_code: int

	if is_windows:
		exit_code = OS.execute("cmd.exe", ["/c", init_script, project_dir], output, true)
	else:
		exit_code = OS.execute("bash", [init_script, project_dir], output, true)

	var log_text := "\n".join(output)

	if exit_code == 0:
		OS.alert("Project initialized!\n\n" + log_text, "gode: Done")
	else:
		OS.alert("Init failed (exit %d):\n\n%s" % [exit_code, log_text], "gode: Failed")
