#include "utils/javascript_vm.h"
#include <string>

using namespace godot;

namespace gode {

TypedArray<Dictionary> extract_js_definitions(Napi::Env env, const String &source) {
	TypedArray<Dictionary> result;
	
	Napi::HandleScope scope(env);
	
	try {
		Napi::Object global = env.Global();
		Napi::Function require = global.Get("require").As<Napi::Function>();
		if (require.IsUndefined()) {
			godot::UtilityFunctions::printerr("JS Extractor: 'require' not found in global scope");
			return result;
		}

		Napi::Object vm = require.Call({ Napi::String::New(env, "vm") }).As<Napi::Object>();
		Napi::Function script_cls = vm.Get("Script").As<Napi::Function>();
		
		std::string src_str = source.utf8().get_data();
		std::string search_str = "export default";
		size_t pos = src_str.find(search_str);
		if (pos != std::string::npos) {
			src_str.replace(pos, search_str.length(), "module.exports =");
		}
		
		Napi::Object script_obj = script_cls.New({ Napi::String::New(env, src_str) });
		
		Napi::Object context = Napi::Object::New(env);
		Napi::Object module = Napi::Object::New(env);
		Napi::Object exports = Napi::Object::New(env);
		module.Set("exports", exports);
		context.Set("module", module);
		context.Set("exports", exports);
		context.Set("console", global.Get("console"));
		
		Napi::Function create_context = vm.Get("createContext").As<Napi::Function>();
		create_context.Call({ context });
		
		Napi::Function run_in_context = script_obj.Get("runInContext").As<Napi::Function>();
		run_in_context.Call(script_obj, { context });
		
		Napi::Object result_module = context.Get("module").As<Napi::Object>();
		Napi::Value result_exports = result_module.Get("exports");
		
		if (result_exports.IsFunction()) {
			Dictionary d;
			Napi::Function func = result_exports.As<Napi::Function>();
			
			Napi::Value name_prop = func.Get("name");
			std::string name_str = "default";
			if (!name_prop.IsUndefined()) {
				std::string n = name_prop.ToString().Utf8Value();
				if (!n.empty()) name_str = n;
			}
			
			d["name"] = String(name_str.c_str());
			d["kind"] = String("export_default_class");
			d["line"] = 0;
			result.push_back(d);
		} else if (result_exports.IsObject()) {
			Napi::Object exports_obj = result_exports.As<Napi::Object>();
			Napi::Array props = exports_obj.GetPropertyNames();
			uint32_t len = props.Length();
			for (uint32_t i = 0; i < len; i++) {
				Napi::Value key = props.Get(i);
				std::string key_str = key.ToString().Utf8Value();
				Napi::Value val = exports_obj.Get(key);
				
				Dictionary d;
				d["name"] = String(key_str.c_str());
				d["line"] = 0;
				
				if (val.IsFunction()) {
					d["kind"] = String("export_class");
				} else {
					d["kind"] = String("export_variable");
				}
				
				if (key_str == "default") {
					d["kind"] = String("export_default_class");
					if (val.IsFunction()) {
						Napi::Value name_prop = val.As<Napi::Function>().Get("name");
						if (!name_prop.IsUndefined()) {
							std::string n = name_prop.ToString().Utf8Value();
							if (!n.empty()) d["name"] = String(n.c_str());
						}
					}
				}
				
				result.push_back(d);
			}
		}
		
	} catch (const Napi::Error &e) {
		godot::UtilityFunctions::printerr("JS Extractor Error: ", String(e.Message().c_str()));
	}
	
	return result;
}

Napi::Object create_js_instance(Napi::Env env, const String &source, const String &class_name) {
	Napi::HandleScope scope(env);
	Napi::Object instance;
	
	try {
		Napi::Object global = env.Global();
		Napi::Function require = global.Get("require").As<Napi::Function>();
		if (require.IsUndefined()) {
			godot::UtilityFunctions::printerr("JS Instance Error: 'require' not found");
			return instance;
		}

		Napi::Object vm = require.Call({ Napi::String::New(env, "vm") }).As<Napi::Object>();
		Napi::Function script_cls = vm.Get("Script").As<Napi::Function>();
		
		std::string src_str = source.utf8().get_data();
		std::string search_str = "export default";
		size_t pos = src_str.find(search_str);
		if (pos != std::string::npos) {
			src_str.replace(pos, search_str.length(), "module.exports =");
		}
		
		Napi::Object script_obj = script_cls.New({ Napi::String::New(env, src_str) });
		Napi::Object context = Napi::Object::New(env);
		Napi::Object module = Napi::Object::New(env);
		Napi::Object exports = Napi::Object::New(env);
		module.Set("exports", exports);
		context.Set("module", module);
		context.Set("exports", exports);
		context.Set("console", global.Get("console"));
		
		Napi::Function create_context = vm.Get("createContext").As<Napi::Function>();
		create_context.Call({ context });
		
		Napi::Function run_in_context = script_obj.Get("runInContext").As<Napi::Function>();
		run_in_context.Call(script_obj, { context });
		
		Napi::Value target_cls_val = env.Undefined();
		Napi::Object result_module = context.Get("module").As<Napi::Object>();
		Napi::Value result_exports = result_module.Get("exports");
		
		if (class_name.is_empty()) {
			if (result_exports.IsFunction()) {
				target_cls_val = result_exports;
			} else if (result_exports.IsObject() && result_exports.As<Napi::Object>().Has("default")) {
				target_cls_val = result_exports.As<Napi::Object>().Get("default");
			}
		} else {
			std::string cls_name_utf8 = class_name.utf8().get_data();
			if (result_exports.IsObject()) {
				Napi::Object exports_obj = result_exports.As<Napi::Object>();
				if (exports_obj.Has(cls_name_utf8)) {
					target_cls_val = exports_obj.Get(cls_name_utf8);
				}
			}
		}
		
		if (target_cls_val.IsFunction()) {
			Napi::Function constructor = target_cls_val.As<Napi::Function>();
			instance = constructor.New({});
		} else {
			godot::UtilityFunctions::printerr("JS Instance Error: Target class not found or not a constructor");
		}
		
	} catch (const Napi::Error &e) {
		godot::UtilityFunctions::printerr("JS Instance Error: ", String(e.Message().c_str()));
	}
	
	return instance;
}

} // namespace gode

