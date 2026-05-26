import asyncio

from src.agent.executor import AgentExecutor


def test_executor_records_json_serializable_result_once():
    executor = AgentExecutor()

    async def handler(agent_id, task):
        return {"ok": True, "items": [task["id"], agent_id]}

    execution_id = asyncio.run(executor.execute("agent-1", {"id": "task-1"}, handler))

    result = executor.get_result(execution_id)
    assert result["execution_id"] == execution_id
    assert result["result"] == {"ok": True, "items": ["task-1", "agent-1"]}


def test_executor_fails_closed_for_non_json_serializable_result():
    executor = AgentExecutor()

    async def handler(_agent_id, _task):
        return {"bad": object()}

    execution_id = asyncio.run(executor.execute("agent-1", {"id": "task-1"}, handler))

    result = executor.get_result(execution_id)
    assert result["execution_id"] == execution_id
    assert result["agent_id"] == "agent-1"
    assert result["task_id"] == "task-1"
    assert result["error_type"] == "ValueError"
    assert "not JSON serializable" in result["error"]
