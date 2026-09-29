import importlib.util
import os
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "external_benchmark_runner.py"
SPEC = importlib.util.spec_from_file_location("external_benchmark_runner", SCRIPT)
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


class ModelDiscoveryTests(unittest.TestCase):
    def test_discovers_current_ref_models_and_skips_projectors(self):
        with tempfile.TemporaryDirectory() as temp:
            hub = Path(temp)
            repo = hub / "models--acme--toy-GGUF"
            snapshot = repo / "snapshots" / "rev123"
            snapshot.mkdir(parents=True)
            (repo / "refs").mkdir()
            (repo / "refs" / "main").write_text("rev123\n")
            (snapshot / "toy-Q4_K_M.gguf").write_bytes(b"model")
            (snapshot / "mmproj-toy.gguf").write_bytes(b"projector")
            os.environ["HF_HUB_CACHE"] = temp
            try:
                models = runner.find_models()
            finally:
                os.environ.pop("HF_HUB_CACHE", None)
            self.assertEqual([path.name for path in models], ["toy-Q4_K_M.gguf"])


class PlanTests(unittest.TestCase):
    def test_default_plan_contains_all_four_tools_for_each_model(self):
        plan = runner.build_plan([Path("/models/a.gguf"), Path("/models/b.gguf")])
        self.assertEqual(len(plan), 8)
        self.assertEqual({entry["tool"] for entry in plan}, set(runner.TOOL_NAMES))

    def test_result_completion_requires_success_marker(self):
        with tempfile.TemporaryDirectory() as temp:
            result = Path(temp) / "result.json"
            self.assertFalse(runner.result_is_complete(result))
            result.write_text('{"status":"failed"}\n')
            self.assertFalse(runner.result_is_complete(result))
            result.write_text('{"status":"completed"}\n')
            self.assertTrue(runner.result_is_complete(result))

    def test_llm_benchmark_slice_is_repeatable_and_does_not_enable_code_execution(self):
        config = runner.llm_bench_config("http://127.0.0.1:8080")
        self.assertIn("runs_per_task: 1", config)
        self.assertIn("temperature: 0.0", config)
        self.assertNotIn("allow_code_exec", config)
        self.assertEqual(len(runner.LLM_BENCH_TASKS), 6)

    def test_evalplus_sample_is_evenly_spread_across_the_task_set(self):
        indices = runner.evenly_spaced_indices(164, 10)
        self.assertEqual(len(indices), 10)
        self.assertEqual(indices[0], 0)
        self.assertEqual(indices[-1], 163)
        self.assertGreater(indices[1], 10)
        with self.assertRaises(ValueError):
            runner.evenly_spaced_indices(10, 11)

    def test_evalplus_codegen_sets_a_string_instruction_prefix(self):
        code = runner.evalplus_codegen_source()
        self.assertIn("instruction_prefix=''", code)

    def test_evalplus_scoring_mounts_cached_dataset_read_only_offline(self):
        dataset = Path("/tmp/HumanEvalPlus-v0.1.10.jsonl")
        command = runner.evalplus_docker_command(
            samples=Path("/tmp/generated"),
            dataset=dataset,
            alias="model-id",
            uid=1000,
            gid=1000,
            image="evalplus:test",
        )
        self.assertIn("--network=none", command)
        self.assertIn("HUMANEVAL_OVERRIDE_PATH=/bench-data/HumanEvalPlus.jsonl", command)
        self.assertIn(
            f"{dataset.resolve()}:/bench-data/HumanEvalPlus.jsonl:ro", command
        )


if __name__ == "__main__":
    unittest.main()
