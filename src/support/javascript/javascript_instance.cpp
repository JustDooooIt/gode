#include "support/javascript/javascript_instance.h"

using namespace godot;

namespace gode {

JavascriptInstance::JavascriptInstance(const Ref<Javascript> &p_javascript, Object *p_owner, bool p_placeholder) {
	javascript = p_javascript;
	owner = p_owner;
	placeholder = p_placeholder;
}

Object *JavascriptInstance::get_owner() const {
	return owner;
}

bool JavascriptInstance::is_placeholder() const {
	return placeholder;
}

bool JavascriptInstance::set(const StringName &p_name, const Variant &p_value) {
	(void)p_name;
	(void)p_value;
	return false;
}

bool JavascriptInstance::get(const StringName &p_name, Variant &r_value) const {
	(void)p_name;
	(void)r_value;
	return false;
}

bool JavascriptInstance::has_method(const StringName &p_method) const {
	(void)p_method;
	return false;
}

int32_t JavascriptInstance::get_method_argument_count(const StringName &p_method, bool &r_is_valid) const {
	(void)p_method;
	r_is_valid = false;
	return 0;
}

Variant JavascriptInstance::call(const StringName &p_method, const Variant **p_args, int32_t p_argcount, GDExtensionCallError &r_error) {
	(void)p_method;
	(void)p_args;
	(void)p_argcount;
	r_error.error = GDEXTENSION_CALL_ERROR_INVALID_METHOD;
	r_error.argument = 0;
	r_error.expected = 0;
	return Variant();
}

String JavascriptInstance::to_string(bool &r_is_valid) const {
	r_is_valid = false;
	return String();
}

bool JavascriptInstance::property_can_revert(const StringName &p_name) const {
	(void)p_name;
	return false;
}

bool JavascriptInstance::property_get_revert(const StringName &p_name, Variant &r_ret) const {
	(void)p_name;
	(void)r_ret;
	return false;
}

void JavascriptInstance::get_property_list(const GDExtensionPropertyInfo *&r_list, uint32_t &r_count) const {
	(void)r_list;
	r_count = 0;
}

void JavascriptInstance::get_method_list(const GDExtensionMethodInfo *&r_list, uint32_t &r_count) const {
	(void)r_list;
	r_count = 0;
}

Ref<Javascript> JavascriptInstance::get_script() const {
	return javascript;
}

} // namespace gode

