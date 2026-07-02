import importlib.util
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
RUNNER_PATH = ROOT / "test" / "run_godot_smoke.py"

spec = importlib.util.spec_from_file_location("run_godot_smoke", RUNNER_PATH)
run_godot_smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run_godot_smoke)


class GodotSmokeRunnerTests(unittest.TestCase):
	def test_leak_lines_are_classified_separately_from_runtime_errors(self):
		output = "\n".join(
			[
				'ERROR: 1 RID allocations of type "Viewport" were leaked at exit.',
				"WARNING: 17 ObjectDB instances were leaked at exit.",
				"Leaked instance: Javascript:123 - Reference count: 1",
				"ERROR: Script failed before running the test.",
			]
		)

		self.assertEqual(3, len(run_godot_smoke.leak_lines(output)))
		self.assertEqual(["ERROR: Script failed before running the test."], run_godot_smoke.non_leak_error_lines(output))

	def test_timeout_output_is_normalized_from_bytes(self):
		self.assertEqual(
			"Godot Engine\nSCRIPT ERROR: Parse Error\n",
			run_godot_smoke.captured_output_text(b"Godot Engine\nSCRIPT ERROR: Parse Error\n"),
		)


if __name__ == "__main__":
	unittest.main()
