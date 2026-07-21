"""Tests for application startup orchestration without persistent I/O."""

import asyncio

import pytest

import main as main_module


def test_lifespan_runs_migrations_then_enabled_demo_seed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    startup_calls: list[str] = []

    monkeypatch.setattr(main_module.settings, "seed_demo_data", True)
    monkeypatch.setattr(
        main_module,
        "run_database_migrations",
        lambda: startup_calls.append("migrations"),
    )
    monkeypatch.setattr(
        main_module,
        "seed",
        lambda: startup_calls.append("seed"),
    )

    async def run_lifespan() -> None:
        async with main_module.lifespan(main_module.app):
            assert startup_calls == ["migrations", "seed"]

    asyncio.run(run_lifespan())

    assert startup_calls == ["migrations", "seed"]
