#ifndef GODOT_JAVASCRIPT_LOADER_H
#define GODOT_JAVASCRIPT_LOADER_H

#include "support/javascript/javascript.h"
#include <godot_cpp/classes/resource_format_loader.hpp>
#include <godot_cpp/templates/hash_map.hpp>

using namespace godot;

namespace gode {

class JavascriptLoader : public ResourceFormatLoader {
	GDCLASS(JavascriptLoader, ResourceFormatLoader);

private:
	JavascriptLoader() = default;

public:
	~JavascriptLoader();
	static JavascriptLoader *get_singleton();

private:
	static JavascriptLoader *singleton;
	mutable HashMap<StringName, Ref<Javascript>> scripts;

protected:
	static void _bind_methods();

public:
	PackedStringArray _get_recognized_extensions() const override;
	bool _recognize_path(const String &p_path, const StringName &p_type) const override;
	bool _handles_type(const StringName &p_type) const override;
	String _get_resource_type(const String &p_path) const override;
	String _get_resource_script_class(const String &p_path) const override;
	int64_t _get_resource_uid(const String &p_path) const override;
	PackedStringArray _get_dependencies(const String &p_path, bool p_add_types) const override;
	Error _rename_dependencies(const String &p_path, const Dictionary &p_renames) const override;
	bool _exists(const String &p_path) const override;
	PackedStringArray _get_classes_used(const String &p_path) const override;
	Variant _load(const String &p_path, const String &p_original_path, bool p_use_sub_threads, int32_t p_cache_mode) const override;
};
} //namespace gode

#endif // GODOT_JAVASCRIPT_LOADER_H
