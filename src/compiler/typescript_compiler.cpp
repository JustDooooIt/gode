#include "compiler/typescript_compiler.h"

#include "compiler/typescript_project_compiler.h"

#include <godot_cpp/core/class_db.hpp>

using namespace godot;

namespace gode {

void GodeTypeScriptCompiler::_bind_methods() {
	ClassDB::bind_static_method(get_class_static(), D_METHOD("compile_project", "force"), &GodeTypeScriptCompiler::compile_project, DEFVAL(false));
	ClassDB::bind_static_method(get_class_static(), D_METHOD("compile_script", "source_path", "force"), &GodeTypeScriptCompiler::compile_script, DEFVAL(false));
	ClassDB::bind_static_method(get_class_static(), D_METHOD("get_compiled_path", "source_path"), &GodeTypeScriptCompiler::get_compiled_path);
	ClassDB::bind_static_method(get_class_static(), D_METHOD("get_exported_path", "source_path"), &GodeTypeScriptCompiler::get_exported_path);
	ClassDB::bind_static_method(get_class_static(), D_METHOD("get_cache_root"), &GodeTypeScriptCompiler::get_cache_root);
	ClassDB::bind_static_method(get_class_static(), D_METHOD("clear_compile_cache"), &GodeTypeScriptCompiler::clear_compile_cache);
}

Dictionary GodeTypeScriptCompiler::compile_project(bool p_force) {
	return compile_typescript_project(p_force);
}

Dictionary GodeTypeScriptCompiler::compile_script(const String &p_source_path, bool p_force) {
	return compile_typescript_source(p_source_path, p_force);
}

String GodeTypeScriptCompiler::get_compiled_path(const String &p_source_path) {
	return get_typescript_compiled_path(p_source_path);
}

String GodeTypeScriptCompiler::get_exported_path(const String &p_source_path) {
	return get_typescript_exported_path(p_source_path);
}

String GodeTypeScriptCompiler::get_cache_root() {
	return get_typescript_cache_root();
}

void GodeTypeScriptCompiler::clear_compile_cache() {
	clear_typescript_project_compile_cache();
}

} // namespace gode
