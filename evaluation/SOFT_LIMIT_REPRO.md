# Evaluation-only soft-limit reproducer

This loads the complete public large4 model and the already observed v1
cost331 cover, asserts exact feasibility, then invokes the current helper's
default synchronous `bounded=False` HiGHS path with a four-second deadline.
The first JSON announces the request; a returning native call prints actual wall.

After the root pinned-environment setup:

```sh
timeout 20s eligible-baseline/main-env/bin/python -B evaluation/reproduce_soft_limit.py
```

An external timeout exits124. The four-second command is supplied for regression
reproduction; this release executed no additional native run for that script.
Measured evidence is the original v2/v2.1 large4 sixty-second timeouts and
v3's checked prior-incumbent deadline exits. Existing upstream issue coverage:
[#3606](https://github.com/ERGO-Code/HiGHS/issues/3606),
[#3314](https://github.com/ERGO-Code/HiGHS/issues/3314).
The MIP start is evaluation-only; the Main algorithm reads only its instance.
