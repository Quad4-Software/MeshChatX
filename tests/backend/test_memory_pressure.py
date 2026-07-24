# SPDX-License-Identifier: 0BSD

from unittest.mock import MagicMock, patch

from meshchatx.src.backend.memory_pressure import MemoryPressureManager


def test_run_periodic_cleanup_sweeps_and_reports_stats():
    app = MagicMock()
    app.reticulum = MagicMock()
    app.rnpath_handler = MagicMock()
    app.database = MagicMock()
    manager = MemoryPressureManager(app=app)

    with (
        patch(
            "meshchatx.src.backend.memory_pressure.nomadnet_downloader.cached_link_count",
            side_effect=[2, 1],
        ),
        patch(
            "meshchatx.src.backend.memory_pressure.nomadnet_downloader.sweep_stale_links",
        ) as nomad_sweep,
        patch(
            "meshchatx.src.backend.memory_pressure.rns_link_manager.cached_link_count",
            side_effect=[3, 2],
        ),
        patch(
            "meshchatx.src.backend.memory_pressure.rns_link_manager.sweep_stale_links",
        ) as rns_sweep,
        patch(
            "meshchatx.src.backend.memory_pressure.reticulum_pathfinding.prune_expired_path_table_entries",
            return_value=4,
        ),
        patch(
            "meshchatx.src.backend.memory_pressure.reticulum_pathfinding.prune_path_table_to_soft_cap",
            return_value=1,
        ),
        patch(
            "meshchatx.src.backend.memory_pressure.reticulum_pathfinding.clean_rns_announce_cache",
            return_value=True,
        ),
        patch(
            "meshchatx.src.backend.memory_pressure.reticulum_pathfinding.path_table_size",
            return_value=42,
        ),
        patch.object(manager, "_count_held_announces", return_value=0),
    ):
        stats = manager.run_periodic_cleanup()

    nomad_sweep.assert_called_once()
    rns_sweep.assert_called_once()
    assert stats["nomad_links_swept"] == 1
    assert stats["rns_links_swept"] == 1
    assert stats["paths_pruned_expired"] == 4
    assert stats["paths_pruned_cap"] == 1
    assert stats["announce_cache_cleaned"] is True
    assert stats["path_table_size"] == 42


def test_on_memory_low_relaxes_sqlite():
    app = MagicMock()
    app.database = MagicMock()
    app.landlock_active = False
    app.appcontainer_active = False
    manager = MemoryPressureManager(app=app)
    with patch.object(manager, "run_periodic_cleanup", return_value={"ok": True}):
        stats = manager.on_memory_low(50.0)
    app.database.apply_memory_pressure_pragmas.assert_called_once_with(
        True,
        fs_sandbox_active=False,
    )
    assert stats["sqlite_relaxed"] is True
    assert stats["sqlite_file_temp"] is True
    manager.on_memory_recovered()
    app.database.apply_memory_pressure_pragmas.assert_called_with(False)


def test_on_memory_low_keeps_memory_temp_when_landlock_active():
    app = MagicMock()
    app.database = MagicMock()
    app.landlock_active = True
    app.appcontainer_active = False
    manager = MemoryPressureManager(app=app)
    with patch.object(manager, "run_periodic_cleanup", return_value={"ok": True}):
        stats = manager.on_memory_low(50.0)
    app.database.apply_memory_pressure_pragmas.assert_called_once_with(
        True,
        fs_sandbox_active=True,
    )
    assert stats["sqlite_relaxed"] is True
    assert stats["sqlite_file_temp"] is False


def test_on_memory_low_keeps_memory_temp_when_appcontainer_active():
    app = MagicMock()
    app.database = MagicMock()
    app.landlock_active = False
    app.appcontainer_active = True
    manager = MemoryPressureManager(app=app)
    with patch.object(manager, "run_periodic_cleanup", return_value={"ok": True}):
        stats = manager.on_memory_low(50.0)
    app.database.apply_memory_pressure_pragmas.assert_called_once_with(
        True,
        fs_sandbox_active=True,
    )
    assert stats["sqlite_file_temp"] is False
