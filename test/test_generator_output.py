import importlib.util
import pathlib
import tempfile
import time
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


@unittest.skipUnless(importlib.util.find_spec("jinja2"), "jinja2 is required for generator output tests")
class GeneratorOutputTests(unittest.TestCase):
	def test_render_does_not_touch_unchanged_files(self):
		from generator.base_generator import CodeGenerator

		with tempfile.TemporaryDirectory() as temp_dir:
			root = pathlib.Path(temp_dir)
			templates = root / "templates"
			output = root / "out"
			templates.mkdir()
			output.mkdir()
			(templates / "sample.jinja2").write_text("value={{ value }}\n", encoding="utf-8")

			generator = CodeGenerator(str(templates), {"default": str(output)})
			generator.render("sample.jinja2", {"value": 42}, "sample.txt")

			target = output / "sample.txt"
			first_mtime = target.stat().st_mtime_ns
			time.sleep(0.01)
			generator.render("sample.jinja2", {"value": 42}, "sample.txt")
			self.assertEqual(first_mtime, target.stat().st_mtime_ns)

			generator.render("sample.jinja2", {"value": 43}, "sample.txt")
			self.assertNotEqual(first_mtime, target.stat().st_mtime_ns)

	def test_cpp_type_mapping_is_shared_and_stable(self):
		from generator.utils.type_mappings import get_cpp_type

		refcounted = {"Resource", "Script"}
		self.assertEqual("int32_t", get_cpp_type("int", "int32", refcounted))
		self.assertEqual("uint64_t", get_cpp_type("int", "uint64", refcounted))
		self.assertEqual("char32_t", get_cpp_type("int", "char32", refcounted))
		self.assertEqual("godot::real_t", get_cpp_type("float", "", refcounted))
		self.assertEqual("const godot::String &", get_cpp_type("String", "", refcounted, is_arg=True))
		self.assertEqual("godot::Vector3", get_cpp_type("Vector3", "", refcounted))
		self.assertEqual("const godot::Ref<godot::Resource> &", get_cpp_type("Resource", "", refcounted, is_arg=True))
		self.assertEqual("godot::Node *", get_cpp_type("Node", "", refcounted))
		self.assertEqual("godot::BitField<godot::Window::Flags>", get_cpp_type("bitfield::Window.Flags", "", refcounted))
		self.assertEqual("const godot::TypedArray<godot::Node> &", get_cpp_type("typedarray::Node", "", refcounted, is_arg=True))
		self.assertEqual("godot::TypedArray<godot::Ref<godot::Resource>>", get_cpp_type("typedarray::Resource", "", refcounted))
		self.assertEqual("godot::TypedArray<int64_t>", get_cpp_type("typedarray::int", "", refcounted))
		self.assertEqual("const godot::TypedDictionary<int64_t, godot::String> &", get_cpp_type("typeddictionary::int;String", "", refcounted, is_arg=True))

	def test_typed_collection_parsing_is_shared_and_stable(self):
		from generator.dts_generator import godot_type_to_ts
		from generator.utils.type_mappings import parse_typedarray_element_type, parse_typeddictionary_types

		self.assertEqual("CompositorEffect", parse_typedarray_element_type("typedarray::24/17:CompositorEffect"))
		self.assertEqual("Dictionary", parse_typedarray_element_type("typedarray::27/0:"))
		self.assertEqual(("Color", "Color"), parse_typeddictionary_types("typeddictionary::Color;Color"))
		self.assertEqual("number | bigint", godot_type_to_ts("int", is_input=True))
		self.assertEqual("number", godot_type_to_ts("int", is_input=False))
		self.assertEqual("GDArray | Array<Node>", godot_type_to_ts("typedarray::Node", is_input=True))
		self.assertEqual(
			"Array<{ [key: string]: VariantArgument } | Map<VariantArgument, VariantArgument>>",
			godot_type_to_ts("typedarray::27/0:"),
		)
		self.assertEqual(
			"GDDictionary | Map<number | bigint, string>",
			godot_type_to_ts("typeddictionary::int;String", is_input=True),
		)
		self.assertEqual(
			"GDDictionary | Record<string, number> | Map<string, number>",
			godot_type_to_ts("typeddictionary::String;int", is_input=True),
		)
		self.assertEqual(
			"{ [key: string]: VariantArgument } | Map<VariantArgument, VariantArgument>",
			godot_type_to_ts("Dictionary"),
		)
		self.assertEqual(
			"PackedInt32Array | Array<number | bigint>",
			godot_type_to_ts("PackedInt32Array", is_input=True),
		)
		self.assertEqual(
			"PackedStringArray | Array<GDString | StringName | string>",
			godot_type_to_ts("PackedStringArray", is_input=True),
		)

	def test_builtin_argument_matching_accepts_js_arrays_for_array_types(self):
		from generator.builtin_classes_generator import napi_match_expr

		self.assertEqual("(info[0].IsNumber() || info[0].IsBigInt())", napi_match_expr("int", 0))
		self.assertEqual("info[0].IsNumber()", napi_match_expr("float", 0))
		self.assertEqual(
			"info[0].IsArray() || (info[0].IsObject() && info[0].As<Napi::Object>().InstanceOf(ArrayBinding::constructor.Value()))",
			napi_match_expr("Array", 0),
		)
		self.assertEqual(
			"info[0].IsArray() || (info[0].IsObject() && info[0].As<Napi::Object>().InstanceOf(PackedInt32ArrayBinding::constructor.Value()))",
			napi_match_expr("PackedInt32Array", 0),
		)
		self.assertEqual("info[1].IsArray() || info[1].IsObject()", napi_match_expr("typedarray::Node", 1))

	def test_default_arg_mapping_is_shared_and_stable(self):
		from generator.utils.type_mappings import default_arg_napi_expr

		self.assertEqual('info.Env().Null()', default_arg_napi_expr({"type": "Variant", "default_value": "null"}))
		self.assertEqual('Napi::Boolean::New(info.Env(), true)', default_arg_napi_expr({"type": "bool", "default_value": "true"}))
		self.assertEqual('Napi::Number::New(info.Env(), static_cast<double>(42))', default_arg_napi_expr({"type": "int", "default_value": 42}))
		self.assertEqual('gode::godot_to_napi(info.Env(), godot::Array())', default_arg_napi_expr({"type": "typedarray::Node", "default_value": "[]"}))
		self.assertEqual('gode::godot_to_napi(info.Env(), godot::Vector3(1, 2, 3))', default_arg_napi_expr({"type": "Vector3", "default_value": "Vector3(1, 2, 3)"}))
		self.assertEqual('gode::godot_to_napi(info.Env(), godot::String("ok"))', default_arg_napi_expr({"type": "String", "default_value": '"ok"'}))
		self.assertEqual('gode::godot_to_napi(info.Env(), godot::StringName(""))', default_arg_napi_expr({"type": "StringName", "default_value": '&""'}))
		self.assertEqual('gode::godot_to_napi(info.Env(), godot::StringName("Master"))', default_arg_napi_expr({"type": "StringName", "default_value": '&"Master"'}))
		self.assertEqual('gode::godot_to_napi(info.Env(), godot::NodePath("root"))', default_arg_napi_expr({"type": "NodePath", "default_value": '^"root"'}))

	def test_builtin_compatibility_table_covers_color_okhsl(self):
		from generator.utils.builtin_compat import builtin_member_compat, builtin_method_compat

		method = builtin_method_compat("Color", "from_ok_hsl")
		self.assertEqual("gode::color_okhsl_compat::from_ok_hsl", method["function"])

		for member in ("ok_hsl_h", "ok_hsl_s", "ok_hsl_l"):
			compat = builtin_member_compat("Color", member)
			self.assertEqual("runtime/color_okhsl_compat.h", compat["include"])
			self.assertIn(member, compat["getter"])
			self.assertIn(member, compat["setter"])


if __name__ == "__main__":
	unittest.main()
