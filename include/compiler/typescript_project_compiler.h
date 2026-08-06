#ifndef GODE_TYPESCRIPT_PROJECT_COMPILER_H
#define GODE_TYPESCRIPT_PROJECT_COMPILER_H

#include <godot_cpp/variant/dictionary.hpp>
#include <godot_cpp/variant/string.hpp>

namespace gode {

godot::Dictionary compile_typescript_project(bool p_force = false);
godot::Dictionary compile_typescript_source(const godot::String &p_source_path, bool p_force = false);
godot::String get_typescript_compiled_path(const godot::String &p_source_path);
godot::String get_typescript_exported_path(const godot::String &p_source_path);
godot::String get_typescript_cache_root();
void clear_typescript_project_compile_cache();

} // namespace gode

#endif // GODE_TYPESCRIPT_PROJECT_COMPILER_H
