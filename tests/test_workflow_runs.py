from novel_assistant.workflow_runs import WorkflowRunStore


def test_workflow_run_store_creates_completes_and_loads_run(tmp_path):
    store = WorkflowRunStore(tmp_path / "workflow-runs")

    created = store.create(
        workflow_id="novel-demo-run",
        project_id="novel-demo",
        request={
            "project_id": "novel-demo",
            "chapter_count": 3,
            "start_chapter": 1,
            "end_chapter": 2,
            "mode": "deterministic",
        },
    )
    completed = store.complete(
        "novel-demo-run",
        result={"project_id": "novel-demo", "generated_chapter_count": 2},
        progress={
            "total_chapters": 3,
            "completed_chapters": 2,
            "current_chapter": 2,
        },
    )

    loaded = store.get("novel-demo-run")

    assert created.status == "running"
    assert completed.status == "completed"
    assert loaded == completed
    assert loaded.result == {"project_id": "novel-demo", "generated_chapter_count": 2}
    assert loaded.error is None


def test_workflow_run_store_records_failed_run(tmp_path):
    store = WorkflowRunStore(tmp_path / "workflow-runs")
    store.create(
        workflow_id="novel-demo-run",
        project_id="novel-demo",
        request={"project_id": "novel-demo"},
    )

    failed = store.fail("novel-demo-run", error="LLM timeout")

    assert failed.status == "failed"
    assert failed.error == "LLM timeout"
    assert store.get("missing-run") is None
