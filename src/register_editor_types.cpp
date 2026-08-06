#include "compiler/typescript_compiler.h"

#include <godot_cpp/core/class_db.hpp>
#include <godot_cpp/godot.hpp>

namespace {

void initialize_gode_editor_module(godot::ModuleInitializationLevel p_level) {
	if (p_level != godot::MODULE_INITIALIZATION_LEVEL_SCENE) {
		return;
	}
	GDREGISTER_CLASS(gode::GodeTypeScriptCompiler);
}

void uninitialize_gode_editor_module(godot::ModuleInitializationLevel p_level) {
	if (p_level != godot::MODULE_INITIALIZATION_LEVEL_SCENE) {
		return;
	}
	gode::GodeTypeScriptCompiler::clear_compile_cache();
}

} // namespace

extern "C" {

GDExtensionBool GDE_EXPORT gode_editor_library_init(GDExtensionInterfaceGetProcAddress p_get_proc_address, const GDExtensionClassLibraryPtr p_library, GDExtensionInitialization *r_initialization) {
	godot::GDExtensionBinding::InitObject init_obj(p_get_proc_address, p_library, r_initialization);

	init_obj.register_initializer(initialize_gode_editor_module);
	init_obj.register_terminator(uninitialize_gode_editor_module);
	init_obj.set_minimum_library_initialization_level(godot::MODULE_INITIALIZATION_LEVEL_SCENE);

	return init_obj.init();
}
}
