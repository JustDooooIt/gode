#ifndef GODE_UTILS_VALUE_CONVER_H
#define GODE_UTILS_VALUE_CONVER_H

#include <napi.h>
#include <godot_cpp/variant/variant.hpp>

namespace gode {
extern Napi::Value godot_to_napi(Napi::Env env, const godot::Variant &variant);
extern godot::Variant napi_to_godot(const Napi::Value &value);
} //namespace gode

#endif // GODE_UTILS_VALUE_CONVER_H
