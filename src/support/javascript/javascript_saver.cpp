#include "support/javascript/javascript_saver.h"
#include <godot_cpp/classes/file_access.hpp>
#include <godot_cpp/classes/resource_format_saver.hpp>
#include <godot_cpp/classes/resource_saver.hpp>
#include <godot_cpp/classes/resource_uid.hpp>
#include "support/javascript/javascript.h"

using namespace godot;
using namespace gode;

Error JavascriptSaver::_save(const Ref<Resource> &p_resource, const String &p_path, uint32_t p_flags) {
	switch (p_flags) {
		case ResourceSaver::SaverFlags::FLAG_NONE: {
			Javascript *js = reinterpret_cast<Javascript *>(p_resource.ptr());
			String source_code = js->_get_source_code();
			Ref<FileAccess> file = FileAccess::open(p_path, FileAccess::WRITE);
			file->store_string(source_code);
            file->close();
		} break;
	}
	return Error::OK;
}

Error JavascriptSaver::_set_uid(const String &p_path, int64_t p_uid) {
	ResourceUID::get_singleton()->set_id(p_uid, p_path);
    return Error::OK;
}

bool JavascriptSaver::_recognize(const Ref<Resource> &p_resource) const {
	return true;
}

PackedStringArray JavascriptSaver::_get_recognized_extensions(const Ref<Resource> &p_resource) const {
	PackedStringArray arr;
	arr.push_back(String("js"));
	return arr;
}

bool JavascriptSaver::_recognize_path(const Ref<Resource> &p_resource, const String &p_path) const {
	return p_path.get_extension().to_lower() == String("js");
}
