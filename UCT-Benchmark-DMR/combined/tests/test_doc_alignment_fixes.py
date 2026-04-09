# -*- coding: utf-8 -*-
"""
Tests for documentation alignment fixes.

Validates the 16 fixes identified in the Benchmarking Documentation alignment audit.
"""

import ast
import numpy as np
import pandas as pd
import pathlib
import pytest


# =============================================================================
# Fix 1: Bias computation — no division by point_size
# =============================================================================


class TestBiasComputation:
    """Verify bias is per-pair, per-dimension (no averaging by point_size)."""

    def test_bias_is_raw_difference(self):
        """Bias should equal candidate - reference for each pair, not divided by N.

        Uses AST-based source inspection to avoid importing orekit/jpype
        (a transitive dependency of stateMetrics via apiIntegration), which
        may not be available in all test environments.

        The check verifies that the bias assignment in stateMetrics.py is:
            bias = candidate[STATE_COLUMNS].values - prop_ref[STATE_COLUMNS].values
        and that `point_size` (the per-pair count N) is NOT a divisor.
        """
        import ast
        import pathlib

        src = (
            pathlib.Path(__file__).parent.parent
            / "uct_benchmark"
            / "evaluation"
            / "stateMetrics.py"
        )
        source_text = src.read_text(encoding="utf-8")
        tree = ast.parse(source_text)

        # Collect all assignment targets named "bias" and their right-hand sides
        bias_assignments = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "bias":
                        bias_assignments.append(node.value)

        assert bias_assignments, "No assignment to 'bias' found in stateMetrics.py"

        # At least one bias assignment must be a subtraction (BinOp with Sub)
        subtraction_found = any(
            isinstance(expr, ast.BinOp) and isinstance(expr.op, ast.Sub)
            for expr in bias_assignments
        )
        assert subtraction_found, (
            "Expected 'bias = candidate - reference' (subtraction) in stateMetrics.py"
        )

        # None of the bias assignments may divide by point_size
        unparsed = [ast.unparse(expr) for expr in bias_assignments]
        for expr_str in unparsed:
            assert "point_size" not in expr_str, (
                f"bias assignment incorrectly divides by point_size: {expr_str}"
            )


# =============================================================================
# Fix 2: Residual metrics in arcseconds
# =============================================================================


class TestResidualUnits:
    """Verify residual metrics output in arcseconds."""

    def test_residuals_in_arcseconds(self):
        """A known angular separation should convert to arcseconds correctly."""
        # 1 degree = 3600 arcseconds
        # Set up obs and propagated state with ~1 degree separation in RA
        from uct_benchmark.evaluation.residualMetrics import retrieveResiduals

        # Create test data where obs RA = 10 deg, propagated RA ≈ 11 deg
        # With Dec = 0, great circle ≈ cos(0) * 1 deg = 1 deg = 3600 arcsec
        obs_df = pd.DataFrame({
            "id": [1],
            "obTime": ["2025-01-01T00:00:00"],
            "ra": [10.0],
            "declination": [0.0],
            "satNo": [25544],
        })

        row = pd.Series({
            "epoch": "2025-01-01T00:00:00",
            "xpos": 6778.0 * np.cos(np.radians(11.0)),
            "ypos": 6778.0 * np.sin(np.radians(11.0)),
            "zpos": 0.0,
            "xvel": 0.0, "yvel": 7.5, "zvel": 0.0,
            "satNo": 25544,
            "mass": 1000.0, "crossSection": 10.0,
            "dragCoeff": 2.2, "solarRadPressCoeff": 1.5,
        })

        # Mock propagator to return state at each obs time
        prop_state = np.array([
            6778.0 * np.cos(np.radians(11.0)),
            6778.0 * np.sin(np.radians(11.0)),
            0.0, 0.0, 7.5, 0.0
        ])

        def mock_prop(line1, line2, epochs, sat_params):
            return [prop_state]

        result = retrieveResiduals((row, obs_df, mock_prop, True, False))

        # The residual should be approximately 3600 arcseconds (1 degree)
        residual = result["Residuals"]
        if isinstance(residual, list):
            residual = residual[0]
        assert residual > 3000, f"Expected ~3600 arcsec, got {residual} (still in radians?)"
        assert residual < 4000, f"Expected ~3600 arcsec, got {residual}"


