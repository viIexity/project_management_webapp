"""
Comprehensive Automated Verification & Test Suite for NexusPM.
Verifies all Basic, Intermediate (PERT & CPM), and Advanced (RCPSP) Goals and Metrics of Success.

Run with:
    python test.py
"""
from __future__ import annotations
import math
import os
import tempfile
import unittest

from backend.app import dispatch_api_request
from backend.seed import seed_if_empty


class TestProjectManagementApp(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_pm.db")
        seed_if_empty(self.db_path, force_reset=True)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    # =========================================================================
    # BASIC GOALS: Project & Task CRUD, Team Workload, and DAG Dependencies
    # =========================================================================
    def test_01_basic_task_crud_and_persistence(self) -> None:
        """
        Verify:
          - Users are able to create, edit, assign, and delete tasks consistently.
          - Task information (description, assignee, status, start date & deadline, priority) is saved accurately.
        """
        # Create a new project
        st, res = dispatch_api_request(
            "POST",
            "/api/projects",
            body={
                "name": "Test Engineering Project",
                "description": "Verification project for CRUD accuracy",
                "start_date": "2026-11-16",
                "target_deadline_days": 20,
                "max_labor": 5,
                "max_equipment": 3,
                "max_budget_per_day": 4000,
            },
            db_path=self.db_path,
        )
        self.assertEqual(st, 201)
        pid = res["project"]["id"]

        # Create a team member with role
        st, mem_res = dispatch_api_request(
            "POST",
            f"/api/projects/{pid}/team",
            body={
                "name": "Dr. Evelyn Reed",
                "role": "Lead Optimization Scientist",
                "email": "evelyn@nexus.io",
                "capacity_hours_per_day": 8.0,
                "hourly_rate": 130.0,
            },
            db_path=self.db_path,
        )
        self.assertEqual(st, 201)
        member_id = mem_res["team_member"]["id"]

        # Create Task 1
        st, t1_res = dispatch_api_request(
            "POST",
            f"/api/projects/{pid}/tasks",
            body={
                "code": "T1",
                "title": "Design Database Schema",
                "description": "Normalize tables and indexes",
                "assignee_id": member_id,
                "status": "In Progress",
                "priority": "Critical",
                "start_date": "2026-11-16",
                "deadline_date": "2026-11-20",
                "optimistic_days": 2.0,
                "most_likely_days": 4.0,
                "pessimistic_days": 6.0,
                "duration_days": 4.0,
                "labor_req": 2.0,
                "equipment_req": 1.0,
                "budget_req": 1000.0,
            },
            db_path=self.db_path,
        )
        self.assertEqual(st, 201)
        t1 = t1_res["task"]
        t1_id = t1["id"]

        # Verify saved task fields accurately match input
        self.assertEqual(t1["code"], "T1")
        self.assertEqual(t1["title"], "Design Database Schema")
        self.assertEqual(t1["description"], "Normalize tables and indexes")
        self.assertEqual(t1["assignee_id"], member_id)
        self.assertEqual(t1["assignee_name"], "Dr. Evelyn Reed")
        self.assertEqual(t1["status"], "In Progress")
        self.assertEqual(t1["priority"], "Critical")
        self.assertEqual(t1["start_date"], "2026-11-16")
        self.assertEqual(t1["deadline_date"], "2026-11-20")
        self.assertAlmostEqual(t1["expected_duration"], 4.0, places=4)

        # Edit Task 1
        st, upd_res = dispatch_api_request(
            "PUT",
            f"/api/tasks/{t1_id}",
            body={
                "title": "Design Distributed SQL Schema",
                "status": "Completed",
                "priority": "High",
                "duration_days": 5.0,
            },
            db_path=self.db_path,
        )
        self.assertEqual(st, 200)
        self.assertEqual(upd_res["task"]["title"], "Design Distributed SQL Schema")
        self.assertEqual(upd_res["task"]["status"], "Completed")
        self.assertEqual(upd_res["task"]["priority"], "High")
        self.assertEqual(upd_res["task"]["duration_days"], 5.0)

        # Verify Team Workload tracking
        st, team_res = dispatch_api_request(
            "GET", f"/api/projects/{pid}/team", db_path=self.db_path
        )
        self.assertEqual(st, 200)
        w = team_res["workload"]
        self.assertEqual(w["team_size"], 1)
        self.assertEqual(w["total_assigned_tasks"], 1)
        self.assertEqual(w["members"][0]["completed_tasks"], 1)
        self.assertAlmostEqual(w["members"][0]["estimated_hours"], 40.0, places=2)

        # Delete Task 1
        st, del_res = dispatch_api_request(
            "DELETE", f"/api/tasks/{t1_id}", db_path=self.db_path
        )
        self.assertEqual(st, 200)
        self.assertTrue(del_res["deleted"])

        st, list_res = dispatch_api_request(
            "GET", f"/api/projects/{pid}/tasks", db_path=self.db_path
        )
        self.assertEqual(len(list_res["tasks"]), 0)

    def test_02_dag_dependencies_and_cycle_prevention(self) -> None:
        """
        Verify:
          - Users are able to create dependencies between tasks.
          - Dependent tasks track whether predecessors are accomplished (gating).
          - Circular dependencies (cycles) and self-loops are strictly rejected.
        """
        st, proj_res = dispatch_api_request("GET", "/api/projects/3", db_path=self.db_path)
        self.assertEqual(st, 200)
        tasks = proj_res["tasks"]
        by_code = {t["code"]: t for t in tasks}

        # Task A is Completed, Task B is In Progress, Task D depends on B
        self.assertTrue(by_code["B"]["is_ready_to_start"])  # Because A is Completed
        self.assertFalse(by_code["D"]["is_ready_to_start"])  # Because B is not Completed yet
        self.assertEqual(by_code["D"]["blocking_predecessors"][0]["code"], "B")

        # Attempt to create a cycle H -> A (since A -> B -> D -> G -> H exists)
        st_cycle, cycle_res = dispatch_api_request(
            "POST",
            "/api/projects/3/dependencies",
            body={
                "predecessor_id": by_code["H"]["id"],
                "successor_id": by_code["A"]["id"],
            },
            db_path=self.db_path,
        )
        self.assertEqual(st_cycle, 400)
        self.assertIn("circular dependency cycle", cycle_res["error"].lower())

    # =========================================================================
    # INTERMEDIATE GOALS: PERT & Critical Path Method (CPM)
    # =========================================================================
    def test_03_pert_expected_duration_variance_and_probability(self) -> None:
        """
        Verify PERT Metrics of Success against independent hand calculations on Benchmark Project #3:
          Critical Path: A -> B -> D -> G -> H
          Task A: O=2, M=3, P=4 => TE = (2+12+4)/6 = 3.0, V = ((4-2)/6)^2 = 4/36 = 1/9
          Task B: O=3, M=5, P=7 => TE = (3+20+7)/6 = 5.0, V = ((7-3)/6)^2 = 16/36 = 4/9
          Task D: O=4, M=6, P=8 => TE = (4+24+8)/6 = 6.0, V = ((8-4)/6)^2 = 16/36 = 4/9
          Task G: O=3, M=4, P=5 => TE = (3+16+5)/6 = 4.0, V = ((5-3)/6)^2 = 4/36 = 1/9
          Task H: O=1, M=2, P=3 => TE = (1+8+3)/6  = 2.0, V = ((3-1)/6)^2 = 4/36 = 1/9
          Total Critical Path Expected Duration TE_project = 3 + 5 + 6 + 4 + 2 = 20.0 days
          Total Critical Path Variance V_project = (4 + 16 + 16 + 4 + 4) / 36 = 44 / 36 = 11 / 9 = 1.222222...
          Std Dev sigma_project = sqrt(11 / 9) = 1.1055415967851332
          For Target Deadline D = 22.0 days:
            Z = (22.0 - 20.0) / sqrt(11 / 9) = 2.0 / 1.1055415967851332 = 1.8090680674665818
            Probability = 0.5 * (1 + erf(Z / sqrt(2))) = 0.964778... (96.48%)
        """
        target_d = 22.0
        st, pert = dispatch_api_request(
            "GET",
            "/api/projects/3/pert",
            query_params={"target_deadline": str(target_d)},
            db_path=self.db_path,
        )
        self.assertEqual(st, 200)
        self.assertTrue(pert["is_valid_dag"])

        indep_te = 3.0 + 5.0 + 6.0 + 4.0 + 2.0
        indep_var = (4.0 + 16.0 + 16.0 + 4.0 + 4.0) / 36.0
        indep_std = math.sqrt(indep_var)
        indep_z = (target_d - indep_te) / indep_std
        indep_prob = 0.5 * (1.0 + math.erf(indep_z / math.sqrt(2.0)))

        self.assertAlmostEqual(pert["project_expected_duration"], indep_te, places=4)
        self.assertAlmostEqual(pert["project_variance"], round(indep_var, 4), places=4)
        self.assertAlmostEqual(pert["project_std_dev"], round(indep_std, 4), places=4)
        self.assertAlmostEqual(pert["z_score"], round(indep_z, 4), places=4)
        self.assertAlmostEqual(pert["completion_probability"], round(indep_prob, 6), places=5)

    def test_04_cpm_critical_path_and_slack_float(self) -> None:
        """
        Verify CPM Metrics of Success on Benchmark Project #3:
          - Critical path is correctly identified: ['A', 'B', 'D', 'G', 'H'] with duration 20.0
          - Non-critical tasks C, E, F have exact positive Total Float and Free Float:
            * A: ES=0, EF=3, LS=0, LF=3, TF=0, FF=0 (Critical)
            * B: ES=3, EF=8, LS=3, LF=8, TF=0, FF=0 (Critical)
            * C: ES=3, EF=7, LS=7, LF=11, TF=4, FF=0
            * D: ES=8, EF=14, LS=8, LF=14, TF=0, FF=0 (Critical)
            * E: ES=7, EF=10, LS=11, LF=14, TF=4, FF=4 (since Succ(E)=[G] and ES(G)=14 => 14-10=4)
            * F: ES=7, EF=11, LS=14, LF=18, TF=7, FF=7 (since Succ(F)=[H] and ES(H)=18 => 18-11=7)
            * G: ES=14, EF=18, LS=14, LF=18, TF=0, FF=0 (Critical)
            * H: ES=18, EF=20, LS=18, LF=20, TF=0, FF=0 (Critical)
        """
        st, cpm = dispatch_api_request(
            "GET",
            "/api/projects/3/cpm",
            query_params={"duration_mode": "deterministic"},
            db_path=self.db_path,
        )
        self.assertEqual(st, 200)
        self.assertEqual(cpm["project_duration"], 20.0)
        self.assertEqual(cpm["primary_critical_path_codes"], ["A", "B", "D", "G", "H"])

        by_code = {m["code"]: m for m in cpm["tasks_schedule"]}

        # Check Critical Task D
        self.assertEqual((by_code["D"]["es"], by_code["D"]["ef"]), (8.0, 14.0))
        self.assertEqual((by_code["D"]["ls"], by_code["D"]["lf"]), (8.0, 14.0))
        self.assertEqual(by_code["D"]["total_float"], 0.0)
        self.assertTrue(by_code["D"]["is_critical"])

        # Check Non-Critical Tasks C, E, F Slack/Float
        self.assertEqual(by_code["C"]["total_float"], 4.0)
        self.assertEqual(by_code["C"]["free_float"], 0.0)
        self.assertFalse(by_code["C"]["is_critical"])

        self.assertEqual(by_code["E"]["total_float"], 4.0)
        self.assertEqual(by_code["E"]["free_float"], 4.0)

        self.assertEqual(by_code["F"]["total_float"], 7.0)
        self.assertEqual(by_code["F"]["free_float"], 7.0)

    # =========================================================================
    # ADVANCED GOALS: Resource-Constrained Project Scheduling Problem (RCPSP)
    # =========================================================================
    def test_05_rcpsp_constraints_and_makespan_reduction(self) -> None:
        """
        Verify RCPSP Metrics of Success across all 3 seeded projects:
          1. Generated schedules (Heuristic & CP-SAT) strictly satisfy all resource constraints.
          2. Every task is assigned a valid start and finish time.
          3. Optimized schedules showcase a measurable reduction in project makespan
             compared to the initial resource-constrained scheduling method.
        """
        for project_id in (1, 2, 3):
            st, rcpsp = dispatch_api_request(
                "GET", f"/api/projects/{project_id}/rcpsp", db_path=self.db_path
            )
            self.assertEqual(st, 200)
            self.assertTrue(rcpsp["is_valid_dag"])

            sc = rcpsp["summary_comparison"]
            methods = rcpsp["methods"]

            for method_key in ("initial_baseline", "heuristic", "cp_sat"):
                ver = methods[method_key]["verification"]
                self.assertTrue(
                    ver["is_valid"],
                    f"Project {project_id} {method_key} failed verification: {ver}",
                )
                self.assertTrue(ver["all_tasks_assigned_valid_times"])
                self.assertTrue(ver["precedence_satisfied"])
                self.assertTrue(ver["resource_constraints_satisfied"])
                self.assertEqual(ver["violation_days_count"], 0)

            # Verify measurable makespan reduction compared to initial scheduling method
            self.assertLess(
                sc["cp_sat_makespan"],
                sc["initial_makespan"],
                f"Project {project_id}: CP-SAT makespan ({sc['cp_sat_makespan']}) should be strictly less than initial makespan ({sc['initial_makespan']})",
            )
            self.assertLessEqual(
                sc["cp_sat_makespan"],
                sc["heuristic_makespan"],
                f"Project {project_id}: CP-SAT makespan ({sc['cp_sat_makespan']}) should be <= heuristic makespan ({sc['heuristic_makespan']})",
            )
            self.assertGreater(sc["cp_sat_makespan_reduction_days"], 0)
            self.assertGreater(sc["cp_sat_makespan_reduction_pct"], 0.0)


if __name__ == "__main__":
    print("=" * 78)
    print("NexusPM — Automated Verification & Metrics of Success Test Suite")
    print("=" * 78)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestProjectManagementApp)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if not result.wasSuccessful():
        raise SystemExit(1)
