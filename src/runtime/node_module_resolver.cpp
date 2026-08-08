#include "runtime/node_module_resolver.h"

#include <godot_cpp/classes/file_access.hpp>
#include <godot_cpp/classes/json.hpp>
#include <godot_cpp/variant/dictionary.hpp>
#include <godot_cpp/variant/variant.hpp>

#include <cctype>

namespace gode::node_module_resolver {

static bool is_path_separator(char c) {
	return c == '/' || c == '\\';
}

static std::string parent_directory(const std::string &path) {
	if (path.empty() || path == "/" || path == "res://" || path == "user://") {
		return std::string();
	}

	std::string dir = path;
	while (dir.size() > 1 && is_path_separator(dir.back())) {
		if (dir == "res://" || dir == "user://") {
			return std::string();
		}
		dir.pop_back();
	}

	if (dir.size() == 3 && dir[1] == ':' && is_path_separator(dir[2])) {
		return std::string();
	}

	size_t slash = dir.find_last_of("/\\");
	if (slash == std::string::npos) {
		return std::string();
	}

	if (dir.rfind("res://", 0) == 0) {
		return slash < 6 ? std::string("res://") : dir.substr(0, slash);
	}
	if (dir.rfind("user://", 0) == 0) {
		return slash < 7 ? std::string("user://") : dir.substr(0, slash);
	}
	if (slash == 0) {
		return std::string("/");
	}
	if (slash == 2 && dir[1] == ':') {
		return dir.substr(0, 3);
	}

	return dir.substr(0, slash);
}

static int read_package_module_type(const std::string &filename) {
	std::string dir = filename;
	size_t last_slash = dir.find_last_of("/\\");
	if (last_slash == std::string::npos) {
		return 0;
	}
	dir = dir.substr(0, last_slash);

	while (!dir.empty()) {
		const std::string pkg_path = dir + "/package.json";
		const godot::String gd_pkg_path = godot::String::utf8(pkg_path.c_str());
		if (godot::FileAccess::file_exists(gd_pkg_path)) {
			godot::Ref<godot::FileAccess> file = godot::FileAccess::open(gd_pkg_path, godot::FileAccess::READ);
			if (file.is_valid()) {
				const godot::String content = file->get_as_text();
				const godot::Variant parsed = godot::JSON::parse_string(content);
				if (parsed.get_type() == godot::Variant::Type::DICTIONARY) {
					const godot::Dictionary json = parsed;
					const godot::String type = json.get("type", godot::String());
					if (type == "module") {
						return 1;
					}
					if (type == "commonjs") {
						return -1;
					}
					return 0;
				}
			}
		}

		std::string parent = parent_directory(dir);
		if (parent.empty() || parent == dir) {
			break;
		}
		dir = parent;
	}

	return 0;
}

static bool is_identifier_continue(char c) {
	unsigned char value = static_cast<unsigned char>(c);
	return std::isalnum(value) || c == '_' || c == '$';
}

static std::string sanitize_js_for_module_markers(const std::string &source) {
	enum class State {
		Normal,
		SingleQuote,
		DoubleQuote,
		Template,
		LineComment,
		BlockComment,
	};

	std::string code;
	code.reserve(source.size());
	State state = State::Normal;
	bool escaped = false;

	auto append_masked = [&code](char c) {
		code.push_back(c == '\n' || c == '\r' ? c : ' ');
	};

	for (size_t i = 0; i < source.size(); i++) {
		char c = source[i];
		char next = i + 1 < source.size() ? source[i + 1] : '\0';

		switch (state) {
			case State::Normal:
				if (c == '/' && next == '/') {
					append_masked(c);
					append_masked(next);
					i++;
					state = State::LineComment;
				} else if (c == '/' && next == '*') {
					append_masked(c);
					append_masked(next);
					i++;
					state = State::BlockComment;
				} else if (c == '\'') {
					append_masked(c);
					escaped = false;
					state = State::SingleQuote;
				} else if (c == '"') {
					append_masked(c);
					escaped = false;
					state = State::DoubleQuote;
				} else if (c == '`') {
					append_masked(c);
					escaped = false;
					state = State::Template;
				} else {
					code.push_back(c);
				}
				break;
			case State::SingleQuote:
			case State::DoubleQuote:
			case State::Template: {
				append_masked(c);
				char quote = state == State::SingleQuote ? '\'' : (state == State::DoubleQuote ? '"' : '`');
				if (escaped) {
					escaped = false;
				} else if (c == '\\') {
					escaped = true;
				} else if (c == quote) {
					state = State::Normal;
				} else if ((state == State::SingleQuote || state == State::DoubleQuote) && (c == '\n' || c == '\r')) {
					state = State::Normal;
				}
				break;
			}
			case State::LineComment:
				append_masked(c);
				if (c == '\n' || c == '\r') {
					state = State::Normal;
				}
				break;
			case State::BlockComment:
				append_masked(c);
				if (c == '*' && next == '/') {
					append_masked(next);
					i++;
					state = State::Normal;
				}
				break;
		}
	}

	return code;
}

static bool module_keyword_at(const std::string &code, size_t pos, const char *keyword) {
	size_t length = std::char_traits<char>::length(keyword);
	if (pos + length > code.size() || code.compare(pos, length, keyword) != 0) {
		return false;
	}
	if (pos > 0 && is_identifier_continue(code[pos - 1])) {
		return false;
	}

	char next = pos + length < code.size() ? code[pos + length] : '\0';
	if (std::string(keyword) == "import") {
		return std::isspace(static_cast<unsigned char>(next)) || next == '{' || next == '*' || next == '.';
	}
	return std::isspace(static_cast<unsigned char>(next)) || next == '{' || next == '*';
}

static bool has_static_esm_syntax(const std::string &code) {
	bool line_start = true;
	for (size_t i = 0; i < code.size(); i++) {
		char c = code[i];
		if (line_start) {
			while (i < code.size() && (code[i] == ' ' || code[i] == '\t' || code[i] == '\v' || code[i] == '\f')) {
				i++;
			}
			if (i >= code.size()) {
				return false;
			}
			if (module_keyword_at(code, i, "import") || module_keyword_at(code, i, "export")) {
				return true;
			}
			line_start = false;
			c = code[i];
		}
		if (c == '\n' || c == '\r') {
			line_start = true;
		}
	}
	return false;
}

static bool has_commonjs_markers(const std::string &code) {
	return code.find("module.exports") != std::string::npos ||
			code.find("exports.") != std::string::npos ||
			code.find("exports[") != std::string::npos ||
			code.find("Object.defineProperty(exports") != std::string::npos ||
			code.find("require(") != std::string::npos;
}

bool is_esm_file(const std::string &filename, const std::string &code) {
	if (filename.size() >= 4 && filename.substr(filename.size() - 4) == ".mjs") {
		return true;
	}
	if (filename.size() >= 4 && filename.substr(filename.size() - 4) == ".cjs") {
		return false;
	}

	if (filename.size() >= 3 && filename.substr(filename.size() - 3) == ".js") {
		const int package_type = read_package_module_type(filename);
		if (package_type > 0) {
			return true;
		}
		if (package_type < 0) {
			return false;
		}
	}

	const std::string sanitized_code = sanitize_js_for_module_markers(code);
	if (has_static_esm_syntax(sanitized_code)) {
		return true;
	}

	if (has_commonjs_markers(sanitized_code)) {
		return false;
	}

	return false;
}

} // namespace gode::node_module_resolver
