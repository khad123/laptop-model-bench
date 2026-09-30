import importlib.util
import datetime as dt
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "external_benchmark_runner.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("external_benchmark_runner", SCRIPT)
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)
SCORER_SCRIPT = SCRIPT.with_name("evalplus_subset_score.py")
SCORER_SPEC = importlib.util.spec_from_file_location("evalplus_subset_score", SCORER_SCRIPT)
scorer = importlib.util.module_from_spec(SCORER_SPEC)
SCORER_SPEC.loader.exec_module(scorer)
TELEMETRY_SCRIPT = SCRIPT.with_name("benchmark_telemetry.py")
TELEMETRY_SPEC = importlib.util.spec_from_file_location("benchmark_telemetry", TELEMETRY_SCRIPT)
telemetry = importlib.util.module_from_spec(TELEMETRY_SPEC)
TELEMETRY_SPEC.loader.exec_module(telemetry)


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
    def test_evalplus_metrics_capture_token_counts_and_llama_cpp_rates(self):
        metrics = telemetry.completion_metrics(
            "HumanEval/7",
            3.5,
            {"prompt_tokens": 120, "completion_tokens": 60, "total_tokens": 180},
            {
                "prompt_n": 120,
                "cache_n": 0,
                "prompt_per_second": 80.0,
                "predicted_n": 60,
                "predicted_per_second": 20.0,
            },
        )
        self.assertEqual(metrics["prompt_tokens"], 120)
        self.assertEqual(metrics["completion_tokens"], 60)
        self.assertEqual(metrics["total_tokens"], 180)
        self.assertEqual(metrics["prompt_tokens_per_second"], 80.0)
        self.assertEqual(metrics["generation_tokens_per_second"], 20.0)
        self.assertEqual(metrics["context_tokens"], 180)

    def test_estimated_remaining_time_uses_recorded_task_durations(self):
        self.assertEqual(telemetry.estimate_remaining_seconds([10.0, 20.0], 3), 45.0)
        self.assertEqual(telemetry.estimate_remaining_seconds([], 3), None)

    def test_task_progress_shows_measured_rates_and_marks_missing_eta(self):
        line = telemetry.progress_line(
            "HumanEval/7", 8, 164, 12.5,
            {"prompt_tokens": 120, "completion_tokens": 60,
             "prompt_tokens_per_second": 80.0, "generation_tokens_per_second": 20.0},
            None,
        )
        self.assertIn("[8/164] HumanEval/7: done in 12s", line)
        self.assertIn("120 prompt / 60 output tokens", line)
        self.assertIn("generation 20.0 tok/s", line)
        self.assertIn("ETA unknown", line)

    def test_duration_display_is_compact_and_human_readable(self):
        self.assertEqual(telemetry.format_duration(3661), "1h 1m")
        self.assertEqual(telemetry.format_duration(42), "42s")

    def test_evalplus_summary_counts_failures_and_averages_measured_rates(self):
        summary = telemetry.summarize_task_metrics(
            [
                {"task_id": "HumanEval/0", "prompt_tokens": 80, "completion_tokens": 20,
                 "prompt_tokens_per_second": 40.0, "generation_tokens_per_second": 10.0,
                 "context_tokens": 100,
                 "request_elapsed_seconds": 3.0},
                {"task_id": "HumanEval/1", "prompt_tokens": 100, "completion_tokens": 30,
                 "prompt_tokens_per_second": 60.0, "generation_tokens_per_second": 20.0,
                 "context_tokens": 125,
                 "request_elapsed_seconds": 2.0},
            ],
            [{"task_id": "HumanEval/2"}],
            3,
        )
        self.assertEqual(summary["tasks_generated"], 2)
        self.assertEqual(summary["tasks_failed_or_skipped"], 1)
        self.assertEqual(summary["prompt_tokens_total"], 180)
        self.assertEqual(summary["output_tokens_total"], 50)
        self.assertEqual(summary["max_context_tokens_used"], 125)
        self.assertEqual(summary["generation_tokens_per_second_average"], 15.0)
        self.assertEqual(summary["request_elapsed_seconds_total"], 5.0)
        self.assertEqual(summary["failed_task_ids"], ["HumanEval/2"])

    def test_peak_rss_reads_linux_process_high_water_mark(self):
        with tempfile.TemporaryDirectory() as temp:
            status = Path(temp) / "123" / "status"
            status.parent.mkdir()
            status.write_text("Name:\tllama-server\nVmHWM:\t9876 kB\n")
            self.assertEqual(runner.process_peak_rss_kib(123, Path(temp)), 9876)

    def test_run_timing_accumulates_active_time_separately_from_resume_pause(self):
        metadata = {
            "started_at": "2026-09-30T02:00:00+00:00",
            "active_elapsed_seconds": 3600.0,
            "sessions": [{"started_at": "2026-09-30T04:50:00+00:00", "finished_at": None}],
        }
        finished_at = dt.datetime.fromisoformat("2026-09-30T05:00:00+00:00")
        result = telemetry.finalize_run_timing(metadata, 600.0, finished_at)
        self.assertEqual(result["active_elapsed_seconds"], 4200.0)
        self.assertEqual(result["total_elapsed_seconds"], 10800.0)
        self.assertEqual(result["sessions"][0]["elapsed_seconds"], 600.0)

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

    def test_tool_result_keeps_elapsed_time_and_start_timestamp(self):
        with tempfile.TemporaryDirectory() as temp:
            marker = Path(temp) / "status.json"
            runner.write_result(
                marker, "completed", "", "2026-09-30T10:00:00+00:00", 12.75,
            )
            result = json.loads(marker.read_text())
            self.assertEqual(result["elapsed_seconds"], 12.75)
            self.assertEqual(result["started_at"], "2026-09-30T10:00:00+00:00")

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
            scorer=Path("/tmp/evalplus_subset_score.py"),
            alias="model-id",
            uid=1000,
            gid=1000,
            image="evalplus:test",
        )
        self.assertIn("--network=none", command)
        self.assertIn("XDG_CACHE_HOME=/tmp/.cache", command)
        self.assertIn("/tmp:rw,noexec,nosuid,size=256m", command)
        self.assertIn("HUMANEVAL_OVERRIDE_PATH=/bench-data/HumanEvalPlus.jsonl", command)
        self.assertIn(
            "/tmp/evalplus_subset_score.py:/bench-scripts/evalplus_subset_score.py:ro",
            command,
        )
        self.assertIn("/bench-scripts/evalplus_subset_score.py", command)
        self.assertNotIn("evalplus.evaluate", command)
        self.assertIn(
            f"{dataset.resolve()}:/bench-data/HumanEvalPlus.jsonl:ro", command
        )

    def test_evalplus_reuses_only_a_complete_one_sample_per_task_file(self):
        with tempfile.TemporaryDirectory() as temp:
            samples = Path(temp) / "samples.jsonl"
            task_ids = ["HumanEval/0", "HumanEval/18"]
            samples.write_text(
                "".join(
                    json.dumps({"task_id": task_id, "solution": "def f(): pass"}) + "\n"
                    for task_id in task_ids
                )
            )
            self.assertTrue(runner.evalplus_samples_complete(samples, task_ids))

            samples.write_text(
                json.dumps({"task_id": task_ids[0], "solution": "def f(): pass"}) + "\n"
            )
            self.assertFalse(runner.evalplus_samples_complete(samples, task_ids))

    def test_evalplus_subset_scorer_accepts_only_present_known_tasks(self):
        with tempfile.TemporaryDirectory() as temp:
            samples = Path(temp) / "samples.jsonl"
            samples.write_text(
                json.dumps({"task_id": "HumanEval/18", "solution": "def f(): return 1"})
                + "\n"
            )
            loaded = scorer.load_subset_samples(samples, {"HumanEval/0", "HumanEval/18"})
            self.assertEqual([item["task_id"] for item in loaded], ["HumanEval/18"])

            samples.write_text(
                json.dumps({"task_id": "HumanEval/18", "solution": "def f(): return 1"})
                + "\n"
                + json.dumps({"task_id": "HumanEval/18", "solution": "def f(): return 2"})
                + "\n"
            )
            with self.assertRaisesRegex(ValueError, "Duplicate sample"):
                scorer.load_subset_samples(samples, {"HumanEval/18"})

            samples.write_text(
                json.dumps({"task_id": "HumanEval/999", "solution": "def f(): pass"})
                + "\n"
            )
            with self.assertRaisesRegex(ValueError, "Unknown HumanEval task ID"):
                scorer.load_subset_samples(samples, {"HumanEval/0", "HumanEval/18"})

    def test_evalplus_generation_timeout_kills_child_and_restarts_server(self):
        with tempfile.TemporaryDirectory() as temp:
            log = Path(temp) / "task.log"
            restarts = []
            code, timed_out, output, elapsed = runner.run_command_with_timeout(
                [sys.executable, "-c", "import time; print('request started', flush=True); time.sleep(5)"],
                log,
                timeout_seconds=0.1,
                on_timeout=lambda: restarts.append("restarted"),
            )
            self.assertEqual(code, 124)
            self.assertTrue(timed_out)
            self.assertGreaterEqual(elapsed, 0.1)
            self.assertIn("request started", output)
            self.assertEqual(restarts, ["restarted"])
            self.assertIn("request started", log.read_text())

    def test_evalplus_worker_command_is_scoped_to_one_task_and_has_a_request_timeout(self):
        command = runner.evalplus_worker_command(
            "HumanEval/56", "model-id", "http://127.0.0.1:8080/v1",
            Path("/tmp/samples.jsonl"), Path("/tmp/raw.jsonl"),
            Path("/tmp/metrics.jsonl"), 290,
        )
        self.assertIn("--task-id", command)
        self.assertIn("HumanEval/56", command)
        self.assertIn("--request-timeout", command)
        self.assertIn("290", command)
        self.assertIn("--metrics", command)
        self.assertIn("/tmp/metrics.jsonl", command)

    def test_empty_evalplus_chat_content_is_not_accepted_as_a_generated_sample(self):
        self.assertTrue(runner.evalplus_solution_is_usable("def f(): return 1"))
        self.assertFalse(runner.evalplus_solution_is_usable(""))
        self.assertFalse(runner.evalplus_solution_is_usable(" \n\t "))

    def test_llama_server_uses_reasoning_off_for_consistent_evalplus_answers(self):
        command = runner.llama_server_command(
            Path("/model.gguf"), "model-id", 12345, 4096, 4,
        )
        self.assertIn("--reasoning", command)
        self.assertEqual(command[command.index("--reasoning") + 1], "off")

    def test_evalplus_partial_samples_can_be_resumed_without_redoing_saved_ids(self):
        with tempfile.TemporaryDirectory() as temp:
            samples = Path(temp) / "samples.jsonl"
            samples.write_text(json.dumps({"task_id": "HumanEval/55", "solution": "ok"}) + "\n")
            self.assertEqual(
                runner.evalplus_saved_task_ids(samples, ["HumanEval/55", "HumanEval/56"]),
                {"HumanEval/55"},
            )

    def test_evalplus_skipped_task_is_saved_as_failed_sample_and_failure_record(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            samples = root / "samples.jsonl"
            raw = root / "samples.raw.jsonl"
            failures = root / "generation_failures.jsonl"
            runner.record_evalplus_skipped_task(
                task_id="HumanEval/56",
                sample_file=samples,
                raw_sample_file=raw,
                failure_file=failures,
                reason="generation timed out",
                timeout_seconds=300,
                elapsed_seconds=300.0,
            )
            self.assertEqual(
                runner.evalplus_saved_task_ids(samples, ["HumanEval/56"]),
                {"HumanEval/56"},
            )
            self.assertEqual(json.loads(samples.read_text()) ["solution"], "")
            self.assertEqual(json.loads(raw.read_text()) ["solution"], "")
            failure = json.loads(failures.read_text())
            self.assertEqual(failure["task_id"], "HumanEval/56")
            self.assertEqual(failure["timeout_seconds"], 300)
            self.assertEqual(failure["elapsed_seconds"], 300.0)


if __name__ == "__main__":
    unittest.main()