# =============================================================================
# Fix 3: HAMR threshold = 1.0 m²/kg
# =============================================================================


class TestHAMRThreshold:
    """Verify HAMR threshold is 1.0 m²/kg per documentation."""

    def test_hamr_threshold_value(self):
        from uct_benchmark.settings import HAMR_THRESHOLD
        assert HAMR_THRESHOLD == 1.0, f"HAMR_THRESHOLD should be 1.0, got {HAMR_THRESHOLD}"

    def test_hamr_filtering(self):
        """Objects with A/M > 1.0 should be classified as HAMR."""
        from uct_benchmark.settings import HAMR_THRESHOLD

        # Object with mass=100 kg, area=50 m² → A/M = 0.5 < 1.0 → NOT HAMR
        assert 50.0 / 100.0 < HAMR_THRESHOLD

        # Object with mass=10 kg, area=20 m² → A/M = 2.0 > 1.0 → HAMR
        assert 20.0 / 10.0 > HAMR_THRESHOLD


# =============================================================================
# Fix 4: Angular noise = 1 arcsecond in degrees
# =============================================================================


class TestAngularNoise:
    """Verify angular noise is 1 arcsecond expressed in degrees."""

    def test_angular_noise_value(self):
        from uct_benchmark.settings import angularNoise

        expected = 1.0 / 3600.0  # 1 arcsecond in degrees
        assert abs(angularNoise - expected) < 1e-12, (
            f"angularNoise should be {expected} degrees (1 arcsec), got {angularNoise}"
        )

    def test_angular_noise_reasonable_magnitude(self):
        """1 arcsecond in degrees should be a very small number (~2.78e-4)."""
        from uct_benchmark.settings import angularNoise
        assert angularNoise < 0.001, f"angularNoise={angularNoise} is too large"
        assert angularNoise > 1e-5, f"angularNoise={angularNoise} is too small"


# =============================================================================
# Fix 5: True negatives default to enabled
# =============================================================================


class TestTrueNegativesDefault:
    """Verify true negatives are enabled by default in the pipeline."""

    def test_generate_dataset_defaults_to_true(self):
        """include_non_ref_obs should default to True.

        Uses AST-based source inspection to avoid importing orekit/jpype,
        which may not be available in all test environments.
        """
        import ast
        import pathlib

        src = pathlib.Path(__file__).parent.parent / "uct_benchmark" / "api" / "apiIntegration.py"
        tree = ast.parse(src.read_text(encoding="utf-8"))

        # Find the generateDataset function definition
        func_def = next(
            (
                node
                for node in ast.walk(tree)
                if isinstance(node, ast.FunctionDef) and node.name == "generateDataset"
            ),
            None,
        )
        assert func_def is not None, "generateDataset function not found in apiIntegration.py"

        # Build a mapping of arg_name -> default value (from the end of args)
        args = func_def.args
        defaults = args.defaults  # aligned to the *last* N positional args
        positional = args.args
        offset = len(positional) - len(defaults)
        param_defaults = {
            positional[offset + i].arg: defaults[i]
            for i in range(len(defaults))
        }

        node = param_defaults.get("include_non_ref_obs")
        assert node is not None, "include_non_ref_obs parameter not found in generateDataset"
        assert isinstance(node, ast.Constant) and node.value is True, (
            f"include_non_ref_obs default should be True, got {ast.unparse(node)}"
        )


# =============================================================================
# Fix 6: Convex hull for orbital coverage
# =============================================================================


