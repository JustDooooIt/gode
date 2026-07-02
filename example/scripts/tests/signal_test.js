import { Node, Vector3 } from "godot";

function assert(condition, message) {
	if (!condition) {
		throw new Error(message);
	}
}

export default class SignalTest extends Node {
	static signals = {
		completed: [{ name: "payload", type: "Object" }],
		test_finished: [
			{ name: "success", type: "bool" },
			{ name: "message", type: "String" },
		],
	};

	static exports = {
		threshold: { type: "int" },
		spawn_offset: { type: "Vector3" },
	};

	threshold = 3;
	spawn_offset = new Vector3(1, 2, 3);

	run_test() {
		void this.run();
	}

	async run() {
		try {
			assert(this.has_signal("completed"), "static signal metadata was not registered");
			assert(this.threshold === 3, "exported scalar default was not applied");
			assert(this.spawn_offset.x === 1 && this.spawn_offset.y === 2 && this.spawn_offset.z === 3, "exported Vector3 default was not applied");

			const received = [];
			this.connect("completed", payload => {
				received.push(payload);
			});

			setTimeout(() => {
				this.emit_signal("completed", { ok: true, count: received.length + 1 });
			}, 0);

			const payload = await this.to_signal("completed", { timeoutMs: 1000 });
			assert(payload.ok === true, "signal payload did not cross the Godot/JavaScript boundary");
			assert(received.length === 1, "signal callback did not run exactly once");

			console.log("[GodeTest] signal_test passed");
			this.emit_signal("test_finished", true, "");
		} catch (error) {
			const message = error && error.stack ? error.stack : String(error);
			console.error("[GodeTest] signal_test failed", message);
			this.emit_signal("test_finished", false, message);
		}
	}
}
