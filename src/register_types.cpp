#include "register_types.h"
#include "utils/node_runtime.h"

#include "napi.h"
#include "support/javascript/javascript.h"
#include "support/javascript/javascript_language.h"
#include "support/javascript/javascript_loader.h"
#include "support/javascript/javascript_saver.h"
#include <godot_cpp/classes/engine.hpp>
#include <godot_cpp/classes/resource_loader.hpp>
#include <godot_cpp/classes/resource_saver.hpp>
#include <godot_cpp/core/class_db.hpp>
#include <godot_cpp/core/defs.hpp>
#include <godot_cpp/godot.hpp>

using namespace godot;

void initialize_node_module(ModuleInitializationLevel p_level) {
	if (p_level != MODULE_INITIALIZATION_LEVEL_SCENE) {
		return;
	}
	GDREGISTER_CLASS(gode::Javascript);
	GDREGISTER_CLASS(gode::JavascriptLanguage);
	GDREGISTER_CLASS(gode::JavascriptSaver);
	GDREGISTER_CLASS(gode::JavascriptLoader);
	Engine::get_singleton()->register_script_language(gode::JavascriptLanguage::get_singleton());
	ResourceSaver::get_singleton()->add_resource_format_saver(gode::JavascriptSaver::get_singleton());
	ResourceLoader::get_singleton()->add_resource_format_loader(gode::JavascriptLoader::get_singleton());

	static bool js_bootstrapped = false;
	if (!js_bootstrapped) {
		gode::NodeRuntime::run_script("require('gode')");
		js_bootstrapped = true;
	}
}

void uninitialize_node_module(ModuleInitializationLevel p_level) {
	if (p_level != MODULE_INITIALIZATION_LEVEL_SCENE) {
		return;
	}
	Engine::get_singleton()->unregister_script_language(gode::JavascriptLanguage::get_singleton());
	ResourceSaver::get_singleton()->remove_resource_format_saver(gode::JavascriptSaver::get_singleton());
	ResourceLoader::get_singleton()->remove_resource_format_loader(gode::JavascriptLoader::get_singleton());

	gode::NodeRuntime::shutdown();
}

extern "C" {
// Initialization.
GDExtensionBool GDE_EXPORT node_library_init(GDExtensionInterfaceGetProcAddress p_get_proc_address, const GDExtensionClassLibraryPtr p_library, GDExtensionInitialization *r_initialization) {
	godot::GDExtensionBinding::InitObject init_obj(p_get_proc_address, p_library, r_initialization);

	init_obj.register_initializer(initialize_node_module);
	init_obj.register_terminator(uninitialize_node_module);
	init_obj.set_minimum_library_initialization_level(MODULE_INITIALIZATION_LEVEL_SCENE);

	return init_obj.init();
}
}
