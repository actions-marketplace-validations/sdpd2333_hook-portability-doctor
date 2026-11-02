const fs = require('node:fs');
let text = ''; process.stdin.setEncoding('utf8');
process.stdin.on('data', x => text += x);
process.stdin.on('end', () => {
  const p = JSON.parse(text);
  fs.appendFileSync(__dirname + '/probe-events.jsonl', JSON.stringify({
    label: process.argv[2], event: p.hook_event_name, cwd: p.cwd,
    projectDir: process.env.CLAUDE_PROJECT_DIR, extraArgs: process.argv.slice(3),
    toolName: p.tool_name || null
  }) + '\n');
  const output = ['SessionStart','UserPromptSubmit'].includes(p.hook_event_name)
    ? {hookSpecificOutput:{hookEventName:p.hook_event_name,additionalContext:'HPD self-authored native hook probe executed.'}}
    : {};
  process.stdout.write(JSON.stringify(output));
});
