let selectedTestId = "godot-signal";

export function setSelectedTestId(id: string): void {
	selectedTestId = id;
}

export function getSelectedTestId(): string {
	return selectedTestId;
}
