//
// Created by 84473 on 2026/2/18.
//
#ifndef GODOT_GODE_JAVASCRIPT_H
#define GODOT_GODE_JAVASCRIPT_H

#include <godot_cpp/classes/script_extension.hpp>

using namespace godot;

namespace gode {

class Javascript : public ScriptExtension {
	GDCLASS(Javascript, ScriptExtension)

	bool is_dirty = false;
	String source_code;

private:
	bool compile();

protected:
	static void _bind_methods();

public:
	bool _editor_can_reload_from_file() override;
	void _placeholder_erased(void *p_placeholder) override;
	bool _can_instantiate() const override;
	Ref<Script> _get_base_script() const override;
	StringName _get_global_name() const override;
	bool _inherits_script(const Ref<Script> &p_script) const override;
	StringName _get_instance_base_type() const override;
	void *_instance_create(Object *p_for_object) const override;
	void *_placeholder_instance_create(Object *p_for_object) const override;
	bool _instance_has(Object *p_object) const override;
	bool _has_source_code() const override;
	String _get_source_code() const override;
	void _set_source_code(const String &p_code) override;
	Error _reload(bool p_keep_state) override;
	StringName _get_doc_class_name() const override;
	TypedArray<Dictionary> _get_documentation() const override;
	String _get_class_icon_path() const override;
	bool _has_method(const StringName &p_method) const override;
	bool _has_static_method(const StringName &p_method) const override;
	Variant _get_script_method_argument_count(const StringName &p_method) const override;
	Dictionary _get_method_info(const StringName &p_method) const override;
	bool _is_tool() const override;
	bool _is_valid() const override;
	bool _is_abstract() const override;
	bool _has_script_signal(const StringName &p_signal) const override;
	TypedArray<Dictionary> _get_script_signal_list() const override;
	bool _has_property_default_value(const StringName &p_property) const override;
	Variant _get_property_default_value(const StringName &p_property) const override;
	void _update_exports() override;
	TypedArray<Dictionary> _get_script_method_list() const override;
	TypedArray<Dictionary> _get_script_property_list() const override;
	int32_t _get_member_line(const StringName &p_member) const override;
	Dictionary _get_constants() const override;
	TypedArray<StringName> _get_members() const override;
	bool _is_placeholder_fallback_enabled() const override;
	Variant _get_rpc_config() const override;
};
} //namespace gode

#endif // GODE_JAVASCRIPT_H
