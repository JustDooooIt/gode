#ifndef GODE_TYPESCRIPT_COMPILER_H
#define GODE_TYPESCRIPT_COMPILER_H

#include <godot_cpp/core/object.hpp>
#include <godot_cpp/variant/dictionary.hpp>
#include <godot_cpp/variant/string.hpp>

namespace gode {

class GodeTypeScriptCompiler : public godot::Object {
	GDCLASS(GodeTypeScriptCompiler, godot::Object)

protected:
	static void _bind_methods();

public:
	static godot::Dictionary compile_project(bool p_force = false);
	static godot::Dictionary compile_script(const godot::String &p_source_path, bool p_force = false);
	static godot::String get_compiled_path(const godot::String &p_source_path);
	static godot::String get_exported_path(const godot::String &p_source_path);
	static godot::String get_cache_root();
	static void clear_compile_cache();
};

} // namespace gode

#endif // GODE_TYPESCRIPT_COMPILER_H
