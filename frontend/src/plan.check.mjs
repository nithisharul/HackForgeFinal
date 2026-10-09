// Run: node frontend/src/plan.check.mjs
import assert from 'node:assert/strict'
import { bits, infoGain, plan } from './plan.js'

assert.equal(bits(0.5), 1)
assert.equal(bits(1), 0)
assert.ok(Math.abs(bits(0.95) - 0.286) < 0.001) // the spec's H = 0.286 b example
assert.ok(Math.abs(infoGain(0.5, 1, 0) - 1) < 1e-9) // a perfect test removes all doubt
assert.equal(infoGain(0.5, 0.3, 0.3), 0) // a test that ignores the truth removes none
for (const p of [0.05, 0.3, 0.5, 0.95]) assert.ok(infoGain(p, 0.8, 0.1) <= bits(p) + 1e-12)

const us = plan(0.95, 'impossible_timing', 'us')
assert.equal(us[0].id, 'logs')
assert.equal(us[0].u, 1)
assert.ok(us.every((a) => a.id !== 'field')) // India-only step stays out of the US plan
assert.ok(plan(0.6, 'claim_after_death', 'in').some((a) => a.id === 'registry'))
console.log('plan ok')
