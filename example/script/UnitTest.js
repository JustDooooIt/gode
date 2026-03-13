const godot = require("godot");

class UnitTest extends godot.Node {
  // Test exported properties on UnitTest itself
  static exports = {
	export_float: { type: "float", default: 3.14 },
	export_int: { type: "int", default: 42 },
	export_string: { type: "String", default: "hello" },
	export_bool: { type: "bool", default: true },
	export_no_default: { type: "int" },
  };

  export_float = 3.14;
  export_int = 42;
  export_string = "hello";
  export_bool = true;
  export_no_default = 0;

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
	  await this.test_to_signal();
	  this.test_callable_constructor();
	  this.test_exports();

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
	this.assert(
	  Math.abs(v1.length() - 2.23606) < 0.0001,
	  "Vector2.length() works",
	);

	// Operator tests
	let v3 = v1.add(v2);
	this.assert(v3.x === 4.0 && v3.y === 6.0, "Vector2.add works");

	let v4 = v2.subtract(v1);
	this.assert(v4.x === 2.0 && v4.y === 2.0, "Vector2.subtract works");

	let v5 = v1.multiply(2);
	this.assert(
	  v5.x === 2.0 && v5.y === 4.0,
	  "Vector2.multiply (scalar) works",
	);

	let v6 = v1.multiply(v2);
	this.assert(
	  v6.x === 3.0 && v6.y === 8.0,
	  "Vector2.multiply (vector) works",
	);

	this.assert(v1.equal(new Vector2(1, 2)), "Vector2.equal works");
	this.assert(v1.not_equal(v2), "Vector2.not_equal works");
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
	this.assert(
	  signal instanceof Signal,
	  "Signal property returns Signal object",
	);
	this.assert(signal.get_name() === "renamed", "Signal name is correct");

	// Cleanup
	this.remove_child(node);
	node.queue_free();
  }

  async test_to_signal() {
	GD.print("\n[Testing toSignal]");
	let node = new godot.Node();
	this.add_child(node);

	// We need to schedule the emit/change AFTER we await
	// But await blocks. So we use setTimeout to trigger it later.
	setTimeout(() => {
	  GD.print("  -> Triggering rename async...");
	  node.name = "NewNameAsync";
	}, 100);

	await node.toSignal("renamed");
	GD.print("  -> toSignal resolved!");
	this.assert(node.name === "NewNameAsync", "toSignal awaited correctly");

	// Cleanup
	this.remove_child(node);
	node.queue_free();
  }

  test_callable_constructor() {
	GD.print("\n[Testing Callable Constructor]");
	// Test the new feature: creating a Callable from a JS function
	let js_func = () => {
	  return "Hello from JS";
	};
	let callable = new Callable(js_func);

	this.assert(
	  callable.is_valid(),
	  "Callable created from JS function is valid",
	);
	this.assert(callable.is_custom(), "Callable from JS function is custom");

	let result = callable.call();
	this.assert(
	  result === "Hello from JS",
	  "Callable.call() returns correct JS value",
	);
  }

  test_exports() {
	GD.print("\n[Testing static exports / @export]");

	// 1. static exports object is defined and has correct structure
	const exp = UnitTest.exports;
	this.assert(
	  typeof exp === "object" && exp !== null,
	  "static exports is an object",
	);
	this.assert("export_float" in exp, "export_float is declared in exports");
	this.assert("export_int" in exp, "export_int is declared in exports");
	this.assert("export_string" in exp, "export_string is declared in exports");
	this.assert("export_bool" in exp, "export_bool is declared in exports");

	// 2. type metadata is preserved
	this.assert(
	  exp.export_float.type === "float",
	  "export_float type is 'float'",
	);
	this.assert(exp.export_int.type === "int", "export_int type is 'int'");
	this.assert(
	  exp.export_string.type === "String",
	  "export_string type is 'String'",
	);
	this.assert(exp.export_bool.type === "bool", "export_bool type is 'bool'");

	// 3. default values are declared correctly
	this.assert(
	  exp.export_float.default === 3.14,
	  "export_float default is 3.14",
	);
	this.assert(exp.export_int.default === 42, "export_int default is 42");
	this.assert(
	  exp.export_string.default === "hello",
	  "export_string default is 'hello'",
	);
	this.assert(
	  exp.export_bool.default === true,
	  "export_bool default is true",
	);
	this.assert(
	  !("default" in exp.export_no_default),
	  "export_no_default has no default value",
	);

	// 4. instance fields have the correct initial values (matching declared defaults)
	this.assert(
	  Math.abs(this.export_float - 3.14) < 0.0001,
	  "instance export_float starts at 3.14",
	);
	this.assert(this.export_int === 42, "instance export_int starts at 42");
	this.assert(
	  this.export_string === "hello",
	  "instance export_string starts at 'hello'",
	);
	this.assert(
	  this.export_bool === true,
	  "instance export_bool starts at true",
	);

	// 5. exported properties can be mutated and read back
	this.export_float = 2.71;
	this.assert(
	  Math.abs(this.export_float - 2.71) < 0.0001,
	  "export_float can be set to 2.71",
	);

	this.export_int = 99;
	this.assert(this.export_int === 99, "export_int can be set to 99");

	this.export_string = "world";
	this.assert(
	  this.export_string === "world",
	  "export_string can be set to 'world'",
	);

	this.export_bool = false;
	this.assert(this.export_bool === false, "export_bool can be set to false");

	// Restore originals so this node stays predictable
	this.export_float = 3.14;
	this.export_int = 42;
	this.export_string = "hello";
	this.export_bool = true;
  }
}

module.exports = { default: UnitTest };
