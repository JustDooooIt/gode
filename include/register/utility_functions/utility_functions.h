#ifndef GODE_UTILITY_FUNCTIONS_H
#define GODE_UTILITY_FUNCTIONS_H

#include <napi.h>
#include <godot_cpp/variant/utility_functions.hpp>

using namespace godot;

namespace gode {
class GD : public Napi::ObjectWrap<GD> {
public:
	static Napi::Object Init(Napi::Env env, Napi::Object exports);
	GD(const Napi::CallbackInfo &info);

private:
	Napi::Value print(const Napi::CallbackInfo &info);
};
} //namespace gode

#endif // GODE_UTILITY_FUNCTIONS_H
