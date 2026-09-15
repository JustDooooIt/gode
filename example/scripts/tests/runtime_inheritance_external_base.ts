import RuntimeIntegrationBase from "./runtime_base_test.js";

export interface ExternalRow {
	title: string;
	enabled: boolean;
}

interface ExternalNestedSettings {
	count: number;
}

interface ExternalSettings {
	label: string;
	nested: ExternalNestedSettings;
}

export abstract class RuntimeInheritanceExternalBase extends RuntimeIntegrationBase {
	@Export()
	external_count: number = 19;

	@Export()
	external_dynamic: number = 18;

	@Export()
	external_rows: ExternalRow[] = [];

	@Export()
	external_settings: ExternalSettings = { label: "external", nested: { count: 4 } };
}

export default RuntimeInheritanceExternalBase;
