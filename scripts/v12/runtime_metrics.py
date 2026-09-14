#!/usr/bin/env python3
from __future__ import annotations

import math
import os
import statistics
import threading
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable


PROC = Path("/proc")
CLK_TCK = os.sysconf(os.sysconf_names["SC_CLK_TCK"])


def _read_meminfo() -> dict[str, int]:
    out: dict[str, int] = {}

    for line in Path("/proc/meminfo").read_text().splitlines():
        if ":" not in line:
            continue

        key, value = line.split(":", 1)
        parts = value.strip().split()

        if not parts:
            continue

        try:
            n = int(parts[0])
        except ValueError:
            continue

        # /proc/meminfo values are normally kB.
        if len(parts) > 1 and parts[1].lower() == "kb":
            n *= 1024

        out[key] = n

    return out


def system_memory_snapshot() -> dict[str, int | float]:
    m = _read_meminfo()

    total = m.get("MemTotal", 0)
    available = m.get("MemAvailable", 0)
    swap_total = m.get("SwapTotal", 0)
    swap_free = m.get("SwapFree", 0)

    ram_used = max(0, total - available)
    swap_used = max(0, swap_total - swap_free)

    gib = 1024 ** 3

    return {
        "ram_total_bytes": total,
        "ram_available_bytes": available,
        "ram_used_bytes": ram_used,
        "swap_total_bytes": swap_total,
        "swap_free_bytes": swap_free,
        "swap_used_bytes": swap_used,
        "ram_used_gib": round(ram_used / gib, 6),
        "swap_used_gib": round(swap_used / gib, 6),
    }


def process_rss_bytes(pid: int) -> int | None:
    status = PROC / str(pid) / "status"

    try:
        text = status.read_text()
    except (FileNotFoundError, PermissionError, ProcessLookupError):
        return None

    for line in text.splitlines():
        if line.startswith("VmRSS:"):
            parts = line.split()

            if len(parts) >= 2:
                return int(parts[1]) * 1024

    return None


def process_cpu_seconds(pid: int) -> float | None:
    stat = PROC / str(pid) / "stat"

    try:
        text = stat.read_text()
    except (FileNotFoundError, PermissionError, ProcessLookupError):
        return None

    # comm may contain spaces and parentheses, so split after final ')'.
    end = text.rfind(")")

    if end < 0:
        return None

    fields = text[end + 2:].split()

    # After removing pid + comm:
    # field 14 utime => index 11
    # field 15 stime => index 12
    try:
        utime = int(fields[11])
        stime = int(fields[12])
    except (IndexError, ValueError):
        return None

    return (utime + stime) / CLK_TCK


def child_pids(pid: int) -> list[int]:
    children_file = PROC / str(pid) / "task" / str(pid) / "children"

    try:
        text = children_file.read_text().strip()
    except (FileNotFoundError, PermissionError, ProcessLookupError):
        return []

    if not text:
        return []

    result = []

    for item in text.split():
        try:
            result.append(int(item))
        except ValueError:
            pass

    return result


def process_tree_pids(root_pid: int) -> list[int]:
    seen: set[int] = set()
    stack = [root_pid]

    while stack:
        pid = stack.pop()

        if pid in seen:
            continue

        seen.add(pid)
        stack.extend(child_pids(pid))

    return sorted(seen)


def process_tree_rss_bytes(root_pid: int) -> int:
    total = 0

    for pid in process_tree_pids(root_pid):
        rss = process_rss_bytes(pid)

        if rss is not None:
            total += rss

    return total


def process_tree_cpu_seconds(root_pid: int) -> float:
    total = 0.0

    for pid in process_tree_pids(root_pid):
        cpu = process_cpu_seconds(pid)

        if cpu is not None:
            total += cpu

    return total


@dataclass
class Sample:
    t_s: float
    process_rss_bytes: int
    system_ram_used_bytes: int
    swap_used_bytes: int


