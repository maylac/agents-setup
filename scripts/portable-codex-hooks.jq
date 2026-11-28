def rex_session_start_group:
  (keys == ["hooks"])
  and ((.hooks | length) == 1)
  and (.hooks[0] == {
    "command": "/bin/sh -c 'rex __internal session-start --agent codex --feature-session-naming=false 2>/dev/null || true'",
    "timeout": 5,
    "type": "command"
  });

if ((.hooks | type) == "object") then
  (.hooks.SessionStart // [] | map(select(rex_session_start_group)) | length) as $rex_group_count
  | if $rex_group_count > 1 then
      error("duplicate exact Rex SessionStart groups")
    elif $rex_group_count == 1 then
      .hooks.SessionStart |= map(select(rex_session_start_group | not))
      | if (.hooks.SessionStart | length) == 0 then del(.hooks.SessionStart) else . end
    else . end
else . end
