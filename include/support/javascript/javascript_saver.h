#ifndef GODOT_GODE_JAVASCRIPT_SAVER_H
#define GODOT_GODE_JAVASCRIPT_SAVER_H

#include <godot_cpp/classes/resource_format_saver.hpp>

using namespace godot;

namespace gode {

class JavascriptSaver : public ResourceFormatSaver {
	GDCLASS(JavascriptSaver, ResourceFormatSaver);

private:
	JavascriptSaver() = default;

public:
	~JavascriptSaver();
	static JavascriptSaver *get_singleton();

private:
	static JavascriptSaver *singleton;

protected:
	static void _bind_methods();

public:
	Error _save(const Ref<Resource> &p_resource, const String &p_path, uint32_t p_flags) override;
	Error _set_uid(const String &p_path, int64_t p_uid) override;
	bool _recognize(const Ref<Resource> &p_resource) const override;
	PackedStringArray _get_recognized_extensions(const Ref<Resource> &p_resource) const override;
	bool _recognize_path(const Ref<Resource> &p_resource, const String &p_path) const override;
};
} //namespace gode

#endif // GODOT_GODE_JAVASCRIPT_SAVER_H
