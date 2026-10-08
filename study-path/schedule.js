'use strict';
// P14-02 scheduling + import/export logic (node-testable; mirrors app.js).
//
// Blocks carry {id, day, startMin, endMin}. Conflicts are reported, never
// silently merged. Imports validate through the model; a failed import
// returns the PREVIOUS plan untouched (progress preserved). Prerequisite
// consistency is enforced by model.validate on every mutation.
const model = require('./model.js');

function overlaps(a, b) {
  return a.day === b.day && a.startMin < b.endMin && b.startMin < a.endMin;
}

function detectConflicts(blocks) {
  const conflicts = [];
  for (let i = 0; i < blocks.length; i++) {
    for (let j = i + 1; j < blocks.length; j++) {
      if (overlaps(blocks[i], blocks[j])) {
        conflicts.push({ a: blocks[i].id, b: blocks[j].id,
                         day: blocks[i].day });
      }
    }
  }
  return conflicts;
}

function planBlock(blocks, block) {
  if (block.startMin >= block.endMin) throw new Error('empty block');
  const clashes = blocks.filter(b => overlaps(b, block));
  if (clashes.length) return { blocks, conflict: clashes.map(b => b.id) };
  return { blocks: [...blocks, block], conflict: null };
}

function importPlan(current, text) {
  try {
    if (Buffer.byteLength(text, 'utf8') > 1000000) {
      throw new Error('Maximum 1 MB');
    }
    const next = model.validate(JSON.parse(text));
    return { plan: next, error: null };
  } catch (err) {
    return { plan: current, error: String((err && err.message) || err) };
  }
}

function exportPlan(plan) {
  return JSON.stringify(model.validate(plan), null, 2);
}

function progressConsistency(plan) {
  const valid = model.validate(plan);
  for (const t of valid.topics) {
    if (t.done && t.requires.some(id =>
      !valid.topics.find(x => x.id === id && x.done))) {
      throw new Error('completed topic has unfinished prerequisites');
    }
  }
  return true;
}

module.exports = { detectConflicts, planBlock, importPlan, exportPlan,
  progressConsistency };
