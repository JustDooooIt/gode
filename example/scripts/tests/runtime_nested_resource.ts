import { Resource } from "godot";
import RuntimeArrayResource from "./runtime_array_resource.js";

export default class RuntimeNestedResource extends Resource {
	@Export()
	nested: RuntimeArrayResource | null = null;
}
