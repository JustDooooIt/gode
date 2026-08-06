#ifndef GODE_TYPESCRIPT_COMPILE_SERVICE_H
#define GODE_TYPESCRIPT_COMPILE_SERVICE_H

#include <godot_cpp/variant/string.hpp>

namespace gode {

bool ensure_typescript_script_compiled(const godot::String &p_source_path, godot::String *r_compiled_path = nullptr, bool *r_retryable_failure = nullptr);

} // namespace gode

#endif // GODE_TYPESCRIPT_COMPILE_SERVICE_H
