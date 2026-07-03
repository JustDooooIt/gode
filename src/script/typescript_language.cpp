#include "script/typescript_language.h"
#include "script/typescript_script.h"
#include <godot_cpp/classes/resource_loader.hpp>
#include <godot_cpp/core/memory.hpp>

using namespace godot;
using namespace gode;

TypeScriptLanguage *TypeScriptLanguage::singleton = nullptr;

TypeScriptLanguage::~TypeScriptLanguage() {
	if (singleton == this) {
		singleton = nullptr;
	}
}

TypeScriptLanguage *TypeScriptLanguage::get_singleton() {
	if (singleton) {
		return singleton;
	}
	singleton = memnew(TypeScriptLanguage);
	return singleton;
}

String TypeScriptLanguage::_get_name() const {
	return String("TypeScript");
}

void TypeScriptLanguage::_init() {
}

String TypeScriptLanguage::_get_type() const {
	return String("TypeScript");
}

String TypeScriptLanguage::_get_extension() const {
	return String("ts");
}

void TypeScriptLanguage::_finish() {
}

PackedStringArray TypeScriptLanguage::_get_reserved_words() const {
	PackedStringArray arr;
	return arr;
}

bool TypeScriptLanguage::_is_control_flow_keyword(const String &p_keyword) const {
	return false;
}

PackedStringArray TypeScriptLanguage::_get_comment_delimiters() const {
	PackedStringArray delimiters;
	delimiters.push_back("//");
	return delimiters;
}

PackedStringArray TypeScriptLanguage::_get_doc_comment_delimiters() const {
	PackedStringArray delimiters;
	return delimiters;
}

PackedStringArray TypeScriptLanguage::_get_string_delimiters() const {
	PackedStringArray delimiters;
	delimiters.push_back("\"\"");
	delimiters.push_back("''");
	return delimiters;
}

PackedStringArray TypeScriptLanguage::_get_recognized_extensions() const {
	PackedStringArray arr;
	arr.push_back(String("ts"));
	arr.push_back(String("tsx"));
	return arr;
}

Ref<Script> TypeScriptLanguage::_make_template(const String &p_template, const String &p_class_name, const String &p_base_class_name) const {
	Ref<TypeScriptScript> script;
	script.instantiate();

	String class_name = p_class_name;
	if (class_name.is_empty()) {
		class_name = String("NewScript");
	}

	String base_name = p_base_class_name;
	if (base_name.is_empty()) {
		base_name = String("Node");
	}

	String code;
	code += String("import { ") + base_name + String(" } from \"godot\";\n\n");
	code += String("export default class ") + class_name + String(" extends ") + base_name + String(" {\n");
	code += String("\t_ready(): void {\n");
	code += String("\t}\n");
	code += String("}\n");

	script->_set_source_code(code);
	return script;
}

TypedArray<Dictionary> TypeScriptLanguage::_get_built_in_templates(const StringName &p_object) const {
	TypedArray<Dictionary> arr;
	return arr;
}

bool TypeScriptLanguage::_is_using_templates() {
	return false;
}

Dictionary TypeScriptLanguage::_validate(const String &p_script, const String &p_path, bool p_validate_functions, bool p_validate_errors, bool p_validate_warnings, bool p_validate_safe_lines) const {
	Dictionary d;
	return d;
}

String TypeScriptLanguage::_validate_path(const String &p_path) const {
	return String();
}

Object *TypeScriptLanguage::_create_script() const {
	return memnew(TypeScriptScript);
}

bool TypeScriptLanguage::_has_named_classes() const {
	return false;
}

bool TypeScriptLanguage::_supports_builtin_mode() const {
	return false;
}

bool TypeScriptLanguage::_supports_documentation() const {
	return false;
}

bool TypeScriptLanguage::_can_inherit_from_file() const {
	return false;
}

int32_t TypeScriptLanguage::_find_function(const String &p_function, const String &p_code) const {
	return -1;
}

String TypeScriptLanguage::_make_function(const String &p_class_name, const String &p_function_name, const PackedStringArray &p_function_args) const {
	return String();
}

bool TypeScriptLanguage::_can_make_function() const {
	return false;
}

Error TypeScriptLanguage::_open_in_external_editor(const Ref<Script> &p_script, int32_t p_line, int32_t p_column) {
	return Error::ERR_UNAVAILABLE;
}

bool TypeScriptLanguage::_overrides_external_editor() {
	return false;
}

ScriptLanguage::ScriptNameCasing TypeScriptLanguage::_preferred_file_name_casing() const {
	return ScriptLanguage::ScriptNameCasing::SCRIPT_NAME_CASING_PASCAL_CASE;
}

