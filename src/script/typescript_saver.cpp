#include "script/typescript_saver.h"
#include "script/typescript_script.h"
#include <godot_cpp/classes/file_access.hpp>
#include <godot_cpp/classes/resource_saver.hpp>
#include <godot_cpp/classes/resource_uid.hpp>

using namespace godot;
using namespace gode;

TypeScriptSaver *TypeScriptSaver::singleton = nullptr;

static bool is_typescript_script_path(const String &path) {
	const String lower = path.to_lower();
	return (lower.ends_with(".ts") || lower.ends_with(".tsx")) && !lower.ends_with(".d.ts");
}

TypeScriptSaver *TypeScriptSaver::get_singleton() {
	if (singleton) {
		return singleton;
	}
	singleton = memnew(TypeScriptSaver);
	return singleton;
}

TypeScriptSaver::~TypeScriptSaver() {
	if (singleton == this) {
		singleton = nullptr;
	}
}

Error TypeScriptSaver::_save(const Ref<Resource> &p_resource, const String &p_path, uint32_t p_flags) {
	Ref<TypeScriptScript> ts = p_resource;
	if (!ts.is_valid()) {
		return Error::ERR_INVALID_PARAMETER;
	}
	Ref<FileAccess> file = FileAccess::open(p_path, FileAccess::WRITE);
	if (!file.is_valid()) {
		return Error::ERR_CANT_OPEN;
	}
	file->store_string(ts->_get_source_code());
	file->close();
	return Error::OK;
}

Error TypeScriptSaver::_set_uid(const String &p_path, int64_t p_uid) {
	ResourceUID::get_singleton()->set_id(p_uid, p_path);
	return Error::OK;
}

bool TypeScriptSaver::_recognize(const Ref<Resource> &p_resource) const {
	if (!p_resource.is_valid()) {
		return false;
	}
	return is_typescript_script_path(p_resource->get_path());
}

PackedStringArray TypeScriptSaver::_get_recognized_extensions(const Ref<Resource> &p_resource) const {
	PackedStringArray arr;
	arr.push_back(String("ts"));
	arr.push_back(String("tsx"));
	return arr;
}

bool TypeScriptSaver::_recognize_path(const Ref<Resource> &p_resource, const String &p_path) const {
	return is_typescript_script_path(p_path);
}
