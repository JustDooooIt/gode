#include "support/typescript/typescript_loader.h"
#include "godot_cpp/classes/resource_uid.hpp"
#include "support/typescript/typescript.h"
#include <godot_cpp/classes/file_access.hpp>
#include <godot_cpp/classes/resource_loader.hpp>
#include <regex>
#include <unordered_set>

using namespace godot;
using namespace gode;

namespace {

String resolve_script_dependency(const String &p_owner_path, const String &p_dependency, const char *p_default_extension) {
	if (p_dependency.begins_with("res://") || p_dependency.begins_with("uid://")) {
		return p_dependency;
	}
	if (p_dependency.begins_with("./") || p_dependency.begins_with("../")) {
		String resolved = p_owner_path.get_base_dir().path_join(p_dependency).simplify_path();
		if (resolved.get_extension().is_empty()) {
			resolved += ".";
			resolved += p_default_extension;
		}
		return resolved;
	}
	return String();
}

PackedStringArray scan_script_dependencies(const String &p_path, const char *p_default_extension) {
	PackedStringArray deps;
	if (!FileAccess::file_exists(p_path)) {
		return deps;
	}

	std::string source = FileAccess::get_file_as_string(p_path).utf8().get_data();
	std::unordered_set<std::string> seen;
	const std::regex patterns[] = {
		std::regex(R"((?:preload|load|require)\s*\(\s*["']([^"']+)["'])"),
		std::regex(R"(ResourceLoader\s*\.\s*load\s*\(\s*["']([^"']+)["'])"),
		std::regex(R"(import\s+(?:[^"']+\s+from\s+)?["']([^"']+)["'])")
	};

	for (const std::regex &pattern : patterns) {
		for (std::sregex_iterator it(source.begin(), source.end(), pattern), end; it != end; ++it) {
			String dep = resolve_script_dependency(p_path, String((*it)[1].str().c_str()), p_default_extension);
			if (dep.is_empty()) {
				continue;
			}
			std::string key = dep.utf8().get_data();
			if (seen.insert(key).second) {
				deps.push_back(dep);
			}
		}
	}

	return deps;
}

} // namespace

TypescriptLoader *TypescriptLoader::singleton = nullptr;

TypescriptLoader *TypescriptLoader::get_singleton() {
	if (singleton) {
		return singleton;
	}
	singleton = memnew(TypescriptLoader);
	return singleton;
}

TypescriptLoader::~TypescriptLoader() {
	if (singleton == this) {
		singleton = nullptr;
	}
}

PackedStringArray TypescriptLoader::_get_recognized_extensions() const {
	PackedStringArray arr;
	arr.push_back(String("ts"));
	arr.push_back(String("tsx"));
	return arr;
}

bool TypescriptLoader::_recognize_path(const String &p_path, const StringName &p_type) const {
	String ext = p_path.get_extension().to_lower();
	return ext == String("ts") || ext == String("tsx");
}

bool TypescriptLoader::_handles_type(const StringName &p_type) const {
	return p_type == StringName("Script");
}

String TypescriptLoader::_get_resource_type(const String &p_path) const {
	String ext = p_path.get_extension().to_lower();
	if (ext == String("ts") || ext == String("tsx")) {
		return String("Script");
	}
	return String();
}

String TypescriptLoader::_get_resource_script_class(const String &p_path) const {
	Ref<Typescript> script;
	if (scripts.has(p_path)) {
		script = scripts.get(p_path);
	} else if (FileAccess::file_exists(p_path)) {
		Typescript *loaded = memnew(Typescript);
		loaded->_set_source_code(FileAccess::get_file_as_string(p_path));
		script = Ref<Typescript>(loaded);
		scripts[p_path] = script;
	}
	if (script.is_valid()) {
		StringName global_name = script->_get_global_name();
		if (global_name != StringName()) {
			return String(global_name);
		}
	}
	return String();
}

int64_t TypescriptLoader::_get_resource_uid(const String &p_path) const {
	return ResourceUID::get_singleton()->text_to_id(p_path);
}

PackedStringArray TypescriptLoader::_get_dependencies(const String &p_path, bool p_add_types) const {
	return scan_script_dependencies(p_path, "ts");
}

Error TypescriptLoader::_rename_dependencies(const String &p_path, const Dictionary &p_renames) const {
	return Error::OK;
}

bool TypescriptLoader::_exists(const String &p_path) const {
	return FileAccess::file_exists(p_path);
}

PackedStringArray TypescriptLoader::_get_classes_used(const String &p_path) const {
	PackedStringArray classes;
	String class_name = _get_resource_script_class(p_path);
	if (!class_name.is_empty()) {
		classes.push_back(class_name);
	}
	return classes;
}

Variant TypescriptLoader::_load(const String &p_path, const String &p_original_path, bool p_use_sub_threads, int32_t p_cache_mode) const {
	if (p_cache_mode == ResourceLoader::CacheMode::CACHE_MODE_REUSE && scripts.has(p_path)) {
		return scripts.get(p_path);
	}

	String source_code = FileAccess::get_file_as_string(p_original_path);
	Typescript *script = memnew(Typescript);
	script->_set_source_code(source_code);
	scripts[p_path] = Ref(script);
	return script;
}
