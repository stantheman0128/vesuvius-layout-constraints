import numpy as np

from layout_constraints.project import bilinear, decimate, ds8_to_grid, to_collections


def grid3():
    """3x3 grid where x = 10 j, y = 10 i, z = 100 + i + 2 j (linear, so bilinear is exact)."""
    i, j = np.mgrid[0:3, 0:3].astype(np.float32)
    return np.stack([10 * j, 10 * i, 100 + i + 2 * j], -1)


def test_bilinear_known_values_and_edges():
    pts, ok = bilinear(grid3(), [0.5, 1.25, 2.0, 0.0], [1.5, 0.0, 2.0, 0.0])
    assert ok.all()
    np.testing.assert_allclose(pts, [[15, 5, 103.5], [0, 12.5, 101.25], [20, 20, 106], [0, 0, 100]], atol=1e-5)


def test_invalid_vertex_rejects_only_its_quads():
    g = grid3()
    g[2, 2] = -1
    _, ok = bilinear(g, [1.5, 0.5, 1.5, 0.5], [1.5, 0.5, 0.5, 1.5])
    assert ok.tolist() == [False, True, True, True]
    _, ok = bilinear(grid3(), [-0.1, 2.1, 1.0], [1.0, 1.0, 2.5])
    assert not ok.any()


def test_ds8_to_grid():
    i, j = ds8_to_grid([5, 6325], [10, 4550])
    np.testing.assert_allclose(i, [2.0, 2530.0])
    np.testing.assert_allclose(j, [4.0, 1820.0])


def test_decimate_min_spacing():
    pts = np.stack([np.arange(0, 101, 1.0), np.zeros(101), np.zeros(101)], 1)
    kept = decimate(pts, 10.0)
    np.testing.assert_allclose(kept[:, 0], np.arange(0, 101, 10.0))
    assert (np.linalg.norm(np.diff(kept, axis=0), axis=1) >= 10.0).all()


def test_point_ids_increase_along_each_chain():
    chains = [{"name": n, "kind": "text_line", "metadata": {}, "points": np.arange(9.0).reshape(3, 3) + k}
              for k, n in enumerate(["a", "b"])]
    doc = to_collections(chains, creation_time=1)
    assert doc["vc_pointcollections_json_version"] == "1"
    seen = []
    for c in doc["collections"].values():
        assert c["metadata"]["winding_is_absolute"] is False
        ids = list(c["points"])
        assert [int(k) for k in ids] == sorted(int(k) for k in ids)
        assert all(c["points"][k]["wind_a"] is None for k in ids)
        assert c["points"][ids[0]]["p"] == [float(v) for v in chains[len(seen)]["points"][0]]
        seen.append(ids)
    assert int(seen[0][-1]) < int(seen[1][0])
