import configparser
import json
import pathlib
import re
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
EXAMPLE_ROOT = ROOT / "example"
EXTENSION_API_PATH = ROOT / "third/godot-cpp/gdextension/extension_api.json"
SKIPPED_BUILTIN_CLASSES = {"Nil", "void", "bool", "int", "float"}


def res_path_to_file(path: str) -> pathlib.Path:
	if not path.startswith("res://"):
		raise ValueError(f"not a Godot resource path: {path}")
	return EXAMPLE_ROOT / path.removeprefix("res://")


def load_extension_api() -> dict:
	return json.loads(EXTENSION_API_PATH.read_text(encoding="utf-8"))


def to_snake_case(name: str) -> str:
	name = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
	name = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)
	name = name.lower()
	name = name.replace("2_d", "2d")
	name = name.replace("3_d", "3d")
	name = name.replace("4_d", "4d")
	return name


class RepositoryIntegrityTests(unittest.TestCase):
	def test_scene_resource_paths_exist(self):
		missing = []
		for scene_path in sorted(EXAMPLE_ROOT.glob("scenes/**/*.tscn")):
			for match in re.finditer(r'path="(res://[^"]+)"', scene_path.read_text(encoding="utf-8")):
				resource_path = match.group(1)
				if not res_path_to_file(resource_path).exists():
					missing.append(f"{scene_path.relative_to(ROOT)} -> {resource_path}")

		self.assertEqual([], missing)

	def test_project_resource_paths_exist(self):
		project_text = (EXAMPLE_ROOT / "project.godot").read_text(encoding="utf-8")
		paths = set(re.findall(r'"(res://[^"]+)"', project_text))
		autoloads = re.findall(r'=\s*"\*?(res://[^"]+)"', project_text)
		paths.update(autoloads)

		missing = sorted(path for path in paths if not res_path_to_file(path).exists())
		self.assertEqual([], missing)

	def test_example_demo_console_is_separate_from_runtime_tests(self):
		expected_demo_files = [
			EXAMPLE_ROOT / "scripts/capability_catalog.ts",
			EXAMPLE_ROOT / "scripts/capability_selection.ts",
			EXAMPLE_ROOT / "scripts/capability_workspace.ts",
			EXAMPLE_ROOT / "scenes/capability_workspace.tscn",
		]
		missing = [str(path.relative_to(ROOT)) for path in expected_demo_files if not path.exists()]
		self.assertEqual([], missing)

		retired_demo_test_names = [
			EXAMPLE_ROOT / "scripts/test_catalog.ts",
			EXAMPLE_ROOT / "scripts/test_selection.ts",
			EXAMPLE_ROOT / "scripts/test_workspace.ts",
			EXAMPLE_ROOT / "scenes/test_workspace.tscn",
		]
		present = [str(path.relative_to(ROOT)) for path in retired_demo_test_names if path.exists()]
		self.assertEqual([], present)

		demo_text = "\n".join(
			path.read_text(encoding="utf-8")
			for path in (
				EXAMPLE_ROOT / "scripts/main_menu.ts",
				EXAMPLE_ROOT / "scripts/capability_workspace.ts",
				EXAMPLE_ROOT / "scenes/main_menu.tscn",
				EXAMPLE_ROOT / "scenes/capability_workspace.tscn",
			)
		)
		for token in ("test_catalog", "test_selection", "test_workspace", "TestGrid", "TestButton", "TestWorkspace"):
			self.assertNotIn(token, demo_text)

		self.assertTrue((EXAMPLE_ROOT / "scripts/tests").is_dir())

	def test_example_capability_menu_has_button_for_each_demo(self):
		catalog_text = (EXAMPLE_ROOT / "scripts/capability_catalog.ts").read_text(encoding="utf-8")
		scene_text = (EXAMPLE_ROOT / "scenes/main_menu.tscn").read_text(encoding="utf-8")
		demo_count = len(re.findall(r'\n\t\tid: "[^"]+"', catalog_text))
		button_count = len(re.findall(r'name="CapabilityButton[0-9]{2}"', scene_text))

		self.assertGreater(demo_count, 0)
		self.assertEqual(demo_count, button_count)

	def test_generator_sources_do_not_contain_local_machine_paths(self):
		local_path_pattern = re.compile(r"(?:[A-Za-z]:\\|/Users/|/home/[^/\s]+/)")
		offenders = []
		for path in sorted((ROOT / "generator").rglob("*.py")):
			text = path.read_text(encoding="utf-8")
			if local_path_pattern.search(text):
				offenders.append(str(path.relative_to(ROOT)))

		self.assertEqual([], offenders)

	def test_generator_readme_matches_package_layout(self):
		text = (ROOT / "generator/README.md").read_text(encoding="utf-8")
		for package_name in ("builtin", "class", "register", "dts", "core", "utils", "templates"):
			self.assertIn(f"`{package_name}/`", text)

		self.assertIn("python generator/generator.py", text)
		self.assertNotIn("`utility/`", text)

	def test_plugin_version_matches_cmake_project_version(self):
		cmake_text = (ROOT / "CMakeLists.txt").read_text(encoding="utf-8")
		match = re.search(r"project\s*\(\s*gode\s+VERSION\s+([0-9]+\.[0-9]+\.[0-9]+)", cmake_text)
		self.assertIsNotNone(match, "CMake project version was not found")
		cmake_version = match.group(1)

		parser = configparser.ConfigParser()
		parser.read(EXAMPLE_ROOT / "addons/gode/plugin.cfg", encoding="utf-8")
		self.assertEqual(cmake_version, parser["plugin"]["version"].strip('"'))

	def test_platform_build_scripts_pin_codegen_python(self):
		scripts = [
			ROOT / "shell/build-linux.sh",
			ROOT / "shell/build-macos.sh",
			ROOT / "shell/build-ios.sh",
			ROOT / "shell/build-android.sh",
			ROOT / "shell/build-windows.ps1",
			ROOT / "shell/build-android.ps1",
		]

		missing = []
		for script in scripts:
			text = script.read_text(encoding="utf-8")
			for token in ("Python3_EXECUTABLE", "GODE_RUN_CODEGEN"):
				if token not in text:
					missing.append(f"{script.relative_to(ROOT)} missing {token}")

		self.assertEqual([], missing)

	def test_node_runtime_helpers_are_split_from_runtime_lifecycle(self):
		expected_files = [
			ROOT / "include/utils/node_bootstrap_scripts.h",
			ROOT / "src/utils/node_bootstrap_scripts.cpp",
			ROOT / "include/utils/node_godot_bridge.h",
			ROOT / "src/utils/node_godot_bridge.cpp",
			ROOT / "include/utils/node_module_resolver.h",
			ROOT / "src/utils/node_module_resolver.cpp",
			ROOT / "src/utils/node_typescript_compiler_bridge.cpp",
		]
		missing = [str(path.relative_to(ROOT)) for path in expected_files if not path.exists()]
		self.assertEqual([], missing)

		source = (ROOT / "src/utils/node_runtime.cpp").read_text(encoding="utf-8")
		self.assertLessEqual(len(source.splitlines()), 450)
		for pattern in (
			r"std::string\s+boot_script\s*=\s*\n\s*\"",
			r"std::string\s+esm_script\s*=\s*\n\s*\"",
			r"static\s+Napi::Value\s+fs_readFile",
			r"static\s+Napi::Value\s+fs_stat",
			r"static\s+Napi::Value\s+preload_dlls",
			r"static\s+int\s+read_package_module_type",
			r"NodeRuntime::is_esm_file",
		):
			self.assertIsNone(re.search(pattern, source), pattern)

		bootstrap_source = (ROOT / "src/utils/node_bootstrap_scripts.cpp").read_text(encoding="utf-8")
		self.assertIn("std::string commonjs_bootstrap_script()", bootstrap_source)
		self.assertIn("std::string esm_bootstrap_script()", bootstrap_source)
		self.assertIn("'.js', '.json', '.node', '.mjs', '.cjs'", bootstrap_source)
		self.assertIn("const _gode_source_fallback", bootstrap_source)
		self.assertIn("res://.gode/build/typescript/", bootstrap_source)

	def test_node_runtime_public_v8_entries_hold_locker_and_safe_scopes(self):
		source = (ROOT / "src/utils/node_runtime.cpp").read_text(encoding="utf-8")

		def method_body(name: str) -> str:
			marker = f"NodeRuntime::{name}"
			start = source.find(marker)
			self.assertNotEqual(-1, start, name)
			next_start = len(source)
			for match in re.finditer(r"\n(?:[A-Za-z0-9_:<>]+\s+)+NodeRuntime::[A-Za-z0-9_]+\(", source[start + len(marker):]):
				next_start = start + len(marker) + match.start()
				break
			return source[start:next_start]

		for method in ("run_script", "compile_script", "get_default_class", "eval_expression"):
			body = method_body(method)
			self.assertIn("v8::Locker locker(isolate);", body)
			self.assertIn("v8::Isolate::Scope isolate_scope(isolate);", body)

		for method in ("run_script", "eval_expression"):
			body = method_body(method)
			self.assertIn("v8::HandleScope handle_scope(isolate);", body)

		for method in ("compile_script", "get_default_class"):
			body = method_body(method)
			self.assertNotIn("Napi::EscapableHandleScope", body)
			self.assertNotIn("v8::HandleScope handle_scope(isolate);", body)

	def test_module_lifecycle_owns_resource_format_refs_until_node_shutdown(self):
		source = (ROOT / "src/register_types.cpp").read_text(encoding="utf-8")

		for name in ("typescript_saver", "typescript_loader"):
			self.assertIn(f"godot::Ref<gode::{''.join(part.capitalize() for part in name.split('_'))}> {name};", source)

		self.assertNotRegex(
			source,
			r"add_resource_format_(?:loader|saver)\(gode::(?:Javascript|Typescript)(?:Loader|Saver)::get_singleton\(\)\)",
		)
		self.assertNotRegex(
			source,
			r"remove_resource_format_(?:loader|saver)\([^)]*::get_singleton\(\)\)",
		)

		shutdown_index = source.index("gode::NodeRuntime::shutdown();")
		for token in (
			"typescript_loader->clear_cache();",
			"typescript_loader.unref();",
			"typescript_saver.unref();",
		):
			self.assertIn(token, source)
			self.assertLess(source.index(token), shutdown_index, token)

		for token in (
			"javascript_loader",
			"javascript_saver",
			"add_resource_format_loader(javascript_loader)",
			"add_resource_format_saver(javascript_saver)",
		):
			self.assertNotIn(token, source)

	def test_napi_references_are_released_before_or_suppressed_after_runtime_shutdown(self):
		node_header = (ROOT / "include/utils/node_runtime.h").read_text(encoding="utf-8")
		node_source = (ROOT / "src/utils/node_runtime.cpp").read_text(encoding="utf-8")
		javascript_header = (ROOT / "include/support/javascript.h").read_text(encoding="utf-8")
		javascript_source = (ROOT / "src/support/javascript.cpp").read_text(encoding="utf-8")
		instance_source = (ROOT / "src/support/javascript_instance.cpp").read_text(encoding="utf-8")
		callable_source = (ROOT / "src/support/javascript_callable.cpp").read_text(encoding="utf-8")

		self.assertIn("static bool is_running();", node_header)
		self.assertIn("bool NodeRuntime::is_running()", node_source)
		self.assertIn("node_initialized && isolate != nullptr && env != nullptr", node_source)

		self.assertIn("~Javascript();", javascript_header)
		self.assertIn("Javascript::~Javascript()", javascript_source)
		for source in (javascript_source, instance_source, callable_source):
			self.assertIn("NodeRuntime::is_running()", source)
			self.assertIn("SuppressDestruct()", source)

		self.assertIn("default_class.Reset();", javascript_source)
		self.assertIn("js_instance.Reset();", instance_source)
		self.assertIn("func_ref.Reset();", callable_source)
		self.assertIn("javascript->instance_objects.erase(owner);", instance_source)

	def test_generated_static_napi_references_reset_before_node_environment_free(self):
		node_source = (ROOT / "src/utils/node_runtime.cpp").read_text(encoding="utf-8")
		builtin_header = (ROOT / "include/generated/register_builtin.gen.h").read_text(encoding="utf-8")
		builtin_source = (ROOT / "src/generated/register_builtin.gen.cpp").read_text(encoding="utf-8")
		class_header = (ROOT / "include/generated/register_classes.gen.h").read_text(encoding="utf-8")
		class_source = (ROOT / "src/generated/register_classes.gen.cpp").read_text(encoding="utf-8")
		register_builtin_template = (ROOT / "generator/templates/register_builtin.cpp.jinja2").read_text(encoding="utf-8")
		register_classes_template = (ROOT / "generator/templates/register_classes.cpp.jinja2").read_text(encoding="utf-8")

		for token in (
			"reset_builtin_references();",
			"reset_class_references();",
			"clear_registered_godot_classes();",
		):
			self.assertIn(token, node_source)
			self.assertLess(node_source.index(token), node_source.index("node::FreeEnvironment(env);"))

		self.assertIn("void reset_builtin_references();", builtin_header)
		self.assertIn("void reset_class_references();", class_header)
		self.assertIn("void reset_builtin_references()", builtin_source)
		self.assertIn("void reset_class_references()", class_source)
		self.assertIn("constructor.Reset();", builtin_source)
		self.assertIn("constructor.Reset();", class_source)
		self.assertIn("constructor.Reset();", register_builtin_template)
		self.assertIn("constructor.Reset();", register_classes_template)

	def test_value_convert_registry_and_cache_are_restart_safe(self):
		header = (ROOT / "include/utils/value_convert.h").read_text(encoding="utf-8")
		source = (ROOT / "src/utils/value_convert.cpp").read_text(encoding="utf-8")

		self.assertIn("void clear_registered_godot_classes();", header)
		self.assertIn("static std::vector<std::string> class_order;", source)
		self.assertIn("const bool is_new_class", source)
		self.assertIn("if (is_new_class)", source)
		self.assertNotIn("std::vector<ClassInfo> class_list", source)
		self.assertNotIn("class_list.push_back", source)
		self.assertIn("static void release_object_reference", source)
		self.assertIn("NodeRuntime::is_running()", source)
		self.assertIn("object_cache[id] = Napi::Persistent(js_obj);", source)
		self.assertNotIn("object_cache[id] = Napi::Weak(js_obj);", source)
		self.assertIn("ref.SuppressDestruct();", source)
		self.assertNotIn("entry.second.Reset();", source)

	def test_generated_refcounted_wrappers_delete_from_unref_result(self):
		template = (ROOT / "generator/templates/class_binding.cpp.jinja2").read_text(encoding="utf-8")
		resource_source = (ROOT / "src/generated/classes/resource_binding.gen.cpp").read_text(encoding="utf-8")

		for source in (template, resource_source):
			self.assertIn("if (ref->unreference())", source)
			self.assertNotIn("ref->get_reference_count() == 0", source)
			self.assertNotIn("ref->unreference();\n                if", source)

	def test_typescript_loader_exposes_explicit_cache_clear(self):
		header = (ROOT / "include/support/typescript_loader.h").read_text(encoding="utf-8")
		source = (ROOT / "src/support/typescript_loader.cpp").read_text(encoding="utf-8")

		self.assertIn("void clear_cache();", header)
		self.assertIn("void TypescriptLoader::clear_cache()", source)
		self.assertIn("scripts.clear();", source)
		self.assertIn("clear_cache();", source)

	def test_legacy_javascript_resource_loader_and_saver_are_removed(self):
		for path in (
			ROOT / "include/support/javascript_loader.h",
			ROOT / "include/support/javascript_saver.h",
			ROOT / "src/support/javascript_loader.cpp",
			ROOT / "src/support/javascript_saver.cpp",
			EXAMPLE_ROOT / "addons/gode/icons/javascript.svg",
			EXAMPLE_ROOT / "addons/gode/icons/javascript.svg.import",
		):
			self.assertFalse(path.exists(), f"{path.relative_to(ROOT)} should not exist")

		for path in sorted((ROOT / "src").glob("**/*.cpp")) + sorted((ROOT / "include").glob("**/*.h")):
			if "generated" in path.parts:
				continue
			text = path.read_text(encoding="utf-8")
			self.assertNotIn("JavascriptLoader", text, str(path.relative_to(ROOT)))
			self.assertNotIn("JavascriptSaver", text, str(path.relative_to(ROOT)))

	def test_typescript_default_config_is_packaged_and_project_root_config_exists(self):
		template_path = EXAMPLE_ROOT / "addons/gode/config/tsconfig.json"
		project_config_path = EXAMPLE_ROOT / "tsconfig.json"
		self.assertTrue(template_path.exists())
		self.assertTrue(project_config_path.exists())

		template = json.loads(template_path.read_text(encoding="utf-8"))
		project_config = json.loads(project_config_path.read_text(encoding="utf-8"))
		self.assertEqual(template, project_config)

		options = template["compilerOptions"]
		self.assertEqual("ESNext", options["module"])
		self.assertEqual("Bundler", options["moduleResolution"])
		self.assertTrue(options["strict"])
		self.assertEqual([], options["types"])
		self.assertNotIn("baseUrl", options)
		self.assertNotIn("paths", options)
		self.assertIn("**/*.ts", template["include"])
		self.assertIn("**/*.tsx", template["include"])
		self.assertIn("**/*.d.ts", template["include"])
		self.assertIn("addons/gode/tsc", template["exclude"])

		compiler_source = (ROOT / "src/utils/typescript_compiler.cpp").read_text(encoding="utf-8")
		self.assertIn('PROJECT_TYPESCRIPT_CONFIG_PATH = "res://tsconfig.json"', compiler_source)
		self.assertIn('DEFAULT_TYPESCRIPT_CONFIG_PATH = "res://addons/gode/config/tsconfig.json"', compiler_source)
		self.assertIn("ensure_project_typescript_config", compiler_source)

	def test_example_project_has_no_root_external_dependency_marker(self):
		for name in (
			"package.json",
			"node_modules",
			"gode.json",
		):
			self.assertFalse(
				(EXAMPLE_ROOT / name).exists(),
				f"example/{name} should not be present in the dependency-free sample project",
			)

	def test_gode_json_controls_commercial_npm_export_policy(self):
		template_path = EXAMPLE_ROOT / "addons/gode/config/gode.json"
		self.assertTrue(template_path.exists())
		config = json.loads(template_path.read_text(encoding="utf-8"))
		npm_config = config["export"]["npm"]
		self.assertEqual(
			{
				"exportDependencies",
				"requireTools",
				"includeManifests",
				"includeNodeModules",
				"excludePaths",
				"extraIncludePaths",
			},
			set(npm_config),
		)
		self.assertEqual(["node_modules/.cache", "node_modules/.bin"], npm_config["excludePaths"])

		plugin_source = (EXAMPLE_ROOT / "addons/gode/gode.gd").read_text(encoding="utf-8")
		export_source = (EXAMPLE_ROOT / "addons/gode/runtime/export_plugin.gd").read_text(encoding="utf-8")

		for token in (
			"gode/export/npm",
			"ProjectSettings.add_property_info",
			"_ensure_export_settings",
		):
			self.assertNotIn(token, plugin_source)
			self.assertNotIn(token, export_source)

		for token in (
			'GODE_CONFIG_PATH := "res://gode.json"',
			'DEFAULT_GODE_CONFIG_PATH := "res://addons/gode/config/gode.json"',
			"_load_npm_config",
			"_create_project_gode_config",
			"_default_npm_config",
			"_merge_npm_config_value",
			'"exportDependencies": true',
			'"requireTools": true',
			'"includeManifests": true',
			'"includeNodeModules": true',
			'"excludePaths": PackedStringArray(["node_modules/.cache", "node_modules/.bin"])',
			'"extraIncludePaths": PackedStringArray()',
		):
			self.assertIn(token, export_source)

		for token in (
			"NPM_MANIFEST_FILES",
			"_prepare_npm_export",
			"_export_npm_runtime_snapshot",
			"_add_export_directory(\"res://node_modules\")",
			"add_file(source_path, FileAccess.get_file_as_bytes(source_path), false)",
			"OS.execute(candidate, PackedStringArray([\"--version\"])",
			'_command_exists("node")',
			'_command_exists("npm")',
			'_file_exists("res://package.json") or _dir_exists("res://node_modules")',
			"[Gode Export] Created project config from template",
		):
			self.assertIn(token, export_source)

		for token in (
			"nativeAddons",
			"get_extension().to_lower() == \"node\"",
			"NPM_MARKER_FILES",
			"_detect_package_manager",
			"allowYarnPnP",
			"packageManager",
			".pnp.cjs",
		):
			self.assertNotIn(token, export_source)

	def test_support_sources_are_not_nested_by_language(self):
		for directory in (
			ROOT / "include/support/javascript",
			ROOT / "include/support/typescript",
			ROOT / "src/support/javascript",
			ROOT / "src/support/typescript",
		):
			self.assertFalse(directory.exists(), f"{directory} should be flattened; filenames already include the language")

	def test_godot_module_no_longer_exports_legacy_globals(self):
		for path in (
			ROOT / "generator/templates/register_classes.cpp.jinja2",
			ROOT / "generator/templates/builtin_binding.cpp.jinja2",
			ROOT / "generator/templates/utility_functions.cpp.jinja2",
			ROOT / "src/generated/register_classes.gen.cpp",
			ROOT / "src/generated/utility_functions/utility_functions.cpp",
		):
			text = path.read_text(encoding="utf-8")
			self.assertNotIn("env.Global()", text, str(path.relative_to(ROOT)))
			self.assertNotIn("global.Set(", text, str(path.relative_to(ROOT)))

		for path in (ROOT / "src/generated/builtin").glob("*_binding.gen.cpp"):
			text = path.read_text(encoding="utf-8")
			self.assertNotIn("env.Global()", text, str(path.relative_to(ROOT)))
			self.assertNotIn("global.Set(", text, str(path.relative_to(ROOT)))

		for path in (
			ROOT / "generator/dts/dts_generator.py",
			ROOT / "example/addons/gode/types/godot.d.ts",
			ROOT / "example/addons/gode/types/globals.d.ts",
		):
			text = path.read_text(encoding="utf-8")
			self.assertNotIn("GodotNamespace", text, str(path.relative_to(ROOT)))
			self.assertNotIn("export default", text, str(path.relative_to(ROOT)))
			self.assertNotIn("GodotModule.", text, str(path.relative_to(ROOT)))

	def test_gallery_scripts_use_explicit_godot_imports(self):
		for script_root in (ROOT / "example/scripts", ROOT / "gallery/tps-demo-js", ROOT / "gallery/tps-demo-ts"):
			if not script_root.exists():
				continue
			for path in sorted(list(script_root.rglob("*.js")) + list(script_root.rglob("*.ts"))):
				if "node_modules" in path.parts or path.name.endswith(".d.ts"):
					continue
				text = path.read_text(encoding="utf-8")
				self.assertNotIn("import godot from \"godot\"", text, str(path.relative_to(ROOT)))
				self.assertIsNone(
					re.search(
						r"globalThis\.(?:Performance|Engine|ProjectSettings|OS|Time|ResourceLoader|ResourceSaver|Input|DisplayServer|RenderingServer|PhysicsServer3D|GD|Vector[234]i?|Color|Node)",
						text,
					),
					str(path.relative_to(ROOT)),
				)

	def test_default_value_evaluator_uses_local_godot_scope_only(self):
		source = (ROOT / "src/utils/node_runtime.cpp").read_text(encoding="utf-8")
		self.assertIn("with (godot)", source)
		self.assertIn("process._linkedBinding('godot')", source)
		self.assertNotIn("globalThis.Vector3", source)
		self.assertNotIn("globalThis.Engine", source)

	def test_func_utils_short_circuits_pending_conversion_exceptions(self):
		source = (ROOT / "include/utils/func_utils.h").read_text(encoding="utf-8")
		self.assertIn("env.IsExceptionPending()", source)
		self.assertIn("convert_args<0, P...>", source)
		self.assertNotIn("Func(napi_to_godot<P>(args[Is])...)", source)
		self.assertNotIn("(instance->*Func)(napi_to_godot<P>(args[Is])...)", source)
		self.assertNotIn("(instance->*Func)(napi_to_godot<P>(val)...)", source)

	def test_fixed_arity_bindings_validate_argument_count(self):
		source = (ROOT / "include/utils/func_utils.h").read_text(encoding="utf-8")
		runtime_test = (ROOT / "example/scripts/tests/runtime_integration_test.ts").read_text(encoding="utf-8")

		self.assertIn("prepare_fixed_args", source)
		self.assertIn("required_arg_count", source)
		self.assertIn("Godot API call expected", source)
		self.assertNotIn("apply_default_args", source)
		self.assertNotIn("args.resize(sizeof...(P), info.Env().Undefined())", source)

		for token in (
			"this.set_process()",
			"this.set_process(true, false)",
			"this.tr()",
			"this.tr(\"message\", \"context\", \"extra\")",
			"packedInts.slice()",
			"packedInts.slice(1, 2, 3)",
			"packedInts.size(1)",
			):
				self.assertIn(token, runtime_test)

	def test_scalar_and_string_conversions_reject_wrong_javascript_types(self):
		value_convert = (ROOT / "include/utils/value_convert.h").read_text(encoding="utf-8")
		runtime_test = (ROOT / "example/scripts/tests/runtime_integration_test.ts").read_text(encoding="utf-8")

		for token in (
			"napi_to_godot_bool",
			"napi_to_godot_float",
			"throw_string_type_error",
			"throw_node_path_type_error",
			"std::isnan(number)",
			"!value.IsBoolean()",
			"!value.IsNumber()",
			"variant.get_type() == godot::Variant::Type::STRING",
			"variant.get_type() == godot::Variant::Type::STRING_NAME",
			"variant.get_type() == godot::Variant::Type::NODE_PATH",
		):
			self.assertIn(token, value_convert)

		for token in (
			"return value.ToBoolean().Value();",
			"return static_cast<ClearType>(value.ToNumber().DoubleValue());",
			"return godot::String();",
		):
			self.assertNotIn(token, value_convert)

		for token in (
			'this.set_process("true")',
			"this.tr(1)",
			"this.has_node(1)",
			'Color.from_ok_hsl("0.58", 0.5, 0.79)',
			"Color.from_ok_hsl(NaN, 0.5, 0.79)",
			"new Vector3(Infinity, 0, 0)",
			'vector3.x = "4"',
		):
			self.assertIn(token, runtime_test)

	def test_object_and_ref_conversions_reject_plain_javascript_objects(self):
		value_convert = (ROOT / "include/utils/value_convert.h").read_text(encoding="utf-8")
		class_template = (ROOT / "generator/templates/class_binding.cpp.jinja2").read_text(encoding="utf-8")
		node_source = (ROOT / "src/generated/classes/node_binding.gen.cpp").read_text(encoding="utf-8")
		runtime_test = (ROOT / "example/scripts/tests/runtime_integration_test.ts").read_text(encoding="utf-8")

		for token in (
			"napi_to_godot_object_value",
			"napi_to_godot_object_pointer",
			"is_godot_ref",
			"Expected a Godot object wrapper or null",
			"Expected a Godot object wrapper compatible with the API parameter type",
			"unwrap_godot_object(value.As<Napi::Object>())",
			"ClearType(godot::Variant(typed_object))",
		):
			self.assertIn(token, value_convert)

		for token in (
			"constructor expected a Godot object wrapper",
			"constructor expected an object compatible with",
			"constructor expected no arguments",
			"cannot be constructed directly",
		):
			self.assertIn(token, class_template)

		for token in (
			"Node constructor expected a Godot object wrapper",
			"Node constructor expected an object compatible with Node",
			"Node constructor expected no arguments",
		):
			self.assertIn(token, node_source)

		for token in (
			"this.add_child({})",
			"ImageTexture.create_from_image({})",
			"new Node({})",
			"new Node(1)",
		):
			self.assertIn(token, runtime_test)

	def test_builtin_constructors_and_operators_reject_invalid_signatures(self):
		template = (ROOT / "generator/templates/builtin_binding.cpp.jinja2").read_text(encoding="utf-8")
		builtin_generator = (ROOT / "generator/builtin/builtin_classes_generator.py").read_text(encoding="utf-8")
		runtime_test = (ROOT / "example/scripts/tests/runtime_integration_test.ts").read_text(encoding="utf-8")
		vector2i_source = (ROOT / "src/generated/builtin/vector2i_binding.gen.cpp").read_text(encoding="utf-8")
		array_source = (ROOT / "src/generated/builtin/array_binding.gen.cpp").read_text(encoding="utf-8")
		packed_source = (ROOT / "src/generated/builtin/packed_int32_array_binding.gen.cpp").read_text(encoding="utf-8")

		self.assertIn("No matching constructor overload for {{ js_class_name }}", template)
		self.assertIn("has_unary", builtin_generator)
		self.assertIn("has_binary", builtin_generator)
		self.assertIn("gode::throw_arg_count_error(info.Env(), info.Length(), 1, 1);", template)
		self.assertIn("gode::throw_arg_count_error(info.Env(), info.Length(), 0, 0);", template)

		self.assertIn("No matching constructor overload for Vector2i", vector2i_source)
		self.assertIn("No matching constructor overload for GDArray", array_source)
		self.assertIn("No matching constructor overload for PackedInt32Array", packed_source)
		self.assertIn("info[0].IsNumber() || info[0].IsBigInt()", vector2i_source)
		self.assertIn("gode::throw_arg_count_error(info.Env(), info.Length(), 1, 1);", vector2i_source)
		self.assertIn("gode::throw_arg_count_error(info.Env(), info.Length(), 0, 0);", vector2i_source)

		for token in (
			"new Vector2i(1)",
			"new Vector2i(\"x\", 2)",
			"new Vector2i(1, 2, 3)",
			"vector2i.add(new Vector2i(3, 4), new Vector2i(5, 6))",
			"vector2i.negate(1)",
			"new Vector2i(1n, 2n)",
			"vector2i.multiply(2n)",
			"new PackedInt32Array([1n, 2n])",
			"new GDArray(1)",
			"new PackedInt32Array(1)",
		):
			self.assertIn(token, runtime_test)

	def test_js_arrays_are_first_class_array_arguments(self):
		func_utils = (ROOT / "include/utils/func_utils.h").read_text(encoding="utf-8")
		value_convert = (ROOT / "include/utils/value_convert.h").read_text(encoding="utf-8")
		value_convert_source = (ROOT / "src/utils/value_convert.cpp").read_text(encoding="utf-8")
		binding_policy = (ROOT / "generator/utils/binding_policy.py").read_text(encoding="utf-8")
		builtin_generator = (ROOT / "generator/builtin/builtin_classes_generator.py").read_text(encoding="utf-8")
		dts_generator = (ROOT / "generator/dts/dts_generator.py").read_text(encoding="utf-8")
		runtime_test = (ROOT / "example/scripts/tests/runtime_integration_test.ts").read_text(encoding="utf-8")
		packed_source = (ROOT / "src/generated/builtin/packed_int32_array_binding.gen.cpp").read_text(encoding="utf-8")
		array_source = (ROOT / "src/generated/builtin/array_binding.gen.cpp").read_text(encoding="utf-8")
		resource_loader_source = (ROOT / "src/generated/classes/resource_loader_binding.gen.cpp").read_text(encoding="utf-8")

		self.assertIn("is_godot_typed_array", value_convert)
		self.assertIn("is_godot_packed_array", value_convert)
		self.assertIn("js_array_to_packed_array", value_convert)
		self.assertIn("js_array_to_typed_array", value_convert)
		self.assertIn("std::is_same_v<ClearType, godot::Array>", value_convert)
		self.assertIn("sync_godot_out_argument", value_convert)
		self.assertIn("sync_godot_array_to_js_array", value_convert_source)
		self.assertIn("sync_godot_variant_out_argument", value_convert_source)
		self.assertIn("sync_out_args", func_utils)
		self.assertIn("std::is_lvalue_reference_v<Param>", func_utils)
		self.assertIn("call_class_method_bind", func_utils)
		self.assertIn('("ResourceLoader", "load_threaded_get_status"): (1,)', binding_policy)
		self.assertIn("BIND_NAPI_TO_BUILTIN(StringBinding)", value_convert_source)
		self.assertIn("BIND_NAPI_TO_BUILTIN(StringNameBinding)", value_convert_source)
		self.assertIn("BIND_NAPI_TO_BUILTIN(NodePathBinding)", value_convert_source)
		self.assertIn("PACKED_ARRAY_TYPES", builtin_generator)
		self.assertIn("PACKED_ARRAY_ELEMENT_TYPES", dts_generator)
		self.assertIn("new PackedInt32Array([1, 2, 3])", runtime_test)
		self.assertIn("load_threaded_get_status", runtime_test)
		self.assertIn("threadedProgress[0]", runtime_test)
		self.assertIn("call_class_method_bind(", resource_loader_source)
		self.assertIn('"load_threaded_get_status"', resource_loader_source)
		self.assertNotIn("call_builtin_method(&godot::ResourceLoader::load_threaded_get_status", resource_loader_source)
		self.assertIn("info[0].IsArray() || (info[0].IsObject() && info[0].As<Napi::Object>().InstanceOf(PackedInt32ArrayBinding::constructor.Value()))", packed_source)
		self.assertIn("info[0].IsArray() || (info[0].IsObject() && info[0].As<Napi::Object>().InstanceOf(ArrayBinding::constructor.Value()))", array_source)

	def test_builtin_template_short_circuits_pending_conversion_exceptions(self):
		source = (ROOT / "generator/templates/builtin_binding.cpp.jinja2").read_text(encoding="utf-8")
		self.assertIn("gode::ConvertedArgTuple", source)
		self.assertIn("if (!gode::convert_args<0,", source)
		self.assertIn("auto converted_value = gode::napi_to_godot", source)
		self.assertIn("if (info.Env().IsExceptionPending())", source)
		self.assertIn("return info.Env().Undefined();", source)
		self.assertNotIn("{{ member.custom_setter }}(instance, gode::napi_to_godot", source)
		self.assertNotIn("replace('{value}', 'gode::napi_to_godot", source)

	def test_javascript_runtime_clears_pending_conversion_exceptions(self):
		instance_source = (ROOT / "src/support/javascript_instance.cpp").read_text(encoding="utf-8")
		callable_source = (ROOT / "src/support/javascript_callable.cpp").read_text(encoding="utf-8")
		node_runtime_source = (ROOT / "src/utils/node_runtime.cpp").read_text(encoding="utf-8")

		self.assertIn('log_and_clear_pending_js_exception(env, context + " return conversion")', instance_source)
		self.assertIn('log_and_clear_pending_js_exception(env, "JS Callable return conversion")', callable_source)
		self.assertIn('log_and_clear_pending_js_exception(thread_local_env, "NodeRuntime eval expression result conversion")', node_runtime_source)
		self.assertNotIn("r_error.error = GDEXTENSION_CALL_OK;\n\t\tr_error.argument = 0;\n\t\tr_error.expected = 0;\n\t\tif (result.IsPromise())", instance_source)
		self.assertNotIn("r_return_value = napi_to_godot(result);\n\t\tr_call_error.error = GDEXTENSION_CALL_OK", callable_source)

	def test_class_vararg_methodbind_errors_surface_to_javascript(self):
		func_utils = (ROOT / "include/utils/func_utils.h").read_text(encoding="utf-8")
		vararg_macros = (ROOT / "include/utils/vararg_macros.h").read_text(encoding="utf-8")
		runtime_test = (ROOT / "example/scripts/tests/runtime_integration_test.ts").read_text(encoding="utf-8")

		self.assertIn("throw_if_godot_call_failed", func_utils)
		self.assertIn("GDEXTENSION_CALL_ERROR_TOO_FEW_ARGUMENTS", func_utils)
		self.assertIn("GDExtensionCallError *r_error", vararg_macros)
		self.assertIn("object_method_bind_call", vararg_macros)
		self.assertIn("error->error != GDEXTENSION_CALL_OK", vararg_macros)
		self.assertNotIn("GDExtensionCallError error; \\\n\t::godot::gdextension_interface::object_method_bind_call", vararg_macros)
		self.assertIn("this.emit_signal()", runtime_test)
		self.assertIn("Godot vararg MethodBind call failed: TOO_FEW_ARGUMENTS", runtime_test)

	def test_addon_manifest_paths_exist(self):
		manifest = EXAMPLE_ROOT / "addons/gode/binary/gode.gdextension"
		text = manifest.read_text(encoding="utf-8")
		missing = []
		for match in re.finditer(r'=\s*"(res://[^"]+)"', text):
			resource_path = match.group(1)
			if "/binary/" in resource_path and resource_path != "res://addons/gode/binary/gode.gdextension":
				continue
			if not res_path_to_file(resource_path).exists():
				missing.append(resource_path)

		self.assertEqual([], sorted(missing))

	def test_generated_utility_functions_match_extension_api(self):
		api = load_extension_api()
		expected = sorted(func["name"] for func in api.get("utility_functions", []))

		source = (ROOT / "src/generated/utility_functions/utility_functions.cpp").read_text(encoding="utf-8")
		actual = sorted(re.findall(r'InstanceMethod\("([^"]+)"', source))

		self.assertEqual(expected, actual)

	def test_godot_cpp_omitted_utility_functions_use_low_level_bindings(self):
		sys.path.insert(0, str(ROOT / "generator"))
		try:
			from register.utility_functions_generator import GODOT_CPP_OMITTED_UTILITY_FUNCTIONS
		finally:
			sys.path.pop(0)

		api = load_extension_api()
		api_functions = {func["name"]: func for func in api.get("utility_functions", [])}
		upstream_generator = (ROOT / "third/godot-cpp/binding_generator.py").read_text(encoding="utf-8")
		source = (ROOT / "src/generated/utility_functions/utility_functions.cpp").read_text(encoding="utf-8")
		low_level_header = (ROOT / "include/generated/utility_functions/utility_functions_vararg_method.h").read_text(encoding="utf-8")

		self.assertEqual({"is_instance_valid"}, set(GODOT_CPP_OMITTED_UTILITY_FUNCTIONS))
		for name in GODOT_CPP_OMITTED_UTILITY_FUNCTIONS:
			self.assertIn(name, api_functions)
			self.assertIn(f'function["name"] == "{name}"', upstream_generator)
			self.assertIn(f"gode::utility::{name}_internal", source)
			self.assertNotIn(f"godot::UtilityFunctions::{name}", source)
			self.assertRegex(
				low_level_header,
				rf"DEFINE_UTILITY_FUNC_RET\({re.escape(name)}, {api_functions[name]['hash']}, bool\)",
			)

	def test_generated_builtin_registration_matches_extension_api(self):
		api = load_extension_api()
		expected = sorted(
			cls["name"]
			for cls in api.get("builtin_classes", [])
			if cls["name"] not in SKIPPED_BUILTIN_CLASSES
		)

		source = (ROOT / "src/generated/register_builtin.gen.cpp").read_text(encoding="utf-8")
		actual = sorted(re.findall(r"\b([A-Za-z0-9_]+)Binding::init\(env, exports\);", source))

		self.assertEqual(expected, actual)

	def test_generated_class_registration_matches_extension_api(self):
		api = load_extension_api()
		expected = sorted(cls["name"] for cls in api.get("classes", []))

		source = (ROOT / "src/generated/register_classes.gen.cpp").read_text(encoding="utf-8")
		actual = sorted(re.findall(r"\b([A-Za-z0-9_]+)Binding::init\(env, exports\);", source))

		self.assertEqual(expected, actual)

		missing_files = []
		for class_name in expected:
			snake_name = to_snake_case(class_name)
			for generated_path in (
				ROOT / "include/generated/classes" / f"{snake_name}_binding.gen.h",
				ROOT / "src/generated/classes" / f"{snake_name}_binding.gen.cpp",
			):
				if not generated_path.exists():
					missing_files.append(str(generated_path.relative_to(ROOT)))

		self.assertEqual([], missing_files)

	def test_generated_singleton_accessors_use_shared_object_wrapping(self):
		source = (ROOT / "src/generated/register_classes.gen.cpp").read_text(encoding="utf-8")
		self.assertNotIn("static Napi::ObjectReference ref", source)
		self.assertIn("gode::wrap_godot_object", source)

	def test_generated_class_object_wrappers_use_external_factory(self):
		source = (ROOT / "src/generated/classes/project_settings_binding.gen.cpp").read_text(encoding="utf-8")
		self.assertIn("Napi::Object ProjectSettingsBinding_create", source)
		self.assertIn("return ProjectSettingsBinding::create_singleton(env, typed_instance);", source)
		self.assertIn("&ProjectSettingsBinding_create", source)

	def test_generated_refcounted_wrappers_hold_external_references(self):
		api = load_extension_api()
		missing = []

		for cls in api.get("classes", []):
			if not cls.get("is_refcounted"):
				continue
			class_name = cls["name"]
			source_path = ROOT / "src/generated/classes" / f"{to_snake_case(class_name)}_binding.gen.cpp"
			source = source_path.read_text(encoding="utf-8")
			if "if (!owns_instance) {" not in source:
				missing.append(f"{class_name}: missing non-owned reference guard")
			if "ref->reference();" not in source:
				missing.append(f"{class_name}: missing RefCounted reference")
			if "referenced_instance = true;" not in source:
				missing.append(f"{class_name}: missing referenced_instance flag")

		self.assertEqual([], missing)

	def test_generated_default_args_do_not_emit_raw_godot_string_markers(self):
		offenders = []
		for source_path in sorted((ROOT / "src/generated").glob("**/*.gen.cpp")):
			source = source_path.read_text(encoding="utf-8")
			for line_number, line in enumerate(source.splitlines(), start=1):
				if 'godot_to_napi(info.Env(), &"' in line or 'godot_to_napi(info.Env(), ^"' in line:
					offenders.append(f"{source_path.relative_to(ROOT)}:{line_number}: {line.strip()}")

		self.assertEqual([], offenders)

	def test_generated_js_api_renames_match_typescript_contract(self):
		sys.path.insert(0, str(ROOT / "generator"))
		try:
			from utils.type_mappings import JS_CLASS_RENAME_MAP
		finally:
			sys.path.pop(0)

		self.assertEqual(
			{
				"Object": "GodotObject",
				"String": "GDString",
				"Dictionary": "GDDictionary",
				"Array": "GDArray",
			},
			JS_CLASS_RENAME_MAP,
		)

		godot_dts = (ROOT / "example/addons/gode/types/godot.d.ts").read_text(encoding="utf-8")
		globals_dts = (ROOT / "example/addons/gode/types/globals.d.ts").read_text(encoding="utf-8")
		source_paths = {
			"Object": ROOT / "src/generated/classes/object_binding.gen.cpp",
			"String": ROOT / "src/generated/builtin/string_binding.gen.cpp",
			"Dictionary": ROOT / "src/generated/builtin/dictionary_binding.gen.cpp",
			"Array": ROOT / "src/generated/builtin/array_binding.gen.cpp",
		}

		for godot_name, js_name in JS_CLASS_RENAME_MAP.items():
			source = source_paths[godot_name].read_text(encoding="utf-8")
			self.assertIn(f'DefineClass(env, "{js_name}"', source)
			self.assertIn(f'exports.Set("{js_name}", func);', source)
			self.assertIn(f"    export class {js_name}", godot_dts)
			self.assertNotIn(f"        {js_name}: typeof {js_name};", godot_dts)
			self.assertNotIn(f"  type {js_name} = GodotModule.{js_name};", globals_dts)
			self.assertNotIn(f"  const {js_name}: typeof GodotModule.{js_name};", globals_dts)

		object_source = source_paths["Object"].read_text(encoding="utf-8")
		self.assertIn('register_class("GodotObject", "Object"', object_source)
		bootstrap_source = (ROOT / "src/utils/node_bootstrap_scripts.cpp").read_text(encoding="utf-8")
		self.assertIn("gode.GodotObject.prototype.to_signal", bootstrap_source)
		self.assertNotIn("gode.GDObject", bootstrap_source)
		self.assertNotIn("GDObject", object_source)
		self.assertNotIn("GDObject", godot_dts)
		self.assertNotIn("GDObject", globals_dts)
		self.assertIn('"typeof"(variable: VariantArgument): number;', godot_dts)
		self.assertNotIn("typeof_gd(", godot_dts)
		self.assertIn("add(right: Vector2i): Vector2i;", godot_dts)
		self.assertIn("multiply(right: number | bigint): Vector2i;", godot_dts)

	def test_generated_color_okhsl_compatibility_matches_dts(self):
		source = (ROOT / "src/generated/builtin/color_binding.gen.cpp").read_text(encoding="utf-8")
		header = (ROOT / "include/generated/builtin/color_binding.gen.h").read_text(encoding="utf-8")
		dts = (ROOT / "example/addons/gode/types/godot.d.ts").read_text(encoding="utf-8")

		self.assertIn('#include "utils/color_okhsl_compat.h"', source)
		self.assertIn('StaticMethod("from_ok_hsl", &ColorBinding::from_ok_hsl)', source)
		self.assertIn("return call_builtin_method(&gode::color_okhsl_compat::from_ok_hsl", source)
		self.assertIn("static Napi::Value from_ok_hsl", header)
		self.assertIn("static from_ok_hsl(h: number, s: number, l: number, alpha?: number): Color;", dts)

		for member in ("ok_hsl_h", "ok_hsl_s", "ok_hsl_l"):
			self.assertIn(f'InstanceAccessor("{member}"', source)
			self.assertIn(f"{member}: number;", dts)
			self.assertIn(f"gode::color_okhsl_compat::get_{member}", source)
			self.assertIn(f"gode::color_okhsl_compat::set_{member}", source)

	def test_generated_dts_singletons_are_instances_not_constructors(self):
		api = load_extension_api()
		godot_dts = (ROOT / "example/addons/gode/types/godot.d.ts").read_text(encoding="utf-8")
		globals_dts = (ROOT / "example/addons/gode/types/globals.d.ts").read_text(encoding="utf-8")
		rename_map = {
			"Object": "GodotObject",
			"String": "GDString",
			"Dictionary": "GDDictionary",
			"Array": "GDArray",
		}

		for singleton in api.get("singletons", []):
			name = singleton["name"]
			type_name = rename_map.get(singleton["type"], singleton["type"])

			self.assertEqual(
				1,
				godot_dts.count(f"    export const {name}: {type_name};"),
				f"{name} should be exported once as a singleton instance",
			)
			self.assertIn(f"    export type {type_name} = __GodotSingletonBases.{type_name};", godot_dts)
			self.assertNotIn(f"    export const {name}: typeof {type_name};", godot_dts)
			self.assertNotIn(f"        {name}: {type_name};", godot_dts)
			self.assertNotIn(f"        {name}: typeof {type_name};", godot_dts)
			self.assertNotIn(f"  type {name} = GodotModule.{type_name};", globals_dts)
			self.assertNotIn(f"  const {name}: GodotModule.{type_name};", globals_dts)
			self.assertNotIn(f"  const {name}: typeof GodotModule.{type_name};", globals_dts)

		self.assertIn("    export class Node extends GodotObject {", godot_dts)
		self.assertNotIn("    export const Node: typeof Node;", godot_dts)
		self.assertNotIn("    export type Node = Node;", godot_dts)
		self.assertNotIn("        Node: typeof Node;", godot_dts)
		self.assertIn("    export class Color {", godot_dts)
		self.assertIn("export type VariantArgument = null | undefined | boolean | number | bigint | string", godot_dts)
		self.assertIn("Map<VariantArgument, VariantArgument>", godot_dts)
		self.assertIn("GDDictionary | { [key: string]: VariantArgument } | Map<VariantArgument, VariantArgument>", godot_dts)
		self.assertIn("count: number | bigint", godot_dts)
		self.assertNotIn("  const Color: typeof GodotModule.Color;", globals_dts)
		self.assertNotIn("  const Engine: GodotModule.Engine;", globals_dts)
		self.assertIn("  function Export(hint: number, hintString?: string): any;", globals_dts)
		self.assertIn("  function Signal(...args: any[]): any;", globals_dts)
		self.assertIn("  function Tool(...args: any[]): any;", globals_dts)
		self.assertNotIn("GodotModule.", globals_dts)
		self.assertIn("    export const enum VariantType {", godot_dts)
		self.assertNotIn("    export const VariantType: typeof VariantType;", godot_dts)
		self.assertIn("    export class PhysicsServer3DExtension extends __GodotSingletonBases.PhysicsServer3D {", godot_dts)

	def test_unsafe_pointer_methods_are_not_exposed(self):
		sys.path.insert(0, str(ROOT / "generator"))
		try:
			from utils.binding_policy import skipped_method_reason
		finally:
			sys.path.pop(0)

		api = load_extension_api()
		object_class_names = {cls["name"] for cls in api.get("classes", [])}
		dts = (ROOT / "example/addons/gode/types/godot.d.ts").read_text(encoding="utf-8")

		unsafe_methods = []
		for cls in api.get("classes", []):
			for method in cls.get("methods", []):
				reason = skipped_method_reason(method, object_class_names)
				if reason:
					unsafe_methods.append((cls["name"], method["name"], reason))

		self.assertGreater(len(unsafe_methods), 0)

		still_exposed = []
		for class_name, method_name, reason in unsafe_methods:
			snake_name = to_snake_case(class_name)
			source = (ROOT / "src/generated/classes" / f"{snake_name}_binding.gen.cpp").read_text(encoding="utf-8")
			header = (ROOT / "include/generated/classes" / f"{snake_name}_binding.gen.h").read_text(encoding="utf-8")
			dts_name = "GodotObject" if class_name == "Object" else class_name
			class_match = re.search(
				rf"    class {re.escape(dts_name)}[^\n]* \{{\n(?P<body>.*?)\n    \}}",
				dts,
				re.DOTALL,
			)
			if f'prototype.Set("{method_name}"' in source:
				still_exposed.append(f"{class_name}.{method_name} source ({reason})")
			if f" {method_name}(const Napi::CallbackInfo& info)" in header:
				still_exposed.append(f"{class_name}.{method_name} header ({reason})")
			if class_match and f"        {method_name}(" in class_match.group("body"):
				still_exposed.append(f"{class_name}.{method_name} dts ({reason})")

		self.assertEqual([], still_exposed)

	def test_all_typed_collection_api_types_have_cpp_mappings(self):
		sys.path.insert(0, str(ROOT / "generator"))
		try:
			from utils.type_mappings import get_cpp_type
		finally:
			sys.path.pop(0)

		api = load_extension_api()
		refcounted_classes = {cls["name"] for cls in api.get("classes", []) if cls.get("is_refcounted")}
		typed_types = set()

		def collect_type(type_name):
			if isinstance(type_name, str) and type_name.startswith(("typedarray::", "typeddictionary::")):
				typed_types.add(type_name)

		for section in ("classes", "builtin_classes"):
			for cls in api.get(section, []):
				for prop in cls.get("properties", []):
					collect_type(prop.get("type"))
				for method in cls.get("methods", []):
					collect_type((method.get("return_value") or {}).get("type"))
					collect_type(method.get("return_type"))
					for arg in method.get("arguments", []):
						collect_type(arg.get("type"))

		for func in api.get("utility_functions", []):
			collect_type((func.get("return_value") or {}).get("type"))
			collect_type(func.get("return_type"))
			for arg in func.get("arguments", []):
				collect_type(arg.get("type"))

		self.assertGreater(len(typed_types), 0)
		invalid = []
		for type_name in sorted(typed_types):
			cpp_type = get_cpp_type(type_name, "", refcounted_classes, is_arg=True)
			if "typedarray::" in cpp_type or "typeddictionary::" in cpp_type:
				invalid.append(f"{type_name} -> {cpp_type}")

		self.assertEqual([], invalid)


if __name__ == "__main__":
	unittest.main()
