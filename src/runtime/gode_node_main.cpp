#ifdef _WIN32
#include <windows.h>

#include <string>
#include <vector>

extern "C" __declspec(dllimport) int gode_node_probe_main(int p_argc, char **p_argv);

static std::string wide_to_utf8(const wchar_t *p_value) {
	if (p_value == nullptr) {
		return {};
	}
	int size = WideCharToMultiByte(CP_UTF8, 0, p_value, -1, nullptr, 0, nullptr, nullptr);
	if (size <= 0) {
		return {};
	}
	std::string out(static_cast<size_t>(size - 1), '\0');
	WideCharToMultiByte(CP_UTF8, 0, p_value, -1, out.data(), size, nullptr, nullptr);
	return out;
}

int wmain(int p_argc, wchar_t **p_argv) {
	std::vector<std::string> utf8_args;
	utf8_args.reserve(static_cast<size_t>(p_argc));
	std::vector<char *> argv;
	argv.reserve(static_cast<size_t>(p_argc) + 1);
	for (int i = 0; i < p_argc; i++) {
		utf8_args.push_back(wide_to_utf8(p_argv[i]));
		argv.push_back(utf8_args.back().data());
	}
	argv.push_back(nullptr);
	return gode_node_probe_main(p_argc, argv.data());
}
#else
extern "C" int gode_node_probe_main(int p_argc, char **p_argv);

int main(int p_argc, char **p_argv) {
	return gode_node_probe_main(p_argc, p_argv);
}
#endif
