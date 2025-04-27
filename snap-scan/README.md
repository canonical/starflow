# NOT WORKING

Note: This action doesn't work yet, as our hosted runners don't have access to the
security scanning API. Security is working on this.

# Snap scanner

This action uses the security API to scan a snap.

# Usage

```yaml
- uses: canonical/starflow/snap-scan@main
  with:
    # One or paths to snaps, separated with spaces.
    # If no paths are set, no local snaps will be scanned.
    paths: "my-snap_1.snap your-snap_2.snap"

    # One or more snaps on the store to scan.
    # NOTE: Right now this only scans the 'latest/stable' channel.
    store-names: "my-snap your-snap"

    # The channel from which to install the secscan client
    client-channel: "latest/stable"

    # Which scanners to use for scanning the snap.
    scanners: "osv trivy blackduck"
```
