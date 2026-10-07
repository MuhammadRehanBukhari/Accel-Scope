# Reproduction and troubleshooting

## Full rebuild

Install the Ubuntu prerequisites and Python dependencies listed in README.md. Activate the virtual environment, then run from the repository root:

```bash
python scripts/rebuild.py
```

The command uses the vector generator's defaults: six targeted cases and 1,000 deterministic random cases. It runs the Python suite, regenerates vectors, lints the RTL with warnings enabled, compiles fresh native simulators, then invokes the architecture comparison script. That final script verifies both simulations and runs Yosys for each architecture.

Generated simulator object directories `build/seq/obj/` and `build/parallel/obj/` are rebuilt. No source files are removed. Build outputs are excluded from Git; the evidence in `reports/` is retained for review and refreshed on a successful comparison.

The recorded development environment used Python 3.12.3, Verilator 5.020, Yosys 0.33, g++ 13.3.0, and GNU Make 4.3. The automated GitHub workflow uses Ubuntu 24.04 and installs its distribution tool packages. Consult each generated report for the actual versions used by that run. Exact generic cell counts can vary with tool versions and synthesis changes; verification correctness and compute-cycle counts are the functional requirements.

## Python tests only

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

## Manual native checks after a build

```bash
build/seq/obj/Vaccelscope_seq build/seq/vectors.txt
build/parallel/obj/Vaccelscope_parallel build/seq/vectors.txt
python scripts/compare_architectures.py
```

Expected completion measurements are 16 compute cycles for Sequential and 4 for Parallel. Both executables should report all reference cases passing, alongside protocol and reset checks.

## Interface

```bash
python -m streamlit run app/main.py --server.address 127.0.0.1
```

Open http://localhost:8501. The live-input test writes a temporary single-case vector file and runs the same native testbench executables. Those executables compare the hardware output with the Python reference and also perform their built-in protocol and reset checks. The app rejects a failed simulation or a cycle measurement inconsistent with the saved report.

## Troubleshooting

| Symptom | Action |
|---|---|
| A hardware tool is missing | Install `verilator yosys g++ make` inside Ubuntu, not only on Windows |
| Python cannot import `accelscope` | Activate the project environment; use `PYTHONPATH=src` for standalone Python test discovery |
| Live simulations are disabled after cloning | Run `python scripts/rebuild.py` to create local executables and matching evidence |
| A saved fingerprint no longer matches | Rebuild and regenerate the report after the RTL, testbench, or executable changes |
| A compiler step fails | Read its full log under `build/logs/`; the rebuild also prints the end of the log |
| Neither design meets the limits | Inspect the exclusion reasons; increase a budget or implement and verify another architecture |
| The interface command occupies the terminal | This is expected while the server runs; use Ctrl+C to stop it |

## GitHub verification

The included workflow runs on pushes, pull requests, and manual dispatch. It installs the native tools and pinned Python interface dependency, then runs the rebuild command. A workflow file being present does not establish a passing hosted run; inspect the Actions result after pushing the repository.

The workflow regenerates reports in its working checkout and prints the comparison in its log. It does not commit regenerated reports back to the repository. Saved repository evidence should be refreshed locally when making changes that affect the benchmark.
