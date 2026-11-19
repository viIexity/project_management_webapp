# NexusPM — Project Management Web Application (DAG, PERT, CPM & RCPSP)

A full-stack Project Management Web Application built with Python, SQLite, and an interactive Web UI implementing **Directed Acyclic Graph (DAG)** workflow dependencies, **Team Management & Workload Tracking**, **PERT Risk & Probability Analysis**, **Critical Path Method (CPM)**, and **Resource-Constrained Project Scheduling Problem (RCPSP)** optimization via **Priority-Rule Heuristics (SSGS/PSGS)** and **CP-SAT Exact Optimization**.

---

## Quick Start

1. **Start the Web Application Server:**
   ```powershell
   python main.py
   ```
   Then open **http://127.0.0.1:8000** in your browser.

2. **Run the Automated Verification & Metrics of Success Test Suite:**
   ```powershell
   python test.py
   ```

---

## Features & Goals Coverage

### 1. Basic Goals
- **Project & Task Creation (`backend/database.py`, `frontend/app.js`)**:
  - Full CRUD for projects and tasks including code, title, description, assignee, status (`Todo`, `In Progress`, `Blocked`, `Completed`), start date, deadline date, priority (`Low`, `Medium`, `High`, `Critical`), PERT three-point estimates ($O, M, P$), and renewable resource requirements (Labor, Equipment, Daily Budget).
  - Both **Table View** and **Kanban Board** views with filtering by status, priority, and assignee.
- **Team Management & Workload (`backend/algorithms/workload.py`)**:
  - Add, edit, and remove team members with roles, hourly rates, and daily capacity.
  - Real-time calculation of assigned task counts, completed vs. active workload, total estimated effort (hours & cost), role-level breakdown, and utilization gauges (`Balanced`, `Optimal`, `Overloaded`).
- **DAG Structure (`backend/algorithms/dag.py`)**:
  - Tasks form a **Directed Acyclic Graph (DAG)** where predecessor tasks must be accomplished before proceeding to dependent tasks.
  - Automatic cycle detection (Kahn's topological sort + 3-color DFS cycle path reconstruction) prevents self-loops and circular dependencies.
  - Interactive SVG **DAG Network Topology Visualizer** with stage layering, critical path highlighting, and predecessor readiness lock indicators.

### 2. Intermediate Goals
- **PERT Analysis (`backend/algorithms/pert.py`)**:
  - Per-task Expected Duration $TE_i = \frac{O_i + 4M_i + P_i}{6}$, Standard Deviation $\sigma_i = \frac{P_i - O_i}{6}$, and Variance $V_i = \sigma_i^2$.
  - Project Expected Duration $TE_{\text{project}} = \sum_{i \in CP} TE_i$ and Critical Path Variance $V_{\text{project}} = \sum_{i \in CP} V_i$.
  - Interactive Target Deadline Simulator computing $Z = \frac{D - TE_{\text{project}}}{\sqrt{V_{\text{project}}}}$ and Completion Probability $P(T \le D) = \Phi(Z)$ with an SVG Normal Distribution Bell Curve and Confidence Milestones Table (10% to 99%).
- **Critical Path Method — CPM (`backend/algorithms/cpm.py`)**:
  - Forward Pass ($ES_i, EF_i$) and Backward Pass ($LS_i, LF_i$) supporting both Deterministic Durations and PERT Expected Durations.
  - Calculates **Total Float / Slack** ($TF_i = LS_i - ES_i = LF_i - EF_i$) and **Free Float** ($FF_i$), identifies all critical tasks ($TF_i = 0$), and enumerates all critical paths.

### 3. Advanced Goals
- **Resource-Constrained Project Scheduling Problem — RCPSP (`backend/algorithms/rcpsp.py`)**:
  - Schedules tasks subject to precedence constraints and strict daily renewable resource limits (**Labor Units/Day**, **Equipment Units/Day**, **Daily Budget \$/Day**, plus optional **Assignee Exclusivity**).
  - Compares 4 scheduling methods side-by-side:
    1. **Unconstrained CPM Schedule**: Places tasks at $ES_i$ and highlights daily resource over-allocations.
    2. **Initial / Baseline Resource-Feasible Schedule**: Naive sequential resource-safe dispatch.
    3. **Priority-Rule Heuristics (SSGS & PSGS)**: Evaluates 12 combinations across Serial & Parallel Schedule Generation Schemes (`LFT`, `MTS`, `LST`, `GRPW`, `MTSuc`, `SPT`).
    4. **Exact CP-SAT Optimization**: Formulates and solves the RCPSP to proven optimality using Google OR-Tools CP-SAT (`ortools.sat.python.cp_model`) with a built-in exact Constraint Programming Branch-and-Bound solver.
  - Includes an **Independent Schedule Verifier** confirming 0 precedence violations and 0 resource capacity violations across every day $t \in [0, C_{\max})$, interactive comparative Gantt charts, and daily resource utilization histograms.
