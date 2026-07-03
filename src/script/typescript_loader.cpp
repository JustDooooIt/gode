#include "script/typescript_loader.h"
#include "godot_cpp/classes/resource_uid.hpp"
#include "script/typescript_script.h"
#include <godot_cpp/classes/file_access.hpp>
#include <godot_cpp/classes/resource_loader.hpp>

using namespace godot;
using namespace gode;

TypeScriptLoader *TypeScriptLoader::singleton = nullptr;

TypeScriptLoader *TypeScriptLoader::get_singleton() {
	if (singleton) {
		return singleton;
	}
	singleton = memnew(TypeScriptLoader);
	return singleton;
}

TypeScriptLoader::~TypeScriptLoader() {
	clear_cache();
	if (singleton == this) {
		singleton = nullptr;
	}
}

void TypeScriptLoader::clear_cache() {
	scripts.clear();
}

PackedStringArray TypeScriptLoader::_get_recognized_extensions() const {
	PackedStringArray arr;
	arr.push_back(String("ts"));
	arr.push_back(String("tsx"));
	return arr;
}

bool TypeScriptLoader::_recognize_path(const String &p_path, const StringName &p_type) const {
	String ext = p_path.get_extension().to_lower();
	return ext == String("ts") || ext == String("tsx");
}

bool TypeScriptLoader::_handles_type(const StringName &p_type) const {
	return p_type == StringName("Script");
}

String TypeScriptLoader::_get_resource_type(const String &p_path) const {
	String ext = p_path.get_extension().to_lower();
	if (ext == String("ts") || ext == String("tsx")) {
		return String("Script");
	}
	return String();
}

String TypeScriptLoader::_get_resource_script_class(const String &p_path) const {
	return String();
}

int64_t TypeScriptLoader::_get_resource_uid(const String &p_path) const {
	return ResourceUID::get_singleton()->text_to_id(p_path);
}

PackedStringArray TypeScriptLoader::_get_dependencies(const String &p_path, bool p_add_types) const {
	return PackedStringArray();
}

Error TypeScriptLoader::_rename_dependencies(const String &p_path, const Dictionary &p_renames) const {
	return Error::OK;
}

bool TypeScriptLoader::_exists(const String &p_path) const {
	return FileAccess::file_exists(p_path);
}

PackedStringArray TypeScriptLoader::_get_classes_used(const String &p_path) const {
	return PackedStringArray();
}

Variant TypeScriptLoader::_load(const String &p_path, const String &p_original_path, bool p_use_sub_threads, int32_t p_cache_mode) const {
	if (p_cache_mode == ResourceLoader::CacheMode::CACHE_MODE_REUSE && scripts.has(p_path)) {
		return scripts.get(p_path);
	}

	String source_code = FileAccess::get_file_as_string(p_original_path);
	TypeScriptScript *script = memnew(TypeScriptScript);
	script->_set_source_code(source_code);
	scripts[p_path] = Ref(script);
	return script;
}
