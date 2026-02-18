#include "hello_world.h"
#include <godot_cpp/core/class_db.hpp>
#include <godot_cpp/variant/utility_functions.hpp>

using namespace godot;

void HelloWorld::_bind_methods() {
    ClassDB::bind_method(D_METHOD("test_node_api"), &HelloWorld::test_node_api);
}

HelloWorld::HelloWorld() {
    // Initialize
}

HelloWorld::~HelloWorld() {
    // Cleanup
}

void HelloWorld::_process(double delta) {
    // Process logic
}

void HelloWorld::test_node_api() {
    UtilityFunctions::print("Hello from Godot! Node API (header only) compiled successfully.");
    // To actually use Node.js features, we would need to initialize the Node.js runtime here.
    // For now, we just demonstrate that headers are included and linked.
}
