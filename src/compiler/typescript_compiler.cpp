#include "compiler/typescript_compiler.h"

#include "runtime/node_runtime.h"

#include <godot_cpp/classes/dir_access.hpp>
#include <godot_cpp/classes/engine.hpp>
#include <godot_cpp/classes/file_access.hpp>
#include <godot_cpp/classes/json.hpp>
#include <godot_cpp/classes/project_settings.hpp>
#include <godot_cpp/core/class_db.hpp>
#include <godot_cpp/variant/packed_string_array.hpp>
#include <godot_cpp/variant/utility_functions.hpp>

#include <mutex>

using namespace godot;

namespace gode {
namespace {

constexpr const char *TYPESCRIPT_COMPILER_BRIDGE_PATH = "res://addons/gode/runtime/typescript_compiler.js";
constexpr const char *TYPESCRIPT_RUNTIME_PATH = "res://addons/gode/tsc/lib/typescript.js";
constexpr const char *PROJECT_TYPESCRIPT_CONFIG_PATH = "res://tsconfig.json";
constexpr const char *DEFAULT_TYPESCRIPT_CONFIG_PATH = "res://addons/gode/config/tsconfig.json";
constexpr const char *GODE_GLOBAL_TYPES_PATH = "res://addons/gode/types/globals.d.ts";
constexpr const char *GODE_MODULE_TYPES_PATH = "res://addons/gode/types/godot.d.ts";
constexpr const char *TYPESCRIPT_BUILD_ROOT = "res://.gode/build/typescript";

std::mutex &typescript_compile_mutex() {
	static std::mutex mutex;
	return mutex;
}

bool is_dts_path(const String &path) {
	return path.to_lower().ends_with(".d.ts");
}

bool is_typescript_path(const String &path) {
	String lower = path.to_lower();
	return lower.ends_with(".ts") || lower.ends_with(".tsx");
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

String cache_root() {
	return TYPESCRIPT_BUILD_ROOT;
}

String exported_build_root() {
	return TYPESCRIPT_BUILD_ROOT;
}

String exported_manifest_path() {
	return exported_build_root().path_join("manifest.json");
}

bool should_skip_directory(const String &directory_path) {
	String rel = resource_relative_path(directory_path).trim_suffix("/");
	if (rel.is_empty()) {
		return false;
	}

	static const char *skipped_prefixes[] = {
		".godot",
		".gode",
		"node_modules",
		"addons/gode/tsc",
		"addons/gode/types"
	};

	for (const char *prefix : skipped_prefixes) {
		String skipped(prefix);
		if (rel == skipped || rel.begins_with(skipped + "/")) {
			return true;
		}
	}
	return false;
}

Dictionary make_error_diagnostic(const String &message, const String &file_path = String()) {
	Dictionary diagnostic;
	diagnostic["category"] = "error";
	diagnostic["code"] = 0;
	diagnostic["message"] = message;
	diagnostic["file"] = file_path;
	diagnostic["line"] = 0;
	diagnostic["column"] = 0;
	return diagnostic;
}

bool read_source_file(const String &path, Dictionary &file, Array &diagnostics) {
	String source = FileAccess::get_file_as_string(path);
	if (FileAccess::get_open_error() != OK) {
		diagnostics.append(make_error_diagnostic("Failed to read TypeScript source: " + path, path));
		return false;
	}
	file["path"] = path;
	file["source"] = source;
	return true;
}

void collect_sources_recursive(const String &directory_path, Array &sources, Array &diagnostics) {
	if (should_skip_directory(directory_path)) {
		return;
	}

	PackedStringArray files = DirAccess::get_files_at(directory_path);
	for (int64_t i = 0; i < files.size(); i++) {
		String file_name = files[i];
		String file_path = directory_path.path_join(file_name);
		if (!is_typescript_path(file_path) && !is_dts_path(file_path)) {
			continue;
		}
		Dictionary file;
		if (read_source_file(file_path, file, diagnostics)) {
			sources.append(file);
		}
	}

	PackedStringArray directories = DirAccess::get_directories_at(directory_path);
	for (int64_t i = 0; i < directories.size(); i++) {
		String child = directory_path.path_join(directories[i]);
		collect_sources_recursive(child, sources, diagnostics);
	}
}

Array collect_project_sources(Array &diagnostics) {
	Array sources;
	collect_sources_recursive("res://", sources, diagnostics);
	if (FileAccess::file_exists(GODE_GLOBAL_TYPES_PATH)) {
		Dictionary file;
		if (read_source_file(GODE_GLOBAL_TYPES_PATH, file, diagnostics)) {
			sources.append(file);
		}
	}
	return sources;
}

String compiled_path_for_source_internal(const String &source_path) {
	String rel = resource_relative_path(source_path);
	return cache_root().path_join(rel.get_basename() + ".js");
}

String exported_path_for_source_internal(const String &source_path) {
	String rel = resource_relative_path(source_path);
	return exported_build_root().path_join(rel.get_basename() + ".js");
}

Dictionary output_mapping_for_source(const String &source_path) {
	Dictionary output;
	output["source"] = source_path;
	output["path"] = compiled_path_for_source_internal(source_path);
	output["exported_path"] = exported_path_for_source_internal(source_path);
	return output;
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
	if (output.has("path")) {
		String output_path = output["path"];
		if (!output_string_field_is_valid(output, "path") ||
				!path_is_under_root(output_path, cache_root()) ||
				!path_has_extension(output_path, ".js")) {
			return false;
		}
	}
	return true;
}

bool manifest_outputs_are_valid(const Array &outputs) {
	for (int64_t i = 0; i < outputs.size(); i++) {
		if (!output_entry_is_valid(outputs[i])) {
			return false;
		}
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

Dictionary make_result(bool ok, const String &message = String()) {
	Dictionary result;
	result["ok"] = ok;
	result["compiled"] = 0;
	result["outputs"] = Array();
	result["diagnostics"] = Array();
	result["cache_root"] = cache_root();
	result["output_root"] = cache_root();
	if (!message.is_empty()) {
		Array diagnostics;
		diagnostics.append(make_error_diagnostic(message));
		result["diagnostics"] = diagnostics;
		result["message"] = message;
	}
	return result;
}

void append_error_diagnostic(Dictionary &result, const String &message) {
	Array diagnostics = result.has("diagnostics") ? Array(result["diagnostics"]) : Array();
	diagnostics.append(make_error_diagnostic(message));
	result["diagnostics"] = diagnostics;
	result["message"] = message;
	result["ok"] = false;
}

void print_diagnostics(const Array &diagnostics) {
	for (int64_t i = 0; i < diagnostics.size(); i++) {
		Dictionary diagnostic = diagnostics[i];
		String message = diagnostic.has("message") ? String(diagnostic["message"]) : String();
		String file = diagnostic.has("file") ? String(diagnostic["file"]) : String();
		int64_t line = diagnostic.has("line") ? int64_t(diagnostic["line"]) : 0;
		int64_t column = diagnostic.has("column") ? int64_t(diagnostic["column"]) : 0;
		if (!file.is_empty()) {
			UtilityFunctions::printerr("[Gode TypeScript] ", file, ":", line, ":", column, " ", message);
		} else {
			UtilityFunctions::printerr("[Gode TypeScript] ", message);
		}
	}
}

bool write_text_file(const String &path, const String &content) {
	Error dir_error = DirAccess::make_dir_recursive_absolute(path.get_base_dir());
	if (dir_error != OK) {
		return false;
	}
	Ref<FileAccess> file = FileAccess::open(path, FileAccess::WRITE);
	if (file.is_null()) {
		return false;
	}
	file->store_string(content);
	file->close();
	return true;
}

bool load_manifest(const String &path, Dictionary &r_manifest) {
	if (!FileAccess::file_exists(path)) {
		return false;
	}

	String content = FileAccess::get_file_as_string(path);
	if (FileAccess::get_open_error() != OK) {
		return false;
	}

	Variant parsed = JSON::parse_string(content);
	if (parsed.get_type() != Variant::DICTIONARY) {
		return false;
	}

	r_manifest = parsed;
	return true;
}

bool load_manifest_outputs_from_path(const String &path, Array &r_outputs) {
	Dictionary manifest;
	if (!load_manifest(path, manifest)) {
		return false;
	}

	Variant outputs_value = manifest.get("outputs", Array());
	if (outputs_value.get_type() != Variant::ARRAY) {
		return false;
	}

	Array outputs = outputs_value;
	if (!manifest_outputs_are_valid(outputs)) {
		return false;
	}

	r_outputs = outputs;
	return true;
}

bool remove_generated_file_if_safe(const String &path) {
	if (path.is_empty()) {
		return true;
	}

	String normalized_path = path.replace("\\", "/");
	if (!path_is_under_root(normalized_path, cache_root())) {
		return false;
	}
	if (!FileAccess::file_exists(normalized_path)) {
		return true;
	}

	Error remove_error = DirAccess::remove_absolute(normalized_path);
	if (remove_error != OK) {
		UtilityFunctions::printerr("[Gode TypeScript] Failed to remove generated output: ", normalized_path);
		return false;
	}
	return true;
}

bool clear_generated_directory_contents(const String &directory_path) {
	if (!path_is_under_root(directory_path, cache_root())) {
		return false;
	}
	if (!DirAccess::dir_exists_absolute(directory_path)) {
		return true;
	}

	PackedStringArray files = DirAccess::get_files_at(directory_path);
	for (int64_t i = 0; i < files.size(); i++) {
		String file_path = directory_path.path_join(files[i]);
		if (!remove_generated_file_if_safe(file_path)) {
			return false;
		}
	}

	PackedStringArray directories = DirAccess::get_directories_at(directory_path);
	for (int64_t i = 0; i < directories.size(); i++) {
		String child_path = directory_path.path_join(directories[i]);
		if (!clear_generated_directory_contents(child_path)) {
			return false;
		}
		Error remove_error = DirAccess::remove_absolute(child_path);
		if (remove_error != OK) {
			UtilityFunctions::printerr("[Gode TypeScript] Failed to remove generated output directory: ", child_path);
			return false;
		}
	}
	return true;
}

bool clear_generated_output_root() {
	return clear_generated_directory_contents(cache_root());
}

bool ensure_project_typescript_config(String *r_error) {
	if (FileAccess::file_exists(PROJECT_TYPESCRIPT_CONFIG_PATH)) {
		return true;
	}

	if (!FileAccess::file_exists(DEFAULT_TYPESCRIPT_CONFIG_PATH)) {
		if (r_error) {
			*r_error = "The packaged default TypeScript config is missing: " + String(DEFAULT_TYPESCRIPT_CONFIG_PATH);
		}
		return false;
	}

	String content = FileAccess::get_file_as_string(DEFAULT_TYPESCRIPT_CONFIG_PATH);
	if (FileAccess::get_open_error() != OK) {
		if (r_error) {
			*r_error = "Failed to read the packaged default TypeScript config: " + String(DEFAULT_TYPESCRIPT_CONFIG_PATH);
		}
		return false;
	}

	Ref<FileAccess> file = FileAccess::open(PROJECT_TYPESCRIPT_CONFIG_PATH, FileAccess::WRITE);
	if (file.is_null()) {
		if (r_error) {
			*r_error = "Project tsconfig.json is missing and Gode could not create " + String(PROJECT_TYPESCRIPT_CONFIG_PATH) + " from " + String(DEFAULT_TYPESCRIPT_CONFIG_PATH);
		}
		return false;
	}

	file->store_string(content);
	file->close();
	UtilityFunctions::print("[Gode TypeScript] Created default project config: ", PROJECT_TYPESCRIPT_CONFIG_PATH);
	return true;
}

Dictionary compile_project_internal(bool force) {
	(void)force;
	std::lock_guard<std::mutex> compile_lock(typescript_compile_mutex());

	if (!FileAccess::file_exists(TYPESCRIPT_RUNTIME_PATH)) {
		return make_result(false, "The packaged TypeScript compiler is missing: " + String(TYPESCRIPT_RUNTIME_PATH));
	}

	String config_error;
	if (!ensure_project_typescript_config(&config_error)) {
		return make_result(false, config_error);
	}

	Array source_diagnostics;
	Array sources = collect_project_sources(source_diagnostics);
	Dictionary result = make_result(true);
	if (!source_diagnostics.is_empty()) {
		result["ok"] = false;
		result["message"] = "Failed to read one or more TypeScript project sources.";
		result["diagnostics"] = source_diagnostics;
		return result;
	}

	if (!clear_generated_output_root()) {
		return make_result(false, "Failed to clear generated TypeScript output: " + cache_root());
	}

	Dictionary compile_result = NodeRuntime::compile_typescript_project(sources);
	Array diagnostics = compile_result.has("diagnostics") ? Array(compile_result["diagnostics"]) : Array();
	result["diagnostics"] = diagnostics;
	if (!bool(compile_result.get("ok", false))) {
		result["ok"] = false;
		result["message"] = "TypeScript compilation failed.";
		return result;
	}

	Array emitted_outputs = compile_result.has("outputs") ? Array(compile_result["outputs"]) : Array();
	Array actual_outputs;
	int64_t written_count = 0;
	for (int64_t i = 0; i < emitted_outputs.size(); i++) {
		Dictionary emitted = emitted_outputs[i];
		String source_path = emitted["source"];
		Dictionary output = output_mapping_for_source(source_path);
		String output_path = output["path"];
		String code = emitted["code"];
		String source_map = emitted.has("sourceMap") ? String(emitted["sourceMap"]) : String();
		String source_map_path = output_path + ".map";
		if (!write_text_file(output_path, code)) {
			return make_result(false, "Failed to write compiled TypeScript output: " + output_path);
		}
		if (!source_map.is_empty() && !write_text_file(source_map_path, source_map)) {
			return make_result(false, "Failed to write TypeScript source map: " + source_map_path);
		}
		actual_outputs.append(output);
		written_count++;
	}

	result["outputs"] = actual_outputs;
	result["compiled"] = written_count;
	return result;
}

} // namespace

void GodeTypeScriptCompiler::_bind_methods() {
	ClassDB::bind_method(D_METHOD("compile_project", "force"), &GodeTypeScriptCompiler::compile_project, DEFVAL(false));
	ClassDB::bind_method(D_METHOD("compile_script", "source_path", "force"), &GodeTypeScriptCompiler::compile_script, DEFVAL(false));
	ClassDB::bind_method(D_METHOD("get_compiled_path", "source_path"), &GodeTypeScriptCompiler::get_compiled_path);
	ClassDB::bind_method(D_METHOD("get_exported_path", "source_path"), &GodeTypeScriptCompiler::get_exported_path);
	ClassDB::bind_method(D_METHOD("get_cache_root"), &GodeTypeScriptCompiler::get_cache_root);
}

Dictionary GodeTypeScriptCompiler::compile_project(bool p_force) {
	return compile_project_internal(p_force);
}

Dictionary GodeTypeScriptCompiler::compile_script(const String &p_source_path, bool p_force) {
	String source_path;
	String path_error;
	if (!normalize_typescript_source_path(p_source_path, source_path, &path_error)) {
		Dictionary result = make_result(false, path_error);
		result["source"] = String();
		result["path"] = String();
		result["exported_path"] = String();
		return result;
	}

	Dictionary result = compile_project_internal(p_force);
	result["source"] = source_path;
	result["path"] = compiled_path_for_source_internal(source_path);
	result["exported_path"] = exported_path_for_source_internal(source_path);
	if (bool(result.get("ok", false))) {
		Array outputs = result.has("outputs") ? Array(result["outputs"]) : Array();
		Dictionary output;
		if (output_for_source(outputs, source_path, output)) {
			result["path"] = output.get("path", result["path"]);
			result["exported_path"] = output.get("exported_path", result["exported_path"]);
		} else {
			append_error_diagnostic(result, String("Source was not emitted by the active TypeScript project: ") + source_path);
		}
	}
	return result;
}

String GodeTypeScriptCompiler::get_compiled_path(const String &p_source_path) const {
	String source_path;
	if (!normalize_typescript_source_path(p_source_path, source_path)) {
		return String();
	}
	return compiled_path_for_source_internal(source_path);
}

String GodeTypeScriptCompiler::get_exported_path(const String &p_source_path) const {
	String source_path;
	if (!normalize_typescript_source_path(p_source_path, source_path)) {
		return String();
	}
	return exported_path_for_source_internal(source_path);
}

String GodeTypeScriptCompiler::get_cache_root() const {
	return cache_root();
}

String GodeTypeScriptCompiler::compiled_path_for_source(const String &p_source_path) {
	String source_path;
	if (!normalize_typescript_source_path(p_source_path, source_path)) {
		return String();
	}
	return compiled_path_for_source_internal(source_path);
}

String GodeTypeScriptCompiler::exported_path_for_source(const String &p_source_path) {
	String source_path;
	if (!normalize_typescript_source_path(p_source_path, source_path)) {
		return String();
	}
	return exported_path_for_source_internal(source_path);
}

bool GodeTypeScriptCompiler::ensure_script_compiled(const String &p_source_path, String *r_compiled_path) {
	String source_path;
	String path_error;
	if (!normalize_typescript_source_path(p_source_path, source_path, &path_error)) {
		UtilityFunctions::printerr("[Gode TypeScript] ", path_error);
		return false;
	}
	String exported_path = exported_path_for_source_internal(source_path);
	Engine *engine = Engine::get_singleton();
	if (engine && !engine->is_editor_hint()) {
		Array exported_outputs;
		if (load_manifest_outputs_from_path(exported_manifest_path(), exported_outputs)) {
			Dictionary output;
			if (!output_for_source(exported_outputs, source_path, output)) {
				UtilityFunctions::printerr("[Gode TypeScript] Source was not included in the exported TypeScript manifest: ", source_path);
				return false;
			}

			String manifest_exported_path = output.get("exported_path", exported_path);
			if (!FileAccess::file_exists(manifest_exported_path)) {
				UtilityFunctions::printerr("[Gode TypeScript] Exported TypeScript output is missing: ", manifest_exported_path);
				return false;
			}

			if (r_compiled_path) {
				*r_compiled_path = manifest_exported_path;
			}
			return true;
		}
	}

	Dictionary result = compile_project_internal(false);
	if (!bool(result.get("ok", false))) {
		Array diagnostics = result.has("diagnostics") ? Array(result["diagnostics"]) : Array();
		print_diagnostics(diagnostics);
		return false;
	}

	Array outputs = result.has("outputs") ? Array(result["outputs"]) : Array();
	Dictionary output;
	if (!output_for_source(outputs, source_path, output)) {
		UtilityFunctions::printerr("[Gode TypeScript] Source was not emitted by the active TypeScript project: ", source_path);
		return false;
	}

	String compiled_path = output.get("path", compiled_path_for_source_internal(source_path));
	if (!FileAccess::file_exists(compiled_path)) {
		UtilityFunctions::printerr("[Gode TypeScript] Compiled output was not generated: ", compiled_path);
		return false;
	}

	if (r_compiled_path) {
		*r_compiled_path = compiled_path;
	}
	return true;
}

} // namespace gode
