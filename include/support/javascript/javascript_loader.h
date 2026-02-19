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
    mutable HashMap<StringName, Ref<Javascript>> scripts;

public:
	PackedStringArray _get_recognized_extensions() const;
	bool _recognize_path(const String &p_path, const StringName &p_type) const;
	bool _handles_type(const StringName &p_type) const;
	String _get_resource_type(const String &p_path) const;
	String _get_resource_script_class(const String &p_path) const;
	int64_t _get_resource_uid(const String &p_path) const;
	PackedStringArray _get_dependencies(const String &p_path, bool p_add_types) const;
	Error _rename_dependencies(const String &p_path, const Dictionary &p_renames) const;
	bool _exists(const String &p_path) const;
	PackedStringArray _get_classes_used(const String &p_path) const;
	Variant _load(const String &p_path, const String &p_original_path, bool p_use_sub_threads, int32_t p_cache_mode) const;
};
} //namespace gode

#endif // GODOT_JAVASCRIPT_LOADER_H