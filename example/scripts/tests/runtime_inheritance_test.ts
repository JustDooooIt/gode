import nodeAssert from "node:assert/strict";
import { ClassDB, GodotObject, PropertyHint, Resource, type VariantArgument } from "godot";
import * as InheritanceBaseModule from "./runtime_inheritance_external_base.js";

interface InheritedRow {
	label: string;
	count: number;
}

interface DerivedRow {
	label: string;
	count: number;
	tag: string;
}

interface InheritedSettings {
	label: string;
	count: number;
}

function Observe(_target: object, _property: string): void {}
function ExportIgnored(_target: object, _property: string): void {}

function computedDefault(value: number): number {
	return value;
}

abstract class RuntimeInheritanceAbstractRoot extends InheritanceBaseModule.RuntimeInheritanceExternalBase {
	@Export()
	abstract_root_value: number = 20;
}

class RuntimeInheritanceGrandparent extends RuntimeInheritanceAbstractRoot {
	@Export({ hint: PropertyHint.PROPERTY_HINT_RANGE, hint_string: "0,100,1" })
	overridden_count: number = 11;

	@Export()
	initializer_override: number = 12;

	@Export()
	leaf_override: number = 13;

	@Export()
	opaque_count: number = 14;
}

export abstract class RuntimeInheritanceParent extends RuntimeInheritanceGrandparent {
	static exports: ExportMap = {
		inherited_static: { type: "int", hint: 1, hint_string: "0,20,1", default: 7 },
		inherited_static_initializer: { type: "int" },
	};

	inherited_static: number = 7;
	inherited_static_initializer: number = 9;

	@Export({ hint: PropertyHint.PROPERTY_HINT_RANGE, hint_string: "0,50,1" })
	override overridden_count: number = 23;

	override initializer_override: number = 24;
	override opaque_count: number = computedDefault(44);

	@Export()
	override leaf_override: number = 25;

	@Observe
	@Export(PropertyHint.PROPERTY_HINT_RANGE, "0,10,0.5")
	inherited_range: number = 5;

	@Export({ hint: PropertyHint.PROPERTY_HINT_RESOURCE_TYPE, hint_string: "Resource" })
	inherited_resource: Resource | null = null;

	@Export()
	inherited_rows: InheritedRow[] = [];

	@Export()
	overridden_rows: InheritedRow[] = [];

	@Export()
	inherited_settings: InheritedSettings = { label: "parent", count: 6 };

	@ExportIgnored
	inherited_not_exported: number = 5;
}

export default class RuntimeInheritanceTest extends RuntimeInheritanceParent {
	static signals = {
		test_finished: [
			{ name: "success", type: "bool" },
			{ name: "message", type: "String" },
		],
	} as const;

	static exports: ExportMap = {
		direct_static: { type: "int", default: 3 },
		inherited_count: { type: "float", hint: 1, hint_string: "0,100,1" },
		inherited_static: { type: "int", hint: 1, hint_string: "0,30,1" },
		inherited_rows: { type: "Array", hint: 31, hint_string: "24/17:TypeScriptInterfaceResource" },
		external_rows: { type: "Array", hint: 31, hint_string: "24/17:TypeScriptInterfaceResource" },
		explicit_default: { type: "float", default: 99 },
	};

	direct_static: number = 3;
	explicit_default: number = computedDefault(27);
	override leaf_override: number = 37;
	override external_dynamic: number = computedDefault(38);
	override inherited_settings: InheritedSettings = { label: "leaf", count: 8 };

	@Export()
	override overridden_rows: DerivedRow[] = [];

	@ExportIgnored
	direct_not_exported: number = 6;

