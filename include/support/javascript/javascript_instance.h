#ifndef GODOT_JAVASCRIPT_INSTANCE_H
#define GODOT_JAVASCRIPT_INSTANCE_H

#include "support/javascript/javascript.h"

using namespace godot;

namespace gode {

class JavascriptInstance {
	Ref<Javascript> javascript;
	Object *owner = nullptr;
	bool placeholder = false;

public:
	JavascriptInstance(const Ref<Javascript> &p_javascript, Object *p_owner, bool p_placeholder);

	Object *get_owner() const;
	bool is_placeholder() const;

	bool set(const StringName &p_name, const Variant &p_value);
	bool get(const StringName &p_name, Variant &r_value) const;

	bool has_method(const StringName &p_method) const;
	int32_t get_method_argument_count(const StringName &p_method, bool &r_is_valid) const;
	Variant call(const StringName &p_method, const Variant **p_args, int32_t p_argcount, GDExtensionCallError &r_error);

	String to_string(bool &r_is_valid) const;

	bool property_can_revert(const StringName &p_name) const;
	bool property_get_revert(const StringName &p_name, Variant &r_ret) const;

	void get_property_list(const GDExtensionPropertyInfo *&r_list, uint32_t &r_count) const;
	void get_method_list(const GDExtensionMethodInfo *&r_list, uint32_t &r_count) const;

	Ref<Javascript> get_script() const;

};
} // namespace gode


