#include "support/javascript/javascript_language.h"
#include "godot_cpp/core/memory.hpp"
#include "support/javascript/javascript.h"

using namespace godot;
using namespace gode;

JavascriptLanguage *JavascriptLanguage::singleton = nullptr;

JavascriptLanguage::~JavascriptLanguage() {
	if (singleton == this) {
		ClassDB::_unregister_engine_singleton(JavascriptLanguage::get_class_static());
		memdelete(singleton);
		singleton = nullptr;
	}
}

JavascriptLanguage *JavascriptLanguage::get_singleton() {
	if (singleton) {
		return singleton;
	}
	singleton = memnew(JavascriptLanguage);
	if (likely(singleton)) {
		ClassDB::_register_engine_singleton(JavascriptLanguage::get_class_static(), singleton);
	}
	return singleton;
}

void JavascriptLanguage::_bind_methods() {
}

String JavascriptLanguage::_get_name() const {
	return String("Javascript");
}

void JavascriptLanguage::_init() {
}

String JavascriptLanguage::_get_type() const {
	return String("Javascript");
}

String JavascriptLanguage::_get_extension() const {
	return String("js");
}

void JavascriptLanguage::_finish() {
}

PackedStringArray JavascriptLanguage::_get_reserved_words() const {
	PackedStringArray arr;
	return arr;
}

bool JavascriptLanguage::_is_control_flow_keyword(const String &p_keyword) const {
	return false;
}

PackedStringArray JavascriptLanguage::_get_comment_delimiters() const {
	PackedStringArray arr;
	return arr;
}

PackedStringArray JavascriptLanguage::_get_doc_comment_delimiters() const {
	PackedStringArray arr;
	return arr;
}

PackedStringArray JavascriptLanguage::_get_string_delimiters() const {
	PackedStringArray arr;
	return arr;
}

Ref<Script> JavascriptLanguage::_make_template(const String &p_template, const String &p_class_name, const String &p_base_class_name) const {
	return Ref<Javascript>();
}

TypedArray<Dictionary> JavascriptLanguage::_get_built_in_templates(const StringName &p_object) const {
	TypedArray<Dictionary> arr;
	return arr;
}

bool JavascriptLanguage::_is_using_templates() {
	return false;
}

Dictionary JavascriptLanguage::_validate(const String &p_script, const String &p_path, bool p_validate_functions, bool p_validate_errors, bool p_validate_warnings, bool p_validate_safe_lines) const {
	Dictionary d;
	return d;
}

String JavascriptLanguage::_validate_path(const String &p_path) const {
	return String();
}

Object *JavascriptLanguage::_create_script() const {
	return nullptr;
}

bool JavascriptLanguage::_has_named_classes() const {
	return false;
}

bool JavascriptLanguage::_supports_builtin_mode() const {
	return false;
}

bool JavascriptLanguage::_supports_documentation() const {
	return false;
}

bool JavascriptLanguage::_can_inherit_from_file() const {
	return false;
}

int32_t JavascriptLanguage::_find_function(const String &p_function, const String &p_code) const {
	return -1;
}

String JavascriptLanguage::_make_function(const String &p_class_name, const String &p_function_name, const PackedStringArray &p_function_args) const {
	return String();
}

bool JavascriptLanguage::_can_make_function() const {
	return false;
}

Error JavascriptLanguage::_open_in_external_editor(const Ref<Script> &p_script, int32_t p_line, int32_t p_column) {
	return Error::ERR_UNAVAILABLE;
}

bool JavascriptLanguage::_overrides_external_editor() {
	return false;
}

ScriptLanguage::ScriptNameCasing JavascriptLanguage::_preferred_file_name_casing() const {
	return ScriptLanguage::ScriptNameCasing::SCRIPT_NAME_CASING_PASCAL_CASE;
}

Dictionary JavascriptLanguage::_complete_code(const String &p_code, const String &p_path, Object *p_owner) const {
	Dictionary d;
	return d;
}

