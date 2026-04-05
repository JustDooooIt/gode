import { Control } from "godot";
import { getLlama, LlamaChatSession } from "node-llama-cpp";

export default class Demo extends Control {
	async _ready(): Promise<void> {
		GD.print("Demo ready");
		const llama = await getLlama("lastBuild");
		const model = await llama.loadModel({
			modelPath: "D:\\qwen2.5-3b-instruct-q2_k.gguf",
		});
		const context = await model.createContext();
		const session = new LlamaChatSession({
			contextSequence: context.getSequence(),
		});

		const response = await session.prompt("你好，请介绍一下你自己");
		GD.print("AI:", response);

		await llama.dispose();
	}
}