class ResourceSampler:
    """
    Sample process-tree RSS + system RAM + swap while a benchmark runs.

    CPU utilization is calculated from /proc CPU-time deltas across the
    sampling interval. Linux reports 100% as one fully busy logical CPU.
    """

    def __init__(self, pid: int, interval_s: float = 0.10):
        self.pid = pid
        self.interval_s = interval_s

        self.samples: list[Sample] = []

        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

        self.started_perf: float | None = None
        self.finished_perf: float | None = None

        self.cpu_start_s: float | None = None
        self.cpu_end_s: float | None = None

    def start(self) -> None:
        if self._thread is not None:
            raise RuntimeError("sampler already started")

        self.started_perf = time.perf_counter()
        self.cpu_start_s = process_tree_cpu_seconds(self.pid)

        self._thread = threading.Thread(
            target=self._run,
            name=f"resource-sampler-{self.pid}",
            daemon=True,
        )
        self._thread.start()

    def _run(self) -> None:
        assert self.started_perf is not None

        while not self._stop.is_set():
            now = time.perf_counter()
            mem = system_memory_snapshot()

            self.samples.append(
                Sample(
                    t_s=now - self.started_perf,
                    process_rss_bytes=process_tree_rss_bytes(self.pid),
                    system_ram_used_bytes=int(mem["ram_used_bytes"]),
                    swap_used_bytes=int(mem["swap_used_bytes"]),
                )
            )

            self._stop.wait(self.interval_s)

    def stop(self) -> dict:
        if self._thread is None:
            raise RuntimeError("sampler was not started")

        self._stop.set()
        self._thread.join(timeout=max(1.0, self.interval_s * 5))

        self.finished_perf = time.perf_counter()
        self.cpu_end_s = process_tree_cpu_seconds(self.pid)

        return self.summary()

    def summary(self) -> dict:
        if self.started_perf is None:
            raise RuntimeError("sampler has no start time")

        end = self.finished_perf or time.perf_counter()
        wall_s = max(0.0, end - self.started_perf)

        rss = [x.process_rss_bytes for x in self.samples]
        ram = [x.system_ram_used_bytes for x in self.samples]
        swap = [x.swap_used_bytes for x in self.samples]

        cpu_total_s = None
        cpu_percent = None

        if self.cpu_start_s is not None and self.cpu_end_s is not None:
            cpu_total_s = max(0.0, self.cpu_end_s - self.cpu_start_s)

            if wall_s > 0:
                cpu_percent = 100.0 * cpu_total_s / wall_s

        gib = 1024 ** 3

        return {
            "sample_interval_s": self.interval_s,
            "sample_count": len(self.samples),
            "wall_seconds": round(wall_s, 6),

            "peak_process_rss_bytes": max(rss, default=0),
            "peak_process_rss_gib": round(max(rss, default=0) / gib, 6),

            "peak_system_ram_used_bytes": max(ram, default=0),
            "peak_system_ram_used_gib": round(max(ram, default=0) / gib, 6),

            "system_ram_used_start_bytes": ram[0] if ram else None,
            "system_ram_used_end_bytes": ram[-1] if ram else None,

            "swap_used_start_bytes": swap[0] if swap else None,
            "swap_used_end_bytes": swap[-1] if swap else None,
            "peak_swap_used_bytes": max(swap, default=0),
            "peak_swap_used_gib": round(max(swap, default=0) / gib, 6),

            "cpu_total_seconds": (
                round(cpu_total_s, 6)
                if cpu_total_s is not None else None
            ),
            "avg_cpu_percent": (
                round(cpu_percent, 3)
                if cpu_percent is not None else None
            ),
        }

    def samples_as_dicts(self) -> list[dict]:
        return [asdict(x) for x in self.samples]


def median(values: Iterable[float]) -> float | None:
    vals = list(values)

    if not vals:
        return None

    return float(statistics.median(vals))


def mean(values: Iterable[float]) -> float | None:
    vals = list(values)

    if not vals:
        return None

    return float(statistics.mean(vals))


def sample_stddev(values: Iterable[float]) -> float | None:
    vals = list(values)

    if len(vals) < 2:
        return 0.0 if vals else None

    return float(statistics.stdev(vals))


def coefficient_of_variation(values: Iterable[float]) -> float | None:
    vals = list(values)

    if len(vals) < 2:
        return 0.0 if vals else None

    avg = statistics.mean(vals)

    if math.isclose(avg, 0.0):
        return 0.0

    return float(statistics.stdev(vals) / avg * 100.0)


def summarize_repeats(values: Iterable[float]) -> dict:
    vals = [float(v) for v in values]

    if not vals:
        return {
            "n": 0,
            "median": None,
            "mean": None,
            "min": None,
            "max": None,
            "stddev": None,
            "cv_percent": None,
        }

    return {
        "n": len(vals),
        "median": round(float(statistics.median(vals)), 6),
        "mean": round(float(statistics.mean(vals)), 6),
        "min": round(min(vals), 6),
        "max": round(max(vals), 6),
        "stddev": round(float(statistics.stdev(vals)), 6)
            if len(vals) >= 2 else 0.0,
        "cv_percent": round(coefficient_of_variation(vals) or 0.0, 4),
    }


def self_test() -> None:
    print("v1.2 runtime metrics self-test")
    print()

    mem = system_memory_snapshot()

    print(f"PID: {os.getpid()}")
    print(f"RAM used:  {mem['ram_used_gib']:.3f} GiB")
    print(f"Swap used: {mem['swap_used_gib']:.3f} GiB")

    sampler = ResourceSampler(os.getpid(), interval_s=0.05)
    sampler.start()

    # Small deterministic CPU + memory workload.
    blob = bytearray(16 * 1024 * 1024)

    total = 0
    end = time.perf_counter() + 0.75

    while time.perf_counter() < end:
        for i in range(5000):
            total += i * i

    blob[0] = total & 0xFF

    summary = sampler.stop()

    print()
    print("Sampler:")
    print(f"  samples:          {summary['sample_count']}")
    print(f"  wall:             {summary['wall_seconds']:.3f} s")
    print(f"  peak process RSS: {summary['peak_process_rss_gib']:.3f} GiB")
    print(f"  peak system RAM:  {summary['peak_system_ram_used_gib']:.3f} GiB")
    print(f"  peak swap:        {summary['peak_swap_used_gib']:.3f} GiB")
    print(f"  avg CPU:          {summary['avg_cpu_percent']:.1f}%")

    stats = summarize_repeats([10.0, 11.0, 9.0])

    print()
    print("Repeat-stat test:")
    print(f"  median: {stats['median']}")
    print(f"  mean:   {stats['mean']}")
    print(f"  stddev: {stats['stddev']}")
    print(f"  CV:     {stats['cv_percent']}%")

    assert summary["sample_count"] >= 2
    assert summary["peak_process_rss_bytes"] > 0
    assert summary["peak_system_ram_used_bytes"] > 0
    assert stats["median"] == 10.0

    print()
    print("SELF-TEST: PASS")


if __name__ == "__main__":
    self_test()
