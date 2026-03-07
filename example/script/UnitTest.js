const godot = require('godot');

class UnitTest extends godot.Node {
	_ready() {
		GD.print("=======================================");
		GD.print("   Starting Gode Unit Tests");
		GD.print("=======================================");

		this.run_tests();
	}

	async run_tests() {
		try {
			this.test_vector2();
			this.test_node_creation();
			this.test_signals_with_callable();
			this.test_callable_constructor();
			
			GD.print("\n---------------------------------------");
			GD.print("✅ ALL TESTS PASSED");
			GD.print("---------------------------------------");
		} catch (e) {
			GD.printerr("\n---------------------------------------");
			GD.printerr("❌ TEST FAILED");
			GD.printerr(e.message);
			GD.printerr(e.stack);
			GD.printerr("---------------------------------------");
		}
	}

	assert(condition, message) {
		if (!condition) {
			throw new Error("Assertion failed: " + message);
		}
		GD.print(`[PASS] ${message}`);
	}

	test_vector2() {
		GD.print("\n[Testing Vector2]");
		let v1 = new Vector2(1, 2);
		let v2 = new Vector2(3, 4);
		
		this.assert(v1.x === 1 && v1.y === 2, "Vector2 constructor sets x and y");
		this.assert(Math.abs(v1.length() - 2.23606) < 0.0001, "Vector2.length() works");
	}

	test_node_creation() {
		GD.print("\n[Testing Node Creation]");
		let node = new godot.Node();
		node.name = "TestNode";
		this.assert(node.name === "TestNode", "Node name property works");
		
		this.add_child(node);
		this.assert(node.get_parent() === this, "add_child works");
		
		node.queue_free();
		// We can't easily check if it's freed immediately as queue_free is deferred.
	}

	test_signals_with_callable() {
		GD.print("\n[Testing Signals with JS Callable]");
		let node = new godot.Node();
		let called = false;
		
		// Add to tree to ensure proper signal propagation if needed (though renamed usually doesn't need it)
		this.add_child(node);

		// Test connecting a JS arrow function to a signal
		node.connect("renamed", () => {
			called = true;
			GD.print("  -> Signal callback executed!");
		});
		
		node.name = "NewName";
		this.assert(called, "JS Arrow function connected to signal was called");
		
		// Test Signal Object
		GD.print("  -> Testing signal object property...");
		let signal = node.renamed;
		this.assert(signal instanceof Signal, "Signal property returns Signal object");
		this.assert(signal.get_name() === "renamed", "Signal name is correct");
		
		// Cleanup
		this.remove_child(node);
		node.queue_free();
	}

	test_callable_constructor() {
		GD.print("\n[Testing Callable Constructor]");
		// Test the new feature: creating a Callable from a JS function
		let js_func = () => { return "Hello from JS"; };
		let callable = new Callable(js_func);
		
		this.assert(callable.is_valid(), "Callable created from JS function is valid");
		this.assert(callable.is_custom(), "Callable from JS function is custom");
		
		let result = callable.call();
		this.assert(result === "Hello from JS", "Callable.call() returns correct JS value");
	}
}

module.exports = { default: UnitTest };
