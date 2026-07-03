#ifndef GODE_UTILS_NAPI_ERROR_UTILS_H
#define GODE_UTILS_NAPI_ERROR_UTILS_H

#include <napi.h>

#include <string>

namespace gode {

std::string js_error_to_string(Napi::Value value);
std::string js_error_to_string(const Napi::Error &error);
void log_js_error(const std::string &context, const std::string &message);
bool log_and_clear_pending_js_exception(Napi::Env env, const std::string &context);

} // namespace gode

#endif // GODE_UTILS_NAPI_ERROR_UTILS_H
