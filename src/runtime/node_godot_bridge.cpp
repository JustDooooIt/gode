#include "runtime/node_godot_bridge.h"

#include <godot_cpp/classes/dir_access.hpp>
#include <godot_cpp/classes/file_access.hpp>

#include <cstdint>
#include <string>

#ifdef WIN32
#include <windows.h>

static std::wstring get_module_file_name(HMODULE module) {
	std::wstring path(MAX_PATH, L'\0');
	for (;;) {
		DWORD length = GetModuleFileNameW(module, path.data(), static_cast<DWORD>(path.size()));
		if (length == 0) {
			return {};
		}
		if (length < path.size()) {
			path.resize(length);
			return path;
		}
		path.resize(path.size() * 2);
	}
}
#elif defined(__APPLE__) || defined(__linux__)
#include <dlfcn.h>

static void promote_current_module_symbols(void *symbol) {
	Dl_info info = {};
	if (dladdr(symbol, &info) == 0 || !info.dli_fname) {
		return;
	}
#ifdef RTLD_NOLOAD
	void *existing_handle = dlopen(info.dli_fname, RTLD_NOW | RTLD_GLOBAL | RTLD_NOLOAD);
	if (existing_handle) {
		return;
	}
#endif
	(void)dlopen(info.dli_fname, RTLD_NOW | RTLD_GLOBAL);
}
#endif

namespace gode::node_runtime_bridge {

static bool is_godot_path(const std::string &path) {
	return path.find("res://") == 0 || path.find("user://") == 0;
}

static Napi::Value fs_readFile(const Napi::CallbackInfo &info) {
	Napi::Env env = info.Env();
	if (info.Length() < 1 || !info[0].IsString()) {
		return env.Null();
	}
	std::string path = info[0].As<Napi::String>().Utf8Value();
	if (!is_godot_path(path)) {
		return env.Null();
	}

	godot::Ref<godot::FileAccess> file = godot::FileAccess::open(path.c_str(), godot::FileAccess::READ);
	if (file.is_null()) {
		return env.Null();
	}

	uint64_t len = file->get_length();
	godot::PackedByteArray pba = file->get_buffer(len);
	return Napi::String::New(env, reinterpret_cast<const char *>(pba.ptr()), len);
}

static Napi::Value fs_stat(const Napi::CallbackInfo &info) {
	Napi::Env env = info.Env();
	if (info.Length() < 1 || !info[0].IsString()) {
		return Napi::Number::New(env, 0);
	}
	std::string path = info[0].As<Napi::String>().Utf8Value();
	if (!is_godot_path(path)) {
		return Napi::Number::New(env, 0);
	}

	godot::String gd_path = godot::String::utf8(path.c_str());
	if (godot::FileAccess::file_exists(gd_path)) {
		return Napi::Number::New(env, 1);
	}
	if (godot::DirAccess::dir_exists_absolute(gd_path)) {
		return Napi::Number::New(env, 2);
	}
	return Napi::Number::New(env, 0);
}

static Napi::Value noop_decorator(const Napi::CallbackInfo &info) {
	return info.Env().Undefined();
}

static Napi::Value preload_dlls(const Napi::CallbackInfo &info) {
	Napi::Env env = info.Env();
#ifdef WIN32
	if (info.Length() < 1 || !info[0].IsString()) {
		return env.Undefined();
	}
	std::string dir_utf8 = info[0].As<Napi::String>().Utf8Value();

	auto to_wide = [](const std::string &s) -> std::wstring {
		int n = MultiByteToWideChar(CP_UTF8, 0, s.c_str(), -1, nullptr, 0);
		std::wstring w(n, 0);
		MultiByteToWideChar(CP_UTF8, 0, s.c_str(), -1, &w[0], n);
		return w;
	};

	std::string dirs_to_add = dir_utf8;

	char cuda_buf[4096] = {};
	if (GetEnvironmentVariableA("CUDA_PATH", cuda_buf, sizeof(cuda_buf)) > 0) {
		dirs_to_add += ";" + std::string(cuda_buf) + "\\bin";
	}

	for (const char *varname : { "CUDA_PATH_V12_6", "CUDA_PATH_V12_5", "CUDA_PATH_V12_4",
				 "CUDA_PATH_V12_3", "CUDA_PATH_V12_2", "CUDA_PATH_V12_1", "CUDA_PATH_V12_0",
				 "CUDA_PATH_V11_8", "CUDA_PATH_V11_7" }) {
		char buf[4096] = {};
		if (GetEnvironmentVariableA(varname, buf, sizeof(buf)) > 0) {
			dirs_to_add += ";" + std::string(buf) + "\\bin";
			break;
		}
	}

	char path_buf[32767] = {};
	GetEnvironmentVariableA("PATH", path_buf, sizeof(path_buf));
	std::string new_path = dirs_to_add + ";" + std::string(path_buf);
	SetEnvironmentVariableA("PATH", new_path.c_str());

	SetDllDirectoryW(to_wide(dir_utf8).c_str());

	std::wstring wdir = to_wide(dir_utf8);
	std::wstring pattern = wdir + L"\\*.dll";
	WIN32_FIND_DATAW fd;
	HANDLE h = FindFirstFileW(pattern.c_str(), &fd);
	if (h != INVALID_HANDLE_VALUE) {
		do {
			std::wstring dll_path = wdir + L"\\" + fd.cFileName;
			HMODULE hm = LoadLibraryExW(dll_path.c_str(), nullptr, LOAD_WITH_ALTERED_SEARCH_PATH);
			if (!hm) {
				LoadLibraryExW(dll_path.c_str(), nullptr, 0);
			}
		} while (FindNextFileW(h, &fd));
		FindClose(h);
	}
#endif
	return env.Undefined();
}

void prepare_native_addon_host() {
#ifdef WIN32
	HMODULE current_module = nullptr;
	if (!GetModuleHandleExW(
			GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
			reinterpret_cast<LPCWSTR>(&prepare_native_addon_host),
			&current_module)) {
		return;
	}
	std::wstring node_dll_path = get_module_file_name(current_module);
	if (node_dll_path.empty()) {
		return;
	}
	size_t sep = node_dll_path.find_last_of(L"\\/");
	if (sep == std::wstring::npos) {
		return;
	}
	node_dll_path.resize(sep + 1);
	node_dll_path += L"node.dll";
	LoadLibraryW(node_dll_path.c_str());
#elif defined(__APPLE__) || defined(__linux__)
	promote_current_module_symbols(reinterpret_cast<void *>(&prepare_native_addon_host));
#endif
}

void install_exports(Napi::Env env, Napi::Object exports) {
	exports.Set("fs_readFile", Napi::Function::New(env, fs_readFile));
	exports.Set("fs_stat", Napi::Function::New(env, fs_stat));
	exports.Set("preload_dlls", Napi::Function::New(env, preload_dlls));
}

void install_global_decorators(Napi::Env env) {
	Napi::Object global = env.Global();
	global.Set("Export", Napi::Function::New(env, noop_decorator));
	global.Set("Signal", Napi::Function::New(env, noop_decorator));
	global.Set("Tool", Napi::Function::New(env, noop_decorator));
}

} // namespace gode::node_runtime_bridge
