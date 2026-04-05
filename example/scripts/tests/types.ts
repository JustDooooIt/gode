export interface ExternalStats {
	damage: number;
	defense: number;
}

export interface ExternalConfig {
	name: string;
	level: number;
	stats: ExternalStats;
}
