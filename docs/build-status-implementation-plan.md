# Plan: Add `epycloud build status` Command

## Overview

Add a `build status` subcommand to the epycloud CLI to display recent/ongoing Cloud Build jobs, eliminating the need for users to manually use `gcloud builds list` commands.

## Current State

- **Build submission**: Cloud builds are submitted asynchronously with `epycloud build cloud`
- **Build ID tracking**: Build IDs are displayed to user but NOT persisted anywhere
- **Monitoring**: Users must manually copy build IDs and use `gcloud builds` commands
- **Command structure**: Build command uses positional argument `mode` (not subparsers)

## Proposed Solution

Convert the `build` command from positional arguments to subparsers (matching the `workflow` command pattern) and add a new `status` subcommand.

## Implementation Approach

### Option A: Subparser Approach (RECOMMENDED)

**Pros**:
- Matches workflow command pattern (consistency)
- Allows future expansion (`build cancel`, `build describe`)
- Clearer UX: `epycloud build status` vs `epycloud build --status`
- Documentation already anticipates this pattern

**Cons**:
- More refactoring required (~50 lines)
- Changes existing command structure slightly

### Option B: Add Status Flag

**Pros**:
- Simpler implementation
- Less refactoring

**Cons**:
- Inconsistent with other commands
- Less extensible for future features

**Recommendation**: Use Option A (Subparser Approach)

## Detailed Changes

### 1. Refactor `src/epycloud/commands/build.py`

**Current Structure**:
```python
parser.add_argument(
    "mode",
    nargs="?",
    choices=["cloud", "local", "dev"],
    default="cloud",
)
```

**New Structure**:
```python
build_subparsers = parser.add_subparsers(
    dest="build_subcommand",
    help="",
    title="Subcommands",
)

# epycloud build cloud
cloud_parser = build_subparsers.add_parser("cloud", ...)

# epycloud build local
local_parser = build_subparsers.add_parser("local", ...)

# epycloud build dev
dev_parser = build_subparsers.add_parser("dev", ...)

# epycloud build status (NEW)
status_parser = build_subparsers.add_parser("status", ...)
status_parser.add_argument("--limit", type=int, default=20)
status_parser.add_argument("--ongoing", action="store_true")
```

**Handler Routing**:
```python
def handle(ctx: dict[str, Any]) -> int:
    """Route to appropriate subcommand handler."""
    args = ctx["args"]

    if not hasattr(args, "build_subcommand") or args.build_subcommand is None:
        # Show help if no subcommand
        ctx.get("_build_parser").print_help()
        return 1

    if args.build_subcommand == "cloud":
        return _handle_cloud(ctx)
    elif args.build_subcommand == "local":
        return _handle_local(ctx)
    elif args.build_subcommand == "dev":
        return _handle_dev(ctx)
    elif args.build_subcommand == "status":
        return _handle_status(ctx)
```

### 2. Implement `_handle_status()` Function

**Function Logic**:
```python
def _handle_status(ctx: dict[str, Any]) -> int:
    """Display recent/ongoing Cloud Build jobs.

    Uses gcloud builds list with JSON output to fetch build information.
    """
    config = require_config(ctx)
    args = ctx["args"]
    verbose = ctx.get("verbose", False)

    project_id = config.get("PROJECT_ID")
    region = config.get("REGION")

    # Build gcloud command
    cmd = [
        "gcloud", "builds", "list",
        f"--project={project_id}",
        f"--region={region}",
        f"--limit={args.limit}",
        "--format=json",
    ]

    if args.ongoing:
        cmd.append("--ongoing")

    # Execute command
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    builds = json.loads(result.stdout)

    # Display results
    _display_build_status(builds)

    return 0
```

**Display Function**:
```python
def _display_build_status(builds: list[dict]) -> None:
    """Format and display build status in table format."""
    from epycloud.lib.output import info, success, error, warning
    from epycloud.lib.formatters import format_status, format_timestamp_full, format_duration

    if not builds:
        info("No builds found")
        return

    info("Recent Cloud Builds")
    info("=" * 80)

    # Header
    print(f"{'BUILD ID':<38} {'STATUS':<12} {'START TIME':<20} {'DURATION':<10}")
    print("-" * 80)

    # Rows
    for build in builds:
        build_id = build.get("id", "N/A")
        status = build.get("status", "UNKNOWN")
        start_time = build.get("startTime", "")
        finish_time = build.get("finishTime", "")

        # Format status with color
        status_formatted = format_status(status)

        # Format timestamp
        start_formatted = format_timestamp_full(start_time) if start_time else "N/A"

        # Calculate duration
        duration = ""
        if start_time and finish_time:
            duration = format_duration(start_time, finish_time)
        elif start_time:
            # Ongoing build - show elapsed time
            duration = format_duration(start_time, datetime.now().isoformat())

        print(f"{build_id:<38} {status_formatted:<12} {start_formatted:<20} {duration:<10}")

    print()
    info(f"Showing {len(builds)} build(s) (use --limit to adjust)")
```

### 3. Update Documentation

**Files to Update**:

1. **CLAUDE.md** (lines 158-162):
   ```markdown
   **Cloud Build:** Submits asynchronously with layer caching enabled. Returns immediately with a build ID. Monitor with:
   ```bash
   epycloud build status
   epycloud build status --ongoing  # Show only active builds
   ```
   ```

