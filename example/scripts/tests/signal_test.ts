import { Node } from "godot";

export default class SignalTest extends Node {
	no_args_signal!: Signal<() => void>;
	one_arg_signal!: Signal<(value: number) => void>;
	multi_arg_signal!: Signal<(name: string, count: number) => void>;

	private pass = 0;
	private fail = 0;

	private assert(label: string, actual: any, expected: any): void {
		if (actual === expected) {
			GD.print(`  [PASS] ${label}`);
			this.pass++;
		} else {
			GD.print(`  [FAIL] ${label}: expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`);
			this.fail++;
		}
	}

	private assert_true(label: string, value: boolean): void {
		this.assert(label, value, true);
	}

	async _ready(): Promise<void> {
		GD.print("=== Test: Signal<T>注册 ===");
		this.assert_true("no_args_signal 已注册", this.has_user_signal("no_args_signal"));
		this.assert_true("one_arg_signal 已注册", this.has_user_signal("one_arg_signal"));
		this.assert_true("multi_arg_signal 已注册", this.has_user_signal("multi_arg_signal"));
		this.assert_true("未声明信号不存在", !this.has_user_signal("nonexistent_signal"));

		GD.print("=== Test: Signal<T>连接与发射（无参） ===");
		let no_args_received = false;
		this.connect("no_args_signal", () => {
			no_args_received = true;
		});
		this.emit_signal("no_args_signal");
		this.assert_true("no_args_signal 回调触发", no_args_received);

		GD.print("=== Test: Signal<T>连接与发射（单参） ===");
		let received_value = -1;
		this.connect("one_arg_signal", (v: number) => {
			received_value = v;
		});
		this.emit_signal("one_arg_signal", 42);
		this.assert("one_arg_signal 参数传递", received_value, 42);

		GD.print("=== Test: Signal<T>多参数 ===");
		let received_name = "";
		let received_count = -1;
		this.connect("multi_arg_signal", (n: string, c: number) => {
			received_name = n;
			received_count = c;
		});
		this.emit_signal("multi_arg_signal", "hero", 3);
		this.assert("multi_arg_signal name 参数", received_name, "hero");
		this.assert("multi_arg_signal count 参数", received_count, 3);

		GD.print("=== Test: Signal<T>多次发射 ===");
		let call_count = 0;
		this.connect("one_arg_signal", (_v: number) => {
			call_count++;
		});
		this.emit_signal("one_arg_signal", 1);
		this.emit_signal("one_arg_signal", 2);
		this.assert("多次发射累计次数", call_count, 2);

		GD.print("=== Test: Signal<T>参数更新 ===");
		let last_val = 0;
		this.connect("one_arg_signal", (v: number) => {
			last_val = v;
		});
		this.emit_signal("one_arg_signal", 99);
		this.assert("最后一次发射的参数", last_val, 99);

		GD.print("=== Test: Signal<T> 异步等待（to_signal） ===");
		// 先建立等待，再通过 setTimeout 延迟发射，确保 emit 发生在 await yield 之后
		setTimeout(() => this.emit_signal("no_args_signal"), 0);
		await this.to_signal("no_args_signal");
		this.assert_true("to_signal 无参信号 resolve", true);

		setTimeout(() => this.emit_signal("one_arg_signal", 123), 0);
		const one_arg_result = await this.to_signal("one_arg_signal");
		this.assert("to_signal 单参返回值", one_arg_result, 123);

		setTimeout(() => this.emit_signal("multi_arg_signal", "world", 9), 0);
		const multi_result = await this.to_signal("multi_arg_signal");
		this.assert_true("to_signal 多参返回数组", Array.isArray(multi_result));
		this.assert("to_signal 多参 name", (multi_result as any[])[0], "world");
		this.assert("to_signal 多参 count", (multi_result as any[])[1], 9);

		GD.print(`=== 结果: ${this.pass} passed, ${this.fail} failed ===`);
	}
}