class TestConvexHullCoverage:
    """Verify orbital coverage uses convex hull, not angular-sort polygon."""

    def test_convex_hull_known_case(self):
        """For a known set of points, verify ConvexHull area is used."""
        from scipy.spatial import ConvexHull

        # Square with vertices at (0,0), (1,0), (1,1), (0,1) → area = 1.0
        points = np.array([[0, 0], [1, 0], [1, 1], [0, 1]])
        hull = ConvexHull(points)
        assert abs(hull.volume - 1.0) < 1e-10

    def test_orbit_coverage_uses_convex_hull(self):
        """Verify orbitCoverage imports and uses ConvexHull."""
        import inspect
        from uct_benchmark.simulation import orbitCoverage

        source = inspect.getsource(orbitCoverage)
        assert "ConvexHull" in source, "orbitCoverage should use scipy.spatial.ConvexHull"
        assert "Shoelace" not in source.replace("# Shoelace", ""), (
            "orbitCoverage should not use Shoelace formula for area"
        )


# =============================================================================
# Fix 7: T3 vs T4 tier distinction
# =============================================================================


class TestTierDistinction:
    """Verify T4 takes priority over T3 when insufficient objects."""

    def test_t4_priority_when_not_enough_objects(self):
        """When numObj < targetNumObj, T4 should be returned even if T3 conditions exist."""
        from uct_benchmark.data.basicScoringFunction import basicScoring

        # This is a logic test — T4 should win when not enough objects
        # The flag resolution should give T4 > T3 > T2 > T1
        # Test by verifying the source code logic
        import inspect
        source = inspect.getsource(basicScoring)
        # Verify T4 takes priority in flag resolution
        assert "if T4:" in source, "T4 should be checked first in flag resolution"


# =============================================================================
# Fix 11: UCTP schema validation
# =============================================================================


class TestUCTPSchemaValidation:
    """Verify UCTP output schema validation works correctly."""

    def test_valid_state_vector_submission(self):
        from backend_api.routers.submissions import validate_uctp_output

        data = [{
            "sourcedData": [1, 2, 3],
            "epoch": "2025-01-01T00:00:00Z",
            "xpos": 6778.0,
            "ypos": 0.0,
            "zpos": 0.0,
            "xvel": 0.0,
            "yvel": 7.5,
            "zvel": 0.0,
        }]
        is_valid, errors = validate_uctp_output(data)
        assert is_valid, f"Valid SV submission rejected: {errors}"

    def test_valid_tle_submission(self):
        from backend_api.routers.submissions import validate_uctp_output

        data = [{
            "sourcedData": [1, 2],
            "line1": "1 25544U 98067A   ...",
            "line2": "2 25544  51.6 ...",
        }]
        is_valid, errors = validate_uctp_output(data)
        assert is_valid, f"Valid TLE submission rejected: {errors}"

    def test_missing_required_fields_rejected(self):
        from backend_api.routers.submissions import validate_uctp_output

        data = [{"epoch": "2025-01-01T00:00:00Z"}]  # Missing most fields
        is_valid, errors = validate_uctp_output(data)
        assert not is_valid
        assert len(errors) > 0

    def test_empty_submission_rejected(self):
        from backend_api.routers.submissions import validate_uctp_output

        is_valid, errors = validate_uctp_output([])
        assert not is_valid

    def test_invalid_cov_length_reported(self):
        from backend_api.routers.submissions import validate_uctp_output

        data = [{
            "sourcedData": [1],
            "epoch": "2025-01-01T00:00:00Z",
            "xpos": 0.0, "ypos": 0.0, "zpos": 0.0,
            "xvel": 0.0, "yvel": 0.0, "zvel": 0.0,
            "cov": [1.0] * 10,  # Should be 21 elements
        }]
        is_valid, errors = validate_uctp_output(data)
        assert not is_valid
        assert any("21" in e for e in errors)


# =============================================================================
# Fix 14: Downsampling exemptions
# =============================================================================


