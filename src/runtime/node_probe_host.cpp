#include <godot_cpp/core/defs.hpp>
#include <node.h>

extern "C" {

int GDE_EXPORT gode_node_probe_main(int p_argc, char **p_argv) {
	return node::Start(p_argc, p_argv);
}
}
