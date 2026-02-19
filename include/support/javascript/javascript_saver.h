#ifndef GODOT_GODE_JAVASCRIPT_SAVER_H
#define GODOT_GODE_JAVASCRIPT_SAVER_H

#include <godot_cpp/classes/resource_format_saver.hpp>

using namespace godot;

namespace gode {

class JavascriptSaver : public ResourceFormatSaver {
	GDCLASS(JavascriptSaver, ResourceFormatSaver);

public:
	Error _save(const Ref<Resource> &p_resource, const String &p_path, uint32_t p_flags);
	Error _set_uid(const String &p_path, int64_t p_uid);
	bool _recognize(const Ref<Resource> &p_resource) const;
	PackedStringArray _get_recognized_extensions(const Ref<Resource> &p_resource) const;
	bool _recognize_path(const Ref<Resource> &p_resource, const String &p_path) const;
};
} //namespace gode

#endif // GODOT_GODE_JAVASCRIPT_SAVER_H