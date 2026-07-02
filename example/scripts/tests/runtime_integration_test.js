import nodeAssert from "node:assert/strict";
import path from "node:path";
import v8 from "node:v8";
import vm from "node:vm";
import { Color, Engine, GD, GDArray, GDString, GodotObject, Image, ImageTexture, Node, PackedInt32Array, PackedStringArray, PackedVector3Array, ResourceLoader, Vector2i, Vector3 } from "godot";
import cjsFixture, { makeCommonPayload } from "./commonjs_fixture.cjs";
import { buildRuntimePayload, moduleMarker, waitForEventLoopTurn } from "./runtime_helpers";

v8.setFlagsFromString("--expose-gc");
const forceGarbageCollection = vm.runInNewContext("gc");

function assert(condition, message) {
	if (!condition) {
		throw new Error(message);
	}
}

function assertApprox(actual, expected, epsilon, message) {
	assert(Math.abs(actual - expected) <= epsilon, `${message}: expected ${expected}, got ${actual}`);
}

export default class RuntimeIntegrationTest extends Node {
	static signals = {
		test_finished: [
			{ name: "success", type: "bool" },
			{ name: "message", type: "String" },
		],
	};

	static exports = {
		label: { type: "String" },
		enabled: { type: "bool" },
		count: { type: "int" },
		spawn_offset: { type: "Vector3" },
	};

	label = "runtime";
	enabled = true;
	count = 7;
	spawn_offset = new Vector3(4, 5, 6);

	run_test() {
		void this.run();
	}

