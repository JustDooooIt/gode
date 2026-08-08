if (process.send) {
	process.send({
		type: "gode-fork-probe",
		execPath: process.execPath,
		version: process.version,
	});
}
