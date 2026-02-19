#include "register/utility_functions/utility_functions.h"
#include "napi.h"
#include "utils/func_utils.h"
#include <godot_cpp/variant/utility_functions.hpp>

using namespace godot;
Napi::Object gode::GD::Init(Napi::Env env, Napi::Object exports) {
	Napi::Function func = DefineClass(env, "GD", {
														 InstanceMethod("print", &GD::print),
												 });
	Napi::Object global = env.Global();
	Napi::Object gd_instance = func.New({});
	global.Set("GD", gd_instance);
	return exports;
}

gode::GD::GD(const Napi::CallbackInfo &info) :
		Napi::ObjectWrap<GD>(info) {}

Napi::Value gode::GD::print(const Napi::CallbackInfo &info) {
	return gode::call_builtin_static_vararg_method_no_ret(&godot::UtilityFunctions::print, info);
}
