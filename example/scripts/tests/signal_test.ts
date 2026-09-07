import { GDDictionary, Node, Signal, type VariantArgument, Vector3 } from "godot";

function verifyTypedSignalDeclarations(signal: Signal<(message: string, count: number) => void>): void {
	signal.connect((message, count) => void `${message}:${count}`);
	signal.disconnect((message, count) => void `${message}:${count}`);
	signal.is_connected((message, count) => void `${message}:${count}`);
	signal.emit("ready", 1);
	// @ts-expect-error Typed signals reject arguments in the wrong order.
	signal.emit(1, "ready");
	// @ts-expect-error Typed signals reject callbacks with incompatible parameters.
	signal.connect((message: number) => void message);
}

void verifyTypedSignalDeclarations;

function verifyGeneratedGodotSignalDeclarations(node: Node): void {
	node.ready.connect(() => undefined);
	node.ready.emit();
	node.child_entered_tree.connect(child => void child.get_name());
	// @ts-expect-error Node.ready has no signal arguments.
	node.ready.emit("unexpected");
	// @ts-expect-error child_entered_tree provides a Node, not a string.
	node.child_entered_tree.connect((child: string) => void child);
}

void verifyGeneratedGodotSignalDeclarations;

function assert(condition: boolean, message: string): void {
	if (!condition) {
		throw new Error(message);
	}
}

function dictionaryValue(container: VariantArgument, key: string): VariantArgument {
	if (container instanceof GDDictionary) {
		for (const candidate of container.keys()) {
			if (String(candidate) === key) {
				return container.get(candidate);
			}
		}
		return undefined;
	}
	if (container instanceof Map) {
		for (const [candidate, value] of container) {
			if (String(candidate) === key) {
				return value;
			}
		}
		return undefined;
	}
	if (container !== null && typeof container === "object") {
		return (container as Record<string, VariantArgument>)[key];
	}
	return undefined;
}

export default class SignalTest extends Node {
	static constructor_owner_id: number | bigint = 0;

	typed_completed!: Signal<(message: string, count: number) => void>;

	static signals = {
		completed: [{ name: "payload", type: "Object" }],
		test_finished: [
			{ name: "success", type: "bool" },
			{ name: "message", type: "String" },
		],
	} as const;

	static exports = {
		"threshold": { "type": "int", "hint": 1, "hint_string": "0,10,1", "default": 3 as const },
		"spawn_offset": { "type": "Vector3" },
	} satisfies ExportMap;

	static rpc_config = {
		run_test: { rpc_mode: "authority", transfer_mode: "reliable", call_local: true, channel: 0 },
	} satisfies RpcConfig;

	threshold = 3 as const;
	spawn_offset = new Vector3(1, 2, 3) as Vector3;

	constructor() {
		// Deliberately do not forward Gode's internal owner argument. ScriptInstance
		// must still bind this wrapper to the Godot object that owns the script.
		super();
		SignalTest.constructor_owner_id = this.get_instance_id();
	}

	run_test() {
		void this.run();
	}

	async run() {
		try {
			assert(SignalTest.constructor_owner_id === this.get_instance_id(), "explicit super() created a second Godot object");
			assert(this.has_signal("completed"), "static signal metadata was not registered");
			assert(this.has_signal("typed_completed"), "Signal<T> field annotation was not registered");
			let typedSignalPayload = "";
			this.typed_completed.connect((message, count) => {
				typedSignalPayload = `${message}:${count}`;
			});
			this.typed_completed.emit("ready", 2);
			assert(typedSignalPayload === "ready:2", "Signal<T> field was not bound to the runtime Godot signal");
			assert(this.threshold === 3, "exported scalar default was not applied");
			assert(this.spawn_offset.x === 1 && this.spawn_offset.y === 2 && this.spawn_offset.z === 3, "exported Vector3 default was not applied");
			const propertyList = this.get_property_list() as Array<{ name: VariantArgument; hint?: VariantArgument; hint_string?: VariantArgument }>;
			const thresholdProperty = propertyList.find(property => String(property.name) === "threshold");
			if (!thresholdProperty) {
				throw new Error("threshold export metadata missing from property list");
			}
			assert(Number(thresholdProperty.hint) === 1, "static exports hint was not preserved");
			assert(String(thresholdProperty.hint_string) === "0,10,1", "static exports hint string was not preserved");

			const script = this.get_script() as { get_rpc_config(): VariantArgument };
			const rpcMetadata = dictionaryValue(script.get_rpc_config(), "run_test");
			assert(rpcMetadata !== undefined, "rpc_config metadata was not registered");
			assert(Number(dictionaryValue(rpcMetadata, "rpc_mode")) === 2, "rpc_config rpc_mode was not preserved");
			assert(Number(dictionaryValue(rpcMetadata, "transfer_mode")) === 2, "rpc_config transfer_mode was not preserved");
			assert(Boolean(dictionaryValue(rpcMetadata, "call_local")) === true, "rpc_config call_local was not preserved");
			assert(Number(dictionaryValue(rpcMetadata, "channel")) === 0, "rpc_config channel was not preserved");

			const received: VariantArgument[] = [];
			this.connect("completed", (payload: VariantArgument) => {
				received.push(payload);
			});

			setTimeout(() => {
				this.emit_signal("completed", { ok: true, count: received.length + 1 });
			}, 0);

			const payload = await this.to_signal("completed", { timeoutMs: 1000 }) as { ok?: boolean };
			assert(payload.ok === true, "signal payload did not cross the Godot/TypeScript boundary");
			assert(received.length === 1, "signal callback did not run exactly once");

			console.log("[GodeTest] signal_test passed");
			this.emit_signal("test_finished", true, "");
		} catch (error) {
			const message = error instanceof Error ? (error.stack ?? error.message) : String(error);
			console.error("[GodeTest] signal_test failed", message);
			this.emit_signal("test_finished", false, message);
		}
	}
}