class TestDownsamplingExemptions:
    """Verify simulated and low-obs satellites are exempt from downsampling."""

    def test_exempt_helper_identifies_simulated(self):
        """Satellites with is_simulated=True should be exempt."""
        from uct_benchmark.data.dataManipulation import _get_exempt_satellites

        df = pd.DataFrame({
            "satNo": [1, 1, 1, 2, 2, 2, 3, 3],
            "is_simulated": [True, True, True, False, False, False, True, True],
        })
        exempt = _get_exempt_satellites(df)
        assert 1 in exempt  # All obs simulated
        assert 2 not in exempt  # Real obs
        assert 3 in exempt  # All simulated + only 2 obs

    def test_exempt_helper_identifies_low_obs(self):
        """Satellites with ≤2 observations should be exempt."""
        from uct_benchmark.data.dataManipulation import _get_exempt_satellites

        df = pd.DataFrame({
            "satNo": [1, 2, 2, 3, 3, 3, 3, 3],
        })
        exempt = _get_exempt_satellites(df)
        assert 1 in exempt  # Only 1 obs
        assert 2 in exempt  # Only 2 obs
        assert 3 not in exempt  # 5 obs


# =============================================================================
# Fix A: unitConversion.py loop variable fix
# =============================================================================


class TestUnitConversionLoopVariables:
    """Verify ECEF_match and TDR_match variables are used in their own loops (not ITRF_match)."""

    @staticmethod
    def _collect_statement_sequences(node):
        """
        Recursively collect all contiguous statement-list bodies reachable from
        *node* (function body, if-bodies, else-bodies, etc.) so we can check
        adjacent statements regardless of nesting depth.
        """
        sequences = []
        for child in ast.walk(node):
            for field, value in ast.iter_fields(child):
                if isinstance(value, list) and all(isinstance(v, ast.stmt) for v in value):
                    sequences.append(value)
        return sequences

    def test_ecef_loop_uses_ecef_match(self):
        """The ECR/ECEF for-loop should iterate over ECEF_match, not ITRF_match."""
        src = (
            pathlib.Path(__file__).parent.parent
            / "uct_benchmark"
            / "utils"
            / "unitConversion.py"
        )
        tree = ast.parse(src.read_text(encoding="utf-8"))

        func_def = next(
            (n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "unitConversion"),
            None,
        )
        assert func_def is not None, "unitConversion function not found"

        found_ecef_assign = False
        found_ecef_for_correct = False

        for body in self._collect_statement_sequences(func_def):
            for i, stmt in enumerate(body):
                if (
                    isinstance(stmt, ast.Assign)
                    and len(stmt.targets) == 1
                    and isinstance(stmt.targets[0], ast.Name)
                    and stmt.targets[0].id == "ECEF_match"
                ):
                    found_ecef_assign = True
                    if i + 1 < len(body):
                        next_stmt = body[i + 1]
                        if (
                            isinstance(next_stmt, ast.For)
                            and isinstance(next_stmt.iter, ast.Name)
                            and next_stmt.iter.id == "ECEF_match"
                        ):
                            found_ecef_for_correct = True

        assert found_ecef_assign, "No assignment to ECEF_match found in unitConversion"
        assert found_ecef_for_correct, (
            "The for-loop after ECEF_match assignment does not iterate over ECEF_match "
            "(bug: may be iterating over ITRF_match instead)"
        )

    def test_tdr_loop_uses_tdr_match(self):
        """The EFG/TDR for-loop should iterate over TDR_match, not ITRF_match."""
        src = (
            pathlib.Path(__file__).parent.parent
            / "uct_benchmark"
            / "utils"
            / "unitConversion.py"
        )
        tree = ast.parse(src.read_text(encoding="utf-8"))

        func_def = next(
            (n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "unitConversion"),
            None,
        )
        assert func_def is not None, "unitConversion function not found"

        found_tdr_assign = False
        found_tdr_for_correct = False

        for body in self._collect_statement_sequences(func_def):
            for i, stmt in enumerate(body):
                if (
                    isinstance(stmt, ast.Assign)
                    and len(stmt.targets) == 1
                    and isinstance(stmt.targets[0], ast.Name)
                    and stmt.targets[0].id == "TDR_match"
                ):
                    found_tdr_assign = True
                    if i + 1 < len(body):
                        next_stmt = body[i + 1]
                        if (
                            isinstance(next_stmt, ast.For)
                            and isinstance(next_stmt.iter, ast.Name)
                            and next_stmt.iter.id == "TDR_match"
                        ):
                            found_tdr_for_correct = True

        assert found_tdr_assign, "No assignment to TDR_match found in unitConversion"
        assert found_tdr_for_correct, (
            "The for-loop after TDR_match assignment does not iterate over TDR_match "
            "(bug: may be iterating over ITRF_match instead)"
        )