Dictionary JavascriptLanguage::_lookup_code(const String &p_code, const String &p_symbol, const String &p_path, Object *p_owner) const {
	Dictionary d;
	return d;
}

String JavascriptLanguage::_auto_indent_code(const String &p_code, int32_t p_from_line, int32_t p_to_line) const {
	return p_code;
}

void JavascriptLanguage::_add_global_constant(const StringName &p_name, const Variant &p_value) {
}

void JavascriptLanguage::_add_named_global_constant(const StringName &p_name, const Variant &p_value) {
}

void JavascriptLanguage::_remove_named_global_constant(const StringName &p_name) {
}

void JavascriptLanguage::_thread_enter() {
}

void JavascriptLanguage::_thread_exit() {
}

String JavascriptLanguage::_debug_get_error() const {
	return String();
}

int32_t JavascriptLanguage::_debug_get_stack_level_count() const {
	return 0;
}

int32_t JavascriptLanguage::_debug_get_stack_level_line(int32_t p_level) const {
	return -1;
}

String JavascriptLanguage::_debug_get_stack_level_function(int32_t p_level) const {
	return String();
}

String JavascriptLanguage::_debug_get_stack_level_source(int32_t p_level) const {
	return String();
}

Dictionary JavascriptLanguage::_debug_get_stack_level_locals(int32_t p_level, int32_t p_max_subitems, int32_t p_max_depth) {
	Dictionary d;
	return d;
}

Dictionary JavascriptLanguage::_debug_get_stack_level_members(int32_t p_level, int32_t p_max_subitems, int32_t p_max_depth) {
	Dictionary d;
	return d;
}

void *JavascriptLanguage::_debug_get_stack_level_instance(int32_t p_level) {
	return nullptr;
}

Dictionary JavascriptLanguage::_debug_get_globals(int32_t p_max_subitems, int32_t p_max_depth) {
	Dictionary d;
	return d;
}

String JavascriptLanguage::_debug_parse_stack_level_expression(int32_t p_level, const String &p_expression, int32_t p_max_subitems, int32_t p_max_depth) {
	return String();
}

TypedArray<Dictionary> JavascriptLanguage::_debug_get_current_stack_info() {
	TypedArray<Dictionary> arr;
	return arr;
}

void JavascriptLanguage::_reload_all_scripts() {
}

void JavascriptLanguage::_reload_scripts(const Array &p_scripts, bool p_soft_reload) {
}

void JavascriptLanguage::_reload_tool_script(const Ref<Script> &p_script, bool p_soft_reload) {
}

PackedStringArray JavascriptLanguage::_get_recognized_extensions() const {
	PackedStringArray arr;
	arr.push_back(String("js"));
	return arr;
}

TypedArray<Dictionary> JavascriptLanguage::_get_public_functions() const {
	TypedArray<Dictionary> arr;
	return arr;
}

Dictionary JavascriptLanguage::_get_public_constants() const {
	Dictionary d;
	return d;
}

TypedArray<Dictionary> JavascriptLanguage::_get_public_annotations() const {
	TypedArray<Dictionary> arr;
	return arr;
}

void JavascriptLanguage::_profiling_start() {
}

void JavascriptLanguage::_profiling_stop() {
}

void JavascriptLanguage::_profiling_set_save_native_calls(bool p_enable) {
}

int32_t JavascriptLanguage::_profiling_get_accumulated_data(ScriptLanguageExtensionProfilingInfo *p_info_array, int32_t p_info_max) {
	return 0;
}

int32_t JavascriptLanguage::_profiling_get_frame_data(ScriptLanguageExtensionProfilingInfo *p_info_array, int32_t p_info_max) {
	return 0;
}

void JavascriptLanguage::_frame() {
}

bool JavascriptLanguage::_handles_global_class_type(const String &p_type) const {
	return false;
}

Dictionary JavascriptLanguage::_get_global_class_name(const String &p_path) const {
	Dictionary d;
	return d;
}
