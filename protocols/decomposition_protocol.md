# decomposition protocol

Use this protocol for a construction task. It changes planning behavior only. Do not invent or require a geometry helper API.

1. Before the first `execute_luau`, form a short hierarchy in comments or reasoning:
   - root and ground contact
   - primary masses and silhouette
   - secondary subsystems
   - small details
   Name the parent each subsystem belongs to.

2. Build the root and primary masses first. Keep the first edit focused on the recognizable silhouette. Do not add trim, goods, battlements, handles, or other detail until the primary form exists.

3. Preserve parent connections in code. When a new part belongs on an existing part, derive its placement from that part's actual returned instance, size, position, or CFrame. Do not recreate a supposedly connected parent from memory and do not scatter unrelated absolute coordinates.

4. Build one subsystem per edit in dependency order. After each subsystem, use `inspect_instance`, `search_game_tree`, or a screenshot when useful to verify that the expected named parts exist and are where they should be.

5. Make edits retry-safe. Use stable, descriptive names and check for an existing named part before creating it. If a tool call errors, assume it may have partially applied, inspect the workspace, and continue from what exists. Never replay a complete build blindly after an `execute_luau` error.

6. Finish with a coherence pass: verify ground contact, primary silhouette, required prompt features, visible material contrast, and that secondary pieces visibly attach to their parents. Repair missing or disconnected parts only after inspection.

Use the fewest edits that produce a complete, readable result. A complete simple structure is better than a detailed partial structure.
