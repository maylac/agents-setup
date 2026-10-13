# Motion

Use springs for anything a person can touch. Start ordinary moves critically damped (damping ratio `1.0`, response about `0.3–0.4s`). Use a little bounce (about `0.8`) only after a flick or throw. Springs have no prescribed duration; their settle is an outcome of the parameters.

Animate from the current presentation value, never a stale logical target. On reversal, preserve velocity so movement remains continuous. Animate compositor-friendly `transform` and `opacity` via `requestAnimationFrame` or a motion library; avoid layout-property animation.

For fast motion, a subtle stretch or blur can convey speed. Do not add looping or decorative movement that does not communicate state, direction, or causality.