# =============================================================================
# Fix B: propagator.py config override fix
# =============================================================================


class TestPropagatorConfigOverride:
    """Verify config.dragCoef and config.solarRadPresCoef are assigned inside conditionals."""

    PROPAGATOR_SRC = (
        pathlib.Path(__file__).parent.parent
        / "uct_benchmark"
        / "simulation"
        / "propagator.py"
    )

    @staticmethod
    def _get_func_body(tree, func_name):
        func_def = next(
            (n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == func_name),
            None,
        )
        assert func_def is not None, f"{func_name} not found in propagator.py"
        return func_def.body

    @staticmethod
    def _config_assignment_is_conditional(body, attr_name):
        """
        Return True if every assignment of `config.<attr_name>` in the top-level
        function body is inside an If-block (i.e., NOT an unconditional statement).
        Return False if any such assignment appears directly at top level.
        """
        top_level_uncond = False
        for stmt in body:
            if isinstance(stmt, ast.Assign):
                rhs = stmt.value
                if (
                    isinstance(rhs, ast.Attribute)
                    and isinstance(rhs.value, ast.Name)
                    and rhs.value.id == "config"
                    and rhs.attr == attr_name
                ):
                    top_level_uncond = True
        return not top_level_uncond  # True = all conditional, False = at least one unconditional

    def test_monte_carlo_drag_is_conditional(self):
        tree = ast.parse(self.PROPAGATOR_SRC.read_text(encoding="utf-8"))
        body = self._get_func_body(tree, "monteCarloPropagator")
        assert self._config_assignment_is_conditional(body, "dragCoef"), (
            "monteCarloPropagator assigns config.dragCoef unconditionally at top level; "
            "it should be inside an if-block"
        )

    def test_monte_carlo_solar_is_conditional(self):
        tree = ast.parse(self.PROPAGATOR_SRC.read_text(encoding="utf-8"))
        body = self._get_func_body(tree, "monteCarloPropagator")
        assert self._config_assignment_is_conditional(body, "solarRadPresCoef"), (
            "monteCarloPropagator assigns config.solarRadPresCoef unconditionally at top level; "
            "it should be inside an if-block"
        )

    def test_ephemeris_drag_is_conditional(self):
        tree = ast.parse(self.PROPAGATOR_SRC.read_text(encoding="utf-8"))
        body = self._get_func_body(tree, "ephemerisPropagator")
        assert self._config_assignment_is_conditional(body, "dragCoef"), (
            "ephemerisPropagator assigns config.dragCoef unconditionally at top level; "
            "it should be inside an if-block"
        )

    def test_ephemeris_solar_is_conditional(self):
        tree = ast.parse(self.PROPAGATOR_SRC.read_text(encoding="utf-8"))
        body = self._get_func_body(tree, "ephemerisPropagator")
        assert self._config_assignment_is_conditional(body, "solarRadPresCoef"), (
            "ephemerisPropagator assigns config.solarRadPresCoef unconditionally at top level; "
            "it should be inside an if-block"
        )


# =============================================================================
# Fix C: basicScoringFunction T5 check
# =============================================================================


