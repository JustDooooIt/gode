#include "compiler/typescript_compiler.h"

#include "runtime/node_runtime.h"

#include <godot_cpp/classes/dir_access.hpp>
#include <godot_cpp/classes/engine.hpp>
#include <godot_cpp/classes/file_access.hpp>
#include <godot_cpp/classes/project_settings.hpp>
#include <godot_cpp/core/class_db.hpp>
#include <godot_cpp/variant/packed_string_array.hpp>
#include <godot_cpp/variant/utility_functions.hpp>

#include <algorithm>

using namespace godot;

namespace gode {
namespace {

constexpr const char *TYPESCRIPT_VERSION = "6.0.3";
constexpr const char *TYPESCRIPT_RUNTIME_PATH = "res://addons/gode/tsc/lib/typescript.js";
constexpr const char *PROJECT_TYPESCRIPT_CONFIG_PATH = "res://tsconfig.json";
constexpr const char *DEFAULT_TYPESCRIPT_CONFIG_PATH = "res://addons/gode/config/tsconfig.json";
constexpr const char *GODE_GLOBAL_TYPES_PATH = "res://addons/gode/types/globals.d.ts";
constexpr const char *GODE_MODULE_TYPES_PATH = "res://addons/gode/types/godot.d.ts";

bool is_dts_path(const String &path) {
	return path.to_lower().ends_with(".d.ts");
}

bool is_typescript_path(const String &path) {
	String lower = path.to_lower();
	return lower.ends_with(".ts") || lower.ends_with(".tsx");
}

bool is_emittable_typescript_path(const String &path) {
	return is_typescript_path(path) && !is_dts_path(path);
}

String normalize_project_path(const String &path) {
	String normalized = path.replace("\\", "/");
	if (normalized.begins_with("res://")) {
		return normalized;
	}
	ProjectSettings *project_settings = ProjectSettings::get_singleton();
	if (project_settings) {
		String localized = project_settings->localize_path(normalized);
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

String project_hash() {
	ProjectSettings *project_settings = ProjectSettings::get_singleton();
	String project_root = project_settings ? project_settings->globalize_path("res://") : String("res://");
	String hash = project_root.sha256_text();
	return hash.substr(0, 16);
}

String cache_root() {
	return String("user://.gode/typescript/") + project_hash() + "/typescript-" + TYPESCRIPT_VERSION;
}

String exported_build_root() {
	return "res://.gode/build/typescript";
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

bool read_source_file(const String &path, Dictionary &file) {
	String source = FileAccess::get_file_as_string(path);
	if (FileAccess::get_open_error() != OK) {
		return false;
	}
	file["path"] = path;
	file["source"] = source;
	return true;
}

void collect_sources_recursive(const String &directory_path, Array &sources) {
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
		if (read_source_file(file_path, file)) {
			sources.append(file);
		}
	}

	PackedStringArray directories = DirAccess::get_directories_at(directory_path);
	for (int64_t i = 0; i < directories.size(); i++) {
		String child = directory_path.path_join(directories[i]);
		collect_sources_recursive(child, sources);
	}
}

Array collect_project_sources() {
	Array sources;
	collect_sources_recursive("res://", sources);
	if (FileAccess::file_exists(GODE_GLOBAL_TYPES_PATH)) {
		Dictionary file;
		if (read_source_file(GODE_GLOBAL_TYPES_PATH, file)) {
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

Array output_mappings_for_sources(const Array &sources) {
	Array outputs;
	for (int64_t i = 0; i < sources.size(); i++) {
		Dictionary source = sources[i];
		String source_path = source["path"];
		if (!is_emittable_typescript_path(source_path)) {
			continue;
		}
		Dictionary output;
		output["source"] = source_path;
		output["path"] = compiled_path_for_source_internal(source_path);
		output["exported_path"] = exported_path_for_source_internal(source_path);
		outputs.append(output);
	}
	return outputs;
}

uint64_t newest_input_mtime(const Array &sources) {
	uint64_t newest = 0;
	for (int64_t i = 0; i < sources.size(); i++) {
		Dictionary source = sources[i];
		String source_path = source["path"];
		if (FileAccess::file_exists(source_path)) {
			newest = std::max(newest, FileAccess::get_modified_time(source_path));
		}
	}
	if (FileAccess::file_exists(PROJECT_TYPESCRIPT_CONFIG_PATH)) {
		newest = std::max(newest, FileAccess::get_modified_time(PROJECT_TYPESCRIPT_CONFIG_PATH));
	}
	if (FileAccess::file_exists(TYPESCRIPT_RUNTIME_PATH)) {
		newest = std::max(newest, FileAccess::get_modified_time(TYPESCRIPT_RUNTIME_PATH));
	}
	if (FileAccess::file_exists(GODE_MODULE_TYPES_PATH)) {
		newest = std::max(newest, FileAccess::get_modified_time(GODE_MODULE_TYPES_PATH));
	}
	return newest;
}

bool outputs_are_fresh(const Array &outputs, uint64_t input_mtime) {
	for (int64_t i = 0; i < outputs.size(); i++) {
		Dictionary output = outputs[i];
		String output_path = output["path"];
		if (!FileAccess::file_exists(output_path)) {
			return false;
		}
		if (FileAccess::get_modified_time(output_path) < input_mtime) {
			return false;
		}
	}
	return true;
}

Dictionary make_result(bool ok, const String &message = String()) {
	Dictionary result;
	result["ok"] = ok;
	result["compiled"] = 0;
	result["skipped"] = 0;
	result["outputs"] = Array();
	result["diagnostics"] = Array();
	result["cache_root"] = cache_root();
	if (!message.is_empty()) {
		Array diagnostics;
		Dictionary diagnostic;
		diagnostic["category"] = "error";
		diagnostic["code"] = 0;
		diagnostic["message"] = message;
		diagnostic["file"] = "";
		diagnostic["line"] = 0;
		diagnostic["column"] = 0;
		diagnostics.append(diagnostic);
		result["diagnostics"] = diagnostics;
		result["message"] = message;
	}
	return result;
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
	if (!FileAccess::file_exists(TYPESCRIPT_RUNTIME_PATH)) {
		return make_result(false, "The packaged TypeScript compiler is missing: " + String(TYPESCRIPT_RUNTIME_PATH));
	}

	String config_error;
	if (!ensure_project_typescript_config(&config_error)) {
		return make_result(false, config_error);
	}

	Array sources = collect_project_sources();
	Array output_mappings = output_mappings_for_sources(sources);
	Dictionary result = make_result(true);
	result["outputs"] = output_mappings;

	if (output_mappings.is_empty()) {
		return result;
	}

	uint64_t newest_input = newest_input_mtime(sources);
	if (!force && outputs_are_fresh(output_mappings, newest_input)) {
		result["skipped"] = output_mappings.size();
		return result;
	}

	Dictionary compile_result = NodeRuntime::compile_typescript_project(sources);
	Array diagnostics = compile_result.has("diagnostics") ? Array(compile_result["diagnostics"]) : Array();
	result["diagnostics"] = diagnostics;
	if (!bool(compile_result.get("ok", false))) {
		print_diagnostics(diagnostics);
		result["ok"] = false;
		result["message"] = "TypeScript compilation failed.";
		return result;
	}

	Array emitted_outputs = compile_result.has("outputs") ? Array(compile_result["outputs"]) : Array();
	int64_t written_count = 0;
	for (int64_t i = 0; i < emitted_outputs.size(); i++) {
		Dictionary emitted = emitted_outputs[i];
		String source_path = emitted["source"];
		String output_path = compiled_path_for_source_internal(source_path);
		String code = emitted["code"];
		String source_map = emitted.has("sourceMap") ? String(emitted["sourceMap"]) : String();
		if (!write_text_file(output_path, code)) {
			return make_result(false, "Failed to write compiled TypeScript output: " + output_path);
		}
		if (!source_map.is_empty() && !write_text_file(output_path + ".map", source_map)) {
			return make_result(false, "Failed to write TypeScript source map: " + output_path + ".map");
		}
		written_count++;
	}

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
	Dictionary result = compile_project_internal(p_force);
	result["source"] = normalize_project_path(p_source_path);
	result["path"] = compiled_path_for_source_internal(p_source_path);
	result["exported_path"] = exported_path_for_source_internal(p_source_path);
	return result;
}

String GodeTypeScriptCompiler::get_compiled_path(const String &p_source_path) const {
	return compiled_path_for_source_internal(p_source_path);
}

String GodeTypeScriptCompiler::get_exported_path(const String &p_source_path) const {
	return exported_path_for_source_internal(p_source_path);
}

String GodeTypeScriptCompiler::get_cache_root() const {
	return cache_root();
}

String GodeTypeScriptCompiler::compiled_path_for_source(const String &p_source_path) {
	return compiled_path_for_source_internal(p_source_path);
}

String GodeTypeScriptCompiler::exported_path_for_source(const String &p_source_path) {
	return exported_path_for_source_internal(p_source_path);
}

bool GodeTypeScriptCompiler::ensure_script_compiled(const String &p_source_path, String *r_compiled_path) {
	String source_path = normalize_project_path(p_source_path);
	String exported_path = exported_path_for_source_internal(source_path);
	Engine *engine = Engine::get_singleton();
	if (engine && !engine->is_editor_hint() && FileAccess::file_exists(exported_path)) {
		if (r_compiled_path) {
			*r_compiled_path = exported_path;
		}
		return true;
	}

	Dictionary result = compile_project_internal(false);
	if (!bool(result.get("ok", false))) {
		Array diagnostics = result.has("diagnostics") ? Array(result["diagnostics"]) : Array();
		print_diagnostics(diagnostics);
		return false;
	}

	String compiled_path = compiled_path_for_source_internal(source_path);
	if (!FileAccess::file_exists(compiled_path)) {
		if (FileAccess::file_exists(exported_path)) {
			if (r_compiled_path) {
				*r_compiled_path = exported_path;
			}
			return true;
		}
		UtilityFunctions::printerr("[Gode TypeScript] Compiled output was not generated: ", compiled_path);
		return false;
	}

	if (r_compiled_path) {
		*r_compiled_path = compiled_path;
	}
	return true;
}

} // namespace gode