	async run() {
		try {
			nodeAssert.equal(moduleMarker, "esm-runtime-helper");
			nodeAssert.equal(path.posix.basename("res://scripts/tests/runtime_integration_test.js"), "runtime_integration_test.js");

			const esmPayload = buildRuntimePayload("alpha");
			nodeAssert.deepEqual(esmPayload.values, [1, 2, 3]);
			nodeAssert.equal(esmPayload.nested.ok, true);

			const okColor = Color.from_ok_hsl(0.58, 0.5, 0.79, 0.8);
			assert(okColor instanceof Color, "Color.from_ok_hsl did not return a Color");
			assertApprox(okColor.a, 0.8, 0.0001, "Color.from_ok_hsl alpha was not preserved");
			assert(okColor.ok_hsl_h >= 0 && okColor.ok_hsl_h <= 1, "ok_hsl_h getter is out of range");
			assert(okColor.ok_hsl_s >= 0 && okColor.ok_hsl_s <= 1, "ok_hsl_s getter is out of range");
			assert(okColor.ok_hsl_l >= 0 && okColor.ok_hsl_l <= 1, "ok_hsl_l getter is out of range");
			okColor.ok_hsl_l = 0;
			assertApprox(okColor.r, 0, 0.0001, "ok_hsl_l setter did not produce black red channel");
			assertApprox(okColor.g, 0, 0.0001, "ok_hsl_l setter did not produce black green channel");
			assertApprox(okColor.b, 0, 0.0001, "ok_hsl_l setter did not produce black blue channel");

			nodeAssert.equal(cjsFixture.kind, "commonjs-runtime-fixture");
			nodeAssert.deepEqual(makeCommonPayload(3).values, [3, 4, 5]);
			nodeAssert.equal(makeCommonPayload(3).total, 12);

			assert(this.property_can_revert("label"), "exported string property cannot revert");
			assert(this.property_can_revert("spawn_offset"), "exported Vector3 property cannot revert");
			nodeAssert.equal(this.property_get_revert("label"), "runtime");
			const offset = this.property_get_revert("spawn_offset");
			assert(offset.x === 4 && offset.y === 5 && offset.z === 6, "Vector3 revert value was not preserved");

			this.label = "changed";
			this.enabled = false;
			this.count = 9;
			nodeAssert.equal(this.label, "changed");
			nodeAssert.equal(this.enabled, false);
			nodeAssert.equal(this.count, 9);

			const propertyNames = this.get_property_list().map(property => String(property.name));
			for (const name of ["label", "enabled", "count", "spawn_offset"]) {
				assert(propertyNames.includes(name), `exported property missing from property list: ${name}`);
			}

			assert(GD.is_instance_valid(this), "GD.is_instance_valid did not accept a live Godot object");
			assert(!GD.is_instance_valid(null), "GD.is_instance_valid should reject null");
			assert(GD.is_instance_valid(Engine), "Engine singleton was not wrapped as a Godot object");
			const multiplayer = this.get_multiplayer();
			assert(GD.is_instance_valid(multiplayer), "Node.get_multiplayer did not return a live Godot object");
			nodeAssert.equal(typeof multiplayer.get_unique_id(), "number");
			for (let i = 0; i < 5000; i++) {
				nodeAssert.equal(typeof this.get_multiplayer().get_unique_id(), "number");
				if (i % 100 === 0) {
					forceGarbageCollection();
					await waitForEventLoopTurn();
				}
			}
			const printErrors = Engine.is_printing_error_messages();
			Engine.set_print_error_messages(false);
			try {
				nodeAssert.throws(
					() => this.emit_signal(),
					/Godot vararg MethodBind call failed: TOO_FEW_ARGUMENTS/,
					"invalid class vararg MethodBind calls should surface as JavaScript exceptions",
				);
			} finally {
				Engine.set_print_error_messages(printErrors);
			}
			assert(typeof GodotObject === "function", "GodotObject constructor was not exported");
			assert(this instanceof GodotObject, "Node script instance does not inherit from GodotObject");
			assert(!Object.prototype.hasOwnProperty.call(globalThis, "Engine"), "Engine should not be injected into globalThis");
			assert(!Object.prototype.hasOwnProperty.call(globalThis, "Vector3"), "Vector3 should not be injected into globalThis");
			assert(Engine.get_version_info().major >= 4, "Engine singleton did not return version info");
			const threadedPath = "res://scenes/signal_test.tscn";
			ResourceLoader.load_threaded_request(threadedPath);
			const threadedProgress = [];
			const threadedStatus = ResourceLoader.load_threaded_get_status(threadedPath, threadedProgress);
			assert(
				threadedStatus === ResourceLoader.THREAD_LOAD_IN_PROGRESS || threadedStatus === ResourceLoader.THREAD_LOAD_LOADED,
				`unexpected threaded load status: ${threadedStatus}`,
			);
			nodeAssert.equal(typeof threadedProgress[0], "number");
			assert(!Number.isNaN(threadedProgress[0]), "threaded load progress out Array was not synchronized");
			assert(ResourceLoader.load_threaded_get(threadedPath) !== null, "threaded resource did not finish loading");
			nodeAssert.equal(this.tr("gode_runtime_translation_probe"), "gode_runtime_translation_probe");
			nodeAssert.throws(() => this.set_process(), /Godot API call expected exactly 1 argument, got 0/);
			nodeAssert.throws(() => this.set_process(true, false), /Godot API call expected exactly 1 argument, got 2/);
			const wasProcessing = this.is_processing();
			nodeAssert.throws(() => this.set_process("true"), TypeError);
			nodeAssert.equal(this.is_processing(), wasProcessing);
			nodeAssert.throws(() => this.tr(), /Godot API call expected at least 1 argument, got 0/);
			nodeAssert.throws(() => this.tr(1), TypeError);
			nodeAssert.throws(() => this.tr("message", "context", "extra"), /Godot API call expected at most 2 arguments, got 3/);
			nodeAssert.throws(() => this.has_node(1), TypeError);
			nodeAssert.throws(() => this.add_child({}), TypeError);

			const image = Image.create_empty(2, 2, false, Image.FORMAT_RGBA8);
			assert(image instanceof Image, "Image.create_empty did not return an Image");
			assert(image.get_reference_count() >= 1, "Returned Image wrapper did not hold a RefCounted reference");
			nodeAssert.equal(image.get_width(), 2);
			nodeAssert.equal(image.get_height(), 2);
			const texture = ImageTexture.create_from_image(image);
			assert(texture instanceof ImageTexture, "ImageTexture.create_from_image did not return an ImageTexture");
			assert(texture.get_reference_count() >= 1, "Returned ImageTexture wrapper did not hold a RefCounted reference");
			nodeAssert.equal(texture.get_image().get_width(), 2);
			nodeAssert.throws(() => ImageTexture.create_from_image({}), TypeError);
			nodeAssert.throws(() => Color.from_ok_hsl("0.58", 0.5, 0.79), TypeError);
			nodeAssert.throws(() => Color.from_ok_hsl(NaN, 0.5, 0.79), TypeError);
			const infiniteVector = new Vector3(Infinity, 0, 0);
			nodeAssert.equal(infiniteVector.x, Infinity);

			nodeAssert.equal(GD.typeof(7), 2);
			nodeAssert.equal(GD.typeof(7.5), 3);
			nodeAssert.equal(GD.typeof(Number.MAX_SAFE_INTEGER), 2);
			nodeAssert.equal(GD.typeof(Number.MAX_SAFE_INTEGER + 1), 3);
			nodeAssert.equal(GD.typeof(7n), 2);
			nodeAssert.equal(GD.var_to_str(9223372036854775807n), "9223372036854775807");
			nodeAssert.throws(() => GD.typeof(9223372036854775808n), RangeError);
			this.set_process_priority(5);
			nodeAssert.equal(this.get_process_priority(), 5);
			nodeAssert.throws(() => this.set_process_priority(9223372036854775808n), RangeError);
			nodeAssert.equal(this.get_process_priority(), 5);
			const vector2i = new Vector2i(1, 2);
			const defaultVector2i = new Vector2i();
			nodeAssert.equal(defaultVector2i.x, 0);
			nodeAssert.equal(defaultVector2i.y, 0);
			nodeAssert.throws(() => new Vector2i(1), /No matching constructor overload for Vector2i/);
			nodeAssert.throws(() => new Vector2i("x", 2), /No matching constructor overload for Vector2i/);
			nodeAssert.throws(() => new Vector2i(1, 2, 3), /No matching constructor overload for Vector2i/);
			nodeAssert.throws(() => vector2i.add(new Vector2i(3, 4), new Vector2i(5, 6)), /Godot API call expected exactly 1 argument, got 2/);
			nodeAssert.throws(() => vector2i.negate(1), /Godot API call expected exactly 0 arguments, got 1/);
			const vector2iFromBigInt = new Vector2i(1n, 2n);
			nodeAssert.equal(vector2iFromBigInt.x, 1);
			nodeAssert.equal(vector2iFromBigInt.y, 2);
			const doubledVector2i = vector2i.multiply(2n);
			nodeAssert.equal(doubledVector2i.x, 2);
			nodeAssert.equal(doubledVector2i.y, 4);
			nodeAssert.throws(() => vector2i.multiply(9223372036854775808n), RangeError);
			nodeAssert.throws(() => new Vector2i(Number.MAX_SAFE_INTEGER + 1, 2), TypeError);
			const vector3 = new Vector3(1, 2, 3);
			nodeAssert.throws(() => {
				vector3.x = "4";
			}, TypeError);
			nodeAssert.equal(vector3.x, 1);
			nodeAssert.throws(() => {
				vector2i.x = 9223372036854775808n;
			}, RangeError);
			nodeAssert.equal(vector2i.x, 1);

			const gdArray = new GDArray([1, "two", true]);
			nodeAssert.equal(gdArray.size(), 3);
			nodeAssert.equal(gdArray.get(1), "two");
			nodeAssert.throws(() => new GDArray(1), /No matching constructor overload for GDArray/);
			const packedInts = new PackedInt32Array([1, 2, 3]);
			nodeAssert.equal(packedInts.size(), 3);
			nodeAssert.equal(packedInts.get(1), 2);
			packedInts.append_array([4, 5]);
			nodeAssert.equal(packedInts.size(), 5);
			nodeAssert.equal(packedInts.get(4), 5);
			const packedTail = packedInts.slice(1);
			nodeAssert.equal(packedTail.size(), 4);
			nodeAssert.equal(packedTail.get(0), 2);
			nodeAssert.throws(() => packedInts.slice(), /Godot API call expected at least 1 argument, got 0/);
			nodeAssert.throws(() => packedInts.slice(1, 2, 3), /Godot API call expected at most 2 arguments, got 3/);
			nodeAssert.throws(() => packedInts.size(1), /Godot API call expected exactly 0 arguments, got 1/);
			const packedBigInts = new PackedInt32Array([1n, 2n]);
			nodeAssert.equal(packedBigInts.size(), 2);
			nodeAssert.equal(packedBigInts.get(1), 2);
			nodeAssert.throws(() => new PackedInt32Array(1), /No matching constructor overload for PackedInt32Array/);
			nodeAssert.throws(() => new PackedInt32Array([9223372036854775808n]), RangeError);
				const packedStrings = new PackedStringArray(["alpha", new GDString("beta")]);
			nodeAssert.equal(packedStrings.size(), 2);
			nodeAssert.equal(packedStrings.get(1), "beta");
			const packedVectors = new PackedVector3Array([new Vector3(1, 2, 3), new Vector3(4, 5, 6)]);
			nodeAssert.equal(packedVectors.size(), 2);
			nodeAssert.equal(packedVectors.get(1).z, 6);

			const metadataKey = "gode_runtime_payload";
			this.set_meta(metadataKey, {
				payload: esmPayload,
				fromCommonJS: makeCommonPayload(2),
			});
			const restored = this.get_meta(metadataKey);
			nodeAssert.equal(restored.payload.label, "alpha");
			nodeAssert.equal(restored.fromCommonJS.total, 9);
			assert(this.has_meta(metadataKey), "metadata key was not registered");
			this.remove_meta(metadataKey);
			assert(!this.has_meta(metadataKey), "metadata key was not removed");

			const keyedDictionary = new Map([
				[7, "seven"],
				["nested", new Map([[2, "two"]])],
			]);
			nodeAssert.equal(GD.typeof(keyedDictionary), 27);
			const keyedRoundTrip = GD.str_to_var(GD.var_to_str(keyedDictionary));
			assert(keyedRoundTrip instanceof Map, "Dictionary with non-string keys did not round-trip as Map");
			nodeAssert.equal(keyedRoundTrip.get(7), "seven");
			const nestedRoundTrip = keyedRoundTrip.get("nested");
			assert(nestedRoundTrip instanceof Map, "Nested Dictionary with non-string keys did not round-trip as Map");
			nodeAssert.equal(nestedRoundTrip.get(2), "two");

			const objectRoundTrip = GD.str_to_var(GD.var_to_str({ name: "gode", count: 3 }));
			assert(!(objectRoundTrip instanceof Map), "String-key Dictionary should round-trip as a plain object");
			nodeAssert.equal(objectRoundTrip.name, "gode");
			nodeAssert.equal(objectRoundTrip.count, 3);

			nodeAssert.throws(() => new Node({}), TypeError);
			nodeAssert.throws(() => new Node(1), TypeError);
			const child = new Node();
			child.name = "RuntimeChild";
			const beforeCount = this.get_child_count();
			this.add_child(child);
			nodeAssert.equal(this.get_child_count(), beforeCount + 1);
			nodeAssert.equal(child.get_parent().get_instance_id(), this.get_instance_id());
			nodeAssert.equal(this.get_children().some(item => item.name === "RuntimeChild"), true);
			this.remove_child(child);
			child.queue_free();

			const events = [];
			process.nextTick(() => events.push("nextTick"));
			queueMicrotask(() => events.push("microtask"));
			await Promise.resolve();
			await waitForEventLoopTurn();
			assert(events.includes("nextTick"), "process.nextTick did not run");
			assert(events.includes("microtask"), "queueMicrotask did not run");

			this.emit_signal("test_finished", true, "");
		} catch (error) {
			const message = error && error.stack ? error.stack : String(error);
			console.error("[GodeTest] runtime_integration_test failed", message);
			this.emit_signal("test_finished", false, message);
		}
	}
}