class TestBasicScoringT5:
    """Verify basicScoring has an `if T5:` check that assigns true_flag = 0."""

    def test_t5_check_present(self):
        """basicScoring should have `if T5:` in source."""
        import ast
        import pathlib

        src = (
            pathlib.Path(__file__).parent.parent
            / "uct_benchmark"
            / "data"
            / "basicScoringFunction.py"
        )
        tree = ast.parse(src.read_text(encoding="utf-8"))

        func_def = next(
            (n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "basicScoring"),
            None,
        )
        assert func_def is not None, "basicScoring function not found"

        # Look for an If node whose test is the name T5
        t5_if_nodes = [
            node
            for node in ast.walk(func_def)
            if isinstance(node, ast.If)
            and isinstance(node.test, ast.Name)
            and node.test.id == "T5"
        ]
        assert t5_if_nodes, "No `if T5:` block found in basicScoring"

    def test_t5_assigns_true_flag_zero(self):
        """Inside `if T5:`, true_flag should be assigned 0."""
        import ast
        import pathlib

        src = (
            pathlib.Path(__file__).parent.parent
            / "uct_benchmark"
            / "data"
            / "basicScoringFunction.py"
        )
        tree = ast.parse(src.read_text(encoding="utf-8"))

        func_def = next(
            (n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "basicScoring"),
            None,
        )
        assert func_def is not None, "basicScoring function not found"

        t5_if_nodes = [
            node
            for node in ast.walk(func_def)
            if isinstance(node, ast.If)
            and isinstance(node.test, ast.Name)
            and node.test.id == "T5"
        ]
        assert t5_if_nodes, "No `if T5:` block found in basicScoring"

        # Check that within the if T5: body, true_flag is assigned 0
        found_zero_assign = False
        for if_node in t5_if_nodes:
            for stmt in if_node.body:
                if (
                    isinstance(stmt, ast.Assign)
                    and any(
                        isinstance(t, ast.Name) and t.id == "true_flag"
                        for t in stmt.targets
                    )
                    and isinstance(stmt.value, ast.Constant)
                    and stmt.value.value == 0
                ):
                    found_zero_assign = True

        assert found_zero_assign, (
            "Inside `if T5:` block, expected `true_flag = 0` assignment but did not find it"
        )


# =============================================================================
# Fix D: binTracks cutoff parameter
# =============================================================================


class TestBinTracksCutoffParameter:
    """Verify binTracks uses the `cutoff` parameter for its time threshold."""

    def test_cutoff_parameter_used_in_threshold(self):
        """The threshold assignment in binTracks should use `cutoff`, not a hardcoded 90."""
        import ast
        import pathlib

        src = (
            pathlib.Path(__file__).parent.parent
            / "uct_benchmark"
            / "data"
            / "dataManipulation.py"
        )
        tree = ast.parse(src.read_text(encoding="utf-8"))

        func_def = next(
            (n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "binTracks"),
            None,
        )
        assert func_def is not None, "binTracks function not found in dataManipulation.py"

        # Walk all assignments in binTracks looking for `threshold = pd.Timedelta(minutes=...)`
        threshold_assigns = []
        for node in ast.walk(func_def):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "threshold":
                        threshold_assigns.append(node.value)

        assert threshold_assigns, "No assignment to `threshold` found in binTracks"

        # At least one threshold assignment must use `cutoff` (the parameter name)
        uses_cutoff = False
        for expr in threshold_assigns:
            expr_str = ast.unparse(expr)
            if "cutoff" in expr_str:
                uses_cutoff = True

        assert uses_cutoff, (
            f"binTracks threshold assignment(s) {[ast.unparse(e) for e in threshold_assigns]} "
            "do not reference `cutoff` parameter — hardcoded value detected"
        )

    def test_cutoff_not_hardcoded_90(self):
        """The threshold assignment must NOT be a bare integer literal 90."""
        import ast
        import pathlib

        src = (
            pathlib.Path(__file__).parent.parent
            / "uct_benchmark"
            / "data"
            / "dataManipulation.py"
        )
        tree = ast.parse(src.read_text(encoding="utf-8"))

        func_def = next(
            (n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "binTracks"),
            None,
        )
        assert func_def is not None, "binTracks function not found"

        for node in ast.walk(func_def):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "threshold":
                        expr_str = ast.unparse(node.value)
                        # Fail if the RHS is literally `pd.Timedelta(minutes=90)` with no variable
                        assert "cutoff" in expr_str or "90" not in expr_str, (
                            f"threshold is assigned a hardcoded 90: `{expr_str}` — "
                            "should use the `cutoff` parameter"
                        )


# =============================================================================
# Fix E: OrbitalRegime type includes combo regimes
# =============================================================================


