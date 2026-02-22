#ifndef GODE_UTILS_JAVASCRIPT_VM_H
#define GODE_UTILS_JAVASCRIPT_VM_H

#include "godot_cpp/variant/typed_array.hpp"
#include <godot_cpp/variant/array.hpp>
#include <godot_cpp/variant/dictionary.hpp>
#include <godot_cpp/variant/string.hpp>
#include <napi.h>

namespace gode {

godot::TypedArray<godot::Dictionary> extract_js_definitions(Napi::Env env, const godot::String &source);

Napi::Object create_js_instance(Napi::Env env, const godot::String &source, const godot::String &class_name = "");

} // namespace gode

#endif // GODE_UTILS_JAVASCRIPT_VM_H

