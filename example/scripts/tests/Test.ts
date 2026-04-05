import { Control } from 'godot';
import { ExternalStats, ExternalConfig } from './types';

interface Stats {
	health: number;
	speed: number;
}

interface MyiInterface {
	a: number;
	b: string;
	stats: Stats;
}

class BaseNode extends Control {
	@Export
	base_v: string = "base_hello";

	@Export
	base_i: MyiInterface = {
		a: 10,
		b: "base_world",
		stats: { health: 50, speed: 2 }
	};
}

export default class Test extends BaseNode {
	@Export
	v: string = "hello";

	@Export
	i: MyiInterface = {
		a: 1,
		b: "world",
		stats: { health: 100, speed: 5 }
	};

	@Export
	ext: ExternalStats = {
		damage: 30,
		defense: 10,
	};

	@Export
	cfg: ExternalConfig = {
		name: "boss",
		level: 5,
		stats: { damage: 50, defense: 20 },
	};

	private pass = 0;
	private fail = 0;

	private assert(name: string, actual: any, expected: any): void {
		if (actual === expected) {
			GD.print(`  [PASS] ${name}`);
			this.pass++;
		} else {
			GD.print(`  [FAIL] ${name}: expected ${expected}, got ${actual}`);
			this.fail++;
		}
	}

	_ready(): void {
		GD.print("=== Test: @Export 基础属性 ===");
		this.assert("v 初始值", this.v, "hello");

		GD.print("=== Test: @Export interface 展开 ===");
		this.assert("i::a 初始值", this.i.a, 1);
		this.assert("i::b 初始值", this.i.b, "world");

		GD.print("=== Test: @Export 嵌套 interface (subgroup) ===");
		this.assert("i::stats::health 初始值", this.i.stats.health, 100);
		this.assert("i::stats::speed 初始值", this.i.stats.speed, 5);

		GD.print("=== Test: 写入属性后读取 ===");
		this.v = "updated";
		this.assert("v 写入后", this.v, "updated");

		this.i = { ...this.i, a: 42 };
		this.assert("i::a 写入后", this.i.a, 42);

		this.i = { ...this.i, stats: { ...this.i.stats, health: 200 } };
		this.assert("i::stats::health 写入后", this.i.stats.health, 200);

		GD.print("=== Test: 外部 import interface @Export ===");
		this.assert("ext::damage 初始值", this.ext.damage, 30);
		this.assert("ext::defense 初始值", this.ext.defense, 10);

		GD.print("=== Test: 外部 import 嵌套 interface @Export ===");
		this.assert("cfg::name 初始值", this.cfg.name, "boss");
		this.assert("cfg::level 初始值", this.cfg.level, 5);
		this.assert("cfg::stats::damage 初始值", this.cfg.stats.damage, 50);
		this.assert("cfg::stats::defense 初始值", this.cfg.stats.defense, 20);

		GD.print("=== Test: 外部 import interface 写入后读取 ===");
		this.ext = { ...this.ext, damage: 99 };
		this.assert("ext::damage 写入后", this.ext.damage, 99);

		this.cfg = { ...this.cfg, stats: { ...this.cfg.stats, defense: 77 } };
		this.assert("cfg::stats::defense 写入后", this.cfg.stats.defense, 77);

		GD.print("=== Test: 父类 @Export 基础属性 ===");
		this.assert("base_v 初始值", this.base_v, "base_hello");

		GD.print("=== Test: 父类 @Export interface 展开 ===");
		this.assert("base_i::a 初始值", this.base_i.a, 10);
		this.assert("base_i::b 初始值", this.base_i.b, "base_world");

		GD.print("=== Test: 父类 @Export 嵌套 interface (subgroup) ===");
		this.assert("base_i::stats::health 初始值", this.base_i.stats.health, 50);
		this.assert("base_i::stats::speed 初始值", this.base_i.stats.speed, 2);

		GD.print("=== Test: 写入父类属性后读取 ===");
		this.base_v = "base_updated";
		this.assert("base_v 写入后", this.base_v, "base_updated");

		this.base_i = { ...this.base_i, a: 99 };
		this.assert("base_i::a 写入后", this.base_i.a, 99);

		this.base_i = { ...this.base_i, stats: { ...this.base_i.stats, health: 999 } };
		this.assert("base_i::stats::health 写入后", this.base_i.stats.health, 999);

		GD.print(`=== 结果: ${this.pass} passed, ${this.fail} failed ===`);
	}
}