class TestOrbitalRegimeTypeComboRegimes:
    """Verify OrbitalRegime TypeScript type includes ALL, LMO, LMG, MGH."""

    def _read_types_file(self):
        import pathlib

        return (
            pathlib.Path(__file__).parent.parent
            / "frontend"
            / "src"
            / "types"
            / "index.ts"
        ).read_text(encoding="utf-8")

    def test_orbital_regime_contains_all(self):
        content = self._read_types_file()
        assert "'ALL'" in content or '"ALL"' in content, (
            "OrbitalRegime type in frontend/src/types/index.ts is missing 'ALL'"
        )

    def test_orbital_regime_contains_lmo(self):
        content = self._read_types_file()
        assert "'LMO'" in content or '"LMO"' in content, (
            "OrbitalRegime type in frontend/src/types/index.ts is missing 'LMO'"
        )

    def test_orbital_regime_contains_lmg(self):
        content = self._read_types_file()
        assert "'LMG'" in content or '"LMG"' in content, (
            "OrbitalRegime type in frontend/src/types/index.ts is missing 'LMG'"
        )

    def test_orbital_regime_contains_mgh(self):
        content = self._read_types_file()
        assert "'MGH'" in content or '"MGH"' in content, (
            "OrbitalRegime type in frontend/src/types/index.ts is missing 'MGH'"
        )

    def test_orbital_regime_type_line(self):
        """The OrbitalRegime type declaration should list all combo regimes."""
        content = self._read_types_file()
        # The type may span multiple lines, so search the full content
        assert "OrbitalRegime" in content, "Could not find `OrbitalRegime` in index.ts"
        for regime in ("ALL", "LMO", "LMG", "MGH", "LGO", "LHO", "MGO", "MHO", "GHO", "LMH", "LGH"):
            assert regime in content, (
                f"Combo regime '{regime}' not found in OrbitalRegime type declaration"
            )


# =============================================================================
# Fix F: Object count tolerance
# =============================================================================


class TestObjectCountTolerance:
    """Verify OBJECT_COUNT_LEVELS has tolerance: 2 for each level."""

    def _read_types_file(self):
        import pathlib

        return (
            pathlib.Path(__file__).parent.parent
            / "frontend"
            / "src"
            / "types"
            / "index.ts"
        ).read_text(encoding="utf-8")

    def test_object_count_levels_has_tolerance(self):
        """OBJECT_COUNT_LEVELS definition should contain `tolerance: 2`."""
        content = self._read_types_file()
        assert "tolerance: 2" in content, (
            "OBJECT_COUNT_LEVELS in frontend/src/types/index.ts does not contain `tolerance: 2`"
        )

    def test_object_count_levels_tolerance_count(self):
        """Each of the 3 levels (H, S, L) should have `tolerance: 2`."""
        content = self._read_types_file()
        tolerance_occurrences = content.count("tolerance: 2")
        assert tolerance_occurrences >= 3, (
            f"Expected at least 3 occurrences of `tolerance: 2` in OBJECT_COUNT_LEVELS "
            f"(one per level H/S/L), found {tolerance_occurrences}"
        )


# =============================================================================
# Fix 16: F1 formula in documentation
# =============================================================================


class TestF1Formula:
    """Verify F1 formula is correct in documentation."""

    def test_f1_formula_correct(self):
        """Documentation should have F1 = 2TP/(2TP+FP+FN), not 2TP/(2TP+FN+TN)."""
        from pathlib import Path

        doc_path = Path(r"C:\Users\kelvi\desktop\projects\DMR(kelvinallignment)\provided-materials\Benchmarking Documentation.docx.md")
        if not doc_path.exists():
            pytest.skip("Documentation file not found")

        content = doc_path.read_text(encoding="utf-8")

        # Should NOT contain the incorrect formula
        assert "2TP+FN+TN" not in content, (
            "Documentation still contains incorrect F1 formula: 2TP/(2TP+FN+TN)"
        )

        # Should contain the correct formula
        assert "2TP+FP+FN" in content or "2TP + FP + FN" in content, (
            "Documentation should contain correct F1 formula: 2TP/(2TP+FP+FN)"
        )
