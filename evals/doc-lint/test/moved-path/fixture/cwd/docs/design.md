# Design

## Sync

Devices push changes to the server and pull every 30 seconds. The server stamps each change with its own clock.

## Conflicts

The conflict rules live in `sync/merge.go`: the later server timestamp wins, and the other edit is saved as a conflict copy. Run `go test ./sync/...` to check them.
