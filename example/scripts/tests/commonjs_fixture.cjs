module.exports = {
	kind: "commonjs-runtime-fixture",
	makeCommonPayload(seed) {
		return {
			seed,
			values: [seed, seed + 1, seed + 2],
			total: seed * 3 + 3,
		};
	},
};
