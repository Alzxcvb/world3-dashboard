# SW (Stabilized World) Scenario: Validation Note

This note records what the SW scenario in `src/scenarios.py` (`run_sw`, lines 64 to 96) changes relative to the base run (`run_bau`, lines 28 to 36), where the code names a source, and what is not verified. Everything below is read from the code, existing docs, the pyworld3 source named where used, and a Crossref lookup for the book citation. The model was not run to write this note (pyworld3 is not installed in the environment used), so no output values were produced for this note; the output figures quoted under Claimed behavior come from the code's own docstring and header (`src/scenarios.py`) and from the smoke test recorded in `tasks/todo.md`.

## What the code says SW is

`run_sw` describes itself as "Stabilized World (Scenario 9)", a full policy bundle of population, economy and technology measures applied together from 2002, and as "the only scenario in Meadows et al. (2004) that avoids overshoot and achieves a sustainable equilibrium" (`src/scenarios.py:65` to `67`; the module header at line 9 repeats the Scenario 9 label). The dashboard text in `web/build_data.py` and `src/app.py` repeats this description.

Source named: Meadows, Randers and Meadows (2004), *Limits to Growth: The 30-Year Update*, Chelsea Green Publishing (the book itself was not fetched; DOI 10.5944/empiria.10.2005.1051 is a Crossref record of a 2005 article in the journal Empiria whose title names the book and "Chelsea Green, 2004", so it is a secondary record, not the book; no page or table number is cited in the code or docs). The Scenario 9 claim is not verified against the source.

## Parameters changed relative to the base run

The base run calls `init_world3_constants()` with no arguments (`src/scenarios.py:31`), so it uses the pyworld3 defaults. SW passes these overrides (`src/scenarios.py:77` to `91`):

| Parameter | SW value | Code comment | Named source for the value |
|---|---|---|---|
| `zpgt` | 2002 | zero population growth target year | none |
| `pet` | 2002 | population equilibrium trigger | none |
| `fcest` | 2002 | family size completion trigger | none |
| `iet` | 2002 | industrial equilibrium trigger | none |
| `iopcd` | 350 | industrial output per capita desired (cap growth) | none |
| `nruf2` | 0.1 | resource efficiency after pyear | none |
| `ppgf2` | 0.1 | pollution generation factor after pyear | none |
| `ppgf21` | 0.1 | secondary pollution chain factor after pyear | none (may have no effect in the coupled run, see assumption 3) |
| `lyf2` | 1.2 | land yield factor (ag tech) | none |
| `alai2` | 1 | arable land adjustment after pyear | none |

Defaults these replace, read from the pyworld3 master branch (world3.py lines 106 to 121, https://raw.githubusercontent.com/cvanwynsberghe/pyworld3/master/pyworld3/world3.py): `zpgt`, `pet`, `fcest`, `iet` = 4000; `iopcd` = 400; `nruf2`, `ppgf2`, `ppgf21` = 1; `lyf2` = 1; `alai2` = 2. Whether the pip release matches master was not checked. The comments are the code author's labels. They were not checked against the pyworld3 source or documentation.

Not changed in SW: `nri` (initial nonrenewable resources). BAU2 and CT both set `nri=2e12` (`src/scenarios.py:42`, `54`); SW does not, so it starts from the default resource stock. CT sets `nruf2=0.125` (`src/scenarios.py:55`) and SW sets `nruf2=0.1`.

Values the code deliberately does not use: the docstring says an earlier spec in `tasks/todo.md` listed 2004 World3-03 values `dcfsn=2` and `imti=350`, and that `dcfsn=2` in the 1974 model "crushes population from 1900" because it is a global constant, not gated by a policy year (`src/scenarios.py:69` to `73`). That statement is the code author's finding and was not independently reproduced here.

## Claimed behavior

The docstring says the chosen switches produce "the correct qualitative SW behavior: population stabilizes near 6B, resources are conserved, no overshoot collapse" (`src/scenarios.py:73` to `74`). Not verified against the source, and not re run for this note.

Known mismatch: `tasks/todo.md` line 11 and line 31 record a smoke test where SW peaks at 6.03B in 2019 and stabilizes near 6B. By the pyworld3 source (assumption 3 below), the SW technology values switch on in 1975 (the `pyear` default) rather than 2002. Whether the resulting population path matches the published Scenario 9 path was not checked. The code's header also says partial 2004 corrections dropped the BAU peak population to 6B "vs. real 8B" (`src/scenarios.py:15` to `16`), which is about the real world, not Scenario 9.

## Assumptions

1. The pip installable pyworld3 is the 1974 World3, and `docs/METHODOLOGY.md` ("Model Version Note") says the same.
2. `zpgt`, `pet`, `fcest` and `iet` are compared against model time in the pyworld3 population and capital sectors (`population.py` lines 850, 921, 945 and `capital.py` line 561 at the master branch), so the value 2002 sets the year they switch on. Their defaults are 4000.
3. The technology values (`nruf2`, `ppgf2`, `lyf2`, `alai2`) are documented in pyworld3 as the value "after time=pyear". The World3 constructor default is `pyear=1975` (https://raw.githubusercontent.com/cvanwynsberghe/pyworld3/master/pyworld3/world3.py, line 94), and `run_sw` builds `World3(dt=0.5, year_min=1900, year_max=2100)` without `pyear` (`src/scenarios.py:76`). So per that source these four values take effect from 1975, not 2002, which contradicts the code header's "applied together from 2002" for the technology part. `ppgf21` is different. Its pyworld3 docstring says only "DESCRIPTION. The default is 1." (pollution.py line 102), and the code reads it only at lines 322 and 352, in `self.ppgf2 = switch(self.ppgf21, self.ppgf22[k], self.swat)`, in code that uses exogenous input functions (`pop_f`, `aiph_f`, `al_f`), which looks like the standalone pollution loop. The coupled run uses `ppgf2` through `clip(self.ppgf2, self.ppgf1, self.time[k], ...)` at line 475 (https://raw.githubusercontent.com/cvanwynsberghe/pyworld3/master/pyworld3/pollution.py). So the SW override of `ppgf21` may have no effect in the coupled run; it was not run to confirm. Read from the master branch on October 24, 2026 (local date); the version installed by `pip install pyworld3` was not checked.
4. The 2002 start date is taken from the 2004 scenario description as the code author recorded it.

## Limitations of adapting a 1974 scenario

1. The code attributes Scenario 9 to Meadows et al. (2004), which is the World3-03 update. The code runs the 1974 model, so SW here is a qualitative stand in, not a reproduction of the published run (`src/scenarios.py:11` to `17`).
2. `docs/METHODOLOGY.md` lists differences between the 1974 and 2004 versions, including `dcfsn` and `alln` defaults and extra policy year parameters in 2004. The 2004 parameter and table set is not applied.
3. The Nebel et al. (2024) recalibration is not integrated (`src/scenarios.py:19` to `20`), so SW is not calibrated to 1970 to 2020 data.
4. The code notes that applying only some 2004 corrections made results worse (`src/scenarios.py:13` to `16`).
5. Because the base run and SW share the 1974 structure but differ in about ten constants, the SW curves should be read as directional. The dashboard's own methodology text says the comparison "is directional, not absolute calibration" (`web/public/index.html`).
6. Before SW is presented as a canonical Scenario 9, each value above needs to be checked against Meadows et al. (2004) and, where relevant, Nebel et al. (2024). This was an open item in `tasks/todo.md`.
