# Gesture behavior

Use Pointer Events and `setPointerCapture`. Preserve the offset where the person grabbed the object, collect a short timestamped position history, and use the release velocity rather than only the final position.

Do not use fixed CSS transitions or keyframes for gesture-driven movement. A new drag must start from the live rendered transform and carry velocity through a retarget; use independent X/Y springs when their velocities differ.

Project release velocity to choose a snap target, then hand the same velocity into the spring. Apple's exponential projection is:

```js
function project(initialVelocity, decelerationRate = 0.998) {
  return (initialVelocity / 1000) * decelerationRate / (1 - decelerationRate);
}
const target = nearestSnapPoint(currentPosition + project(releaseVelocity));
```

Use a small movement threshold before committing to a drag direction. At a boundary, apply increasing resistance instead of a hard stop:

```js
function rubberband(overshoot, dimension, constant = 0.55) {
  return (overshoot * dimension * constant) /
    (dimension + constant * Math.abs(overshoot));
}
```

Mirror entry and exit paths, anchor popovers and sheets to their trigger, and let intermediate movement hint at the chosen destination.
