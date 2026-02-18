#ifndef HELLO_WORLD_H
#define HELLO_WORLD_H

#include <godot_cpp/classes/node.hpp>
#include <napi.h>

namespace godot {

class HelloWorld : public Node {
    GDCLASS(HelloWorld, Node)

protected:
    static void _bind_methods();

public:
    HelloWorld();
    ~HelloWorld();

    void _process(double delta) override;
    
    // Example method exposed to Godot
    void test_node_api();
};

}

#endif
