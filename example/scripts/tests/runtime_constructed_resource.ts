import { Resource, Vector2 } from "godot";

export default class RuntimeConstructedResource extends Resource {
	static constructions: number = 0;

	@Export()
	label: string = "default";

	@Export()
	position: Vector2 = new Vector2(1, 2);

	@Export()
	children: RuntimeConstructedResource[] = [];

	constructor(label: string = "default") {
		super();
		RuntimeConstructedResource.constructions++;
		this.label = label;
	}
}
