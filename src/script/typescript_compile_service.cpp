#include "script/typescript_compile_service.h"

#include <godot_cpp/classes/engine.hpp>
#include <godot_cpp/classes/file_access.hpp>
#include <godot_cpp/classes/json.hpp>
#include <godot_cpp/classes/os.hpp>
#include <godot_cpp/classes/project_settings.hpp>
#include <godot_cpp/core/class_db.hpp>
#include <godot_cpp/variant/array.hpp>
#include <godot_cpp/variant/dictionary.hpp>
#include <godot_cpp/variant/packed_string_array.hpp>
#include <godot_cpp/variant/utility_functions.hpp>

#include <mutex>

using namespace godot;

namespace gode {
namespace {

constexpr const char *TYPESCRIPT_BUILD_ROOT = "res://.gode/build/typescript";
constexpr const char *GODE_TYPESCRIPT_COMPILER_CLASS = "GodeTypeScriptCompiler";

struct ExportManifestCache {
	bool loaded = false;
	bool valid = false;
	Array outputs;
};

std::mutex &export_manifest_mutex() {
	static std::mutex mutex;
	return mutex;
}

ExportManifestCache &export_manifest_cache() {
	static ExportManifestCache cache;
	return cache;
}

String normalize_path_string(const String &path) {
	return path.replace("\\", "/").simplify_path();
}

bool path_has_parent_segment(const String &path) {
	String normalized = path.replace("\\", "/");
	PackedStringArray segments = normalized.split("/", false);
	for (int64_t i = 0; i < segments.size(); i++) {
		if (segments[i] == "..") {
			return true;
		}
	}
	return false;
}

String normalize_project_path(const String &path) {
	String normalized = normalize_path_string(path);
	if (normalized.begins_with("res://")) {
		return normalized;
	}
	ProjectSettings *project_settings = ProjectSettings::get_singleton();
	if (project_settings) {
		String localized = normalize_path_string(project_settings->localize_path(normalized));
		if (localized.begins_with("res://")) {
			return localized;
		}
	}
	return normalized;
}

String resource_relative_path(const String &source_path) {
	String normalized = normalize_project_path(source_path);
	if (normalized.begins_with("res://")) {
		return normalized.substr(6);
	}
	return normalized;
}

String exported_build_root() {
	return TYPESCRIPT_BUILD_ROOT;
}

String exported_manifest_path() {
	return exported_build_root().path_join("manifest.json");
}

String compiled_path_for_source_internal(const String &source_path) {
	String rel = resource_relative_path(source_path);
	return exported_build_root().path_join(rel.get_basename() + ".js");
}

bool path_has_extension(const String &path, const String &extension) {
	return path.to_lower().ends_with(extension);
}

bool source_output_path_is_valid(const String &path) {
	if (path_has_parent_segment(path)) {
		return false;
	}

	String normalized = normalize_project_path(path);
	return normalized.begins_with("res://") &&
			(path_has_extension(normalized, ".ts") || path_has_extension(normalized, ".tsx")) &&
			!path_has_extension(normalized, ".d.ts");
}

bool normalize_typescript_source_path(const String &path, String &r_source_path, String *r_error = nullptr) {
	if (path_has_parent_segment(path)) {
		if (r_error) {
			*r_error = "TypeScript source path cannot contain parent-directory segments: " + path;
		}
		return false;
	}

	String normalized = normalize_project_path(path);
	if (!source_output_path_is_valid(normalized)) {
		if (r_error) {
			*r_error = "Invalid TypeScript source path, expected a .ts or .tsx file under res://: " + path;
		}
		return false;
	}

	r_source_path = normalized;
	return true;
}

bool output_string_field_is_valid(const Dictionary &output, const String &field) {
	Variant value = output.get(field, Variant());
	return value.get_type() == Variant::STRING && !String(value).is_empty();
}

bool path_is_under_root(const String &path, const String &root_path) {
	if (path_has_parent_segment(path) || path_has_parent_segment(root_path)) {
		return false;
	}

	String normalized_path = normalize_path_string(path);
	String root = normalize_path_string(root_path).trim_suffix("/");
	return normalized_path == root || normalized_path.begins_with(root + String("/"));
}

bool output_entry_is_valid(const Variant &output_value) {
	if (output_value.get_type() != Variant::DICTIONARY) {
		return false;
	}

	Dictionary output = output_value;
	if (!output_string_field_is_valid(output, "source") || !output_string_field_is_valid(output, "exported_path")) {
		return false;
	}
	if (!source_output_path_is_valid(String(output["source"]))) {
		return false;
	}
	if (!path_is_under_root(String(output["exported_path"]), exported_build_root()) || !path_has_extension(String(output["exported_path"]), ".js")) {
		return false;
	}
	return true;
}

bool output_for_source(const Array &outputs, const String &source_path, Dictionary &r_output) {
	const String normalized_source_path = normalize_project_path(source_path);
	for (int64_t i = 0; i < outputs.size(); i++) {
		Variant output_value = outputs[i];
		if (!output_entry_is_valid(output_value)) {
			continue;
		}

		Dictionary output = output_value;
		String output_source = output.get("source", String());
		if (normalize_project_path(output_source) == normalized_source_path) {
			r_output = output;
			return true;
		}
	}
	return false;
}

bool load_exported_manifest_outputs(Array &r_outputs) {
	std::lock_guard<std::mutex> lock(export_manifest_mutex());
	ExportManifestCache &cache = export_manifest_cache();
	if (cache.loaded) {
		if (!cache.valid) {
			return false;
		}
		r_outputs = cache.outputs;
		return true;
	}

	cache.loaded = true;
	String content = FileAccess::get_file_as_string(exported_manifest_path());
	if (FileAccess::get_open_error() != OK) {
		cache.valid = false;
		return false;
	}

	Variant parsed = JSON::parse_string(content);
	if (parsed.get_type() != Variant::DICTIONARY) {
		cache.valid = false;
		return false;
	}

	Dictionary manifest = parsed;
	Variant outputs_value = manifest.get("outputs", Array());
	if (outputs_value.get_type() != Variant::ARRAY) {
		cache.valid = false;
		return false;
	}

	Array outputs = outputs_value;
	for (int64_t i = 0; i < outputs.size(); i++) {
		if (!output_entry_is_valid(outputs[i])) {
			cache.valid = false;
			return false;
		}
	}

	cache.valid = true;
	cache.outputs = outputs;
	r_outputs = cache.outputs;
	return true;
}

void print_diagnostics(const Array &diagnostics) {
	for (int64_t i = 0; i < diagnostics.size(); i++) {
		Variant diagnostic_value = diagnostics[i];
		if (diagnostic_value.get_type() != Variant::DICTIONARY) {
			continue;
		}
		Dictionary diagnostic = diagnostic_value;
		String message = diagnostic.has("message") ? String(diagnostic["message"]) : String();
		String file = diagnostic.has("file") ? String(diagnostic["file"]) : String();
		int64_t line = diagnostic.has("line") ? int64_t(diagnostic["line"]) : 0;
		int64_t column = diagnostic.has("column") ? int64_t(diagnostic["column"]) : 0;
		if (!file.is_empty()) {
			UtilityFunctions::printerr("[Gode TypeScript] ", file, ":", line, ":", column, " ", message);
		} else if (!message.is_empty()) {
			UtilityFunctions::printerr("[Gode TypeScript] ", message);
		}
	}
}

Dictionary make_error_result(const String &message) {
	Dictionary diagnostic;
	diagnostic["category"] = "error";
	diagnostic["code"] = 0;
	diagnostic["message"] = message;
	diagnostic["file"] = String();
	diagnostic["line"] = 0;
	diagnostic["column"] = 0;

	Array diagnostics;
	diagnostics.append(diagnostic);

	Dictionary result;
	result["ok"] = false;
	result["compiled"] = 0;
	result["outputs"] = Array();
	result["diagnostics"] = diagnostics;
	result["cached"] = false;
	result["retryable"] = true;
	result["message"] = message;
	return result;
}

Dictionary compile_with_editor_service(const String &source_path) {
	const StringName compiler_class(GODE_TYPESCRIPT_COMPILER_CLASS);
	const StringName compile_method("compile_script");
	if (!ClassDB::class_exists(compiler_class) || !ClassDB::class_has_method(compiler_class, compile_method)) {
		return make_error_result("Gode editor TypeScript compiler service is not loaded.");
	}

	Variant result = ClassDB::class_call_static(compiler_class, compile_method, source_path, false);
	if (result.get_type() != Variant::DICTIONARY) {
		return make_error_result("Gode editor TypeScript compiler service returned an invalid result.");
	}
	return result;
}

bool ensure_from_export_manifest(const String &source_path, String *r_compiled_path, bool *r_retryable_failure) {
	Array exported_outputs;
	if (!load_exported_manifest_outputs(exported_outputs)) {
		UtilityFunctions::printerr("[Gode TypeScript] Exported TypeScript manifest is missing or invalid: ", exported_manifest_path());
		if (r_retryable_failure) {
			*r_retryable_failure = false;
		}
		return false;
	}

	Dictionary output;
	if (!output_for_source(exported_outputs, source_path, output)) {
		UtilityFunctions::printerr("[Gode TypeScript] Source was not included in the exported TypeScript manifest: ", source_path);
		if (r_retryable_failure) {
			*r_retryable_failure = false;
		}
		return false;
	}

	String exported_path = output.get("exported_path", compiled_path_for_source_internal(source_path));
	if (!FileAccess::file_exists(exported_path)) {
		UtilityFunctions::printerr("[Gode TypeScript] Exported TypeScript output is missing: ", exported_path);
		if (r_retryable_failure) {
			*r_retryable_failure = false;
		}
		return false;
	}

	if (r_compiled_path) {
		*r_compiled_path = exported_path;
	}
	if (r_retryable_failure) {
		*r_retryable_failure = false;
	}
	return true;
}

bool ensure_from_editor_compiler(const String &source_path, String *r_compiled_path, bool *r_retryable_failure) {
	Dictionary result = compile_with_editor_service(source_path);
	if (!bool(result.get("ok", false))) {
		if (!bool(result.get("cached", false))) {
			Array diagnostics = result.has("diagnostics") ? Array(result["diagnostics"]) : Array();
			print_diagnostics(diagnostics);
		}
		if (r_retryable_failure) {
			*r_retryable_failure = bool(result.get("retryable", true));
		}
		return false;
	}

	Array outputs = result.has("outputs") ? Array(result["outputs"]) : Array();
	Dictionary output;
	if (!output_for_source(outputs, source_path, output)) {
		UtilityFunctions::printerr("[Gode TypeScript] Source was not emitted by the active TypeScript project: ", source_path);
		if (r_retryable_failure) {
			*r_retryable_failure = false;
		}
		return false;
	}

	String compiled_path = output.get("path", compiled_path_for_source_internal(source_path));
	if (!FileAccess::file_exists(compiled_path)) {
		UtilityFunctions::printerr("[Gode TypeScript] Compiled output was not generated: ", compiled_path);
		if (r_retryable_failure) {
			*r_retryable_failure = true;
		}
		return false;
	}

	if (r_compiled_path) {
		*r_compiled_path = compiled_path;
	}
	if (r_retryable_failure) {
		*r_retryable_failure = false;
	}
	return true;
}

bool is_export_runtime_process() {
	Engine *engine = Engine::get_singleton();
	if (engine && engine->is_editor_hint()) {
		return false;
	}

	OS *os = OS::get_singleton();
	return !os || !os->has_feature("editor");
}

} // namespace

bool ensure_typescript_script_compiled(const String &p_source_path, String *r_compiled_path, bool *r_retryable_failure) {
	if (r_retryable_failure) {
		*r_retryable_failure = true;
	}

	String source_path;
	String path_error;
	if (!normalize_typescript_source_path(p_source_path, source_path, &path_error)) {
		UtilityFunctions::printerr("[Gode TypeScript] ", path_error);
		if (r_retryable_failure) {
			*r_retryable_failure = false;
		}
		return false;
	}

	if (is_export_runtime_process()) {
		return ensure_from_export_manifest(source_path, r_compiled_path, r_retryable_failure);
	}

	return ensure_from_editor_compiler(source_path, r_compiled_path, r_retryable_failure);
}

} // namespace gode
