# Architecture and measurements

## Workload

For each row `r`, the circuit calculates:

```text
y[r] = W[r][0] * x[0] + W[r][1] * x[1]
     + W[r][2] * x[2] + W[r][3] * x[3]
```

There are 16 products per operation. Inputs and weights are signed 8-bit integers from −128 to 127. A product fits in signed 16 bits. The sum of four products requires signed 18 bits: four products of −128 × −128 produce 65,536, which would exceed signed 17-bit capacity. The outputs are exact integers with no bias, activation, requantization, clipping, or wrapping.

## Sequential circuit

The controller advances through four columns for each of four rows. One multiplier and one accumulator compute a product and accumulation each processing cycle. At the end of a row, its result is written to that row's output slice and the accumulator is cleared for the next row. All four rows complete after 16 compute cycles.

The row output uses explicit fixed-width slice assignments. This avoids counting an incidental multiplication for dynamic output indexing as a data multiplier in the high-level synthesis report.

## Parallel circuit

Four row lanes run at the same time. Each lane has a multiplier and an accumulator. A shared column counter advances over four columns, and each lane performs one product and accumulation per processing cycle. All four outputs are captured after the fourth compute cycle.

Both circuits latch the input matrix and vector when an idle circuit accepts a start request. Changes to external inputs after acceptance do not change that operation. A start during processing is ignored. Reset is synchronous and active high. Completion produces a one-cycle `done` pulse. The results remain available after completion until the next accepted start or reset. During sequential computation, some row outputs become available before others; consumers should use completion to know the full output is valid.

## Interface packing

| Signal | Width | Packing |
|---|---:|---|
| `weights` | 128 bits | Element `(row, column)` occupies bits `8*(4*row+column) +: 8` |
| `x_vec` | 32 bits | Element `column` occupies bits `8*column +: 8` |
| `y` | 72 bits | Row `row` occupies bits `18*row +: 18` |

Each packed value uses two's-complement representation. The testbench decodes each output slice as a signed 18-bit value.

## What the measurements mean

- **Compute cycles:** clock edges after the input-acceptance edge, through the edge that raises `done`. Input acceptance is excluded.
- **High-level multipliers:** Yosys `$mul` operators after process lowering and optimization, before generic synthesis mapping.
- **Generic cells:** cells in the generic synthesized netlist, without a target FPGA or standard-cell library.
- **Mapped register bits:** flip-flop bits counted from the mapped netlist using the report script's flip-flop cell categories.

The sequential implementation has 256 mapped register bits in the recorded flow; the parallel implementation has 308. These totals reflect all included mapped registers, not only the arithmetic accumulators.

## Selection rule

The selector rejects unverified designs and designs exceeding either active budget. It chooses the eligible design with the smallest generic cell count. Ties are resolved by compute cycles, then architecture name. Limits include their boundary values. If nothing qualifies, it returns no recommendation and lists the reasons.

The recommendation applies only to the saved workload and measured candidates. The tool does not search all possible accelerator architectures or infer unknown power and timing properties.

## Evidence and limits

The comparison script runs both compiled simulations against the same generated vectors before producing the benchmark report. It checks simulator freshness, captures verification logs, runs the same Yosys flow for both designs, and records fingerprints and tool versions. The interface checks source, testbench, and executable fingerprints before running a custom-input simulation.

Clock speed, propagation delay, physical area, power, device-specific resources, data-transfer costs, and sustained throughput are unmeasured. Comparing processing cycles alone cannot establish a wall-clock speedup. Generic synthesis counts are useful for comparing these two designs in the recorded flow, but cannot be treated as physical area or compared blindly across tool flows.
