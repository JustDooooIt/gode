#ifndef GODE_UTILITY_FUNCTIONS_VARARG_METHOD_H
#define GODE_UTILITY_FUNCTIONS_VARARG_METHOD_H

#include <godot_cpp/variant/variant.hpp>
#include <vector>

using namespace godot;

namespace gode {
namespace utility {

inline void print_internal(const Variant **p_args, GDExtensionInt p_arg_count) {
	static GDExtensionPtrUtilityFunction _gde_function = ::godot::gdextension_interface::variant_get_ptr_utility_function(StringName("print")._native_ptr(), 2648703342);
	CHECK_METHOD_BIND(_gde_function);
	Variant ret;
	_gde_function(&ret, reinterpret_cast<GDExtensionConstVariantPtr *>(p_args), p_arg_count);
}
inline void print(const Variant &arg, const std::vector<Variant> &args) {
	std::vector<Variant> variant_args;
	std::vector<Variant *> variant_args_ptr;
	variant_args.push_back(arg);
	for (int i = 0; i < args.size(); i++) {
		variant_args.push_back(args[i]);
	}
	for (int i = 0; i < variant_args.size(); i++) {
		variant_args_ptr.push_back(&variant_args[i]);
	}
	print_internal(const_cast<const Variant **>(variant_args_ptr.data()), variant_args_ptr.size());
}
} //namespace utility
} //namespace gode

#endif // GODE_UTILITY_FUNCTIONS_VARARG_METHOD_H