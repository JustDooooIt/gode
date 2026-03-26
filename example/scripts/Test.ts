import { Control } from "godot";

export default class Test extends Control {
	static exports: ExportMap = {
		_hello: {
			type: "string",
			default: "hahaha"
		},
	};

	_hello: string = "pre";

	_ready(): void {
		GD.print(this._hello);
	} 
}
