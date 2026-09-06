#include "script/typescript_interface_resource.h"

#include <godot_cpp/core/class_db.hpp>
#include <godot_cpp/variant/array.hpp>

#include <cctype>

using namespace godot;

namespace gode {

namespace {

constexpr const char *SCHEMA_PROPERTY = "_gode_interface_schema";

static std::string trim_type_text(const std::string &value) {
	size_t start = 0;
	while (start < value.size() && std::isspace(static_cast<unsigned char>(value[start]))) {
		start++;
	}
	size_t end = value.size();
	while (end > start && std::isspace(static_cast<unsigned char>(value[end - 1]))) {
		end--;
	}
	return value.substr(start, end - start);
}

static std::string interface_array_element(const StringName &class_name) {
	std::string type = trim_type_text(String(class_name).utf8().get_data());
	if (type.size() > 2 && type.substr(type.size() - 2) == "[]") {
		return trim_type_text(type.substr(0, type.size() - 2));
	}
	if (type.rfind("Array<", 0) == 0 && type.back() == '>') {
		return trim_type_text(type.substr(6, type.size() - 7));
	}
	if (type.rfind("ReadonlyArray<", 0) == 0 && type.back() == '>') {
		return trim_type_text(type.substr(14, type.size() - 15));
	}
	return {};
}

} // namespace

HashMap<StringName, TypeScriptInterfaceResource::Schema> TypeScriptInterfaceResource::schemas;

void TypeScriptInterfaceResource::_bind_methods() {
}

void TypeScriptInterfaceResource::register_schema(
		const StringName &p_schema_id,
		const StringName &p_interface_name,
		const HashMap<StringName, Vector<PropertyInfo>> &p_interfaces) {
	Schema schema;
	schema.interface_name = p_interface_name;
	schema.interfaces = p_interfaces;
	schemas[p_schema_id] = schema;
}

void TypeScriptInterfaceResource::configure(const StringName &p_schema_id) {
	if (schema_id == p_schema_id && !fields.is_empty()) {
		return;
	}
	schema_id = p_schema_id;
	apply_schema();
	notify_property_list_changed();
}

void TypeScriptInterfaceResource::apply_schema() {
	fields.clear();
	nested_interfaces.clear();
	nested_interface_arrays.clear();

	const Schema *schema = schemas.getptr(schema_id);
	if (!schema || !schema->interfaces.has(schema->interface_name)) {
		return;
	}
	set_name(String(schema->interface_name));

	for (const PropertyInfo &source_field : schema->interfaces[schema->interface_name]) {
		PropertyInfo field = source_field;
		const StringName structural_type = source_field.class_name;
		if (!structural_type.is_empty() && schema->interfaces.has(structural_type)) {
			nested_interfaces[field.name] = structural_type;
			field.type = Variant::OBJECT;
			field.hint = PROPERTY_HINT_RESOURCE_TYPE;
			field.hint_string = get_class_static();
			field.class_name = get_class_static();
		} else if (field.type == Variant::ARRAY && !structural_type.is_empty()) {
			const StringName element_type(interface_array_element(structural_type).c_str());
			if (!element_type.is_empty() && schema->interfaces.has(element_type)) {
				nested_interface_arrays[field.name] = element_type;
				field.hint = PROPERTY_HINT_ARRAY_TYPE;
				field.hint_string = String::num_int64(Variant::OBJECT) + "/" + String::num_int64(PROPERTY_HINT_RESOURCE_TYPE) + ":" + String(get_class_static());
				field.class_name = StringName();
			} else {
				field.class_name = StringName();
			}
		} else if (field.type != Variant::OBJECT) {
			field.class_name = StringName();
		}
		fields.push_back(field);
	}
}

void TypeScriptInterfaceResource::configure_nested_value(const StringName &p_name, const Variant &p_value) {
	const Schema *schema = schemas.getptr(schema_id);
	if (!schema) {
		return;
	}
	if (nested_interfaces.has(p_name)) {
		TypeScriptInterfaceResource *resource = Object::cast_to<TypeScriptInterfaceResource>(p_value);
		if (resource) {
			const StringName nested_schema_id(String(schema_id) + "::" + String(nested_interfaces[p_name]));
			register_schema(nested_schema_id, nested_interfaces[p_name], schema->interfaces);
			resource->configure(nested_schema_id);
		}
		return;
	}
	if (nested_interface_arrays.has(p_name) && p_value.get_type() == Variant::ARRAY) {
		const StringName nested_name = nested_interface_arrays[p_name];
		const StringName nested_schema_id(String(schema_id) + "::" + String(nested_name));
		register_schema(nested_schema_id, nested_name, schema->interfaces);
		Array array = p_value;
		for (int64_t i = 0; i < array.size(); i++) {
			TypeScriptInterfaceResource *resource = Object::cast_to<TypeScriptInterfaceResource>(array[i]);
			if (resource) {
				resource->configure(nested_schema_id);
			}
		}
	}
}

bool TypeScriptInterfaceResource::_set(const StringName &p_name, const Variant &p_value) {
	if (p_name == StringName(SCHEMA_PROPERTY)) {
		configure(StringName(String(p_value)));
		return true;
	}
	for (const PropertyInfo &field : fields) {
		if (field.name == p_name) {
			configure_nested_value(p_name, p_value);
			values[p_name] = p_value;
			emit_changed();
			return true;
		}
	}
	return false;
}

bool TypeScriptInterfaceResource::_get(const StringName &p_name, Variant &r_value) const {
	if (p_name == StringName(SCHEMA_PROPERTY)) {
		r_value = String(schema_id);
		return true;
	}
	if (values.has(p_name)) {
		r_value = values[p_name];
		return true;
	}
	for (const PropertyInfo &field : fields) {
		if (field.name == p_name) {
			r_value = Variant();
			return true;
		}
	}
	return false;
}

void TypeScriptInterfaceResource::_get_property_list(List<PropertyInfo> *p_list) const {
	PropertyInfo schema_property(Variant::STRING, SCHEMA_PROPERTY, PROPERTY_HINT_NONE, "", PROPERTY_USAGE_STORAGE | PROPERTY_USAGE_INTERNAL);
	p_list->push_back(schema_property);
	for (const PropertyInfo &field : fields) {
		p_list->push_back(field);
	}
}

StringName TypeScriptInterfaceResource::get_interface_field_name(int64_t p_index) const {
	if (p_index < 0 || p_index >= fields.size()) {
		return StringName();
	}
	return fields[p_index].name;
}

} // namespace gode
