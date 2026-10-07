# Third-party tools and assistance

AccelScope uses the following external tools. The tools retain their own licenses; this list does not relicense them.

| Tool | Role | Upstream |
|---|---|---|
| Python | Reference arithmetic, selector, scripts, tests, and interface runner | https://www.python.org/ |
| Verilator | Compiles Verilog designs into native simulation models | https://verilator.org/ |
| Yosys | Generic hardware synthesis and resource inspection | https://yosyshq.net/yosys/ |
| GCC / g++ | Compiles the C++ testbenches and generated simulation models | https://gcc.gnu.org/ |
| GNU Make | Builds the native simulators | https://www.gnu.org/software/make/ |
| Streamlit | Local interactive interface | https://streamlit.io/ |
| Git | Source control | https://git-scm.com/ |
| GitHub Actions and actions/checkout | Hosted verification workflow and source checkout | https://github.com/actions/checkout |

Python packages resolved for the development environment are listed in `requirements.lock.txt` when present. Verilator-generated C++ and native build outputs are generated locally and excluded from the source repository.

## AI assistance

ChatGPT/Codex assisted with project planning, source and test drafting, debugging, interface development, and documentation. The developer ran the project locally and supplied the Python test, native simulation, synthesis, and live-interface results used to validate the prototype. AI assistance is disclosed here so reviewers can assess the work and its validation clearly.

## Data and credentials

The reference vectors are generated synthetic integer matrices and vectors. This prototype does not require an external dataset, trained model, API key, or paid cloud service.
