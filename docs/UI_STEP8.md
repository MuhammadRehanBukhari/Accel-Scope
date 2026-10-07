# AccelScope — Phase 1, Step 8

This update adds the visual interface to the existing AccelScope project.

## Install inside Ubuntu

Keep the project virtual environment active. Download the ZIP to Windows Downloads.

    cd /mnt/c/Users/mreha/Documents/accel-scope
    source .venv/bin/activate
    python -m zipfile -e /mnt/c/Users/mreha/Downloads/accelscope-ui-step8.zip .
    python -m pip install -r requirements.txt
    python -m pip freeze > requirements.lock.txt
    python -m streamlit run app/main.py --server.address 127.0.0.1

Open http://localhost:8501 in the Windows browser. Keep the Ubuntu terminal open.
Use Ctrl+C in Ubuntu to stop the application.

## Check the interface

1. At 16 processing cycles with no cell budget, Sequential should be recommended.
2. At 8 cycles with no cell budget, Parallel should be recommended.
3. At 8 cycles with a 2,000-cell budget, neither design should be eligible.
4. Open Test your inputs and run the default example through both simulations.
   The Python reference is [30, -30, 10, -4].
5. Try -128 for every weight and input. Each output should be 65536.
6. Try an input value of 128. The application should reject it.

Native simulation requires the existing compiled executables and the current
reports/architecture-comparison.json. Live tests check the recorded fingerprints
of the circuit, testbench, and executable. If one has changed, rebuild that
simulation and rerun python scripts/compare_architectures.py.

## Files in this update

- app/main.py: interface and custom-input hardware test runner.
- requirements.txt: Streamlit version tested for this interface.
- .streamlit/config.toml: interface theme and headless local server setting.
- docs/UI_STEP8.md: this guide.

Saved benchmark results describe a signed 8-bit 4x4 matrix-vector kernel.
Processing cycles exclude the input-acceptance edge. Generic synthesis cell
counts do not measure physical chip area, maximum clock rate, or power.
