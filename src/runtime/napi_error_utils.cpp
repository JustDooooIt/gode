#include "runtime/napi_error_utils.h"

#include <godot_cpp/variant/utility_functions.hpp>

namespace gode {

std::string js_error_to_string(Napi::Value value) {
	try {
		if (value.IsObject()) {
			Napi::Object obj = value.As<Napi::Object>();
			if (obj.Has("stack")) {
				Napi::Value stack = obj.Get("stack");
				if (!stack.IsNull() && !stack.IsUndefined()) {
					return stack.ToString().Utf8Value();
				}
			}
			if (obj.Has("message")) {
				Napi::Value message = obj.Get("message");
				if (!message.IsNull() && !message.IsUndefined()) {
					return message.ToString().Utf8Value();
				}
			}
		}
		if (!value.IsNull() && !value.IsUndefined()) {
			return value.ToString().Utf8Value();
		}
	} catch (...) {
		if (!value.IsEmpty() && value.Env().IsExceptionPending()) {
			value.Env().GetAndClearPendingException();
		}
	}
	return "Unknown JavaScript exception";
}

std::string js_error_to_string(const Napi::Error &error) {
	std::string message = js_error_to_string(error.Value());
	if (message == "Unknown JavaScript exception" && !error.Message().empty()) {
		return error.Message();
	}
	return message;
}

void log_js_error(const std::string &context, const std::string &message) {
	godot::UtilityFunctions::printerr(context.c_str(), ": ", message.c_str());
}

bool log_and_clear_pending_js_exception(Napi::Env env, const std::string &context) {
	if (!env.IsExceptionPending()) {
		return false;
	}
	Napi::Error error = env.GetAndClearPendingException();
	log_js_error(context, js_error_to_string(error));
	return true;
}

} // namespace gode
