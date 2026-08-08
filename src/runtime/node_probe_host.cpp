#include <godot_cpp/core/defs.hpp>
#include <node.h>

#include "runtime/node_godot_bridge.h"

extern "C" {

int GDE_EXPORT gode_node_probe_main(int p_argc, char **p_argv) {
	gode::node_runtime_bridge::prepare_native_addon_host();
	return node::Start(p_argc, p_argv);
}
}