Dictionary TypeScriptLanguage::_complete_code(const String &p_code, const String &p_path, Object *p_owner) const {
	Dictionary d;
	d["result"] = Error::ERR_UNAVAILABLE;
	d["options"] = Array();
	d["force"] = false;
	d["call_hint"] = String();
	return d;
}

Dictionary TypeScriptLanguage::_lookup_code(const String &p_code, const String &p_symbol, const String &p_path, Object *p_owner) const {
	Dictionary d;
	d["result"] = Error::ERR_UNAVAILABLE;
	d["type"] = ScriptLanguageExtension::LOOKUP_RESULT_SCRIPT_LOCATION;
	return d;
}

String TypeScriptLanguage::_auto_indent_code(const String &p_code, int32_t p_from_line, int32_t p_to_line) const {
	return p_code;
}

void TypeScriptLanguage::_add_global_constant(const StringName &p_name, const Variant &p_value) {
}

void TypeScriptLanguage::_add_named_global_constant(const StringName &p_name, const Variant &p_value) {
}

void TypeScriptLanguage::_remove_named_global_constant(const StringName &p_name) {
}

void TypeScriptLanguage::_thread_enter() {
}

void TypeScriptLanguage::_thread_exit() {
}

String TypeScriptLanguage::_debug_get_error() const {
	return String();
}

int32_t TypeScriptLanguage::_debug_get_stack_level_count() const {
	return 0;
}

int32_t TypeScriptLanguage::_debug_get_stack_level_line(int32_t p_level) const {
	return -1;
}

String TypeScriptLanguage::_debug_get_stack_level_function(int32_t p_level) const {
	return String();
}

String TypeScriptLanguage::_debug_get_stack_level_source(int32_t p_level) const {
	return String();
}

Dictionary TypeScriptLanguage::_debug_get_stack_level_locals(int32_t p_level, int32_t p_max_subitems, int32_t p_max_depth) {
	Dictionary d;
	return d;
}

Dictionary TypeScriptLanguage::_debug_get_stack_level_members(int32_t p_level, int32_t p_max_subitems, int32_t p_max_depth) {
	Dictionary d;
	return d;
}

void *TypeScriptLanguage::_debug_get_stack_level_instance(int32_t p_level) {
	return nullptr;
}

Dictionary TypeScriptLanguage::_debug_get_globals(int32_t p_max_subitems, int32_t p_max_depth) {
	Dictionary d;
	return d;
}

String TypeScriptLanguage::_debug_parse_stack_level_expression(int32_t p_level, const String &p_expression, int32_t p_max_subitems, int32_t p_max_depth) {
	return String();
}

TypedArray<Dictionary> TypeScriptLanguage::_debug_get_current_stack_info() {
	TypedArray<Dictionary> arr;
	return arr;
}

void TypeScriptLanguage::_reload_all_scripts() {
}

void TypeScriptLanguage::_reload_scripts(const Array &p_scripts, bool p_soft_reload) {
}

void TypeScriptLanguage::_reload_tool_script(const Ref<Script> &p_script, bool p_soft_reload) {
}

TypedArray<Dictionary> TypeScriptLanguage::_get_public_functions() const {
	TypedArray<Dictionary> arr;
	return arr;
}

Dictionary TypeScriptLanguage::_get_public_constants() const {
	Dictionary d;
	return d;
}

TypedArray<Dictionary> TypeScriptLanguage::_get_public_annotations() const {
	TypedArray<Dictionary> arr;
	return arr;
}

void TypeScriptLanguage::_profiling_start() {
}

void TypeScriptLanguage::_profiling_stop() {
}

void TypeScriptLanguage::_profiling_set_save_native_calls(bool p_enable) {
}

int32_t TypeScriptLanguage::_profiling_get_accumulated_data(ScriptLanguageExtensionProfilingInfo *p_info_array, int32_t p_info_max) {
	return 0;
}

int32_t TypeScriptLanguage::_profiling_get_frame_data(ScriptLanguageExtensionProfilingInfo *p_info_array, int32_t p_info_max) {
	return 0;
}

void TypeScriptLanguage::_frame() {
}

bool TypeScriptLanguage::_handles_global_class_type(const String &p_type) const {
	return false;
}

Dictionary TypeScriptLanguage::_get_global_class_name(const String &p_path) const {
	Dictionary d;
	Ref<TypeScriptScript> script = ResourceLoader::get_singleton()->load(p_path, "", ResourceLoader::CACHE_MODE_REUSE);
	if (script.is_null()) {
		return d;
	}
	StringName name = script->_get_global_name();
	if (name == StringName()) {
		return d;
	}
	d["name"] = name;
	d["base_type"] = script->get_base_class_name();
	return d;
}
