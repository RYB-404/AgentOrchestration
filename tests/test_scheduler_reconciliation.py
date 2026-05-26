import pytest

from src.orchestrator.scheduler import TaskScheduler


def test_periodic_reconciliation_is_staggered_without_same_second_burst():
    scheduler = TaskScheduler()
    tasks = [{"name": "node-a"}, {"name": "node-b"}, {"name": "node-c"}]

    task_ids = scheduler.schedule_periodic_reconciliation(tasks, interval=30, initial_delay=5)

    scheduled_times = [scheduler._scheduled[task_id] for task_id in task_ids]
    offsets = [round(t - scheduled_times[0], 3) for t in scheduled_times]
    assert offsets == [0, 10, 20]


def test_periodic_reconciliation_preserves_audit_metadata():
    scheduler = TaskScheduler()

    task_id = scheduler.schedule_periodic_reconciliation([{"name": "node-a"}], interval=60)[0]

    task = scheduler._scheduled_tasks[task_id]
    assert task["reconciliation_index"] == 0
    assert task["reconciliation_interval"] == 60
    assert task["queue"] == "default"


def test_periodic_reconciliation_rejects_invalid_interval():
    scheduler = TaskScheduler()

    with pytest.raises(ValueError, match="interval must be greater than zero"):
        scheduler.schedule_periodic_reconciliation([{"name": "node-a"}], interval=0)
