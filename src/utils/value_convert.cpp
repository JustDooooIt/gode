#include "utils/value_convert.h"

#include "godot_cpp/variant/utility_functions.hpp"
#include <godot_cpp/classes/object.hpp>
#include <godot_cpp/variant/builtin_types.hpp>

#include "builtin/aabb_binding.gen.h"
#include "builtin/array_binding.gen.h"
#include "builtin/basis_binding.gen.h"
#include "builtin/callable_binding.gen.h"
#include "builtin/color_binding.gen.h"
#include "builtin/dictionary_binding.gen.h"
#include "builtin/node_path_binding.gen.h"
#include "builtin/packed_byte_array_binding.gen.h"
#include "builtin/packed_color_array_binding.gen.h"
#include "builtin/packed_float32_array_binding.gen.h"
#include "builtin/packed_float64_array_binding.gen.h"
#include "builtin/packed_int32_array_binding.gen.h"
#include "builtin/packed_int64_array_binding.gen.h"
#include "builtin/packed_string_array_binding.gen.h"
#include "builtin/packed_vector2_array_binding.gen.h"
#include "builtin/packed_vector3_array_binding.gen.h"
#include "builtin/packed_vector4_array_binding.gen.h"
#include "builtin/plane_binding.gen.h"
#include "builtin/projection_binding.gen.h"
#include "builtin/quaternion_binding.gen.h"
#include "builtin/rect2_binding.gen.h"
#include "builtin/rect2i_binding.gen.h"
#include "builtin/rid_binding.gen.h"
#include "builtin/signal_binding.gen.h"
#include "builtin/string_binding.gen.h"
#include "builtin/string_name_binding.gen.h"
#include "builtin/transform2d_binding.gen.h"
#include "builtin/transform3d_binding.gen.h"
#include "builtin/vector2_binding.gen.h"
#include "builtin/vector2i_binding.gen.h"
#include "builtin/vector3_binding.gen.h"
#include "builtin/vector3i_binding.gen.h"
#include "builtin/vector4_binding.gen.h"
#include "builtin/vector4i_binding.gen.h"

// Helper macros for creating N-API objects from Godot variants
#define BIND_BUILTIN_TO_NAPI(VariantType, BindingClass)               \
	case godot::Variant::Type::VariantType: {                         \
		Napi::Object obj = BindingClass::constructor.Value().New({}); \
		BindingClass *binding = BindingClass::Unwrap(obj);            \
		binding->instance = variant;                                  \
		return obj;                                                   \
	}

using namespace godot;

namespace gode {

Napi::Value godot_to_napi(Napi::Env env, const godot::Variant &variant) {
	switch (variant.get_type()) {
		case godot::Variant::Type::NIL:
			return env.Null();
		case godot::Variant::Type::INT:
			return Napi::Number::New(env, variant.operator int64_t());
		case godot::Variant::Type::FLOAT:
			return Napi::Number::New(env, variant.operator double());
		case godot::Variant::Type::BOOL:
			return Napi::Boolean::New(env, variant.operator bool());
		case godot::Variant::Type::STRING:
			return Napi::String::New(env, variant.operator String().utf8().get_data());
		case godot::Variant::Type::STRING_NAME:
			return Napi::String::New(env, variant.operator String().utf8().get_data());

			BIND_BUILTIN_TO_NAPI(VECTOR2, Vector2Binding)
			BIND_BUILTIN_TO_NAPI(VECTOR2I, Vector2iBinding)
			BIND_BUILTIN_TO_NAPI(RECT2, Rect2Binding)
			BIND_BUILTIN_TO_NAPI(RECT2I, Rect2iBinding)
			BIND_BUILTIN_TO_NAPI(VECTOR3, Vector3Binding)
			BIND_BUILTIN_TO_NAPI(VECTOR3I, Vector3iBinding)
			BIND_BUILTIN_TO_NAPI(TRANSFORM2D, Transform2DBinding)
			BIND_BUILTIN_TO_NAPI(VECTOR4, Vector4Binding)
			BIND_BUILTIN_TO_NAPI(VECTOR4I, Vector4iBinding)
			BIND_BUILTIN_TO_NAPI(PLANE, PlaneBinding)
			BIND_BUILTIN_TO_NAPI(QUATERNION, QuaternionBinding)
			BIND_BUILTIN_TO_NAPI(AABB, AABBBinding)
			BIND_BUILTIN_TO_NAPI(BASIS, BasisBinding)
			BIND_BUILTIN_TO_NAPI(TRANSFORM3D, Transform3DBinding)
			BIND_BUILTIN_TO_NAPI(PROJECTION, ProjectionBinding)
			BIND_BUILTIN_TO_NAPI(COLOR, ColorBinding)
			BIND_BUILTIN_TO_NAPI(NODE_PATH, NodePathBinding)
			BIND_BUILTIN_TO_NAPI(RID, RIDBinding)
			BIND_BUILTIN_TO_NAPI(CALLABLE, CallableBinding)
			BIND_BUILTIN_TO_NAPI(SIGNAL, SignalBinding)
			BIND_BUILTIN_TO_NAPI(DICTIONARY, DictionaryBinding)
			BIND_BUILTIN_TO_NAPI(ARRAY, ArrayBinding)
			BIND_BUILTIN_TO_NAPI(PACKED_BYTE_ARRAY, PackedByteArrayBinding)
			BIND_BUILTIN_TO_NAPI(PACKED_INT32_ARRAY, PackedInt32ArrayBinding)
			BIND_BUILTIN_TO_NAPI(PACKED_INT64_ARRAY, PackedInt64ArrayBinding)
			BIND_BUILTIN_TO_NAPI(PACKED_FLOAT32_ARRAY, PackedFloat32ArrayBinding)
			BIND_BUILTIN_TO_NAPI(PACKED_FLOAT64_ARRAY, PackedFloat64ArrayBinding)
			BIND_BUILTIN_TO_NAPI(PACKED_STRING_ARRAY, PackedStringArrayBinding)
			BIND_BUILTIN_TO_NAPI(PACKED_VECTOR2_ARRAY, PackedVector2ArrayBinding)
			BIND_BUILTIN_TO_NAPI(PACKED_VECTOR3_ARRAY, PackedVector3ArrayBinding)
			BIND_BUILTIN_TO_NAPI(PACKED_VECTOR4_ARRAY, PackedVector4ArrayBinding)
			BIND_BUILTIN_TO_NAPI(PACKED_COLOR_ARRAY, PackedColorArrayBinding)

		case godot::Variant::Type::OBJECT: {
			godot::Object *obj = variant.operator godot::Object *();
			if (!obj) {
				return env.Null();
			}
			// TODO: Find correct binding class for object instance and wrap it
			// For now return null or generic wrapper if available
			return env.Null();
		}

		default:
			return env.Undefined();
	}
}

godot::Variant napi_to_godot(const Napi::Value &value) {
	if (value.IsNumber()) {
		return value.ToNumber().DoubleValue();
	} else if (value.IsBoolean()) {
		return value.ToBoolean().Value();
	} else if (value.IsString()) {
		return String::utf8(value.ToString().Utf8Value().c_str());
	} else if (value.IsObject()) {
		Napi::Object obj = value.As<Napi::Object>();
		// Detect specific types or return Dictionary
		// TODO: Check if it's a wrapped Godot object
		return godot::Variant();
	} else {
		return godot::Variant();
	}
}

} //namespace gode
