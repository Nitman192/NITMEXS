"""Local stress harness for NITMEXS LAN delivery flow."""

from __future__ import annotations

import argparse
import asyncio
import random
import statistics
import time
from dataclasses import dataclass

import httpx


@dataclass
class StudentResult:
    success: bool
    duration_ms: float
    errors: int
    conflict_count: int
    finalize_attempts: int
    idempotent_ok: bool


async def run_student(
    client: httpx.AsyncClient,
    exam_id: str,
    student_id: str,
    max_answer_delay_s: float,
    max_finalize_delay_s: float,
    finalize_storm_size: int,
) -> StudentResult:
    start = time.perf_counter()
    errors = 0
    conflicts = 0
    idempotent_ok = True

    try:
        response = await client.post(
            f"/student/exams/{exam_id}/start",
            headers={"x-student-id": student_id},
        )
        response.raise_for_status()
        attempt_payload = response.json()["data"]
        attempt_id = attempt_payload["attempt_id"]

        seq = 1
        while True:
            q = await client.get(
                f"/student/attempts/{attempt_id}/questions/{seq}",
                headers={"x-student-id": student_id},
            )
            if q.status_code == 404:
                break
            q.raise_for_status()
            body = q.json()["data"]
            question_id = body["question"]["id"]
            options = body.get("options", [])
            if not options:
                break
            selected = random.choice(options)["id"]

            await asyncio.sleep(random.uniform(0.0, max_answer_delay_s))
            submit = await client.post(
                f"/student/attempts/{attempt_id}/answers",
                headers={"x-student-id": student_id},
                json={"question_id": question_id, "selected_option_id": selected},
            )
            if submit.status_code >= 400:
                errors += 1
            seq += 1

        await asyncio.sleep(random.uniform(0.0, max_finalize_delay_s))

        async def finalize_once() -> httpx.Response:
            return await client.post(
                f"/student/attempts/{attempt_id}/finalize",
                headers={"x-student-id": student_id},
            )

        finalize_responses = await asyncio.gather(
            *(finalize_once() for _ in range(max(1, finalize_storm_size)))
        )

        baseline_result = None
        for resp in finalize_responses:
            if resp.status_code >= 400:
                detail = ""
                try:
                    detail = resp.json().get("detail", "")
                except Exception:
                    detail = resp.text
                if "Concurrent update detected" in detail:
                    conflicts += 1
                else:
                    errors += 1
                continue

            payload = resp.json().get("data", {}).get("result")
            if baseline_result is None:
                baseline_result = payload
            elif payload != baseline_result:
                idempotent_ok = False

        result_resp = await client.get(
            f"/student/attempts/{attempt_id}/result",
            headers={"x-student-id": student_id},
        )
        if result_resp.status_code >= 400:
            errors += 1

        return StudentResult(
            success=errors == 0,
            duration_ms=(time.perf_counter() - start) * 1000,
            errors=errors,
            conflict_count=conflicts,
            finalize_attempts=max(1, finalize_storm_size),
            idempotent_ok=idempotent_ok,
        )
    except Exception:
        return StudentResult(
            success=False,
            duration_ms=(time.perf_counter() - start) * 1000,
            errors=errors + 1,
            conflict_count=conflicts,
            finalize_attempts=max(1, finalize_storm_size),
            idempotent_ok=False,
        )


async def main() -> None:
    parser = argparse.ArgumentParser(description="NITMEXS local stress harness")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--exam-id", required=True)
    parser.add_argument("--students", type=int, default=20)
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--max-answer-delay", type=float, default=0.5)
    parser.add_argument("--max-finalize-delay", type=float, default=0.3)
    parser.add_argument("--finalize-storm-size", type=int, default=3)
    args = parser.parse_args()

    semaphore = asyncio.Semaphore(args.concurrency)

    async with httpx.AsyncClient(base_url=args.base_url, timeout=30.0) as client:

        async def bounded(i: int) -> StudentResult:
            async with semaphore:
                return await run_student(
                    client=client,
                    exam_id=args.exam_id,
                    student_id=f"stress-student-{i}",
                    max_answer_delay_s=args.max_answer_delay,
                    max_finalize_delay_s=args.max_finalize_delay,
                    finalize_storm_size=args.finalize_storm_size,
                )

        results = await asyncio.gather(*(bounded(i) for i in range(args.students)))

    durations = [r.duration_ms for r in results]
    successes = sum(1 for r in results if r.success)
    total_errors = sum(r.errors for r in results)
    total_conflicts = sum(r.conflict_count for r in results)
    total_finalize_attempts = sum(r.finalize_attempts for r in results)
    idempotent_failures = sum(1 for r in results if not r.idempotent_ok)
    conflict_rate = (
        (total_conflicts / total_finalize_attempts) * 100
        if total_finalize_attempts > 0
        else 0.0
    )

    print("=== Stress Summary ===")
    print(f"students: {args.students}")
    print(f"successes: {successes}")
    print(f"failures: {args.students - successes}")
    print(f"error_events: {total_errors}")
    print(f"conflict_events: {total_conflicts}")
    print(f"conflict_rate_pct: {conflict_rate:.2f}")
    print(f"grading_idempotency_failures: {idempotent_failures}")
    print(f"duration_mean_ms: {statistics.mean(durations):.2f}")
    print(
        f"duration_p95_ms: {statistics.quantiles(durations, n=20)[-1]:.2f}"
        if len(durations) > 1
        else f"duration_p95_ms: {durations[0]:.2f}"
    )


if __name__ == "__main__":
    asyncio.run(main())
