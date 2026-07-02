#include "register_types.h"
#include "napi.h"
#include "support/javascript.h"
#include "support/javascript_language.h"
#include "support/javascript_loader.h"
#include "support/javascript_saver.h"
#include "support/typescript.h"
#include "support/typescript_language.h"
#include "support/typescript_loader.h"
#include "support/typescript_saver.h"
#include "utils/gode_event_loop.h"
#include "utils/node_runtime.h"
#include <godot_cpp/classes/engine.hpp>
#include <godot_cpp/classes/ref.hpp>
#include <godot_cpp/classes/resource_loader.hpp>
#include <godot_cpp/classes/resource_saver.hpp>
#include <godot_cpp/core/class_db.hpp>
#include <godot_cpp/core/defs.hpp>
#include <godot_cpp/core/memory.hpp>
#include <godot_cpp/godot.hpp>

namespace {

godot::Ref<gode::JavascriptSaver> javascript_saver;
godot::Ref<gode::TypescriptSaver> typescript_saver;
godot::Ref<gode::JavascriptLoader> javascript_loader;
godot::Ref<gode::TypescriptLoader> typescript_loader;

} // namespace

void initialize_node_module(godot::ModuleInitializationLevel p_level) {
	if (p_level != godot::MODULE_INITIALIZATION_LEVEL_SCENE) {
		return;
	}
	GDREGISTER_CLASS(gode::Javascript);
	GDREGISTER_CLASS(gode::JavascriptLanguage);
	GDREGISTER_CLASS(gode::JavascriptSaver);
	GDREGISTER_CLASS(gode::JavascriptLoader);
	GDREGISTER_CLASS(gode::Typescript);
	GDREGISTER_CLASS(gode::TypescriptLanguage);
	GDREGISTER_CLASS(gode::TypescriptSaver);
	GDREGISTER_CLASS(gode::TypescriptLoader);
	GDREGISTER_CLASS(gode::GodeEventLoop);
	godot::Engine::get_singleton()->register_script_language(gode::JavascriptLanguage::get_singleton());
	godot::Engine::get_singleton()->register_script_language(gode::TypescriptLanguage::get_singleton());
	javascript_saver = gode::JavascriptSaver::get_singleton();
	typescript_saver = gode::TypescriptSaver::get_singleton();
	javascript_loader = gode::JavascriptLoader::get_singleton();
	typescript_loader = gode::TypescriptLoader::get_singleton();

	godot::ResourceSaver::get_singleton()->add_resource_format_saver(javascript_saver);
	godot::ResourceSaver::get_singleton()->add_resource_format_saver(typescript_saver);
	godot::ResourceLoader::get_singleton()->add_resource_format_loader(javascript_loader);
	godot::ResourceLoader::get_singleton()->add_resource_format_loader(typescript_loader);

	gode::NodeRuntime::init_once();
}

void uninitialize_node_module(godot::ModuleInitializationLevel p_level) {
	if (p_level != godot::MODULE_INITIALIZATION_LEVEL_SCENE) {
		return;
	}
	gode::JavascriptLanguage *javascript_language = gode::JavascriptLanguage::get_singleton();
	gode::TypescriptLanguage *typescript_language = gode::TypescriptLanguage::get_singleton();

	godot::Engine::get_singleton()->unregister_script_language(javascript_language);
	godot::Engine::get_singleton()->unregister_script_language(typescript_language);

	if (javascript_loader.is_valid()) {
		javascript_loader->clear_cache();
	}
	if (typescript_loader.is_valid()) {
		typescript_loader->clear_cache();
	}

	godot::ResourceSaver *resource_saver = godot::ResourceSaver::get_singleton();
	if (resource_saver) {
		if (javascript_saver.is_valid()) {
			resource_saver->remove_resource_format_saver(javascript_saver);
		}
		if (typescript_saver.is_valid()) {
			resource_saver->remove_resource_format_saver(typescript_saver);
		}
	}

	godot::ResourceLoader *resource_loader = godot::ResourceLoader::get_singleton();
	if (resource_loader) {
		if (javascript_loader.is_valid()) {
			resource_loader->remove_resource_format_loader(javascript_loader);
		}
		if (typescript_loader.is_valid()) {
			resource_loader->remove_resource_format_loader(typescript_loader);
		}
	}

	javascript_loader.unref();
	typescript_loader.unref();
	javascript_saver.unref();
	typescript_saver.unref();

	memdelete(typescript_language);
	memdelete(javascript_language);

	gode::NodeRuntime::shutdown();
}

extern "C" {
// Initialization.
GDExtensionBool GDE_EXPORT node_library_init(GDExtensionInterfaceGetProcAddress p_get_proc_address, const GDExtensionClassLibraryPtr p_library, GDExtensionInitialization *r_initialization) {
	godot::GDExtensionBinding::InitObject init_obj(p_get_proc_address, p_library, r_initialization);

	init_obj.register_initializer(initialize_node_module);
	init_obj.register_terminator(uninitialize_node_module);
	init_obj.set_minimum_library_initialization_level(godot::MODULE_INITIALIZATION_LEVEL_SCENE);

	return init_obj.init();
}
}