2. **docs/operations.md** (lines 109-116):
   ```markdown
   This submits the build asynchronously and returns immediately with a build ID. Monitor progress with:

   ```bash
   # View build status
   epycloud build status
   epycloud build status --ongoing

   # Or use gcloud commands for specific build
   gcloud builds log <BUILD_ID> --region=$REGION --stream
   gcloud builds describe <BUILD_ID> --region=$REGION
   ```
   ```

3. **docs/google-cloud-guide.md** (line 799-802):
   ```markdown
   # Build
   epycloud build cloud           # Cloud Build (recommended)
   epycloud build local           # Build locally and push
   epycloud build dev             # Build for local development
   epycloud build status          # Check build status (NEW)
   epycloud build status --ongoing # Show only active builds (NEW)
   ```

## Commands After Implementation

```bash
# Build commands
epycloud build cloud                    # Cloud Build (async)
epycloud build local                    # Local build + push
epycloud build dev                      # Local dev build

# Status commands (NEW)
epycloud build status                   # Show last 20 builds
epycloud build status --ongoing         # Show only QUEUED/WORKING builds
epycloud build status --limit 50        # Show last 50 builds
```

## Expected Output

```
Recent Cloud Builds
================================================================================
BUILD ID                              STATUS      START TIME           DURATION
--------------------------------------------------------------------------------
abc123xyz-456                         SUCCESS     2025-11-14 10:30:00  5m 23s
def789uvw-123                         WORKING     2025-11-14 10:45:00  2m 15s
ghi456rst-789                         FAILED      2025-11-14 09:15:00  3m 45s

Showing 3 build(s) (use --limit to adjust)
```

**Status Color Coding** (reuse existing `format_status()`):
- Green: SUCCESS
- Red: FAILURE, CANCELLED, TIMEOUT
- Yellow: QUEUED, WORKING
- Cyan: PENDING

## Implementation Details

### API Choice: gcloud CLI vs REST API

**Decision**: Use gcloud CLI (same as batch job monitoring)

**Rationale**:
- Consistent with existing batch job monitoring pattern
- Simpler implementation (no manual auth token handling)
- Built-in pagination and filtering
- Automatic error handling

**Command**:
```bash
gcloud builds list \
  --project=PROJECT_ID \
  --region=REGION \
  --format=json \
  --limit=20 \
  [--ongoing]
```

### gcloud Output Format

**JSON Structure** (example):
```json
[
  {
    "id": "abc123xyz-456",
    "status": "SUCCESS",
    "startTime": "2025-11-14T10:30:00.123456Z",
    "finishTime": "2025-11-14T10:35:23.789012Z",
    "source": {
      "storageSource": {
        "bucket": "...",
        "object": "..."
      }
    },
    "logUrl": "https://..."
  }
]
```

**Fields to Display**:
- `id` - Build ID
- `status` - Build status (SUCCESS, FAILURE, WORKING, QUEUED, etc.)
- `startTime` - When build started
- `finishTime` - When build finished (if completed)

## Files to Modify

1. **`src/epycloud/commands/build.py`** - Main implementation (~150 lines changed)
   - Refactor to use subparsers
   - Add `_handle_status()` function
   - Add `_display_build_status()` function

2. **`CLAUDE.md`** - Update build monitoring section (~5 lines)

3. **`docs/operations.md`** - Update Cloud Build section (~10 lines)

4. **`docs/google-cloud-guide.md`** - Update CLI reference (~5 lines)

## Testing Considerations

**Manual Testing**:
1. Submit cloud build: `epycloud build cloud`
2. Check status: `epycloud build status`
3. Verify ongoing filter: `epycloud build status --ongoing`
4. Test with no builds: Ensure graceful empty state
5. Test with completed builds: Verify duration calculation
6. Test with failed builds: Verify status color coding

**Edge Cases**:
- No builds exist (empty list)
- Build without finish time (ongoing build)
- Invalid gcloud auth
- Missing gcloud CLI
- Different region than config

## Challenges and Considerations

### 1. No Build ID Persistence
- **Challenge**: Build IDs are not saved anywhere
- **Solution**: `build status` lists all recent builds, no need to remember ID
- **Future**: Could add `~/.config/epycloud/build_history.json`

### 2. Backward Compatibility
- **Challenge**: Changing to subparsers changes command structure
- **Impact**: Minimal - `epycloud build` still works (defaults to `cloud`)
- **Mitigation**: Update documentation, provide clear error messages

### 3. Region Handling
- **Challenge**: Builds are regional
- **Solution**: Use config region by default
- **Future**: Add `--region` flag to override

### 4. Watch Mode
- **Future Enhancement**: Add `--watch` flag like `epycloud status --watch`
- **For Now**: Start with one-time display

## Estimated Complexity

**Total Effort**: Medium

**Breakdown**:
- Subparser refactoring: ~50 lines
- Status handler implementation: ~100 lines
- Display formatting: ~50 lines
- Documentation updates: ~20 lines
- Testing: 1-2 hours

**Total**: ~220 lines of code, 2-3 hours implementation time

## Future Enhancements

1. **Build History Tracking**: Save last N build IDs to local config
2. **Watch Mode**: `epycloud build status --watch` for live updates
3. **Build Details**: `epycloud build describe <build-id>` for full details
4. **Build Logs**: `epycloud build logs <build-id>` to stream logs
5. **Build Cancel**: `epycloud build cancel <build-id>` to cancel running build

## Summary

This implementation adds a frequently-requested feature that aligns with existing CLI patterns and documentation. The subparser approach ensures consistency with other commands and provides a foundation for future build management features.