	run_test(): void {
		try {
			const properties = this.get_property_list() as Array<{
				name: VariantArgument;
				type: VariantArgument;
				hint: VariantArgument;
				hint_string: VariantArgument;
				usage: VariantArgument;
			}>;
			const property = (name: string) => {
				const matches = properties.filter(entry => String(entry.name) === name);
				nodeAssert.equal(matches.length, 1, `${name} must be exported exactly once`);
				return matches[0];
			};
			const assertHint = (name: string, hint: number | bigint, hintString: string) => {
				const metadata = property(name);
				nodeAssert.equal(Number(metadata.hint), Number(hint), `${name} hint`);
				nodeAssert.equal(String(metadata.hint_string), hintString, `${name} hint string`);
			};
			assertHint("inherited_range", PropertyHint.PROPERTY_HINT_RANGE, "0,10,0.5");
			assertHint("overridden_count", PropertyHint.PROPERTY_HINT_RANGE, "0,50,1");
			assertHint("inherited_static", PropertyHint.PROPERTY_HINT_RANGE, "0,30,1");
			assertHint("inherited_count", PropertyHint.PROPERTY_HINT_RANGE, "0,100,1");
			assertHint("inherited_label", 20, "base label");
			assertHint("inherited_resource", PropertyHint.PROPERTY_HINT_RESOURCE_TYPE, "Resource");
			nodeAssert.equal(Number(property("inherited_resource").type), 24);
			assertHint("inherited_rows", PropertyHint.PROPERTY_HINT_ARRAY_TYPE, "24/17:TypeScriptInterfaceResource");
			assertHint("external_rows", PropertyHint.PROPERTY_HINT_ARRAY_TYPE, "24/17:TypeScriptInterfaceResource");
			assertHint("overridden_rows", PropertyHint.PROPERTY_HINT_ARRAY_TYPE, "24/17:TypeScriptInterfaceResource");
			const propertyNames = properties.map(entry => String(entry.name));
			nodeAssert.ok(!propertyNames.includes("inherited_not_exported"));
			nodeAssert.ok(!propertyNames.includes("direct_not_exported"));
			nodeAssert.ok(propertyNames.indexOf("direct_static") < propertyNames.indexOf("inherited_range"));
			nodeAssert.ok(propertyNames.indexOf("inherited_range") < propertyNames.indexOf("external_count"));

			for (const [name, expected] of Object.entries({
				overridden_count: 23,
				initializer_override: 24,
				leaf_override: 37,
				inherited_range: 5,
				inherited_static: 7,
				inherited_static_initializer: 9,
				direct_static: 3,
				inherited_count: 11,
				external_count: 19,
				abstract_root_value: 20,
			})) {
				property(name);
				nodeAssert.equal(this.get(name), expected, `${name} actual value`);
				nodeAssert.equal(this.property_can_revert(name), true, `${name} can revert`);
				nodeAssert.equal(this.property_get_revert(name), expected, `${name} default`);
			}
			nodeAssert.equal(this.property_get_revert("inherited_resource"), null);
			nodeAssert.deepEqual(this.property_get_revert("inherited_rows"), []);
			nodeAssert.deepEqual(this.property_get_revert("external_rows"), []);
			nodeAssert.deepEqual(this.property_get_revert("overridden_rows"), []);
			for (const [name, actual] of [["opaque_count", 44], ["external_dynamic", 38]] as const) {
				property(name);
				nodeAssert.equal(this.get(name), actual);
				nodeAssert.equal(this.property_can_revert(name), false, `${name} must not use an ancestor's stale default`);
			}
			nodeAssert.equal(this.get("explicit_default"), 27);
			nodeAssert.equal(this.property_get_revert("explicit_default"), 99);
			property("inherited_settings::label");
			property("inherited_settings::count");
			nodeAssert.equal(this.get("inherited_settings::label"), "leaf");
			nodeAssert.equal(this.property_get_revert("inherited_settings::label"), "leaf");
			nodeAssert.equal(this.property_get_revert("inherited_settings::count"), 8);
			property("external_settings::nested::count");
			nodeAssert.equal(this.property_get_revert("external_settings::nested::count"), 4);
			for (const [name, prefix, usage] of [
				["InheritedSettings", "inherited_settings::", 64],
				["ExternalSettings", "external_settings::", 64],
				["ExternalNestedSettings", "external_settings::nested::", 256],
			] as const) {
				const group = property(name);
				nodeAssert.equal(Number(group.usage), usage);
				nodeAssert.equal(String(group.hint_string), prefix);
			}

			for (const [name, fieldName] of [["inherited_rows", "label"], ["external_rows", "title"], ["overridden_rows", "tag"]] as const) {
				const row = ClassDB.instantiate("TypeScriptInterfaceResource") as GodotObject;
				this.set(name, [row]);
				const fields = row.get_property_list() as Array<{ name: VariantArgument }>;
				nodeAssert.ok(fields.some(field => String(field.name) === fieldName), `${name} schema missing`);
				row.set(fieldName, "inherited");
				nodeAssert.equal(row.get(fieldName), "inherited");
				this.set(name, []);
			}
			this.emit_signal("test_finished", true, "runtime inheritance test passed");
		} catch (error) {
			const message = error instanceof Error ? error.stack ?? error.message : String(error);
			this.emit_signal("test_finished", false, message);
		}
	}
}
